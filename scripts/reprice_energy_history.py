#!/usr/bin/env python3
"""Recalcule les montants euros historiques sans modifier les kWh."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from config import Config  # noqa: E402
from database import Database  # noqa: E402
from phocos_store import ensure_schema  # noqa: E402
from tempo_edf import build_pricing_context  # noqa: E402


def _set_timezone(config_data: dict) -> None:
    time_zone = config_data.get("time_zone")
    if not time_zone:
        return
    os.environ["TZ"] = str(time_zone)
    if hasattr(time, "tzset"):
        time.tzset()


def _pricing_for_day(prices_config: dict, local_day: str) -> dict:
    return build_pricing_context(
        None,
        prices_config=prices_config,
        reference_time=f"{local_day}T12:00:00",
    )


def _available_days(db: Database, start_day: str | None, end_day: str | None) -> list[str]:
    filters = []
    params: list[str] = []
    if start_day:
        filters.append("local_day >= ?")
        params.append(start_day)
    if end_day:
        filters.append("local_day < ?")
        params.append(end_day)
    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    rows = db.execute(
        f"""
        SELECT local_day
        FROM energy_summary_days
        {where_clause}
        ORDER BY local_day ASC
        """,
        params,
    )
    return [row["local_day"] for row in rows]


def _day_totals(db: Database, start_day: str | None, end_day: str | None) -> dict:
    filters = []
    params: list[str] = []
    if start_day:
        filters.append("local_day >= ?")
        params.append(start_day)
    if end_day:
        filters.append("local_day < ?")
        params.append(end_day)
    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    row = db.fetchone(
        f"""
        SELECT
            COUNT(*) AS day_count,
            COALESCE(SUM(pv_energy_kwh), 0.0) AS pv_energy_kwh,
            COALESCE(SUM(load_energy_kwh), 0.0) AS load_energy_kwh,
            COALESCE(SUM(grid_export_energy_kwh), 0.0) AS grid_export_energy_kwh,
            COALESCE(SUM(pv_to_load_energy_kwh), 0.0) AS pv_to_load_energy_kwh,
            COALESCE(SUM(battery_to_load_energy_kwh), 0.0) AS battery_to_load_energy_kwh,
            COALESCE(SUM(earned_feed_in_eur), 0.0) AS earned_feed_in_eur,
            COALESCE(SUM(earned_savings_eur), 0.0) AS earned_savings_eur
        FROM energy_summary_days
        {where_clause}
        """,
        params,
    )
    return dict(row) if row else {}


def _update_detailed_intervals(
    db: Database,
    local_day: str,
    grid_price: float,
    feed_in_revenue: float,
) -> int:
    rows = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM derived_energy_intervals
        WHERE local_day = ?
        """,
        [local_day],
    )
    count = int(rows[0]["count"] if rows else 0)
    if count <= 0:
        return 0
    db.execute(
        """
        UPDATE derived_energy_intervals
        SET
            grid_price_eur_per_kwh = ?,
            feed_in_revenue_eur_per_kwh = ?
        WHERE local_day = ?
        """,
        [grid_price, feed_in_revenue, local_day],
    )
    return count


def _update_day_summary(
    db: Database,
    local_day: str,
    grid_price: float,
    feed_in_revenue: float,
) -> dict:
    row = db.fetchone(
        """
        SELECT
            grid_export_energy_kwh,
            pv_to_load_energy_kwh,
            battery_to_load_energy_kwh
        FROM energy_summary_days
        WHERE local_day = ?
        """,
        [local_day],
    )
    if row is None:
        return {
            "local_day": local_day,
            "updated": False,
        }

    earned_feed_in = float(row["grid_export_energy_kwh"] or 0.0) * feed_in_revenue
    earned_savings = (
        float(row["pv_to_load_energy_kwh"] or 0.0)
        + float(row["battery_to_load_energy_kwh"] or 0.0)
    ) * grid_price
    db.execute(
        """
        UPDATE energy_summary_days
        SET
            earned_feed_in_eur = ?,
            earned_savings_eur = ?,
            updated_at = datetime('now')
        WHERE local_day = ?
        """,
        [earned_feed_in, earned_savings, local_day],
    )
    return {
        "local_day": local_day,
        "updated": True,
        "grid_price_eur_per_kwh": grid_price,
        "feed_in_revenue_eur_per_kwh": feed_in_revenue,
        "earned_feed_in_eur": earned_feed_in,
        "earned_savings_eur": earned_savings,
    }


