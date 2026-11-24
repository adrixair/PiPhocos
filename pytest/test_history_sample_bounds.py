from datetime import datetime, timedelta, timezone

import pytest

import server
from database import Database
from phocos_store import ensure_schema


@pytest.fixture
def history_db(tmp_path):
    db = Database(str(tmp_path / "history_bounds.sqlite"))
    ensure_schema(db)
    # These indexes are also present in the production database. Keep a single
    # recent day in samples, the distribution that triggered the historical scan.
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_samples_local_day_recorded_at "
        "ON samples(local_day, recorded_at)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_compressed_samples_day_recorded_at "
        "ON compressed_samples_10m(local_day, recorded_at)"
    )
    recent_start = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)
    rows = []
    for offset in range(400):
        recorded_at = (recent_start + timedelta(seconds=offset)).isoformat()
        rows.append(
            (recorded_at, recorded_at[:16], "2026-11-18", "2026-11", "2026", "{}")
        )
    with db.transaction():
        db.executemany(
            """
            INSERT INTO samples (
                recorded_at, recorded_minute, local_day, local_month,
                local_year, raw_snapshot_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        for recorded_at in (
            "2026-11-11T12:00:00+00:00",
            "2026-11-11T12:10:00+00:00",
            "2026-11-12T12:00:00+00:00",
            # Preserve UNION ALL's count even if sources share a timestamp.
            recent_start.isoformat(),
        ):
            db.execute(
                """
                INSERT INTO compressed_samples_10m (
                    bucket_local, recorded_at, recorded_minute,
                    local_day, local_month, local_year
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [recorded_at, recorded_at, recorded_at[:16], recorded_at[:10],
                 recorded_at[:7], recorded_at[:4]],
            )
    db.execute("ANALYZE")
    yield db
    db.close()


@pytest.mark.parametrize(
    "filters",
    [
        {},
        {"local_day": "2026-11-11"},
        {"local_day": "2026-11-18"},
        {"local_day": "2026-11-01"},
        {"since_iso": "2026-11-11T12:10:00+00:00"},
        {"since_iso": "2026-11-19T00:00:00+00:00"},
        {"local_day": "2026-11-11", "since_iso": "2026-11-11T12:10:00+00:00"},
        {"local_day": "2026-11-11", "since_iso": "2026-11-12T00:00:00+00:00"},
    ],
)
def test_history_bounds_match_union_for_date_and_time_filters(history_db, filters):
    bounds, where_clause, params = server._history_sample_bounds(history_db, **filters)
    expected = history_db.fetchone(
        f"""
        SELECT COUNT(*) AS sample_count,
               MIN(recorded_at) AS first_recorded_at,
               MAX(recorded_at) AS last_recorded_at
        FROM history_samples {where_clause}
        """,
        params,
    )

    assert dict(bounds) == dict(expected)


def test_archived_day_bounds_use_indexes_without_scanning_recent_samples(
    history_db, monkeypatch
):
    captured = []
    original_fetchone = history_db.fetchone

    def capture_query(query, params=None):
        captured.append((query, params))
        return original_fetchone(query, params)

    monkeypatch.setattr(history_db, "fetchone", capture_query)
    bounds, _, _ = server._history_sample_bounds(history_db, local_day="2026-11-11")
    query, params = captured[-1]
    plan = [
        row["detail"]
        for row in history_db.execute("EXPLAIN QUERY PLAN " + query, params)
    ]

    assert bounds["sample_count"] == 2
    assert any("SEARCH samples USING COVERING INDEX" in step for step in plan), plan
    assert any(
        "SEARCH compressed_samples_10m USING COVERING INDEX" in step
        for step in plan
    ), plan
    assert not any("SCAN samples" in step for step in plan), plan


@pytest.mark.parametrize("table", ["samples", "compressed_samples_10m", "minute_samples"])
def test_history_bounds_keep_single_source_queries(history_db, table):
    bounds, where_clause, params = server._history_sample_bounds(
        history_db,
        local_day="2026-11-18",
        since_iso="2026-11-18T12:00:00+00:00",
        table=table,
    )
    expected = history_db.fetchone(
        f"""
        SELECT COUNT(*) AS sample_count,
               MIN(recorded_at) AS first_recorded_at,
               MAX(recorded_at) AS last_recorded_at
        FROM {table} {where_clause}
        """,
        params,
    )

    assert dict(bounds) == dict(expected)
