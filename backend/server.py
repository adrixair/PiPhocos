import csv
import io
import json
import logging
import math
import os
import threading
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import (
    Flask,
    g,
    has_app_context,
    jsonify,
    make_response,
    request,
    send_from_directory,
)
from flask_compress import Compress

from config import Config
from database import Database
from energy_flow import estimate_site_flow, percent_or_default
from paths import CONFIG_PATH, DATA_DIR, DB_PATH, SERVER_LOG_PATH, SITE_DIR
from phocos_store import (
    calculate_power_flow_breakdown,
    csv_rows_for_samples,
    ensure_schema,
    get_best_bucket_total,
    get_bucket_totals,
    get_capabilities,
    get_current_snapshot,
    get_grouped_cumulative,
    get_history_series,
)
from tempo_edf import TempoApiClient, build_pricing_context
import version


config = None
tempo_client = None

app = Flask(__name__)
Compress(app)

MAX_GRAPH_POINTS = 200
_SCHEMA_READY = False
_SCHEMA_LOCK = threading.Lock()
STATIC_ASSET_CACHE_MAX_AGE_SECONDS = 31536000
STATIC_ASSET_PREFIXES = ("assets/", "css/", "js/", "lib/")
STATIC_ASSET_NAMES = {"favicon.ico", "manifest.webmanifest"}
STALE_ZERO_SEMANTICS = "stale_zero"
STALE_ZERO_LIVE_METRICS = {
    "ac_input_voltage_v",
    "ac_input_frequency_hz",
    "ac_output_voltage_v",
    "ac_output_frequency_hz",
    "ac_output_active_power_w",
    "ac_output_apparent_power_va",
    "ac_output_load_percent",
    "battery_voltage_v",
    "battery_state_of_charge_percent",
    "battery_charge_current_a",
    "battery_discharge_current_a",
    "total_charging_current_a",
    "battery_charge_power_w",
    "battery_discharge_power_w",
    "pv_input_voltage_v",
    "pv_input_current_a",
    "pv_power_w",
    "pv_charging_power_w",
    "solar_feed_to_grid_power_w",
    "total_ac_output_apparent_power_va",
    "total_output_active_power_w",
    "total_output_load_percent",
    "max_charging_current_set_a",
    "max_charging_current_possible_a",
    "max_ac_charging_current_set_a",
    "bus_voltage_v",
    "inverter_temperature_c",
    "battery_voltage_from_scc_v",
    "solar_to_house_power_w",
    "solar_to_battery_power_w",
    "battery_to_house_power_w",
    "grid_to_house_power_w",
    "grid_to_battery_power_w",
}
STALE_DYNAMIC_DEVICE_FIELDS = {
    "other_units_connected",
    "other_units_connected_code",
    "operation_mode",
    "operation_mode_code",
    "fault",
    "fault_code",
    "ac_output_mode",
    "output_source_priority",
    "battery_charger_source_priority",
}
STALE_LIVE_TEXT_FIELDS = {
    "battery_state",
    "output_source_priority",
    "battery_charger_source_priority",
    "status_bits",
}


def _ensure_server_schema(db):
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    with _SCHEMA_LOCK:
        if _SCHEMA_READY:
            return
        ensure_schema(db)
        _SCHEMA_READY = True


def _open_db():
    if has_app_context():
        db = getattr(g, "_db", None)
        if db is None:
            db = Database(str(DB_PATH))
            _ensure_server_schema(db)
            g._db = db
        return db

    db = Database(str(DB_PATH))
    _ensure_server_schema(db)
    return db


@app.teardown_appcontext
def _close_db(_exception):
    db = getattr(g, "_db", None)
    if db is not None:
        db.close()
        g._db = None


def _metric(value, unit, semantics):
    return {"value": value, "unit": unit, "semantics": semantics}


def _zero_stale_live_payload(payload):
    payload["live_values_zeroed"] = True

    for key in STALE_DYNAMIC_DEVICE_FIELDS:
        if key in payload["device"]:
            payload["device"][key] = None

    payload["health"].update(
        {
            "fault_active": False,
            "ac_input_available": False,
            "ac_output_on": False,
            "mppt_active": False,
            "solar_charging_on": False,
            "ac_charging_on": False,
            "solar_feed_to_grid_enabled": False,
            "active_warning_bits": [],
            "warning_bitmap": None,
            "flag_blob": None,
        }
    )

    for key in STALE_ZERO_LIVE_METRICS:
        metric = payload["live"].get(key)
        if isinstance(metric, dict):
            metric["value"] = 0
            metric["semantics"] = STALE_ZERO_SEMANTICS

    for key in STALE_LIVE_TEXT_FIELDS:
        if key in payload["live"]:
            payload["live"][key] = None

    return payload


def _configured_local_tz():
    tz_name = None
    if config is not None:
        tz_name = (config.config_data or {}).get("time_zone")
    if tz_name:
        try:
            return ZoneInfo(tz_name)
        except ZoneInfoNotFoundError:
            logging.warning(
                "Server: unknown configured time zone %s, falling back to system local time",
                tz_name,
            )
    return datetime.now().astimezone().tzinfo


def _to_local(value: datetime) -> datetime:
    return value.astimezone(_configured_local_tz())


def _now_local():
    return datetime.now(_configured_local_tz())


def _configured_start_date(reference_time=None):
    now_local = (reference_time or _now_local()).astimezone()
    start_date = config.config_data["device"].get("start_date") if config else None
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    return start_date or now_local.date()


def _is_cacheable_static_asset(path: str) -> bool:
    if not path:
        return False
    if path in STATIC_ASSET_NAMES:
        return True
    return path.startswith(STATIC_ASSET_PREFIXES)


def _apply_static_cache_headers(response, path: str):
    if path == "index.html":
        response.headers["Cache-Control"] = "no-cache"
        return response

    if _is_cacheable_static_asset(path):
        response.headers["Cache-Control"] = (
            f"public, max-age={STATIC_ASSET_CACHE_MAX_AGE_SECONDS}, immutable"
        )
        return response

    response.headers["Cache-Control"] = "public, max-age=3600"
    return response


def _start_of_operation_date(db, reference_time=None):
    now_local = (reference_time or _now_local()).astimezone()
    first_recorded_at = None
    for table_name in ("samples", "compressed_samples_10m"):
        row = db.fetchone(
            f"SELECT MIN(recorded_at) AS first_recorded_at FROM {table_name}"
        )
        candidate = row["first_recorded_at"] if row else None
        if candidate and (first_recorded_at is None or candidate < first_recorded_at):
            first_recorded_at = candidate
    if first_recorded_at:
        return (
            datetime.fromisoformat(first_recorded_at)
            .astimezone(now_local.tzinfo)
            .date()
        )
    return _configured_start_date(reference_time=now_local)


def _stale_gap_threshold_seconds():
    grabber = (config.config_data or {}).get("grabber", {}) if config else {}
    interval_seconds = float(grabber.get("interval_s") or 60.0)
    gap_seconds = float(grabber.get("max_gap_for_cumulative_s") or 180.0)
    stale_after_seconds = float(
        grabber.get("stale_after_s") or (interval_seconds * 3.0 + 5.0)
    )
    return max(interval_seconds, min(gap_seconds, stale_after_seconds))


def _pricing_context(db=None, current=None, force_refresh=False):
    if current is not None:
        stored_pricing = current.get("pricing")
        if stored_pricing:
            return stored_pricing

    if db is not None and current is None:
        current = get_current_snapshot(
            db,
            include_cumulative=False,
            include_capabilities=False,
        )
        if current and current.get("pricing"):
            return current["pricing"]

    prices = config.config_data["prices"]
    tempo_state = (
        tempo_client.get_state(force_refresh=force_refresh)
        if tempo_client is not None
        else None
    )
    return build_pricing_context(
        tempo_state,
        prices["price_per_grid_kwh"],
        prices["revenue_per_fed_in_kwh"],
    )


def _safe_float(value):
    try:
        if value is None:
            return 0.0
        return max(float(value), 0.0)
    except (TypeError, ValueError):
        return 0.0


def _graph_max_points():
    return MAX_GRAPH_POINTS


def _instance_name():
    if config is None:
        return "PiPhocos"

    instance = config.config_data.get("instance")
    if not isinstance(instance, dict):
        instance = {}
    return instance.get("name") or "PiPhocos"


def _diagnostics_enabled():
    if config is None:
        return False

    diagnostics = (config.config_data or {}).get("diagnostics", {})
    if not isinstance(diagnostics, dict):
        return False
    return bool(diagnostics.get("enabled", False))


def _history_sample_bounds(db, *, since_iso=None, local_day=None, table="history_samples"):
    filters = []
    params = []
    if since_iso is not None:
        filters.append("recorded_at >= ?")
        params.append(since_iso)
    if local_day is not None:
        filters.append("local_day = ?")
        params.append(local_day)

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    bounds = db.fetchone(
        f"""
        SELECT
            COUNT(*) AS sample_count,
            MIN(recorded_at) AS first_recorded_at,
            MAX(recorded_at) AS last_recorded_at
        FROM {table}
        {where_clause}
        """,
        params,
    )
    return bounds, where_clause, params


