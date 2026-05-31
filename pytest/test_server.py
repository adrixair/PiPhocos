import json
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import server
from database import Database
from phocos_store import (
    compact_historical_samples,
    ensure_schema,
    rebuild_energy_rollups,
    record_snapshot,
)


def _sample(
    recorded_at,
    pv_power_w,
    output_w,
    charge_w=0.0,
    discharge_w=0.0,
    export_w=0.0,
    soc=100.0,
):
    battery_voltage_v = 50.0
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
        "battery_voltage_v": battery_voltage_v,
        "battery_charge_current_a": charge_w / battery_voltage_v,
        "battery_state_of_charge_percent": soc,
        "pv_input_voltage_v": 280.0,
        "total_charging_current_a": charge_w / battery_voltage_v,
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
        "battery_discharge_current_a": discharge_w / battery_voltage_v,
        "pv_power_w": pv_power_w,
        "pv_power_semantics": "derived",
        "battery_charge_power_w": charge_w,
        "battery_discharge_power_w": discharge_w,
        "solar_feed_to_grid_power_w": export_w,
        "inverter_status": {
            "raw": "11100010",
            "mppt_active": pv_power_w > 0,
            "ac_charging_on": charge_w > 0,
            "solar_charging_on": charge_w > 0,
            "battery_state_code": "00",
            "battery_state": "Battery voltage normal",
            "ac_input_available": True,
            "ac_output_on": True,
        },
        "metadata": {"serial_port": "/dev/test", "unit": 0},
    }


def _configure_server_globals():
    server.config = SimpleNamespace(
        config_data={
            "time_zone": "Europe/Paris",
            "prices": {
                "price_per_grid_kwh": 0.3,
                "revenue_per_fed_in_kwh": 0.1,
            },
            "grabber": {
                "interval_s": 2,
                "max_gap_for_cumulative_s": 180,
                "stale_after_s": 11,
            },
            "instance": {"name": "Test"},
            "server": {"public_url": "http://localhost"},
            "diagnostics": {"enabled": False},
            "device": {"start_date": date(2026, 4, 4)},
        }
    )
    server.tempo_client = None


def _pricing():
    return {
        "grid_price_eur_per_kwh": 0.3,
        "feed_in_revenue_eur_per_kwh": 0.1,
        "source": "config",
        "tempo_available": False,
        "tariff_label": None,
        "color_label": None,
        "tomorrow_color_label": None,
        "display": None,
    }


def _recent_timestamps():
    end = datetime.now(timezone.utc).replace(microsecond=0)
    start = end - timedelta(minutes=1)
    return start.isoformat(), end.isoformat()


def test_overview_payload_compact_omits_heavy_sections(tmp_path):
    _configure_server_globals()
    db = Database(str(tmp_path / "overview.sqlite"))
    ensure_schema(db)

    recorded_at = "2026-04-05T12:00:00+00:00"
    record_snapshot(
        db,
        _sample(recorded_at, 800.0, 400.0, export_w=50.0),
        {"QPGS0": {"supported": True, "checked_at": recorded_at, "crc_ok": True}},
        [],
        max_gap_seconds=180,
        persist_raw_frames=False,
        pricing=_pricing(),
    )

    compact = server._overview_payload(compact=True, db=db)
    full = server._overview_payload(compact=False, db=db)

    assert compact["state"] == "ok"
    assert compact["recorded_at"] == recorded_at
    assert "cumulative" not in compact
    assert "capabilities" not in compact
    assert "today_coverage_percent" not in compact
    assert full["cumulative"]["today"]["pv_energy_kwh"] >= 0.0
    assert "capabilities" in full


def test_diagnostics_endpoint_is_disabled_by_default():
    _configure_server_globals()

    response = server.app.test_client().get("/api/diagnostics")

    assert response.status_code == 404
    assert response.get_json()["state"] == "disabled"


def test_diagnostics_endpoint_can_be_enabled(tmp_path, monkeypatch):
    _configure_server_globals()
    server.config.config_data["diagnostics"]["enabled"] = True
    db = Database(str(tmp_path / "diagnostics.sqlite"))
    ensure_schema(db)
    recorded_at = "2026-04-05T12:00:00+00:00"
    record_snapshot(
        db,
        _sample(recorded_at, 800.0, 400.0, export_w=50.0),
        {"QPGS0": {"supported": True, "checked_at": recorded_at, "crc_ok": True}},
        [],
        max_gap_seconds=180,
        persist_raw_frames=False,
        pricing=_pricing(),
    )
    monkeypatch.setattr(server, "_open_db", lambda: db)

    response = server.app.test_client().get("/api/diagnostics")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["state"] == "ok"
    assert payload["device"]["serial_number"] == "TEST-SERIAL-0001"
    assert "raw_snapshot" in payload


