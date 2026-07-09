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


def test_billing_card_uses_short_invoice_labels():
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    localization = (ROOT / "site" / "js" / "localization.js").read_text(
        encoding="utf-8"
    )
    visible_copy = html + "\n" + localization

    assert "Coût brut TTC" in visible_copy
    assert "Économie solaire" in visible_copy
    assert "Crédit injection" in visible_copy
    assert "Facture TTC estimée" in visible_copy
    assert "abonnement fixe TTC" in visible_copy
    assert "Énergie réseau" not in visible_copy
    assert "history_text_bill_subscription" not in visible_copy
    assert "Réduction solaire" not in visible_copy
    assert "Coût net estimé" not in visible_copy
    assert "sans autoconsommation" not in visible_copy
    assert "Réduction autoconsommation" not in visible_copy
