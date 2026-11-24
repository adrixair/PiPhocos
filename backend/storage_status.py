"""Cheap, read-only storage metadata for the dashboard.

Archived chart points live in SQLite, alongside the energy summaries. This
module reads file sizes and SQLite header/index metadata; it never scans the
measurement tables, checkpoints the WAL, vacuums, or deletes anything.
"""

import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from storage_guard import configured_min_free_bytes, get_storage_pressure


def _file_size(path, *, missing_size=None):
    try:
        return path.stat().st_size
    except FileNotFoundError:
        return missing_size
    except OSError:
        return None


def _retention_value(database_config, key, default):
    value = database_config.get(key, default)
    if value is None:
        value = default
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return None


def get_storage_status(db_path, data_dir, config_data):
    """Return public storage metrics without paths or configuration secrets.

    SQLite is opened with ``mode=ro`` so a missing
    database is never created and WAL contents remain visible to the reader.
    """
    db_path = Path(db_path)
    data_dir = Path(data_dir)
    database_config = (config_data or {}).get("database") or {}
    errors = []
    database = {
        "file_bytes": _file_size(db_path),
        "wal_bytes": _file_size(Path(f"{db_path}-wal"), missing_size=0),
        "shm_bytes": _file_size(Path(f"{db_path}-shm"), missing_size=0),
        "total_bytes": None,
        "page_size_bytes": None,
        "page_count": None,
        "free_page_count": None,
        "allocated_bytes": None,
        "reusable_bytes": None,
        "live_bytes_estimate": None,
    }
    if all(database[key] is not None for key in ("file_bytes", "wal_bytes", "shm_bytes")):
        database["total_bytes"] = sum(
            database[key] for key in ("file_bytes", "wal_bytes", "shm_bytes")
        )
    else:
        errors.append("database_files_unavailable")

    disk = {"total_bytes": None, "used_bytes": None, "free_bytes": None}
    try:
        usage = shutil.disk_usage(data_dir)
        disk.update(total_bytes=usage.total, used_bytes=usage.used, free_bytes=usage.free)
    except OSError:
        errors.append("disk_unavailable")

    history = {"first_day": None, "last_day": None}
    connection = None
    try:
        connection = sqlite3.connect(
            f"{db_path.resolve().as_uri()}?mode=ro",
            uri=True,
            timeout=0.1,
        )
        try:
            page_size = int(connection.execute("PRAGMA page_size").fetchone()[0])
            page_count = int(connection.execute("PRAGMA page_count").fetchone()[0])
            free_pages = int(connection.execute("PRAGMA freelist_count").fetchone()[0])
            database.update(
                page_size_bytes=page_size,
                page_count=page_count,
                free_page_count=free_pages,
                allocated_bytes=page_size * page_count,
                reusable_bytes=page_size * free_pages,
                live_bytes_estimate=page_size * (page_count - free_pages),
            )
        except sqlite3.Error:
            errors.append("database_metrics_unavailable")
        try:
            for field, order in (("first_day", "ASC"), ("last_day", "DESC")):
                row = connection.execute(
                    "SELECT local_day FROM energy_summary_days "
                    f"ORDER BY local_day {order} LIMIT 1"
                ).fetchone()
                history[field] = row[0] if row else None
        except sqlite3.Error:
            errors.append("history_unavailable")
    except (OSError, sqlite3.Error):
        errors.append("database_unavailable")
    finally:
        if connection is not None:
            connection.close()

    retention = {
        "raw_history_hours": _retention_value(
            database_config, "raw_history_retention_hours", 6
        ),
        "energy_interval_days": _retention_value(
            database_config, "energy_interval_retention_days", 45
        ),
        "history_resolution_minutes": 10,
        "summary_retention": "unlimited",
    }
    if retention["raw_history_hours"] is None or retention["energy_interval_days"] is None:
        errors.append("retention_unavailable")
    return {
        "state": "partial" if errors else "ok",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disk": disk,
        "database": database,
        "retention": retention,
        "history": history,
        "recording": get_storage_pressure(
            data_dir, min_free_bytes=configured_min_free_bytes(config_data)
        ),
        "errors": errors,
    }