def test_csv_filename_sanitizes_query_parameters(tmp_path, monkeypatch):
    _configure_server_globals()
    db = Database(str(tmp_path / "csv_filename.sqlite"))
    ensure_schema(db)
    monkeypatch.setattr(server, "_open_db", lambda: db)

    response = server.app.test_client().get(
        "/api/csv?bucket=day&prefix=2026%0d%0aX-Evil:%201"
    )

    assert response.status_code == 200
    assert "X-Evil" not in response.headers
    assert (
        response.headers["Content-Disposition"]
        == "attachment; filename=phocos_day_2026__X-Evil__1.csv"
    )


def test_period_payload_keeps_battery_charge_out_of_direct_pv_consumption(tmp_path):
    _configure_server_globals()
    db = Database(str(tmp_path / "history.sqlite"))
    ensure_schema(db)

    for recorded_at in ("2026-04-04T10:00:00+00:00", "2026-04-04T10:01:00+00:00"):
        record_snapshot(
            db,
            _sample(recorded_at, 500.0, 500.0, charge_w=500.0),
            {"QPGS0": {"supported": True, "checked_at": recorded_at, "crc_ok": True}},
            [],
            max_gap_seconds=180,
            persist_raw_frames=False,
            pricing=_pricing(),
        )

    payload = server._period_history_payload(db, "day", "2026-04-04")

    assert payload["state"] == "ok"
    assert payload["usage_self_consumed_kwh"] > 0.0
    assert payload["produced_to_battery_kwh"] > 0.0
    assert abs(payload["consumed_from_pv_kwh"]) < 1e-9
    assert abs(payload["consumed_from_grid_kwh"] - payload["consumed_total_kwh"]) < 1e-9
    assert abs(payload["earned_savings"]) < 1e-9


def test_period_payload_counts_battery_discharge_as_savings(tmp_path):
    _configure_server_globals()
    db = Database(str(tmp_path / "battery_earned.sqlite"))
    ensure_schema(db)

    for recorded_at in ("2026-04-04T10:00:00+00:00", "2026-04-04T10:01:00+00:00"):
        record_snapshot(
            db,
            _sample(recorded_at, 0.0, 500.0, discharge_w=500.0),
            {"QPGS0": {"supported": True, "checked_at": recorded_at, "crc_ok": True}},
            [],
            max_gap_seconds=180,
            persist_raw_frames=False,
            pricing=_pricing(),
        )

    payload = server._period_history_payload(db, "day", "2026-04-04")

    assert payload["state"] == "ok"
    assert payload["consumed_from_pv_kwh"] == 0.0
    assert payload["consumed_from_battery_kwh"] > 0.0
    assert payload["earned_savings"] > 0.0


def test_history_payload_from_totals_uses_full_grid_price():
    _configure_server_globals()

    payload = server._history_payload_from_totals(
        {
            "produced": 7.0,
            "consumed": 4.0,
            "fed_in": 0.0,
            "pv_to_load": 2.0,
            "battery_to_load": 1.0,
            "pv_to_battery": 3.0,
            "battery_charge": 3.0,
            "battery_discharge": 1.0,
            "grid_to_load": 1.0,
            "grid_to_battery": 0.0,
            "earned_feed_in_eur": 0.0,
            "earned_savings_eur": (2.0 + 1.0) * 0.3,
        },
        pricing=_pricing(),
    )

    assert payload["produced_to_battery_kwh"] == 3.0
    assert payload["locally_supplied_kwh"] == 3.0
    assert abs(payload["earned_savings"] - 0.9) < 1e-9


def test_live_projection_savings_use_full_grid_price():
    _configure_server_globals()

    projection = server._live_projection_from_flow(
        {
            "produced": 600.0,
            "consumed_total": 500.0,
            "battery_charged": 0.0,
            "battery_discharged": 200.0,
            "consumed_from_pv": 300.0,
            "consumed_from_battery": 200.0,
            "produced_to_battery": 100.0,
            "consumed_from_grid": 0.0,
            "battery_charged_from_grid": 0.0,
            "fed_in": 100.0,
        },
        _pricing(),
        elapsed_seconds=3600.0,
    )

    assert abs(projection["pv_to_load_kwh"] - 0.3) < 1e-9
    assert abs(projection["battery_to_load_kwh"] - 0.2) < 1e-9
    assert abs(projection["earned_savings_eur"] - 0.15) < 1e-9
    assert abs(projection["earned_feed_in_eur"] - 0.01) < 1e-9


