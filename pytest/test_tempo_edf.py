from config import Config
from tempo_edf import TempoApiClient, build_pricing_context


class _FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_tempo_client_caches_and_builds_pricing_context():
    cfg = Config("templates/config.yml")
    client = TempoApiClient(cfg)

    calls = []

    def fake_get(url, timeout):
        calls.append((url, timeout))
        if url.endswith("/now"):
            return _FakeResponse(
                {
                    "applicableIn": 0,
                    "codeCouleur": 1,
                    "codeHoraire": 1,
                    "tarifKwh": 0.1612,
                    "libTarif": "Bleu-HP",
                }
            )
        if url.endswith("/jourTempo/today"):
            return _FakeResponse({"dateJour": "2026-04-04", "libCouleur": "Bleu"})
        if url.endswith("/jourTempo/tomorrow"):
            return _FakeResponse({"dateJour": "2026-04-05", "libCouleur": "Blanc"})
        if url.endswith("/tarifs"):
            return _FakeResponse({"bleuHP": 0.1612, "rougeHP": 0.706})
        raise AssertionError(f"Unexpected URL {url}")

    client.session.get = fake_get

    state_first = client.get_state()
    state_second = client.get_state()
    pricing = build_pricing_context(state_second, 0.325, 0.085)

    assert state_first["available"] is True
    assert state_second["available"] is True
    assert len(calls) == 4
    assert pricing["tempo_available"] is True
    assert pricing["grid_price_eur_per_kwh"] == 0.1612
    assert pricing["tariff_label"] == "Bleu-HP"
    assert pricing["color_label"] == "Bleu"
    assert pricing["tomorrow_color_label"] == "Blanc"
    assert pricing["display"] == "Bleu-HP 0.1612 EUR/kWh"


def test_tempo_pricing_context_falls_back_to_config():
    pricing = build_pricing_context(None, 0.325, 0.085)
    assert pricing["tempo_available"] is False
    assert pricing["grid_price_eur_per_kwh"] == 0.325
    assert pricing["feed_in_revenue_eur_per_kwh"] == 0.085
    assert pricing["source"] == "config"


def test_zen_weekend_pricing_context_uses_weekday_and_weekend_prices():
    prices = {
        "tariff": "zen_weekend",
        "revenue_per_fed_in_kwh": 0.085,
        "zen_weekend": {
            "weekday_ttc_per_kwh": 0.2180,
            "weekend_ttc_per_kwh": 0.1637,
        },
    }

    weekday = build_pricing_context(
        None,
        prices_config=prices,
        reference_time="2026-04-07T12:00:00+02:00",
    )
    holiday = build_pricing_context(
        None,
        prices_config=prices,
        reference_time="2026-05-08T12:00:00+02:00",
    )

    assert weekday["grid_price_eur_per_kwh"] == 0.2180
    assert weekday["tariff_label"] == "Zen Week-End - Heures Semaine"
    assert weekday["tariff_mode"] == "zen_weekend"
    assert holiday["grid_price_eur_per_kwh"] == 0.1637
    assert holiday["tariff_label"] == "Zen Week-End - Heures Week-End"


def test_standard_pricing_context_uses_tarif_bleu_base_price():
    prices = {
        "tariff": "standard",
        "revenue_per_fed_in_kwh": 0.085,
        "standard": {
            "base_ttc_per_kwh": 0.1927,
        },
    }

    pricing = build_pricing_context(
        None,
        prices_config=prices,
        reference_time="2026-04-07T12:00:00+02:00",
    )

    assert pricing["grid_price_eur_per_kwh"] == 0.1927
    assert pricing["source"] == "config_standard"
    assert pricing["tariff_label"] == "Tarif Bleu - Option Base"
    assert pricing["tariff_mode"] == "standard"


def test_zen_weekend_pricing_context_can_match_invoice_ht_lines():
    prices = {
        "tariff": "zen_weekend",
        "revenue_per_fed_in_kwh": 0.085,
        "zen_weekend": {
            "weekday_ttc_per_kwh": 0.2180,
            "weekend_ttc_per_kwh": 0.1637,
            "weekday_eht_per_kwh": 0.1514,
            "weekend_eht_per_kwh": 0.1060,
            "accise_eht_per_kwh": 0.03086,
            "vat_rate": 0.20,
        },
    }

    weekday = build_pricing_context(
        None,
        prices_config=prices,
        reference_time="2026-04-21T12:00:00+02:00",
    )
    weekend = build_pricing_context(
        None,
        prices_config=prices,
        reference_time="2026-04-25T12:00:00+02:00",
    )

    assert round(weekday["grid_price_eur_per_kwh"], 6) == 0.218712
    assert round(weekend["grid_price_eur_per_kwh"], 6) == 0.164232
