"""Stop recording before disk exhaustion; never reclaim historical data."""

import math
import shutil
import sqlite3
from pathlib import Path


DEFAULT_MIN_FREE_BYTES = 512 * 1024 * 1024


def configured_min_free_bytes(config_data):
    try:
        value = float((config_data or {}).get("database", {}).get("min_free_space_mb", 512))
        if not math.isfinite(value) or value <= 0:
            raise ValueError("invalid storage reserve")
        return max(int(value * 1024 * 1024), 1)
    except (AttributeError, TypeError, ValueError, OverflowError):
        return DEFAULT_MIN_FREE_BYTES


def get_storage_pressure(path, *, min_free_bytes=DEFAULT_MIN_FREE_BYTES):
    """Measure the data filesystem. An unavailable measurement forbids writes."""
    status = {
        "state": "paused", "write_allowed": False,
        "reason": "disk_usage_unavailable", "free_bytes": None,
        "total_bytes": None, "min_free_bytes": min_free_bytes,
    }
    try:
        target = Path(path)
        # A fresh installation may not have created its data directory yet.
        while not target.exists() and target.parent != target:
            target = target.parent
        usage = shutil.disk_usage(target)
        status.update(free_bytes=usage.free, total_bytes=usage.total)
        if usage.free >= min_free_bytes:
            status.update(state="ok", write_allowed=True, reason=None)
        else:
            status["reason"] = "low_disk_space"
    except Exception:
        pass
    return status


class StoragePressure(RuntimeError):
    def __init__(self, status):
        self.status = status
        super().__init__(status["reason"])


def is_sqlite_full(error):
    return isinstance(error, sqlite3.Error) and (
        ((getattr(error, "sqlite_errorcode", 0) or 0) & 0xFF) == getattr(sqlite3, "SQLITE_FULL", 13)
        or "database or disk is full" in str(error).lower()
    )