def test_statistics_use_first_sample_date_for_start_of_operation(tmp_path, monkeypatch):
    _configure_server_globals()
    db = Database(str(tmp_path / "statistics.sqlite"))
    ensure_schema(db)

    for recorded_at, pv_power_w, output_w in (
        ("2026-04-02T10:00:00+00:00", 400.0, 250.0),
        ("2026-04-03T10:00:00+00:00", 450.0, 300.0),
    ):
        record_snapshot(
            db,
            _sample(recorded_at, pv_power_w, output_w),
            {"QPGS0": {"supported": True, "checked_at": recorded_at, "crc_ok": True}},
            [],
            max_gap_seconds=180,
            persist_raw_frames=False,
        )

    monkeypatch.setattr(
        server,
        "_now_local",
        lambda: datetime(2026, 4, 7, 12, 0, tzinfo=timezone.utc),
    )

    payload = server._statistics_payload(db)

    assert payload["start_of_operation"] == "2026-04-02"
    assert payload["days_of_operation"] == 5


def test_period_payload_uses_ten_minute_archive_for_old_days(tmp_path, monkeypatch):
    _configure_server_globals()
    db = Database(str(tmp_path / "history_archive.sqlite"))
    ensure_schema(db)

    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    old_bucket_start = now - timedelta(hours=26, minutes=now.minute % 10)
    search_day = old_bucket_start.astimezone().strftime("%Y-%m-%d")

    for offset_seconds, pv_power_w, output_w in (
        (0, 300.0, 150.0),
        (20, 600.0, 180.0),
        (9 * 60 + 40, 900.0, 210.0),
    ):
        recorded_at = (old_bucket_start + timedelta(seconds=offset_seconds)).isoformat()
        record_snapshot(
            db,
            _sample(recorded_at, pv_power_w, output_w),
            {"QPGS0": {"supported": True, "checked_at": recorded_at, "crc_ok": True}},
            [],
            max_gap_seconds=180,
            persist_raw_frames=False,
            pricing=_pricing(),
        )

    compact_historical_samples(db, reference_time=now)
    monkeypatch.setattr(server, "_now_local", lambda: now.astimezone())

    payload = server._period_history_payload(db, "day", search_day)
    high_res = json.loads(payload["high_res"])

    assert payload["state"] == "ok"
    assert len(high_res) == 1
    assert abs(high_res[0][1] - 0.6) < 1e-9
    assert abs(high_res[0][2] - 0.18) < 1e-9


def test_period_payload_keeps_recent_one_second_samples_for_current_day(tmp_path, monkeypatch):
    _configure_server_globals()
    db = Database(str(tmp_path / "history_recent_day.sqlite"))
    ensure_schema(db)

    now = datetime(2026, 4, 5, 12, 0, tzinfo=timezone.utc)
    sample_times = [
        now - timedelta(seconds=3),
        now - timedelta(seconds=2),
        now - timedelta(seconds=1),
    ]
    search_day = now.astimezone().strftime("%Y-%m-%d")

    for offset, recorded_at in enumerate(sample_times, start=1):
        recorded_at_iso = recorded_at.isoformat()
        record_snapshot(
            db,
            _sample(recorded_at_iso, 300.0 * offset, 120.0 * offset),
            {"QPGS0": {"supported": True, "checked_at": recorded_at_iso, "crc_ok": True}},
            [],
            max_gap_seconds=180,
            persist_raw_frames=False,
            pricing=_pricing(),
        )

    monkeypatch.setattr(server, "_now_local", lambda: now.astimezone())

    payload = server._period_history_payload(db, "day", search_day)
    high_res = json.loads(payload["high_res"])

    assert payload["state"] == "ok"
    assert len(high_res) == 3
    assert [row[0] for row in high_res] == [
        recorded_at.astimezone().strftime("%H:%M:%S")
        for recorded_at in sample_times
    ]
    assert [row[1] for row in high_res] == [0.3, 0.6, 0.9]


def test_period_payload_exposes_battery_and_grid_curves_for_current_day(tmp_path, monkeypatch):
    _configure_server_globals()
    db = Database(str(tmp_path / "history_day_flows.sqlite"))
    ensure_schema(db)

    now = datetime(2026, 4, 7, 12, 0, tzinfo=timezone.utc)
    search_day = now.astimezone().strftime("%Y-%m-%d")
    recorded_at = now.isoformat()

    record_snapshot(
        db,
        _sample(recorded_at, 200.0, 900.0, discharge_w=500.0),
        {"QPGS0": {"supported": True, "checked_at": recorded_at, "crc_ok": True}},
        [],
        max_gap_seconds=180,
        persist_raw_frames=False,
        pricing=_pricing(),
    )

    monkeypatch.setattr(server, "_now_local", lambda: now.astimezone())

    payload = server._period_history_payload(db, "day", search_day)
    high_res = json.loads(payload["high_res"])

    assert payload["state"] == "ok"
    assert len(high_res) == 1
    assert abs(high_res[0][1] - 0.2) < 1e-9
    assert abs(high_res[0][2] - 0.9) < 1e-9
    assert abs(high_res[0][3] - 0.5) < 1e-9
    assert abs(high_res[0][4] - 0.2) < 1e-9


