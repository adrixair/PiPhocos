import logging
import os
import signal
import time

from config import Config
from database import Database
from devices.Phocos import Phocos
from paths import CONFIG_PATH, DATA_DIR, DB_PATH, GRABBER_LOG_PATH
from phocos_store import (
    compact_historical_samples,
    ensure_schema,
    prune_detailed_energy_intervals,
    refresh_current_summary_rollups,
    record_snapshot,
)
from tempo_edf import TempoApiClient, build_pricing_context
import version


config = None
tempo_client = None
run = True


def set_time_zone(tz):
    """Sets the time zone environment variable."""
    if not tz:
        logging.warning("Grabber: no time zone set")
        return
    logging.info("Grabber: setting time zone to %s", tz)
    os.environ["TZ"] = tz
    time.tzset()
    logging.info("Grabber: time is now %s", time.strftime("%X %x %Z"))


def _pricing_from_cached_tempo(reference_time=None):
    tempo_state = tempo_client.get_cached_state() if tempo_client else None
    if tempo_client:
        tempo_client.refresh_if_due_background()
    prices_config = config.config_data.get("prices", {})
    return build_pricing_context(
        tempo_state,
        prices_config.get("price_per_grid_kwh", 0.0),
        prices_config.get("revenue_per_fed_in_kwh", 0.0),
        prices_config=prices_config,
        reference_time=reference_time,
    )


def _max_integrated_gap_seconds(interval_s):
    grabber_config = config.config_data.get("grabber", {})
    configured = grabber_config.get("max_integrated_gap_s")
    if configured is not None:
        return float(configured)
    return max(float(interval_s) * 3.0, float(interval_s) + 1.0)


def update_data(device, db, interval_s):
    """Polls the device and persists the result."""
    started = time.monotonic()

    poll_started = time.monotonic()
    poll_result = device.poll()
    poll_elapsed = time.monotonic() - poll_started
    pricing = _pricing_from_cached_tempo(
        reference_time=poll_result["snapshot"].get("recorded_at")
    )

    persist_started = time.monotonic()
    record_snapshot(
        db=db,
        snapshot=poll_result["snapshot"],
        capabilities=poll_result["capabilities"],
        raw_frames=poll_result["raw_frames"],
        max_gap_seconds=config.config_data["grabber"]["max_gap_for_cumulative_s"],
        expected_interval_seconds=interval_s,
        max_integrated_gap_seconds=_max_integrated_gap_seconds(interval_s),
        persist_raw_frames=config.config_data["phocos"]["verbose_protocol_logging"],
        pricing=pricing,
        refresh_rollups=False,
        run_compaction=False,
        update_capabilities_row=poll_result.get("capabilities_changed", True),
        store_sample_raw_snapshot=bool(
            config.config_data.get("database", {}).get(
                "store_sample_raw_snapshot_json",
                False,
            )
        ),
    )
    persist_elapsed = time.monotonic() - persist_started
    total_elapsed = time.monotonic() - started
    if total_elapsed > max(float(interval_s) * 0.8, 1.0):
        logging.info(
            "Grabber: slow poll total=%.3fs serial=%.3fs persist=%.3fs",
            total_elapsed,
            poll_elapsed,
            persist_elapsed,
        )


def _database_float(name, default):
    database_config = config.config_data.get("database", {})
    value = database_config.get(name, default)
    if value is None:
        return default
    return float(value)


def _database_int(name, default):
    return int(_database_float(name, default))


