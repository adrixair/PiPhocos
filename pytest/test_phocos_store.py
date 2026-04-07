from datetime import datetime, timedelta, timezone

from database import Database
from phocos_store import (
    calculate_energy_deltas,
    compact_historical_samples,
    ensure_schema,
    get_bucket_totals,
    get_current_snapshot,
    get_grouped_cumulative,
    get_history_series,
    record_snapshot,
    rebuild_energy_rollups,
)


def _sample(recorded_at, pv_power_w, output_w, charge_w=0.0, discharge_w=0.0):
    return {
        "recorded_at": recorded_at,
        "serial_number": "TEST-SERIAL-0001",
        "protocol_id": "PI30",
        "device_id": "TEST-DEVICE-0001",
        "operation_mode_code": "L",
        "operation_mode": "Grid / Line mode",
        "fault_code": "00",
        "fault": "No fault",
        "ac_input_voltage_v": 234.0,
        "ac_input_frequency_hz": 50.0,
        "ac_output_voltage_v": 234.0,
        "ac_output_frequency_hz": 50.0,
        "ac_output_apparent_power_va": output_w,
        "ac_output_active_power_w": output_w,
        "ac_output_load_percent": 5,
        "battery_voltage_v": 55.0,
        "battery_charge_current_a": 0,
        "battery_state_of_charge_percent": 100,
        "pv_input_voltage_v": 280.0,
        "total_charging_current_a": 0,
        "total_ac_output_apparent_power_va": output_w,
        "total_output_active_power_w": output_w,
        "total_output_load_percent": 5,
        "ac_output_mode_code": "0",
        "ac_output_mode": "Single Any-Grid unit",
        "battery_charger_source_priority_code": "3",
        "battery_charger_source_priority": "Solar only",
        "max_charging_current_set_a": 80,
        "max_charging_current_possible_a": 80,
        "max_ac_charging_current_set_a": 60,
        "pv_input_current_a": 1.5,
        "battery_discharge_current_a": 0,
        "pv_power_w": pv_power_w,
        "pv_power_semantics": "derived",
        "battery_charge_power_w": charge_w,
        "battery_discharge_power_w": discharge_w,
        "inverter_status": {
            "raw": "11100010",
            "mppt_active": True,
            "ac_charging_on": True,
            "solar_charging_on": True,
            "battery_state_code": "00",
            "battery_state": "Battery voltage normal",
            "ac_input_available": True,
            "ac_output_on": True,
        },
        "metadata": {"serial_port": "/dev/test", "unit": 0},
    }


def test_energy_delta_breaks_on_large_gap():
    first = {
        "recorded_at": "2026-04-04T10:00:00+00:00",
        "local_day": "2026-04-04",
        "local_month": "2026-04",
        "local_year": "2026",
        "pv_power_w": 500.0,
        "ac_output_active_power_w": 300.0,
        "battery_charge_power_w": 0.0,
        "battery_discharge_power_w": 0.0,
        "solar_feed_to_grid_power_w": 0.0,
    }
    second = {
        "recorded_at": "2026-04-04T10:10:00+00:00",
        "local_day": "2026-04-04",
        "local_month": "2026-04",
        "local_year": "2026",
        "pv_power_w": 500.0,
        "ac_output_active_power_w": 300.0,
        "battery_charge_power_w": 0.0,
        "battery_discharge_power_w": 0.0,
        "solar_feed_to_grid_power_w": 0.0,
    }
    delta = calculate_energy_deltas(first, second, max_gap_seconds=180)
    assert delta["contiguous"] == 0
    assert delta["pv_energy_kwh"] == 0.0
    assert delta["load_energy_kwh"] == 0.0


