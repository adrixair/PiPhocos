// This base URL is used as the destination for REST query calls
var gBaseUrl = "";

// Global status flag
var gDashboardVisible = false;
var gAppInitialized = false;


// History types
const histories = {
    TODAY: 'today',
    DAY: 'day',
    MONTH: 'month',
    YEAR: 'year',
    ALL: 'all'
}

let gCurHistory = histories.DAY;

let gCurDate = new Date();
let gMinDate = null

let gDahboardGraphTimespan = 24

const dashboardTableConfigs = {
    current: [
        { kind: "metric", key: "ac_input_voltage_v", labelId: "metric_ac_input_voltage", icon: "fas fa-plug-circle-bolt", digits: 1, source: "QPGS0 / QPIGS" },
        { kind: "metric", key: "ac_input_frequency_hz", labelId: "metric_ac_input_frequency", icon: "fas fa-wave-square", digits: 2, source: "QPGS0 / QPIGS" },
        { kind: "metric", key: "ac_output_voltage_v", labelId: "metric_ac_output_voltage", icon: "fas fa-bolt", digits: 1, source: "QPGS0 / QPIGS" },
        { kind: "metric", key: "ac_output_frequency_hz", labelId: "metric_ac_output_frequency", icon: "fas fa-wave-square", digits: 2, source: "QPGS0 / QPIGS" },
        { kind: "metric", key: "ac_output_active_power_w", labelId: "metric_ac_output_active_power", icon: "fas fa-house", digits: 0, source: "QPGS0 / QPIGS" },
        { kind: "metric", key: "ac_output_apparent_power_va", labelId: "metric_ac_output_apparent_power", icon: "fas fa-gauge-high", digits: 0, source: "QPGS0 / QPIGS" },
        { kind: "metric", key: "ac_output_load_percent", labelId: "metric_ac_output_load", icon: "fas fa-chart-column", digits: 0, source: "QPGS0 / QPIGS" },
    ],
    battery: [
        { kind: "metric", key: "battery_state_of_charge_percent", labelId: "metric_battery_soc", icon: "fas fa-battery-half", digits: 0, source: "QPGS0 / QPIGS" },
        { kind: "text", path: ["live", "battery_state"], labelId: "metric_battery_state", icon: "fas fa-heart-pulse", sourceKind: "decoded", source: "status bits" },
        { kind: "metric", key: "battery_voltage_v", labelId: "metric_battery_voltage", icon: "fas fa-bolt", digits: 2, source: "QPGS0 / QPIGS" },
        { kind: "metric", key: "battery_voltage_from_scc_v", labelId: "metric_battery_voltage_scc", icon: "fas fa-solar-panel", digits: 2, source: "QPIGS" },
        { kind: "metric", key: "battery_charge_current_a", labelId: "metric_battery_charge_current", icon: "fas fa-arrow-up", digits: 2, source: "QPGS0 / QPIGS" },
        { kind: "metric", key: "battery_discharge_current_a", labelId: "metric_battery_discharge_current", icon: "fas fa-arrow-down", digits: 2, source: "QPGS0 / QPIGS" },
        { kind: "metric", key: "total_charging_current_a", labelId: "metric_total_charging_current", icon: "fas fa-charging-station", digits: 2, source: "QPGS0 / QPIGS" },
        { kind: "text", path: ["device", "battery_charger_source_priority"], labelId: "metric_battery_priority", icon: "fas fa-sliders", sourceKind: "decoded", source: "QPIRI / QPGS0" },
    ],
    solar: [
        { kind: "metric", key: "pv_input_voltage_v", labelId: "metric_pv_voltage", icon: "fas fa-solar-panel", digits: 1, source: "QPGS0 / QPIGS" },
        { kind: "metric", key: "pv_input_current_a", labelId: "metric_pv_current", icon: "fas fa-sun", digits: 2, source: "QPGS0 / QPIGS" },
        { kind: "metric", key: "pv_power_w", labelId: "metric_pv_power", icon: "fas fa-solar-panel", digits: 0, source: "QPIGS" },
        { kind: "metric", key: "pv_charging_power_w", labelId: "metric_pv_charging_power", icon: "fas fa-battery-three-quarters", digits: 0, source: "QPIGS" },
        { kind: "boolean", path: ["health", "mppt_active"], labelId: "metric_mppt_active", icon: "fas fa-sun", sourceKind: "decoded", source: "status bits" },
        { kind: "boolean", path: ["health", "solar_charging_on"], labelId: "metric_solar_charging", icon: "fas fa-solar-panel", sourceKind: "decoded", source: "status bits" },
        { kind: "boolean", path: ["health", "ac_charging_on"], labelId: "metric_ac_charging", icon: "fas fa-plug-circle-bolt", sourceKind: "decoded", source: "status bits" },
        { kind: "metric", key: "bus_voltage_v", labelId: "metric_bus_voltage", icon: "fas fa-microchip", digits: 1, source: "QPIGS" },
        { kind: "metric", key: "inverter_temperature_c", labelId: "metric_inverter_temperature", icon: "fas fa-temperature-half", digits: 1, source: "QPIGS" },
    ],
    device: [
        { kind: "text", path: ["device", "serial_number"], labelId: "metric_serial_number", icon: "fas fa-hashtag", sourceKind: "reported", source: "QID" },
        { kind: "text", path: ["device", "protocol_id"], labelId: "metric_protocol_id", icon: "fas fa-code", sourceKind: "reported", source: "QPI" },
        { kind: "text", path: ["device", "operation_mode"], labelId: "metric_operation_mode", icon: "fas fa-gear", sourceKind: "decoded", source: "QMOD" },
        { kind: "text", path: ["device", "ac_output_mode"], labelId: "metric_ac_output_mode", icon: "fas fa-diagram-project", sourceKind: "decoded", source: "QPGS0 / QPIRI" },
        { kind: "text", path: ["device", "output_source_priority"], labelId: "metric_output_priority", icon: "fas fa-shuffle", sourceKind: "decoded", source: "QPIRI" },
        { kind: "text", path: ["device", "other_units_connected"], labelId: "metric_other_units", icon: "fas fa-network-wired", sourceKind: "decoded", source: "QPGS0" },
        { kind: "text", path: ["device", "fault"], labelId: "metric_fault", icon: "fas fa-triangle-exclamation", sourceKind: "decoded", source: "QMOD / QPGS0" },
        { kind: "boolean", path: ["health", "ac_input_available"], labelId: "metric_ac_input_available", icon: "fas fa-plug-circle-check", sourceKind: "decoded", source: "status bits" },
        { kind: "boolean", path: ["health", "ac_output_on"], labelId: "metric_ac_output_on", icon: "fas fa-power-off", sourceKind: "decoded", source: "status bits" },
        { kind: "list", path: ["health", "active_warning_bits"], labelId: "metric_active_warnings", icon: "fas fa-circle-exclamation", sourceKind: "decoded", source: "QPIWS", showWhenEmpty: true },
    ],
}

const staticInfoBadgeConfigs = [
    { elementId: "history_text_produced", tooltipId: "produced_kwh" },
    { elementId: "history_text_self_consumed", tooltipId: "produced_to_house_kwh" },
    { elementId: "history_text_battery_charge", tooltipId: "produced_to_battery_kwh" },
    { elementId: "history_text_fedin", tooltipId: "usage_fed_in_kwh" },
    { elementId: "history_text_consumption_grid", tooltipId: "consumed_from_grid_kwh" },
    { elementId: "history_text_consumption_self", tooltipId: "consumed_from_pv_kwh" },
    { elementId: "history_text_consumption_battery", tooltipId: "consumed_from_battery_kwh" },
    { elementId: "history_text_consumption_total", tooltipId: "consumed_total_kwh" },
    { elementId: "history_text_earned_feedin", tooltipId: "earned_feedin" },
    { elementId: "history_text_earned_self", tooltipId: "earned_savings" },
    { elementId: "history_text_earned_total", tooltipId: "earned_total" },
    { elementId: "history_text_autarky", tooltipId: "autarky" },
];

let gActiveInfoBadge = null;
let gFloatingInfoTooltip = null;
let gChartResizeFrame = null;
let gInfoTooltipHandlersReady = false;
let gInfoTooltipShowTimer = null;
let gInfoTooltipHideTimer = null;
let gLastTelemetryRecordedAt = null;
let gTelemetryConnectionHealthy = false;
let gInitialViewApplied = false;
let gCurrentView = "dashboard";
let gDashboardOverviewRequest = null;
let gDashboardStatsRefreshInFlight = false;
let gDashboardGraphRefreshInFlight = false;
let gDashboardHasLoadedOnce = false;
let gDashboardGraphHasLoadedOnce = false;
let gHistoryLiveRefreshInFlight = false;
let gStatisticsRequestToken = 0;
let gStatisticsHasLoadedOnce = false;
let gHistoryRequestToken = 0;
let gHistoryHasLoadedOnce = false;
let gLastDashboardGraphRecordedAt = null;
let gLastDashboardGraphRefreshAt = 0;
let gLastDashboardRenderSignature = null;
let gLastTelemetryBackgroundFetchAt = 0;
let gLastHistoryLiveRefreshAt = 0;
let gLastHistoryHighResSelectionKey = null;
let gLastHistoryHighResRaw = null;
let gDateBoundsRequest = null;
let gDateSelectorsInitialized = false;
let gDateBoundsLoaded = false;

