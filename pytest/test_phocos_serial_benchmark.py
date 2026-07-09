from scripts.phocos_serial_benchmark import (
    CommandResult,
    build_command_schedule,
    summarize_results,
)


def test_serial_benchmark_schedule_prioritizes_qpgs():
    assert build_command_schedule(
        samples=5,
        unit=0,
        qpigs_every=2,
        qpiws_every=4,
    ) == [
        "QPGS0",
        "QPGS0",
        "QPIGS",
        "QPGS0",
        "QPGS0",
        "QPIGS",
        "QPIWS",
        "QPGS0",
    ]


def test_serial_benchmark_summary_reports_percentiles():
    summary = summarize_results(
        [
            CommandResult("QPGS0", True, 100.0, 8, 110, crc_ok=True),
            CommandResult("QPGS0", True, 200.0, 8, 110, crc_ok=True),
            CommandResult("QPGS0", False, 300.0, 8, 0, error="timeout"),
            CommandResult("QPIGS", True, 400.0, 8, 120, crc_ok=True),
        ]
    )

    assert summary["QPGS0"]["count"] == 3
    assert summary["QPGS0"]["ok"] == 2
    assert summary["QPGS0"]["errors"] == 1
    assert summary["QPGS0"]["avg_ms"] == 150.0
    assert summary["QPGS0"]["p95_ms"] == 200.0
    assert summary["QPIGS"]["avg_response_bytes"] == 120.0
