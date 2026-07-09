#!/usr/bin/env python3
"""Reconstruit les resumes qualite journaliers hors boucle d'acquisition."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from database import Database  # noqa: E402
from phocos_store import (  # noqa: E402
    rebuild_quality_summary_days,
    refresh_missing_quality_summary_days,
)


def rebuild(db_path: Path, start_day: str | None, end_day: str | None) -> dict:
    started = time.perf_counter()
    db = Database(str(db_path))
    try:
        if start_day or end_day:
            result = refresh_missing_quality_summary_days(
                db,
                start_day or "0000-01-01",
                end_day or "9999-12-31",
                max_days=10_000,
            )
            refreshed_days = result["refreshed_days"]
            limited = result["limited"]
        else:
            refreshed_days = rebuild_quality_summary_days(db)
            limited = False
        return {
            "database": str(db_path),
            "start_day": start_day,
            "end_day_exclusive": end_day,
            "refreshed_days": refreshed_days,
            "limited": limited,
            "elapsed_s": round(time.perf_counter() - started, 3),
        }
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reconstruit energy_quality_summary_days hors acquisition."
    )
    parser.add_argument("--db", default="data/db.sqlite", help="Chemin SQLite")
    parser.add_argument("--start-day", default=None, help="Jour inclus YYYY-MM-DD")
    parser.add_argument("--end-day", default=None, help="Jour exclu YYYY-MM-DD")
    args = parser.parse_args()

    print(
        json.dumps(
            rebuild(Path(args.db), args.start_day, args.end_day),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