const DATA_REFRESH_INTERVAL_MS = 5 * 1000;
const DASHBOARD_GRAPH_REFRESH_THROTTLE_MS = 10 * 1000;
const HISTORY_LIVE_REFRESH_MS = DATA_REFRESH_INTERVAL_MS;
const HISTORY_LIVE_REFRESH_THROTTLE_MS = 15 * 1000;
const BACKGROUND_TELEMETRY_REFRESH_MS = 20 * 1000;
const FLOATING_INFO_TOOLTIP_ID = "floating-info-tooltip";
const INFO_TOOLTIP_SHOW_DELAY_MS = 0;
const INFO_TOOLTIP_HIDE_DELAY_MS = 0;
const VIEW_STATE_STORAGE_KEY = "piphocos_view_state";
const STATISTICS_LOADING_ELEMENT_IDS = [
    "stats_highest_prod_value",
    "stats_highest_prod_date",
    "stats_best_day_value",
    "stats_best_day_date",
    "stats_best_month_value",
    "stats_best_month_date",
    "stats_best_year_value",
    "stats_best_year_date",
    "statistics_value_avg_daily_prod",
    "statistics_value_start_date",
    "statistics_value_runtime",
];
const HISTORY_LOADING_ELEMENT_IDS = [
    "history_stat_produced",
    "history_stat_self_consumed",
    "history_stat_battery_charge",
    "history_stat_fedin",
    "history_stat_consumption_grid",
    "history_stat_consumption_self",
    "history_stat_consumption_battery",
    "history_stat_consumption_total",
    "history_stat_earned_feedin",
    "history_stat_earned_self",
    "history_stat_earned_total",
    "history_stat_autarky",
];
const HISTORY_CHART_SHELL_IDS = [
    "history_chart_usage_shell",
    "history_chart_consumption_shell",
    "history_chart_details_production_shell",
    "history_chart_details_consumption_shell",
    "history_chart_high_res_shell",
];
const DASHBOARD_SKELETON_TABLE_ROWS = {
    dash_current_table: 7,
    dash_battery_table: 8,
    dash_solar_table: 9,
    dash_device_table: 10,
};

function getInitialViewFromQuery() {
    const params = new URLSearchParams(window.location.search);
    return (params.get("view") || "").toLowerCase();
}

function getInitialHistoryModeFromQuery(value) {
    switch ((value || "").toLowerCase()) {
        case histories.TODAY:
            return histories.TODAY;
        case histories.MONTH:
            return histories.MONTH;
        case histories.YEAR:
            return histories.YEAR;
        case histories.ALL:
            return histories.ALL;
        case histories.DAY:
        default:
            return histories.DAY;
    }
}

function parseHistoryDateForViewState(value, mode) {
    if (typeof value !== "string" || value.trim() === "")
        return null;

    const normalized = value.trim();
    let candidate = null;

    if ((mode === histories.DAY || mode === histories.TODAY) && /^\d{4}-\d{2}-\d{2}$/.test(normalized))
        candidate = new Date(normalized + "T12:00:00");
    else if (mode === histories.MONTH && /^\d{4}-\d{2}$/.test(normalized))
        candidate = new Date(normalized + "-01T12:00:00");
    else if (mode === histories.YEAR && /^\d{4}$/.test(normalized))
        candidate = new Date(normalized + "-01-01T12:00:00");

    if (!(candidate instanceof Date) || !Number.isFinite(candidate.getTime()))
        return null;

    return candidate;
}

function clampSelectableDate(date) {
    if (!(date instanceof Date) || !Number.isFinite(date.getTime()))
        return new Date();

    const clamped = new Date(date);
    if (gMinDate instanceof Date && Number.isFinite(gMinDate.getTime()) && clamped < gMinDate)
        clamped.setTime(gMinDate.getTime());

    const maxDate = new Date();
    if (clamped > maxDate)
        clamped.setTime(maxDate.getTime());

    return clamped;
}

function formatHistoryDateForViewState(mode) {
    if (mode === histories.ALL)
        return "";
    if (!(gCurDate instanceof Date) || !Number.isFinite(gCurDate.getTime()))
        return "";

    const year = gCurDate.getFullYear();
    const month = padStr(gCurDate.getMonth() + 1);
    const day = padStr(gCurDate.getDate());

    switch (mode) {
        case histories.MONTH:
            return year + "-" + month;
        case histories.YEAR:
            return String(year);
        case histories.DAY:
        case histories.TODAY:
        default:
            return year + "-" + month + "-" + day;
    }
}

function normalizeViewState(candidate) {
    const view = (candidate?.view || "").toLowerCase();
    if (view === "statistics")
        return { view: "statistics" };
    if (view === "csv")
        return { view: "csv" };
    if (view === "history")
        return {
            view: "history",
            history: getInitialHistoryModeFromQuery(candidate?.history),
            date: typeof candidate?.date === "string" ? candidate.date : "",
        };
    return { view: "dashboard" };
}

function getStoredViewState() {
    try {
        const raw = localStorage.getItem(VIEW_STATE_STORAGE_KEY);
        if (!raw)
            return null;
        return normalizeViewState(JSON.parse(raw));
    } catch {
        return null;
    }
}

function getCurrentViewState() {
    switch (gCurrentView) {
        case "statistics":
            return { view: "statistics" };
        case "csv":
            return { view: "csv" };
        case "history":
            return {
                view: "history",
                history: gCurHistory,
                date: formatHistoryDateForViewState(gCurHistory),
            };
        case "dashboard":
        default:
            return { view: "dashboard" };
    }
}

function persistCurrentViewState() {
    const state = normalizeViewState(getCurrentViewState());

    try {
        localStorage.setItem(VIEW_STATE_STORAGE_KEY, JSON.stringify(state));
    } catch {
        // Ignore storage failures and keep the URL in sync.
    }

    const url = new URL(window.location.href);
    const params = url.searchParams;

    if (state.view === "dashboard") {
        params.delete("view");
        params.delete("history");
        params.delete("date");
    } else {
        params.set("view", state.view);
        if (state.view === "history") {
            params.set("history", state.history);
            if (state.date)
                params.set("date", state.date);
            else
                params.delete("date");
        } else {
            params.delete("history");
            params.delete("date");
        }
    }

    const query = params.toString();
    const nextUrl = url.pathname + (query ? "?" + query : "") + url.hash;
    window.history.replaceState({}, "", nextUrl);
}

function getInitialViewState() {
    const params = new URLSearchParams(window.location.search);
    const view = getInitialViewFromQuery();

    if (view !== "") {
        return normalizeViewState({
            view,
            history: params.get("history"),
            date: params.get("date") || "",
        });
    }

    return getStoredViewState() || { view: "dashboard" };
}

function applyInitialViewState() {
    if (gInitialViewApplied)
        return;

    gInitialViewApplied = true;

    const state = getInitialViewState();
    switch (state.view) {
        case "statistics":
            showViewStatistics({ persist: false });
            break;
        case "history":
            showViewHistory(state.history, { persist: false, initialDate: state.date });
            break;
        case "csv":
            showViewCsv({ persist: false });
            break;
        case "dashboard":
        default:
            showViewDashboard({ persist: false });
            break;
    }

    persistCurrentViewState();
}


// Called when index.html has finished loading
window.addEventListener('DOMContentLoaded', event => {
    gBaseUrl = new URL('.', window.location.href).href;
    console.log("Setting base URI to " + gBaseUrl);
    restoreLanguage();
    restoreSettings();
    setupInfoTooltipHandlers();
    configureDashboardLayout();
    configureStaticInfoBadges();
    setInterval(updateTime, 1000);
    setInterval(updateCurrentStats, DATA_REFRESH_INTERVAL_MS);
    setInterval(refreshTelemetryStatus, DATA_REFRESH_INTERVAL_MS);
    setInterval(refreshLiveHistoryStats, HISTORY_LIVE_REFRESH_MS);
    initSelectionBoxes();
    updateCsvDateSelector();
    setVersion();
    setName();
    gAppInitialized = true;
    applyInitialViewState();
    const initialView = getInitialViewState().view;
    window.setTimeout(() => {
        ensureDateBoundsLoaded().catch(() => { });
    }, initialView === "dashboard" ? 1500 : 0);
});

