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
