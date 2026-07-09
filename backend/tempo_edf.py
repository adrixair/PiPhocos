import logging
import threading
import time
from datetime import date, datetime, timedelta, timezone

import requests


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_reference_time(reference_time=None):
    if reference_time is None:
        return datetime.now(timezone.utc).astimezone()
    if isinstance(reference_time, datetime):
        if reference_time.tzinfo is None:
            return reference_time.replace(tzinfo=timezone.utc).astimezone()
        return reference_time.astimezone()
    if isinstance(reference_time, str):
        parsed = datetime.fromisoformat(reference_time)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone()
    return datetime.now(timezone.utc).astimezone()


def _easter_sunday(year):
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _french_national_holidays(year):
    easter = _easter_sunday(year)
    return {
        date(year, 1, 1),
        easter + timedelta(days=1),
        date(year, 5, 1),
        date(year, 5, 8),
        easter + timedelta(days=39),
        easter + timedelta(days=50),
        date(year, 7, 14),
        date(year, 8, 15),
        date(year, 11, 1),
        date(year, 11, 11),
        date(year, 12, 25),
    }


def _is_french_weekend_or_holiday(reference_time):
    local = _coerce_reference_time(reference_time)
    local_date = local.date()
    return local.weekday() >= 5 or local_date in _french_national_holidays(local.year)


def _prices_config_from_args(fallback_grid_price, feed_in_revenue, prices_config):
    if prices_config is None:
        return {
            "price_per_grid_kwh": fallback_grid_price,
            "revenue_per_fed_in_kwh": feed_in_revenue,
        }
    merged = dict(prices_config)
    if fallback_grid_price is not None:
        merged.setdefault("price_per_grid_kwh", fallback_grid_price)
    if feed_in_revenue is not None:
        merged.setdefault("revenue_per_fed_in_kwh", feed_in_revenue)
    return merged


def _flat_pricing_context(prices_config, *, source="config", display=None):
    grid_price = float(prices_config.get("price_per_grid_kwh", 0.0) or 0.0)
    feed_in_revenue = float(prices_config.get("revenue_per_fed_in_kwh", 0.0) or 0.0)
    subscription = float(prices_config.get("subscription_ttc_per_month", 0.0) or 0.0)
    price_display = display or f"{grid_price:.4f} EUR/kWh"
    return {
        "grid_price_eur_per_kwh": grid_price,
        "feed_in_revenue_eur_per_kwh": feed_in_revenue,
        "subscription_ttc_per_month": subscription,
        "source": source,
        "tempo_available": False,
        "tariff_label": None,
        "color_label": None,
        "tomorrow_color_label": None,
        "display": price_display,
        "price_display": price_display,
        "tariff_mode": "flat",
    }


def _standard_pricing_context(prices_config):
    standard_config = prices_config.get("standard") or {}
    grid_price = float(
        standard_config.get(
            "base_ttc_per_kwh",
            prices_config.get("price_per_grid_kwh", 0.0),
        )
        or 0.0
    )
    feed_in_revenue = float(prices_config.get("revenue_per_fed_in_kwh", 0.0) or 0.0)
    subscription = float(
        standard_config.get(
            "subscription_ttc_per_month",
            prices_config.get("subscription_ttc_per_month", 0.0),
        )
        or 0.0
    )
    label = str(standard_config.get("label") or "Tarif Bleu - Option Base")
    price_display = f"{label} {grid_price:.4f} EUR/kWh"
    return {
        "grid_price_eur_per_kwh": grid_price,
        "feed_in_revenue_eur_per_kwh": feed_in_revenue,
        "subscription_ttc_per_month": subscription,
        "source": "config_standard",
        "tempo_available": False,
        "tariff_label": label,
        "color_label": "Base",
        "tomorrow_color_label": None,
        "display": price_display,
        "price_display": price_display,
        "tariff_mode": "standard",
    }


