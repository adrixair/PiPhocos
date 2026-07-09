#!/usr/bin/env python3
"""Mesure directe de latence des commandes serie Phocos."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from phocos_protocol import build_command_frame, decode_frame, parse_probe_payload, parse_qpgs_payload  # noqa: E402


@dataclass
class CommandResult:
    command: str
    ok: bool
    latency_ms: float
    request_bytes: int
    response_bytes: int
    crc_ok: bool = False
    field_count: int | None = None
    error: str | None = None


def percentile(values: list[float], ratio: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(max(int(round((len(ordered) - 1) * ratio)), 0), len(ordered) - 1)
    return ordered[index]


def summarize_results(results: Iterable[CommandResult]) -> dict:
    summary: dict[str, dict] = {}
    for result in results:
        bucket = summary.setdefault(
            result.command,
            {
                "count": 0,
                "ok": 0,
                "errors": 0,
                "latencies_ms": [],
                "response_bytes": [],
            },
        )
        bucket["count"] += 1
        if result.ok:
            bucket["ok"] += 1
            bucket["latencies_ms"].append(result.latency_ms)
            bucket["response_bytes"].append(result.response_bytes)
        else:
            bucket["errors"] += 1

    for bucket in summary.values():
        latencies = bucket.pop("latencies_ms")
        response_bytes = bucket.pop("response_bytes")
        bucket["avg_ms"] = round(statistics.fmean(latencies), 3) if latencies else None
        bucket["p50_ms"] = round(percentile(latencies, 0.50), 3) if latencies else None
        bucket["p95_ms"] = round(percentile(latencies, 0.95), 3) if latencies else None
        bucket["max_ms"] = round(max(latencies), 3) if latencies else None
        bucket["avg_response_bytes"] = (
            round(statistics.fmean(response_bytes), 1) if response_bytes else None
        )
    return summary


def build_command_schedule(
    samples: int,
    unit: int,
    qpigs_every: int,
    qpiws_every: int,
) -> list[str]:
    qpgs = f"QPGS{unit}"
    commands: list[str] = []
    for index in range(samples):
        commands.append(qpgs)
        if qpigs_every > 0 and (index + 1) % qpigs_every == 0:
            commands.append("QPIGS")
        if qpiws_every > 0 and (index + 1) % qpiws_every == 0:
            commands.append("QPIWS")
    return commands


def parse_payload(command: str, payload_ascii: str) -> dict:
    if command.startswith("QPGS"):
        return parse_qpgs_payload(payload_ascii)
    return parse_probe_payload(command, payload_ascii)


def run_command(ser, command: str, *, include_payload: bool = False) -> CommandResult:
    request = build_command_frame(command)
    started = time.perf_counter()
    try:
        if hasattr(ser, "reset_input_buffer"):
            ser.reset_input_buffer()
        ser.write(request)
        ser.flush()
        response = ser.read_until(b"\r", size=1024)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        if not response:
            raise TimeoutError("aucune reponse")
        decoded = decode_frame(response)
        if not decoded["crc_ok"]:
            raise ValueError("CRC invalide")
        parsed = parse_payload(command, decoded["payload_ascii"])
        result = CommandResult(
            command="QPGS0" if command.startswith("QPGS") else command,
            ok=True,
            latency_ms=elapsed_ms,
            request_bytes=len(request),
            response_bytes=len(response),
            crc_ok=True,
            field_count=parsed.get("field_count"),
        )
        if include_payload:
            result.error = decoded["payload_ascii"]
        return result
    except Exception as exc:
        return CommandResult(
            command="QPGS0" if command.startswith("QPGS") else command,
            ok=False,
            latency_ms=(time.perf_counter() - started) * 1000.0,
            request_bytes=len(request),
            response_bytes=0,
            error=str(exc),
        )


def open_serial(args):
    try:
        import serial
    except ImportError as exc:
        raise SystemExit("pyserial est requis pour ce benchmark") from exc

    return serial.Serial(
        port=args.port,
        baudrate=args.baudrate,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=args.timeout,
        write_timeout=args.timeout,
    )


def benchmark(args) -> dict:
    schedule = build_command_schedule(
        args.samples,
        args.unit,
        args.qpigs_every,
        args.qpiws_every,
    )
    results: list[CommandResult] = []
    started = time.perf_counter()
    with open_serial(args) as ser:
        for command in schedule:
            before = time.perf_counter()
            results.append(run_command(ser, command, include_payload=args.include_payload))
            elapsed = time.perf_counter() - before
            if args.interval > elapsed:
                time.sleep(args.interval - elapsed)
    total_seconds = time.perf_counter() - started
    return {
        "port": args.port,
        "baudrate": args.baudrate,
        "samples": args.samples,
        "interval_s": args.interval,
        "commands_sent": len(schedule),
        "total_seconds": round(total_seconds, 3),
        "effective_commands_per_second": round(len(schedule) / total_seconds, 3)
        if total_seconds > 0
        else None,
        "summary": summarize_results(results),
        "errors": [
            result.__dict__
            for result in results
            if not result.ok
        ][:20],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark direct QPGS0/QPIGS/QPIWS sur le port serie Phocos."
    )
    parser.add_argument("--port", default="/dev/ttyUSB0", help="Port serie")
    parser.add_argument("--baudrate", type=int, default=2400, help="Baudrate")
    parser.add_argument("--timeout", type=float, default=2.0, help="Timeout lecture/ecriture")
    parser.add_argument("--unit", type=int, default=0, help="Numero unite QPGS")
    parser.add_argument("--samples", type=int, default=60, help="Nombre de lectures QPGS")
    parser.add_argument(
        "--interval",
        type=float,
        default=0.0,
        help="Intervalle cible entre commandes; 0 mesure la cadence maximale",
    )
    parser.add_argument("--qpigs-every", type=int, default=5, help="Ajouter QPIGS tous les N samples; 0 desactive")
    parser.add_argument("--qpiws-every", type=int, default=120, help="Ajouter QPIWS tous les N samples; 0 desactive")
    parser.add_argument(
        "--include-payload",
        action="store_true",
        help="Inclure les payloads bruts dans les erreurs; a eviter pour un partage public",
    )
    args = parser.parse_args()

    print(json.dumps(benchmark(args), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
