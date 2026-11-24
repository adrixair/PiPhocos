from datetime import datetime, timedelta, timezone

from database import Database
from phocos_store import ensure_schema, record_snapshot, refresh_current_summary_rollups
from scripts.reprice_energy_history import _update_detailed_intervals, reprice


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


def test_reprice_energy_history_updates_euros_without_changing_kwh(tmp_path):
    db_path = tmp_path / "reprice.sqlite"
    config_path = tmp_path / "config.yml"
    config_path.write_text(
        """
time_zone: Europe/Paris
prices:
  tariff: standard
  revenue_per_fed_in_kwh: 0.05
  standard:
    base_ttc_per_kwh: 0.1927
""".strip(),
        encoding="utf-8",
    )

    db = Database(str(db_path))
    ensure_schema(db)
    start = datetime(2026, 4, 7, 10, 0, tzinfo=timezone.utc)
    pricing = {
        "grid_price_eur_per_kwh": 0.3,
        "feed_in_revenue_eur_per_kwh": 0.1,
    }
    for recorded_at in (start, start + timedelta(hours=1)):
        record_snapshot(
            db,
            _sample(recorded_at.isoformat()),
            {},
            [],
            max_gap_seconds=7200,
            persist_raw_frames=False,
            pricing=pricing,
        )

    before = db.fetchone(
        """
        SELECT pv_to_load_energy_kwh, earned_savings_eur
        FROM energy_summary_days
        WHERE local_day = '2026-04-07'
        """
    )
    db.close()

    dry_run = reprice(db_path, config_path)
    assert dry_run["applied"] is False
    assert dry_run["days"] == 1

    report = reprice(db_path, config_path, apply=True)
    assert report["applied"] is True
    assert report["days"] == 1

    db = Database(str(db_path))
    try:
        after = db.fetchone(
            """
            SELECT pv_to_load_energy_kwh, earned_savings_eur
            FROM energy_summary_days
            WHERE local_day = '2026-04-07'
            """
        )
        interval = db.fetchone(
            """
            SELECT grid_price_eur_per_kwh
            FROM derived_energy_intervals
            WHERE local_day = '2026-04-07'
              AND previous_recorded_at IS NOT NULL
            """
        )
    finally:
        db.close()

    assert after["pv_to_load_energy_kwh"] == before["pv_to_load_energy_kwh"]
    assert after["earned_savings_eur"] < before["earned_savings_eur"]
    assert abs(
        after["earned_savings_eur"]
        - after["pv_to_load_energy_kwh"] * 0.1927
    ) < 1e-9
    assert interval["grid_price_eur_per_kwh"] == 0.1927


def test_repricing_detailed_intervals_invalidates_incremental_totals(tmp_path):
    db = Database(str(tmp_path / "reprice-incremental.sqlite"))
    try:
        ensure_schema(db)
        start = datetime(2026, 4, 7, 10, 0, tzinfo=timezone.utc)
        for offset in (0, 1):
            recorded_at = start + timedelta(hours=offset)
            record_snapshot(
                db, _sample(recorded_at.isoformat()), {}, [],
                max_gap_seconds=7200, persist_raw_frames=False,
                pricing={"grid_price_eur_per_kwh": 0.3, "feed_in_revenue_eur_per_kwh": 0.1},
                refresh_rollups=False, run_compaction=False,
            )
        refresh_current_summary_rollups(db, reference_time=start + timedelta(hours=1))
        with db.transaction():
            _update_detailed_intervals(db, "2026-04-07", 0.1927, 0.05)
        record_snapshot(
            db, _sample((start + timedelta(hours=2)).isoformat()), {}, [],
            max_gap_seconds=7200, persist_raw_frames=False,
            pricing={"grid_price_eur_per_kwh": 0.1927, "feed_in_revenue_eur_per_kwh": 0.05},
            refresh_rollups=False, run_compaction=False,
        )
        refresh_current_summary_rollups(db, reference_time=start + timedelta(hours=2))
        row = db.fetchone(
            "SELECT earned_savings_eur, pv_to_load_energy_kwh, "
            "battery_to_load_energy_kwh FROM energy_summary_days WHERE local_day = ?",
            ["2026-04-07"],
        )
        expected = (row["pv_to_load_energy_kwh"] + row["battery_to_load_energy_kwh"]) * 0.1927
        assert abs(row["earned_savings_eur"] - expected) < 1e-9
    finally:
        db.close()