def test_record_snapshot_builds_current_and_history(tmp_path):
    db = Database(str(tmp_path / "phocos.sqlite"))
    ensure_schema(db)
    end = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    start = end - timedelta(minutes=1)

    record_snapshot(
        db,
        _sample(start.isoformat(), 400.0, 250.0),
        {"QPGS0": {"supported": True, "checked_at": start.isoformat(), "crc_ok": True}},
        [],
        max_gap_seconds=180,
        persist_raw_frames=False,
    )
    record_snapshot(
        db,
        _sample(end.isoformat(), 500.0, 300.0),
        {"QPGS0": {"supported": True, "checked_at": end.isoformat(), "crc_ok": True}},
        [],
        max_gap_seconds=180,
        persist_raw_frames=False,
    )

    current = get_current_snapshot(db)
    assert current is not None
    assert current["snapshot"]["ac_output_active_power_w"] == 300.0
    assert current["cumulative"]["all_time"]["pv_energy_kwh"] > 0.0

    history = get_history_series(db, "pv_power_w", 24)
    assert len(history["series"]) >= 1
    assert history["series"][-1]["value"] == 500.0

    grouped = get_grouped_cumulative(db, "day", 7)
    assert grouped["items"][-1]["pv_energy_kwh"] > 0.0


def test_get_current_snapshot_reuses_stored_cumulative_totals(tmp_path):
    db = Database(str(tmp_path / "phocos_current_snapshot_cache.sqlite"))
    ensure_schema(db)
    end = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    start = end - timedelta(minutes=1)

    record_snapshot(
        db,
        _sample(start.isoformat(), 400.0, 250.0),
        {"QPGS0": {"supported": True, "checked_at": start.isoformat(), "crc_ok": True}},
        [],
        max_gap_seconds=180,
        persist_raw_frames=False,
    )
    record_snapshot(
        db,
        _sample(end.isoformat(), 500.0, 300.0),
        {"QPGS0": {"supported": True, "checked_at": end.isoformat(), "crc_ok": True}},
        [],
        max_gap_seconds=180,
        persist_raw_frames=False,
    )

    cached_before = get_current_snapshot(db)
    assert cached_before is not None
    assert cached_before["cumulative"]["all_time"]["pv_energy_kwh"] > 0.0

    db.execute("DELETE FROM derived_energy_intervals")

    cached_after = get_current_snapshot(db)
    assert cached_after is not None
    assert cached_after["cumulative"]["all_time"]["pv_energy_kwh"] == cached_before["cumulative"]["all_time"]["pv_energy_kwh"]


def test_materialized_rollups_survive_interval_table_cleanup(tmp_path):
    db = Database(str(tmp_path / "phocos_rollups.sqlite"))
    ensure_schema(db)

    for recorded_at, pv_power_w, output_w in (
        ("2026-04-04T10:00:00+00:00", 400.0, 250.0),
        ("2026-04-04T10:01:00+00:00", 500.0, 300.0),
        ("2026-04-05T10:00:00+00:00", 600.0, 350.0),
        ("2026-04-05T10:01:00+00:00", 700.0, 400.0),
    ):
        record_snapshot(
            db,
            _sample(recorded_at, pv_power_w, output_w),
            {"QPGS0": {"supported": True, "checked_at": recorded_at, "crc_ok": True}},
            [],
            max_gap_seconds=180,
            persist_raw_frames=False,
        )

    before = get_bucket_totals(db, "all_time")
    assert before["pv_energy_kwh"] > 0.0

    db.execute("DELETE FROM derived_energy_intervals")

    after = get_bucket_totals(db, "all_time")
    assert after["pv_energy_kwh"] == before["pv_energy_kwh"]
    assert after["load_energy_kwh"] == before["load_energy_kwh"]


def test_energy_summary_tables_are_without_rowid(tmp_path):
    db = Database(str(tmp_path / "phocos_rollup_schema.sqlite"))
    ensure_schema(db)

    tables = {
        row["name"]: row["sql"]
        for row in db.execute(
            """
            SELECT name, sql
            FROM sqlite_master
            WHERE type = 'table' AND name LIKE 'energy_summary_%'
            """
        )
    }

    assert "WITHOUT ROWID" in tables["energy_summary_days"]
    assert "WITHOUT ROWID" in tables["energy_summary_months"]
    assert "WITHOUT ROWID" in tables["energy_summary_years"]