def _prefix_range_params(prefix):
    if not prefix:
        return None
    return [prefix, prefix + "\uffff"]


def _aggregated_history_samples(
    db,
    *,
    since_iso=None,
    local_day=None,
    max_points=None,
    table="history_samples",
):
    bounds, where_clause, params = _history_sample_bounds(
        db,
        since_iso=since_iso,
        local_day=local_day,
        table=table,
    )
    sample_count = int((dict(bounds) if bounds else {}).get("sample_count") or 0)
    if sample_count <= 0:
        return []

    max_points = max(int(max_points or _graph_max_points()), 1)
    if sample_count <= max_points:
        return db.execute(
            f"""
            SELECT
                recorded_at,
                pv_power_w,
                ac_output_active_power_w,
                battery_charge_power_w,
                battery_discharge_power_w,
                solar_feed_to_grid_power_w
            FROM {table}
            {where_clause}
            ORDER BY recorded_at ASC
            """,
            params,
        )

    first_recorded_at = datetime.fromisoformat(bounds["first_recorded_at"])
    last_recorded_at = datetime.fromisoformat(bounds["last_recorded_at"])
    total_seconds = max((last_recorded_at - first_recorded_at).total_seconds(), 1.0)
    bucket_seconds = max(int(math.ceil(total_seconds / float(max_points))), 1)

    return db.execute(
        f"""
        WITH filtered AS (
            SELECT
                recorded_at,
                pv_power_w,
                ac_output_active_power_w,
                battery_charge_power_w,
                battery_discharge_power_w,
                solar_feed_to_grid_power_w,
                CAST(
                    ((julianday(recorded_at) - julianday(?)) * 86400.0) / ?
                    AS INTEGER
                ) AS bucket_index
            FROM {table}
            {where_clause}
        )
        SELECT
            MAX(recorded_at) AS recorded_at,
            AVG(pv_power_w) AS pv_power_w,
            AVG(ac_output_active_power_w) AS ac_output_active_power_w,
            AVG(battery_charge_power_w) AS battery_charge_power_w,
            AVG(battery_discharge_power_w) AS battery_discharge_power_w,
            AVG(solar_feed_to_grid_power_w) AS solar_feed_to_grid_power_w
        FROM filtered
        GROUP BY bucket_index
        ORDER BY recorded_at ASC
        """,
        [bounds["first_recorded_at"], bucket_seconds, *params],
    )


def _prefer_minute_rollup_for_day(db, local_day, max_points):
    if local_day != _now_local().strftime("%Y-%m-%d"):
        return False

    row = db.fetchone(
        """
        SELECT COUNT(*) AS sample_count
        FROM samples
        WHERE local_day = ?
        """,
        [local_day],
    )
    sample_count = int((dict(row) if row else {}).get("sample_count") or 0)
    return sample_count > max(max_points * 5, 1000)


def _live_projection_seconds(recorded_at, reference_time=None):
    if not recorded_at:
        return 0.0
    reference_time = reference_time or datetime.now(timezone.utc)
    recorded_dt = datetime.fromisoformat(recorded_at).astimezone(timezone.utc)
    elapsed_seconds = max((reference_time - recorded_dt).total_seconds(), 0.0)
    interval_seconds = float(
        ((config.config_data or {}).get("grabber", {}) if config else {}).get(
            "interval_s",
            60.0,
        )
        or 60.0
    )
    return min(elapsed_seconds, max(interval_seconds, 1.0))


def _live_projection_from_flow(live_flow, pricing, elapsed_seconds):
    elapsed_seconds = max(float(elapsed_seconds or 0.0), 0.0)
    if elapsed_seconds <= 0.0:
        return {
            "produced_kwh": 0.0,
            "consumed_kwh": 0.0,
            "battery_charge_kwh": 0.0,
            "battery_discharge_kwh": 0.0,
            "fed_in_kwh": 0.0,
            "pv_to_load_kwh": 0.0,
            "pv_to_battery_kwh": 0.0,
            "battery_to_load_kwh": 0.0,
            "grid_to_load_kwh": 0.0,
            "grid_to_battery_kwh": 0.0,
            "earned_feed_in_eur": 0.0,
            "earned_savings_eur": 0.0,
        }

    revenue = _safe_float(pricing.get("feed_in_revenue_eur_per_kwh"))
    savings_rate = _safe_float(pricing.get("grid_price_eur_per_kwh"))

    def power_to_kwh(power_w):
        return _safe_float(power_w) * elapsed_seconds / 3_600_000.0

    pv_to_load_kwh = power_to_kwh(live_flow.get("consumed_from_pv"))
    battery_to_load_kwh = power_to_kwh(live_flow.get("consumed_from_battery"))
    fed_in_kwh = power_to_kwh(live_flow.get("fed_in"))

    return {
        "produced_kwh": power_to_kwh(live_flow.get("produced")),
        "consumed_kwh": power_to_kwh(live_flow.get("consumed_total")),
        "battery_charge_kwh": power_to_kwh(live_flow.get("battery_charged")),
        "battery_discharge_kwh": power_to_kwh(live_flow.get("battery_discharged")),
        "fed_in_kwh": fed_in_kwh,
        "pv_to_load_kwh": pv_to_load_kwh,
        "pv_to_battery_kwh": power_to_kwh(live_flow.get("produced_to_battery")),
        "battery_to_load_kwh": battery_to_load_kwh,
        "grid_to_load_kwh": power_to_kwh(live_flow.get("consumed_from_grid")),
        "grid_to_battery_kwh": power_to_kwh(live_flow.get("battery_charged_from_grid")),
        "earned_feed_in_eur": fed_in_kwh * revenue,
        "earned_savings_eur": (pv_to_load_kwh + battery_to_load_kwh) * savings_rate,
    }


def _extend_aggregated_totals_with_live_projection(
    totals,
    current,
    pricing,
    reference_time=None,
):
    if not totals or not current or _snapshot_is_stale(current.get("recorded_at")):
        return totals

    elapsed_seconds = _live_projection_seconds(
        current.get("recorded_at"),
        reference_time=reference_time,
    )
    if elapsed_seconds <= 0.0:
        return totals

    extension = _live_projection_from_flow(
        _current_live_breakdown(current["snapshot"]),
        pricing,
        elapsed_seconds,
    )
    merged = dict(totals)
    merged["produced"] = _safe_float(merged.get("produced")) + extension["produced_kwh"]
    merged["consumed"] = _safe_float(merged.get("consumed")) + extension["consumed_kwh"]
    merged["fed_in"] = _safe_float(merged.get("fed_in")) + extension["fed_in_kwh"]
    merged["battery_charge"] = _safe_float(merged.get("battery_charge")) + extension[
        "battery_charge_kwh"
    ]
    merged["battery_discharge"] = _safe_float(
        merged.get("battery_discharge")
    ) + extension["battery_discharge_kwh"]
    merged["pv_to_load"] = _safe_float(merged.get("pv_to_load")) + extension[
        "pv_to_load_kwh"
    ]
    merged["pv_to_battery"] = _safe_float(merged.get("pv_to_battery")) + extension[
        "pv_to_battery_kwh"
    ]
    merged["battery_to_load"] = _safe_float(merged.get("battery_to_load")) + extension[
        "battery_to_load_kwh"
    ]
    merged["grid_to_load"] = _safe_float(merged.get("grid_to_load")) + extension[
        "grid_to_load_kwh"
    ]
    merged["grid_to_battery"] = _safe_float(
        merged.get("grid_to_battery")
    ) + extension["grid_to_battery_kwh"]
    merged["earned_feed_in_eur"] = _safe_float(
        merged.get("earned_feed_in_eur")
    ) + extension["earned_feed_in_eur"]
    merged["earned_savings_eur"] = _safe_float(
        merged.get("earned_savings_eur")
    ) + extension["earned_savings_eur"]
    merged["live_projection_seconds"] = elapsed_seconds
    merged["live_projection_applied"] = True
    return merged


