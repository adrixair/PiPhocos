from database import Database


def test_database_uses_wal_pragmas_and_checkpoint_helpers(tmp_path):
    db = Database(str(tmp_path / "perf.sqlite"))

    assert db.fetchone("PRAGMA journal_mode")["journal_mode"].lower() == "wal"
    assert int(db.fetchone("PRAGMA synchronous")["synchronous"]) == 1
    assert int(db.fetchone("PRAGMA wal_autocheckpoint")["wal_autocheckpoint"]) == 1000
    assert int(db.fetchone("PRAGMA journal_size_limit")["journal_size_limit"]) == 67_108_864

    db.execute("CREATE TABLE samples (id INTEGER PRIMARY KEY, value TEXT)")
    for index in range(100):
        db.execute("INSERT INTO samples (value) VALUES (?)", [str(index)])

    assert db.wal_size_bytes() >= 0
    rows = db.checkpoint_wal()
    assert len(rows) == 1

    db.close()


def test_database_iter_execute_streams_rows(tmp_path):
    db = Database(str(tmp_path / "iter.sqlite"))
    db.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, value TEXT)")
    db.executemany(
        "INSERT INTO items (value) VALUES (?)",
        [("a",), ("b",)],
    )

    rows = list(db.iter_execute("SELECT value FROM items ORDER BY id"))

    assert [row["value"] for row in rows] == ["a", "b"]
    db.close()
