import json
import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from phocos_protocol import (
    SEMANTICS_CACHED,
    SEMANTICS_DERIVED,
    SEMANTICS_EXACT,
    SEMANTICS_UNSUPPORTED,
)


CURRENT_SNAPSHOT_SLOT = "current"
RAW_HISTORY_RETENTION_HOURS = 24
ARCHIVED_SAMPLE_BUCKET_MINUTES = 10
DEFAULT_ENERGY_INTERVAL_RETENTION_DAYS = 45
DEFAULT_ENERGY_INTERVAL_PRUNE_MAX_DAYS = 14

HISTORY_SAMPLE_COLUMNS = (
    "recorded_at",
    "recorded_minute",
    "local_day",
    "local_month",
    "local_year",
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
)

ARCHIVED_SAMPLE_AVERAGE_COLUMNS = (
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
    "solar_feed_to_grid_power_w",
)

METRIC_DEFINITIONS = {
    "ac_input_voltage_v": {
        "table": "history_samples",
        "column": "ac_input_voltage_v",
        "semantics": SEMANTICS_EXACT,
        "unit": "V",
        "label": "AC input voltage",
    },
    "ac_output_active_power_w": {
        "table": "history_samples",
        "column": "ac_output_active_power_w",
        "semantics": SEMANTICS_EXACT,
        "unit": "W",
        "label": "AC output power",
    },
    "ac_output_load_percent": {
        "table": "history_samples",
        "column": "ac_output_load_percent",
        "semantics": SEMANTICS_EXACT,
        "unit": "%",
        "label": "AC output load",
    },
    "load_percent": {
        "table": "history_samples",
        "column": "ac_output_load_percent",
        "semantics": SEMANTICS_EXACT,
        "unit": "%",
        "label": "AC output load",
    },
    "battery_voltage_v": {
        "table": "history_samples",
        "column": "battery_voltage_v",
        "semantics": SEMANTICS_EXACT,
        "unit": "V",
        "label": "Battery voltage",
    },
    "battery_state_of_charge_percent": {
        "table": "history_samples",
        "column": "battery_state_of_charge_percent",
        "semantics": SEMANTICS_EXACT,
        "unit": "%",
        "label": "Battery state of charge",
    },
    "battery_charge_current_a": {
        "table": "history_samples",
        "column": "battery_charge_current_a",
        "semantics": SEMANTICS_EXACT,
        "unit": "A",
        "label": "Battery charge current",
    },
    "battery_discharge_current_a": {
        "table": "history_samples",
        "column": "battery_discharge_current_a",
        "semantics": SEMANTICS_EXACT,
        "unit": "A",
        "label": "Battery discharge current",
    },
    "pv_input_voltage_v": {
        "table": "history_samples",
        "column": "pv_input_voltage_v",
        "semantics": SEMANTICS_EXACT,
        "unit": "V",
        "label": "PV voltage",
    },
    "pv_input_current_a": {
        "table": "history_samples",
        "column": "pv_input_current_a",
        "semantics": SEMANTICS_EXACT,
        "unit": "A",
        "label": "PV current",
    },
    "pv_power_w": {
        "table": "history_samples",
        "column": "pv_power_w",
        "semantics_column": "pv_power_semantics",
        "semantics": SEMANTICS_DERIVED,
        "unit": "W",
        "label": "PV power",
    },
    "solar_feed_to_grid_power_w": {
        "table": "history_samples",
        "column": "solar_feed_to_grid_power_w",
        "semantics": SEMANTICS_EXACT,
        "unit": "W",
        "label": "Solar feed to grid power",
    },
}

ENERGY_COLUMNS = (
    "pv_energy_kwh",
    "load_energy_kwh",
    "battery_charge_energy_kwh",
    "battery_discharge_energy_kwh",
    "grid_export_energy_kwh",
)

FLOW_ENERGY_COLUMNS = (
    "pv_to_load_energy_kwh",
    "pv_to_battery_energy_kwh",
    "battery_to_load_energy_kwh",
    "grid_to_load_energy_kwh",
    "grid_to_battery_energy_kwh",
)

ALL_ENERGY_COLUMNS = ENERGY_COLUMNS + FLOW_ENERGY_COLUMNS

CUMULATIVE_TOTAL_COLUMNS = ALL_ENERGY_COLUMNS + (
    "earned_feed_in_eur",
    "earned_savings_eur",
)

SUMMARY_ROLLUP_STATE_KEY = "energy_rollups_version"
SUMMARY_ROLLUP_VERSION = "1"
QUALITY_SUMMARY_ROLLUP_STATE_KEY = "energy_quality_rollups_version"
QUALITY_SUMMARY_ROLLUP_VERSION = "1"
FLOW_ENERGY_BACKFILL_STATE_KEY = "flow_energy_backfill_version"
FLOW_ENERGY_BACKFILL_VERSION = "2"
MAX_AUTOMATIC_FLOW_BACKFILL_ROWS = 50_000
MAX_AUTOMATIC_ARCHIVE_BUCKET_BACKFILL_ROWS = 50_000
SUMMARY_ROLLUP_TABLES = {
    "day": "energy_summary_days",
    "month": "energy_summary_months",
    "year": "energy_summary_years",
}
QUALITY_SUMMARY_DAYS_TABLE = "energy_quality_summary_days"
SUMMARY_ROLLUP_KEYS = {
    "day": "local_day",
    "month": "local_month",
    "year": "local_year",
}

SAMPLE_COLUMNS = (
    "recorded_at",
    "recorded_minute",
    "archive_bucket_local",
    "local_day",
    "local_month",
    "local_year",
    "serial_number",
    "protocol_id",
    "device_id",
    "operation_mode_code",
    "operation_mode",
    "fault_code",
    "fault",
    "ac_input_voltage_v",
    "ac_input_frequency_hz",
    "ac_output_voltage_v",
    "ac_output_frequency_hz",
    "ac_output_apparent_power_va",
    "ac_output_active_power_w",
    "ac_output_load_percent",
    "battery_voltage_v",
    "battery_charge_current_a",
    "battery_state_of_charge_percent",
    "pv_input_voltage_v",
    "total_charging_current_a",
    "total_ac_output_apparent_power_va",
    "total_output_active_power_w",
    "total_output_load_percent",
    "ac_output_mode_code",
    "ac_output_mode",
    "battery_charger_source_priority_code",
    "battery_charger_source_priority",
    "max_charging_current_set_a",
    "max_charging_current_possible_a",
    "max_ac_charging_current_set_a",
    "pv_input_current_a",
    "battery_discharge_current_a",
    "pv_power_w",
    "pv_power_semantics",
    "battery_charge_power_w",
    "battery_discharge_power_w",
    "bus_voltage_v",
    "inverter_temperature_c",
    "battery_voltage_from_scc_v",
    "pv_charging_power_w",
    "solar_feed_to_grid_power_w",
    "mppt_active",
    "ac_charging_on",
    "solar_charging_on",
    "battery_state_code",
    "battery_state",
    "ac_input_available",
    "ac_output_on",
    "inverter_status_raw",
    "inverter_status_json",
    "qpigs_status_flags_raw",
    "qpigs_status_flags_json",
    "device_status2_raw",
    "device_status2_json",
    "solar_feed_to_grid_enabled",
    "country_code",
    "qpiws_raw",
    "warnings_json",
    "qflag_raw",
    "flags_json",
    "qpiri_json",
    "metadata_json",
    "raw_snapshot_json",
)


def _json(value: Any) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(value, sort_keys=True)


def _bool_to_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    return 1 if bool(value) else 0


