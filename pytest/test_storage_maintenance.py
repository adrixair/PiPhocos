from datetime import datetime, timezone

from database import Database
from phocos_store import compact_historical_samples, ensure_schema


def test_new_schema_has_covering_history_indexes(tmp_path):
    db = Database(tmp_path / "storage.sqlite")
    try:
        ensure_schema(db)
        for table, index in (
            ("samples", "idx_samples_local_day_recorded_at"),
            ("compressed_samples_10m", "idx_compressed_samples_day_recorded_at"),
        ):
            columns = db.execute(f"PRAGMA index_info({index})")
            assert [row["name"] for row in columns] == ["local_day", "recorded_at"]
            plan = db.execute(
                f"EXPLAIN QUERY PLAN SELECT COUNT(*), MIN(recorded_at), "
                f"MAX(recorded_at) FROM {table} WHERE local_day = ?",
                ["2026-11-11"],
            )
            assert any("COVERING INDEX" in row["detail"] for row in plan)
    finally:
        db.close()


def test_compaction_without_expired_samples_avoids_wide_aggregation(tmp_path):
    db = Database(tmp_path / "storage.sqlite")
    try:
        ensure_schema(db)
        db.execute(
            """INSERT INTO samples (
                recorded_at, recorded_minute, archive_bucket_local,
                local_day, local_month, local_year, raw_snapshot_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [
                "2026-11-18T11:59:00+00:00", "2026-11-18T12:59",
                "2026-11-18T12:50", "2026-11-18", "2026-11", "2026", "{}",
            ],
        )
        statements = []
        db.connection.set_trace_callback(statements.append)
        compact_historical_samples(
            db,
            reference_time=datetime(2026, 11, 18, 12, tzinfo=timezone.utc),
            retention_hours=6,
        )
        db.connection.set_trace_callback(None)
        assert not any("WITH eligible" in statement for statement in statements)
        assert not any(statement.startswith("DELETE") for statement in statements)
        assert db.fetchone("SELECT COUNT(*) AS count FROM samples")["count"] == 1
        assert db.fetchone("SELECT COUNT(*) AS count FROM compressed_samples_10m")["count"] == 0
    finally:
        db.close()