def run_maintenance(db, *, prune_energy_intervals_due=False):
    started = time.monotonic()
    raw_retention_hours = _database_int("raw_history_retention_hours", 24)
    compact_historical_samples(db, retention_hours=raw_retention_hours)
    refresh_current_summary_rollups(db)
    prune_report = None
    if prune_energy_intervals_due:
        prune_report = prune_detailed_energy_intervals(
            db,
            retention_days=_database_int("energy_interval_retention_days", 45),
            max_days=_database_int("energy_interval_prune_max_days", 14),
        )
    db.optimize(force=True)
    database_config = config.config_data.get("database", {})
    threshold_mb = float(database_config.get("wal_truncate_threshold_mb") or 96.0)
    wal_size = db.wal_size_bytes()
    checkpoint_rows = db.checkpoint_wal(
        truncate=wal_size > threshold_mb * 1024 * 1024,
    )
    elapsed = time.monotonic() - started
    logging.info(
        "Grabber: maintenance completed in %.3fs wal_size=%s prune=%s checkpoint=%s",
        elapsed,
        wal_size,
        prune_report,
        [dict(row) for row in checkpoint_rows] if checkpoint_rows else [],
    )

def handler_stop_signals(signum, frame):
    del signum, frame
    global run
    logging.debug("Grabber: SIGTERM/SIGINT received")
    run = False


def main():
    """Main loop."""
    global config

    signal.signal(signal.SIGINT, handler_stop_signals)
    signal.signal(signal.SIGTERM, handler_stop_signals)

    os.makedirs(DATA_DIR, exist_ok=True)
    logging.basicConfig(
        filename=str(GRABBER_LOG_PATH),
        filemode="w",
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.info("Starting PiPhocos grabber version %s", version.get_version())

    logging.info("Grabber: reading backend configuration from %s", CONFIG_PATH)
    config = Config(str(CONFIG_PATH))
    logging.getLogger().setLevel(config.log_level)
    set_time_zone(config.config_data.get("time_zone"))

    logging.info("Grabber: loading Phocos device adapter")
    device = Phocos(config)
    
    global tempo_client
    tempo_client = TempoApiClient(config)
    tempo_client.refresh_if_due_background(force=True)

    db = Database(str(DB_PATH))
    ensure_schema(db)

    interval_s = float(config.config_data["grabber"]["interval_s"])
    maintenance_interval_s = max(
        float(config.config_data["grabber"].get("maintenance_interval_s") or 60.0),
        interval_s,
    )
    energy_interval_prune_interval_s = max(
        _database_float("energy_interval_prune_interval_s", 3600.0),
        maintenance_interval_s,
    )
    next_run_monotonic = time.monotonic()
    next_maintenance_monotonic = next_run_monotonic + maintenance_interval_s
    next_energy_prune_monotonic = next_maintenance_monotonic
    logging.info("Grabber: entering main loop with %ss target interval", interval_s)
    while run:
        try:
            update_data(device, db, interval_s)
        except Exception:
            logging.exception("Updating data from device failed")
        now_monotonic = time.monotonic()
        if now_monotonic >= next_maintenance_monotonic:
            prune_energy_intervals_due = now_monotonic >= next_energy_prune_monotonic
            try:
                run_maintenance(
                    db,
                    prune_energy_intervals_due=prune_energy_intervals_due,
                )
            except Exception:
                logging.exception("Grabber maintenance failed")
            if prune_energy_intervals_due:
                next_energy_prune_monotonic = (
                    time.monotonic() + energy_interval_prune_interval_s
                )
            next_maintenance_monotonic = time.monotonic() + maintenance_interval_s
        next_run_monotonic += interval_s
        now_monotonic = time.monotonic()
        if next_run_monotonic <= now_monotonic:
            late_by_seconds = now_monotonic - next_run_monotonic
            missed_intervals = int(late_by_seconds // interval_s)
            if missed_intervals > 0:
                next_run_monotonic += missed_intervals * interval_s
                logging.warning(
                    "Grabber: polling is behind schedule by %.2fs, skipping %s interval(s)",
                    late_by_seconds,
                    missed_intervals,
                )
            else:
                next_run_monotonic = now_monotonic
            continue

        sleep_seconds = next_run_monotonic - now_monotonic
        end_sleep_monotonic = now_monotonic + sleep_seconds
        while run:
            remaining = end_sleep_monotonic - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(remaining, 0.5))

    device.close()
    db.close()
    logging.info("Grabber: exiting main loop")


if __name__ == "__main__":
    main()
