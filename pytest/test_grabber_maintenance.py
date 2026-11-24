from types import SimpleNamespace

import pytest

import grabber
from database import Database


def test_frequent_maintenance_respects_hourly_statistics_interval(tmp_path, monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(grabber.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(Database, "_last_optimize_monotonic", 0.0)
    monkeypatch.setattr(grabber, "config", SimpleNamespace(config_data={"database": {}}))
    monkeypatch.setattr(grabber, "compact_historical_samples", lambda *a, **kw: None)
    monkeypatch.setattr(grabber, "refresh_current_summary_rollups", lambda *a, **kw: None)
    db = Database(str(tmp_path / "maintenance.sqlite"))
    statements = []
    db.connection.set_trace_callback(statements.append)
    try:
        for maintenance_time in (160.0, 220.0):
            clock[0] = maintenance_time
            grabber.run_maintenance(db)

        assert not any(statement.upper() == "PRAGMA OPTIMIZE" for statement in statements)

        clock[0] = 3700.0
        grabber.run_maintenance(db)

        assert sum(statement.upper() == "PRAGMA OPTIMIZE" for statement in statements) == 1
    finally:
        db.close()


@pytest.mark.parametrize("prune_due", [False, True])
@pytest.mark.parametrize("wal_mb", [64, 97])
def test_maintenance_logs_stage_times_and_keeps_retention_and_checkpoint_policy(
    monkeypatch, caplog, prune_due, wal_mb
):
    clock = [100.0]
    calls = []
    monkeypatch.setattr(grabber.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(
        grabber,
        "config",
        SimpleNamespace(config_data={"database": {
            "raw_history_retention_hours": 13,
            "energy_interval_retention_days": 99,
            "energy_interval_prune_max_days": 4,
            "wal_truncate_threshold_mb": 96,
        }}),
    )

    def compact(db, *, retention_hours):
        calls.append(("compact", retention_hours))
        clock[0] += 1.5

    def refresh(db):
        calls.append(("refresh",))
        clock[0] += 2.5

    def prune(db, *, retention_days, max_days):
        calls.append(("prune", retention_days, max_days))
        clock[0] += 3.0
        return {"pruned_intervals": 7}

    class MaintenanceDatabase:
        def optimize(self):
            clock[0] += 0.25

        def wal_size_bytes(self):
            return wal_mb * 1024 * 1024

        def checkpoint_wal(self, *, truncate):
            calls.append(("checkpoint", truncate))
            clock[0] += 0.5
            return [{"busy": 0, "log": 20, "checkpointed": 20}]

    monkeypatch.setattr(grabber, "compact_historical_samples", compact)
    monkeypatch.setattr(grabber, "refresh_current_summary_rollups", refresh)
    monkeypatch.setattr(grabber, "prune_detailed_energy_intervals", prune)

    with caplog.at_level("INFO"):
        grabber.run_maintenance(MaintenanceDatabase(), prune_energy_intervals_due=prune_due)

    expected_calls = [("compact", 13), ("refresh",)]
    if prune_due:
        expected_calls.append(("prune", 99, 4))
    expected_calls.append(("checkpoint", wal_mb > 96))
    assert calls == expected_calls
    message = caplog.records[-1].getMessage()
    assert f"maintenance completed in {7.75 if prune_due else 4.75:.3f}s" in message
    assert "compaction=1.500s rollups=2.500s" in message
    assert f"prune={3.0 if prune_due else 0.0:.3f}s" in message
    assert "optimize=0.250s checkpoint=0.500s" in message
    assert f"wal_size={wal_mb * 1024 * 1024}" in message
    assert "checkpoint_result=[{'busy': 0, 'log': 20, 'checkpointed': 20}]" in message