def _utc_from_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _archive_bucket_for_local(local: datetime) -> str:
    bucket_start = local.replace(
        minute=(local.minute // ARCHIVED_SAMPLE_BUCKET_MINUTES)
        * ARCHIVED_SAMPLE_BUCKET_MINUTES,
        second=0,
        microsecond=0,
    )
    return bucket_start.strftime("%Y-%m-%dT%H:%M")


def _local_parts(recorded_at: str) -> tuple[str, str, str, str, str]:
    local = _utc_from_iso(recorded_at).astimezone()
    return (
        local.strftime("%Y-%m-%dT%H:%M"),
        _archive_bucket_for_local(local),
        local.strftime("%Y-%m-%d"),
        local.strftime("%Y-%m"),
        local.strftime("%Y"),
    )


def _summary_reference_periods(
    reference_time: Optional[datetime] = None,
) -> tuple[str, str, str]:
    local = (reference_time or datetime.now(timezone.utc)).astimezone()
    return (
        local.strftime("%Y-%m-%d"),
        local.strftime("%Y-%m"),
        local.strftime("%Y"),
    )


def _summary_is_finalized(
    bucket: str,
    bucket_value: str,
    reference_time: Optional[datetime] = None,
) -> int:
    current_day, current_month, current_year = _summary_reference_periods(reference_time)
    if bucket == "day":
        return int(bucket_value < current_day)
    if bucket == "month":
        return int(bucket_value < current_month)
    if bucket == "year":
        return int(bucket_value < current_year)
    raise ValueError(f"Unsupported summary bucket {bucket}")


def _summary_totals_select(
    *,
    source_prefix: str = "",
    earned_from_prices: bool = False,
) -> str:
    prefix = f"{source_prefix}." if source_prefix else ""
    expressions = [
        f"COALESCE(SUM({prefix}{column}), 0.0) AS {column}"
        for column in ALL_ENERGY_COLUMNS
    ]
    if earned_from_prices:
        expressions.extend(
            (
                "COALESCE("
                f"SUM({prefix}grid_export_energy_kwh * {prefix}feed_in_revenue_eur_per_kwh), 0.0"
                ") AS earned_feed_in_eur",
                "COALESCE("
                f"SUM(({prefix}pv_to_load_energy_kwh + {prefix}battery_to_load_energy_kwh) * {prefix}grid_price_eur_per_kwh), 0.0"
                ") AS earned_savings_eur",
            )
        )
    else:
        expressions.extend(
            [
                f"COALESCE(SUM({prefix}earned_feed_in_eur), 0.0) AS earned_feed_in_eur",
                f"COALESCE(SUM({prefix}earned_savings_eur), 0.0) AS earned_savings_eur",
            ]
        )
    return ", ".join(expressions)


def _write_summary_row(db, table: str, row: dict[str, Any]):
    columns = list(row.keys())
    placeholders = ", ".join(["?"] * len(columns))
    db.execute(
        f"INSERT OR REPLACE INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
        [row[column] for column in columns],
    )


def _delete_summary_row(db, table: str, key_column: str, key_value: str):
    db.execute(f"DELETE FROM {table} WHERE {key_column} = ?", [key_value])


def _history_sample_stats_for_day(db, local_day: str) -> dict[str, Any]:
    row = db.fetchone(
        """
        SELECT
            COALESCE((SELECT COUNT(*) FROM samples WHERE local_day = ?), 0)
                + COALESCE((SELECT SUM(sample_count) FROM compressed_samples_10m WHERE local_day = ?), 0)
                AS sample_count,
            (
                SELECT MIN(recorded_at)
                FROM (
                    SELECT recorded_at FROM samples WHERE local_day = ?
                    UNION ALL
                    SELECT recorded_at FROM compressed_samples_10m WHERE local_day = ?
                )
            ) AS first_recorded_at,
            (
                SELECT MAX(recorded_at)
                FROM (
                    SELECT recorded_at FROM samples WHERE local_day = ?
                    UNION ALL
                    SELECT recorded_at FROM compressed_samples_10m WHERE local_day = ?
                )
            ) AS last_recorded_at
        """,
        [local_day, local_day, local_day, local_day, local_day, local_day],
    )
    return dict(row) if row else {}


def _aggregate_day_summary(db, local_day: str) -> dict[str, Any]:
    row = db.fetchone(
        f"""
        SELECT
            COUNT(*) AS interval_count,
            COALESCE(MAX(local_month), ?) AS local_month,
            COALESCE(MAX(local_year), ?) AS local_year,
            COALESCE(SUM(CASE WHEN contiguous = 1 THEN interval_seconds ELSE 0.0 END), 0.0)
                AS covered_seconds,
            COALESCE(
                SUM(
                    CASE
                        WHEN contiguous = 0 AND previous_recorded_at IS NOT NULL THEN 1
                        ELSE 0
                    END
                ),
                0
            ) AS missing_intervals,
            {_summary_totals_select(earned_from_prices=True)}
        FROM derived_energy_intervals
        WHERE local_day = ?
        """,
        [local_day[:7], local_day[:4], local_day],
    )
    return dict(row) if row else {}


def _reconciliation_quality_select(source_prefix: str = "") -> str:
    prefix = f"{source_prefix}." if source_prefix else ""
    return f"""
            COALESCE({prefix}quality, 'unknown') AS quality,
            COUNT(*) AS interval_count,
            COALESCE(SUM(CASE WHEN {prefix}contiguous = 1 THEN 1 ELSE 0 END), 0) AS integrated_interval_count,
            COALESCE(SUM(CASE WHEN {prefix}contiguous = 0 THEN 1 ELSE 0 END), 0) AS dropped_interval_count,
            COALESCE(SUM(CASE WHEN {prefix}contiguous = 1 THEN {prefix}interval_seconds ELSE 0.0 END), 0.0) AS integrated_seconds,
            COALESCE(SUM(CASE WHEN {prefix}contiguous = 0 AND {prefix}interval_seconds > 0 THEN {prefix}interval_seconds ELSE 0.0 END), 0.0) AS dropped_seconds,
            COALESCE(SUM(CASE WHEN {prefix}interval_seconds > 0 THEN {prefix}interval_seconds ELSE 0.0 END), 0.0) AS observed_interval_seconds,
            COALESCE(MAX({prefix}interval_seconds), 0.0) AS max_interval_seconds,
            COALESCE(SUM(CASE WHEN {prefix}interval_seconds > 0 THEN 1 ELSE 0 END), 0) AS positive_interval_count,
            COALESCE(SUM({prefix}pv_energy_kwh), 0.0) AS pv_energy_kwh,
            COALESCE(SUM({prefix}load_energy_kwh), 0.0) AS load_energy_kwh,
            COALESCE(SUM({prefix}grid_export_energy_kwh), 0.0) AS grid_export_energy_kwh,
            COALESCE(SUM({prefix}grid_to_load_energy_kwh + {prefix}grid_to_battery_energy_kwh), 0.0) AS grid_import_energy_kwh,
            COALESCE(SUM({prefix}grid_to_load_energy_kwh), 0.0) AS grid_to_load_energy_kwh,
            COALESCE(SUM({prefix}grid_to_battery_energy_kwh), 0.0) AS grid_to_battery_energy_kwh
    """


def _refresh_day_quality_summary(db, local_day: str):
    if not local_day:
        return
    rows = db.execute(
        f"""
        SELECT
            local_day,
            {_reconciliation_quality_select()}
        FROM derived_energy_intervals
        WHERE local_day = ?
        GROUP BY local_day, quality
        """,
        [local_day],
    )
    db.execute(
        f"DELETE FROM {QUALITY_SUMMARY_DAYS_TABLE} WHERE local_day = ?",
        [local_day],
    )
    if not rows:
        return

    updated_at = datetime.now(timezone.utc).isoformat()
    db.executemany(
        f"""
        INSERT OR REPLACE INTO {QUALITY_SUMMARY_DAYS_TABLE} (
            local_day,
            quality,
            interval_count,
            integrated_interval_count,
            dropped_interval_count,
            integrated_seconds,
            dropped_seconds,
            observed_interval_seconds,
            max_interval_seconds,
            positive_interval_count,
            pv_energy_kwh,
            load_energy_kwh,
            grid_export_energy_kwh,
            grid_import_energy_kwh,
            grid_to_load_energy_kwh,
            grid_to_battery_energy_kwh,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["local_day"],
                row["quality"] or "unknown",
                row["interval_count"],
                row["integrated_interval_count"],
                row["dropped_interval_count"],
                row["integrated_seconds"],
                row["dropped_seconds"],
                row["observed_interval_seconds"],
                row["max_interval_seconds"],
                row["positive_interval_count"],
                row["pv_energy_kwh"],
                row["load_energy_kwh"],
                row["grid_export_energy_kwh"],
                row["grid_import_energy_kwh"],
                row["grid_to_load_energy_kwh"],
                row["grid_to_battery_energy_kwh"],
                updated_at,
            )
            for row in rows
        ],
    )


def _aggregate_summary_rows(
    db,
    source_table: str,
    filter_column: Optional[str] = None,
    filter_value: Optional[str] = None,
    *,
    extra_selects: tuple[str, ...] = (),
) -> dict[str, Any]:
    where_clause = ""
    params: list[Any] = []
    if filter_column is not None and filter_value is not None:
        where_clause = f"WHERE {filter_column} = ?"
        params.append(filter_value)

    row = db.fetchone(
        f"""
        SELECT
            COUNT(*) AS row_count,
            COALESCE(SUM(interval_count), 0) AS interval_count,
            COALESCE(SUM(sample_count), 0) AS sample_count,
            COALESCE(SUM(covered_seconds), 0.0) AS covered_seconds,
            COALESCE(SUM(missing_intervals), 0) AS missing_intervals,
            MIN(first_recorded_at) AS first_recorded_at,
            MAX(last_recorded_at) AS last_recorded_at,
            {", ".join(extra_selects + (_summary_totals_select(),))}
        FROM {source_table}
        {where_clause}
        """,
        params,
    )
    return dict(row) if row else {}


def _refresh_day_summary(
    db,
    local_day: str,
    *,
    reference_time: Optional[datetime] = None,
):
    if not local_day:
        return

    aggregate = _aggregate_day_summary(db, local_day)
    sample_stats = _history_sample_stats_for_day(db, local_day)
    interval_count = int(aggregate.get("interval_count") or 0)
    sample_count = int(sample_stats.get("sample_count") or 0)
    if interval_count <= 0 and sample_count <= 0:
        _delete_summary_row(db, SUMMARY_ROLLUP_TABLES["day"], "local_day", local_day)
        return

    row = {
        "local_day": local_day,
        "local_month": aggregate.get("local_month") or local_day[:7],
        "local_year": aggregate.get("local_year") or local_day[:4],
        "interval_count": interval_count,
        "sample_count": sample_count,
        "covered_seconds": float(aggregate.get("covered_seconds") or 0.0),
        "missing_intervals": int(aggregate.get("missing_intervals") or 0),
        "first_recorded_at": sample_stats.get("first_recorded_at"),
        "last_recorded_at": sample_stats.get("last_recorded_at"),
        "finalized": _summary_is_finalized("day", local_day, reference_time),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **{
            column: float(aggregate.get(column) or 0.0)
            for column in CUMULATIVE_TOTAL_COLUMNS
        },
    }
    _write_summary_row(db, SUMMARY_ROLLUP_TABLES["day"], row)
    _refresh_day_quality_summary(db, local_day)


def _refresh_month_summary(
    db,
    local_month: str,
    *,
    reference_time: Optional[datetime] = None,
):
    if not local_month:
        return

    aggregate = _aggregate_summary_rows(
        db,
        SUMMARY_ROLLUP_TABLES["day"],
        "local_month",
        local_month,
        extra_selects=("MAX(local_year) AS local_year",),
    )
    if int(aggregate.get("row_count") or 0) <= 0:
        _delete_summary_row(db, SUMMARY_ROLLUP_TABLES["month"], "local_month", local_month)
        return

    row = {
        "local_month": local_month,
        "local_year": aggregate.get("local_year") or local_month[:4],
        "interval_count": int(aggregate.get("interval_count") or 0),
        "sample_count": int(aggregate.get("sample_count") or 0),
        "covered_seconds": float(aggregate.get("covered_seconds") or 0.0),
        "missing_intervals": int(aggregate.get("missing_intervals") or 0),
        "first_recorded_at": aggregate.get("first_recorded_at"),
        "last_recorded_at": aggregate.get("last_recorded_at"),
        "finalized": _summary_is_finalized("month", local_month, reference_time),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **{
            column: float(aggregate.get(column) or 0.0)
            for column in CUMULATIVE_TOTAL_COLUMNS
        },
    }
    _write_summary_row(db, SUMMARY_ROLLUP_TABLES["month"], row)


def _refresh_year_summary(
    db,
    local_year: str,
    *,
    reference_time: Optional[datetime] = None,
):
    if not local_year:
        return

    aggregate = _aggregate_summary_rows(
        db,
        SUMMARY_ROLLUP_TABLES["month"],
        "local_year",
        local_year,
    )
    if int(aggregate.get("row_count") or 0) <= 0:
        _delete_summary_row(db, SUMMARY_ROLLUP_TABLES["year"], "local_year", local_year)
        return

    row = {
        "local_year": local_year,
        "interval_count": int(aggregate.get("interval_count") or 0),
        "sample_count": int(aggregate.get("sample_count") or 0),
        "covered_seconds": float(aggregate.get("covered_seconds") or 0.0),
        "missing_intervals": int(aggregate.get("missing_intervals") or 0),
        "first_recorded_at": aggregate.get("first_recorded_at"),
        "last_recorded_at": aggregate.get("last_recorded_at"),
        "finalized": _summary_is_finalized("year", local_year, reference_time),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **{
            column: float(aggregate.get(column) or 0.0)
            for column in CUMULATIVE_TOTAL_COLUMNS
        },
    }
    _write_summary_row(db, SUMMARY_ROLLUP_TABLES["year"], row)


def _refresh_summary_rollups_for_snapshot(
    db,
    current_row: dict[str, Any],
    previous_row: Optional[dict[str, Any]] = None,
    *,
    reference_time: Optional[datetime] = None,
):
    days = {current_row.get("local_day")}
    months = {current_row.get("local_month")}
    years = {current_row.get("local_year")}
    if previous_row:
        days.add(previous_row.get("local_day"))
        months.add(previous_row.get("local_month"))
        years.add(previous_row.get("local_year"))

    for local_day in sorted(day for day in days if day):
        _refresh_day_summary(db, local_day, reference_time=reference_time)
    for local_month in sorted(month for month in months if month):
        _refresh_month_summary(db, local_month, reference_time=reference_time)
    for local_year in sorted(year for year in years if year):
        _refresh_year_summary(db, local_year, reference_time=reference_time)


def _set_rollup_state(db, key: str, value: str):
    db.execute(
        """
        INSERT OR REPLACE INTO summary_rollup_state (key, value)
        VALUES (?, ?)
        """,
        [key, value],
    )


def rebuild_energy_rollups(
    db,
    *,
    reference_time: Optional[datetime] = None,
):
    reference_time = reference_time or datetime.now(timezone.utc)
    for table in (
        QUALITY_SUMMARY_DAYS_TABLE,
        SUMMARY_ROLLUP_TABLES["year"],
        SUMMARY_ROLLUP_TABLES["month"],
        SUMMARY_ROLLUP_TABLES["day"],
    ):
        db.execute(f"DELETE FROM {table}")

    day_rows = db.execute(
        """
        SELECT DISTINCT local_day
        FROM derived_energy_intervals
        ORDER BY local_day ASC
        """
    )
    for row in day_rows:
        _refresh_day_summary(db, row["local_day"], reference_time=reference_time)

    month_rows = db.execute(
        f"""
        SELECT DISTINCT local_month
        FROM {SUMMARY_ROLLUP_TABLES["day"]}
        ORDER BY local_month ASC
        """
    )
    for row in month_rows:
        _refresh_month_summary(db, row["local_month"], reference_time=reference_time)

    year_rows = db.execute(
        f"""
        SELECT DISTINCT local_year
        FROM {SUMMARY_ROLLUP_TABLES["month"]}
        ORDER BY local_year ASC
        """
    )
    for row in year_rows:
        _refresh_year_summary(db, row["local_year"], reference_time=reference_time)

    _set_rollup_state(db, SUMMARY_ROLLUP_STATE_KEY, SUMMARY_ROLLUP_VERSION)
    _set_rollup_state(
        db,
        QUALITY_SUMMARY_ROLLUP_STATE_KEY,
        QUALITY_SUMMARY_ROLLUP_VERSION,
    )


def rebuild_quality_summary_days(
    db,
    *,
    start_day: Optional[str] = None,
    end_day_exclusive: Optional[str] = None,
    reference_time: Optional[datetime] = None,
) -> int:
    del reference_time  # Reserved for symmetry with the energy rollup rebuild API.
    filters = []
    params = []
    if start_day:
        filters.append("local_day >= ?")
        params.append(start_day)
    if end_day_exclusive:
        filters.append("local_day < ?")
        params.append(end_day_exclusive)
    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    days = [
        row["local_day"]
        for row in db.execute(
            f"""
            SELECT DISTINCT local_day
            FROM derived_energy_intervals
            {where_clause}
            ORDER BY local_day ASC
            """,
            params,
        )
    ]
    for local_day in days:
        _refresh_day_quality_summary(db, local_day)

    if start_day is None and end_day_exclusive is None:
        _set_rollup_state(
            db,
            QUALITY_SUMMARY_ROLLUP_STATE_KEY,
            QUALITY_SUMMARY_ROLLUP_VERSION,
        )
    return len(days)


def refresh_missing_quality_summary_days(
    db,
    start_day: str,
    end_day_exclusive: str,
    *,
    max_days: int = 400,
) -> dict[str, Any]:
    rows = db.execute(
        f"""
        SELECT DISTINCT d.local_day
        FROM derived_energy_intervals d
        LEFT JOIN (
            SELECT DISTINCT local_day
            FROM {QUALITY_SUMMARY_DAYS_TABLE}
        ) q ON q.local_day = d.local_day
        WHERE
            d.local_day >= ?
            AND d.local_day < ?
            AND q.local_day IS NULL
        ORDER BY d.local_day ASC
        LIMIT ?
        """,
        [start_day, end_day_exclusive, max(int(max_days), 1) + 1],
    )
    days = [row["local_day"] for row in rows]
    limited = len(days) > max_days
    if limited:
        days = days[:max_days]
    for local_day in days:
        _refresh_day_quality_summary(db, local_day)
    return {
        "refreshed_days": len(days),
        "limited": limited,
    }


def get_reconciliation_quality_summary_rows(
    db,
    start_day: str,
    end_day_exclusive: str,
):
    return db.execute(
        f"""
        SELECT
            COALESCE(quality, 'unknown') AS quality,
            COALESCE(SUM(interval_count), 0) AS interval_count,
            COALESCE(SUM(integrated_interval_count), 0) AS integrated_interval_count,
            COALESCE(SUM(dropped_interval_count), 0) AS dropped_interval_count,
            COALESCE(SUM(integrated_seconds), 0.0) AS integrated_seconds,
            COALESCE(SUM(dropped_seconds), 0.0) AS dropped_seconds,
            COALESCE(SUM(observed_interval_seconds), 0.0) AS observed_interval_seconds,
            COALESCE(MAX(max_interval_seconds), 0.0) AS max_interval_seconds,
            COALESCE(SUM(positive_interval_count), 0) AS positive_interval_count,
            COALESCE(SUM(pv_energy_kwh), 0.0) AS pv_energy_kwh,
            COALESCE(SUM(load_energy_kwh), 0.0) AS load_energy_kwh,
            COALESCE(SUM(grid_export_energy_kwh), 0.0) AS grid_export_energy_kwh,
            COALESCE(SUM(grid_import_energy_kwh), 0.0) AS grid_import_energy_kwh,
            COALESCE(SUM(grid_to_load_energy_kwh), 0.0) AS grid_to_load_energy_kwh,
            COALESCE(SUM(grid_to_battery_energy_kwh), 0.0) AS grid_to_battery_energy_kwh
        FROM {QUALITY_SUMMARY_DAYS_TABLE}
        WHERE local_day >= ? AND local_day < ?
        GROUP BY quality
        ORDER BY quality ASC
        """,
        [start_day, end_day_exclusive],
    )


def get_reconciliation_full_day_rows(
    db,
    start_day: str,
    end_day_exclusive: str,
):
    return db.execute(
        f"""
        WITH summarized_days AS (
            SELECT DISTINCT local_day
            FROM {QUALITY_SUMMARY_DAYS_TABLE}
            WHERE local_day >= ? AND local_day < ?
        ),
        summary_rows AS (
            SELECT
                COALESCE(quality, 'unknown') AS quality,
                COALESCE(SUM(interval_count), 0) AS interval_count,
                COALESCE(SUM(integrated_interval_count), 0) AS integrated_interval_count,
                COALESCE(SUM(dropped_interval_count), 0) AS dropped_interval_count,
                COALESCE(SUM(integrated_seconds), 0.0) AS integrated_seconds,
                COALESCE(SUM(dropped_seconds), 0.0) AS dropped_seconds,
                COALESCE(SUM(observed_interval_seconds), 0.0) AS observed_interval_seconds,
                COALESCE(MAX(max_interval_seconds), 0.0) AS max_interval_seconds,
                COALESCE(SUM(positive_interval_count), 0) AS positive_interval_count,
                COALESCE(SUM(pv_energy_kwh), 0.0) AS pv_energy_kwh,
                COALESCE(SUM(load_energy_kwh), 0.0) AS load_energy_kwh,
                COALESCE(SUM(grid_export_energy_kwh), 0.0) AS grid_export_energy_kwh,
                COALESCE(SUM(grid_import_energy_kwh), 0.0) AS grid_import_energy_kwh,
                COALESCE(SUM(grid_to_load_energy_kwh), 0.0) AS grid_to_load_energy_kwh,
                COALESCE(SUM(grid_to_battery_energy_kwh), 0.0) AS grid_to_battery_energy_kwh
            FROM {QUALITY_SUMMARY_DAYS_TABLE}
            WHERE local_day >= ? AND local_day < ?
            GROUP BY quality
        ),
        interval_rows AS (
            SELECT
                {_reconciliation_quality_select("d")}
            FROM derived_energy_intervals d
            WHERE
                d.local_day >= ?
                AND d.local_day < ?
                AND NOT EXISTS (
                    SELECT 1
                    FROM summarized_days s
                    WHERE s.local_day = d.local_day
                )
            GROUP BY d.quality
        ),
        combined_rows AS (
            SELECT * FROM summary_rows
            UNION ALL
            SELECT * FROM interval_rows
        )
        SELECT
            quality,
            COALESCE(SUM(interval_count), 0) AS interval_count,
            COALESCE(SUM(integrated_interval_count), 0) AS integrated_interval_count,
            COALESCE(SUM(dropped_interval_count), 0) AS dropped_interval_count,
            COALESCE(SUM(integrated_seconds), 0.0) AS integrated_seconds,
            COALESCE(SUM(dropped_seconds), 0.0) AS dropped_seconds,
            COALESCE(SUM(observed_interval_seconds), 0.0) AS observed_interval_seconds,
            COALESCE(MAX(max_interval_seconds), 0.0) AS max_interval_seconds,
            COALESCE(SUM(positive_interval_count), 0) AS positive_interval_count,
            COALESCE(SUM(pv_energy_kwh), 0.0) AS pv_energy_kwh,
            COALESCE(SUM(load_energy_kwh), 0.0) AS load_energy_kwh,
            COALESCE(SUM(grid_export_energy_kwh), 0.0) AS grid_export_energy_kwh,
            COALESCE(SUM(grid_import_energy_kwh), 0.0) AS grid_import_energy_kwh,
            COALESCE(SUM(grid_to_load_energy_kwh), 0.0) AS grid_to_load_energy_kwh,
            COALESCE(SUM(grid_to_battery_energy_kwh), 0.0) AS grid_to_battery_energy_kwh
        FROM combined_rows
        GROUP BY quality
        ORDER BY quality ASC
        """,
        [
            start_day,
            end_day_exclusive,
            start_day,
            end_day_exclusive,
            start_day,
            end_day_exclusive,
        ],
    )


def count_reconciliation_quality_summary_days(
    db,
    start_day: str,
    end_day_exclusive: str,
) -> int:
    row = db.fetchone(
        f"""
        SELECT COUNT(DISTINCT local_day) AS day_count
        FROM {QUALITY_SUMMARY_DAYS_TABLE}
        WHERE local_day >= ? AND local_day < ?
        """,
        [start_day, end_day_exclusive],
    )
    return int(row["day_count"] or 0) if row else 0


def count_reconciliation_unsummarized_interval_days(
    db,
    start_day: str,
    end_day_exclusive: str,
) -> int:
    row = db.fetchone(
        f"""
        SELECT COUNT(DISTINCT d.local_day) AS day_count
        FROM derived_energy_intervals d
        WHERE
            d.local_day >= ?
            AND d.local_day < ?
            AND NOT EXISTS (
                SELECT 1
                FROM {QUALITY_SUMMARY_DAYS_TABLE} q
                WHERE q.local_day = d.local_day
            )
        """,
        [start_day, end_day_exclusive],
    )
    return int(row["day_count"] or 0) if row else 0


def count_reconciliation_interval_days(
    db,
    start_day: str,
    end_day_exclusive: str,
) -> int:
    row = db.fetchone(
        """
        SELECT COUNT(DISTINCT local_day) AS day_count
        FROM derived_energy_intervals
        WHERE local_day >= ? AND local_day < ?
        """,
        [start_day, end_day_exclusive],
    )
    return int(row["day_count"] or 0) if row else 0


def get_reconciliation_interval_rows(db, start_utc_iso: str, end_utc_iso: str):
    return db.execute(
        f"""
        SELECT
            {_reconciliation_quality_select()}
        FROM derived_energy_intervals
        WHERE recorded_at >= ? AND recorded_at < ?
        GROUP BY quality
        ORDER BY quality ASC
        """,
        [start_utc_iso, end_utc_iso],
    )


def _ensure_energy_rollups(db):
    row = db.fetchone(
        "SELECT value FROM summary_rollup_state WHERE key = ?",
        [SUMMARY_ROLLUP_STATE_KEY],
    )
    if row and row["value"] == SUMMARY_ROLLUP_VERSION:
        return
    rebuild_energy_rollups(db)


def _archived_bucket_start_local(
    reference_time: Optional[datetime] = None,
    retention_hours: int = RAW_HISTORY_RETENTION_HOURS,
    bucket_minutes: int = ARCHIVED_SAMPLE_BUCKET_MINUTES,
) -> str:
    local = (reference_time or datetime.now(timezone.utc)).astimezone()
    cutoff = local - timedelta(hours=retention_hours)
    bucket_start = cutoff.replace(
        minute=(cutoff.minute // bucket_minutes) * bucket_minutes,
        second=0,
        microsecond=0,
    )
    if bucket_start + timedelta(minutes=bucket_minutes) > cutoff:
        bucket_start -= timedelta(minutes=bucket_minutes)
    return bucket_start.strftime("%Y-%m-%dT%H:%M")


def _archived_row_recorded_at(bucket_local: str, latest_recorded_at: str) -> str:
    latest_local = _utc_from_iso(latest_recorded_at).astimezone()
    bucket_local_dt = datetime.fromisoformat(bucket_local).replace(
        tzinfo=latest_local.tzinfo
    )
    return bucket_local_dt.astimezone(timezone.utc).isoformat()


def _history_bucket_expr(column_name: str) -> str:
    return (
        f"substr({column_name}, 1, 14) || "
        f"printf('%02d', CAST(CAST(substr({column_name}, 15, 2) AS INTEGER) / "
        f"{ARCHIVED_SAMPLE_BUCKET_MINUTES} AS INTEGER) * {ARCHIVED_SAMPLE_BUCKET_MINUTES})"
    )


def _power_value(value: Any) -> float:
    return max(float(value or 0.0), 0.0)


def calculate_power_flow_breakdown(values: dict[str, Any]) -> dict[str, float]:
    pv_power_w = _power_value(values.get("pv_power_w"))
    grid_export_power_w = min(
        _power_value(values.get("solar_feed_to_grid_power_w")),
        pv_power_w,
    )
    load_power_w = _power_value(values.get("ac_output_active_power_w"))
    battery_charge_power_w = _power_value(values.get("battery_charge_power_w"))
    battery_discharge_power_w = _power_value(values.get("battery_discharge_power_w"))
    operation_mode_code = values.get("operation_mode_code")
    ac_input_available = values.get("ac_input_available")
    if ac_input_available is None:
        ac_input_available = (values.get("inverter_status") or {}).get(
            "ac_input_available"
        )
    ac_input_available = bool(ac_input_available)

    local_pv_power_w = max(pv_power_w - grid_export_power_w, 0.0)
    prefer_battery_charge_first = (
        operation_mode_code == "L"
        and ac_input_available
        and battery_charge_power_w > 0.0
        and battery_discharge_power_w <= 0.0
    )

    if prefer_battery_charge_first:
        pv_to_battery_power_w = min(local_pv_power_w, battery_charge_power_w)
        remaining_local_pv_power_w = max(local_pv_power_w - pv_to_battery_power_w, 0.0)
        battery_to_load_power_w = 0.0
        remaining_load_power_w = load_power_w
        pv_to_load_power_w = min(remaining_local_pv_power_w, remaining_load_power_w)
        grid_to_load_power_w = max(remaining_load_power_w - pv_to_load_power_w, 0.0)
    else:
        battery_to_load_power_w = min(battery_discharge_power_w, load_power_w)
        remaining_load_power_w = max(load_power_w - battery_to_load_power_w, 0.0)
        pv_to_load_power_w = min(local_pv_power_w, remaining_load_power_w)
        grid_to_load_power_w = max(remaining_load_power_w - pv_to_load_power_w, 0.0)
        remaining_local_pv_power_w = max(local_pv_power_w - pv_to_load_power_w, 0.0)
        pv_to_battery_power_w = min(remaining_local_pv_power_w, battery_charge_power_w)

    grid_to_battery_power_w = max(
        battery_charge_power_w - pv_to_battery_power_w,
        0.0,
    )

    return {
        "pv_power_w": pv_power_w,
        "grid_export_power_w": grid_export_power_w,
        "load_power_w": load_power_w,
        "battery_charge_power_w": battery_charge_power_w,
        "battery_discharge_power_w": battery_discharge_power_w,
        "pv_to_load_power_w": pv_to_load_power_w,
        "pv_to_battery_power_w": pv_to_battery_power_w,
        "battery_to_load_power_w": battery_to_load_power_w,
        "grid_to_load_power_w": grid_to_load_power_w,
        "grid_to_battery_power_w": grid_to_battery_power_w,
        "grid_import_power_w": grid_to_load_power_w + grid_to_battery_power_w,
        "local_solar_power_w": pv_to_load_power_w + pv_to_battery_power_w,
        "local_supply_to_load_power_w": (
            pv_to_load_power_w + battery_to_load_power_w
        ),
    }


def _ensure_table_columns(db, table_name: str, columns: dict[str, str]):
    existing = {
        row["name"]
        for row in db.execute(f"PRAGMA table_info({table_name})")
    }
    for column_name, column_definition in columns.items():
        if column_name not in existing:
            db.execute(
                f"ALTER TABLE {table_name} "
                f"ADD COLUMN {column_name} {column_definition}"
            )


def _backfill_archive_bucket_column(db, table_name: str):
    count_row = db.fetchone(
        f"""
        SELECT COUNT(*) AS count
        FROM (
            SELECT 1
            FROM {table_name}
            WHERE archive_bucket_local IS NULL
            LIMIT ?
        )
        """,
        [MAX_AUTOMATIC_ARCHIVE_BUCKET_BACKFILL_ROWS + 1],
    )
    missing_count = int(count_row["count"] if count_row else 0)
    if missing_count == 0:
        return
    if missing_count > MAX_AUTOMATIC_ARCHIVE_BUCKET_BACKFILL_ROWS:
        logging.warning(
            "Skipping automatic archive-bucket backfill for %s %s rows; "
            "compaction can still use local_day until a manual migration is run",
            missing_count,
            table_name,
        )
        return

    bucket_expr = _history_bucket_expr("recorded_minute")
    db.execute(
        f"""
        UPDATE {table_name}
        SET archive_bucket_local = {bucket_expr}
        WHERE archive_bucket_local IS NULL
        """,
    )


def _stale_flow_energy_count(db) -> int:
    row = db.fetchone(
        """
        SELECT COUNT(*) AS count
        FROM derived_energy_intervals
        WHERE
            contiguous = 1
            AND (
                pv_energy_kwh > 0.0
                OR load_energy_kwh > 0.0
                OR battery_charge_energy_kwh > 0.0
                OR battery_discharge_energy_kwh > 0.0
                OR grid_export_energy_kwh > 0.0
            )
            AND pv_to_load_energy_kwh = 0.0
            AND pv_to_battery_energy_kwh = 0.0
            AND battery_to_load_energy_kwh = 0.0
            AND grid_to_load_energy_kwh = 0.0
            AND grid_to_battery_energy_kwh = 0.0
        """
    )
    return int(row["count"]) if row else 0


def backfill_flow_energy_columns(db):
    state = db.fetchone(
        "SELECT value FROM summary_rollup_state WHERE key = ?",
        [FLOW_ENERGY_BACKFILL_STATE_KEY],
    )
    if state and state["value"] == FLOW_ENERGY_BACKFILL_VERSION:
        return
    if state and str(state["value"]).startswith("manual_required"):
        return

    row_count = db.fetchone(
        "SELECT COUNT(*) AS count FROM derived_energy_intervals"
    )
    interval_count = int(row_count["count"] if row_count else 0)
    if interval_count > MAX_AUTOMATIC_FLOW_BACKFILL_ROWS:
        logging.warning(
            "Skipping automatic flow-energy backfill for %s intervals; "
            "new intervals will be correct and historical recalculation should be run manually",
            interval_count,
        )
        _set_rollup_state(
            db,
            FLOW_ENERGY_BACKFILL_STATE_KEY,
            f"manual_required:{interval_count}",
        )
        return

    if _stale_flow_energy_count(db) == 0:
        _set_rollup_state(
            db,
            FLOW_ENERGY_BACKFILL_STATE_KEY,
            FLOW_ENERGY_BACKFILL_VERSION,
        )
        return

    rows = db.execute(
        """
        SELECT
            d.recorded_at,
            d.previous_recorded_at,
            d.interval_seconds,
            d.contiguous,
            s.pv_power_w AS current_pv_power_w,
            s.ac_output_active_power_w AS current_load_power_w,
            s.battery_charge_power_w AS current_battery_charge_power_w,
            s.battery_discharge_power_w AS current_battery_discharge_power_w,
            s.solar_feed_to_grid_power_w AS current_grid_export_power_w,
            p.pv_power_w AS previous_pv_power_w,
            p.ac_output_active_power_w AS previous_load_power_w,
            p.battery_charge_power_w AS previous_battery_charge_power_w,
            p.battery_discharge_power_w AS previous_battery_discharge_power_w,
            p.solar_feed_to_grid_power_w AS previous_grid_export_power_w
        FROM derived_energy_intervals d
        JOIN samples s ON s.recorded_at = d.recorded_at
        LEFT JOIN samples p ON p.recorded_at = d.previous_recorded_at
        ORDER BY d.recorded_at ASC
        """
    )

    updates = []
    for row in rows:
        if not row["contiguous"] or row["previous_recorded_at"] is None:
            updates.append((0.0, 0.0, 0.0, 0.0, 0.0, row["recorded_at"]))
            continue

        previous_flows = calculate_power_flow_breakdown(
            {
                "pv_power_w": row["previous_pv_power_w"],
                "ac_output_active_power_w": row["previous_load_power_w"],
                "battery_charge_power_w": row["previous_battery_charge_power_w"],
                "battery_discharge_power_w": row[
                    "previous_battery_discharge_power_w"
                ],
                "solar_feed_to_grid_power_w": row["previous_grid_export_power_w"],
            }
        )
        current_flows = calculate_power_flow_breakdown(
            {
                "pv_power_w": row["current_pv_power_w"],
                "ac_output_active_power_w": row["current_load_power_w"],
                "battery_charge_power_w": row["current_battery_charge_power_w"],
                "battery_discharge_power_w": row[
                    "current_battery_discharge_power_w"
                ],
                "solar_feed_to_grid_power_w": row["current_grid_export_power_w"],
            }
        )
        interval_seconds = max(float(row["interval_seconds"] or 0.0), 0.0)
        updates.append(
            (
                _power_integral_kwh(
                    previous_flows["pv_to_load_power_w"],
                    current_flows["pv_to_load_power_w"],
                    interval_seconds,
                ),
                _power_integral_kwh(
                    previous_flows["pv_to_battery_power_w"],
                    current_flows["pv_to_battery_power_w"],
                    interval_seconds,
                ),
                _power_integral_kwh(
                    previous_flows["battery_to_load_power_w"],
                    current_flows["battery_to_load_power_w"],
                    interval_seconds,
                ),
                _power_integral_kwh(
                    previous_flows["grid_to_load_power_w"],
                    current_flows["grid_to_load_power_w"],
                    interval_seconds,
                ),
                _power_integral_kwh(
                    previous_flows["grid_to_battery_power_w"],
                    current_flows["grid_to_battery_power_w"],
                    interval_seconds,
                ),
                row["recorded_at"],
            )
        )

    db.executemany(
        """
        UPDATE derived_energy_intervals
        SET
            pv_to_load_energy_kwh = ?,
            pv_to_battery_energy_kwh = ?,
            battery_to_load_energy_kwh = ?,
            grid_to_load_energy_kwh = ?,
            grid_to_battery_energy_kwh = ?
        WHERE recorded_at = ?
        """,
        updates,
    )
    remaining_stale = _stale_flow_energy_count(db)
    if remaining_stale:
        logging.warning(
            "Flow-energy backfill remains partial for %s intervals; "
            "historical recalculation should be run manually",
            remaining_stale,
        )
        _set_rollup_state(
            db,
            FLOW_ENERGY_BACKFILL_STATE_KEY,
            f"manual_required:{remaining_stale}",
        )
        return
    _set_rollup_state(
        db,
        FLOW_ENERGY_BACKFILL_STATE_KEY,
        FLOW_ENERGY_BACKFILL_VERSION,
    )


def ensure_schema(db):
    db.execute_script(
        """
        CREATE TABLE IF NOT EXISTS current_snapshot (
            slot TEXT PRIMARY KEY,
            recorded_at TEXT NOT NULL,
            snapshot_json TEXT NOT NULL,
            cumulative_json TEXT NOT NULL,
            pricing_json TEXT,
            semantics_json TEXT NOT NULL,
            capabilities_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS capabilities (
            command TEXT PRIMARY KEY,
            supported INTEGER NOT NULL,
            checked_at TEXT NOT NULL,
            protocol_id TEXT,
            field_count INTEGER,
            crc_ok INTEGER,
            response_preview TEXT,
            parsed_json TEXT,
            raw_payload TEXT
        );

        CREATE TABLE IF NOT EXISTS samples (
            recorded_at TEXT PRIMARY KEY,
            recorded_minute TEXT NOT NULL,
            archive_bucket_local TEXT,
            local_day TEXT NOT NULL,
            local_month TEXT NOT NULL,
            local_year TEXT NOT NULL,
            serial_number TEXT,
            protocol_id TEXT,
            device_id TEXT,
            operation_mode_code TEXT,
            operation_mode TEXT,
            fault_code TEXT,
            fault TEXT,
            ac_input_voltage_v REAL,
            ac_input_frequency_hz REAL,
            ac_output_voltage_v REAL,
            ac_output_frequency_hz REAL,
            ac_output_apparent_power_va REAL,
            ac_output_active_power_w REAL,
            ac_output_load_percent REAL,
            battery_voltage_v REAL,
            battery_charge_current_a REAL,
            battery_state_of_charge_percent REAL,
            pv_input_voltage_v REAL,
            total_charging_current_a REAL,
            total_ac_output_apparent_power_va REAL,
            total_output_active_power_w REAL,
            total_output_load_percent REAL,
            ac_output_mode_code TEXT,
            ac_output_mode TEXT,
            battery_charger_source_priority_code TEXT,
            battery_charger_source_priority TEXT,
            max_charging_current_set_a REAL,
            max_charging_current_possible_a REAL,
            max_ac_charging_current_set_a REAL,
            pv_input_current_a REAL,
            battery_discharge_current_a REAL,
            pv_power_w REAL,
            pv_power_semantics TEXT,
            battery_charge_power_w REAL,
            battery_discharge_power_w REAL,
            bus_voltage_v REAL,
            inverter_temperature_c REAL,
            battery_voltage_from_scc_v REAL,
            pv_charging_power_w REAL,
            solar_feed_to_grid_power_w REAL,
            mppt_active INTEGER,
            ac_charging_on INTEGER,
            solar_charging_on INTEGER,
            battery_state_code TEXT,
            battery_state TEXT,
            ac_input_available INTEGER,
            ac_output_on INTEGER,
            inverter_status_raw TEXT,
            inverter_status_json TEXT,
            qpigs_status_flags_raw TEXT,
            qpigs_status_flags_json TEXT,
            device_status2_raw TEXT,
            device_status2_json TEXT,
            solar_feed_to_grid_enabled INTEGER,
            country_code TEXT,
            qpiws_raw TEXT,
            warnings_json TEXT,
            qflag_raw TEXT,
            flags_json TEXT,
            qpiri_json TEXT,
            metadata_json TEXT,
            raw_snapshot_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_samples_recorded_minute
            ON samples(recorded_minute);
        CREATE INDEX IF NOT EXISTS idx_samples_local_day
            ON samples(local_day);
        CREATE INDEX IF NOT EXISTS idx_samples_local_month
            ON samples(local_month);
        CREATE INDEX IF NOT EXISTS idx_samples_local_year
            ON samples(local_year);
        CREATE INDEX IF NOT EXISTS idx_samples_peak_pv
            ON samples(pv_power_w DESC, recorded_at ASC);

        CREATE TABLE IF NOT EXISTS minute_samples (
            recorded_minute TEXT PRIMARY KEY,
            recorded_at TEXT NOT NULL,
            archive_bucket_local TEXT,
            local_day TEXT NOT NULL,
            local_month TEXT NOT NULL,
            local_year TEXT NOT NULL,
            serial_number TEXT,
            protocol_id TEXT,
            device_id TEXT,
            operation_mode_code TEXT,
            operation_mode TEXT,
            fault_code TEXT,
            fault TEXT,
            ac_input_voltage_v REAL,
            ac_input_frequency_hz REAL,
            ac_output_voltage_v REAL,
            ac_output_frequency_hz REAL,
            ac_output_apparent_power_va REAL,
            ac_output_active_power_w REAL,
            ac_output_load_percent REAL,
            battery_voltage_v REAL,
            battery_charge_current_a REAL,
            battery_state_of_charge_percent REAL,
            pv_input_voltage_v REAL,
            total_charging_current_a REAL,
            total_ac_output_apparent_power_va REAL,
            total_output_active_power_w REAL,
            total_output_load_percent REAL,
            ac_output_mode_code TEXT,
            ac_output_mode TEXT,
            battery_charger_source_priority_code TEXT,
            battery_charger_source_priority TEXT,
            max_charging_current_set_a REAL,
            max_charging_current_possible_a REAL,
            max_ac_charging_current_set_a REAL,
            pv_input_current_a REAL,
            battery_discharge_current_a REAL,
            pv_power_w REAL,
            pv_power_semantics TEXT,
            battery_charge_power_w REAL,
            battery_discharge_power_w REAL,
            bus_voltage_v REAL,
            inverter_temperature_c REAL,
            battery_voltage_from_scc_v REAL,
            pv_charging_power_w REAL,
            solar_feed_to_grid_power_w REAL,
            mppt_active INTEGER,
            ac_charging_on INTEGER,
            solar_charging_on INTEGER,
            battery_state_code TEXT,
            battery_state TEXT,
            ac_input_available INTEGER,
            ac_output_on INTEGER,
            inverter_status_raw TEXT,
            inverter_status_json TEXT,
            qpigs_status_flags_raw TEXT,
            qpigs_status_flags_json TEXT,
            device_status2_raw TEXT,
            device_status2_json TEXT,
            solar_feed_to_grid_enabled INTEGER,
            country_code TEXT,
            qpiws_raw TEXT,
            warnings_json TEXT,
            qflag_raw TEXT,
            flags_json TEXT,
            qpiri_json TEXT,
            metadata_json TEXT,
            raw_snapshot_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_minute_samples_recorded_at
            ON minute_samples(recorded_at);
        CREATE INDEX IF NOT EXISTS idx_minute_samples_day
            ON minute_samples(local_day);
        CREATE INDEX IF NOT EXISTS idx_minute_samples_month
            ON minute_samples(local_month);
        CREATE INDEX IF NOT EXISTS idx_minute_samples_year
            ON minute_samples(local_year);

        CREATE TABLE IF NOT EXISTS compressed_samples_10m (
            bucket_local TEXT PRIMARY KEY,
            recorded_at TEXT NOT NULL,
            recorded_minute TEXT NOT NULL,
            local_day TEXT NOT NULL,
            local_month TEXT NOT NULL,
            local_year TEXT NOT NULL,
            operation_mode TEXT,
            fault TEXT,
            ac_input_voltage_v REAL,
            ac_output_voltage_v REAL,
            ac_output_active_power_w REAL,
            ac_output_load_percent REAL,
            battery_voltage_v REAL,
            battery_state_of_charge_percent REAL,
            battery_charge_current_a REAL,
            battery_discharge_current_a REAL,
            battery_charge_power_w REAL,
            battery_discharge_power_w REAL,
            pv_input_voltage_v REAL,
            pv_input_current_a REAL,
            pv_power_w REAL,
            pv_power_semantics TEXT,
            solar_feed_to_grid_power_w REAL,
            sample_count INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_compressed_samples_recorded_at
            ON compressed_samples_10m(recorded_at);
        CREATE INDEX IF NOT EXISTS idx_compressed_samples_local_day
            ON compressed_samples_10m(local_day);
        CREATE INDEX IF NOT EXISTS idx_compressed_samples_local_month
            ON compressed_samples_10m(local_month);
        CREATE INDEX IF NOT EXISTS idx_compressed_samples_local_year
            ON compressed_samples_10m(local_year);
        CREATE INDEX IF NOT EXISTS idx_compressed_samples_peak_pv
            ON compressed_samples_10m(pv_power_w DESC, recorded_at ASC);

        CREATE TABLE IF NOT EXISTS derived_energy_intervals (
            recorded_at TEXT PRIMARY KEY,
            previous_recorded_at TEXT,
            interval_seconds REAL NOT NULL,
            contiguous INTEGER NOT NULL,
            local_day TEXT NOT NULL,
            local_month TEXT NOT NULL,
            local_year TEXT NOT NULL,
            pv_energy_kwh REAL NOT NULL,
            load_energy_kwh REAL NOT NULL,
            battery_charge_energy_kwh REAL NOT NULL,
            battery_discharge_energy_kwh REAL NOT NULL,
            grid_export_energy_kwh REAL NOT NULL,
            pv_to_load_energy_kwh REAL NOT NULL,
            pv_to_battery_energy_kwh REAL NOT NULL,
            battery_to_load_energy_kwh REAL NOT NULL,
            grid_to_load_energy_kwh REAL NOT NULL,
            grid_to_battery_energy_kwh REAL NOT NULL,
            quality TEXT NOT NULL DEFAULT 'unknown',
            derived_json TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_energy_local_day
            ON derived_energy_intervals(local_day);
        CREATE INDEX IF NOT EXISTS idx_energy_local_month
            ON derived_energy_intervals(local_month);
        CREATE INDEX IF NOT EXISTS idx_energy_local_year
            ON derived_energy_intervals(local_year);

        CREATE TABLE IF NOT EXISTS energy_summary_days (
            local_day TEXT PRIMARY KEY,
            local_month TEXT NOT NULL,
            local_year TEXT NOT NULL,
            interval_count INTEGER NOT NULL DEFAULT 0,
            sample_count INTEGER NOT NULL DEFAULT 0,
            covered_seconds REAL NOT NULL DEFAULT 0.0,
            missing_intervals INTEGER NOT NULL DEFAULT 0,
            first_recorded_at TEXT,
            last_recorded_at TEXT,
            finalized INTEGER NOT NULL DEFAULT 0,
            pv_energy_kwh REAL NOT NULL DEFAULT 0.0,
            load_energy_kwh REAL NOT NULL DEFAULT 0.0,
            battery_charge_energy_kwh REAL NOT NULL DEFAULT 0.0,
            battery_discharge_energy_kwh REAL NOT NULL DEFAULT 0.0,
            grid_export_energy_kwh REAL NOT NULL DEFAULT 0.0,
            pv_to_load_energy_kwh REAL NOT NULL DEFAULT 0.0,
            pv_to_battery_energy_kwh REAL NOT NULL DEFAULT 0.0,
            battery_to_load_energy_kwh REAL NOT NULL DEFAULT 0.0,
            grid_to_load_energy_kwh REAL NOT NULL DEFAULT 0.0,
            grid_to_battery_energy_kwh REAL NOT NULL DEFAULT 0.0,
            earned_feed_in_eur REAL NOT NULL DEFAULT 0.0,
            earned_savings_eur REAL NOT NULL DEFAULT 0.0,
            updated_at TEXT NOT NULL
        ) WITHOUT ROWID;
        CREATE INDEX IF NOT EXISTS idx_energy_summary_days_month
            ON energy_summary_days(local_month, local_day);
        CREATE INDEX IF NOT EXISTS idx_energy_summary_days_year
            ON energy_summary_days(local_year, local_day);
        CREATE INDEX IF NOT EXISTS idx_energy_summary_days_peak_pv
            ON energy_summary_days(pv_energy_kwh DESC, local_day ASC);

        CREATE TABLE IF NOT EXISTS energy_summary_months (
            local_month TEXT PRIMARY KEY,
            local_year TEXT NOT NULL,
            interval_count INTEGER NOT NULL DEFAULT 0,
            sample_count INTEGER NOT NULL DEFAULT 0,
            covered_seconds REAL NOT NULL DEFAULT 0.0,
            missing_intervals INTEGER NOT NULL DEFAULT 0,
            first_recorded_at TEXT,
            last_recorded_at TEXT,
            finalized INTEGER NOT NULL DEFAULT 0,
            pv_energy_kwh REAL NOT NULL DEFAULT 0.0,
            load_energy_kwh REAL NOT NULL DEFAULT 0.0,
            battery_charge_energy_kwh REAL NOT NULL DEFAULT 0.0,
            battery_discharge_energy_kwh REAL NOT NULL DEFAULT 0.0,
            grid_export_energy_kwh REAL NOT NULL DEFAULT 0.0,
            pv_to_load_energy_kwh REAL NOT NULL DEFAULT 0.0,
            pv_to_battery_energy_kwh REAL NOT NULL DEFAULT 0.0,
            battery_to_load_energy_kwh REAL NOT NULL DEFAULT 0.0,
            grid_to_load_energy_kwh REAL NOT NULL DEFAULT 0.0,
            grid_to_battery_energy_kwh REAL NOT NULL DEFAULT 0.0,
            earned_feed_in_eur REAL NOT NULL DEFAULT 0.0,
            earned_savings_eur REAL NOT NULL DEFAULT 0.0,
            updated_at TEXT NOT NULL
        ) WITHOUT ROWID;
        CREATE INDEX IF NOT EXISTS idx_energy_summary_months_year
            ON energy_summary_months(local_year, local_month);
        CREATE INDEX IF NOT EXISTS idx_energy_summary_months_peak_pv
            ON energy_summary_months(pv_energy_kwh DESC, local_month ASC);

        CREATE TABLE IF NOT EXISTS energy_summary_years (
            local_year TEXT PRIMARY KEY,
            interval_count INTEGER NOT NULL DEFAULT 0,
            sample_count INTEGER NOT NULL DEFAULT 0,
            covered_seconds REAL NOT NULL DEFAULT 0.0,
            missing_intervals INTEGER NOT NULL DEFAULT 0,
            first_recorded_at TEXT,
            last_recorded_at TEXT,
            finalized INTEGER NOT NULL DEFAULT 0,
            pv_energy_kwh REAL NOT NULL DEFAULT 0.0,
            load_energy_kwh REAL NOT NULL DEFAULT 0.0,
            battery_charge_energy_kwh REAL NOT NULL DEFAULT 0.0,
            battery_discharge_energy_kwh REAL NOT NULL DEFAULT 0.0,
            grid_export_energy_kwh REAL NOT NULL DEFAULT 0.0,
            pv_to_load_energy_kwh REAL NOT NULL DEFAULT 0.0,
            pv_to_battery_energy_kwh REAL NOT NULL DEFAULT 0.0,
            battery_to_load_energy_kwh REAL NOT NULL DEFAULT 0.0,
            grid_to_load_energy_kwh REAL NOT NULL DEFAULT 0.0,
            grid_to_battery_energy_kwh REAL NOT NULL DEFAULT 0.0,
            earned_feed_in_eur REAL NOT NULL DEFAULT 0.0,
            earned_savings_eur REAL NOT NULL DEFAULT 0.0,
            updated_at TEXT NOT NULL
        ) WITHOUT ROWID;
        CREATE INDEX IF NOT EXISTS idx_energy_summary_years_peak_pv
            ON energy_summary_years(pv_energy_kwh DESC, local_year ASC);

        CREATE TABLE IF NOT EXISTS energy_quality_summary_days (
            local_day TEXT NOT NULL,
            quality TEXT NOT NULL,
            interval_count INTEGER NOT NULL DEFAULT 0,
            integrated_interval_count INTEGER NOT NULL DEFAULT 0,
            dropped_interval_count INTEGER NOT NULL DEFAULT 0,
            integrated_seconds REAL NOT NULL DEFAULT 0.0,
            dropped_seconds REAL NOT NULL DEFAULT 0.0,
            observed_interval_seconds REAL NOT NULL DEFAULT 0.0,
            max_interval_seconds REAL NOT NULL DEFAULT 0.0,
            positive_interval_count INTEGER NOT NULL DEFAULT 0,
            pv_energy_kwh REAL NOT NULL DEFAULT 0.0,
            load_energy_kwh REAL NOT NULL DEFAULT 0.0,
            grid_export_energy_kwh REAL NOT NULL DEFAULT 0.0,
            grid_import_energy_kwh REAL NOT NULL DEFAULT 0.0,
            grid_to_load_energy_kwh REAL NOT NULL DEFAULT 0.0,
            grid_to_battery_energy_kwh REAL NOT NULL DEFAULT 0.0,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(local_day, quality)
        ) WITHOUT ROWID;
        CREATE INDEX IF NOT EXISTS idx_energy_quality_summary_days_quality
            ON energy_quality_summary_days(quality, local_day);

        CREATE TABLE IF NOT EXISTS summary_rollup_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        ) WITHOUT ROWID;

        CREATE TABLE IF NOT EXISTS raw_frames (
            recorded_at TEXT NOT NULL,
            command TEXT NOT NULL,
            request_hex TEXT NOT NULL,
            response_hex TEXT NOT NULL,
            payload_ascii TEXT NOT NULL,
            crc_ok INTEGER NOT NULL,
            PRIMARY KEY(recorded_at, command)
        );

        DROP VIEW IF EXISTS history_samples;
        CREATE VIEW history_samples AS
        SELECT
            recorded_at,
            recorded_minute,
            local_day,
            local_month,
            local_year,
            operation_mode,
            fault,
            ac_input_voltage_v,
            ac_output_voltage_v,
            ac_output_active_power_w,
            ac_output_load_percent,
            battery_voltage_v,
            battery_state_of_charge_percent,
            battery_charge_current_a,
            battery_discharge_current_a,
            battery_charge_power_w,
            battery_discharge_power_w,
            pv_input_voltage_v,
            pv_input_current_a,
            pv_power_w,
            pv_power_semantics,
            solar_feed_to_grid_power_w
        FROM compressed_samples_10m
        UNION ALL
        SELECT
            recorded_at,
            recorded_minute,
            local_day,
            local_month,
            local_year,
            operation_mode,
            fault,
            ac_input_voltage_v,
            ac_output_voltage_v,
            ac_output_active_power_w,
            ac_output_load_percent,
            battery_voltage_v,
            battery_state_of_charge_percent,
            battery_charge_current_a,
            battery_discharge_current_a,
            battery_charge_power_w,
            battery_discharge_power_w,
            pv_input_voltage_v,
            pv_input_current_a,
            pv_power_w,
            pv_power_semantics,
            solar_feed_to_grid_power_w
        FROM samples;
        """
    )
    _ensure_table_columns(
        db,
        "current_snapshot",
        {
            "pricing_json": "TEXT",
        },
    )
    _ensure_table_columns(
        db,
        "samples",
        {
            "archive_bucket_local": "TEXT",
            "battery_charge_power_w": "REAL",
            "battery_discharge_power_w": "REAL",
        },
    )
    _ensure_table_columns(
        db,
        "minute_samples",
        {
            "archive_bucket_local": "TEXT",
            "battery_charge_power_w": "REAL",
            "battery_discharge_power_w": "REAL",
        },
    )
    _ensure_table_columns(
        db,
        "compressed_samples_10m",
        {
            "battery_charge_power_w": "REAL",
            "battery_discharge_power_w": "REAL",
        },
    )
    _ensure_table_columns(
        db,
        "derived_energy_intervals",
        {
            "pv_to_load_energy_kwh": "REAL NOT NULL DEFAULT 0.0",
            "pv_to_battery_energy_kwh": "REAL NOT NULL DEFAULT 0.0",
            "battery_to_load_energy_kwh": "REAL NOT NULL DEFAULT 0.0",
            "grid_to_load_energy_kwh": "REAL NOT NULL DEFAULT 0.0",
            "grid_to_battery_energy_kwh": "REAL NOT NULL DEFAULT 0.0",
            "grid_price_eur_per_kwh": "REAL NOT NULL DEFAULT 0.0",
            "feed_in_revenue_eur_per_kwh": "REAL NOT NULL DEFAULT 0.0",
            "quality": "TEXT NOT NULL DEFAULT 'unknown'",
        },
    )
    _backfill_archive_bucket_column(db, "samples")
    _backfill_archive_bucket_column(db, "minute_samples")
    db.execute_script(
        """
        CREATE INDEX IF NOT EXISTS idx_samples_archive_bucket
            ON samples(archive_bucket_local);
        CREATE INDEX IF NOT EXISTS idx_minute_samples_archive_bucket
            ON minute_samples(archive_bucket_local);
        CREATE INDEX IF NOT EXISTS idx_energy_recorded_quality
            ON derived_energy_intervals(recorded_at, quality);
        """
    )
    backfill_flow_energy_columns(db)
    _ensure_energy_rollups(db)


def flatten_snapshot(
    snapshot: dict[str, Any],
    *,
    store_raw_snapshot: bool = False,
) -> dict[str, Any]:
    recorded_minute, archive_bucket_local, local_day, local_month, local_year = _local_parts(
        snapshot["recorded_at"]
    )
    inverter_status = snapshot.get("inverter_status") or {}
    qpigs_status = snapshot.get("qpigs_status_flags") or {}
    device_status2 = snapshot.get("device_status2") or {}
    warnings = snapshot.get("warning_bits") or snapshot.get("warnings") or {}
    flags = snapshot.get("flags") or {}
    qpiri = snapshot.get("qpiri") or snapshot.get("qpiri_settings") or {}

    row = {
        "recorded_at": snapshot["recorded_at"],
        "recorded_minute": recorded_minute,
        "archive_bucket_local": archive_bucket_local,
        "local_day": local_day,
        "local_month": local_month,
        "local_year": local_year,
        "serial_number": snapshot.get("serial_number"),
        "protocol_id": snapshot.get("protocol_id"),
        "device_id": snapshot.get("device_id"),
        "operation_mode_code": snapshot.get("operation_mode_code"),
        "operation_mode": snapshot.get("operation_mode"),
        "fault_code": snapshot.get("fault_code"),
        "fault": snapshot.get("fault"),
        "ac_input_voltage_v": snapshot.get("ac_input_voltage_v"),
        "ac_input_frequency_hz": snapshot.get("ac_input_frequency_hz"),
        "ac_output_voltage_v": snapshot.get("ac_output_voltage_v"),
        "ac_output_frequency_hz": snapshot.get("ac_output_frequency_hz"),
        "ac_output_apparent_power_va": snapshot.get("ac_output_apparent_power_va"),
        "ac_output_active_power_w": snapshot.get("ac_output_active_power_w"),
        "ac_output_load_percent": snapshot.get("ac_output_load_percent"),
        "battery_voltage_v": snapshot.get("battery_voltage_v"),
        "battery_charge_current_a": snapshot.get("battery_charge_current_a"),
        "battery_state_of_charge_percent": snapshot.get(
            "battery_state_of_charge_percent"
        ),
        "pv_input_voltage_v": snapshot.get("pv_input_voltage_v"),
        "total_charging_current_a": snapshot.get("total_charging_current_a"),
        "total_ac_output_apparent_power_va": snapshot.get(
            "total_ac_output_apparent_power_va"
        ),
        "total_output_active_power_w": snapshot.get("total_output_active_power_w"),
        "total_output_load_percent": snapshot.get("total_output_load_percent"),
        "ac_output_mode_code": snapshot.get("ac_output_mode_code"),
        "ac_output_mode": snapshot.get("ac_output_mode"),
        "battery_charger_source_priority_code": snapshot.get(
            "battery_charger_source_priority_code"
        ),
        "battery_charger_source_priority": snapshot.get(
            "battery_charger_source_priority"
        ),
        "max_charging_current_set_a": snapshot.get("max_charging_current_set_a"),
        "max_charging_current_possible_a": snapshot.get(
            "max_charging_current_possible_a"
        ),
        "max_ac_charging_current_set_a": snapshot.get(
            "max_ac_charging_current_set_a"
        ),
        "pv_input_current_a": snapshot.get("pv_input_current_a"),
        "battery_discharge_current_a": snapshot.get("battery_discharge_current_a"),
        "pv_power_w": snapshot.get("pv_power_w"),
        "pv_power_semantics": snapshot.get("pv_power_semantics"),
        "battery_charge_power_w": snapshot.get("battery_charge_power_w"),
        "battery_discharge_power_w": snapshot.get("battery_discharge_power_w"),
        "bus_voltage_v": snapshot.get("bus_voltage_v"),
        "inverter_temperature_c": snapshot.get("inverter_temperature_c"),
        "battery_voltage_from_scc_v": snapshot.get("battery_voltage_from_scc_v"),
        "pv_charging_power_w": snapshot.get("pv_charging_power_w"),
        "solar_feed_to_grid_power_w": snapshot.get("solar_feed_to_grid_power_w"),
        "mppt_active": _bool_to_int(inverter_status.get("mppt_active")),
        "ac_charging_on": _bool_to_int(inverter_status.get("ac_charging_on")),
        "solar_charging_on": _bool_to_int(inverter_status.get("solar_charging_on")),
        "battery_state_code": inverter_status.get("battery_state_code"),
        "battery_state": inverter_status.get("battery_state"),
        "ac_input_available": _bool_to_int(
            inverter_status.get("ac_input_available")
        ),
        "ac_output_on": _bool_to_int(inverter_status.get("ac_output_on")),
        "inverter_status_raw": inverter_status.get("raw"),
        "inverter_status_json": _json(inverter_status),
        "qpigs_status_flags_raw": snapshot.get("qpigs_status_flags_raw"),
        "qpigs_status_flags_json": _json(qpigs_status),
        "device_status2_raw": snapshot.get("device_status2_raw"),
        "device_status2_json": _json(device_status2),
        "solar_feed_to_grid_enabled": _bool_to_int(
            snapshot.get("solar_feed_to_grid_enabled")
        ),
        "country_code": snapshot.get("country_code"),
        "qpiws_raw": snapshot.get("warning_bitmap"),
        "warnings_json": _json(warnings),
        "qflag_raw": snapshot.get("flag_blob"),
        "flags_json": _json(flags),
        "qpiri_json": _json(qpiri),
        "metadata_json": _json(snapshot.get("metadata") or {}),
        "raw_snapshot_json": _json(snapshot if store_raw_snapshot else {}),
    }
    return row


def insert_sample(db, row: dict[str, Any]):
    placeholders = ", ".join(["?"] * len(SAMPLE_COLUMNS))
    columns = ", ".join(SAMPLE_COLUMNS)
    values = [row.get(column) for column in SAMPLE_COLUMNS]
    db.execute(
        f"INSERT OR REPLACE INTO samples ({columns}) VALUES ({placeholders})",
        values,
    )

    minute_columns = ["recorded_minute"] + [c for c in SAMPLE_COLUMNS if c != "recorded_minute"]
    minute_placeholders = ", ".join(["?"] * len(minute_columns))
    minute_values = [row.get(column) for column in minute_columns]
    db.execute(
        "INSERT OR REPLACE INTO minute_samples "
        f"({', '.join(minute_columns)}) VALUES ({minute_placeholders})",
        minute_values,
    )


def compact_historical_samples(
    db,
    reference_time: Optional[datetime] = None,
    retention_hours: int = RAW_HISTORY_RETENTION_HOURS,
    bucket_minutes: int = ARCHIVED_SAMPLE_BUCKET_MINUTES,
):
    del bucket_minutes  # The SQL expressions are defined for the configured bucket size.
    current_time = reference_time or datetime.now(timezone.utc)
    max_bucket_local = _archived_bucket_start_local(
        reference_time=current_time,
        retention_hours=retention_hours,
    )
    current_local_day = current_time.astimezone().strftime("%Y-%m-%d")
    rows = db.execute(
        f"""
        WITH eligible AS (
            SELECT
                archive_bucket_local AS bucket_local,
                recorded_at,
                local_day,
                local_month,
                local_year,
                operation_mode,
                fault,
                pv_power_semantics,
                ac_input_voltage_v,
                ac_output_voltage_v,
                ac_output_active_power_w,
                ac_output_load_percent,
                battery_voltage_v,
                battery_state_of_charge_percent,
                battery_charge_current_a,
                battery_discharge_current_a,
                battery_charge_power_w,
                battery_discharge_power_w,
                pv_input_voltage_v,
                pv_input_current_a,
                pv_power_w,
                solar_feed_to_grid_power_w
            FROM samples
            WHERE archive_bucket_local <= ?
               OR local_day < ?
        ),
        averages AS (
            SELECT
                bucket_local,
                COUNT(*) AS sample_count,
                AVG(ac_input_voltage_v) AS ac_input_voltage_v,
                AVG(ac_output_voltage_v) AS ac_output_voltage_v,
                AVG(ac_output_active_power_w) AS ac_output_active_power_w,
                AVG(ac_output_load_percent) AS ac_output_load_percent,
                AVG(battery_voltage_v) AS battery_voltage_v,
                AVG(battery_state_of_charge_percent) AS battery_state_of_charge_percent,
                AVG(battery_charge_current_a) AS battery_charge_current_a,
                AVG(battery_discharge_current_a) AS battery_discharge_current_a,
                AVG(battery_charge_power_w) AS battery_charge_power_w,
                AVG(battery_discharge_power_w) AS battery_discharge_power_w,
                AVG(pv_input_voltage_v) AS pv_input_voltage_v,
                AVG(pv_input_current_a) AS pv_input_current_a,
                AVG(pv_power_w) AS pv_power_w,
                AVG(solar_feed_to_grid_power_w) AS solar_feed_to_grid_power_w
            FROM eligible
            GROUP BY bucket_local
        ),
        latest AS (
            SELECT bucket_local, MAX(recorded_at) AS latest_recorded_at
            FROM eligible
            GROUP BY bucket_local
        )
        SELECT
            a.bucket_local,
            a.sample_count,
            a.ac_input_voltage_v,
            a.ac_output_voltage_v,
            a.ac_output_active_power_w,
            a.ac_output_load_percent,
            a.battery_voltage_v,
            a.battery_state_of_charge_percent,
            a.battery_charge_current_a,
            a.battery_discharge_current_a,
            a.battery_charge_power_w,
            a.battery_discharge_power_w,
            a.pv_input_voltage_v,
            a.pv_input_current_a,
            a.pv_power_w,
            a.solar_feed_to_grid_power_w,
            l.latest_recorded_at,
            e.operation_mode,
            e.fault,
            e.pv_power_semantics
        FROM averages a
        JOIN latest l ON l.bucket_local = a.bucket_local
        JOIN eligible e
            ON e.bucket_local = l.bucket_local
            AND e.recorded_at = l.latest_recorded_at
        ORDER BY a.bucket_local ASC
        """,
        [max_bucket_local, current_local_day],
    )
    if not rows:
        return

    insert_rows = []
    for row in rows:
        bucket_local = row["bucket_local"]
        bucket_recorded_at = _archived_row_recorded_at(
            bucket_local,
            row["latest_recorded_at"],
        )
        local_bucket_dt = datetime.fromisoformat(bucket_local)
        insert_rows.append(
            (
                bucket_local,
                bucket_recorded_at,
                bucket_local,
                local_bucket_dt.strftime("%Y-%m-%d"),
                local_bucket_dt.strftime("%Y-%m"),
                local_bucket_dt.strftime("%Y"),
                row["operation_mode"],
                row["fault"],
                row["ac_input_voltage_v"],
                row["ac_output_voltage_v"],
                row["ac_output_active_power_w"],
                row["ac_output_load_percent"],
                row["battery_voltage_v"],
                row["battery_state_of_charge_percent"],
                row["battery_charge_current_a"],
                row["battery_discharge_current_a"],
                row["battery_charge_power_w"],
                row["battery_discharge_power_w"],
                row["pv_input_voltage_v"],
                row["pv_input_current_a"],
                row["pv_power_w"],
                row["pv_power_semantics"] or SEMANTICS_DERIVED,
                row["solar_feed_to_grid_power_w"],
                row["sample_count"],
            )
        )

    db.executemany(
        """
        INSERT OR REPLACE INTO compressed_samples_10m (
            bucket_local,
            recorded_at,
            recorded_minute,
            local_day,
            local_month,
            local_year,
            operation_mode,
            fault,
            ac_input_voltage_v,
            ac_output_voltage_v,
            ac_output_active_power_w,
            ac_output_load_percent,
            battery_voltage_v,
            battery_state_of_charge_percent,
            battery_charge_current_a,
            battery_discharge_current_a,
            battery_charge_power_w,
            battery_discharge_power_w,
            pv_input_voltage_v,
            pv_input_current_a,
            pv_power_w,
            pv_power_semantics,
            solar_feed_to_grid_power_w,
            sample_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        insert_rows,
    )
    db.execute(
        "DELETE FROM samples WHERE archive_bucket_local <= ? OR local_day < ?",
        [max_bucket_local, current_local_day],
    )
    db.execute(
        """
        DELETE FROM minute_samples
        WHERE archive_bucket_local <= ?
           OR local_day < ?
        """,
        [max_bucket_local, current_local_day],
    )
    has_high_res = db.fetchone(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'high_res'"
    )
    if has_high_res:
        keep_high_res_from = (
            current_time.astimezone() - timedelta(days=1)
        ).strftime("%Y-%m-%d")
        db.execute("DELETE FROM high_res WHERE date < ?", [keep_high_res_from])


def _next_local_day(local_day: str) -> str:
    return (datetime.fromisoformat(local_day) + timedelta(days=1)).date().isoformat()


def prune_detailed_energy_intervals(
    db,
    reference_time: Optional[datetime] = None,
    retention_days: int = DEFAULT_ENERGY_INTERVAL_RETENTION_DAYS,
    max_days: int = DEFAULT_ENERGY_INTERVAL_PRUNE_MAX_DAYS,
) -> dict[str, Any]:
    retention_days = int(retention_days or 0)
    max_days = max(int(max_days or 1), 1)
    if retention_days <= 0:
        return {
            "enabled": False,
            "cutoff_day": None,
            "candidate_days": 0,
            "pruned_days": 0,
            "pruned_intervals": 0,
            "limited": False,
            "skipped_days": [],
        }

    current_time = reference_time or datetime.now(timezone.utc)
    cutoff_day = (
        current_time.astimezone() - timedelta(days=retention_days)
    ).date().isoformat()
    candidates = db.execute(
        """
        SELECT
            local_day,
            MAX(local_month) AS local_month,
            MAX(local_year) AS local_year,
            COUNT(*) AS interval_count
        FROM derived_energy_intervals
        WHERE local_day < ?
        GROUP BY local_day
        ORDER BY local_day ASC
        LIMIT ?
        """,
        [cutoff_day, max_days + 1],
    )
    limited = len(candidates) > max_days
    if limited:
        candidates = candidates[:max_days]
    if not candidates:
        return {
            "enabled": True,
            "cutoff_day": cutoff_day,
            "candidate_days": 0,
            "pruned_days": 0,
            "pruned_intervals": 0,
            "limited": False,
            "skipped_days": [],
        }

    pruned_days = []
    skipped_days = []
    pruned_intervals = 0
    months = set()
    years = set()
    for candidate in candidates:
        local_day = candidate["local_day"]
        with db.transaction():
            _refresh_day_summary(db, local_day, reference_time=current_time)
            summary = db.fetchone(
                f"""
                SELECT finalized, interval_count
                FROM {SUMMARY_ROLLUP_TABLES["day"]}
                WHERE local_day = ?
                """,
                [local_day],
            )
            quality_summary_days = count_reconciliation_quality_summary_days(
                db,
                local_day,
                _next_local_day(local_day),
            )
            summary_ready = (
                summary is not None
                and int(summary["finalized"] or 0) == 1
                and int(summary["interval_count"] or 0) > 0
                and quality_summary_days > 0
            )
            if not summary_ready:
                skipped_days.append(local_day)
                continue

            interval_count = int(candidate["interval_count"] or 0)
            db.execute(
                "DELETE FROM derived_energy_intervals WHERE local_day = ?",
                [local_day],
            )
            pruned_intervals += interval_count
            pruned_days.append(local_day)
            months.add(candidate["local_month"] or local_day[:7])
            years.add(candidate["local_year"] or local_day[:4])

    with db.transaction():
        for local_month in sorted(month for month in months if month):
            _refresh_month_summary(db, local_month, reference_time=current_time)
        for local_year in sorted(year for year in years if year):
            _refresh_year_summary(db, local_year, reference_time=current_time)

    return {
        "enabled": True,
        "cutoff_day": cutoff_day,
        "candidate_days": len(candidates),
        "pruned_days": len(pruned_days),
        "pruned_intervals": pruned_intervals,
        "limited": limited,
        "skipped_days": skipped_days,
    }


def history_samples_for_day(db, local_day: str):
    return db.execute(
        """
        SELECT
            recorded_at,
            pv_power_w,
            ac_output_active_power_w,
            battery_charge_power_w,
            battery_discharge_power_w,
            solar_feed_to_grid_power_w
        FROM history_samples
        WHERE local_day = ?
        ORDER BY recorded_at ASC
        """,
        [local_day],
    )


def get_latest_sample(db) -> Optional[dict[str, Any]]:
    row = db.fetchone(
        "SELECT * FROM samples ORDER BY recorded_at DESC LIMIT 1"
    )
    if row:
        return dict(row)

    current = get_current_snapshot(
        db,
        include_cumulative=False,
        include_capabilities=False,
    )
    if current and current.get("snapshot"):
        return flatten_snapshot(current["snapshot"])
    return None


def _power_integral_kwh(previous_value, current_value, interval_seconds):
    if interval_seconds <= 0:
        return 0.0
    if previous_value is None and current_value is None:
        return 0.0
    if previous_value is None:
        previous_value = current_value
    if current_value is None:
        current_value = previous_value
    previous_value = max(float(previous_value), 0.0)
    current_value = max(float(current_value), 0.0)
    average_power_w = (previous_value + current_value) / 2.0
    return average_power_w * interval_seconds / 3_600_000.0


def _interval_power_quality(*rows: dict[str, Any]) -> str:
    semantics = {row.get("pv_power_semantics") for row in rows}
    if SEMANTICS_CACHED in semantics:
        return "cached"
    if SEMANTICS_DERIVED in semantics:
        return "derived"
    return "exact"


def calculate_energy_deltas(
    previous_row: Optional[dict[str, Any]],
    current_row: dict[str, Any],
    max_gap_seconds: float,
    pricing: Optional[dict[str, float]] = None,
    *,
    expected_interval_seconds: Optional[float] = None,
    max_integrated_gap_seconds: Optional[float] = None,
) -> dict[str, Any]:
    max_integrated_gap_seconds = (
        float(max_integrated_gap_seconds)
        if max_integrated_gap_seconds is not None
        else float(max_gap_seconds)
    )
    expected_interval_seconds = (
        float(expected_interval_seconds)
        if expected_interval_seconds is not None
        else None
    )

    if previous_row is None:
        return {
            "recorded_at": current_row["recorded_at"],
            "previous_recorded_at": None,
            "interval_seconds": 0.0,
            "contiguous": 0,
            "local_day": current_row["local_day"],
            "local_month": current_row["local_month"],
            "local_year": current_row["local_year"],
            "pv_energy_kwh": 0.0,
            "load_energy_kwh": 0.0,
            "battery_charge_energy_kwh": 0.0,
            "battery_discharge_energy_kwh": 0.0,
            "grid_export_energy_kwh": 0.0,
            "pv_to_load_energy_kwh": 0.0,
            "pv_to_battery_energy_kwh": 0.0,
            "battery_to_load_energy_kwh": 0.0,
            "grid_to_load_energy_kwh": 0.0,
            "grid_to_battery_energy_kwh": 0.0,
            "grid_price_eur_per_kwh": max(float((pricing or {}).get("grid_price_eur_per_kwh", 0.0)), 0.0),
            "feed_in_revenue_eur_per_kwh": max(float((pricing or {}).get("feed_in_revenue_eur_per_kwh", 0.0)), 0.0),
            "quality": "gap_dropped",
            "derived_json": _json(
                {
                    "reason": "first_sample",
                    "quality": "gap_dropped",
                    "expected_interval_seconds": expected_interval_seconds,
                    "max_integrated_gap_seconds": max_integrated_gap_seconds,
                }
            ),
        }

    previous_at = _utc_from_iso(previous_row["recorded_at"])
    current_at = _utc_from_iso(current_row["recorded_at"])
    interval_seconds = (current_at - previous_at).total_seconds()
    contiguous = int(0 < interval_seconds <= max_integrated_gap_seconds)

    if not contiguous:
        if interval_seconds <= 0:
            reason = "time_reversal"
        elif interval_seconds <= max_gap_seconds:
            reason = "gap_dropped"
        else:
            reason = "gap_or_time_reversal"
        return {
            "recorded_at": current_row["recorded_at"],
            "previous_recorded_at": previous_row["recorded_at"],
            "interval_seconds": max(interval_seconds, 0.0),
            "contiguous": 0,
            "local_day": current_row["local_day"],
            "local_month": current_row["local_month"],
            "local_year": current_row["local_year"],
            "pv_energy_kwh": 0.0,
            "load_energy_kwh": 0.0,
            "battery_charge_energy_kwh": 0.0,
            "battery_discharge_energy_kwh": 0.0,
            "grid_export_energy_kwh": 0.0,
            "pv_to_load_energy_kwh": 0.0,
            "pv_to_battery_energy_kwh": 0.0,
            "battery_to_load_energy_kwh": 0.0,
            "grid_to_load_energy_kwh": 0.0,
            "grid_to_battery_energy_kwh": 0.0,
            "grid_price_eur_per_kwh": max(float((pricing or {}).get("grid_price_eur_per_kwh", 0.0)), 0.0),
            "feed_in_revenue_eur_per_kwh": max(float((pricing or {}).get("feed_in_revenue_eur_per_kwh", 0.0)), 0.0),
            "quality": "gap_dropped",
            "derived_json": _json(
                {
                    "reason": reason,
                    "quality": "gap_dropped",
                    "expected_interval_seconds": expected_interval_seconds,
                    "max_integrated_gap_seconds": max_integrated_gap_seconds,
                    "max_gap_seconds": max_gap_seconds,
                }
            ),
        }

    previous_flows = calculate_power_flow_breakdown(previous_row)
    current_flows = calculate_power_flow_breakdown(current_row)
    interval_quality = _interval_power_quality(previous_row, current_row)
    uses_derived_power = interval_quality == "derived"
    uses_cached_power = interval_quality == "cached"
    gap_integrated = bool(
        expected_interval_seconds and interval_seconds > expected_interval_seconds * 1.5
    )
    if gap_integrated:
        interval_quality = "gap_integrated"

    return {
        "recorded_at": current_row["recorded_at"],
        "previous_recorded_at": previous_row["recorded_at"],
        "interval_seconds": interval_seconds,
        "contiguous": 1,
        "local_day": current_row["local_day"],
        "local_month": current_row["local_month"],
        "local_year": current_row["local_year"],
        "pv_energy_kwh": _power_integral_kwh(
            previous_row.get("pv_power_w"),
            current_row.get("pv_power_w"),
            interval_seconds,
        ),
        "load_energy_kwh": _power_integral_kwh(
            previous_row.get("ac_output_active_power_w"),
            current_row.get("ac_output_active_power_w"),
            interval_seconds,
        ),
        "battery_charge_energy_kwh": _power_integral_kwh(
            previous_row.get("battery_charge_power_w"),
            current_row.get("battery_charge_power_w"),
            interval_seconds,
        ),
        "battery_discharge_energy_kwh": _power_integral_kwh(
            previous_row.get("battery_discharge_power_w"),
            current_row.get("battery_discharge_power_w"),
            interval_seconds,
        ),
        "grid_export_energy_kwh": _power_integral_kwh(
            previous_row.get("solar_feed_to_grid_power_w"),
            current_row.get("solar_feed_to_grid_power_w"),
            interval_seconds,
        ),
        "pv_to_load_energy_kwh": _power_integral_kwh(
            previous_flows["pv_to_load_power_w"],
            current_flows["pv_to_load_power_w"],
            interval_seconds,
        ),
        "pv_to_battery_energy_kwh": _power_integral_kwh(
            previous_flows["pv_to_battery_power_w"],
            current_flows["pv_to_battery_power_w"],
            interval_seconds,
        ),
        "battery_to_load_energy_kwh": _power_integral_kwh(
            previous_flows["battery_to_load_power_w"],
            current_flows["battery_to_load_power_w"],
            interval_seconds,
        ),
        "grid_to_load_energy_kwh": _power_integral_kwh(
            previous_flows["grid_to_load_power_w"],
            current_flows["grid_to_load_power_w"],
            interval_seconds,
        ),
        "grid_to_battery_energy_kwh": _power_integral_kwh(
            previous_flows["grid_to_battery_power_w"],
            current_flows["grid_to_battery_power_w"],
            interval_seconds,
        ),
        "grid_price_eur_per_kwh": max(float((pricing or {}).get("grid_price_eur_per_kwh", 0.0)), 0.0),
        "feed_in_revenue_eur_per_kwh": max(float((pricing or {}).get("feed_in_revenue_eur_per_kwh", 0.0)), 0.0),
        "quality": interval_quality,
        "derived_json": _json(
            {
                "reason": "integrated",
                "quality": interval_quality,
                "expected_interval_seconds": expected_interval_seconds,
                "max_integrated_gap_seconds": max_integrated_gap_seconds,
                "previous_pv_power_semantics": previous_row.get("pv_power_semantics"),
                "current_pv_power_semantics": current_row.get("pv_power_semantics"),
                "uses_derived_power": uses_derived_power,
                "uses_cached_power": uses_cached_power,
                "gap_integrated": gap_integrated,
            }
        ),
    }


def insert_energy_delta(db, delta: dict[str, Any]):
    db.execute(
        """
        INSERT OR REPLACE INTO derived_energy_intervals (
            recorded_at,
            previous_recorded_at,
            interval_seconds,
            contiguous,
            local_day,
            local_month,
            local_year,
            pv_energy_kwh,
            load_energy_kwh,
            battery_charge_energy_kwh,
            battery_discharge_energy_kwh,
            grid_export_energy_kwh,
            pv_to_load_energy_kwh,
            pv_to_battery_energy_kwh,
            battery_to_load_energy_kwh,
            grid_to_load_energy_kwh,
            grid_to_battery_energy_kwh,
            grid_price_eur_per_kwh,
            feed_in_revenue_eur_per_kwh,
            quality,
            derived_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            delta["recorded_at"],
            delta["previous_recorded_at"],
            delta["interval_seconds"],
            delta["contiguous"],
            delta["local_day"],
            delta["local_month"],
            delta["local_year"],
            delta["pv_energy_kwh"],
            delta["load_energy_kwh"],
            delta["battery_charge_energy_kwh"],
            delta["battery_discharge_energy_kwh"],
            delta["grid_export_energy_kwh"],
            delta["pv_to_load_energy_kwh"],
            delta["pv_to_battery_energy_kwh"],
            delta["battery_to_load_energy_kwh"],
            delta["grid_to_load_energy_kwh"],
            delta["grid_to_battery_energy_kwh"],
            delta["grid_price_eur_per_kwh"],
            delta["feed_in_revenue_eur_per_kwh"],
            delta["quality"],
            delta["derived_json"],
        ],
    )


def insert_raw_frames(db, recorded_at: str, frames: list[dict[str, Any]]):
    rows = []
    for frame in frames:
        rows.append(
            (
                recorded_at,
                frame["command"],
                frame["request_hex"],
                frame["response_hex"],
                frame["payload_ascii"],
                1 if frame["crc_ok"] else 0,
            )
        )
    if rows:
        db.executemany(
            """
            INSERT OR REPLACE INTO raw_frames (
                recorded_at,
                command,
                request_hex,
                response_hex,
                payload_ascii,
                crc_ok
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def update_capabilities(db, capabilities: dict[str, dict[str, Any]]):
    rows = []
    for command, data in capabilities.items():
        rows.append(
            (
                command,
                1 if data.get("supported") else 0,
                data.get("checked_at"),
                data.get("protocol_id"),
                data.get("field_count"),
                1 if data.get("crc_ok") else 0,
                data.get("response_preview"),
                _json(data.get("parsed")),
                data.get("raw_payload"),
            )
        )
    if rows:
        db.executemany(
            """
            INSERT OR REPLACE INTO capabilities (
                command,
                supported,
                checked_at,
                protocol_id,
                field_count,
                crc_ok,
                response_preview,
                parsed_json,
                raw_payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def get_capabilities(db) -> dict[str, Any]:
    rows = db.execute("SELECT * FROM capabilities ORDER BY command ASC")
    result = {}
    for row in rows:
        result[row["command"]] = {
            "supported": bool(row["supported"]),
            "checked_at": row["checked_at"],
            "protocol_id": row["protocol_id"],
            "field_count": row["field_count"],
            "crc_ok": bool(row["crc_ok"]),
            "response_preview": row["response_preview"],
            "raw_payload": row["raw_payload"],
            "parsed": json.loads(row["parsed_json"]) if row["parsed_json"] else None,
        }
    return result


def _empty_bucket_totals(bucket: str, value: Optional[str] = None) -> dict[str, Any]:
    return {
        "bucket": bucket,
        "value": value if value is not None else "all_time",
        "semantics": SEMANTICS_DERIVED,
        "interval_count": 0,
        "sample_count": 0,
        "covered_seconds": 0.0,
        "missing_intervals": 0,
        "first_recorded_at": None,
        "last_recorded_at": None,
        "finalized": 0,
        **{column: 0.0 for column in CUMULATIVE_TOTAL_COLUMNS},
    }


def _bucket_totals_from_row(
    bucket: str,
    value: Optional[str],
    row: Optional[dict[str, Any]],
) -> dict[str, Any]:
    result = _empty_bucket_totals(bucket, value)
    if row is None:
        return result

    result["interval_count"] = int(row.get("interval_count") or 0)
    result["sample_count"] = int(row.get("sample_count") or 0)
    result["covered_seconds"] = float(row.get("covered_seconds") or 0.0)
    result["missing_intervals"] = int(row.get("missing_intervals") or 0)
    result["first_recorded_at"] = row.get("first_recorded_at")
    result["last_recorded_at"] = row.get("last_recorded_at")
    result["finalized"] = int(row.get("finalized") or 0)
    for column in CUMULATIVE_TOTAL_COLUMNS:
        result[column] = float(row.get(column) or 0.0)
    return result


def get_best_bucket_total(db, bucket: str) -> Optional[dict[str, Any]]:
    if bucket not in SUMMARY_ROLLUP_TABLES:
        raise ValueError("bucket must be day, month, or year")

    key_column = SUMMARY_ROLLUP_KEYS[bucket]
    table = SUMMARY_ROLLUP_TABLES[bucket]
    row = db.fetchone(
        f"""
        SELECT
            {key_column} AS bucket,
            pv_energy_kwh AS produced_kwh
        FROM {table}
        ORDER BY pv_energy_kwh DESC, {key_column} ASC
        LIMIT 1
        """
    )
    return dict(row) if row else None


def get_period_totals(
    db,
    period: str,
    reference_time: Optional[datetime] = None,
) -> dict[str, Any]:
    reference_time = reference_time or datetime.now(timezone.utc)
    local = reference_time.astimezone()
    if period == "today":
        values = get_bucket_totals(db, "day", local.strftime("%Y-%m-%d"))
    elif period == "month":
        values = get_bucket_totals(db, "month", local.strftime("%Y-%m"))
    elif period == "year":
        values = get_bucket_totals(db, "year", local.strftime("%Y"))
    else:
        values = get_bucket_totals(db, "all_time")
    return {
        "period": period,
        "semantics": SEMANTICS_DERIVED,
        **{column: values[column] for column in CUMULATIVE_TOTAL_COLUMNS},
    }


def _empty_period_totals(period: str) -> dict[str, Any]:
    return {
        "period": period,
        "semantics": SEMANTICS_DERIVED,
        **{column: 0.0 for column in CUMULATIVE_TOTAL_COLUMNS},
    }


def _delta_period_totals(delta: Optional[dict[str, Any]], period: str) -> dict[str, Any]:
    values = _empty_period_totals(period)
    if delta is None:
        return values

    for column in ALL_ENERGY_COLUMNS:
        values[column] = max(float((delta or {}).get(column, 0.0) or 0.0), 0.0)

    grid_price = max(float((delta or {}).get("grid_price_eur_per_kwh", 0.0) or 0.0), 0.0)
    feed_in_revenue = max(
        float((delta or {}).get("feed_in_revenue_eur_per_kwh", 0.0) or 0.0),
        0.0,
    )
    values["earned_feed_in_eur"] = values["grid_export_energy_kwh"] * feed_in_revenue
    values["earned_savings_eur"] = (
        values["pv_to_load_energy_kwh"] + values["battery_to_load_energy_kwh"]
    ) * grid_price
    return values


def _merged_period_totals(
    base: Optional[dict[str, Any]],
    delta: Optional[dict[str, Any]],
    period: str,
) -> dict[str, Any]:
    base_values = dict(base or _empty_period_totals(period))
    delta_values = _delta_period_totals(delta, period)
    merged = {
        "period": period,
        "semantics": SEMANTICS_DERIVED,
    }
    for column in CUMULATIVE_TOTAL_COLUMNS:
        merged[column] = max(
            float(base_values.get(column, 0.0) or 0.0)
            + float(delta_values.get(column, 0.0) or 0.0),
            0.0,
        )
    return merged


def _normalized_cached_cumulative(
    cumulative: Optional[dict[str, Any]],
    recorded_at: str,
    reference_time: Optional[datetime] = None,
) -> dict[str, Any]:
    reference_time = reference_time or datetime.now(timezone.utc)
    _, _, current_day, current_month, current_year = _local_parts(
        reference_time.isoformat()
    )
    _, _, cached_day, cached_month, cached_year = _local_parts(recorded_at)
    cumulative = cumulative or {}
    return {
        "today": dict(cumulative.get("today") or _empty_period_totals("today"))
        if cached_day == current_day
        else _empty_period_totals("today"),
        "month": dict(cumulative.get("month") or _empty_period_totals("month"))
        if cached_month == current_month
        else _empty_period_totals("month"),
        "year": dict(cumulative.get("year") or _empty_period_totals("year"))
        if cached_year == current_year
        else _empty_period_totals("year"),
        "all_time": dict(cumulative.get("all_time") or _empty_period_totals("all_time")),
    }


def update_current_snapshot(
    db,
    snapshot: dict[str, Any],
    capabilities: dict[str, Any],
    pricing: Optional[dict[str, Any]] = None,
    reference_time: Optional[datetime] = None,
    delta: Optional[dict[str, Any]] = None,
):
    current_recorded_at = snapshot["recorded_at"]
    previous_current = db.fetchone(
        """
        SELECT recorded_at, cumulative_json
        FROM current_snapshot
        WHERE slot = ?
        """,
        [CURRENT_SNAPSHOT_SLOT],
    )
    cumulative = None
    if previous_current and previous_current["cumulative_json"]:
        previous_cumulative = json.loads(previous_current["cumulative_json"])
        _, _, current_day, current_month, current_year = _local_parts(current_recorded_at)
        _, _, previous_day, previous_month, previous_year = _local_parts(
            previous_current["recorded_at"]
        )

        cumulative = {
            "today": _merged_period_totals(
                previous_cumulative.get("today")
                if previous_day == current_day
                else None,
                delta,
                "today",
            ),
            "month": _merged_period_totals(
                previous_cumulative.get("month")
                if previous_month == current_month
                else None,
                delta,
                "month",
            ),
            "year": _merged_period_totals(
                previous_cumulative.get("year")
                if previous_year == current_year
                else None,
                delta,
                "year",
            ),
            "all_time": _merged_period_totals(
                previous_cumulative.get("all_time"),
                delta,
                "all_time",
            ),
        }

    if cumulative is None:
        cumulative = {
            "today": get_period_totals(db, "today", reference_time),
            "month": get_period_totals(db, "month", reference_time),
            "year": get_period_totals(db, "year", reference_time),
            "all_time": get_period_totals(db, "all_time", reference_time),
        }
    semantics = {
        "ac_output_active_power_w": SEMANTICS_EXACT,
        "ac_output_load_percent": SEMANTICS_EXACT,
        "battery_state_of_charge_percent": SEMANTICS_EXACT,
        "battery_voltage_v": SEMANTICS_EXACT,
        "pv_power_w": snapshot.get("pv_power_semantics", SEMANTICS_UNSUPPORTED),
        "battery_charge_power_w": SEMANTICS_DERIVED,
        "battery_discharge_power_w": SEMANTICS_DERIVED,
    }
    db.execute(
        """
        INSERT OR REPLACE INTO current_snapshot (
            slot,
            recorded_at,
            snapshot_json,
            cumulative_json,
            pricing_json,
            semantics_json,
            capabilities_json,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            CURRENT_SNAPSHOT_SLOT,
            snapshot["recorded_at"],
            _json(snapshot),
            _json(cumulative),
            _json(pricing),
            _json(semantics),
            _json(capabilities),
            datetime.now(timezone.utc).isoformat(),
        ],
    )


def record_snapshot(
    db,
    snapshot: dict[str, Any],
    capabilities: dict[str, Any],
    raw_frames: list[dict[str, Any]],
    max_gap_seconds: float,
    persist_raw_frames: bool,
    pricing: Optional[dict[str, float]] = None,
    *,
    expected_interval_seconds: Optional[float] = None,
    max_integrated_gap_seconds: Optional[float] = None,
    refresh_rollups: bool = True,
    run_compaction: bool = True,
    update_capabilities_row: bool = True,
    store_sample_raw_snapshot: bool = False,
):
    with db.transaction():
        previous = get_latest_sample(db)
        row = flatten_snapshot(
            snapshot,
            store_raw_snapshot=store_sample_raw_snapshot,
        )
        insert_sample(db, row)
        delta = calculate_energy_deltas(
            previous,
            row,
            max_gap_seconds,
            pricing,
            expected_interval_seconds=expected_interval_seconds,
            max_integrated_gap_seconds=max_integrated_gap_seconds,
        )
        insert_energy_delta(db, delta)
        if refresh_rollups:
            _refresh_summary_rollups_for_snapshot(
                db,
                row,
                previous_row=previous,
                reference_time=_utc_from_iso(row["recorded_at"]),
            )
        if update_capabilities_row:
            update_capabilities(db, capabilities)
        if persist_raw_frames:
            insert_raw_frames(db, row["recorded_at"], raw_frames)
        update_current_snapshot(
            db,
            snapshot,
            capabilities,
            pricing=pricing,
            delta=delta,
        )
    if run_compaction:
        compact_historical_samples(db, reference_time=_utc_from_iso(row["recorded_at"]))


def refresh_current_summary_rollups(db, reference_time: Optional[datetime] = None):
    latest = get_latest_sample(db)
    if not latest:
        return
    _refresh_summary_rollups_for_snapshot(
        db,
        latest,
        reference_time=reference_time or _utc_from_iso(latest["recorded_at"]),
    )


def get_current_snapshot(
    db,
    *,
    include_cumulative: bool = True,
    include_capabilities: bool = True,
) -> Optional[dict[str, Any]]:
    row = db.fetchone(
        "SELECT * FROM current_snapshot WHERE slot = ?",
        [CURRENT_SNAPSHOT_SLOT],
    )
    if not row:
        return None
    snapshot = json.loads(row["snapshot_json"])
    current = {
        "recorded_at": row["recorded_at"],
        "snapshot": snapshot,
        "pricing": json.loads(row["pricing_json"]) if row["pricing_json"] else None,
        "semantics": json.loads(row["semantics_json"]),
        "updated_at": row["updated_at"],
    }
    if include_cumulative:
        reference_time = datetime.now(timezone.utc)
        current["cumulative"] = (
            _normalized_cached_cumulative(
                json.loads(row["cumulative_json"]) if row["cumulative_json"] else None,
                row["recorded_at"],
                reference_time,
            )
            if row["cumulative_json"]
            else None
        )
        if not isinstance(current["cumulative"], dict):
            current["cumulative"] = {
                "today": get_period_totals(db, "today", reference_time),
                "month": get_period_totals(db, "month", reference_time),
                "year": get_period_totals(db, "year", reference_time),
                "all_time": get_period_totals(db, "all_time", reference_time),
            }
    if include_capabilities:
        current["capabilities"] = json.loads(row["capabilities_json"])
    return current


def get_history_series(
    db,
    metric: str,
    hours: int,
    max_points: Optional[int] = None,
) -> dict[str, Any]:
    definition = METRIC_DEFINITIONS.get(metric)
    if definition is None:
        raise KeyError(metric)

    since = datetime.now(timezone.utc).timestamp() - (max(hours, 1) * 3600)
    since_iso = datetime.fromtimestamp(since, timezone.utc).isoformat()

    semantics_column = definition.get("semantics_column")
    max_points = max(int(max_points), 1) if max_points is not None else None

    bounds = db.fetchone(
        f"""
        SELECT
            COUNT(*) AS sample_count,
            MIN(recorded_at) AS first_recorded_at,
            MAX(recorded_at) AS last_recorded_at
        FROM {definition['table']}
        WHERE recorded_at >= ?
        """,
        [since_iso],
    )
    sample_count = int((dict(bounds) if bounds else {}).get("sample_count") or 0)

    if sample_count > 0 and max_points is not None and sample_count > max_points:
        first_recorded_at = datetime.fromisoformat(bounds["first_recorded_at"])
        last_recorded_at = datetime.fromisoformat(bounds["last_recorded_at"])
        total_seconds = max((last_recorded_at - first_recorded_at).total_seconds(), 1.0)
        bucket_seconds = max(int(math.ceil(total_seconds / float(max_points))), 1)

        filtered_columns = [
            "recorded_at",
            f"{definition['column']} AS value",
        ]
        if semantics_column:
            filtered_columns.append(semantics_column)

        semantics_select = (
            f"CASE WHEN COUNT(DISTINCT {semantics_column}) = 1 "
            f"THEN MIN({semantics_column}) ELSE ? END AS semantics"
            if semantics_column
            else "? AS semantics"
        )

        rows = db.execute(
            f"""
            WITH filtered AS (
                SELECT
                    {', '.join(filtered_columns)},
                    CAST(
                        ((julianday(recorded_at) - julianday(?)) * 86400.0) / ?
                        AS INTEGER
                    ) AS bucket_index
                FROM {definition['table']}
                WHERE recorded_at >= ?
            )
            SELECT
                MAX(recorded_at) AS recorded_at,
                AVG(value) AS value,
                {semantics_select}
            FROM filtered
            GROUP BY bucket_index
            ORDER BY recorded_at ASC
            """,
            [
                bounds["first_recorded_at"],
                bucket_seconds,
                since_iso,
                definition["semantics"],
            ],
        )
    else:
        columns = ["recorded_at", f"{definition['column']} AS value"]
        if semantics_column:
            columns.append(f"{semantics_column} AS semantics")

        rows = db.execute(
            f"""
            SELECT {', '.join(columns)}
            FROM {definition['table']}
            WHERE recorded_at >= ?
            ORDER BY recorded_at ASC
            """,
            [since_iso],
        )

    items = []
    for row in rows:
        semantics = (
            row["semantics"]
            if "semantics" in row.keys() and row["semantics"]
            else definition["semantics"]
        )
        items.append(
            {
                "recorded_at": row["recorded_at"],
                "value": row["value"],
                "semantics": semantics,
            }
        )
    return {
        "metric": metric,
        "hours": hours,
        "unit": definition["unit"],
        "label": definition["label"],
        "series": items,
    }


def get_bucket_totals(db, bucket: str, value: Optional[str] = None) -> dict[str, Any]:
    if bucket not in {"day", "month", "year", "all_time"}:
        raise ValueError("bucket must be day, month, year, or all_time")
    if bucket == "all_time":
        row = _aggregate_summary_rows(db, SUMMARY_ROLLUP_TABLES["year"])
        if int((row or {}).get("row_count") or 0) <= 0:
            return _empty_bucket_totals(bucket, value)
        return _bucket_totals_from_row(bucket, value, row)

    if value is None:
        raise ValueError("value is required for day, month and year buckets")

    key_column = SUMMARY_ROLLUP_KEYS[bucket]
    table = SUMMARY_ROLLUP_TABLES[bucket]
    row = db.fetchone(
        f"""
        SELECT
            interval_count,
            sample_count,
            covered_seconds,
            missing_intervals,
            first_recorded_at,
            last_recorded_at,
            finalized,
            {", ".join(CUMULATIVE_TOTAL_COLUMNS)}
        FROM {table}
        WHERE {key_column} = ?
        """,
        [value],
    )
    return _bucket_totals_from_row(bucket, value, dict(row) if row else None)


def _prefix_range_params(prefix: Optional[str]) -> Optional[list[str]]:
    if not prefix:
        return None
    return [prefix, prefix + "\uffff"]


def get_grouped_cumulative(
    db,
    bucket: str,
    limit: int,
    search_prefix: Optional[str] = None,
) -> dict[str, Any]:
    if bucket not in {"day", "month", "year"}:
        raise ValueError("bucket must be day, month, or year")

    bucket_column = SUMMARY_ROLLUP_KEYS[bucket]
    table = SUMMARY_ROLLUP_TABLES[bucket]
    query = f"""
        SELECT
            {bucket_column} AS bucket,
            interval_count,
            sample_count,
            covered_seconds,
            missing_intervals,
            first_recorded_at,
            last_recorded_at,
            finalized,
            {", ".join(CUMULATIVE_TOTAL_COLUMNS)}
        FROM {table}
    """
    params: list[Any] = []
    if search_prefix:
        query += f" WHERE {bucket_column} >= ? AND {bucket_column} < ?"
        params.extend(_prefix_range_params(search_prefix))
    query += (
        f"""
        ORDER BY {bucket_column} DESC
        LIMIT ?
        """
    )
    params.append(max(limit, 1))
    rows = db.execute(
        query,
        params,
    )
    items = [dict(row) for row in reversed(rows)]
    return {
        "bucket": bucket,
        "semantics": SEMANTICS_DERIVED,
        "items": items,
    }


def csv_rows_for_samples(
    db,
    start: Optional[str],
    end: Optional[str],
    *,
    limit: int = 100_000,
):
    query = (
        "SELECT recorded_at, operation_mode, fault, ac_input_voltage_v, "
        "ac_output_voltage_v, ac_output_active_power_w, ac_output_load_percent, "
        "battery_voltage_v, battery_state_of_charge_percent, battery_charge_current_a, "
        "battery_discharge_current_a, pv_input_voltage_v, pv_input_current_a, "
        "pv_power_w, pv_power_semantics, solar_feed_to_grid_power_w "
        "FROM history_samples"
    )
    clauses = []
    params: list[Any] = []
    if start:
        clauses.append("recorded_at >= ?")
        params.append(start)
    if end:
        clauses.append("recorded_at <= ?")
        params.append(end)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY recorded_at ASC LIMIT ?"
    params.append(max(int(limit), 1))
    return db.execute(query, params)


def count_csv_rows_for_samples(
    db,
    start: Optional[str],
    end: Optional[str],
) -> int:
    query = "SELECT COUNT(*) AS count FROM history_samples"
    clauses = []
    params: list[Any] = []
    if start:
        clauses.append("recorded_at >= ?")
        params.append(start)
    if end:
        clauses.append("recorded_at <= ?")
        params.append(end)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    row = db.fetchone(query, params)
    return int(row["count"] or 0) if row else 0


def iter_csv_rows_for_samples(
    db,
    start: Optional[str],
    end: Optional[str],
):
    query = (
        "SELECT recorded_at, operation_mode, fault, ac_input_voltage_v, "
        "ac_output_voltage_v, ac_output_active_power_w, ac_output_load_percent, "
        "battery_voltage_v, battery_state_of_charge_percent, battery_charge_current_a, "
        "battery_discharge_current_a, pv_input_voltage_v, pv_input_current_a, "
        "pv_power_w, pv_power_semantics, solar_feed_to_grid_power_w "
        "FROM history_samples"
    )
    clauses = []
    params: list[Any] = []
    if start:
        clauses.append("recorded_at >= ?")
        params.append(start)
    if end:
        clauses.append("recorded_at <= ?")
        params.append(end)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY recorded_at ASC"
    return db.iter_execute(query, params)