document.addEventListener("visibilitychange", () => {
    if (document.hidden)
        return;
    refreshTelemetryStatus();
    if (gDashboardVisible) {
        updateCurrentStats();
        return;
    }
    refreshLiveHistoryStats();
});

function setName() {
    const instanceName = document.getElementById("instance-name");
    if (instanceName != null)
        instanceName.textContent = "PiPhocos";
    document.title = "PiPhocos";
}

function restoreSettings() {
    var ts = localStorage.getItem("dash_time_span");
    if (ts != null)
        gDahboardGraphTimespan = parseInt(ts);
    updateDashboardTimeSpanButtons();
}

function normalizeRecordedAtKey(recordedAt) {
    if (recordedAt == null)
        return null;
    const timestamp = recordedAt instanceof Date ? recordedAt.getTime() : new Date(recordedAt).getTime();
    if (!Number.isFinite(timestamp))
        return null;
    return new Date(timestamp).toISOString();
}

function getDashboardRenderSignature(stats) {
    return [
        normalizeRecordedAtKey(stats?.["recorded_at"]),
        stats?.["current_data_stale"] === true ? "stale" : "fresh",
        stats?.["pricing"]?.["tempo_display"] || "",
    ].join("|");
}

function getCurrentHistorySelectionKey() {
    return [
        gCurHistory,
        document.getElementById('selection_year2')?.value?.toString() || "",
        padStr(document.getElementById('selection_month2')?.value?.toString() || ""),
        padStr(document.getElementById('selection_day2')?.value?.toString() || ""),
    ].join("|");
}

function getTelemetryTimeLabel() {
    const timestamp = gLastTelemetryRecordedAt instanceof Date ? gLastTelemetryRecordedAt.getTime() : new Date(gLastTelemetryRecordedAt).getTime();
    if (!Number.isFinite(timestamp))
        return null;

    return new Date(timestamp).toLocaleTimeString(getLocale(), { timeZone: "Europe/Paris" });
}

function renderTelemetryDetail() {
    const element = document.getElementById("telemetry_detail");
    if (element == null)
        return;

    const timeLabel = getTelemetryTimeLabel();
    if (timeLabel != null) {
        element.textContent = getGenericString("telemetry_detail_last_sample") + timeLabel;
        return;
    }

    element.textContent = getGenericString("telemetry_detail_waiting");
}

function renderTelemetryStatus() {
    const element = document.getElementById("sidebar_live_telemetry");
    renderTelemetryDetail();
    if (element == null)
        return;

    element.textContent = getGenericString(
        gTelemetryConnectionHealthy
            ? "telemetry_status_connected"
            : "telemetry_status_disconnected"
    );
    element.classList.toggle("is-online", gTelemetryConnectionHealthy);
    element.classList.toggle("is-offline", !gTelemetryConnectionHealthy);
}

function applyTelemetryStatusFromOverview(stats) {
    gTelemetryConnectionHealthy = stats != null;

    if (stats != null && stats["recorded_at"]) {
        const nextRecordedAt = new Date(stats["recorded_at"]);
        if (Number.isFinite(nextRecordedAt.getTime()))
            gLastTelemetryRecordedAt = nextRecordedAt;
    }

    renderTelemetryStatus();
}

function refreshTelemetryStatus() {
    if (document.hidden)
        return;
    if (gDashboardVisible) {
        renderTelemetryStatus();
        return;
    }

    const now = Date.now();
    if ((now - gLastTelemetryBackgroundFetchAt) < BACKGROUND_TELEMETRY_REFRESH_MS) {
        renderTelemetryStatus();
        return;
    }
    gLastTelemetryBackgroundFetchAt = now;

    fetchDashboardOverviewJSON()
        .then(stats => applyTelemetryStatusFromOverview(stats))
        .catch(() => {
            gTelemetryConnectionHealthy = false;
            renderTelemetryStatus();
        });
}

function configureDashboardLayout() {
    updateDashboardTimeSpanButtons();
}

function escapeHtml(text) {
    return String(text ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function getNestedValue(obj, path) {
    let value = obj;
    for (let i = 0; i < path.length; ++i) {
        if (value == null)
            return null;
        value = value[path[i]];
    }
    return value;
}

function buildDashboardTooltip(entry, currentValue) {
    const sections = [];
    const helpText = getDashboardFieldHelpString(entry.labelId);

    if (currentValue != null && String(currentValue).trim() != "")
        sections.push('<strong>' + escapeHtml(getDashboardInfoString("tooltip_current_prefix") + String(currentValue)) + '</strong>');

    if (helpText)
        sections.push(escapeHtml(helpText));

    return sections.join("<br>");
}

function buildInfoBadge(content) {
    return '<button type="button" class="dashboard-info-badge" data-info-content="'
        + escapeHtml(content)
        + '" aria-label="Info" aria-expanded="false">i</button>';
}

function clearInfoTooltipTimers() {
    if (gInfoTooltipShowTimer != null) {
        clearTimeout(gInfoTooltipShowTimer);
        gInfoTooltipShowTimer = null;
    }
    if (gInfoTooltipHideTimer != null) {
        clearTimeout(gInfoTooltipHideTimer);
        gInfoTooltipHideTimer = null;
    }
}

function ensureFloatingInfoTooltip() {
    if (gFloatingInfoTooltip != null)
        return gFloatingInfoTooltip;

    const tooltip = document.createElement("div");
    tooltip.id = FLOATING_INFO_TOOLTIP_ID;
    tooltip.className = "app-floating-tooltip";
    tooltip.setAttribute("role", "tooltip");
    tooltip.setAttribute("aria-hidden", "true");
    document.body.appendChild(tooltip);
    gFloatingInfoTooltip = tooltip;
    return tooltip;
}

function isFloatingInfoTooltipVisible() {
    return gFloatingInfoTooltip != null && gFloatingInfoTooltip.classList.contains("is-visible");
}

function setInfoBadgeExpanded(badge, expanded) {
    if (badge == null)
        return;
    badge.classList.toggle("is-active", expanded);
    badge.setAttribute("aria-expanded", expanded ? "true" : "false");
}

function positionFloatingInfoTooltip(badge) {
    const tooltip = ensureFloatingInfoTooltip();
    const badgeRect = badge.getBoundingClientRect();
    const tooltipRect = tooltip.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const gap = 12;

    let left = badgeRect.left + (badgeRect.width / 2) - (tooltipRect.width / 2);
    let top = badgeRect.bottom + gap;
    let placement = "bottom";

    if (left + tooltipRect.width > viewportWidth - gap)
        left = viewportWidth - tooltipRect.width - gap;
    if (left < gap)
        left = gap;

    if (top + tooltipRect.height > viewportHeight - gap) {
        top = badgeRect.top - tooltipRect.height - gap;
        placement = "top";
    }
    if (top < gap)
        top = gap;

    tooltip.style.left = left + "px";
    tooltip.style.top = top + "px";
    tooltip.dataset.placement = placement;
}

function showFloatingInfoTooltip(badge) {
    if (badge == null)
        return;

    if (gInfoTooltipHideTimer != null) {
        clearTimeout(gInfoTooltipHideTimer);
        gInfoTooltipHideTimer = null;
    }

    const content = badge?.dataset?.infoContent;
    if (badge == null || content == null || content === "")
        return;

    const tooltip = ensureFloatingInfoTooltip();
    if (gActiveInfoBadge != null && gActiveInfoBadge !== badge)
        setInfoBadgeExpanded(gActiveInfoBadge, false);
    gActiveInfoBadge = badge;
    tooltip.innerHTML = content;
    tooltip.classList.add("is-visible");
    tooltip.setAttribute("aria-hidden", "false");
    setInfoBadgeExpanded(badge, true);
    positionFloatingInfoTooltip(badge);
}

function hideFloatingInfoTooltip(force) {
    if (gInfoTooltipShowTimer != null) {
        clearTimeout(gInfoTooltipShowTimer);
        gInfoTooltipShowTimer = null;
    }
    if (gFloatingInfoTooltip == null)
        return;
    gFloatingInfoTooltip.classList.remove("is-visible");
    gFloatingInfoTooltip.setAttribute("aria-hidden", "true");
    if (force)
        gFloatingInfoTooltip.innerHTML = "";
    setInfoBadgeExpanded(gActiveInfoBadge, false);
    gActiveInfoBadge = null;
}

function toggleFloatingInfoTooltip(badge) {
    clearInfoTooltipTimers();
    if (gActiveInfoBadge === badge && isFloatingInfoTooltipVisible()) {
        hideFloatingInfoTooltip(true);
        return;
    }
    showFloatingInfoTooltip(badge);
}

function scheduleShowFloatingInfoTooltip(badge, delay = INFO_TOOLTIP_SHOW_DELAY_MS) {
    if (badge == null)
        return;

    if (gActiveInfoBadge === badge && gFloatingInfoTooltip?.classList.contains("is-visible")) {
        if (gInfoTooltipHideTimer != null) {
            clearTimeout(gInfoTooltipHideTimer);
            gInfoTooltipHideTimer = null;
        }
        positionFloatingInfoTooltip(badge);
        return;
    }

    if (gInfoTooltipShowTimer != null)
        clearTimeout(gInfoTooltipShowTimer);
    gInfoTooltipShowTimer = setTimeout(() => {
        gInfoTooltipShowTimer = null;
        showFloatingInfoTooltip(badge);
    }, delay);
}

function scheduleHideFloatingInfoTooltip(delay = INFO_TOOLTIP_HIDE_DELAY_MS, force = true) {
    if (gInfoTooltipHideTimer != null)
        clearTimeout(gInfoTooltipHideTimer);
    gInfoTooltipHideTimer = setTimeout(() => {
        gInfoTooltipHideTimer = null;
        hideFloatingInfoTooltip(force);
    }, delay);
}

function bindInfoBadgeEvents(root = document) {
    root.querySelectorAll(".dashboard-info-badge[data-info-content]").forEach(badge => {
        if (badge.dataset.infoBound === "1")
            return;

        badge.dataset.infoBound = "1";

        badge.addEventListener("mouseenter", () => {
            scheduleShowFloatingInfoTooltip(badge);
        });

        badge.addEventListener("mouseleave", () => {
            scheduleHideFloatingInfoTooltip();
        });

        badge.addEventListener("click", event => {
            event.preventDefault();
            event.stopPropagation();
            toggleFloatingInfoTooltip(badge);
        });

        badge.addEventListener("keydown", event => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                toggleFloatingInfoTooltip(badge);
                return;
            }
            if (event.key === "Escape")
                hideFloatingInfoTooltip(true);
        });
    });
}

