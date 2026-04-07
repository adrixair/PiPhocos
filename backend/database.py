import sqlite3


class Database:
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
        self.open(file_name)

    def __del__(self):
        self.close()

    def open(self, file_name):
        """Opens the database connection."""
        self.connection = sqlite3.connect(file_name)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()
        self.cursor.execute("PRAGMA journal_mode=WAL")
        self.cursor.execute("PRAGMA foreign_keys=ON")
        self.cursor.execute("PRAGMA busy_timeout=5000")
        self.cursor.execute("PRAGMA temp_store=MEMORY")
        self.cursor.execute("PRAGMA cache_size=-8192")
        self.cursor.execute("PRAGMA mmap_size=268435456")
        self.cursor.execute("PRAGMA optimize")

    def close(self):
        """Closes the data base."""
        if self.connection is not None:
            self.connection.commit()
            self.connection.close()
            self.connection = None
            self.cursor = None

    @classmethod
    def _should_commit(cls, query):
        statement = (query or "").lstrip().upper()
        return statement.startswith(cls._MUTATING_PREFIXES)

    def execute(self, query, params=None):
        """Executes a query and returns resulting rows."""
        self.cursor.execute(query, params or [])
        rows = self.cursor.fetchall()
        if self._should_commit(query):
            self.connection.commit()
        return rows

    def execute_script(self, script):
        """Executes a multi-statement SQL script."""
        self.cursor.executescript(script)
        self.connection.commit()

    def executemany(self, query, rows):
        """Executes one query with multiple parameter sets."""
        self.cursor.executemany(query, rows)
        self.connection.commit()

    def fetchone(self, query, params=None):
        """Executes a query and returns a single row."""
        self.cursor.execute(query, params or [])
        row = self.cursor.fetchone()
        if self._should_commit(query):
            self.connection.commit()
        return row
