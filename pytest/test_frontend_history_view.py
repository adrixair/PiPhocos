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

    assert 'href="css/newdesign.css?build=20260815i"' in html
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
    assert "min-height: 260px;" in design
    assert "function toggleDashboardSettings()" in main_script
    assert "INFO_GRAPHIC_ARROW_COUNT = 10" in flow_script
    assert 'motion.setAttribute("rotate", "auto")' in flow_script
    assert 'stroke-dasharray: none !important;' in design
    assert '.power-flow-arrow-stream.is-active' in design
    assert 'id="flow_track_solar_hub"' in html
    assert 'viewBox="0 0 860 360"' not in html
    assert "function layoutInfoGraphicPaths" in flow_script
    assert "new ResizeObserver(queueInfoGraphicLabelLayout)" in flow_script
    assert "display: grid;" in design
    assert "grid-column: 3;" in design
    assert 'class="power-flow-map is-loading"' in html
    assert 'id="dashboard_power_flow" aria-busy="true"' in html
    assert ".power-flow-map.is-loading .power-flow-node-value" in design
    assert "function setPowerFlowLoadingState(loading)" in main_script


def test_dashboard_flow_displays_inverter_load_without_redundant_subtitle():
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    design = (ROOT / "site" / "css" / "newdesign.css").read_text(
        encoding="utf-8"
    )
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
    assert 'getMetricValueOrNull(payload, "ac_output_load_percent")' in flow_script
    assert 'formatInfoGraphicPercent(inverterLoad)' in flow_script
    assert 'formatInfoGraphicInverterMeta' not in flow_script
    assert 'formatInfoGraphicPercent(inverterLoad),\n        "",' in flow_script
    assert 'batteryMeta += " · " + formatInfoGraphicPercent(batterySoc);' in flow_script
    assert 'batteryMeta += " | "' not in flow_script
    assert 'flow_state_home_active: ["Consommation active"]' in localization
    assert 'flow_state_home_active: ["Charge en cours"]' not in localization
    assert 'class="power-flow-node-progress"' in html
    assert 'max-width: 65rem;' in design
    assert 'getInfoGraphicString("flow_state_live"' not in flow_script


def test_csv_download_is_removed_from_the_frontend():
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    main_script = (ROOT / "site" / "js" / "main.js").read_text(
        encoding="utf-8"
    )
    localization = (ROOT / "site" / "js" / "localization.js").read_text(
        encoding="utf-8"
    )

    assert 'data-nav-target="csv"' not in html
    assert 'id="view_csv"' not in html
    assert 'js/csv.js' not in html
    assert "Téléchargement CSV" not in html + localization
    assert "showViewCsv" not in main_script
    assert "updateCsvDateSelector" not in main_script
    assert not (ROOT / "site" / "js" / "csv.js").exists()


def test_history_energy_colors_are_repeated_by_their_icons():
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    design = (ROOT / "site" / "css" / "newdesign.css").read_text(
        encoding="utf-8"
    )

    assert "energy-metric-row energy-metric-solar is-emphasis" in html
    assert "energy-metric-row energy-metric-home is-emphasis" in html
    assert "energy-metric-row energy-metric-grid" in html
    assert "energy-metric-row energy-metric-battery" in html
    assert ".energy-metric-row > td:first-child" in design
    assert ".energy-metric-row.is-emphasis > td:nth-child(3)" in design
    assert "#history_stat_produced {" not in design
    assert "#history_stat_consumption_total {" not in design


def test_chart_loading_states_are_stable_and_energy_sources_stay_visible():
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    design = (ROOT / "site" / "css" / "newdesign.css").read_text(
        encoding="utf-8"
    )
    main_script = (ROOT / "site" / "js" / "main.js").read_text(
        encoding="utf-8"
    )
    chart_script = (ROOT / "site" / "js" / "chart_factory.js").read_text(
        encoding="utf-8"
    )

    assert 'id="dashboard_chart_shell"\n                                aria-busy="true"' in html
    assert 'role="img"' in html
    assert ".chart-shell-donut.is-loading::before" in design
    assert ".chart-shell.is-refreshing::after" in design
    assert "function setChartShellRefreshingState" in main_script
    assert "const shouldShowSkeleton = !gDashboardGraphHasLoadedOnce;" in main_script
    assert "const shouldShowRefresh = forceRefresh && gDashboardGraphHasLoadedOnce;" in main_script
    assert "hidden: true" not in chart_script
    assert "legendLabels.usePointStyle = true;" in chart_script
    assert "...STACKED_BAR_STYLE" in chart_script


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