function setupInfoTooltipHandlers() {
    ensureFloatingInfoTooltip();
    if (gInfoTooltipHandlersReady)
        return;
    gInfoTooltipHandlersReady = true;

    window.addEventListener("scroll", () => {
        hideFloatingInfoTooltip(true);
    }, true);

    window.addEventListener("resize", () => {
        if (gActiveInfoBadge != null)
            positionFloatingInfoTooltip(gActiveInfoBadge);
    });

    document.addEventListener("click", event => {
        const badge = event.target instanceof Element
            ? event.target.closest(".dashboard-info-badge[data-info-content]")
            : null;
        if (badge != null)
            return;
        hideFloatingInfoTooltip(true);
    });

    document.addEventListener("keydown", event => {
        if (event.key === "Escape")
            hideFloatingInfoTooltip(true);
    });
}

function initDashboardTooltips() {
    bindInfoBadgeEvents(document);
    hideFloatingInfoTooltip(true);
}

function updateDashboardTimeSpanButtons() {
    document.querySelectorAll("[data-dashboard-hours]").forEach(button => {
        const hours = Number(button.dataset.dashboardHours || 0);
        const selected = hours === gDahboardGraphTimespan;
        button.classList.toggle("is-active", selected);
        button.setAttribute("aria-pressed", selected ? "true" : "false");
    });
}

function queueVisibleChartResize() {
    if (typeof resizeVisibleCharts !== "function")
        return;
    if (gChartResizeFrame != null)
        cancelAnimationFrame(gChartResizeFrame);
    gChartResizeFrame = requestAnimationFrame(() => {
        gChartResizeFrame = null;
        requestAnimationFrame(() => resizeVisibleCharts());
    });
}

function setActiveSidebarLink(target) {
    document.querySelectorAll(".app-nav-link").forEach(link => {
        const selected = link.dataset.navTarget === target;
        link.classList.toggle("is-active", selected);
        if (selected)
            link.setAttribute("aria-current", "page");
        else
            link.removeAttribute("aria-current");
    });
}

function setTextSkeletonState(elementIds, loading) {
    elementIds.forEach(id => {
        const element = document.getElementById(id);
        if (element == null)
            return;
        element.classList.toggle("app-skeleton-text", loading === true);
    });
}

function setChartShellLoadingState(elementIds, loading) {
    elementIds.forEach(id => {
        const element = document.getElementById(id);
        if (element == null)
            return;
        element.classList.toggle("is-loading", loading === true);
    });
}

function buildDashboardSkeletonTable(rowCount) {
    let rows = "";
    for (let i = 0; i < rowCount; i++) {
        rows += '<tr>'
            + '<td class="dashboard-icon-cell"><span class="app-skeleton-dot" aria-hidden="true"></span></td>'
            + '<td class="dashboard-label-cell"><span class="app-skeleton-line app-skeleton-line-long" aria-hidden="true"></span></td>'
            + '<td class="text-end text-nowrap"><span class="app-skeleton-line app-skeleton-line-short ms-auto" aria-hidden="true"></span></td>'
            + '<td class="text-end text-nowrap"><span class="app-skeleton-line app-skeleton-line-unit ms-auto" aria-hidden="true"></span></td>'
            + '</tr>';
    }
    return '<table class="table table-borderless table-sm mb-0 dashboard-metrics"><tbody>' + rows + '</tbody></table>';
}

function setDashboardInitialLoadingState(loading) {
    const subtitle = document.getElementById("dashboard_subtitle_time");
    if (subtitle != null)
        subtitle.classList.toggle("app-skeleton-text", loading === true);

    if (loading) {
        setViewBusyState("view_dashboard", true);
        Object.entries(DASHBOARD_SKELETON_TABLE_ROWS).forEach(([containerId, rowCount]) => {
            const container = document.getElementById(containerId);
            if (container != null)
                container.innerHTML = buildDashboardSkeletonTable(rowCount);
        });
        setChartShellLoadingState(["dashboard_chart_shell"], true);
        return;
    }

    setViewBusyState("view_dashboard", false);
    setChartShellLoadingState(["dashboard_chart_shell"], false);
}

function setStatisticsLoadingState(loading) {
    setTextSkeletonState(STATISTICS_LOADING_ELEMENT_IDS, loading);
}

function setHistoryLoadingState(loading) {
    setTextSkeletonState(HISTORY_LOADING_ELEMENT_IDS, loading);
    setChartShellLoadingState(HISTORY_CHART_SHELL_IDS, loading);
}

function getHistoryDateForMode(mode, initialDate = "") {
    if (mode === histories.TODAY)
        return new Date();
    if (mode === histories.ALL)
        return null;

    const parsed = parseHistoryDateForViewState(initialDate, mode);
    if (parsed != null)
        return clampSelectableDate(parsed);

    if (gCurDate instanceof Date && Number.isFinite(gCurDate.getTime()))
        return clampSelectableDate(gCurDate);

    return clampSelectableDate(new Date());
}

function buildDashboardRow(entry, payload) {
    if (entry.kind == "metric") {
        const metric = payload["live"]?.[entry.key];
        if (metric == null || metric["value"] == null || metric["semantics"] != "exact")
            return null;
        return {
            icon: entry.icon,
            label: getDashboardMetricString(entry.labelId),
            value: numFormat(metric["value"], entry.digits ?? 0),
            unit: metric["unit"] || "",
            tooltip: buildDashboardTooltip(entry, numFormat(metric["value"], entry.digits ?? 0) + (metric["unit"] ? " " + metric["unit"] : "")),
        };
    }

    const rawValue = getNestedValue(payload, entry.path);
    if (entry.kind == "boolean") {
        if (rawValue == null)
            return null;
        return {
            icon: entry.icon,
            label: getDashboardMetricString(entry.labelId),
            value: rawValue ? getGenericString("boolean_yes") : getGenericString("boolean_no"),
            unit: "",
            tooltip: buildDashboardTooltip(entry, rawValue ? getGenericString("boolean_yes") : getGenericString("boolean_no")),
        };
    }

    if (entry.kind == "list") {
        const values = Array.isArray(rawValue) ? rawValue : [];
        const localizedValues = values.map(value => localizeDashboardValue(entry.labelId, value));
        if (values.length == 0 && !entry.showWhenEmpty)
            return null;
        return {
            icon: entry.icon,
            label: getDashboardMetricString(entry.labelId),
            value: localizedValues.length > 0 ? localizedValues.join(", ") : getGenericString("none"),
            unit: "",
            tooltip: buildDashboardTooltip(entry, localizedValues.length > 0 ? localizedValues.join(", ") : getGenericString("none")),
        };
    }

    if (rawValue == null || rawValue === "")
        return null;
    const localizedValue = localizeDashboardValue(entry.labelId, rawValue);
    return {
        icon: entry.icon,
        label: getDashboardMetricString(entry.labelId),
        value: String(localizedValue),
        unit: "",
        tooltip: buildDashboardTooltip(entry, String(localizedValue)),
    };
}