def _extend_period_totals_with_live_projection(
    period_totals,
    current,
    pricing,
    reference_time=None,
):
    if not period_totals or not current or _snapshot_is_stale(current.get("recorded_at")):
        return period_totals

    elapsed_seconds = _live_projection_seconds(
        current.get("recorded_at"),
        reference_time=reference_time,
    )
    if elapsed_seconds <= 0.0:
        return period_totals

    extension = _live_projection_from_flow(
        _current_live_breakdown(current["snapshot"]),
        pricing,
        elapsed_seconds,
    )
    merged = dict(period_totals)
    merged["pv_energy_kwh"] = _safe_float(merged.get("pv_energy_kwh")) + extension[
        "produced_kwh"
    ]
    merged["load_energy_kwh"] = _safe_float(merged.get("load_energy_kwh")) + extension[
        "consumed_kwh"
    ]
    merged["battery_charge_energy_kwh"] = _safe_float(
        merged.get("battery_charge_energy_kwh")
    ) + extension["battery_charge_kwh"]
    merged["battery_discharge_energy_kwh"] = _safe_float(
        merged.get("battery_discharge_energy_kwh")
    ) + extension["battery_discharge_kwh"]
    merged["grid_export_energy_kwh"] = _safe_float(
        merged.get("grid_export_energy_kwh")
    ) + extension["fed_in_kwh"]
    merged["pv_to_load_energy_kwh"] = _safe_float(
        merged.get("pv_to_load_energy_kwh")
    ) + extension["pv_to_load_kwh"]
    merged["pv_to_battery_energy_kwh"] = _safe_float(
        merged.get("pv_to_battery_energy_kwh")
    ) + extension["pv_to_battery_kwh"]
    merged["battery_to_load_energy_kwh"] = _safe_float(
        merged.get("battery_to_load_energy_kwh")
    ) + extension["battery_to_load_kwh"]
    merged["grid_to_load_energy_kwh"] = _safe_float(
        merged.get("grid_to_load_energy_kwh")
    ) + extension["grid_to_load_kwh"]
    merged["grid_to_battery_energy_kwh"] = _safe_float(
        merged.get("grid_to_battery_energy_kwh")
    ) + extension["grid_to_battery_kwh"]
    merged["earned_feed_in_eur"] = _safe_float(
        merged.get("earned_feed_in_eur")
    ) + extension["earned_feed_in_eur"]
    merged["earned_savings_eur"] = _safe_float(
        merged.get("earned_savings_eur")
    ) + extension["earned_savings_eur"]
    merged["live_projection_seconds"] = elapsed_seconds
    merged["live_projection_applied"] = True
    return merged


def _period_includes_present(table, search_date, reference_time=None):
    local_now = (reference_time or _now_local()).astimezone()
    if table == "days":
        return search_date == local_now.strftime("%Y-%m-%d")
    if table == "months":
        return search_date == local_now.strftime("%Y-%m")
    if table == "years":
        return search_date == local_now.strftime("%Y")
    if table == "all_time":
        return True
    return False


def _period_window_local(table, search_date, db=None):
    now_local = _now_local()
    local_tz = now_local.tzinfo
    if table == "days":
        start = datetime.fromisoformat(search_date).replace(tzinfo=local_tz)
        end = start + timedelta(days=1)
    elif table == "months":
        year, month = [int(part) for part in search_date.split("-")]
        start = datetime(year, month, 1, tzinfo=local_tz)
        if month == 12:
            end = datetime(year + 1, 1, 1, tzinfo=local_tz)
        else:
            end = datetime(year, month + 1, 1, tzinfo=local_tz)
    elif table == "years":
        start = datetime(int(search_date), 1, 1, tzinfo=local_tz)
        end = datetime(int(search_date) + 1, 1, 1, tzinfo=local_tz)
    elif table == "all_time":
        start_date = _start_of_operation_date(db, reference_time=now_local)
        start = datetime.combine(start_date, datetime.min.time(), tzinfo=local_tz)
        end = now_local
    else:
        raise ValueError(f"Unsupported history bucket {table}")

    if table == "all_time":
        effective_end = end
    else:
        effective_end = now_local if start <= now_local < end else end
    return start, effective_end


def _period_completeness(db, table, search_date):
    period_start_local, period_end_local = _period_window_local(
        table,
        search_date,
        db=db,
    )
    period_start_utc = period_start_local.astimezone(timezone.utc)
    period_end_utc = period_end_local.astimezone(timezone.utc)
    expected_seconds = max((period_end_utc - period_start_utc).total_seconds(), 0.0)
    bucket = {
        "days": "day",
        "months": "month",
        "years": "year",
        "all_time": "all_time",
    }[table]
    rollup = get_bucket_totals(
        db,
        bucket,
        None if bucket == "all_time" else search_date,
    )

    covered_seconds = _safe_float(rollup.get("covered_seconds"))
    missing_seconds = max(expected_seconds - covered_seconds, 0.0)
    missing_intervals = int(rollup.get("missing_intervals") or 0)
    threshold_seconds = _stale_gap_threshold_seconds()
    if missing_intervals == 0 and missing_seconds > threshold_seconds:
        missing_intervals = 1

    coverage_percent = 100.0
    if expected_seconds > 0.0:
        coverage_percent = max(
            0.0,
            min(100.0, (covered_seconds / expected_seconds) * 100.0),
        )

    sample_count = int(rollup.get("sample_count") or 0)
    return {
        "sample_count": sample_count,
        "first_recorded_at": rollup.get("first_recorded_at"),
        "last_recorded_at": rollup.get("last_recorded_at"),
        "data_complete": missing_seconds <= threshold_seconds,
        "missing_intervals": missing_intervals,
        "missing_seconds": round(missing_seconds, 3),
        "coverage_percent": round(coverage_percent, 3),
    }


def _snapshot_is_stale(recorded_at):
    if not recorded_at:
        return True
    age_seconds = (
        datetime.now(timezone.utc) - datetime.fromisoformat(recorded_at).astimezone(timezone.utc)
    ).total_seconds()
    return age_seconds > _stale_gap_threshold_seconds()


def _ratio_percent(part, total):
    part = _safe_float(part)
    total = _safe_float(total)
    if total <= 0.0:
        return 0.0
    return (part / total) * 100.0


def _flow_breakdown(produced, load, battery_charge, battery_discharge, fed_in):
    produced = _safe_float(produced)
    load = _safe_float(load)
    battery_charge = _safe_float(battery_charge)
    battery_discharge = _safe_float(battery_discharge)
    fed_in = min(_safe_float(fed_in), produced)

    solar_after_export = max(produced - fed_in, 0.0)
    battery_to_load = min(load, battery_discharge)
    remaining_load = max(load - battery_to_load, 0.0)
    solar_to_load = min(remaining_load, solar_after_export)
    remaining_solar = max(solar_after_export - solar_to_load, 0.0)
    solar_to_battery = min(battery_charge, remaining_solar)
    grid_to_load = max(remaining_load - solar_to_load, 0.0)
    grid_to_battery = max(battery_charge - solar_to_battery, 0.0)

    return {
        "produced": produced,
        "load": load,
        "fed_in": fed_in,
        "produced_to_house": solar_to_load,
        "produced_to_battery": solar_to_battery,
        "consumed_from_pv": solar_to_load,
        "consumed_from_battery": battery_to_load,
        "consumed_from_grid": grid_to_load,
        "consumed_total": load,
        "battery_charged": battery_charge,
        "battery_charged_from_pv": solar_to_battery,
        "battery_charged_from_grid": grid_to_battery,
        "battery_discharged": battery_discharge,
        "self_powered_total": solar_to_load + battery_to_load,
    }


def _flow_breakdown_from_period(period_data):
    period_data = period_data or {}
    if (
        "pv_to_load_energy_kwh" in period_data
        or "battery_to_load_energy_kwh" in period_data
        or "pv_to_battery_energy_kwh" in period_data
    ):
        return {
            "produced": _safe_float(period_data.get("pv_energy_kwh")),
            "load": _safe_float(period_data.get("load_energy_kwh")),
            "fed_in": _safe_float(period_data.get("grid_export_energy_kwh")),
            "produced_to_house": _safe_float(period_data.get("pv_to_load_energy_kwh")),
            "produced_to_battery": _safe_float(
                period_data.get("pv_to_battery_energy_kwh")
            ),
            "consumed_from_pv": _safe_float(period_data.get("pv_to_load_energy_kwh")),
            "consumed_from_battery": _safe_float(
                period_data.get("battery_to_load_energy_kwh")
            ),
            "consumed_from_grid": _safe_float(
                period_data.get("grid_to_load_energy_kwh")
            ),
            "consumed_total": _safe_float(period_data.get("load_energy_kwh")),
            "battery_charged": _safe_float(period_data.get("battery_charge_energy_kwh")),
            "battery_charged_from_pv": _safe_float(
                period_data.get("pv_to_battery_energy_kwh")
            ),
            "battery_charged_from_grid": _safe_float(
                period_data.get("grid_to_battery_energy_kwh")
            ),
            "battery_discharged": _safe_float(
                period_data.get("battery_discharge_energy_kwh")
            ),
            "self_powered_total": _safe_float(period_data.get("pv_to_load_energy_kwh"))
            + _safe_float(period_data.get("battery_to_load_energy_kwh")),
            "earned_feed_in_eur": _safe_float(period_data.get("earned_feed_in_eur")),
            "earned_savings_eur": _safe_float(period_data.get("earned_savings_eur")),
        }
    return _flow_breakdown(
        period_data.get("pv_energy_kwh"),
        period_data.get("load_energy_kwh"),
        period_data.get("battery_charge_energy_kwh"),
        period_data.get("battery_discharge_energy_kwh"),
        period_data.get("grid_export_energy_kwh"),
    )


