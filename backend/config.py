import copy
import logging
import traceback
from datetime import date

import yaml


DEFAULT_INSTANCE = {
    "name": "PiPhocos",
}


DEFAULT_CONFIG = {
    "logging": "normal",
    "time_zone": "Europe/Paris",
    "device": {
        "type": "Phocos",
        "start_date": "2024-01-01",
    },
    "phocos": {
        "serial_port": "/dev/ttyUSB0",
        "unit": 0,
        "timeout_s": 2.0,
        "enable_pi30_probe": True,
        "verbose_protocol_logging": False,
    },
    "server": {
        "ip": "0.0.0.0",
        "port": 5000,
        "public_host": "localhost",
        "public_url": "http://localhost:5000",
    },
    "grabber": {
        "interval_s": 2,
        "max_gap_for_cumulative_s": 180,
        "stale_after_s": 11,
    },
    "prices": {
        "price_per_grid_kwh": 0.325,
        "revenue_per_fed_in_kwh": 0.085,
    },
    "tempo": {
        "enabled": True,
        "api_base_url": "https://www.api-couleur-tempo.fr/api",
        "timeout_s": 3.0,
        "cache_ttl_s": 3600,
    },
    "instance": DEFAULT_INSTANCE,
}


def _deep_merge(base, incoming):
    merged = copy.deepcopy(base)
    for key, value in (incoming or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged

class Config:
    def __init__(self, file_name):
        try:
            with open(file_name, "r", encoding="utf-8") as file:
                yaml_data = yaml.safe_load(file) or {}
                self.config_data = _deep_merge(DEFAULT_CONFIG, yaml_data)
                self.config_data["instance"] = _deep_merge(
                    DEFAULT_INSTANCE,
                    self.config_data.get("instance"),
                )
                self.load_settings(self.config_data)
        except Exception as exc:
            logging.error(
                "Config error: loading/parsing the configuration file failed"
            )
            logging.error(exc)
            traceback.print_exc()
            raise

    def load_settings(self, yaml_data):
        """Copy settings from the yaml data for easier access."""
        self.log_level = logging.INFO
        if yaml_data.get("logging") == "verbose":
            self.log_level = logging.DEBUG

        start_date = yaml_data["device"].get("start_date")
        if isinstance(start_date, str):
            yaml_data["device"]["start_date"] = date.fromisoformat(start_date)