def _refresh_months_and_years(db: Database, days: list[str]) -> dict:
    months = sorted({day[:7] for day in days})
    years = sorted({day[:4] for day in days})
    for month in months:
        db.execute(
            """
            UPDATE energy_summary_months
            SET
                earned_feed_in_eur = (
                    SELECT COALESCE(SUM(earned_feed_in_eur), 0.0)
                    FROM energy_summary_days
                    WHERE local_month = ?
                ),
                earned_savings_eur = (
                    SELECT COALESCE(SUM(earned_savings_eur), 0.0)
                    FROM energy_summary_days
                    WHERE local_month = ?
                ),
                updated_at = datetime('now')
            WHERE local_month = ?
            """,
            [month, month, month],
        )
    for year in years:
        db.execute(
            """
            UPDATE energy_summary_years
            SET
                earned_feed_in_eur = (
                    SELECT COALESCE(SUM(earned_feed_in_eur), 0.0)
                    FROM energy_summary_months
                    WHERE local_year = ?
                ),
                earned_savings_eur = (
                    SELECT COALESCE(SUM(earned_savings_eur), 0.0)
                    FROM energy_summary_months
                    WHERE local_year = ?
                ),
                updated_at = datetime('now')
            WHERE local_year = ?
            """,
            [year, year, year],
        )
    return {
        "months_refreshed": len(months),
        "years_refreshed": len(years),
    }


def reprice(
    db_path: Path,
    config_path: Path,
    *,
    start_day: str | None = None,
    end_day: str | None = None,
    apply: bool = False,
) -> dict:
    config = Config(str(config_path))
    _set_timezone(config.config_data)
    prices_config = config.config_data.get("prices", {})
    db = Database(str(db_path))
    try:
        ensure_schema(db)
        days = _available_days(db, start_day, end_day)
        before_totals = _day_totals(db, start_day, end_day)
        preview: list[dict] = []
        detailed_interval_count = 0
        day_updates = []
        with db.transaction():
            for local_day in days:
                pricing = _pricing_for_day(prices_config, local_day)
                grid_price = float(pricing.get("grid_price_eur_per_kwh") or 0.0)
                feed_in_revenue = float(
                    pricing.get("feed_in_revenue_eur_per_kwh") or 0.0
                )
                if len(preview) < 7:
                    preview.append(
                        {
                            "local_day": local_day,
                            "grid_price_eur_per_kwh": grid_price,
                            "tariff_label": pricing.get("tariff_label"),
                            "tariff_mode": pricing.get("tariff_mode"),
                        }
                    )
                if apply:
                    detailed_interval_count += _update_detailed_intervals(
                        db,
                        local_day,
                        grid_price,
                        feed_in_revenue,
                    )
                    day_updates.append(
                        _update_day_summary(
                            db,
                            local_day,
                            grid_price,
                            feed_in_revenue,
                        )
                    )
            rollups = _refresh_months_and_years(db, days) if apply else {}
            if apply:
                db.execute(
                    """
                    UPDATE current_snapshot
                    SET cumulative_json = ''
                    WHERE slot = 'current'
                    """
                )
        after_totals = _day_totals(db, start_day, end_day) if apply else before_totals
        return {
            "applied": apply,
            "database": str(db_path),
            "config": str(config_path),
            "tariff": prices_config.get("tariff", "auto"),
            "start_day": start_day,
            "end_day_exclusive": end_day,
            "days": len(days),
            "detailed_intervals_repriced": detailed_interval_count,
            "rollups": rollups,
            "totals_before": before_totals,
            "totals_after": after_totals,
            "preview": preview,
            "day_updates_preview": day_updates[:7],
            "message": "Aucun changement effectue. Relancer avec --apply."
            if not apply
            else "Historique euros recalcule; les kWh sont inchanges.",
        }
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Recalcule les montants euros des rollups avec le tarif configure."
    )
    parser.add_argument("--db", default="data/db.sqlite", help="Chemin SQLite")
    parser.add_argument(
        "--config",
        default="data/config.yml",
        help="Configuration PiPhocos a utiliser",
    )
    parser.add_argument("--start-day", default=None, help="Jour inclus YYYY-MM-DD")
    parser.add_argument("--end-day", default=None, help="Jour exclu YYYY-MM-DD")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Ecrit les nouveaux montants; sans ce flag, mode aperçu.",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            reprice(
                Path(args.db),
                Path(args.config),
                start_day=args.start_day,
                end_day=args.end_day,
                apply=args.apply,
            ),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