def _current_live_breakdown(snapshot):
    flows = calculate_power_flow_breakdown(snapshot)
    return {
        "produced": flows["pv_power_w"],
        "load": flows["load_power_w"],
        "fed_in": flows["grid_export_power_w"],
        "produced_to_house": flows["pv_to_load_power_w"],
        "produced_to_battery": flows["pv_to_battery_power_w"],
        "consumed_from_pv": flows["pv_to_load_power_w"],
        "consumed_from_battery": flows["battery_to_load_power_w"],
        "consumed_from_grid": flows["grid_to_load_power_w"],
        "consumed_total": flows["load_power_w"],
        "battery_charged": flows["battery_charge_power_w"],
        "battery_charged_from_pv": flows["pv_to_battery_power_w"],
        "battery_charged_from_grid": flows["grid_to_battery_power_w"],
        "battery_discharged": flows["battery_discharge_power_w"],
        "self_powered_total": flows["local_supply_to_load_power_w"],
    }


def _derived_energy_available(db):
    row = db.fetchone("SELECT COUNT(*) AS count FROM derived_energy_intervals")
    return bool(row and row["count"] > 0)


def _overview_payload(*, compact=False, db=None, current=None):
    db = db or _open_db()
    current = current or get_current_snapshot(
        db,
        include_cumulative=not compact,
        include_capabilities=not compact,
    )
    if not current:
        return {"state": "nodata"}

    payload = _dashboard_live_payload_from_current(
        current,
        include_capabilities=not compact,
    )
    if compact:
        return payload

    pricing = _pricing_context(current=current)
    cumulative = {
        period: _extend_period_totals_with_live_projection(
            totals,
            current,
            pricing,
        )
        for period, totals in current["cumulative"].items()
    }
    today_date = _now_local().strftime("%Y-%m-%d")
    today_completeness = _period_completeness(db, "days", today_date)

    payload.update(
        {
            "today_data_complete": today_completeness["data_complete"],
            "today_missing_intervals": today_completeness["missing_intervals"],
            "today_missing_seconds": today_completeness["missing_seconds"],
            "today_coverage_percent": today_completeness["coverage_percent"],
            "cumulative": cumulative,
        }
    )
    return payload


def _dashboard_live_payload_from_current(current, *, include_capabilities=True):
    if not current:
        return {"state": "nodata"}

    snapshot = current["snapshot"]
    semantics = current["semantics"]
    pricing = _pricing_context(current=current)
    inverter_status = snapshot.get("inverter_status") or {}
    warning_bits = snapshot.get("warning_bits") or {}
    qpiri = snapshot.get("qpiri") or {}
    live_flow = _current_live_breakdown(snapshot)
    stale = _snapshot_is_stale(current["recorded_at"])

    payload = {
        "state": "ok",
        "name": _instance_name(),
        "recorded_at": current["recorded_at"],
        "public_url": config.config_data["server"]["public_url"],
        "current_data_stale": stale,
        "live_state": "offline" if stale else "live",
        "device": {
            "other_units_connected": snapshot.get("other_units_connected"),
            "other_units_connected_code": snapshot.get("other_units_connected_code"),
            "operation_mode": snapshot.get("operation_mode"),
            "operation_mode_code": snapshot.get("operation_mode_code"),
            "fault": snapshot.get("fault"),
            "fault_code": snapshot.get("fault_code"),
            "ac_output_mode": snapshot.get("ac_output_mode"),
            "country_code": snapshot.get("country_code"),
            "output_source_priority": qpiri.get("output_source_priority"),
            "battery_charger_source_priority": snapshot.get(
                "battery_charger_source_priority"
            ),
        },
        "health": {
            "fault_active": snapshot.get("fault_code") not in {None, "00"},
            "ac_input_available": inverter_status.get("ac_input_available"),
            "ac_output_on": inverter_status.get("ac_output_on"),
            "mppt_active": inverter_status.get("mppt_active"),
            "solar_charging_on": inverter_status.get("solar_charging_on"),
            "ac_charging_on": inverter_status.get("ac_charging_on"),
            "solar_feed_to_grid_enabled": snapshot.get("solar_feed_to_grid_enabled"),
            "active_warning_bits": warning_bits.get("active_bits", []),
            "warning_bitmap": snapshot.get("warning_bitmap"),
            "flag_blob": snapshot.get("flag_blob"),
        },
        "live": {
            "ac_input_voltage_v": _metric(
                snapshot.get("ac_input_voltage_v"), "V", "exact"
            ),
            "ac_input_frequency_hz": _metric(
                snapshot.get("ac_input_frequency_hz"), "Hz", "exact"
            ),
            "ac_output_voltage_v": _metric(
                snapshot.get("ac_output_voltage_v"), "V", "exact"
            ),
            "ac_output_frequency_hz": _metric(
                snapshot.get("ac_output_frequency_hz"), "Hz", "exact"
            ),
            "ac_output_active_power_w": _metric(
                snapshot.get("ac_output_active_power_w"), "W", "exact"
            ),
            "ac_output_apparent_power_va": _metric(
                snapshot.get("ac_output_apparent_power_va"), "VA", "exact"
            ),
            "ac_output_load_percent": _metric(
                snapshot.get("ac_output_load_percent"), "%", "exact"
            ),
            "battery_voltage_v": _metric(
                snapshot.get("battery_voltage_v"), "V", "exact"
            ),
            "battery_state_of_charge_percent": _metric(
                snapshot.get("battery_state_of_charge_percent"), "%", "exact"
            ),
            "battery_charge_current_a": _metric(
                snapshot.get("battery_charge_current_a"), "A", "exact"
            ),
            "battery_discharge_current_a": _metric(
                snapshot.get("battery_discharge_current_a"), "A", "exact"
            ),
            "total_charging_current_a": _metric(
                snapshot.get("total_charging_current_a"), "A", "exact"
            ),
            "battery_charge_power_w": _metric(
                snapshot.get("battery_charge_power_w"),
                "W",
                semantics.get("battery_charge_power_w", "derived"),
            ),
            "battery_discharge_power_w": _metric(
                snapshot.get("battery_discharge_power_w"),
                "W",
                semantics.get("battery_discharge_power_w", "derived"),
            ),
            "pv_input_voltage_v": _metric(
                snapshot.get("pv_input_voltage_v"), "V", "exact"
            ),
            "pv_input_current_a": _metric(
                snapshot.get("pv_input_current_a"), "A", "exact"
            ),
            "pv_power_w": _metric(
                snapshot.get("pv_power_w"),
                "W",
                semantics.get("pv_power_w", "derived"),
            ),
            "pv_charging_power_w": _metric(
                snapshot.get("pv_charging_power_w"),
                "W",
                "exact",
            ),
            "solar_feed_to_grid_power_w": _metric(
                snapshot.get("solar_feed_to_grid_power_w"), "W", "exact"
            ),
            "total_ac_output_apparent_power_va": _metric(
                snapshot.get("total_ac_output_apparent_power_va"), "VA", "exact"
            ),
            "total_output_active_power_w": _metric(
                snapshot.get("total_output_active_power_w"), "W", "exact"
            ),
            "total_output_load_percent": _metric(
                snapshot.get("total_output_load_percent"), "%", "exact"
            ),
            "max_charging_current_set_a": _metric(
                snapshot.get("max_charging_current_set_a"), "A", "exact"
            ),
            "max_charging_current_possible_a": _metric(
                snapshot.get("max_charging_current_possible_a"), "A", "exact"
            ),
            "max_ac_charging_current_set_a": _metric(
                snapshot.get("max_ac_charging_current_set_a"), "A", "exact"
            ),
            "bus_voltage_v": _metric(
                snapshot.get("bus_voltage_v"), "V", "exact"
            ),
            "inverter_temperature_c": _metric(
                snapshot.get("inverter_temperature_c"), "°C", "exact"
            ),
            "battery_voltage_from_scc_v": _metric(
                snapshot.get("battery_voltage_from_scc_v"), "V", "exact"
            ),
            "solar_to_house_power_w": _metric(
                live_flow["produced_to_house"], "W", "derived"
            ),
            "solar_to_battery_power_w": _metric(
                live_flow["produced_to_battery"], "W", "derived"
            ),
            "battery_to_house_power_w": _metric(
                live_flow["consumed_from_battery"], "W", "derived"
            ),
            "grid_to_house_power_w": _metric(
                live_flow["consumed_from_grid"], "W", "derived"
            ),
            "grid_to_battery_power_w": _metric(
                live_flow["battery_charged_from_grid"], "W", "derived"
            ),
            "battery_state": snapshot.get("battery_state")
            or inverter_status.get("battery_state"),
            "output_source_priority": qpiri.get("output_source_priority"),
            "battery_charger_source_priority": snapshot.get(
                "battery_charger_source_priority"
            ),
            "status_bits": inverter_status.get("raw"),
        },
        "pricing": {
            "grid_price_eur_per_kwh": pricing["grid_price_eur_per_kwh"],
            "feed_in_revenue_eur_per_kwh": pricing["feed_in_revenue_eur_per_kwh"],
            "source": pricing["source"],
            "tempo_available": pricing["tempo_available"],
            "tempo_tariff_label": pricing["tariff_label"],
            "tempo_color": pricing["color_label"],
            "tempo_tomorrow_color": pricing["tomorrow_color_label"],
            "tempo_display": pricing["display"],
        },
    }
    if stale:
        _zero_stale_live_payload(payload)
    else:
        payload["live_values_zeroed"] = False
    if include_capabilities:
        payload["capabilities"] = current["capabilities"]
    return payload


