from datetime import datetime, timezone

from database import Database
from phocos_store import ensure_schema, record_snapshot
from scripts.rebuild_quality_summaries import rebuild


def _sample(recorded_at):
    return {
        "recorded_at": recorded_at,
        "pv_power_w": 500.0,
        "pv_power_semantics": "exact",
        "ac_output_active_power_w": 250.0,
        "battery_charge_power_w": 0.0,
        "battery_discharge_power_w": 0.0,
        "solar_feed_to_grid_power_w": 0.0,
        "inverter_status": {},
    }


def test_rebuild_quality_summaries_script_refreshes_range(tmp_path):
    db_path = tmp_path / "quality.sqlite"
    db = Database(str(db_path))
    ensure_schema(db)

    for recorded_at in (
        datetime(2026, 4, 5, 12, 0, tzinfo=timezone.utc).isoformat(),
        datetime(2026, 4, 5, 12, 0, 1, tzinfo=timezone.utc).isoformat(),
    ):
        record_snapshot(
            db,
            _sample(recorded_at),
            {},
            [],
            max_gap_seconds=180,
            persist_raw_frames=False,
        )

    db.execute("DELETE FROM energy_quality_summary_days")
    db.close()

    report = rebuild(db_path, "2026-04-05", "2026-04-06")

    db = Database(str(db_path))
    try:
        row = db.fetchone("SELECT COUNT(*) AS count FROM energy_quality_summary_days")
        assert row["count"] > 0
    finally:
        db.close()
    assert report["refreshed_days"] == 1
    assert report["limited"] is False
