import json
import sqlite3

from storage_status import get_storage_status


def _database(tmp_path):
    path = tmp_path / "history.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE energy_summary_days (local_day TEXT PRIMARY KEY) WITHOUT ROWID"
        )
        connection.executemany(
            "INSERT INTO energy_summary_days VALUES (?)",
            [("2026-11-12",), ("2026-10-03",), ("2026-11-11",)],
        )
    return path


def test_storage_reports_files_free_pages_and_indexed_history_without_mutation(tmp_path):
    path = _database(tmp_path)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE disposable (payload BLOB)")
        connection.execute("INSERT INTO disposable VALUES (zeroblob(131072))")
        connection.execute("DROP TABLE disposable")
    backups = tmp_path / "backups" / "previous"
    backups.mkdir(parents=True)
    (backups / "db.sqlite").write_bytes(b"backup")
    (tmp_path / "backups" / "settings.yml").write_bytes(b"settings")
    before = path.read_bytes()
    config = {
        "database": {"raw_history_retention_hours": 8, "energy_interval_retention_days": 60},
        "password": "private-config-value",
    }

    result = get_storage_status(path, tmp_path, config)

    assert result["state"] == "ok"
    assert result["errors"] == []
    assert result["database"]["file_bytes"] == path.stat().st_size
    assert result["database"]["wal_bytes"] == 0
    assert result["database"]["shm_bytes"] == 0
    assert result["database"]["reusable_bytes"] > 0
    assert result["database"]["allocated_bytes"] == (
        result["database"]["reusable_bytes"] + result["database"]["live_bytes_estimate"]
    )
    assert result["disk"]["total_bytes"] >= result["disk"]["free_bytes"] > 0
    assert "backups" not in result
    assert result["history"] == {"first_day": "2026-10-03", "last_day": "2026-11-12"}
    assert result["retention"] == {
        "raw_history_hours": 8,
        "energy_interval_days": 60,
        "history_resolution_minutes": 10,
        "summary_retention": "unlimited",
    }
    assert path.read_bytes() == before
    public_json = json.dumps(result)
    assert str(tmp_path) not in public_json
    assert "private-config-value" not in public_json


def test_storage_reads_committed_wal_without_checkpointing_it(tmp_path):
    path = _database(tmp_path)
    writer = sqlite3.connect(path)
    try:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute("INSERT INTO energy_summary_days VALUES ('2026-11-18')")
        writer.commit()
        wal = path.with_name(path.name + "-wal")
        before = wal.read_bytes()

        result = get_storage_status(path, tmp_path, {})

        assert result["state"] == "ok"
        assert result["database"]["wal_bytes"] == len(before) > 0
        assert result["history"]["last_day"] == "2026-11-18"
        assert wal.read_bytes() == before
    finally:
        writer.close()


def test_storage_missing_database_is_partial_and_does_not_create_it(tmp_path):
    missing = tmp_path / "not-created.sqlite"

    result = get_storage_status(missing, tmp_path, {})

    assert result["state"] == "partial"
    assert "database_unavailable" in result["errors"]
    assert result["database"]["file_bytes"] is None
    assert result["database"]["allocated_bytes"] is None
    assert result["history"] == {"first_day": None, "last_day": None}
    assert result["retention"]["raw_history_hours"] == 6
    assert result["retention"]["energy_interval_days"] == 45
    assert not missing.exists()


def test_storage_keeps_other_metrics_when_database_is_invalid(tmp_path):
    path = tmp_path / "invalid.sqlite"
    path.write_bytes(b"not a SQLite database")

    result = get_storage_status(path, tmp_path, {})

    assert result["state"] == "partial"
    assert result["database"]["file_bytes"] == len(b"not a SQLite database")
    assert result["database"]["allocated_bytes"] is None
    assert result["disk"]["total_bytes"] > 0
    assert "database_metrics_unavailable" in result["errors"]
    assert "history_unavailable" in result["errors"]