function renderDashboardTable(containerId, config, payload) {
    const container = document.getElementById(containerId);
    if (container == null)
        return;

    const rows = config
        .map(entry => buildDashboardRow(entry, payload))
        .filter(row => row != null);

    if (rows.length == 0) {
        container.innerHTML = '<div class="small text-secondary">' + escapeHtml(getDashboardInfoString("no_direct_values")) + '</div>';
        return;
    }

    container.innerHTML = '<table class="table table-borderless table-sm mb-0 dashboard-metrics"><tbody>'
        + rows.map(row => (
            '<tr>'
            + '<td class="dashboard-icon-cell"><span class="dashboard-row-icon"><i class="' + escapeHtml(row.icon) + '"></i></span></td>'
            + '<td class="dashboard-label-cell">'
            + '<span class="app-inline-label">'
            + '<span class="app-inline-label-text">' + escapeHtml(row.label) + '</span>'
            + buildInfoBadge(row.tooltip)
            + '</span>'
            + '</td>'
            + '<td class="text-end text-nowrap">' + escapeHtml(row.value) + '</td>'
            + '<td class="text-end text-nowrap text-secondary">' + escapeHtml(row.unit) + '</td>'
            + '</tr>'
        )).join("")
        + '</tbody></table>';
}

function configureStaticInfoBadges() {
    staticInfoBadgeConfigs.forEach(entry => {
        const element = document.getElementById(entry.elementId);
        if (element == null)
            return;
        const labelNode = element.querySelector("[data-info-label]");
        const label = labelNode != null ? labelNode.textContent.trim() : element.textContent.trim();
        const tooltip = getHistoryInfoString(entry.tooltipId);
        element.innerHTML = '<span class="app-inline-label">'
            + '<span class="app-inline-label-text" data-info-label="1">' + escapeHtml(label) + '</span>'
            + buildInfoBadge(tooltip)
            + '</span>';
    });
    initDashboardTooltips();
}

// Called cyclically to update the current stats
function updateCurrentStats() {
    if (!gDashboardVisible || document.hidden) return;
    if (gActiveInfoBadge != null || gInfoTooltipShowTimer != null)
        return;
    if (gDashboardStatsRefreshInFlight)
        return;

    if (!gDashboardHasLoadedOnce)
        setDashboardInitialLoadingState(true);

    gDashboardStatsRefreshInFlight = true;
    fetchDashboardOverviewJSON().then(stats => {
        applyTelemetryStatusFromOverview(stats);
        if (stats["state"] != "ok") {
            gLastDashboardRenderSignature = null;
            gDashboardHasLoadedOnce = true;
            setDashboardInitialLoadingState(false);
            document.getElementById("dashboard_subtitle_time").innerHTML = getGenericString("unavailable");
            ["dash_current_table", "dash_battery_table", "dash_solar_table", "dash_device_table"].forEach(id => {
                const container = document.getElementById(id);
                if (container != null)
                    container.innerHTML = '<div class="small text-secondary">' + escapeHtml(getDashboardInfoString("no_direct_values")) + '</div>';
            });
            if (typeof updateInfoGraphic === "function")
                updateInfoGraphic(null);
            return;
        }

        const renderSignature = getDashboardRenderSignature(stats);
        if (renderSignature === gLastDashboardRenderSignature)
            return;
        gLastDashboardRenderSignature = renderSignature;
        gDashboardHasLoadedOnce = true;
        setDashboardInitialLoadingState(false);

        const recordedAt = stats["recorded_at"] ? new Date(stats["recorded_at"]) : new Date();
        let subtitleText = recordedAt.toLocaleTimeString(getLocale(), { timeZone: "Europe/Paris" });
        const tempoDisplay = stats["pricing"]?.["tempo_display"];
        if (tempoDisplay)
            subtitleText += " | Tempo: " + tempoDisplay;
        document.getElementById("dashboard_subtitle_time").innerHTML = subtitleText;

        renderDashboardTable("dash_current_table", dashboardTableConfigs.current, stats);
        renderDashboardTable("dash_battery_table", dashboardTableConfigs.battery, stats);
        renderDashboardTable("dash_solar_table", dashboardTableConfigs.solar, stats);
        renderDashboardTable("dash_device_table", dashboardTableConfigs.device, stats);
        if (typeof updateInfoGraphic === "function")
            updateInfoGraphic(stats);
        initDashboardTooltips();
        const graphRecordedAt = normalizeRecordedAtKey(stats["recorded_at"]);
        if (graphRecordedAt != null && graphRecordedAt !== gLastDashboardGraphRecordedAt)
            updateRealTimeGraph(false, graphRecordedAt);
    }).catch(() => {
        gLastDashboardRenderSignature = null;
        gTelemetryConnectionHealthy = false;
        gDashboardHasLoadedOnce = true;
        setDashboardInitialLoadingState(false);
        renderTelemetryStatus();
        document.getElementById("dashboard_subtitle_time").innerHTML = getGenericString("unavailable");
        ["dash_current_table", "dash_battery_table", "dash_solar_table", "dash_device_table"].forEach(id => {
            const container = document.getElementById(id);
            if (container != null)
                container.innerHTML = '<div class="small text-secondary">' + escapeHtml(getDashboardInfoString("no_direct_values")) + '</div>';
        });
        if (typeof updateInfoGraphic === "function")
            updateInfoGraphic(null);
    }).finally(() => {
        gDashboardStatsRefreshInFlight = false;
    });
}

// Called cyclically to update the time
function updateTime() {
    renderTelemetryStatus();
}

// Async function to get the current stats
async function fetchDashboardOverviewJSON() {
    if (gDashboardOverviewRequest != null)
        return gDashboardOverviewRequest;

    gDashboardOverviewRequest = fetch(gBaseUrl + 'api/live')
        .then(response => response.json())
        .finally(() => {
            gDashboardOverviewRequest = null;
        });

    return gDashboardOverviewRequest;
}

// Called cyclically to update the current stats
function updateRealTimeGraph(forceRefresh = false, sourceRecordedAt = null) {
    if (!gDashboardVisible || document.hidden) return;
    if (gDashboardGraphRefreshInFlight)
        return;
    if (typeof isDashboardChartInteractionActive === "function" && isDashboardChartInteractionActive())
        return;
    if (!forceRefresh && (Date.now() - gLastDashboardGraphRefreshAt) < DASHBOARD_GRAPH_REFRESH_THROTTLE_MS)
        return;

    if (!forceRefresh) {
        const currentRecordedAt = sourceRecordedAt || normalizeRecordedAtKey(gLastTelemetryRecordedAt);
        if (currentRecordedAt != null && currentRecordedAt === gLastDashboardGraphRecordedAt)
            return;
        sourceRecordedAt = currentRecordedAt;
    }

    const shouldShowSkeleton = forceRefresh || !gDashboardGraphHasLoadedOnce;
    if (shouldShowSkeleton)
        setChartShellLoadingState(["dashboard_chart_shell"], true);

    gDashboardGraphRefreshInFlight = true;
    fetchRealTimeStatsJSON().then(stats => {
        createDashboardChart("chart_dashboard", stats);
        gLastDashboardGraphRefreshAt = Date.now();
        gDashboardGraphHasLoadedOnce = true;
        if (sourceRecordedAt != null)
            gLastDashboardGraphRecordedAt = sourceRecordedAt;
    }).finally(() => {
        if (shouldShowSkeleton)
            setChartShellLoadingState(["dashboard_chart_shell"], false);
        gDashboardGraphRefreshInFlight = false;
    });
}

// Async function to get the real time stats
async function fetchRealTimeStatsJSON() {
    async function fetchSeries(hours) {
        const response = await fetch(gBaseUrl + 'api/chart/live?hours=' + hours);
        if (!response.ok)
            return null;
        const payload = await response.json();
        return Array.isArray(payload?.series) ? payload.series : null;
    }

    let stats = await fetchSeries(gDahboardGraphTimespan);
    if (stats != null && stats.length > 0)
        return stats;

    stats = await fetchSeries(24);
    return stats || [];
}

function initSelectionBoxes() {
    if (gDateSelectorsInitialized)
        return;
    gDateSelectorsInitialized = true;

    // Days: numbers 1 to 31
    for (let i = 1; i <= 31; i++) {
        addSelectionItem("selection_day2", i.toString(), i.toString());
        addSelectionItem("csv_selection_day2", i.toString(), i.toString());
    }
}

function applyDateBoundsToSelectors(dates) {
    if (gDateBoundsLoaded)
        return;

    gDateBoundsLoaded = true;
    gMinDate = new Date(dates["year_min"] + "-01-01");
    for (let i = dates["year_min"]; i <= dates["year_max"]; i++) {
        addSelectionItem("selection_year2", i.toString(), i.toString());
        addSelectionItem("csv_selection_year2", i.toString(), i.toString());
    }
    selectDate(new Date());
}

