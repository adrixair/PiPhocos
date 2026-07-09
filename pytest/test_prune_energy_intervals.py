from datetime import datetime, timedelta, timezone

from database import Database
from phocos_store import ensure_schema, record_snapshot
from scripts.prune_energy_intervals import prune


def _sample(recorded_at):
    return {
        "recorded_at": recorded_at,
        "pv_power_w": 500.0,
        "pv_power_semantics": "exact",
        "ac_output_active_power_w": 3600.0,
        "battery_charge_power_w": 0.0,
        "battery_discharge_power_w": 0.0,
        "solar_feed_to_grid_power_w": 0.0,
        "inverter_status": {},
    }


def test_prune_energy_intervals_script_requires_apply(tmp_path):
    report = prune(
        tmp_path / "missing.sqlite",
        retention_days=45,
        max_days=14,
        apply=False,
    )

    assert report["applied"] is False


def test_prune_energy_intervals_script_prunes_ready_days(tmp_path):
    db_path = tmp_path / "prune.sqlite"
    db = Database(str(db_path))
    ensure_schema(db)
    start = datetime.now(timezone.utc) - timedelta(days=60)
    for offset in (0, 1):
        recorded_at = (start + timedelta(seconds=offset)).isoformat()
        record_snapshot(
            db,
            _sample(recorded_at),
            {},
            [],
            max_gap_seconds=180,
            persist_raw_frames=False,
            expected_interval_seconds=1,
            max_integrated_gap_seconds=3,
        )
    db.close()

    report = prune(
        db_path,
        retention_days=45,
        max_days=14,
        apply=True,
    )

    assert report["applied"] is True
    assert report["prune"]["pruned_days"] == 1
    assert report["prune"]["pruned_intervals"] > 0
