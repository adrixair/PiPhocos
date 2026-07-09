import logging
import threading
import time
from datetime import datetime, timezone

import requests


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class TempoApiClient:
    def __init__(self, config):
        tempo_config = config.config_data.get("tempo", {})
        self.enabled = bool(tempo_config.get("enabled", True))
        self.base_url = str(
            tempo_config.get("api_base_url", "https://www.api-couleur-tempo.fr/api")
        ).rstrip("/")
        self.timeout_s = float(tempo_config.get("timeout_s", 3.0))
        self.cache_ttl_s = max(int(tempo_config.get("cache_ttl_s", 300)), 1)
        self.session = requests.Session()
        self._cache = None
        self._cache_monotonic = None
        self._lock = threading.Lock()
        self._refresh_thread = None

    def _fetch_json(self, route):
        response = self.session.get(
            f"{self.base_url}/{route.lstrip('/')}",
            timeout=self.timeout_s,
        )
        response.raise_for_status()
        return response.json()

    def get_state(self, force_refresh=False):
        if not self.enabled:
            return {
                "enabled": False,
                "available": False,
                "source": "disabled",
            }

        now_monotonic = time.monotonic()
        if (
            not force_refresh
            and self._cache is not None
            and self._cache_monotonic is not None
            and now_monotonic - self._cache_monotonic < self.cache_ttl_s
        ):
            return self._cache

        try:
            fetched_at = datetime.now(timezone.utc).isoformat()
            state = {
                "enabled": True,
                "available": True,
                "source": "tempo_api",
                "fetched_at": fetched_at,
                "now": self._fetch_json("now"),
                "today": self._fetch_json("jourTempo/today"),
                "tomorrow": self._fetch_json("jourTempo/tomorrow"),
                "tariffs": self._fetch_json("tarifs"),
            }
            with self._lock:
                self._cache = state
                self._cache_monotonic = now_monotonic
            return state
        except Exception:
            logging.exception("Tempo API refresh failed")
            with self._lock:
                cached = self._cache
            if cached is not None:
                stale = dict(cached)
                stale["source"] = "tempo_api_stale_cache"
                stale["stale"] = True
                return stale
            return {
                "enabled": True,
                "available": False,
                "source": "tempo_api_error",
            }

    def get_cached_state(self):
        if not self.enabled:
            return {
                "enabled": False,
                "available": False,
                "source": "disabled",
            }
        with self._lock:
            cached = self._cache
        if cached is not None:
            return cached
        return {
            "enabled": True,
            "available": False,
            "source": "tempo_cache_empty",
        }

    def refresh_if_due_background(self, force=False):
        if not self.enabled:
            return
        now_monotonic = time.monotonic()
        with self._lock:
            due = (
                force
                or self._cache is None
                or self._cache_monotonic is None
                or now_monotonic - self._cache_monotonic >= self.cache_ttl_s
            )
            running = self._refresh_thread is not None and self._refresh_thread.is_alive()
            if not due or running:
                return
            self._refresh_thread = threading.Thread(
                target=self.get_state,
                kwargs={"force_refresh": True},
                daemon=True,
            )
            self._refresh_thread.start()


def build_pricing_context(state, fallback_grid_price, feed_in_revenue):
    fallback_grid_price = float(fallback_grid_price)
    feed_in_revenue = float(feed_in_revenue)

    if not state or not state.get("available"):
        return {
            "grid_price_eur_per_kwh": fallback_grid_price,
            "feed_in_revenue_eur_per_kwh": feed_in_revenue,
            "source": "config",
            "tempo_available": False,
            "tariff_label": None,
            "color_label": None,
            "tomorrow_color_label": None,
            "display": None,
        }

    now_data = state.get("now") or {}
    today_data = state.get("today") or {}
    tomorrow_data = state.get("tomorrow") or {}
    grid_price = _safe_float(now_data.get("tarifKwh"))
    tariff_label = now_data.get("libTarif")
    color_label = today_data.get("libCouleur")
    tomorrow_color_label = tomorrow_data.get("libCouleur")

    if grid_price is None:
        return {
            "grid_price_eur_per_kwh": fallback_grid_price,
            "feed_in_revenue_eur_per_kwh": feed_in_revenue,
            "source": "config",
            "tempo_available": False,
            "tariff_label": tariff_label,
            "color_label": color_label,
            "tomorrow_color_label": tomorrow_color_label,
            "display": None,
        }

    display_parts = []
    if tariff_label:
        display_parts.append(str(tariff_label))
    display_parts.append(f"{grid_price:.4f} EUR/kWh")

    return {
        "grid_price_eur_per_kwh": grid_price,
        "feed_in_revenue_eur_per_kwh": feed_in_revenue,
        "source": state.get("source", "tempo_api"),
        "tempo_available": True,
        "tariff_label": tariff_label,
        "color_label": color_label,
        "tomorrow_color_label": tomorrow_color_label,
        "display": " ".join(display_parts),
        "raw": state,
    }
