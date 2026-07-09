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
