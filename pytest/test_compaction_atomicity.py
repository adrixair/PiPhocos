import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from database import Database
from phocos_store import compact_historical_samples, ensure_schema, record_snapshot


@pytest.mark.parametrize("failed_table", ["samples", "minute_samples"])
def test_sqlite_full_after_archiving_rolls_back_every_compaction_step(
    tmp_path, monkeypatch, failed_table
):
    db = Database(tmp_path / "compaction.sqlite")
    try:
        ensure_schema(db)
        start = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)
        for minute in range(3):
            record_snapshot(
                db,
                {
                    "recorded_at": (start + timedelta(minutes=minute)).isoformat(),
                    "pv_power_w": 700.0 + minute * 100,
                    "ac_output_active_power_w": 500.0,
                },
                {}, [], max_gap_seconds=180, persist_raw_frames=False,
                refresh_rollups=False, run_compaction=False,
            )
        history_query = (
            "SELECT recorded_at, pv_power_w, ac_output_active_power_w "
            "FROM history_samples ORDER BY recorded_at"
        )
        before_history = [tuple(row) for row in db.execute(history_query)]
        assert len(before_history) == 3
        before_sources = {
            table: db.fetchone(f"SELECT COUNT(*) AS count FROM {table}")["count"]
            for table in ("samples", "minute_samples", "compressed_samples_10m")
        }
        original_execute = db.execute
        failure_observed = []

        def full_during_delete(query, params=None):
            if query.split()[:3] == ["DELETE", "FROM", failed_table]:
                archived = original_execute(
                    "SELECT COUNT(*) AS count FROM compressed_samples_10m"
                )[0]["count"]
                raw_remaining = original_execute(
                    "SELECT COUNT(*) AS count FROM samples"
                )[0]["count"]
                # The failure happens after the archive was written, and in
                # the second case also after the raw deletion was executed.
                assert archived > 0
                assert raw_remaining == (3 if failed_table == "samples" else 0)
                failure_observed.append(True)
                raise sqlite3.OperationalError("database or disk is full")
            return original_execute(query, params)

        monkeypatch.setattr(db, "execute", full_during_delete)
        with pytest.raises(sqlite3.OperationalError, match="database or disk is full"):
            compact_historical_samples(
                db,
                reference_time=start + timedelta(hours=2),
                retention_hours=0,
            )

        assert failure_observed == [True]
        assert db.connection.in_transaction is False
        assert [tuple(row) for row in db.execute(history_query)] == before_history
        for table, expected_count in before_sources.items():
            assert db.fetchone(f"SELECT COUNT(*) AS count FROM {table}")["count"] == expected_count
    finally:
        db.close(optimize=False)