async function ensureDateBoundsLoaded() {
    if (gDateBoundsLoaded)
        return;
    if (gDateBoundsRequest != null)
        return gDateBoundsRequest;

    gDateBoundsRequest = fetchDatesJSON()
        .then(dates => {
            applyDateBoundsToSelectors(dates);
            return dates;
        })
        .finally(() => {
            gDateBoundsRequest = null;
        });

    return gDateBoundsRequest;
}

function selectDate(date) {
    gCurDate = date;
    // Combo boxes 1
    document.getElementById('selection_year2').value = date.getFullYear();
    document.getElementById('selection_month2').value = date.getMonth() + 1;
    document.getElementById('selection_day2').value = date.getDate();
    // Combo boxes 2
    document.getElementById('csv_selection_year2').value = date.getFullYear();
    document.getElementById('csv_selection_month2').value = date.getMonth() + 1;
    document.getElementById('csv_selection_day2').value = date.getDate();
}

// Async function to get the important dates
async function fetchDatesJSON() {
    const response = await fetch(gBaseUrl + 'api/date-bounds');
    const stats = await response.json();
    return stats;
}

function setViewBusyState(viewId, loading) {
    const view = document.getElementById(viewId);
    if (view == null)
        return;

    view.classList.toggle("is-loading", loading === true);
    view.setAttribute("aria-busy", loading === true ? "true" : "false");
}

function setViewStatus(elementId, state, message) {
    const element = document.getElementById(elementId);
    if (element == null)
        return;

    if (message == null || message === "") {
        element.textContent = "";
        element.removeAttribute("data-state");
        element.classList.remove("visually-hidden");
        setElementVisible(elementId, false);
        return;
    }

    element.textContent = message;
    element.setAttribute("data-state", state || "info");
    element.classList.toggle("visually-hidden", state === "loading");
    setElementVisible(elementId, true);
}

function setHistoryAlertMessage(message) {
    const element = document.getElementById("info_no_data");
    if (element != null)
        element.textContent = message;
}

function shouldFetchHistoryDetails(updateDetails) {
    return (
        updateDetails
        && (gCurHistory == histories.MONTH || gCurHistory == histories.YEAR || gCurHistory == histories.ALL)
    );
}

function renderHistoryDetailsGraphs(items) {
    createHistoryDetailsChartProduction("chart_history_details_production", items);
    createHistoryDetailsChartConsumption("chart_history_details_consumption", items);
}

function setStatisticsUnavailable() {
    const unavailable = getGenericString("unavailable");
    [
        "stats_highest_prod_value",
        "stats_highest_prod_date",
        "stats_best_day_value",
        "stats_best_day_date",
        "stats_best_month_value",
        "stats_best_month_date",
        "stats_best_year_value",
        "stats_best_year_date",
        "statistics_value_avg_daily_prod",
        "statistics_value_start_date",
        "statistics_value_runtime",
    ].forEach(id => {
        const element = document.getElementById(id);
        if (element != null)
            element.textContent = unavailable;
    });
}


// Called cyclically to update the current stats
function updateHistoryStats(options = {}) {
    const liveRefresh = options.liveRefresh === true;
    const updateCharts = options.updateCharts !== false;
    const updateHighRes = options.updateHighRes !== false;
    const updateDetails = options.updateDetails !== false;

    if (liveRefresh && (gActiveInfoBadge != null || gInfoTooltipShowTimer != null))
        return;

    if (!liveRefresh)
        hideFloatingInfoTooltip(true);

    // Store data
    let year = document.getElementById('selection_year2').value.toString();
    let month = document.getElementById('selection_month2').value.toString();
    let day = document.getElementById('selection_day2').value.toString();
    gCurDate = new Date(year + "-" + month + "-" + day);
    if (!liveRefresh)
        persistCurrentViewState();
    const historySelectionKey = getCurrentHistorySelectionKey();
    const requestToken = ++gHistoryRequestToken;

    if (!liveRefresh) {
        setViewBusyState("view_history", true);
        setHistoryLoadingState(true);
        setViewStatus("history_status", "loading", getGenericString("loading_history"));
        setHistoryAlertMessage(getTextString("info_no_data"));
        setElementVisible("row_error_banner", false);
        setElementVisible("row_history_data", true);
    }

    const detailsPromise = shouldFetchHistoryDetails(updateDetails)
        ? fetchHistoryDetailsJSON()
        : Promise.resolve(null);

    const request = Promise.all([fetchHistoryStatsJSON(), detailsPromise])
        .then(([stats, details]) => {
            if (requestToken !== gHistoryRequestToken)
                return;

            if (stats["state"] != "ok") {
                if (liveRefresh)
                    return;

                gLastHistoryHighResSelectionKey = null;
                gLastHistoryHighResRaw = null;
                setViewStatus("history_status", "info", getTextString("info_no_data"));
                setElementVisible("row_error_banner", false);
                setElementVisible("row_history_data", false);
                if (updateHighRes)
                    setElementVisible("history_card_high_res", false);
                return;
            }

            gHistoryHasLoadedOnce = true;
            setElementVisible("row_error_banner", false);
            setElementVisible("row_history_data", true);
            if (updateHighRes)
                setElementVisible("history_card_high_res", true);

            document.getElementById("history_stat_produced").innerHTML = numFormat(stats["produced_kwh"], 2);

            const producedToHouseKwh = stats["produced_to_house_kwh"] ?? stats["usage_self_consumed_kwh"];
            const producedToBatteryKwh = stats["produced_to_battery_kwh"] ?? 0.0;
            const usageToHousePercent = stats["usage_to_house_percent"] ?? stats["usage_self_consumed_percent"];
            const usageToBatteryPercent = stats["usage_to_battery_percent"] ?? 0.0;
            const showFeedIn = parseFloat(stats["usage_fed_in_kwh"] || 0.0) > 0.0
                || parseFloat(stats["earned_feedin"] || 0.0) > 0.0;
            const feedInRow = document.getElementById("history_stat_fedin")?.closest("tr");
            const earnedFeedInRow = document.getElementById("history_stat_earned_feedin")?.closest("tr");

            document.getElementById("history_stat_self_consumed").innerHTML = numFormat(producedToHouseKwh, 2);
            document.getElementById("history_stat_battery_charge").innerHTML = numFormat(producedToBatteryKwh, 2);
            document.getElementById("history_stat_fedin").innerHTML = numFormat(stats["usage_fed_in_kwh"], 2);

            document.getElementById("history_stat_consumption_grid").innerHTML = numFormat(stats["consumed_from_grid_kwh"], 2);
            document.getElementById("history_stat_consumption_self").innerHTML = numFormat(stats["consumed_from_pv_kwh"], 2);
            document.getElementById("history_stat_consumption_battery").innerHTML = numFormat(stats["consumed_from_battery_kwh"], 2);
            document.getElementById("history_stat_consumption_total").innerHTML = numFormat(stats["consumed_total_kwh"], 2);

            document.getElementById("history_stat_earned_feedin").innerHTML = formatEarnedValue(stats["earned_feedin"]);
            document.getElementById("history_stat_earned_self").innerHTML = formatEarnedValue(stats["earned_savings"]);
            document.getElementById("history_stat_earned_total").innerHTML = formatEarnedValue(
                showFeedIn ? stats["earned_total"] : stats["earned_savings"]);

            if (feedInRow != null)
                feedInRow.style.display = showFeedIn ? "" : "none";
            if (earnedFeedInRow != null)
                earnedFeedInRow.style.display = showFeedIn ? "" : "none";

            document.getElementById("history_stat_autarky").innerHTML = numFormat(stats["autarky"], 0);

            if (updateCharts) {
                createConsumptionChart(
                    "chart_consumption",
                    parseFloat(stats["consumed_from_grid_percent"]),
                    parseFloat(stats["consumed_from_pv_percent"]),
                    parseFloat(stats["consumed_from_battery_percent"]));

                createUsageChart(
                    "chart_usage",
                    parseFloat(usageToHousePercent),
                    parseFloat(usageToBatteryPercent),
                    parseFloat(stats["usage_fed_in_percent"]));
            }

            if (updateHighRes) {
                if (stats["high_res"] != "") {
                    if (
                        gLastHistoryHighResSelectionKey !== historySelectionKey
                        || gLastHistoryHighResRaw !== stats["high_res"]
                    ) {
                        const data = JSON.parse(stats["high_res"]);
                        createHighResChart("chart_history_high_res", data);
                        gLastHistoryHighResSelectionKey = historySelectionKey;
                        gLastHistoryHighResRaw = stats["high_res"];
                    }
                    setElementVisible("history_card_high_res", true);
                } else {
                    gLastHistoryHighResSelectionKey = null;
                    gLastHistoryHighResRaw = null;
                    setElementVisible("history_card_high_res", false);
                }
            }

            if (details != null)
                renderHistoryDetailsGraphs(details);

            if (!liveRefresh)
                setViewStatus("history_status", null, "");
        })
        .catch(() => {
            if (requestToken !== gHistoryRequestToken || liveRefresh)
                return;

            gLastHistoryHighResSelectionKey = null;
            gLastHistoryHighResRaw = null;
            setViewStatus("history_status", "error", getGenericString("history_load_error"));
            setElementVisible("row_error_banner", false);
            setElementVisible("row_history_data", false);
            if (updateHighRes)
                setElementVisible("history_card_high_res", false);
        })
        .finally(() => {
            if (requestToken !== gHistoryRequestToken || liveRefresh)
                return;
            setHistoryLoadingState(false);
            setViewBusyState("view_history", false);
        });

    return request;
}