def test_chart_live_caps_payload_to_two_hundred_points(tmp_path):
    _configure_server_globals()
    db = Database(str(tmp_path / "real_time_cap.sqlite"))
    ensure_schema(db)

    now = datetime.now(timezone.utc).replace(microsecond=0)
    sample_count = 450
    first_recorded_at = now - timedelta(seconds=sample_count - 1)

    for index in range(sample_count):
        recorded_at = (first_recorded_at + timedelta(seconds=index)).isoformat()
        record_snapshot(
            db,
            _sample(recorded_at, 500.0 + index, 300.0 + index),
            {"QPGS0": {"supported": True, "checked_at": recorded_at, "crc_ok": True}},
            [],
            max_gap_seconds=180,
            persist_raw_frames=False,
            pricing=_pricing(),
        )

    payload = server._live_chart_payload(db, 1)

    assert payload["state"] == "ok"
    assert len(payload["series"]) <= 200
    assert payload["series"][0][1] == now.astimezone().strftime("%H:%M:%S")


def test_period_payload_caps_high_res_payload_to_two_hundred_points(tmp_path, monkeypatch):
    _configure_server_globals()
    db = Database(str(tmp_path / "history_cap.sqlite"))
    ensure_schema(db)

    now = datetime(2026, 4, 5, 12, 0, tzinfo=timezone.utc)
    sample_count = 450
    first_recorded_at = now - timedelta(seconds=sample_count - 1)
    search_day = now.astimezone().strftime("%Y-%m-%d")

    for index in range(sample_count):
        recorded_at = first_recorded_at + timedelta(seconds=index)
        recorded_at_iso = recorded_at.isoformat()
        record_snapshot(
            db,
            _sample(recorded_at_iso, 400.0 + index, 200.0 + index),
            {"QPGS0": {"supported": True, "checked_at": recorded_at_iso, "crc_ok": True}},
            [],
            max_gap_seconds=180,
            persist_raw_frames=False,
            pricing=_pricing(),
        )

    monkeypatch.setattr(server, "_now_local", lambda: now.astimezone())

    payload = server._period_history_payload(db, "day", search_day)
    high_res = json.loads(payload["high_res"])

    assert payload["state"] == "ok"
    assert len(high_res) <= 200
    assert high_res[-1][0] == now.astimezone().strftime("%H:%M:%S")


def test_period_payload_preserves_battery_and_grid_curves_after_compaction(tmp_path, monkeypatch):
    _configure_server_globals()
    db = Database(str(tmp_path / "history_archived_day_flows.sqlite"))
    ensure_schema(db)

    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    old_bucket_start = now - timedelta(hours=26, minutes=now.minute % 10)
    search_day = old_bucket_start.astimezone().strftime("%Y-%m-%d")

    for offset_seconds in (0, 20, 40):
        recorded_at = (old_bucket_start + timedelta(seconds=offset_seconds)).isoformat()
        record_snapshot(
            db,
        _sample(recorded_at, 250.0, 950.0, discharge_w=500.0),
            {"QPGS0": {"supported": True, "checked_at": recorded_at, "crc_ok": True}},
            [],
            max_gap_seconds=180,
            persist_raw_frames=False,
            pricing=_pricing(),
        )

    compact_historical_samples(db, reference_time=now)
    monkeypatch.setattr(server, "_now_local", lambda: now.astimezone())

    payload = server._period_history_payload(db, "day", search_day)
    high_res = json.loads(payload["high_res"])

    assert payload["state"] == "ok"
    assert len(high_res) == 1
    assert abs(high_res[0][1] - 0.25) < 1e-9
    assert abs(high_res[0][2] - 0.95) < 1e-9
    assert abs(high_res[0][3] - 0.5) < 1e-9
    assert abs(high_res[0][4] - 0.2) < 1e-9


