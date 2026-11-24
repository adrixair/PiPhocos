import sqlite3
from types import SimpleNamespace

import pytest
import server
import storage_guard


def test_storage_endpoint_reads_metrics_without_opening_acquisition_database(tmp_path, monkeypatch):
    db_path = tmp_path / "db.sqlite"
    with sqlite3.connect(db_path) as db:
        db.execute("CREATE TABLE energy_summary_days (local_day TEXT PRIMARY KEY)")
        db.executemany(
            "INSERT INTO energy_summary_days VALUES (?)",
            [("2026-11-11",), ("2026-11-18",)],
        )
    monkeypatch.setattr(server, "DB_PATH", db_path)
    monkeypatch.setattr(server, "DATA_DIR", tmp_path)
    monkeypatch.setattr(server, "config", SimpleNamespace(config_data={
        "database": {"raw_history_retention_hours": 6, "energy_interval_retention_days": 45},
        "secret": "never expose this",
    }))

    def fail_open():
        raise AssertionError("Storage status must not initialize or migrate the database")

    monkeypatch.setattr(server, "_open_db", fail_open)
    response = server.app.test_client().get("/api/storage")
    payload = response.get_json()
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert payload["history"] == {"first_day": "2026-11-11", "last_day": "2026-11-18"}
    assert payload["database"]["file_bytes"] == db_path.stat().st_size
    assert payload["retention"]["raw_history_hours"] == 6
    assert "never expose this" not in response.get_data(as_text=True)
    assert str(tmp_path) not in response.get_data(as_text=True)


def test_saturated_storage_keeps_history_readable_without_schema_writes(tmp_path, monkeypatch):
    path = tmp_path / "history.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE history (value TEXT)")
        connection.execute("INSERT INTO history VALUES ('old period')")
    monkeypatch.setattr(server, "DB_PATH", path)
    monkeypatch.setattr(server, "_SCHEMA_READY", False)
    monkeypatch.setattr(server, "_recording_storage_pressure", lambda: {"write_allowed": False})

    def fail_schema(*args):
        raise AssertionError("Paused history must never migrate its schema")

    monkeypatch.setattr(server, "ensure_schema", fail_schema)
    with server.app.test_request_context():
        db = server._open_db()
        assert db.read_only
        assert db.fetchone("SELECT value FROM history")["value"] == "old period"
        with pytest.raises(sqlite3.OperationalError, match="readonly|read-only"):
            db.execute("DELETE FROM history")
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT value FROM history").fetchall() == [("old period",)]
    assert not server._SCHEMA_READY


def test_storage_endpoint_reports_pause_without_hiding_space_or_history(tmp_path, monkeypatch):
    path = tmp_path / "db.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE energy_summary_days (local_day TEXT PRIMARY KEY)")
        connection.execute("INSERT INTO energy_summary_days VALUES ('2026-11-11')")
    monkeypatch.setattr(server, "DB_PATH", path)
    monkeypatch.setattr(server, "DATA_DIR", tmp_path)
    monkeypatch.setattr(server, "config", SimpleNamespace(config_data={}))
    monkeypatch.setattr(storage_guard.shutil, "disk_usage", lambda path: SimpleNamespace(
        free=100, used=900, total=1000,
    ))
    payload = server.app.test_client().get("/api/storage").get_json()
    assert payload["state"] == "ok"
    assert payload["recording"]["write_allowed"] is False
    assert payload["recording"]["reason"] == "low_disk_space"
    assert payload["disk"]["free_bytes"] == 100
    assert payload["history"]["first_day"] == "2026-11-11"
