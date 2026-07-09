#!/usr/bin/env python3
"""Benchmark synthetique du chemin d'ecriture SQLite par sample."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from database import Database  # noqa: E402
from phocos_store import ensure_schema, record_snapshot  # noqa: E402


SAMPLE = {
    "ac_output_active_power_w": 620,
    "ac_output_apparent_power_va": 710,
    "pv_power_w": 1114,
    "pv_power_semantics": "exact",
    "pv_charging_power_w": 438,
    "battery_charge_power_w": 438,
    "battery_discharge_power_w": 0,
    "solar_feed_to_grid_power_w": 0,
    "ac_input_voltage_v": 229.4,
    "ac_output_voltage_v": 229.3,
    "battery_voltage_v": 52.1,
    "battery_state_of_charge_percent": 82,
    "pv_input_voltage_v": 114.8,
    "pv_input_current_a": 9.7,
    "battery_charge_current_a": 8.4,
    "battery_discharge_current_a": 0,
    "total_charging_current_a": 8.4,
    "inverter_status": {"ac_input_available": True, "ac_output_on": True},
    "semantics": {"pv_power_w": "exact", "battery_charge_power_w": "derived"},
}
PRICING = {
    "grid_price_eur_per_kwh": 0.25,
    "feed_in_revenue_eur_per_kwh": 0.1,
    "source": "benchmark",
    "tempo_available": False,
    "tariff_label": None,
    "color_label": None,
    "tomorrow_color_label": None,
    "display": "Tarif fixe",
}


def run_benchmark(
    samples: int,
    interval_s: float,
    db_path: Path | None = None,
    *,
    store_raw_snapshot: bool = False,
) -> dict:
    owns_tmp = db_path is None
    tmp = tempfile.TemporaryDirectory() if owns_tmp else None
    try:
        path = db_path or Path(tmp.name) / "bench.sqlite"
        db = Database(str(path))
        ensure_schema(db)
        start = datetime.now(timezone.utc) - timedelta(seconds=samples * interval_s)
        t0 = time.perf_counter()
        for index in range(samples):
            record_snapshot(
                db=db,
                snapshot={
                    **SAMPLE,
                    "recorded_at": (start + timedelta(seconds=index * interval_s)).isoformat(),
                },
                capabilities={},
                raw_frames=[],
                max_gap_seconds=180,
                expected_interval_seconds=interval_s,
                max_integrated_gap_seconds=max(interval_s * 3.0, interval_s + 1.0),
                persist_raw_frames=False,
                pricing=PRICING,
                refresh_rollups=False,
                run_compaction=False,
                update_capabilities_row=False,
                store_sample_raw_snapshot=store_raw_snapshot,
            )
        elapsed_s = time.perf_counter() - t0
        quality = [
            dict(row)
            for row in db.execute(
                """
                SELECT quality, count(*) AS count
                FROM derived_energy_intervals
                GROUP BY quality
                ORDER BY quality
                """
            )
        ]
        report = {
            "samples": samples,
            "interval_s": interval_s,
            "store_sample_raw_snapshot": store_raw_snapshot,
            "elapsed_s": round(elapsed_s, 6),
            "ms_per_sample": round(elapsed_s * 1000.0 / max(samples, 1), 3),
            "samples_per_second": round(samples / elapsed_s, 3) if elapsed_s > 0 else None,
            "db_bytes": path.stat().st_size if path.exists() else 0,
            "wal_bytes": db.wal_size_bytes(),
            "quality": quality,
        }
        db.close()
        return report
    finally:
        if tmp is not None:
            tmp.cleanup()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark du hot path SQLite sans communication Phocos."
    )
    parser.add_argument("--samples", type=int, default=1000, help="Nombre de samples")
    parser.add_argument("--interval", type=float, default=1.0, help="Intervalle simule")
    parser.add_argument("--db", default=None, help="Chemin DB optionnel")
    parser.add_argument(
        "--store-raw-snapshot",
        action="store_true",
        help="Mesurer le cout de la copie JSON brute par sample",
    )
    args = parser.parse_args()

    db_path = Path(args.db) if args.db else None
    print(
        json.dumps(
            run_benchmark(
                args.samples,
                args.interval,
                db_path,
                store_raw_snapshot=args.store_raw_snapshot,
            ),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