def test_period_payload_formats_labels_in_configured_time_zone(tmp_path):
    _configure_server_globals()
    db = Database(str(tmp_path / "history_timezone.sqlite"))
    ensure_schema(db)

    for recorded_at, pv_power_w in (
        ("2026-04-05T22:00:00+00:00", 400.0),
        ("2026-04-05T23:00:00+00:00", 500.0),
    ):
        record_snapshot(
            db,
            _sample(recorded_at, pv_power_w, 200.0),
            {"QPGS0": {"supported": True, "checked_at": recorded_at, "crc_ok": True}},
            [],
            max_gap_seconds=180,
            persist_raw_frames=False,
            pricing=_pricing(),
        )

    for recorded_at, recorded_minute in (
        ("2026-04-05T22:00:00+00:00", "2026-04-06T00:00"),
        ("2026-04-05T23:00:00+00:00", "2026-04-06T01:00"),
    ):
        for table in ("samples", "minute_samples"):
            db.execute(
                f"""
                UPDATE {table}
                SET
                    recorded_minute = ?,
                    local_day = '2026-04-06',
                    local_month = '2026-04',
                    local_year = '2026'
                WHERE recorded_at = ?
                """,
                [recorded_minute, recorded_at],
            )
        db.execute(
            """
            UPDATE derived_energy_intervals
            SET
                local_day = '2026-04-06',
                local_month = '2026-04',
                local_year = '2026'
            WHERE recorded_at = ?
            """,
            [recorded_at],
        )

    rebuild_energy_rollups(db)

    payload = server._period_history_payload(db, "day", "2026-04-06")
    high_res = json.loads(payload["high_res"])

    assert payload["state"] == "ok"
    assert [row[0] for row in high_res] == ["00:00:00", "01:00:00"]