def _dashboard_live_payload():
    return _dashboard_live_payload_from_current(
        get_current_snapshot(
            _open_db(),
            include_cumulative=False,
            include_capabilities=False,
        ),
        include_capabilities=False,
    )


def _serialized_high_res_for_day(db, local_day):
    max_points = _graph_max_points()
    live_local_day = _now_local().strftime("%Y-%m-%d")
    rows = _aggregated_history_samples(
        db,
        local_day=local_day,
        max_points=max_points,
        table=(
            "minute_samples"
            if _prefer_minute_rollup_for_day(db, local_day, max_points)
            else ("samples" if local_day == live_local_day else "history_samples")
        ),
    )
    if not rows:
        return ""
    data = []
    for row in rows:
        row_data = dict(row)
        flow = calculate_power_flow_breakdown(row_data)
        data.append(
            [
                _to_local(datetime.fromisoformat(row_data["recorded_at"])).strftime(
                    "%H:%M:%S"
                ),
                round(_safe_float(row_data["pv_power_w"]) / 1000.0, 3),
                round(_safe_float(row_data["ac_output_active_power_w"]) / 1000.0, 3),
                round(_safe_float(flow["battery_to_load_power_w"]) / 1000.0, 3),
                round(_safe_float(flow["grid_to_load_power_w"]) / 1000.0, 3),
            ]
        )
    return json.dumps(data)


def _pretty_json(payload):
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True)


def _history_bucket_key(bucket):
    mapping = {
        "day": "days",
        "month": "months",
        "year": "years",
        "all": "all_time",
    }
    try:
        return mapping[bucket]
    except KeyError as exc:
        raise ValueError(f"Unsupported history bucket {bucket}") from exc


def _breakdown_bucket_key(bucket):
    mapping = {
        "day": "days",
        "month": "months",
        "year": "years",
    }
    try:
        return mapping[bucket]
    except KeyError as exc:
        raise ValueError(f"Unsupported breakdown bucket {bucket}") from exc


def _energy_period_filter(table, search_date):
    if table == "days":
        return "WHERE local_day = ?", [search_date]
    if table == "months":
        return "WHERE local_month = ?", [search_date]
    if table == "years":
        return "WHERE local_year = ?", [search_date]
    if table == "all_time":
        return "", []
    raise ValueError(f"Unsupported history bucket {table}")


def _query_energy_totals(db, table, search_date):
    bucket = {
        "days": "day",
        "months": "month",
        "years": "year",
        "all_time": "all_time",
    }[table]
    totals = get_bucket_totals(
        db,
        bucket,
        None if bucket == "all_time" else search_date,
    )
    return {
        "interval_count": int(totals.get("interval_count") or 0),
        "produced": _safe_float(totals.get("pv_energy_kwh")),
        "consumed": _safe_float(totals.get("load_energy_kwh")),
        "fed_in": _safe_float(totals.get("grid_export_energy_kwh")),
        "battery_charge": _safe_float(totals.get("battery_charge_energy_kwh")),
        "battery_discharge": _safe_float(
            totals.get("battery_discharge_energy_kwh")
        ),
        "pv_to_load": _safe_float(totals.get("pv_to_load_energy_kwh")),
        "pv_to_battery": _safe_float(totals.get("pv_to_battery_energy_kwh")),
        "battery_to_load": _safe_float(totals.get("battery_to_load_energy_kwh")),
        "grid_to_load": _safe_float(totals.get("grid_to_load_energy_kwh")),
        "grid_to_battery": _safe_float(totals.get("grid_to_battery_energy_kwh")),
        "earned_feed_in_eur": _safe_float(totals.get("earned_feed_in_eur")),
        "earned_savings_eur": _safe_float(totals.get("earned_savings_eur")),
    }


def _history_payload(
    produced,
    consumed,
    fed_in,
    battery_charge,
    battery_discharge,
    pricing=None,
):
    pricing = pricing or _pricing_context()
    price = pricing["grid_price_eur_per_kwh"]
    revenue = pricing["feed_in_revenue_eur_per_kwh"]
    breakdown = estimate_site_flow(
        produced,
        consumed,
        fed_in,
        battery_charge,
        battery_discharge,
    )

    consumed_total = breakdown["consumed"]
    consumed_from_pv = breakdown["solar_to_load_estimate"]
    consumed_from_battery = breakdown["battery_to_load_estimate"]
    consumed_from_grid = breakdown["grid_to_load_estimate"]
    used_on_site = breakdown["solar_used_on_site"]
    produced_to_battery = breakdown["solar_to_battery_estimate"]

    earned = breakdown["fed_in"] * revenue
    saved = (consumed_from_pv + consumed_from_battery) * price

    return {
        "produced_kwh": breakdown["produced"],
        "consumed_total_kwh": consumed_total,
        "consumed_from_pv_kwh": consumed_from_pv,
        "consumed_from_battery_kwh": consumed_from_battery,
        "consumed_from_grid_kwh": consumed_from_grid,
        "produced_to_house_kwh": consumed_from_pv,
        "produced_to_battery_kwh": produced_to_battery,
        "consumed_from_pv_percent": percent_or_default(
            consumed_from_pv, consumed_total, 0.0
        ),
        "consumed_from_battery_percent": percent_or_default(
            consumed_from_battery, consumed_total, 0.0
        ),
        "consumed_from_grid_percent": percent_or_default(
            consumed_from_grid, consumed_total, 0.0
        ),
        "usage_fed_in_kwh": breakdown["fed_in"],
        "usage_self_consumed_kwh": used_on_site,
        "usage_fed_in_percent": percent_or_default(
            breakdown["fed_in"], breakdown["produced"], 0.0
        ),
        "usage_self_consumed_percent": percent_or_default(
            used_on_site, breakdown["produced"], 100.0
        ),
        "battery_charge_kwh": breakdown["battery_charge"],
        "battery_discharge_kwh": breakdown["battery_discharge"],
        "battery_charge_from_pv_kwh": produced_to_battery,
        "battery_charge_from_grid_kwh": max(
            breakdown["battery_charge"] - produced_to_battery,
            0.0,
        ),
        "usage_to_house_percent": percent_or_default(
            consumed_from_pv, breakdown["produced"], 0.0
        ),
        "usage_to_battery_percent": percent_or_default(
            produced_to_battery, breakdown["produced"], 0.0
        ),
        "locally_supplied_kwh": breakdown["local_supply_estimate"],
        "earned_feedin": earned,
        "earned_savings": saved,
        "earned_total": earned + saved,
        "autarky": percent_or_default(
            breakdown["local_supply_estimate"], consumed_total, 100.0
        ),
        "current_grid_price_eur_per_kwh": price,
        "pricing_source": pricing["source"],
        "tempo_available": pricing["tempo_available"],
        "tempo_tariff_label": pricing["tariff_label"],
        "tempo_color": pricing["color_label"],
        "consumption_breakdown_is_estimated": True,
        "consumption_breakdown_note": (
            "PV, battery and grid shares are estimated from inverter load, "
            "PV, export, battery charge and battery discharge."
        ),
    }


