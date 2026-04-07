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


def update_data(device):
    """Polls the device and persists the result."""
    tempo_state = tempo_client.get_state() if tempo_client else None
    prices_config = config.config_data.get("prices", {})
    pricing = build_pricing_context(
        tempo_state,
        prices_config.get("price_per_grid_kwh", 0.0),
        prices_config.get("revenue_per_fed_in_kwh", 0.0),
    )

    poll_result = device.poll()
    db = Database(str(DB_PATH))
    record_snapshot(
        db=db,
        snapshot=poll_result["snapshot"],
        capabilities=poll_result["capabilities"],
        raw_frames=poll_result["raw_frames"],
        max_gap_seconds=config.config_data["grabber"]["max_gap_for_cumulative_s"],
        persist_raw_frames=config.config_data["phocos"]["verbose_protocol_logging"],
        pricing=pricing,
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

    db = Database(str(DB_PATH))
    ensure_schema(db)
    compact_historical_samples(db)

    interval_s = config.config_data["grabber"]["interval_s"]
    next_run_monotonic = time.monotonic()
    logging.info("Grabber: entering main loop with %ss target interval", interval_s)
    while run:
        try:
            update_data(device)
        except Exception:
            logging.exception("Updating data from device failed")
        next_run_monotonic += interval_s
        now_monotonic = time.monotonic()
        if next_run_monotonic <= now_monotonic:
            late_by_seconds = now_monotonic - next_run_monotonic
            missed_intervals = int(late_by_seconds // interval_s) + 1
            next_run_monotonic += missed_intervals * interval_s
            logging.warning(
                "Grabber: polling is behind schedule by %.2fs, skipping %s interval(s)",
                late_by_seconds,
                missed_intervals,
            )
            continue

        sleep_seconds = next_run_monotonic - now_monotonic
        end_sleep_monotonic = now_monotonic + sleep_seconds
        while run:
            remaining = end_sleep_monotonic - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(remaining, 0.5))

    logging.info("Grabber: exiting main loop")


if __name__ == "__main__":
    main()