def test_get_history_series_caps_payload_to_requested_max_points(tmp_path):
    db = Database(str(tmp_path / "phocos_history_cap.sqlite"))
    ensure_schema(db)

    start = datetime.now(timezone.utc).replace(second=0, microsecond=0) - timedelta(minutes=239)
    for offset in range(240):
        recorded_at = start + timedelta(minutes=offset)
        record_snapshot(
            db,
            _sample(recorded_at.isoformat(), 100.0 + offset, 50.0 + offset),
            {
                "QPGS0": {
                    "supported": True,
                    "checked_at": recorded_at.isoformat(),
                    "crc_ok": True,
                }
            },
            [],
            max_gap_seconds=180,
            persist_raw_frames=False,
        )

    history = get_history_series(db, "pv_power_w", 24, max_points=40)

    assert len(history["series"]) <= 40
    assert history["series"][-1]["recorded_at"] == (start + timedelta(minutes=239)).isoformat()


def test_compaction_archives_old_samples_into_ten_minute_averages(tmp_path):
    db = Database(str(tmp_path / "phocos_compaction.sqlite"))
    ensure_schema(db)

    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    old_bucket_start = now - timedelta(hours=26, minutes=now.minute % 10)
    recent_sample_at = now - timedelta(hours=1)

    for offset_seconds, pv_power_w, output_w in (
        (0, 300.0, 150.0),
        (20, 600.0, 180.0),
        (9 * 60 + 40, 900.0, 210.0),
    ):
        record_snapshot(
            db,
            _sample(
                (old_bucket_start + timedelta(seconds=offset_seconds)).isoformat(),
                pv_power_w,
                output_w,
            ),
            {
                "QPGS0": {
                    "supported": True,
                    "checked_at": (old_bucket_start + timedelta(seconds=offset_seconds)).isoformat(),
                    "crc_ok": True,
                }
            },
            [],
            max_gap_seconds=180,
            persist_raw_frames=False,
        )

    record_snapshot(
        db,
        _sample(recent_sample_at.isoformat(), 750.0, 330.0),
        {
            "QPGS0": {
                "supported": True,
                "checked_at": recent_sample_at.isoformat(),
                "crc_ok": True,
            }
        },
        [],
        max_gap_seconds=180,
        persist_raw_frames=False,
    )

    compact_historical_samples(db, reference_time=now)

    archived_bucket_local = old_bucket_start.astimezone().strftime("%Y-%m-%dT%H:%M")
    archived = db.fetchone(
        "SELECT * FROM compressed_samples_10m WHERE bucket_local = ?",
        [archived_bucket_local],
    )
    assert archived is not None
    assert abs(archived["pv_power_w"] - 600.0) < 1e-9
    assert abs(archived["ac_output_active_power_w"] - 180.0) < 1e-9
    assert archived["sample_count"] == 3

    old_raw = db.fetchone(
        "SELECT COUNT(*) AS count FROM samples WHERE local_day = ?",
        [old_bucket_start.astimezone().strftime("%Y-%m-%d")],
    )
    assert old_raw["count"] == 0

    history = get_history_series(db, "pv_power_w", 30)
    assert len(history["series"]) == 2
    assert abs(history["series"][0]["value"] - 600.0) < 1e-9
    assert abs(history["series"][1]["value"] - 750.0) < 1e-9