def _history_payload_from_totals(totals, pricing=None):
    pricing = pricing or _pricing_context()
    price = pricing["grid_price_eur_per_kwh"]
    revenue = pricing["feed_in_revenue_eur_per_kwh"]

    produced = _safe_float(totals.get("produced"))
    consumed = _safe_float(totals.get("consumed"))
    fed_in = _safe_float(totals.get("fed_in"))
    consumed_from_pv = _safe_float(totals.get("pv_to_load"))
    consumed_from_battery = _safe_float(totals.get("battery_to_load"))
    consumed_from_grid = _safe_float(totals.get("grid_to_load"))
    produced_to_battery = _safe_float(totals.get("pv_to_battery"))
    battery_charge = _safe_float(totals.get("battery_charge"))
    battery_discharge = _safe_float(totals.get("battery_discharge"))
    battery_charge_from_grid = _safe_float(totals.get("grid_to_battery"))
    used_on_site = consumed_from_pv + produced_to_battery
    local_supply = consumed_from_pv + consumed_from_battery

    earned = _safe_float(totals.get("earned_feed_in_eur"))
    saved = _safe_float(totals.get("earned_savings_eur"))

    return {
        "produced_kwh": produced,
        "consumed_total_kwh": consumed,
        "consumed_from_pv_kwh": consumed_from_pv,
        "consumed_from_battery_kwh": consumed_from_battery,
        "consumed_from_grid_kwh": consumed_from_grid,
        "produced_to_house_kwh": consumed_from_pv,
        "produced_to_battery_kwh": produced_to_battery,
        "consumed_from_pv_percent": percent_or_default(
            consumed_from_pv,
            consumed,
            0.0,
        ),
        "consumed_from_battery_percent": percent_or_default(
            consumed_from_battery,
            consumed,
            0.0,
        ),
        "consumed_from_grid_percent": percent_or_default(
            consumed_from_grid,
            consumed,
            0.0,
        ),
        "usage_fed_in_kwh": fed_in,
        "usage_self_consumed_kwh": used_on_site,
        "usage_fed_in_percent": percent_or_default(fed_in, produced, 0.0),
        "usage_self_consumed_percent": percent_or_default(
            used_on_site,
            produced,
            100.0,
        ),
        "battery_charge_kwh": battery_charge,
        "battery_discharge_kwh": battery_discharge,
        "battery_charge_from_pv_kwh": produced_to_battery,
        "battery_charge_from_grid_kwh": battery_charge_from_grid,
        "usage_to_house_percent": percent_or_default(consumed_from_pv, produced, 0.0),
        "usage_to_battery_percent": percent_or_default(
            produced_to_battery,
            produced,
            0.0,
        ),
        "locally_supplied_kwh": local_supply,
        "earned_feedin": earned,
        "earned_savings": saved,
        "earned_total": earned + saved,
        "autarky": percent_or_default(local_supply, consumed, 100.0),
        "current_grid_price_eur_per_kwh": price,
        "pricing_source": pricing["source"],
        "tempo_available": pricing["tempo_available"],
        "tempo_tariff_label": pricing["tariff_label"],
        "tempo_color": pricing["color_label"],
        "consumption_breakdown_is_estimated": False,
        "consumption_breakdown_note": (
            "PV, battery and grid shares are derived from interval-level inverter telemetry."
        ),
    }


def _zero_history_totals():
    return {
        "interval_count": 0,
        "produced": 0.0,
        "consumed": 0.0,
        "fed_in": 0.0,
        "battery_charge": 0.0,
        "battery_discharge": 0.0,
        "pv_to_load": 0.0,
        "pv_to_battery": 0.0,
        "battery_to_load": 0.0,
        "grid_to_load": 0.0,
        "grid_to_battery": 0.0,
        "earned_feed_in_eur": 0.0,
        "earned_savings_eur": 0.0,
    }


def _zero_current_period_payload(db, table, search_date):
    if not _period_includes_present(table, search_date):
        return None

    current = get_current_snapshot(db, include_capabilities=False)
    if not current or not _snapshot_is_stale(current.get("recorded_at")):
        return None

    pricing = _pricing_context(db=db, current=current)
    return {
        **_history_payload_from_totals(_zero_history_totals(), pricing=pricing),
        **_period_completeness(db, table, search_date),
        "history_values_zeroed": True,
    }


def _history_payload_from_derived(db, table, search_date):
    totals = _query_energy_totals(db, table, search_date)
    if not totals or totals["interval_count"] <= 0:
        return _zero_current_period_payload(db, table, search_date)
    current = get_current_snapshot(db, include_capabilities=False)
    pricing = _pricing_context(db=db, current=current)
    if _period_includes_present(table, search_date):
        totals = _extend_aggregated_totals_with_live_projection(
            totals,
            current,
            pricing,
        )
    completeness = _period_completeness(db, table, search_date)
    if any(
        key in totals
        for key in (
            "pv_to_load",
            "pv_to_battery",
            "battery_to_load",
            "grid_to_load",
            "grid_to_battery",
        )
    ):
        payload = _history_payload_from_totals(totals, pricing=pricing)
    else:
        payload = _history_payload(
            totals["produced"],
            totals["consumed"],
            totals["fed_in"],
            totals["battery_charge"],
            totals["battery_discharge"],
            pricing=pricing,
        )
    return {
        **payload,
        **completeness,
    }


def _sorted_distinct_summary_values(db, table_name, column_name):
    rows = db.execute(
        f"""
        SELECT DISTINCT {column_name} AS value
        FROM {table_name}
        WHERE {column_name} IS NOT NULL
        ORDER BY {column_name} ASC
        """
    )
    return [row["value"] for row in rows if row and row["value"] is not None]


def _day_availability_payload(day_values):
    years = set()
    months_by_year = {}
    days_by_month = {}

    for day_value in day_values:
        year_text, month_text, day_text = day_value.split("-")
        years.add(int(year_text))
        months_by_year.setdefault(year_text, set()).add(int(month_text))
        days_by_month.setdefault(f"{year_text}-{month_text}", set()).add(int(day_text))

    return {
        "values": day_values,
        "years": sorted(years),
        "months_by_year": {
            year: sorted(months)
            for year, months in sorted(months_by_year.items())
        },
        "days_by_month": {
            month: sorted(days)
            for month, days in sorted(days_by_month.items())
        },
        "min": day_values[0] if day_values else None,
        "max": day_values[-1] if day_values else None,
    }


def _month_availability_payload(month_values):
    years = set()
    months_by_year = {}

    for month_value in month_values:
        year_text, month_text = month_value.split("-")
        years.add(int(year_text))
        months_by_year.setdefault(year_text, set()).add(int(month_text))

    return {
        "values": month_values,
        "years": sorted(years),
        "months_by_year": {
            year: sorted(months)
            for year, months in sorted(months_by_year.items())
        },
        "min": month_values[0] if month_values else None,
        "max": month_values[-1] if month_values else None,
    }


def _year_availability_payload(year_values):
    return {
        "values": year_values,
        "min": year_values[0] if year_values else None,
        "max": year_values[-1] if year_values else None,
    }


def _include_current_period_for_stale_live_data(
    db,
    day_values,
    month_values,
    year_values,
):
    current = get_current_snapshot(
        db,
        include_cumulative=False,
        include_capabilities=False,
    )
    if not current or not _snapshot_is_stale(current.get("recorded_at")):
        return day_values, month_values, year_values

    now = _now_local()
    recorded_at = datetime.fromisoformat(current["recorded_at"]).astimezone(now.tzinfo)
    if (now - recorded_at) > timedelta(days=2):
        return day_values, month_values, year_values

    return (
        sorted({*day_values, now.strftime("%Y-%m-%d")}),
        sorted({*month_values, now.strftime("%Y-%m")}),
        sorted({*year_values, now.year}),
    )


def _date_bounds_payload(db):
    configured_year = _configured_start_date().year
    current_year = _now_local().year
    day_values = _sorted_distinct_summary_values(db, "energy_summary_days", "local_day")
    month_values = _sorted_distinct_summary_values(
        db, "energy_summary_months", "local_month"
    )
    year_values = [
        int(value)
        for value in _sorted_distinct_summary_values(
            db, "energy_summary_years", "local_year"
        )
    ]

    if not month_values and day_values:
        month_values = sorted({day_value[:7] for day_value in day_values})
    if not year_values and month_values:
        year_values = sorted({int(month_value[:4]) for month_value in month_values})
    if not year_values and day_values:
        year_values = sorted({int(day_value[:4]) for day_value in day_values})

    day_values, month_values, year_values = _include_current_period_for_stale_live_data(
        db,
        day_values,
        month_values,
        year_values,
    )

    year_min = min(year_values) if year_values else configured_year
    year_max = max(year_values) if year_values else current_year
    return {
        "state": "ok",
        "year_min": min(year_min, year_max),
        "year_max": max(year_min, year_max),
        "available_days": _day_availability_payload(day_values),
        "available_months": _month_availability_payload(month_values),
        "available_years": _year_availability_payload(year_values),
    }


def _statistics_best_period(db, bucket_key):
    bucket = {
        "days": "day",
        "months": "month",
        "years": "year",
    }[bucket_key]
    return get_best_bucket_total(db, bucket)


def _statistics_payload(db):
    now_local = _now_local()
    today_local = now_local.date()
    start_date = _start_of_operation_date(db, reference_time=now_local)
    days_of_operation = max((today_local - start_date).days, 1)
    all_time_totals = _query_energy_totals(db, "all_time", "all_time") or {}
    average_daily_production = _safe_float(all_time_totals.get("produced")) / days_of_operation

    best_day = _statistics_best_period(db, "days")
    best_month = _statistics_best_period(db, "months")
    best_year = _statistics_best_period(db, "years")
    peak_candidates = []
    for table_name in ("samples", "compressed_samples_10m"):
        row = db.fetchone(
            f"""
            SELECT recorded_at, pv_power_w
            FROM {table_name}
            WHERE pv_power_w IS NOT NULL
            ORDER BY pv_power_w DESC, recorded_at ASC
            LIMIT 1
            """
        )
        if row and row["recorded_at"] is not None:
            peak_candidates.append(row)
    peak_row = (
        min(
            peak_candidates,
            key=lambda row: (-_safe_float(row["pv_power_w"]), row["recorded_at"]),
        )
        if peak_candidates
        else None
    )

    highest_production_date = "..."
    highest_production_w = 0.0
    if peak_row and peak_row["recorded_at"]:
        highest_production_date = (
            _to_local(datetime.fromisoformat(peak_row["recorded_at"])).date().isoformat()
        )
        highest_production_w = _safe_float(peak_row["pv_power_w"])

    return {
        "state": "ok",
        "start_of_operation": str(start_date),
        "days_of_operation": days_of_operation,
        "average_daily_production_kwh": average_daily_production,
        "best_day_date": best_day["bucket"] if best_day else "...",
        "best_day_production_kwh": _safe_float(best_day["produced_kwh"]) if best_day else 0.0,
        "best_month_date": best_month["bucket"] if best_month else "...",
        "best_month_production_kwh": _safe_float(best_month["produced_kwh"]) if best_month else 0.0,
        "best_year_date": best_year["bucket"] if best_year else "...",
        "best_year_production_kwh": _safe_float(best_year["produced_kwh"]) if best_year else 0.0,
        "highest_production_w": highest_production_w,
        "highest_production_date": highest_production_date,
    }


