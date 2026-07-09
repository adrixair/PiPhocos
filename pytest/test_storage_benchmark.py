from scripts.storage_benchmark import run_benchmark


def test_storage_benchmark_runs_on_temporary_database():
    report = run_benchmark(samples=5, interval_s=1.0)

    assert report["samples"] == 5
    assert report["store_sample_raw_snapshot"] is False
    assert report["ms_per_sample"] >= 0
    assert report["db_bytes"] > 0
    assert report["wal_bytes"] > 0
    assert any(row["quality"] == "exact" for row in report["quality"])


def test_storage_benchmark_can_measure_raw_snapshot_mode():
    report = run_benchmark(
        samples=2,
        interval_s=1.0,
        store_raw_snapshot=True,
    )

    assert report["store_sample_raw_snapshot"] is True
    assert report["samples"] == 2
