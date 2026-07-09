from datetime import datetime, timedelta, timezone

from database import Database
from phocos_store import ensure_schema, record_snapshot
from scripts.compression_report import run_report


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


def test_compression_report_runs_readonly_on_sqlite_database(tmp_path):
    db_path = tmp_path / "compression.sqlite"
    db = Database(str(db_path))
    ensure_schema(db)
    start = datetime(2026, 4, 5, 12, 0, tzinfo=timezone.utc)
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

    report = run_report(
        db_path,
        interval_retention_days=45,
        reference_time=datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc),
    )

    assert report["tables"]["derived_energy_intervals"]["count"] == 2
    assert report["energy_interval_retention"]["candidate_days"] == 1
    assert report["energy_interval_retention"]["candidate_intervals"] == 2
