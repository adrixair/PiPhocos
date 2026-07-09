#!/usr/bin/env python3
"""Rapport local de performance acquisition PiPhocos.

Ce script ne contacte pas le Phocos. Il lit seulement la base SQLite locale et
produit un resume JSON utile avant/apres changement de cadence.
"""

import argparse
import json
import sqlite3
from pathlib import Path


def _row_to_dict(row):
    return {key: row[key] for key in row.keys()} if row else {}


def _query_one(db, query, params=()):
    row = db.execute(query, params).fetchone()
    return _row_to_dict(row)


def _query_all(db, query, params=()):
    return [_row_to_dict(row) for row in db.execute(query, params).fetchall()]


def _sample_gap_stats(db, minutes):
    return _query_one(
        db,
        """
        WITH ordered AS (
            SELECT
                recorded_at,
                (julianday(recorded_at) -
                 julianday(lag(recorded_at) OVER (ORDER BY recorded_at))) * 86400.0
                    AS dt
            FROM samples
            WHERE unixepoch(recorded_at) >= unixepoch('now', ?)
        ),
        ranked AS (
            SELECT
                dt,
                row_number() OVER (ORDER BY dt) AS rn,
                count(*) OVER () AS total
            FROM ordered
            WHERE dt IS NOT NULL
        )
        SELECT
            count(*) AS interval_count,
            round(avg(dt), 3) AS avg_gap_s,
            round(min(dt), 3) AS min_gap_s,
            round(max(dt), 3) AS max_gap_s,
            round(
                COALESCE(
                    min(
                        CASE
                            WHEN rn >= CAST((total * 0.95) + 0.999999 AS INTEGER)
                            THEN dt
                        END
                    ),
                    max(dt),
                    0.0
                ),
                3
            ) AS p95_gap_s,
            sum(CASE WHEN dt > 12 THEN 1 ELSE 0 END) AS gaps_over_12s,
            sum(CASE WHEN dt > 30 THEN 1 ELSE 0 END) AS gaps_over_30s,
            sum(CASE WHEN dt > 60 THEN 1 ELSE 0 END) AS gaps_over_60s
        FROM ranked
        """,
        [f"-{int(minutes)} minutes"],
    )


def _quality_stats(db, days):
    return _query_all(
        db,
        """
        SELECT
            COALESCE(quality, 'unknown') AS quality,
            count(*) AS interval_count,
            round(COALESCE(sum(interval_seconds), 0.0), 3) AS seconds,
            round(COALESCE(sum(pv_energy_kwh), 0.0), 6) AS pv_kwh,
            round(COALESCE(sum(load_energy_kwh), 0.0), 6) AS load_kwh
        FROM derived_energy_intervals
        WHERE unixepoch(recorded_at) >= unixepoch('now', ?)
        GROUP BY quality
        ORDER BY quality ASC
        """,
        [f"-{int(days)} days"],
    )


def _quality_summary_coverage(db, days):
    return _query_one(
        db,
        """
        WITH interval_days AS (
            SELECT DISTINCT local_day
            FROM derived_energy_intervals
            WHERE unixepoch(recorded_at) >= unixepoch('now', ?)
        ),
        summary_days AS (
            SELECT DISTINCT local_day
            FROM energy_quality_summary_days
            WHERE local_day IN (SELECT local_day FROM interval_days)
        )
        SELECT
            (SELECT count(*) FROM interval_days) AS interval_day_count,
            (SELECT count(*) FROM summary_days) AS summarized_day_count
        """,
        [f"-{int(days)} days"],
    )


def _sample_storage_stats(db):
    return _query_one(
        db,
        """
        SELECT
            count(*) AS sample_count,
            round(avg(length(raw_snapshot_json)), 1) AS avg_raw_snapshot_json_bytes,
            max(length(raw_snapshot_json)) AS max_raw_snapshot_json_bytes
        FROM samples
        """,
    )


def _wal_info(db_path):
    wal_path = Path(f"{db_path}-wal")
    shm_path = Path(f"{db_path}-shm")
    return {
        "db_bytes": Path(db_path).stat().st_size if Path(db_path).exists() else 0,
        "wal_bytes": wal_path.stat().st_size if wal_path.exists() else 0,
        "shm_bytes": shm_path.stat().st_size if shm_path.exists() else 0,
    }


def _checkpoint_passive(db):
    try:
        return _query_all(db, "PRAGMA wal_checkpoint(PASSIVE)")
    except sqlite3.OperationalError as exc:
        return [{"error": str(exc)}]


def build_report(db_path, minutes, days):
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    try:
        return {
            "database": str(db_path),
            "sample_gaps": _sample_gap_stats(db, minutes),
            "interval_quality": _quality_stats(db, days),
            "quality_summary_coverage": _quality_summary_coverage(db, days),
            "sample_storage": _sample_storage_stats(db),
            "latest_sample": _query_one(
                db,
                "SELECT recorded_at FROM samples ORDER BY recorded_at DESC LIMIT 1",
            ),
            "wal": _wal_info(db_path),
            "integrity": _query_one(db, "PRAGMA integrity_check"),
            "checkpoint_passive": _checkpoint_passive(db),
        }
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Rapport performance acquisition PiPhocos."
    )
    parser.add_argument("--db", default="data/db.sqlite", help="Chemin SQLite")
    parser.add_argument("--minutes", type=int, default=30, help="Fenetre gaps")
    parser.add_argument("--days", type=int, default=1, help="Fenetre qualite")
    args = parser.parse_args()

    report = build_report(Path(args.db), args.minutes, args.days)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
