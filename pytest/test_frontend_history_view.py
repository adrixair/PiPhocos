import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_all_time_history_view_uses_stable_selection_key():
    script = (ROOT / "site" / "js" / "main.js").read_text(encoding="utf-8")
    initial_key = re.search(
        r"function getInitialHistorySelectionKey\(.*?\n}\n",
        script,
        flags=re.S,
    ).group(0)
    selector_key = re.search(
        r"function getPeriodKeyFromSelectors\(.*?\n}\n",
        script,
        flags=re.S,
    ).group(0)
    apply_key = re.search(
        r"function applyPeriodKeyToSelectors\(.*?\n}\n",
        script,
        flags=re.S,
    ).group(0)

    for body in (initial_key, selector_key, apply_key):
        assert "if (mode === histories.ALL)\n        return histories.ALL;" in body
        assert "if (mode === histories.ALL)\n        return null;" not in body


def test_all_time_period_fetch_uses_period_endpoint():
    script = (ROOT / "site" / "js" / "main.js").read_text(encoding="utf-8")

    assert 'case histories.ALL:\n            query += "all";' in script


def test_history_mode_switch_selects_latest_available_period():
    script = (ROOT / "site" / "js" / "main.js").read_text(encoding="utf-8")
    initial_key = re.search(
        r"function getInitialHistorySelectionKey\(.*?\n}\n",
        script,
        flags=re.S,
    ).group(0)

    assert "const availability = getDateAvailabilityForMode(mode);" in initial_key
    assert "return String(availability.max);" in initial_key
    assert "getPeriodKeyFromDate(mode, gCurDate)" not in initial_key


def test_billing_card_uses_short_invoice_labels():
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    localization = (ROOT / "site" / "js" / "localization.js").read_text(
        encoding="utf-8"
    )
    visible_copy = html + "\n" + localization

    assert '<td id="history_text_bill_total">Coût brut</td>' in html
    assert '["history_text_bill_total", "Coût brut"]' in localization
    assert '["history_text_bill_total", "Coût brut TTC"]' not in localization
    assert "Économie solaire" in visible_copy
    assert "Crédit injection" in visible_copy
    assert '<td id="history_text_earned_total">Facture estimée</td>' in html
    assert '["history_text_earned_total", "Facture estimée"]' in localization
    assert '["history_text_earned_total", "Facture TTC estimée"]' not in localization
    assert "abonnement fixe TTC" in visible_copy
    assert "Énergie réseau" not in visible_copy
    assert "history_text_bill_subscription" not in visible_copy
    assert "Réduction solaire" not in visible_copy
    assert "Coût net estimé" not in visible_copy
    assert "sans autoconsommation" not in visible_copy
    assert "Réduction autoconsommation" not in visible_copy


def test_sidebar_telemetry_status_stays_blank_until_status_is_known():
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "site" / "js" / "main.js").read_text(encoding="utf-8")
    localization = (ROOT / "site" / "js" / "localization.js").read_text(
        encoding="utf-8"
    )

    assert (
        '<div class="app-telemetry-status" id="sidebar_live_telemetry" '
        'aria-live="polite"></div>'
    ) in html
    assert (
        '<div class="app-sidebar-detail" id="telemetry_detail" '
        'aria-live="polite"></div>'
    ) in html
    assert '["sidebar_live_telemetry", ""]' in localization
    assert "let gTelemetryConnectionHealthy = null;" in script
    assert 'element.classList.remove("is-online", "is-offline");' in script
