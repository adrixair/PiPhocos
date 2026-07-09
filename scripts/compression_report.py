#!/usr/bin/env python3
"""Rapport lecture seule sur la compression et la retention SQLite."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


DEFAULT_TABLES = (
    "samples",
    "minute_samples",
    "compressed_samples_10m",
    "derived_energy_intervals",
    "energy_summary_days",
    "energy_summary_months",
    "energy_summary_years",
    "energy_quality_summary_days",
    "raw_frames",
)


def _connect_readonly(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    return conn


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}


def _table_summary(conn: sqlite3.Connection, table: str) -> dict:
    columns = _table_columns(conn, table)
    row = conn.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()
    summary = {"count": int(row["count"] or 0)}
    if "recorded_at" in columns:
        bounds = conn.execute(
            f"SELECT MIN(recorded_at) AS oldest, MAX(recorded_at) AS newest FROM {table}"
        ).fetchone()
        summary.update(oldest=bounds["oldest"], newest=bounds["newest"])
    if "local_day" in columns:
        bounds = conn.execute(
            f"SELECT MIN(local_day) AS oldest_day, MAX(local_day) AS newest_day FROM {table}"
        ).fetchone()
        summary.update(
            oldest_day=bounds["oldest_day"],
            newest_day=bounds["newest_day"],
        )
    return summary


def _dbstat_top(conn: sqlite3.Connection, limit: int) -> list[dict]:
    try:
        rows = conn.execute(
            """
            SELECT name, SUM(pgsize) AS bytes
            FROM dbstat
            GROUP BY name
            ORDER BY bytes DESC
            LIMIT ?
            """,
            [limit],
        )
    except sqlite3.DatabaseError:
        return []
    return [{"name": row["name"], "bytes": int(row["bytes"] or 0)} for row in rows]


def _retention_candidates(
    conn: sqlite3.Connection,
    *,
    reference_time: datetime,
    interval_retention_days: int,
) -> dict:
    cutoff_day = (
        reference_time.astimezone() - timedelta(days=max(interval_retention_days, 1))
    ).date().isoformat()
    rows = conn.execute(
        """
        SELECT
            d.local_day,
            COUNT(*) AS interval_count,
            CASE WHEN s.local_day IS NULL THEN 0 ELSE 1 END AS has_energy_summary,
            CASE WHEN q.local_day IS NULL THEN 0 ELSE 1 END AS has_quality_summary
        FROM derived_energy_intervals d
        LEFT JOIN energy_summary_days s ON s.local_day = d.local_day
        LEFT JOIN (
            SELECT DISTINCT local_day
            FROM energy_quality_summary_days
        ) q ON q.local_day = d.local_day
        WHERE d.local_day < ?
        GROUP BY d.local_day
        ORDER BY d.local_day ASC
        """,
        [cutoff_day],
    )
    days = [dict(row) for row in rows]
    return {
        "cutoff_day": cutoff_day,
        "candidate_days": len(days),
        "candidate_intervals": sum(int(row["interval_count"] or 0) for row in days),
        "ready_days": sum(
            1
            for row in days
            if int(row["has_energy_summary"] or 0)
            and int(row["has_quality_summary"] or 0)
        ),
        "first_days": days[:10],
        "last_days": days[-10:],
    }


def run_report(
    db_path: Path,
    *,
    interval_retention_days: int = 45,
    dbstat_limit: int = 20,
    reference_time: datetime | None = None,
) -> dict:
    reference_time = reference_time or datetime.now(timezone.utc)
    conn = _connect_readonly(db_path)
    try:
        tables = {}
        for table in DEFAULT_TABLES:
            try:
                tables[table] = _table_summary(conn, table)
            except sqlite3.DatabaseError as exc:
                tables[table] = {"error": str(exc)}
        files = {}
        for suffix in ("", "-wal", "-shm"):
            path = Path(str(db_path) + suffix)
            if path.exists():
                files[suffix or "main"] = path.stat().st_size
        return {
            "db_path": str(db_path),
            "generated_at": reference_time.isoformat(),
            "files": files,
            "tables": tables,
            "dbstat_top": _dbstat_top(conn, dbstat_limit),
            "energy_interval_retention": _retention_candidates(
                conn,
                reference_time=reference_time,
                interval_retention_days=interval_retention_days,
            ),
        }
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Mesure la compression SQLite sans modifier la base."
    )
    parser.add_argument(
        "--db",
        default=os.environ.get("PIPHOCOS_DB", "data/db.sqlite"),
        help="Chemin vers la base SQLite",
    )
    parser.add_argument(
        "--interval-retention-days",
        type=int,
        default=45,
        help="Retention cible des intervalles kWh detailles",
    )
    parser.add_argument(
        "--dbstat-limit",
        type=int,
        default=20,
        help="Nombre d'objets SQLite les plus volumineux a afficher",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            run_report(
                Path(args.db),
                interval_retention_days=args.interval_retention_days,
                dbstat_limit=args.dbstat_limit,
            ),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