function formatEarnedValue(value) {
    const numericValue = Number(value);
    if (!Number.isFinite(numericValue))
        return numFormat(value, 5);
    return numFormat(numericValue, 5);
}


function isHistoryViewVisible() {
    const view = document.getElementById("view_history");
    return view != null && view.style.display != "none";
}


function isCurrentHistorySelectionLive() {
    const year = document.getElementById('selection_year2')?.value?.toString();
    const month = padStr(document.getElementById('selection_month2')?.value?.toString() || "");
    const day = padStr(document.getElementById('selection_day2')?.value?.toString() || "");

    if (!year)
        return false;

    const now = new Date();
    const nowYear = now.getFullYear().toString();
    const nowMonth = padStr((now.getMonth() + 1).toString());
    const nowDay = padStr(now.getDate().toString());

    switch (gCurHistory) {
        case histories.TODAY:
            return true;
        case histories.DAY:
            return year == nowYear && month == nowMonth && day == nowDay;
        case histories.MONTH:
            return year == nowYear && month == nowMonth;
        case histories.YEAR:
            return year == nowYear;
        case histories.ALL:
            return true;
        default:
            return false;
    }
}


function refreshLiveHistoryStats() {
    if (document.hidden)
        return;
    if (!gAppInitialized || !isHistoryViewVisible() || !isCurrentHistorySelectionLive())
        return;
    if (document.getElementById("view_history")?.classList.contains("is-loading"))
        return;
    if (gHistoryLiveRefreshInFlight)
        return;
    if ((Date.now() - gLastHistoryLiveRefreshAt) < HISTORY_LIVE_REFRESH_THROTTLE_MS)
        return;

    const preserveChartHover = typeof isHistoryChartInteractionActive === "function"
        && isHistoryChartInteractionActive();

    gHistoryLiveRefreshInFlight = true;
    const request = updateHistoryStats({
        liveRefresh: true,
        updateCharts: !preserveChartHover,
        updateHighRes: !preserveChartHover,
        updateDetails: !preserveChartHover,
    });
    if (request != null && typeof request.finally === "function") {
        request.finally(() => {
            gLastHistoryLiveRefreshAt = Date.now();
            gHistoryLiveRefreshInFlight = false;
        });
    } else {
        gLastHistoryLiveRefreshAt = Date.now();
        gHistoryLiveRefreshInFlight = false;
    }
}

// Async function to get the current stats
async function fetchHistoryStatsJSON() {
    let query = "api/period?bucket=";
    switch (gCurHistory) {
        case histories.TODAY:
        case histories.DAY:
            query += "day&date=";
            query += document.getElementById('selection_year2').value.toString();
            query += "-";
            query += padStr(document.getElementById('selection_month2').value.toString());
            query += "-";
            query += padStr(document.getElementById('selection_day2').value.toString());
            break;
        case histories.MONTH:
            query += "month&date=";
            query += document.getElementById('selection_year2').value.toString();
            query += "-";
            query += padStr(document.getElementById('selection_month2').value.toString());
            break;
        case histories.YEAR:
            query += "year&date=";
            query += document.getElementById('selection_year2').value.toString();
            break;
        case histories.ALL:
            query += "all";
            break;
    }
    const response = await fetch(gBaseUrl + query);
    if (!response.ok)
        throw new Error("Could not load history period");
    const stats = await response.json();
    return stats;
}

// Async function to get the current stats
async function fetchHistoryDetailsJSON() {
    let query = "api/breakdown?bucket=";
    switch (gCurHistory) {
        case histories.MONTH:
            query += "day&prefix=";
            query += document.getElementById('selection_year2').value.toString();
            query += "-";
            query += padStr(document.getElementById('selection_month2').value.toString());
            break;
        case histories.YEAR:
            query += "month&prefix=";
            query += document.getElementById('selection_year2').value.toString();
            break;
        case histories.ALL:
            query += "year";
            break;
    }
    const response = await fetch(gBaseUrl + query);
    if (!response.ok)
        throw new Error("Could not load history details");
    const payload = await response.json();
    return Array.isArray(payload?.items) ? payload.items : [];
}

function updateStatistics() {
    const requestToken = ++gStatisticsRequestToken;
    setViewBusyState("view_statistics", true);
    setStatisticsLoadingState(true);
    setViewStatus("statistics_status", "loading", getGenericString("loading_statistics"));

    fetchStatisticsJSON()
        .then(stats => {
            if (requestToken !== gStatisticsRequestToken)
                return;
            if (stats["state"] != "ok")
                throw new Error("Statistics are unavailable");

            document.getElementById("stats_highest_prod_value").innerHTML = numFormat(stats["highest_production_w"], 0) + " W";
            document.getElementById("stats_highest_prod_date").innerHTML = prettyPrintDateString(stats["highest_production_date"]);

            document.getElementById("stats_best_day_value").innerHTML = numFormat(stats["best_day_production_kwh"], 2) + " kWh";
            document.getElementById("stats_best_day_date").innerHTML = prettyPrintDateString(stats["best_day_date"]);

            document.getElementById("stats_best_month_value").innerHTML = numFormat(stats["best_month_production_kwh"], 2) + " kWh";
            document.getElementById("stats_best_month_date").innerHTML = prettyPrintDateStringWithoutDay(stats["best_month_date"]);

            document.getElementById("stats_best_year_value").innerHTML = numFormat(stats["best_year_production_kwh"], 2) + " kWh";
            document.getElementById("stats_best_year_date").innerHTML = getStatsBestYearPrefix() + stats["best_year_date"];

            document.getElementById("statistics_value_avg_daily_prod").innerHTML = numFormat(stats["average_daily_production_kwh"], 2);

            document.getElementById("statistics_value_start_date").innerHTML = prettyPrintDateString(stats["start_of_operation"]);
            document.getElementById("statistics_value_runtime").innerHTML = stats["days_of_operation"] + " " + getUnitDays();

            gStatisticsHasLoadedOnce = true;
            setViewStatus("statistics_status", null, "");
        })
        .catch(() => {
            if (requestToken !== gStatisticsRequestToken)
                return;
            if (!gStatisticsHasLoadedOnce)
                setStatisticsUnavailable();
            setViewStatus("statistics_status", "error", getGenericString("statistics_load_error"));
        })
        .finally(() => {
            if (requestToken !== gStatisticsRequestToken)
                return;
            setStatisticsLoadingState(false);
            setViewBusyState("view_statistics", false);
        });
}

// Async function to get the statistics stats
async function fetchStatisticsJSON() {
    const response = await fetch(gBaseUrl + 'api/statistics');
    if (!response.ok)
        throw new Error("Could not load statistics");
    const stats = await response.json();
    return stats;
}

function refreshLocalizedContent() {
    updateTime();
    configureDashboardLayout();
    configureStaticInfoBadges();
    gLastDashboardRenderSignature = null;
    gLastHistoryHighResSelectionKey = null;
    gLastHistoryHighResRaw = null;

    if (typeof resetChartsForLanguageChange === "function")
        resetChartsForLanguageChange();

    if (gDashboardVisible) {
        updateCurrentStats();
        updateRealTimeGraph(true);
    }
    else if (document.getElementById("view_statistics").style.display != "none") {
        updateStatistics();
    }
    else if (document.getElementById("view_history").style.display != "none") {
        updateHistoryStats();
    }
    queueVisibleChartResize();
}



function showViewDashboard(options = {}) {
    setElementVisible("view_dashboard", true);
    setElementVisible("view_statistics", false);
    setElementVisible("view_history", false);
    setElementVisible("view_csv", false);
    setInfoGraphicEnabled(true);
    gCurrentView = "dashboard";
    gDashboardVisible = true;
    setActiveSidebarLink("dashboard");
    hideFloatingInfoTooltip(true);
    updateCurrentStats();
    if (options.persist !== false)
        persistCurrentViewState();
    queueVisibleChartResize();
}

function showViewStatistics(options = {}) {
    setElementVisible("view_dashboard", false);
    setElementVisible("view_statistics", true);
    setElementVisible("view_history", false);
    setElementVisible("view_csv", false);
    setInfoGraphicEnabled(false);
    gCurrentView = "statistics";
    gDashboardVisible = false;
    setActiveSidebarLink("statistics");
    hideFloatingInfoTooltip(true);
    updateStatistics();
    if (options.persist !== false)
        persistCurrentViewState();
    queueVisibleChartResize();
}

