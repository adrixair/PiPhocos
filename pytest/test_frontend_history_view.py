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


def test_header_telemetry_status_stays_blank_until_status_is_known():
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "site" / "js" / "main.js").read_text(encoding="utf-8")
    localization = (ROOT / "site" / "js" / "localization.js").read_text(
        encoding="utf-8"
    )

    assert '<div class="app-header-status" aria-live="polite">' in html
    assert '<div class="app-telemetry-status" id="sidebar_live_telemetry"></div>' in html
    assert '<div class="app-sidebar-detail" id="telemetry_detail"></div>' in html
    assert '["sidebar_live_telemetry", ""]' in localization
    assert "let gTelemetryConnectionHealthy = null;" in script
    assert 'element.classList.remove("is-online", "is-offline");' in script


def test_new_design_keeps_header_semantic_and_flow_controls_honest():
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    design = (ROOT / "site" / "css" / "newdesign.css").read_text(
        encoding="utf-8"
    )
    main_script = (ROOT / "site" / "js" / "main.js").read_text(
        encoding="utf-8"
    )
    flow_script = (ROOT / "site" / "js" / "info_graphic.js").read_text(
        encoding="utf-8"
    )

    assert 'href="css/newdesign.css?build=20260815e"' in html
    assert '<div class="app-header-status" aria-live="polite">' in html
    assert "app-sidebar-footer" not in html
    assert "fa-user" not in html
    assert html.count("app-nav-link-temporal") == 4
    assert 'data-nav-target="today"' not in html
    assert 'data-nav-target="day"' in html and "fa-calendar-day" in html
    assert 'data-nav-target="month"' in html and "fa-calendar-days" in html
    assert 'data-nav-target="year"' in html and "fa-calendar" in html
    assert 'data-nav-target="all"' in html and "fa-chart-line" in html
    assert "--app-flow-grid: #dc2626;" in design
    assert 'id="dashboard_settings_toggle"' in html
    assert 'aria-expanded="false"' in html
    assert ".dashboard-settings-panel:not(.is-expanded)" in design
    assert "grid-template-columns: repeat(3, minmax(0, 1fr));" in design
    assert ".power-flow-map {\n  min-height: 260px;" in design
    assert "function toggleDashboardSettings()" in main_script
    assert "INFO_GRAPHIC_ARROW_COUNT = 7" in flow_script
    assert 'motion.setAttribute("rotate", "auto")' in flow_script
    assert 'stroke-dasharray: none !important;' in design
    assert '.power-flow-arrow-stream.is-active' in design


def test_dashboard_flow_displays_inverter_power_without_redundant_subtitle():
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    localization = (ROOT / "site" / "js" / "localization.js").read_text(
        encoding="utf-8"
    )
    main_script = (ROOT / "site" / "js" / "main.js").read_text(
        encoding="utf-8"
    )
    flow_script = (ROOT / "site" / "js" / "info_graphic.js").read_text(
        encoding="utf-8"
    )

    assert 'id="dashboard_subtitle"' not in html
    assert 'id="dashboard_subtitle_time"' not in html
    assert '["dashboard_subtitle",' not in localization
    assert 'getElementById("dashboard_subtitle_time")' not in main_script
    assert 'getMetricValueOrNull(payload, "total_output_active_power_w")' in flow_script
    assert 'formatInfoGraphicPower(inverterPower)' in flow_script
    assert 'localizeCompactOperationMode(payload?.device?.operation_mode)' in flow_script
    assert 'getInfoGraphicString("flow_state_live"' not in flow_script


def test_new_design_formats_invoice_amounts_to_cents():
    script = (ROOT / "site" / "js" / "main.js").read_text(encoding="utf-8")
    earned_formatter = re.search(
        r"function formatEarnedValue\(.*?\n}\n",
        script,
        flags=re.S,
    ).group(0)
    reduction_formatter = re.search(
        r"function formatReductionValue\(.*?\n}\n",
        script,
        flags=re.S,
    ).group(0)

    assert "numFormat(numericValue, 2)" in earned_formatter
    assert "numFormat(-Math.abs(numericValue), 2)" in reduction_formatter
    assert ", 5)" not in earned_formatter + reduction_formatter


def test_dynamic_inverter_count_values_are_localized_in_french():
    localization = (ROOT / "site" / "js" / "localization.js").read_text(
        encoding="utf-8"
    )

    assert '"Single unit only": ["Onduleur unique"]' in localization
    assert (
        '"Multiple units connected": ["Plusieurs onduleurs connectés"]'
        in localization
    )