def test_minute_history_compacts_automatically_on_next_snapshot(tmp_path):
    db = Database(str(tmp_path / "phocos_minute_history.sqlite"))
    ensure_schema(db)

    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    old_bucket_start = now - timedelta(days=3, minutes=now.minute % 10)
    old_day = old_bucket_start.astimezone().strftime("%Y-%m-%d")

    for minute_offset in range(10):
        recorded_at = old_bucket_start + timedelta(minutes=minute_offset)
        record_snapshot(
            db,
            _sample(
                recorded_at.isoformat(),
                100.0 * (minute_offset + 1),
                20.0 * (minute_offset + 1),
            ),
            {
                "QPGS0": {
                    "supported": True,
                    "checked_at": recorded_at.isoformat(),
                    "crc_ok": True,
                }
            },
            [],
            max_gap_seconds=180,
            persist_raw_frames=False,
        )

    assert db.fetchone(
        "SELECT COUNT(*) AS count FROM samples WHERE local_day = ?",
        [old_day],
    )["count"] == 10
    assert db.fetchone(
        "SELECT COUNT(*) AS count FROM minute_samples WHERE local_day = ?",
        [old_day],
    )["count"] == 10

    recent_sample_at = now - timedelta(minutes=5)
    record_snapshot(
        db,
        _sample(recent_sample_at.isoformat(), 777.0, 333.0),
        {
            "QPGS0": {
                "supported": True,
                "checked_at": recent_sample_at.isoformat(),
                "crc_ok": True,
            }
        },
        [],
        max_gap_seconds=180,
        persist_raw_frames=False,
    )

    archived = db.fetchone(
        "SELECT * FROM compressed_samples_10m WHERE bucket_local = ?",
        [old_bucket_start.astimezone().strftime("%Y-%m-%dT%H:%M")],
    )
    assert archived is not None
    assert archived["sample_count"] == 10
    assert abs(archived["pv_power_w"] - 550.0) < 1e-9
    assert abs(archived["ac_output_active_power_w"] - 110.0) < 1e-9

    assert db.fetchone(
        "SELECT COUNT(*) AS count FROM samples WHERE local_day = ?",
        [old_day],
    )["count"] == 0
    assert db.fetchone(
        "SELECT COUNT(*) AS count FROM minute_samples WHERE local_day = ?",
        [old_day],
    )["count"] == 0

    history = get_history_series(db, "pv_power_w", 120)
    assert len(history["series"]) == 2
    assert abs(history["series"][0]["value"] - 550.0) < 1e-9
    assert abs(history["series"][1]["value"] - 777.0) < 1e-9


def test_compaction_finalizes_previous_local_day_after_midnight(tmp_path):
    db = Database(str(tmp_path / "phocos_midnight_compaction.sqlite"))
    ensure_schema(db)

    reference_time = datetime(2026, 4, 7, 22, 10, tzinfo=timezone.utc)
    previous_bucket_start = datetime(2026, 4, 7, 21, 50, tzinfo=timezone.utc)
    previous_local_day = previous_bucket_start.astimezone().strftime("%Y-%m-%d")

    for offset_seconds, pv_power_w, output_w in (
        (0, 300.0, 150.0),
        (20, 600.0, 180.0),
        (9 * 60 + 40, 900.0, 210.0),
    ):
        recorded_at = previous_bucket_start + timedelta(seconds=offset_seconds)
        record_snapshot(
            db,
            _sample(recorded_at.isoformat(), pv_power_w, output_w),
            {
                "QPGS0": {
                    "supported": True,
                    "checked_at": recorded_at.isoformat(),
                    "crc_ok": True,
                }
            },
            [],
            max_gap_seconds=180,
            persist_raw_frames=False,
        )

    compact_historical_samples(db, reference_time=reference_time)

    archived_bucket_local = previous_bucket_start.astimezone().strftime("%Y-%m-%dT%H:%M")
    archived = db.fetchone(
        "SELECT * FROM compressed_samples_10m WHERE bucket_local = ?",
        [archived_bucket_local],
    )
    assert archived is not None
    assert archived["sample_count"] == 3
    assert abs(archived["pv_power_w"] - 600.0) < 1e-9
    assert abs(archived["ac_output_active_power_w"] - 180.0) < 1e-9

    assert db.fetchone(
        "SELECT COUNT(*) AS count FROM samples WHERE local_day = ?",
        [previous_local_day],
    )["count"] == 0
    assert db.fetchone(
        "SELECT COUNT(*) AS count FROM minute_samples WHERE local_day = ?",
        [previous_local_day],
    )["count"] == 0


def test_get_current_snapshot_can_skip_heavy_sections(tmp_path):
    db = Database(str(tmp_path / "phocos_light_current.sqlite"))
    ensure_schema(db)
    recorded_at = "2026-04-05T12:00:00+00:00"

    record_snapshot(
        db,
        _sample(recorded_at, 600.0, 250.0),
        {"QPGS0": {"supported": True, "checked_at": recorded_at, "crc_ok": True}},
        [],
        max_gap_seconds=180,
        persist_raw_frames=False,
    )

    current = get_current_snapshot(
        db,
        include_cumulative=False,
        include_capabilities=False,
    )
    assert current is not None
    assert current["recorded_at"] == recorded_at
    assert "cumulative" not in current
    assert "capabilities" not in current