function showViewHistory(mode, options = {}) {
    setElementVisible("view_dashboard", false);
    setElementVisible("view_statistics", false);
    setElementVisible("view_history", true);
    setElementVisible("view_csv", false);
    setInfoGraphicEnabled(false);
    gCurrentView = "history";
    gDashboardVisible = false;
    gCurHistory = mode;

    const historyView = document.getElementById("view_history");
    const showHistoryToolbar = mode != histories.ALL;
    historyView.classList.toggle("history-no-toolbar", !showHistoryToolbar);
    setElementVisible("history_toolbar", showHistoryToolbar);

    switch (mode) {
        case histories.TODAY:
            document.getElementById("headline_history").innerHTML = getHistoryString("daily_data");
            setElementVisible("selection_prev", true);
            setElementVisible("selection_next", true);
            setElementVisible("selection_year", true);
            setElementVisible("selection_month", true);
            setElementVisible("selection_day", true);
            setElementVisible("history_card_graphs", false);
            setElementVisible("history_card_high_res", true);
            setActiveSidebarLink("today");
        case histories.DAY:
            document.getElementById("headline_history").innerHTML = getHistoryString("daily_data");
            setElementVisible("selection_prev", true);
            setElementVisible("selection_next", true);
            setElementVisible("selection_year", true);
            setElementVisible("selection_month", true);
            setElementVisible("selection_day", true);
            setElementVisible("history_card_graphs", false);
            setElementVisible("history_card_high_res", true);
            if (mode == histories.DAY)
                setActiveSidebarLink("day");
            break;
        case histories.MONTH:
            document.getElementById("headline_history").innerHTML = getHistoryString("monthly_data");
            setElementVisible("selection_prev", true);
            setElementVisible("selection_next", true);
            setElementVisible("selection_year", true);
            setElementVisible("selection_month", true);
            setElementVisible("selection_day", false);
            setElementVisible("history_card_high_res", false);
            // Show the days
            setElementVisible("history_card_graphs", true);
            setActiveSidebarLink("month");
            break;
        case histories.YEAR:
            document.getElementById("headline_history").innerHTML = getHistoryString("yearly_data");
            setElementVisible("selection_prev", true);
            setElementVisible("selection_next", true);
            setElementVisible("selection_year", true);
            setElementVisible("selection_month", false);
            setElementVisible("selection_day", false);
            setElementVisible("history_card_high_res", false);
            // Show the months
            setElementVisible("history_card_graphs", true);
            setActiveSidebarLink("year");
            break;
        case histories.ALL:
            document.getElementById("headline_history").innerHTML = getHistoryString("all_time_data");
            setElementVisible("selection_prev", false);
            setElementVisible("selection_next", false);
            setElementVisible("selection_year", false);
            setElementVisible("selection_month", false);
            setElementVisible("selection_day", false);
            setElementVisible("history_card_high_res", false);
            // Show the years
            setElementVisible("history_card_graphs", true);
            setActiveSidebarLink("all");
            break;
    }
    hideFloatingInfoTooltip(true);
    setViewBusyState("view_history", true);
    setHistoryLoadingState(true);
    setViewStatus("history_status", "loading", getGenericString("loading_history"));
    setElementVisible("row_history_data", true);
    setElementVisible("row_error_banner", false);
    ensureDateBoundsLoaded()
        .then(() => {
            if (gCurHistory !== mode || !isHistoryViewVisible())
                return;
            const nextDate = getHistoryDateForMode(mode, options.initialDate);
            if (nextDate != null)
                selectDate(nextDate);
            if (options.persist !== false)
                persistCurrentViewState();
            updateHistoryStats();
        })
        .catch(() => {
            if (gCurHistory !== mode || !isHistoryViewVisible())
                return;
            setHistoryLoadingState(false);
            setViewBusyState("view_history", false);
            setViewStatus("history_status", "error", getGenericString("history_load_error"));
        });
    queueVisibleChartResize();
}

function showViewCsv(options = {}) {
    setElementVisible("view_dashboard", false);
    setElementVisible("view_statistics", false);
    setElementVisible("view_history", false);
    setElementVisible("view_csv", true);
    setInfoGraphicEnabled(false);
    gCurrentView = "csv";
    gDashboardVisible = false;
    setActiveSidebarLink("csv");
    hideFloatingInfoTooltip(true);
    ensureDateBoundsLoaded().catch(() => { });
    if (options.persist !== false)
        persistCurrentViewState();
    queueVisibleChartResize();
}

function updateCsvDateSelector() {
    if (document.getElementById("csv_range_rad_day").checked == true) {
        setElementVisible("csv_selection_year", true);
        setElementVisible("csv_selection_month", true);
        setElementVisible("csv_selection_day", true);

        setElementEnabled("csv_res_rad_day", true);
        setElementEnabled("csv_res_rad_month", false);
        setElementEnabled("csv_res_rad_year", false);

        if (isElementChecked("csv_res_rad_month") || isElementChecked("csv_res_rad_year"))
            setElementChecked("csv_res_rad_day", true);
    }
    else if (document.getElementById("csv_range_rad_month").checked == true) {
        setElementVisible("csv_selection_year", true);
        setElementVisible("csv_selection_month", true);
        setElementVisible("csv_selection_day", false);

        setElementEnabled("csv_res_rad_day", true);
        setElementEnabled("csv_res_rad_month", false);
        setElementEnabled("csv_res_rad_year", false);

        if (isElementChecked("csv_res_rad_month") || isElementChecked("csv_res_rad_year"))
            setElementChecked("csv_res_rad_day", true);
    }
    else if (document.getElementById("csv_range_rad_year").checked == true) {
        setElementVisible("csv_selection_year", true);
        setElementVisible("csv_selection_month", false);
        setElementVisible("csv_selection_day", false);

        setElementEnabled("csv_res_rad_day", true);
        setElementEnabled("csv_res_rad_month", true);
        setElementEnabled("csv_res_rad_year", false);

        if (isElementChecked("csv_res_rad_year"))
            setElementChecked("csv_res_rad_month", true);
    }
    else {
        setElementVisible("csv_selection_year", false);
        setElementVisible("csv_selection_month", false);
        setElementVisible("csv_selection_day", false);

        setElementEnabled("csv_res_rad_day", true);
        setElementEnabled("csv_res_rad_month", true);
        setElementEnabled("csv_res_rad_year", true);
    }
}


function datePrev() {
    let date = new Date(gCurDate)
    if (gCurHistory == histories.DAY || gCurHistory == histories.TODAY) {
        date.setDate(date.getDate() - 1);
    }
    else if (gCurHistory == histories.MONTH) {
        date.setMonth(date.getMonth() - 1);
    }
    else if (gCurHistory == histories.YEAR) {
        date.setFullYear(date.getFullYear() - 1);
    }

    if (date < gMinDate) date = new Date(gMinDate);

    selectDate(date);
    updateHistoryStats();
}

function dateNext() {
    let date = new Date(gCurDate)
    if (gCurHistory == histories.DAY || gCurHistory == histories.TODAY) {
        date.setDate(date.getDate() + 1);
    }
    else if (gCurHistory == histories.MONTH) {
        date.setMonth(date.getMonth() + 1);
    }
    else if (gCurHistory == histories.YEAR) {
        date.setFullYear(date.getFullYear() + 1);
    }

    const maxDate = new Date()
    if (date > maxDate) date = new Date(maxDate);

    selectDate(date);
    updateHistoryStats();
}

function changeDashboardGraphTimeSpan(hours) {
    gDahboardGraphTimespan = hours;
    localStorage.setItem("dash_time_span", gDahboardGraphTimespan);
    updateDashboardTimeSpanButtons();
    updateRealTimeGraph(true);
}



function setElementVisible(name, visible) {
    const element = document.getElementById(name);
    if (element == null)
        return;

    if (visible) {
        element.style.display = element.dataset.defaultDisplay || "";
        return;
    }

    const computedDisplay = window.getComputedStyle(element).display;
    if (computedDisplay != "none")
        element.dataset.defaultDisplay = computedDisplay;
    element.style.display = "none";
}

function setElementEnabled(name, enabled) {
    if (enabled)
        document.getElementById(name).removeAttribute("disabled");
    else
        document.getElementById(name).setAttribute("disabled", "");
}

function isElementChecked(name) {
    return document.getElementById(name).checked;
}

function setElementChecked(name, checked) {
    document.getElementById(name).checked = checked;
}

function addSelectionItem(control, name, value) {
    const node = document.createElement("option");
    node.setAttribute("value", value);
    const textnode = document.createTextNode(name);
    node.appendChild(textnode);
    document.getElementById(control).appendChild(node);
}

function padStr(i) {
    return (i < 10) ? "0" + i : "" + i;
}
