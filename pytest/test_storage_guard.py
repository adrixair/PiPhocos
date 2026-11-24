import copy
import logging
import sqlite3
from types import SimpleNamespace

import pytest

import database as database_module
import grabber
import storage_guard
from config import DEFAULT_CONFIG
from database import Database


def pressure(allowed):
    return {"state": "ok" if allowed else "paused", "write_allowed": allowed,
            "reason": None if allowed else "low_disk_space",
            "free_bytes": 2 * 1024**3 if allowed else 100,
            "total_bytes": 8 * 1024**3, "min_free_bytes": 512 * 1024**2}


@pytest.mark.parametrize("value", [None, "bad", 0, -1, float("nan"), float("inf")])
def test_storage_reserve_has_safe_default_for_invalid_configuration(value):
    assert storage_guard.configured_min_free_bytes({"database": {"min_free_space_mb": value}}) == 512 * 1024**2


def test_storage_pressure_is_fail_closed_and_recovers_without_reclaiming_data(tmp_path, monkeypatch):
    usages = iter([OSError("unavailable"), SimpleNamespace(free=100, total=1000),
                   SimpleNamespace(free=900, total=1000)])

    def usage(path):
        result = next(usages)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(storage_guard.shutil, "disk_usage", usage)
    assert storage_guard.get_storage_pressure(tmp_path, min_free_bytes=512)["reason"] == "disk_usage_unavailable"
    assert storage_guard.get_storage_pressure(tmp_path, min_free_bytes=512)["reason"] == "low_disk_space"
    assert storage_guard.get_storage_pressure(tmp_path, min_free_bytes=512)["write_allowed"]
    assert storage_guard.configured_min_free_bytes({"database": {"min_free_space_mb": 128}}) == 128 * 1024**2


def test_read_only_database_reads_wal_without_optimization_commits_or_schema_changes(tmp_path, monkeypatch):
    path = tmp_path / "history with spaces.sqlite"
    writer = Database(path)
    writer.execute("CREATE TABLE history (value TEXT)")
    writer.execute("INSERT INTO history VALUES (?)", ["keep this history"])
    statements = []
    original_connect = sqlite3.connect

    def connect(*args, **kwargs):
        connection = original_connect(*args, **kwargs)
        connection.set_trace_callback(statements.append)
        return connection

    monkeypatch.setattr(database_module.sqlite3, "connect", connect)
    reader = Database(path, read_only=True)
    try:
        assert reader.fetchone("SELECT value FROM history")["value"] == "keep this history"
        with pytest.raises(sqlite3.OperationalError, match="readonly|read-only"):
            reader.execute("DELETE FROM history")
        with pytest.raises(sqlite3.OperationalError, match="read-only"):
            reader.checkpoint_wal(truncate=True)
        reader.optimize(force=True)
    finally:
        reader.close()
        writer.close(optimize=False)
    assert not any("OPTIMIZE" in q.upper() or q.upper() == "COMMIT" for q in statements)
    missing = tmp_path / "missing.sqlite"
    with pytest.raises(sqlite3.OperationalError):
        Database(missing, read_only=True)
    assert not missing.exists()


def test_paused_storage_blocks_poll_recording_open_and_all_maintenance(monkeypatch):
    monkeypatch.setattr(grabber, "_storage_pressure", lambda: pressure(False))
    calls = []
    monkeypatch.setattr(grabber, "Database", lambda *a, **k: calls.append("open"))
    monkeypatch.setattr(grabber, "ensure_schema", lambda *a: calls.append("schema"))
    for name in ("record_snapshot", "compact_historical_samples", "refresh_current_summary_rollups",
                 "prune_detailed_energy_intervals"):
        monkeypatch.setattr(grabber, name, lambda *a, **k: calls.append("write"))
    device = SimpleNamespace(poll=lambda: calls.append("poll"))

    with pytest.raises(storage_guard.StoragePressure):
        grabber._open_recording_database()
    with pytest.raises(storage_guard.StoragePressure):
        grabber.update_data(device, None, 1)
    with pytest.raises(storage_guard.StoragePressure):
        grabber.run_maintenance(None, prune_energy_intervals_due=True)
    assert calls == []


def test_pause_remains_active_if_database_cleanup_reports_an_io_error(monkeypatch):
    disabled = []
    monkeypatch.setattr(grabber, "_set_file_logging", disabled.append)

    def fail_close(**kwargs):
        assert kwargs == {"optimize": False}
        raise sqlite3.OperationalError("disk I/O error")

    grabber._pause_recording(SimpleNamespace(close=fail_close), pressure(False), False)
    assert disabled == [False]