def _breakdown_items(db, bucket_key, search_prefix):
    bucket = {
        "days": "day",
        "months": "month",
        "years": "year",
    }[bucket_key]
    rows = get_grouped_cumulative(db, bucket, 100000, search_prefix)["items"]
    items = []
    for row in rows:
        produced_to_house = _safe_float(row["pv_to_load_energy_kwh"])
        produced_to_battery = _safe_float(row["pv_to_battery_energy_kwh"])
        items.append(
            {
                "date": row["bucket"],
                "produced_self": produced_to_house + produced_to_battery,
                "produced_to_house": produced_to_house,
                "produced_to_battery": produced_to_battery,
                "produced_feed_in": _safe_float(row["grid_export_energy_kwh"]),
                "consumed_from_pv": produced_to_house,
                "consumed_from_battery": _safe_float(
                    row["battery_to_load_energy_kwh"]
                ),
                "consumed_from_grid": _safe_float(row["grid_to_load_energy_kwh"]),
            }
        )
    return items


def _breakdown_payload(db, bucket, search_prefix):
    return {
        "state": "ok",
        "items": _breakdown_items(db, _breakdown_bucket_key(bucket), search_prefix),
    }


def _live_chart_payload(db, hours):
    return _live_chart_payload_at(db, hours, reference_time=datetime.now(timezone.utc))


def _live_chart_spans_multiple_local_days(hours, reference_time):
    reference_time = reference_time.astimezone(timezone.utc)
    hours = max(int(hours), 1)
    since_local_day = _to_local(reference_time - timedelta(hours=hours)).strftime(
        "%Y-%m-%d"
    )
    current_local_day = _to_local(reference_time).strftime("%Y-%m-%d")
    return since_local_day != current_local_day


def _aggregated_cross_day_live_samples(
    db,
    *,
    since_iso,
    current_local_day,
    recent_table,
    max_points,
):
    bounds = db.fetchone(
        f"""
        WITH filtered AS (
            SELECT recorded_at
            FROM compressed_samples_10m
            WHERE recorded_at >= ?
            UNION ALL
            SELECT recorded_at
            FROM {recent_table}
            WHERE recorded_at >= ?
              AND local_day = ?
        )
        SELECT
            COUNT(*) AS sample_count,
            MIN(recorded_at) AS first_recorded_at,
            MAX(recorded_at) AS last_recorded_at
        FROM filtered
        """,
        [since_iso, since_iso, current_local_day],
    )
    sample_count = int((dict(bounds) if bounds else {}).get("sample_count") or 0)
    if sample_count <= 0:
        return []

    if sample_count <= max_points:
        return db.execute(
            f"""
            SELECT
                recorded_at,
                pv_power_w,
                ac_output_active_power_w,
                battery_charge_power_w,
                battery_discharge_power_w,
                solar_feed_to_grid_power_w
            FROM compressed_samples_10m
            WHERE recorded_at >= ?
            UNION ALL
            SELECT
                recorded_at,
                pv_power_w,
                ac_output_active_power_w,
                battery_charge_power_w,
                battery_discharge_power_w,
                solar_feed_to_grid_power_w
            FROM {recent_table}
            WHERE recorded_at >= ?
              AND local_day = ?
            ORDER BY recorded_at ASC
            """,
            [since_iso, since_iso, current_local_day],
        )

    first_recorded_at = datetime.fromisoformat(bounds["first_recorded_at"])
    last_recorded_at = datetime.fromisoformat(bounds["last_recorded_at"])
    total_seconds = max((last_recorded_at - first_recorded_at).total_seconds(), 1.0)
    bucket_seconds = max(int(math.ceil(total_seconds / float(max_points))), 1)
    return db.execute(
        f"""
        WITH filtered AS (
            SELECT
                recorded_at,
                pv_power_w,
                ac_output_active_power_w,
                battery_charge_power_w,
                battery_discharge_power_w,
                solar_feed_to_grid_power_w
            FROM compressed_samples_10m
            WHERE recorded_at >= ?
            UNION ALL
            SELECT
                recorded_at,
                pv_power_w,
                ac_output_active_power_w,
                battery_charge_power_w,
                battery_discharge_power_w,
                solar_feed_to_grid_power_w
            FROM {recent_table}
            WHERE recorded_at >= ?
              AND local_day = ?
        ),
        bucketed AS (
            SELECT
                recorded_at,
                pv_power_w,
                ac_output_active_power_w,
                battery_charge_power_w,
                battery_discharge_power_w,
                solar_feed_to_grid_power_w,
                CAST(
                    ((julianday(recorded_at) - julianday(?)) * 86400.0) / ?
                    AS INTEGER
                ) AS bucket_index
            FROM filtered
        )
        SELECT
            MAX(recorded_at) AS recorded_at,
            AVG(pv_power_w) AS pv_power_w,
            AVG(ac_output_active_power_w) AS ac_output_active_power_w,
            AVG(battery_charge_power_w) AS battery_charge_power_w,
            AVG(battery_discharge_power_w) AS battery_discharge_power_w,
            AVG(solar_feed_to_grid_power_w) AS solar_feed_to_grid_power_w
        FROM bucketed
        GROUP BY bucket_index
        ORDER BY recorded_at ASC
        """,
        [
            since_iso,
            since_iso,
            current_local_day,
            bounds["first_recorded_at"],
            bucket_seconds,
        ],
    )


def _live_chart_rows(db, *, hours, reference_time, max_points):
    hours = max(int(hours), 1)
    reference_time = reference_time.astimezone(timezone.utc)
    since_iso = (reference_time - timedelta(hours=hours)).isoformat()
    recent_table = "samples" if hours < 4 else "minute_samples"
    if _live_chart_spans_multiple_local_days(hours, reference_time):
        return _aggregated_cross_day_live_samples(
            db,
            since_iso=since_iso,
            current_local_day=_to_local(reference_time).strftime("%Y-%m-%d"),
            recent_table=recent_table,
            max_points=max_points,
        )
    return _aggregated_history_samples(
        db,
        since_iso=since_iso,
        max_points=max_points,
        table=recent_table,
    )


def _live_chart_payload_at(db, hours, *, reference_time):
    hours = max(int(hours), 1)
    reference_time = reference_time.astimezone(timezone.utc)
    rows = _live_chart_rows(
        db,
        hours=hours,
        reference_time=reference_time,
        max_points=_graph_max_points(),
    )
    payload = []
    for row in reversed(rows):
        row_data = dict(row)
        flow = calculate_power_flow_breakdown(row_data)
        payload.append(
            [
                len(payload),
                _to_local(datetime.fromisoformat(row_data["recorded_at"])).strftime(
                    "%H:%M:%S"
                ),
                round(_safe_float(row_data["pv_power_w"]) / 1000.0, 3),
                round(_safe_float(row_data["ac_output_active_power_w"]) / 1000.0, 3),
                round(_safe_float(flow["battery_to_load_power_w"]) / 1000.0, 3),
                round(_safe_float(flow["grid_to_load_power_w"]) / 1000.0, 3),
            ]
        )
    return {
        "state": "ok" if payload else "nodata",
        "series": payload,
    }


def _period_history_payload(db, bucket, search_date):
    table_key = _history_bucket_key(bucket)
    normalized_search = "all_time" if table_key == "all_time" else search_date
    if table_key != "all_time" and not normalized_search:
        raise ValueError(f"Missing date for history bucket {bucket}")

    derived_payload = _history_payload_from_derived(db, table_key, normalized_search)
    if derived_payload is None:
        return {"state": "nodata"}

    return {
        "state": "ok",
        **derived_payload,
        "high_res": (
            _serialized_high_res_for_day(db, normalized_search)
            if table_key == "days"
            else ""
        ),
    }


def _grouped_energy_csv_rows(db, bucket_key, search_prefix):
    rows = get_grouped_cumulative(db, bucket_key, 100000, search_prefix)["items"]
    return [
        {
            "date": row["bucket"],
            "production": row["pv_energy_kwh"],
            "consumption": row["load_energy_kwh"],
            "feed_in": row["grid_export_energy_kwh"],
        }
        for row in rows
    ]