def test_live_chart_uses_minute_samples_for_long_ranges(monkeypatch):
    _configure_server_globals()
    captured = {}
    reference_time = datetime(2026, 4, 8, 18, 0, tzinfo=timezone.utc)

    def fake_aggregated_history_samples(_db, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(server, "_aggregated_history_samples", fake_aggregated_history_samples)

    payload = server._live_chart_payload_at(None, 12, reference_time=reference_time)

    assert payload["state"] == "nodata"
    assert captured["table"] == "minute_samples"


def test_live_chart_uses_raw_samples_for_short_ranges(monkeypatch):
    _configure_server_globals()
    captured = {}
    reference_time = datetime(2026, 4, 8, 18, 0, tzinfo=timezone.utc)

    def fake_aggregated_history_samples(_db, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(server, "_aggregated_history_samples", fake_aggregated_history_samples)

    payload = server._live_chart_payload_at(None, 1, reference_time=reference_time)

    assert payload["state"] == "nodata"
    assert captured["table"] == "samples"


def test_live_chart_uses_history_samples_when_window_crosses_midnight(monkeypatch):
    _configure_server_globals()
    captured = {}
    reference_time = datetime(2026, 4, 7, 22, 10, tzinfo=timezone.utc)

    def fake_aggregated_cross_day_live_samples(_db, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(
        server,
        "_aggregated_cross_day_live_samples",
        fake_aggregated_cross_day_live_samples,
    )

    payload = server._live_chart_payload_at(None, 2, reference_time=reference_time)

    assert payload["state"] == "nodata"
    assert captured["recent_table"] == "samples"
    assert captured["current_local_day"] == "2026-04-08"


def test_live_chart_exposes_battery_and_grid_curves(tmp_path):
    _configure_server_globals()
    db = Database(str(tmp_path / "live_chart_flows.sqlite"))
    ensure_schema(db)

    reference_time = datetime(2026, 4, 8, 12, 0, tzinfo=timezone.utc)
    recorded_at = reference_time.replace(microsecond=0).isoformat()
    record_snapshot(
        db,
        _sample(recorded_at, 200.0, 900.0, discharge_w=500.0),
        {"QPGS0": {"supported": True, "checked_at": recorded_at, "crc_ok": True}},
        [],
        max_gap_seconds=180,
        persist_raw_frames=False,
    )

    payload = server._live_chart_payload_at(db, 1, reference_time=reference_time)

    assert payload["state"] == "ok"
    assert len(payload["series"]) == 1
    assert abs(payload["series"][0][2] - 0.2) < 1e-9
    assert abs(payload["series"][0][3] - 0.9) < 1e-9
    assert abs(payload["series"][0][4] - 0.5) < 1e-9
    assert abs(payload["series"][0][5] - 0.2) < 1e-9


def test_overview_payload_exposes_battery_split_and_live_metrics(tmp_path, monkeypatch):
    _configure_server_globals()
    db = Database(str(tmp_path / "current.sqlite"))
    ensure_schema(db)

    first_recorded_at, second_recorded_at = _recent_timestamps()
    for recorded_at in (first_recorded_at, second_recorded_at):
        record_snapshot(
            db,
            _sample(recorded_at, 200.0, 700.0, discharge_w=500.0, soc=62.0),
            {"QPGS0": {"supported": True, "checked_at": recorded_at, "crc_ok": True}},
            [],
            max_gap_seconds=180,
            persist_raw_frames=False,
        )

    monkeypatch.setattr(server, "_open_db", lambda: db)
    payload = server._overview_payload()

    assert payload["state"] == "ok"
    assert payload["live"]["solar_to_house_power_w"]["value"] == 200.0
    assert payload["live"]["battery_to_house_power_w"]["value"] == 500.0
    assert payload["live"]["grid_to_house_power_w"]["value"] == 0.0
    assert payload["live"]["battery_state_of_charge_percent"]["value"] == 62.0
    assert payload["live"]["battery_discharge_power_w"]["value"] == 500.0


def test_overview_payload_prefers_battery_charging_over_direct_pv_load_in_line_mode(tmp_path, monkeypatch):
    _configure_server_globals()
    db = Database(str(tmp_path / "current_charge.sqlite"))
    ensure_schema(db)

    first_recorded_at, second_recorded_at = _recent_timestamps()
    for recorded_at in (first_recorded_at, second_recorded_at):
        record_snapshot(
            db,
            _sample(recorded_at, 500.0, 500.0, charge_w=500.0),
            {"QPGS0": {"supported": True, "checked_at": recorded_at, "crc_ok": True}},
            [],
            max_gap_seconds=180,
            persist_raw_frames=False,
        )

    monkeypatch.setattr(server, "_open_db", lambda: db)
    payload = server._overview_payload()

    assert payload["state"] == "ok"
    assert payload["live"]["solar_to_house_power_w"]["value"] == 0.0
    assert payload["live"]["grid_to_house_power_w"]["value"] == 500.0
    assert payload["live"]["solar_to_battery_power_w"]["value"] == 500.0
    assert payload["live"]["grid_to_battery_power_w"]["value"] == 0.0


def test_period_payload_marks_period_incomplete_when_gap_is_excluded(tmp_path):
    _configure_server_globals()
    db = Database(str(tmp_path / "history_gap.sqlite"))
    ensure_schema(db)

    for recorded_at in (
        "2000-01-01T10:00:00+00:00",
        "2000-01-01T10:01:00+00:00",
        "2000-01-01T10:10:00+00:00",
    ):
        record_snapshot(
            db,
            _sample(recorded_at, 600.0, 300.0),
            {"QPGS0": {"supported": True, "checked_at": recorded_at, "crc_ok": True}},
            [],
            max_gap_seconds=180,
            persist_raw_frames=False,
        )

    payload = server._period_history_payload(db, "day", "2000-01-01")

    assert payload["state"] == "ok"
    assert payload["data_complete"] is False
    assert payload["missing_seconds"] > 180.0
    assert abs(payload["produced_kwh"] - 0.01) < 1e-9


def test_overview_payload_marks_stale_snapshots(tmp_path, monkeypatch):
    _configure_server_globals()
    db = Database(str(tmp_path / "current_stale.sqlite"))
    ensure_schema(db)

    for recorded_at in ("2000-01-01T10:00:00+00:00", "2000-01-01T10:01:00+00:00"):
        record_snapshot(
            db,
            _sample(recorded_at, 500.0, 250.0),
            {"QPGS0": {"supported": True, "checked_at": recorded_at, "crc_ok": True}},
            [],
            max_gap_seconds=180,
            persist_raw_frames=False,
        )

    monkeypatch.setattr(server, "_open_db", lambda: db)
    payload = server._overview_payload()

    assert payload["state"] == "ok"
    assert payload["current_data_stale"] is True
    assert payload["live_state"] == "offline"
    assert payload["live_values_zeroed"] is True
    assert payload["live"]["ac_output_active_power_w"]["value"] == 0
    assert payload["live"]["ac_output_active_power_w"]["semantics"] == "stale_zero"
    assert payload["live"]["pv_power_w"]["value"] == 0
    assert payload["live"]["battery_state_of_charge_percent"]["value"] == 0
    assert payload["live"]["battery_discharge_current_a"]["value"] == 0
    assert payload["health"]["ac_output_on"] is False
    assert payload["health"]["ac_input_available"] is False
    assert payload["device"]["operation_mode"] is None
    assert payload["cumulative"]["all_time"]["pv_energy_kwh"] > 0.0


def test_current_period_is_available_with_zero_totals_when_live_data_is_stale(
    tmp_path,
    monkeypatch,
):
    _configure_server_globals()
    db = Database(str(tmp_path / "current_period_stale.sqlite"))
    ensure_schema(db)

    for recorded_at in ("2000-01-01T10:00:00+00:00", "2000-01-01T10:01:00+00:00"):
        record_snapshot(
            db,
            _sample(recorded_at, 500.0, 250.0),
            {"QPGS0": {"supported": True, "checked_at": recorded_at, "crc_ok": True}},
            [],
            max_gap_seconds=180,
            persist_raw_frames=False,
        )

    monkeypatch.setattr(
        server,
        "_now_local",
        lambda: datetime(2000, 1, 2, 12, 0, tzinfo=timezone.utc),
    )

    date_bounds = server._date_bounds_payload(db)
    assert date_bounds["available_days"]["max"] == "2000-01-02"
    assert "2000-01-02" in date_bounds["available_days"]["values"]

    payload = server._period_history_payload(db, "day", "2000-01-02")

    assert payload["state"] == "ok"
    assert payload["history_values_zeroed"] is True
    assert payload["produced_kwh"] == 0.0
    assert payload["consumed_total_kwh"] == 0.0
    assert payload["earned_total"] == 0.0
    assert payload["data_complete"] is False
    assert payload["high_res"] == ""


def test_overview_payload_exposes_dashboard_staleness_and_metric_semantics(tmp_path, monkeypatch):
    _configure_server_globals()
    db = Database(str(tmp_path / "overview_semantics.sqlite"))
    ensure_schema(db)

    first_recorded_at, second_recorded_at = _recent_timestamps()
    for recorded_at in (first_recorded_at, second_recorded_at):
        record_snapshot(
            db,
            _sample(recorded_at, 250.0, 400.0, charge_w=150.0, soc=73.0),
            {"QPGS0": {"supported": True, "checked_at": recorded_at, "crc_ok": True}},
            [],
            max_gap_seconds=180,
            persist_raw_frames=False,
        )

    monkeypatch.setattr(server, "_open_db", lambda: db)
    payload = server._overview_payload()

    assert payload["state"] == "ok"
    assert payload["current_data_stale"] is False
    assert payload["live_state"] == "live"
    assert "today_data_complete" in payload
    assert payload["live"]["ac_output_active_power_w"]["semantics"] == "exact"
    assert payload["live"]["pv_power_w"]["semantics"] == "derived"
    assert payload["live"]["grid_to_house_power_w"]["semantics"] == "derived"
    assert payload["live"]["battery_state_of_charge_percent"]["value"] == 73.0


def test_overview_payload_prefers_pricing_stored_in_current_snapshot(tmp_path, monkeypatch):
    _configure_server_globals()
    db = Database(str(tmp_path / "overview_pricing.sqlite"))
    ensure_schema(db)

    first_recorded_at, second_recorded_at = _recent_timestamps()
    pricing = {
        "grid_price_eur_per_kwh": 0.1812,
        "feed_in_revenue_eur_per_kwh": 0.085,
        "source": "tempo_api",
        "tempo_available": True,
        "tariff_label": "Bleu-HP",
        "color_label": "Bleu",
        "tomorrow_color_label": "Blanc",
        "display": "Bleu-HP 0.1812 EUR/kWh",
    }

    for recorded_at in (first_recorded_at, second_recorded_at):
        record_snapshot(
            db,
            _sample(recorded_at, 250.0, 400.0, charge_w=150.0, soc=73.0),
            {"QPGS0": {"supported": True, "checked_at": recorded_at, "crc_ok": True}},
            [],
            max_gap_seconds=180,
            persist_raw_frames=False,
            pricing=pricing,
        )

    class _FailTempoClient:
        def get_state(self, force_refresh=False):
            raise AssertionError("overview should reuse the stored pricing context")

    monkeypatch.setattr(server, "_open_db", lambda: db)
    monkeypatch.setattr(server, "tempo_client", _FailTempoClient())

    payload = server._overview_payload()

    assert payload["state"] == "ok"
    assert payload["pricing"]["grid_price_eur_per_kwh"] == 0.1812
    assert payload["pricing"]["tempo_tariff_label"] == "Bleu-HP"


def test_dashboard_live_payload_stays_lightweight(tmp_path, monkeypatch):
    _configure_server_globals()
    db = Database(str(tmp_path / "dashboard_live.sqlite"))
    ensure_schema(db)

    first_recorded_at, second_recorded_at = _recent_timestamps()
    for recorded_at in (first_recorded_at, second_recorded_at):
        record_snapshot(
            db,
            _sample(recorded_at, 250.0, 400.0, charge_w=150.0, soc=73.0),
            {"QPGS0": {"supported": True, "checked_at": recorded_at, "crc_ok": True}},
            [],
            max_gap_seconds=180,
            persist_raw_frames=False,
            pricing=_pricing(),
        )

    monkeypatch.setattr(server, "_open_db", lambda: db)
    payload = server._dashboard_live_payload()

    assert payload["state"] == "ok"
    assert "cumulative" not in payload
    assert "today_data_complete" not in payload
    assert payload["pricing"]["grid_price_eur_per_kwh"] == 0.3
    assert payload["live"]["ac_output_active_power_w"]["value"] == 400.0


def test_date_bounds_payload_uses_history_samples(tmp_path):
    _configure_server_globals()
    db = Database(str(tmp_path / "date_bounds.sqlite"))
    ensure_schema(db)

    for recorded_at in (
        "2024-03-01T10:00:00+00:00",
        "2026-04-05T10:00:00+00:00",
    ):
        record_snapshot(
            db,
            _sample(recorded_at, 100.0, 50.0),
            {"QPGS0": {"supported": True, "checked_at": recorded_at, "crc_ok": True}},
            [],
            max_gap_seconds=180,
            persist_raw_frames=False,
        )

    payload = server._date_bounds_payload(db)

    assert payload["state"] == "ok"
    assert payload["year_min"] == 2024
    assert payload["year_max"] == 2026
    assert payload["available_days"]["values"] == ["2024-03-01", "2026-04-05"]
    assert payload["available_days"]["years"] == [2024, 2026]
    assert payload["available_days"]["months_by_year"] == {
        "2024": [3],
        "2026": [4],
    }
    assert payload["available_days"]["days_by_month"] == {
        "2024-03": [1],
        "2026-04": [5],
    }
    assert payload["available_months"]["values"] == ["2024-03", "2026-04"]
    assert payload["available_months"]["years"] == [2024, 2026]
    assert payload["available_months"]["months_by_year"] == {
        "2024": [3],
        "2026": [4],
    }
    assert payload["available_years"]["values"] == [2024, 2026]


def test_static_assets_use_immutable_cache_headers():
    client = server.app.test_client()

    response = client.get("/css/styles.css?build=20260404b")

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "public, max-age=31536000, immutable"


def test_index_html_stays_no_cache():
    client = server.app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-cache"


def test_ensure_schema_creates_minute_samples_recorded_at_index(tmp_path):
    db = Database(str(tmp_path / "schema.sqlite"))
    ensure_schema(db)

    indexes = {row["name"] for row in db.execute("PRAGMA index_list(minute_samples)")}

    assert "idx_minute_samples_recorded_at" in indexes


def test_breakdown_payload_returns_grouped_items(tmp_path):
    _configure_server_globals()
    db = Database(str(tmp_path / "breakdown.sqlite"))
    ensure_schema(db)

    for recorded_at, pv_power_w, output_w, export_w in (
        ("2026-04-04T10:00:00+00:00", 600.0, 300.0, 100.0),
        ("2026-04-04T10:01:00+00:00", 600.0, 300.0, 100.0),
        ("2026-04-05T10:00:00+00:00", 500.0, 250.0, 50.0),
        ("2026-04-05T10:01:00+00:00", 500.0, 250.0, 50.0),
    ):
        record_snapshot(
            db,
            _sample(recorded_at, pv_power_w, output_w, export_w=export_w),
            {"QPGS0": {"supported": True, "checked_at": recorded_at, "crc_ok": True}},
            [],
            max_gap_seconds=180,
            persist_raw_frames=False,
            pricing=_pricing(),
        )

    payload = server._breakdown_payload(db, "day", "2026-04")

    assert payload["state"] == "ok"
    assert len(payload["items"]) == 2
    assert payload["items"][0]["date"] == "2026-04-04"
    assert payload["items"][1]["date"] == "2026-04-05"


def test_statistics_and_breakdown_use_materialized_rollups(tmp_path):
    _configure_server_globals()
    db = Database(str(tmp_path / "rollup_endpoints.sqlite"))
    ensure_schema(db)

    for recorded_at, pv_power_w, output_w, export_w in (
        ("2026-04-04T10:00:00+00:00", 600.0, 300.0, 100.0),
        ("2026-04-04T10:01:00+00:00", 600.0, 300.0, 100.0),
        ("2026-04-05T10:00:00+00:00", 500.0, 250.0, 50.0),
        ("2026-04-05T10:01:00+00:00", 500.0, 250.0, 50.0),
    ):
        record_snapshot(
            db,
            _sample(recorded_at, pv_power_w, output_w, export_w=export_w),
            {"QPGS0": {"supported": True, "checked_at": recorded_at, "crc_ok": True}},
            [],
            max_gap_seconds=180,
            persist_raw_frames=False,
            pricing=_pricing(),
        )

    stats_before = server._statistics_payload(db)
    breakdown_before = server._breakdown_payload(db, "day", "2026-04")

    db.execute("DELETE FROM derived_energy_intervals")

    stats_after = server._statistics_payload(db)
    breakdown_after = server._breakdown_payload(db, "day", "2026-04")

    assert stats_after["best_day_date"] == stats_before["best_day_date"]
    assert stats_after["best_day_production_kwh"] == stats_before["best_day_production_kwh"]
    assert breakdown_after["items"] == breakdown_before["items"]