def _zen_weekend_price(zen_config, reference_time):
    is_weekend_rate = _is_french_weekend_or_holiday(reference_time)
    if is_weekend_rate:
        price = zen_config.get("weekend_ttc_per_kwh")
        label = "Zen Week-End - Heures Week-End"
    else:
        price = zen_config.get("weekday_ttc_per_kwh")
        label = "Zen Week-End - Heures Semaine"

    weekday_eht = float(zen_config.get("weekday_eht_per_kwh", 0.0) or 0.0)
    weekend_eht = float(zen_config.get("weekend_eht_per_kwh", 0.0) or 0.0)
    accise_eht = float(zen_config.get("accise_eht_per_kwh", 0.0) or 0.0)
    vat_rate = float(zen_config.get("vat_rate", 0.20) or 0.0)
    has_eht_pricing = weekday_eht > 0.0 or weekend_eht > 0.0
    if not has_eht_pricing and price is not None:
        return float(price), label, is_weekend_rate

    base_eht = weekend_eht if is_weekend_rate else weekday_eht
    return (base_eht + accise_eht) * (1.0 + vat_rate), label, is_weekend_rate


def _zen_weekend_pricing_context(prices_config, *, reference_time=None):
    zen_config = prices_config.get("zen_weekend") or {}
    grid_price, label, is_weekend_rate = _zen_weekend_price(
        zen_config,
        reference_time,
    )
    feed_in_revenue = float(prices_config.get("revenue_per_fed_in_kwh", 0.0) or 0.0)
    subscription = float(
        zen_config.get(
            "subscription_ttc_per_month",
            prices_config.get("subscription_ttc_per_month", 0.0),
        )
        or 0.0
    )
    price_display = f"{label} {grid_price:.4f} EUR/kWh"
    return {
        "grid_price_eur_per_kwh": grid_price,
        "feed_in_revenue_eur_per_kwh": feed_in_revenue,
        "subscription_ttc_per_month": subscription,
        "source": "config_zen_weekend",
        "tempo_available": False,
        "tariff_label": label,
        "color_label": "Week-End" if is_weekend_rate else "Semaine",
        "tomorrow_color_label": None,
        "display": price_display,
        "price_display": price_display,
        "tariff_mode": "zen_weekend",
        "is_weekend_rate": is_weekend_rate,
    }


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


def build_pricing_context(
    state,
    fallback_grid_price=None,
    feed_in_revenue=None,
    *,
    prices_config=None,
    reference_time=None,
):
    prices_config = _prices_config_from_args(
        fallback_grid_price,
        feed_in_revenue,
        prices_config,
    )
    explicit_tariff = str(prices_config.get("tariff") or "").strip().lower()
    if explicit_tariff == "zen_weekend":
        return _zen_weekend_pricing_context(
            prices_config,
            reference_time=reference_time,
        )
    if explicit_tariff in {"standard", "tarif_bleu_base", "edf_base"}:
        return _standard_pricing_context(prices_config)
    if explicit_tariff == "flat":
        return _flat_pricing_context(prices_config)

    fallback_grid_price = float(prices_config.get("price_per_grid_kwh", 0.0) or 0.0)
    feed_in_revenue = float(prices_config.get("revenue_per_fed_in_kwh", 0.0) or 0.0)

    if not state or not state.get("available"):
        return _flat_pricing_context(
            {
                "price_per_grid_kwh": fallback_grid_price,
                "revenue_per_fed_in_kwh": feed_in_revenue,
                "subscription_ttc_per_month": prices_config.get(
                    "subscription_ttc_per_month",
                    0.0,
                ),
            }
        )

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
            "subscription_ttc_per_month": float(
                prices_config.get("subscription_ttc_per_month", 0.0) or 0.0
            ),
            "source": "config",
            "tempo_available": False,
            "tariff_label": tariff_label,
            "color_label": color_label,
            "tomorrow_color_label": tomorrow_color_label,
            "display": None,
            "price_display": None,
            "tariff_mode": "flat",
        }

    display_parts = []
    if tariff_label:
        display_parts.append(str(tariff_label))
    display_parts.append(f"{grid_price:.4f} EUR/kWh")

    return {
        "grid_price_eur_per_kwh": grid_price,
        "feed_in_revenue_eur_per_kwh": feed_in_revenue,
        "subscription_ttc_per_month": float(
            prices_config.get("subscription_ttc_per_month", 0.0) or 0.0
        ),
        "source": state.get("source", "tempo_api"),
        "tempo_available": True,
        "tariff_label": tariff_label,
        "color_label": color_label,
        "tomorrow_color_label": tomorrow_color_label,
        "display": " ".join(display_parts),
        "price_display": " ".join(display_parts),
        "tariff_mode": "tempo",
        "raw": state,
    }