def _safe_csv_filename_part(value, fallback):
    text = str(value or fallback)
    cleaned = "".join(
        char if char.isalnum() or char in {"-", "_", "."} else "_"
        for char in text
    ).strip("._")
    return (cleaned or fallback)[:64]


def _bounded_query_int(name, default, *, min_value=1, max_value=None):
    raw_value = request.args.get(name)
    if raw_value in {None, ""}:
        return default
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid integer for {name}") from None

    value = max(value, min_value)
    if max_value is not None:
        value = min(value, max_value)
    return value


@app.route("/")
def get_index():
    response = send_from_directory(str(SITE_DIR), "index.html")
    return _apply_static_cache_headers(response, "index.html")


@app.route("/<path:path>")
def get_file(path):
    response = send_from_directory(str(SITE_DIR), path)
    return _apply_static_cache_headers(response, path)


@app.route("/name", methods=["GET"])
def handle_name():
    return jsonify(_instance_name())


@app.route("/api/overview", methods=["GET"])
def api_overview():
    compact = request.args.get("compact", "").lower() in {"1", "true", "yes"}
    return jsonify(_overview_payload(compact=compact))


@app.route("/api/live", methods=["GET"])
def api_live():
    payload = _dashboard_live_payload()
    if payload["state"] != "ok":
        return jsonify(payload), 404
    return jsonify(
        {
            **payload,
            "metrics": payload["live"],
            "semantics": {
                key: value["semantics"]
                for key, value in payload["live"].items()
                if isinstance(value, dict) and "semantics" in value
            },
        }
    )


@app.route("/api/tempo", methods=["GET"])
def api_tempo():
    pricing = _pricing_context(db=_open_db())
    return jsonify(
        {
            "state": "ok" if pricing["tempo_available"] else "nodata",
            "grid_price_eur_per_kwh": pricing["grid_price_eur_per_kwh"],
            "feed_in_revenue_eur_per_kwh": pricing["feed_in_revenue_eur_per_kwh"],
            "source": pricing["source"],
            "tempo_available": pricing["tempo_available"],
            "tempo_tariff_label": pricing["tariff_label"],
            "tempo_color": pricing["color_label"],
            "tempo_tomorrow_color": pricing["tomorrow_color_label"],
            "tempo_display": pricing["display"],
        }
    )


@app.route("/api/date-bounds", methods=["GET"])
def api_date_bounds():
    return jsonify(_date_bounds_payload(_open_db()))


@app.route("/api/statistics", methods=["GET"])
def api_statistics():
    return jsonify(_statistics_payload(_open_db()))


@app.route("/api/chart/live", methods=["GET"])
def api_chart_live():
    try:
        hours = _bounded_query_int("hours", 24, min_value=1, max_value=168)
    except ValueError as exc:
        return jsonify({"state": "error", "message": str(exc)}), 400
    payload = _live_chart_payload(_open_db(), hours)
    return jsonify(payload), (404 if payload["state"] == "nodata" else 200)


@app.route("/api/period", methods=["GET"])
def api_period():
    bucket = request.args.get("bucket", "day")
    search_date = request.args.get("date")
    try:
        payload = _period_history_payload(_open_db(), bucket, search_date)
    except ValueError as exc:
        return jsonify({"state": "error", "message": str(exc)}), 400
    return jsonify(payload), (404 if payload["state"] == "nodata" else 200)


@app.route("/api/breakdown", methods=["GET"])
def api_breakdown():
    bucket = request.args.get("bucket", "day")
    search_prefix = request.args.get("prefix")
    try:
        payload = _breakdown_payload(_open_db(), bucket, search_prefix)
    except ValueError as exc:
        return jsonify({"state": "error", "message": str(exc)}), 400
    return jsonify(payload)


@app.route("/api/history", methods=["GET"])
def api_history():
    metric = request.args.get("metric", "ac_output_active_power_w")
    try:
        hours = _bounded_query_int("hours", 24, min_value=1, max_value=168)
        max_points = _bounded_query_int(
            "max_points",
            _graph_max_points(),
            min_value=1,
            max_value=1000,
        )
    except ValueError as exc:
        return jsonify({"state": "error", "message": str(exc)}), 400
    try:
        data = get_history_series(_open_db(), metric, hours, max_points=max_points)
    except KeyError:
        return jsonify({"state": "error", "message": f"Unsupported metric {metric}"}), 400
    return jsonify({"state": "ok", **data})


@app.route("/api/cumulative", methods=["GET"])
def api_cumulative():
    bucket = request.args.get("bucket", "day")
    try:
        limit = _bounded_query_int("limit", 30, min_value=1, max_value=3650)
    except ValueError as exc:
        return jsonify({"state": "error", "message": str(exc)}), 400
    try:
        data = get_grouped_cumulative(_open_db(), bucket, limit)
    except ValueError as exc:
        return jsonify({"state": "error", "message": str(exc)}), 400
    return jsonify({"state": "ok", **data})


@app.route("/api/diagnostics", methods=["GET"])
def api_diagnostics():
    if not _diagnostics_enabled():
        return jsonify({"state": "disabled"}), 404

    db = _open_db()
    current = get_current_snapshot(db)
    if not current:
        return jsonify({"state": "nodata"}), 404
    snapshot = current["snapshot"]
    return jsonify(
        {
            "state": "ok",
            "recorded_at": current["recorded_at"],
            "device": {
                "serial_number": snapshot.get("serial_number"),
                "device_id": snapshot.get("device_id"),
                "protocol_id": snapshot.get("protocol_id"),
                "operation_mode": snapshot.get("operation_mode"),
                "fault": snapshot.get("fault"),
                "raw_inverter_status": (snapshot.get("inverter_status") or {}).get("raw"),
                "warning_bitmap": snapshot.get("warning_bitmap"),
                "flag_blob": snapshot.get("flag_blob"),
            },
            "capabilities": get_capabilities(db),
            "qpiri": snapshot.get("qpiri"),
            "inverter_status": snapshot.get("inverter_status"),
            "qpigs_status_flags": snapshot.get("qpigs_status_flags"),
            "device_status2": snapshot.get("device_status2"),
            "raw_snapshot": snapshot,
            "raw_text": _pretty_json(
                {
                    "recorded_at": current["recorded_at"],
                    "snapshot": snapshot,
                    "capabilities": current.get("capabilities"),
                    "cumulative": current.get("cumulative"),
                }
            ),
        }
    )


@app.route("/api/csv", methods=["GET"])
def api_csv():
    db = _open_db()
    bucket = request.args.get("bucket")
    prefix = request.args.get("prefix", "")
    if bucket:
        try:
            rows = _grouped_energy_csv_rows(db, bucket, prefix)
        except KeyError:
            return jsonify({"state": "error", "message": f"Unsupported CSV bucket {bucket}"}), 400

        handle = io.StringIO()
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(["date", "production", "consumption", "feed_in"])
        for row in rows:
            writer.writerow(
                [
                    row["date"],
                    row["production"],
                    row["consumption"],
                    row["feed_in"],
                ]
            )
        scope = prefix or "all"
        filename_bucket = _safe_csv_filename_part(bucket, "data")
        filename_scope = _safe_csv_filename_part(scope, "all")
        response = make_response(handle.getvalue())
        response.headers["Content-Disposition"] = (
            f"attachment; filename=phocos_{filename_bucket}_{filename_scope}.csv"
        )
        response.mimetype = "text/csv"
        return response

    start = request.args.get("start")
    end = request.args.get("end")
    rows = csv_rows_for_samples(db, start, end)
    handle = io.StringIO()
    writer = csv.writer(handle, delimiter=";")
    writer.writerow(
        [
            "recorded_at",
            "operation_mode",
            "fault",
            "ac_input_voltage_v",
            "ac_output_voltage_v",
            "ac_output_active_power_w",
            "ac_output_load_percent",
            "battery_voltage_v",
            "battery_state_of_charge_percent",
            "battery_charge_current_a",
            "battery_discharge_current_a",
            "pv_input_voltage_v",
            "pv_input_current_a",
            "pv_power_w",
            "pv_power_semantics",
            "solar_feed_to_grid_power_w",
        ]
    )
    for row in rows:
        writer.writerow(list(row))
    response = make_response(handle.getvalue())
    response.headers["Content-Disposition"] = (
        f"attachment; filename=phocos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )
    response.mimetype = "text/csv"
    return response


def main():
    global config, tempo_client

    os.makedirs(DATA_DIR, exist_ok=True)
    logging.basicConfig(
        filename=str(SERVER_LOG_PATH),
        filemode="w",
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.info("Starting PiPhocos server version %s", version.get_version())
    logging.info("Server: reading backend configuration from %s", CONFIG_PATH)
    config = Config(str(CONFIG_PATH))
    tempo_client = TempoApiClient(config)
    logging.getLogger().setLevel(config.log_level)
    db = _open_db()
    db.close()

    from waitress import serve

    serve(
        app,
        host=config.config_data["server"]["ip"],
        port=config.config_data["server"]["port"],
    )


if __name__ == "__main__":
    main()
