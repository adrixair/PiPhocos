import json
import os
import time
from datetime import datetime, timedelta, timezone

import pytest

from database import Database
import phocos_store as store


@pytest.fixture(autouse=True)
def utc_timezone(monkeypatch):
    previous = os.environ.get("TZ")
    monkeypatch.setenv("TZ", "UTC")
    time.tzset()
    yield
    if previous is None:
        os.environ.pop("TZ", None)
    else:
        os.environ["TZ"] = previous
    time.tzset()


@pytest.fixture
def db(tmp_path):
    database = Database(str(tmp_path / "incremental.sqlite"))
    store.ensure_schema(database)
    yield database
    database.close()


def record(db, recorded_at, *, quality=None, pv=900.0):
    store.record_snapshot(
        db, {"recorded_at": recorded_at.isoformat(), "pv_power_w": pv,
             "ac_output_active_power_w": 600.0, "battery_charge_power_w": 100.0,
             "battery_discharge_power_w": 50.0, "solar_feed_to_grid_power_w": 20.0},
        {}, [], max_gap_seconds=180, persist_raw_frames=False,
        pricing={"grid_price_eur_per_kwh": 0.3, "feed_in_revenue_eur_per_kwh": 0.1},
        refresh_rollups=False, run_compaction=False,
    )
    if quality is not None:
        db.execute("UPDATE derived_energy_intervals SET quality = ? WHERE recorded_at = ?",
                   [quality, recorded_at.isoformat()])


def rollups(db):
    result = {}
    for table, key in (("energy_summary_days", "local_day"),
                       ("energy_summary_months", "local_month"),
                       ("energy_summary_years", "local_year"),
                       ("energy_quality_summary_days", "local_day, quality")):
        result[table] = [{k: v for k, v in dict(row).items() if k != "updated_at"}
                         for row in db.execute(f"SELECT * FROM {table} ORDER BY {key}")]
    return result


def assert_matches_full_rebuild(db, reference_time):
    before = rollups(db)
    oracle = Database(":memory:")
    try:
        db.connection.backup(oracle.connection)
        store.rebuild_energy_rollups(oracle, reference_time=reference_time)
        expected = rollups(oracle)
        for table in expected:
            assert len(before[table]) == len(expected[table])
            for actual, wanted in zip(before[table], expected[table]):
                assert actual.keys() == wanted.keys()
                for key, value in wanted.items():
                    if isinstance(value, (int, float)):
                        assert actual[key] == pytest.approx(value, abs=1e-10), (table, key)
                    else:
                        assert actual[key] == value, (table, key)
    finally:
        oracle.close()


def cursor(db, day):
    row = db.fetchone("SELECT value FROM summary_rollup_state WHERE key = ?",
                      [store.INCREMENTAL_ROLLUP_STATE_PREFIX + day])
    return json.loads(row["value"]) if row else None


def test_append_gap_quality_and_repeated_refresh_match_full_rebuild(db):
    start = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)
    for offset, quality in ((0, "initial"), (1, "exact"), (2, "derived")):
        record(db, start + timedelta(seconds=offset), quality=quality)
    store.refresh_current_summary_rollups(db, start + timedelta(seconds=2))

    for offset, quality in ((3, "cached"), (4, "exact"), (400, "gap_dropped")):
        record(db, start + timedelta(seconds=offset), quality=quality, pv=1200.0)
    end = start + timedelta(seconds=400)
    store.refresh_current_summary_rollups(db, end)
    assert cursor(db, "2026-11-18")["interval_count"] == 6
    assert_matches_full_rebuild(db, end)
    before = rollups(db)
    store.refresh_current_summary_rollups(db, end)
    assert rollups(db) == before


def test_incremental_query_is_timestamp_bounded_using_existing_index(db):
    start = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)
    for offset in range(300):
        record(db, start + timedelta(seconds=offset))
    store.refresh_current_summary_rollups(db, start + timedelta(seconds=299))
    for offset in range(300, 303):
        record(db, start + timedelta(seconds=offset))
    statements = []
    db.connection.set_trace_callback(statements.append)
    store.refresh_current_summary_rollups(db, start + timedelta(seconds=302))
    db.connection.set_trace_callback(None)

    aggregates = [q for q in statements if "FROM derived_energy_intervals" in q]
    assert len(aggregates) == 1
    query = aggregates[0]
    plan = [row["detail"] for row in db.execute("EXPLAIN QUERY PLAN " + query)]
    assert any("idx_energy_recorded_quality (recorded_at>? AND recorded_at<?)" in step
               for step in plan), plan
    assert "2026-11-18T12:04:59+00:00" in query
    assert_matches_full_rebuild(db, start + timedelta(seconds=302))