def test_space_loss_before_pruning_stops_destructive_maintenance(monkeypatch):
    statuses = iter([pressure(True), pressure(True), pressure(False)])
    monkeypatch.setattr(grabber, "_storage_pressure", lambda: next(statuses))
    monkeypatch.setattr(grabber, "config", SimpleNamespace(config_data={"database": {}}))
    calls = []
    monkeypatch.setattr(grabber, "compact_historical_samples", lambda *a, **k: calls.append("compact"))
    monkeypatch.setattr(grabber, "refresh_current_summary_rollups", lambda *a, **k: calls.append("rollups"))
    monkeypatch.setattr(grabber, "prune_detailed_energy_intervals", lambda *a, **k: calls.append("prune"))
    with pytest.raises(storage_guard.StoragePressure):
        grabber.run_maintenance(None, prune_energy_intervals_due=True)
    assert calls == ["compact", "rollups"]


def setup_main(monkeypatch, tmp_path):
    clock = [0.0]
    monkeypatch.setattr(grabber.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(grabber.time, "sleep", lambda duration: clock.__setitem__(0, clock[0] + duration))
    monkeypatch.setattr(grabber.signal, "signal", lambda *a: None)
    monkeypatch.setattr(grabber, "run", True)
    cfg = SimpleNamespace(config_data=copy.deepcopy(DEFAULT_CONFIG), log_level=logging.INFO)
    monkeypatch.setattr(grabber, "Config", lambda *a: cfg)
    monkeypatch.setattr(grabber, "set_time_zone", lambda *a: None)
    monkeypatch.setattr(grabber, "TempoApiClient", lambda *a: SimpleNamespace(refresh_if_due_background=lambda **k: None))
    monkeypatch.setattr(grabber, "_set_file_logging", lambda *a: None)
    monkeypatch.setattr(grabber, "DATA_DIR", tmp_path)
    monkeypatch.setattr(grabber, "DB_PATH", tmp_path / "main.sqlite")
    return clock


def test_startup_waits_before_database_open_then_recording_resumes(tmp_path, monkeypatch):
    clock = setup_main(monkeypatch, tmp_path)
    monkeypatch.setattr(grabber, "_storage_pressure", lambda: pressure(clock[0] >= 2))
    opened, recorded, maintenance = [], [], []
    original_database = Database

    def database(*a, **k):
        opened.append(clock[0])
        return original_database(*a, **k)

    def poll():
        grabber.run = False
        return {"snapshot": {"recorded_at": "2026-11-18T12:00:00+00:00"},
                "capabilities": {}, "raw_frames": []}

    monkeypatch.setattr(grabber, "Database", database)
    monkeypatch.setattr(grabber, "ensure_schema", lambda *a: None)
    monkeypatch.setattr(grabber, "record_snapshot", lambda **kw: recorded.append(clock[0]))
    monkeypatch.setattr(grabber, "run_maintenance", lambda *a, **k: maintenance.append(clock[0]))
    monkeypatch.setattr(grabber, "_pricing_from_cached_tempo", lambda **k: {})
    monkeypatch.setattr(grabber, "Phocos", lambda *a: SimpleNamespace(poll=poll, close=lambda: None))
    grabber.main()
    assert opened == [2.0]
    assert recorded == [2.0]
    assert maintenance == []


def test_sqlite_full_pauses_retries_and_never_runs_cleanup(tmp_path, monkeypatch):
    clock = setup_main(monkeypatch, tmp_path)
    monkeypatch.setattr(grabber, "_storage_pressure", lambda: pressure(True))
    attempts, closed, maintenance = [], [], []
    monkeypatch.setattr(grabber, "_open_recording_database", lambda: SimpleNamespace(close=lambda **kw: closed.append(kw)))
    monkeypatch.setattr(grabber, "Phocos", lambda *a: SimpleNamespace(close=lambda: None))
    monkeypatch.setattr(grabber, "run_maintenance", lambda *a, **k: maintenance.append(clock[0]))

    def update(*a):
        attempts.append(clock[0])
        if len(attempts) == 1:
            raise sqlite3.OperationalError("database or disk is full")
        grabber.run = False

    monkeypatch.setattr(grabber, "update_data", update)
    grabber.main()
    assert attempts == [0.0, 30.0]
    assert all(call == {"optimize": False} for call in closed)
    assert maintenance == []


def test_sqlite_full_fixture_preserves_preexisting_history(tmp_path):
    db = Database(tmp_path / "bounded.sqlite")
    try:
        db.execute("CREATE TABLE history (id INTEGER PRIMARY KEY, payload BLOB)")
        db.execute("INSERT INTO history (payload) VALUES (?)", [b"existing history"])
        pages = db.fetchone("PRAGMA page_count")["page_count"]
        db.execute(f"PRAGMA max_page_count={pages}")
        with pytest.raises(sqlite3.OperationalError) as error:
            with db.transaction():
                db.execute("INSERT INTO history (payload) VALUES (?)", [b"x" * 100_000])
        assert storage_guard.is_sqlite_full(error.value)
        assert db.fetchone("SELECT payload FROM history WHERE id = 1")["payload"] == b"existing history"
        assert db.fetchone("SELECT COUNT(*) AS count FROM history")["count"] == 1
    finally:
        db.close(optimize=False)
