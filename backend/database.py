import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path


class Database:
    _last_optimize_monotonic = 0.0
    _optimize_min_interval_s = 3600.0
    _MUTATING_PREFIXES = (
        "INSERT",
        "UPDATE",
        "DELETE",
        "REPLACE",
        "CREATE",
        "DROP",
        "ALTER",
        "VACUUM",
        "BEGIN",
        "COMMIT",
        "ROLLBACK",
        "ATTACH",
        "DETACH",
    )

    def __init__(self, file_name):
        self.cursor = None
        self.connection = None
        self.file_name = None
        self._transaction_depth = 0
        self.open(file_name)

    def __del__(self):
        self.close()

    def open(self, file_name):
        """Opens the database connection."""
        self.file_name = str(file_name)
        self.connection = sqlite3.connect(file_name)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()
        self.cursor.execute("PRAGMA journal_mode=WAL")
        self.cursor.execute("PRAGMA synchronous=NORMAL")
        self.cursor.execute("PRAGMA foreign_keys=ON")
        self.cursor.execute("PRAGMA busy_timeout=5000")
        self.cursor.execute("PRAGMA temp_store=MEMORY")
        self.cursor.execute("PRAGMA cache_size=-8192")
        self.cursor.execute("PRAGMA mmap_size=268435456")
        self.cursor.execute("PRAGMA wal_autocheckpoint=1000")
        self.cursor.execute("PRAGMA journal_size_limit=67108864")
        self.optimize()

    def close(self):
        """Closes the data base."""
        if self.connection is not None:
            self.optimize()
            self.connection.commit()
            self.connection.close()
            self.connection = None
            self.cursor = None

    @classmethod
    def _should_commit(cls, query):
        statement = (query or "").lstrip().upper()
        return statement.startswith(cls._MUTATING_PREFIXES)

    def _commit_if_needed(self, query):
        if self._transaction_depth == 0 and self._should_commit(query):
            self.connection.commit()

    @contextmanager
    def transaction(self):
        """Groups mutating statements into one SQLite transaction."""
        outermost = self._transaction_depth == 0
        if outermost:
            self.connection.execute("BEGIN")
        self._transaction_depth += 1
        try:
            yield self
        except Exception:
            self._transaction_depth -= 1
            if outermost:
                self.connection.rollback()
            raise
        else:
            self._transaction_depth -= 1
            if outermost:
                self.connection.commit()

    def execute(self, query, params=None):
        """Executes a query and returns resulting rows."""
        self.cursor.execute(query, params or [])
        rows = self.cursor.fetchall()
        self._commit_if_needed(query)
        return rows

    def iter_execute(self, query, params=None):
        """Executes a query and returns an iterator cursor without fetchall()."""
        cursor = self.connection.execute(query, params or [])
        self._commit_if_needed(query)
        return cursor

    def execute_script(self, script):
        """Executes a multi-statement SQL script."""
        self.cursor.executescript(script)
        self.connection.commit()

    def executemany(self, query, rows):
        """Executes one query with multiple parameter sets."""
        self.cursor.executemany(query, rows)
        self._commit_if_needed(query)

    def fetchone(self, query, params=None):
        """Executes a query and returns a single row."""
        self.cursor.execute(query, params or [])
        row = self.cursor.fetchone()
        self._commit_if_needed(query)
        return row

    def optimize(self, *, force=False):
        """Lets SQLite refresh planner statistics when it is cheap to do so."""
        if self.connection is not None:
            now = time.monotonic()
            if (
                not force
                and self._last_optimize_monotonic
                and now - self._last_optimize_monotonic < self._optimize_min_interval_s
            ):
                return
            self.cursor.execute("PRAGMA optimize")
            type(self)._last_optimize_monotonic = now

    def wal_size_bytes(self):
        """Returns the current WAL file size when WAL mode is active."""
        file_name = getattr(self, "file_name", None)
        if not file_name:
            return 0
        wal_path = Path(f"{file_name}-wal")
        return wal_path.stat().st_size if wal_path.exists() else 0

    def checkpoint_wal(self, *, truncate=False):
        """Runs a WAL checkpoint and optionally truncates the WAL file."""
        mode = "TRUNCATE" if truncate else "PASSIVE"
        return self.execute(f"PRAGMA wal_checkpoint({mode})")