def test_restart_reuses_persistent_cursor_and_incoherent_quality_falls_back(db, tmp_path):
    start = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)
    record(db, start)
    record(db, start + timedelta(seconds=1))
    store.refresh_current_summary_rollups(db, start + timedelta(seconds=1))
    db.close()
    db.open(tmp_path / "incremental.sqlite")
    record(db, start + timedelta(seconds=2))
    store.refresh_current_summary_rollups(db, start + timedelta(seconds=2))
    assert_matches_full_rebuild(db, start + timedelta(seconds=2))

    db.execute("DELETE FROM energy_quality_summary_days WHERE local_day = ?", ["2026-11-18"])
    record(db, start + timedelta(seconds=3))
    store.refresh_current_summary_rollups(db, start + timedelta(seconds=3))
    assert cursor(db, "2026-11-18")["interval_count"] == 4
    assert_matches_full_rebuild(db, start + timedelta(seconds=3))


def test_upsert_of_processed_interval_invalidates_cursor_even_without_full_refresh(db):
    start = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)
    record(db, start)
    record(db, start + timedelta(seconds=1))
    store.refresh_current_summary_rollups(db, start + timedelta(seconds=1))

    corrected = dict(db.fetchone("SELECT * FROM derived_energy_intervals WHERE recorded_at = ?",
                                 [(start + timedelta(seconds=1)).isoformat()]))
    corrected.update(pv_energy_kwh=0.25, quality="exact")
    store.insert_energy_delta(db, corrected)
    assert cursor(db, "2026-11-18")["dirty"]
    record(db, start + timedelta(seconds=2))
    store.refresh_current_summary_rollups(db, start + timedelta(seconds=2))
    assert_matches_full_rebuild(db, start + timedelta(seconds=2))

    # A clock rollback/retry also arrives through refresh_rollups=False.
    record(db, start, pv=2000.0)
    assert cursor(db, "2026-11-18")["dirty"]
    store.refresh_current_summary_rollups(db, start + timedelta(seconds=3))
    assert_matches_full_rebuild(db, start + timedelta(seconds=3))


def test_rollover_finishes_previous_day_tail_and_finalizes_it(db):
    start = datetime(2026, 12, 31, 23, 59, 57, tzinfo=timezone.utc)
    record(db, start)
    store.refresh_current_summary_rollups(db, start)
    for offset in range(1, 5):
        record(db, start + timedelta(seconds=offset))
    end = start + timedelta(seconds=4)
    store.refresh_current_summary_rollups(db, end)

    assert cursor(db, "2026-12-31")["finalized"] == 1
    assert cursor(db, "2026-12-31")["interval_count"] == 3
    assert cursor(db, "2027-01-01")["interval_count"] == 2
    assert_matches_full_rebuild(db, end)


@pytest.mark.parametrize("legacy_without_cursor", [False, True])
def test_rollover_recovers_unfinished_day_without_persistent_cursor(db, legacy_without_cursor):
    start = datetime(2026, 12, 31, 23, 59, 57, tzinfo=timezone.utc)
    record(db, start)
    if legacy_without_cursor:
        store.refresh_current_summary_rollups(db, start)
        record(db, start + timedelta(seconds=1))
        db.execute("DELETE FROM summary_rollup_state WHERE key >= ? AND key < ?",
                   [store.INCREMENTAL_ROLLUP_STATE_PREFIX,
                    store.INCREMENTAL_ROLLUP_STATE_PREFIX + "\uffff"])
    else:
        # Explicit full refresh clears the cursor once its work is complete.
        store._refresh_day_summary(db, "2026-12-31", reference_time=start)
    end = datetime(2027, 1, 1, tzinfo=timezone.utc)
    record(db, end)
    store.refresh_current_summary_rollups(db, end)
    assert cursor(db, "2026-12-31")["finalized"] == 1
    assert_matches_full_rebuild(db, end)


def test_repricing_complete_old_days_does_not_queue_full_rebuilds(db):
    start = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
    for day in range(5):
        record(db, start + timedelta(days=day))
    reference = start + timedelta(days=6)
    store.refresh_current_summary_rollups(db, reference)
    for day in range(5):
        store.invalidate_day_rollup_cursor(db, (start + timedelta(days=day)).date().isoformat())
    pending = db.execute("SELECT value FROM summary_rollup_state WHERE key >= ? AND key < ?",
                         [store.INCREMENTAL_ROLLUP_STATE_PREFIX,
                          store.INCREMENTAL_ROLLUP_STATE_PREFIX + "\uffff"])
    assert pending == []


