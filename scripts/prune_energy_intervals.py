#!/usr/bin/env python3
"""Purge controlee des intervalles kWh detailles deja resumes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from database import Database  # noqa: E402
from phocos_store import ensure_schema, prune_detailed_energy_intervals  # noqa: E402


def prune(
    db_path: Path,
    *,
    retention_days: int,
    max_days: int,
    apply: bool,
) -> dict:
    if not apply:
        return {
            "applied": False,
            "message": "Aucune purge effectuee. Relancer avec --apply.",
            "retention_days": retention_days,
            "max_days": max_days,
        }

    db = Database(str(db_path))
    try:
        ensure_schema(db)
        report = prune_detailed_energy_intervals(
            db,
            retention_days=retention_days,
            max_days=max_days,
        )
        checkpoint = db.checkpoint_wal(truncate=False)
        return {
            "applied": True,
            "retention_days": retention_days,
            "max_days": max_days,
            "prune": report,
            "wal_checkpoint": [dict(row) for row in checkpoint] if checkpoint else [],
            "wal_bytes": db.wal_size_bytes(),
        }
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Purge les intervalles kWh detailles quand les rollups existent."
    )
    parser.add_argument("--db", default="data/db.sqlite", help="Chemin SQLite")
    parser.add_argument(
        "--retention-days",
        type=int,
        default=45,
        help="Jours d'intervalles detailles a conserver",
    )
    parser.add_argument(
        "--max-days",
        type=int,
        default=14,
        help="Nombre maximum de jours a purger sur cette execution",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Effectuer vraiment la purge; sans ce flag, aucun changement",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            prune(
                Path(args.db),
                retention_days=args.retention_days,
                max_days=args.max_days,
                apply=args.apply,
            ),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