def test_repricing_keeps_already_pending_late_correction_queued(db):
    start = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
    record(db, start)
    store.refresh_current_summary_rollups(db, start + timedelta(days=1))
    record(db, start + timedelta(seconds=1))
    assert cursor(db, "2026-11-01")["dirty"]
    store.invalidate_day_rollup_cursor(db, "2026-11-01")
    assert cursor(db, "2026-11-01")["dirty"]
    recent = start + timedelta(days=2)
    record(db, recent)
    store.refresh_current_summary_rollups(db, recent)
    assert_matches_full_rebuild(db, recent)


def test_dst_fall_back_keeps_both_local_two_oclock_hours(db, monkeypatch):
    monkeypatch.setenv("TZ", "Europe/Paris")
    time.tzset()
    first = datetime(2026, 10, 25, 0, 30, tzinfo=timezone.utc)
    record(db, first)
    store.refresh_current_summary_rollups(db, first)
    # Both UTC instants belong to local 02:30, on opposite sides of DST.
    second = first + timedelta(hours=1)
    record(db, second)
    store.refresh_current_summary_rollups(db, second)
    assert cursor(db, "2026-10-25")["interval_count"] == 2
    assert_matches_full_rebuild(db, second)


def test_day_quality_and_cursor_updates_roll_back_together(db, monkeypatch):
    start = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)
    record(db, start)
    store.refresh_current_summary_rollups(db, start)
    old_rollups, old_cursor = rollups(db), cursor(db, "2026-11-18")
    record(db, start + timedelta(seconds=1))
    original = store._set_rollup_state

    def fail_after_cursor_write(database, key, value):
        original(database, key, value)
        if key.startswith(store.INCREMENTAL_ROLLUP_STATE_PREFIX):
            raise RuntimeError("simulated cursor write failure")

    monkeypatch.setattr(store, "_set_rollup_state", fail_after_cursor_write)
    with pytest.raises(RuntimeError, match="simulated"):
        store.refresh_current_summary_rollups(db, start + timedelta(seconds=1))
    assert rollups(db) == old_rollups
    assert cursor(db, "2026-11-18") == old_cursor


def test_dirty_finalized_day_keeps_durable_totals_after_detailed_pruning(db):
    old = datetime(2026, 9, 1, 12, tzinfo=timezone.utc)
    record(db, old)
    record(db, old + timedelta(seconds=1))
    store.refresh_current_summary_rollups(db, old + timedelta(days=1))
    archived = rollups(db)["energy_summary_days"][0]
    db.execute("DELETE FROM derived_energy_intervals WHERE local_day = ?", ["2026-09-01"])
    store.invalidate_day_rollup_cursor(db, "2026-09-01")
    recent = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)
    record(db, recent)
    store.refresh_current_summary_rollups(db, recent)
    assert rollups(db)["energy_summary_days"][0] == archived


@pytest.mark.parametrize("retained_intervals", [0, 1])
def test_legacy_unfinished_day_keeps_durable_totals_when_details_are_missing(db, retained_intervals):
    old = datetime(2026, 9, 1, 12, tzinfo=timezone.utc)
    record(db, old)
    record(db, old + timedelta(seconds=1))
    store.refresh_current_summary_rollups(db, old + timedelta(seconds=1))
    archived = rollups(db)["energy_summary_days"][0]
    assert archived["finalized"] == 0
    db.execute("DELETE FROM summary_rollup_state WHERE key >= ? AND key < ?",
               [store.INCREMENTAL_ROLLUP_STATE_PREFIX,
                store.INCREMENTAL_ROLLUP_STATE_PREFIX + "\uffff"])
    db.execute("DELETE FROM derived_energy_intervals WHERE recorded_at >= ?",
               [(old + timedelta(seconds=retained_intervals)).isoformat()])

    recent = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)
    record(db, recent)
    store.refresh_current_summary_rollups(db, recent)
    archived["finalized"] = 1
    assert rollups(db)["energy_summary_days"][0] == archived


def test_cursor_tracks_intervals_even_when_curve_bounds_have_been_compacted(db):
    start = datetime(2026, 11, 18, 12, 0, 20, tzinfo=timezone.utc)
    for offset in (0, 5, 10):
        record(db, start + timedelta(seconds=offset))
    reference = start + timedelta(hours=1)
    store.compact_historical_samples(db, reference_time=reference, retention_hours=0)
    store.refresh_current_summary_rollups(db, reference)
    summary = db.fetchone("SELECT * FROM energy_summary_days WHERE local_day = ?", ["2026-11-18"])
    watermark = cursor(db, "2026-11-18")["recorded_at"]
    assert watermark == (start + timedelta(seconds=10)).isoformat()
    assert watermark != summary["last_recorded_at"]
    record(db, reference)
    store.refresh_current_summary_rollups(db, reference)
    assert_matches_full_rebuild(db, reference)
