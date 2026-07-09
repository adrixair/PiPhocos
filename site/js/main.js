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
let gDateAvailability = null;

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
        { kind: "metric", key: "total_output_active_power_w", labelId: "metric_total_output_active_power", icon: "fas fa-layer-group", digits: 0, source: "QPGS0" },
        { kind: "metric", key: "total_ac_output_apparent_power_va", labelId: "metric_total_output_apparent_power", icon: "fas fa-gauge", digits: 0, source: "QPGS0" },
        { kind: "metric", key: "solar_to_house_power_w", labelId: "metric_solar_to_house", icon: "fas fa-house-signal", digits: 0, source: "derived" },
        { kind: "metric", key: "battery_to_house_power_w", labelId: "metric_battery_to_house", icon: "fas fa-battery-three-quarters", digits: 0, source: "derived" },
        { kind: "metric", key: "grid_to_house_power_w", labelId: "metric_grid_to_house", icon: "fas fa-plug-circle-bolt", digits: 0, source: "derived" },
    ],
    battery: [
        { kind: "metric", key: "battery_state_of_charge_percent", labelId: "metric_battery_soc", icon: "fas fa-battery-half", digits: 0, source: "QPGS0 / QPIGS" },
        { kind: "text", path: ["live", "battery_state"], labelId: "metric_battery_state", icon: "fas fa-heart-pulse", sourceKind: "decoded", source: "status bits" },
        { kind: "metric", key: "battery_voltage_v", labelId: "metric_battery_voltage", icon: "fas fa-bolt", digits: 2, source: "QPGS0 / QPIGS" },
        { kind: "metric", key: "battery_voltage_from_scc_v", labelId: "metric_battery_voltage_scc", icon: "fas fa-solar-panel", digits: 2, source: "QPIGS" },
        { kind: "metric", key: "battery_charge_current_a", labelId: "metric_battery_charge_current", icon: "fas fa-arrow-up", digits: 2, source: "QPGS0 / QPIGS" },
        { kind: "metric", key: "battery_discharge_current_a", labelId: "metric_battery_discharge_current", icon: "fas fa-arrow-down", digits: 2, source: "QPGS0 / QPIGS" },
        { kind: "metric", key: "battery_charge_power_w", labelId: "metric_battery_charge_power", icon: "fas fa-arrow-up-wide-short", digits: 0, source: "derived" },
        { kind: "metric", key: "battery_discharge_power_w", labelId: "metric_battery_discharge_power", icon: "fas fa-arrow-down-wide-short", digits: 0, source: "derived" },
        { kind: "metric", key: "total_charging_current_a", labelId: "metric_total_charging_current", icon: "fas fa-charging-station", digits: 2, source: "QPGS0 / QPIGS" },
    ],
    solar: [
        { kind: "metric", key: "pv_input_voltage_v", labelId: "metric_pv_voltage", icon: "fas fa-solar-panel", digits: 1, source: "QPGS0 / QPIGS" },
        { kind: "metric", key: "pv_input_current_a", labelId: "metric_pv_current", icon: "fas fa-sun", digits: 2, source: "QPGS0 / QPIGS" },
        { kind: "metric", key: "pv_power_w", labelId: "metric_pv_power", icon: "fas fa-solar-panel", digits: 0, source: "QPIGS" },
        { kind: "metric", key: "pv_charging_power_w", labelId: "metric_pv_charging_power", icon: "fas fa-battery-three-quarters", digits: 0, source: "QPIGS" },
        { kind: "metric", key: "solar_to_battery_power_w", labelId: "metric_solar_to_battery", icon: "fas fa-charging-station", digits: 0, source: "derived" },
        { kind: "metric", key: "solar_feed_to_grid_power_w", labelId: "metric_solar_feed_to_grid", icon: "fas fa-tower-broadcast", digits: 0, source: "QPIGS" },
        { kind: "metric", key: "grid_to_battery_power_w", labelId: "metric_grid_to_battery", icon: "fas fa-plug-circle-plus", digits: 0, source: "derived" },
        { kind: "boolean", path: ["health", "mppt_active"], labelId: "metric_mppt_active", icon: "fas fa-sun", sourceKind: "decoded", source: "status bits" },
        { kind: "boolean", path: ["health", "solar_charging_on"], labelId: "metric_solar_charging", icon: "fas fa-solar-panel", sourceKind: "decoded", source: "status bits" },
        { kind: "boolean", path: ["health", "ac_charging_on"], labelId: "metric_ac_charging", icon: "fas fa-plug-circle-bolt", sourceKind: "decoded", source: "status bits" },
        { kind: "metric", key: "bus_voltage_v", labelId: "metric_bus_voltage", icon: "fas fa-microchip", digits: 1, source: "QPIGS" },
        { kind: "metric", key: "inverter_temperature_c", labelId: "metric_inverter_temperature", icon: "fas fa-temperature-half", digits: 1, source: "QPIGS" },
    ],
    device: [
        { kind: "text", path: ["device", "protocol_id"], labelId: "metric_protocol_id", icon: "fas fa-code-branch", sourceKind: "raw", source: "QPI" },
        { kind: "text", path: ["device", "operation_mode"], labelId: "metric_operation_mode", icon: "fas fa-gear", sourceKind: "decoded", source: "QMOD" },
        { kind: "text", path: ["device", "other_units_connected"], labelId: "metric_other_units", icon: "fas fa-network-wired", sourceKind: "decoded", source: "QPGS0" },
        { kind: "text", path: ["device", "fault"], labelId: "metric_fault", icon: "fas fa-triangle-exclamation", sourceKind: "decoded", source: "QMOD / QPGS0" },
        { kind: "boolean", path: ["health", "ac_input_available"], labelId: "metric_ac_input_available", icon: "fas fa-plug-circle-check", sourceKind: "decoded", source: "status bits" },
        { kind: "boolean", path: ["health", "ac_output_on"], labelId: "metric_ac_output_on", icon: "fas fa-power-off", sourceKind: "decoded", source: "status bits" },
        { kind: "list", path: ["health", "active_warning_bits"], labelId: "metric_active_warnings", icon: "fas fa-circle-exclamation", sourceKind: "decoded", source: "QPIWS", showWhenEmpty: true },
        { kind: "text", path: ["health", "warning_bitmap"], labelId: "metric_warning_bitmap", icon: "fas fa-list-ol", sourceKind: "raw", source: "QPIWS" },
        { kind: "text", path: ["health", "flag_blob"], labelId: "metric_flag_blob", icon: "fas fa-flag", sourceKind: "raw", source: "QFLAG" },
        { kind: "text", path: ["live", "status_bits"], labelId: "metric_status_bits", icon: "fas fa-list-check", sourceKind: "raw", source: "status bits" },
    ],
    phocosParameters: [
        { kind: "text", path: ["settings", "battery_type"], labelId: "metric_battery_type", icon: "fas fa-car-battery", sourceKind: "decoded", source: "QPIRI" },
        { kind: "settingMetric", path: ["settings", "battery_rating_voltage_v"], labelId: "metric_battery_rating_voltage", icon: "fas fa-ruler-combined", digits: 1, unit: "V", source: "QPIRI" },
        { kind: "settingMetric", path: ["settings", "battery_bulk_voltage_v"], labelId: "metric_battery_bulk_voltage", icon: "fas fa-arrow-up", digits: 1, unit: "V", source: "QPIRI" },
        { kind: "settingMetric", path: ["settings", "battery_float_voltage_v"], labelId: "metric_battery_float_voltage", icon: "fas fa-water", digits: 1, unit: "V", source: "QPIRI" },
        { kind: "settingMetric", path: ["settings", "battery_recharge_voltage_v"], labelId: "metric_battery_recharge_voltage", icon: "fas fa-rotate", digits: 1, unit: "V", source: "QPIRI" },
        { kind: "settingMetric", path: ["settings", "battery_redischarge_voltage_v"], labelId: "metric_battery_redischarge_voltage", icon: "fas fa-repeat", digits: 1, unit: "V", source: "QPIRI" },
        { kind: "settingMetric", path: ["settings", "battery_redischarge_voltage_from_scc_v"], labelId: "metric_battery_redischarge_voltage_scc", icon: "fas fa-solar-panel", digits: 1, unit: "V", source: "QPIRI" },
        { kind: "settingMetric", path: ["settings", "battery_under_voltage_v"], labelId: "metric_battery_under_voltage", icon: "fas fa-triangle-exclamation", digits: 1, unit: "V", source: "QPIRI" },
        { kind: "settingMetric", path: ["settings", "max_charging_current_a"], labelId: "metric_max_charging_current", icon: "fas fa-charging-station", digits: 0, unit: "A", source: "QPIRI" },
        { kind: "settingMetric", path: ["settings", "max_ac_charging_current_a"], labelId: "metric_max_ac_charging_current", icon: "fas fa-plug-circle-bolt", digits: 0, unit: "A", source: "QPIRI" },
        { kind: "settingMetric", path: ["settings", "cv_charge_time_minutes"], labelId: "metric_cv_charge_time", icon: "fas fa-clock", digits: 0, unit: "min", source: "QPIRI" },
        { kind: "text", path: ["device", "battery_charger_source_priority"], labelId: "metric_battery_priority", icon: "fas fa-sliders", sourceKind: "decoded", source: "QPIRI" },
        { kind: "settingMetric", path: ["settings", "grid_rating_voltage_v"], labelId: "metric_grid_rating_voltage", icon: "fas fa-plug-circle-bolt", digits: 1, unit: "V", source: "QPIRI" },
        { kind: "settingMetric", path: ["settings", "grid_rating_current_a"], labelId: "metric_grid_rating_current", icon: "fas fa-bolt", digits: 1, unit: "A", source: "QPIRI" },
        { kind: "settingMetric", path: ["settings", "ac_output_rating_voltage_v"], labelId: "metric_output_rating_voltage", icon: "fas fa-bolt", digits: 1, unit: "V", source: "QPIRI" },
        { kind: "settingMetric", path: ["settings", "ac_output_rating_frequency_hz"], labelId: "metric_output_rating_frequency", icon: "fas fa-wave-square", digits: 1, unit: "Hz", source: "QPIRI" },
        { kind: "settingMetric", path: ["settings", "ac_output_rating_current_a"], labelId: "metric_rated_output_current", icon: "fas fa-bolt", digits: 1, unit: "A", source: "QPIRI" },
        { kind: "settingMetric", path: ["settings", "ac_output_rating_active_power_w"], labelId: "metric_rated_active_power", icon: "fas fa-certificate", digits: 0, unit: "W", source: "QPIRI" },
        { kind: "settingMetric", path: ["settings", "ac_output_rating_apparent_power_va"], labelId: "metric_rated_apparent_power", icon: "fas fa-certificate", digits: 0, unit: "VA", source: "QPIRI" },
        { kind: "text", path: ["device", "input_voltage_range"], labelId: "metric_input_voltage_range", icon: "fas fa-plug", sourceKind: "decoded", source: "QPIRI" },
        { kind: "text", path: ["device", "output_source_priority"], labelId: "metric_output_priority", icon: "fas fa-shuffle", sourceKind: "decoded", source: "QPIRI" },
        { kind: "settingMetric", path: ["settings", "max_parallel_units"], labelId: "metric_max_parallel_units", icon: "fas fa-network-wired", digits: 0, unit: "", source: "QPIRI" },
        { kind: "text", path: ["device", "machine_type"], labelId: "metric_machine_type", icon: "fas fa-microchip", sourceKind: "decoded", source: "QPIRI" },
        { kind: "text", path: ["device", "topology"], labelId: "metric_topology", icon: "fas fa-sitemap", sourceKind: "decoded", source: "QPIRI" },
        { kind: "text", path: ["settings", "output_mode"], labelId: "metric_ac_output_mode", icon: "fas fa-diagram-project", sourceKind: "decoded", source: "QPIRI" },
        { kind: "text", path: ["device", "pv_ok_condition"], labelId: "metric_pv_ok_condition", icon: "fas fa-circle-check", sourceKind: "decoded", source: "QPIRI" },
        { kind: "text", path: ["device", "pv_power_balance"], labelId: "metric_pv_power_balance", icon: "fas fa-scale-balanced", sourceKind: "decoded", source: "QPIRI" },
        { kind: "text", path: ["device", "country_code"], labelId: "metric_country_code", icon: "fas fa-map", sourceKind: "raw", source: "QPIGS" },
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
    { elementId: "history_text_bill_total", tooltipId: "bill_without_self_consumption_eur" },
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
let gHistoryAbortController = null;
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
    "history_stat_bill_total",
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
    dash_current_table: 12,
    dash_battery_table: 9,
    dash_solar_table: 12,
    dash_device_table: 12,
    dash_phocos_parameters_table: 28,
};
const DASHBOARD_TABLE_IDS = Object.keys(DASHBOARD_SKELETON_TABLE_ROWS);

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

function createSelectionDate(year, month = 1, day = 1) {
    return new Date(Number(year), Number(month) - 1, Number(day), 12, 0, 0, 0);
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
        stats?.["pricing"]?.["price_display"] || stats?.["pricing"]?.["tempo_display"] || "",
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
    gTelemetryConnectionHealthy = stats != null && stats["current_data_stale"] !== true;

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

function getInitialHistorySelectionKey(mode, initialDate = "") {
    if (mode === histories.ALL)
        return histories.ALL;

    const parsed = parseHistoryDateForViewState(initialDate, mode);
    if (parsed != null)
        return getPeriodKeyFromDate(mode, parsed);

    if (gCurDate instanceof Date && Number.isFinite(gCurDate.getTime()))
        return getPeriodKeyFromDate(mode, gCurDate);

    return null;
}

function buildDashboardRow(entry, payload) {
    if (entry.kind == "metric") {
        const metric = payload["live"]?.[entry.key];
        const isStaleZero = payload?.["current_data_stale"] === true && metric?.["semantics"] === "stale_zero";
        if (metric == null || metric["value"] == null || (metric["semantics"] != "exact" && !isStaleZero))
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
    if (entry.kind == "settingMetric") {
        if (rawValue == null || rawValue === "" || Number.isNaN(Number(rawValue)) || !Number.isFinite(Number(rawValue)))
            return null;
        const value = numFormat(Number(rawValue), entry.digits ?? 0);
        return {
            icon: entry.icon,
            label: getDashboardMetricString(entry.labelId),
            value,
            unit: entry.unit || "",
            tooltip: buildDashboardTooltip(entry, value + (entry.unit ? " " + entry.unit : "")),
        };
    }

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
            + '<td class="text-end dashboard-value-cell">' + escapeHtml(row.value) + '</td>'
            + '<td class="text-end dashboard-unit-cell text-secondary">' + escapeHtml(row.unit) + '</td>'
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

function setInfoBadgeContent(elementId, content) {
    const badge = document.getElementById(elementId)?.querySelector(".dashboard-info-badge");
    if (badge == null || content == null || content === "")
        return;
    badge.dataset.infoContent = content;
    if (gActiveInfoBadge === badge && gFloatingInfoTooltip?.classList.contains("is-visible"))
        gFloatingInfoTooltip.innerHTML = escapeHtml(content);
}

function formatTooltipEuro(value, digits = 2) {
    const numericValue = Number(value);
    if (!Number.isFinite(numericValue))
        return getGenericString("unavailable");
    return numFormat(numericValue, digits) + " €";
}

function updateBillingInfoBadges(stats, grossBillEstimate, finalBillEstimate) {
    const monthlySubscription = stats["bill_subscription_ttc_per_month"];
    const periodSubscription = stats["bill_subscription_eur"];
    const gridEnergy = stats["bill_variable_eur"];
    const monthlySubscriptionText = Number.isFinite(Number(monthlySubscription))
        ? formatTooltipEuro(monthlySubscription)
        : getGenericString("unavailable");
    const periodSubscriptionText = Number.isFinite(Number(periodSubscription))
        ? formatTooltipEuro(periodSubscription)
        : getGenericString("unavailable");
    const gridEnergyText = Number.isFinite(Number(gridEnergy))
        ? formatTooltipEuro(gridEnergy)
        : getGenericString("unavailable");

    setInfoBadgeContent(
        "history_text_bill_total",
        "Coût brut TTC si toute l'électricité consommée avait été achetée au réseau. Il inclut l'abonnement fixe au prix réel configuré : "
            + monthlySubscriptionText
            + "/mois TTC. Sur cette période : "
            + periodSubscriptionText
            + " d'abonnement fixe TTC."
    );
    setInfoBadgeContent(
        "history_text_earned_total",
        "Facture estimée TTC à payer : énergie réseau réellement achetée + abonnement fixe TTC proratisé. L'économie solaire n'est pas une remise EDF et ne réduit pas l'abonnement. Sur cette période : "
            + gridEnergyText
            + " d'énergie réseau + "
            + periodSubscriptionText
            + " d'abonnement fixe ("
            + monthlySubscriptionText
            + "/mois TTC) = "
            + formatTooltipEuro(finalBillEstimate)
            + "."
    );
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
            DASHBOARD_TABLE_IDS.forEach(id => {
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
        const priceDisplay = stats["pricing"]?.["price_display"] || stats["pricing"]?.["tempo_display"];
        if (priceDisplay)
            subtitleText += " | Tarif: " + priceDisplay;
        if (stats["current_data_stale"] === true)
            subtitleText += " | " + getGenericString("dashboard_stale_note");
        document.getElementById("dashboard_subtitle_time").textContent = subtitleText;

        renderDashboardTable("dash_current_table", dashboardTableConfigs.current, stats);
        renderDashboardTable("dash_battery_table", dashboardTableConfigs.battery, stats);
        renderDashboardTable("dash_solar_table", dashboardTableConfigs.solar, stats);
        renderDashboardTable("dash_device_table", dashboardTableConfigs.device, stats);
        renderDashboardTable("dash_phocos_parameters_table", dashboardTableConfigs.phocosParameters, stats);
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
        DASHBOARD_TABLE_IDS.forEach(id => {
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

    gDashboardOverviewRequest = fetch(gBaseUrl + 'api/overview?compact=1')
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
    if (Number(gDahboardGraphTimespan) === 24)
        return stats || [];

    stats = await fetchSeries(24);
    return stats || [];
}

function initSelectionBoxes() {
    if (gDateSelectorsInitialized)
        return;
    gDateSelectorsInitialized = true;
}

function normalizeDateAvailabilityPayload(dates) {
    const normalized = {
        day: {
            values: [],
            years: [],
            monthsByYear: {},
            daysByMonth: {},
            min: null,
            max: null,
        },
        month: {
            values: [],
            years: [],
            monthsByYear: {},
            min: null,
            max: null,
        },
        year: {
            values: [],
            min: null,
            max: null,
        },
    };

    const uniqueSortedStrings = values => Array.from(new Set(values.map(String))).sort();
    const uniqueSortedNumbers = values => Array.from(new Set(values.map(Number).filter(Number.isFinite))).sort((a, b) => a - b);

    const rawDayValues = Array.isArray(dates?.available_days?.values)
        ? dates.available_days.values.filter(value => /^\d{4}-\d{2}-\d{2}$/.test(String(value)))
        : [];
    normalized.day.values = uniqueSortedStrings(rawDayValues);

    normalized.day.values.forEach(dayValue => {
        const [yearText, monthText, dayText] = dayValue.split("-");
        if (normalized.day.monthsByYear[yearText] == null)
            normalized.day.monthsByYear[yearText] = [];
        normalized.day.monthsByYear[yearText].push(Number(monthText));

        const monthKey = yearText + "-" + monthText;
        if (normalized.day.daysByMonth[monthKey] == null)
            normalized.day.daysByMonth[monthKey] = [];
        normalized.day.daysByMonth[monthKey].push(Number(dayText));
    });

    Object.keys(normalized.day.monthsByYear).forEach(yearKey => {
        normalized.day.monthsByYear[yearKey] = uniqueSortedNumbers(normalized.day.monthsByYear[yearKey]);
    });
    Object.keys(normalized.day.daysByMonth).forEach(monthKey => {
        normalized.day.daysByMonth[monthKey] = uniqueSortedNumbers(normalized.day.daysByMonth[monthKey]);
    });
    normalized.day.years = uniqueSortedNumbers(
        Object.keys(normalized.day.monthsByYear).map(value => Number(value))
    );
    normalized.day.min = normalized.day.values[0] || null;
    normalized.day.max = normalized.day.values[normalized.day.values.length - 1] || null;

    const rawMonthValues = Array.isArray(dates?.available_months?.values)
        ? dates.available_months.values.filter(value => /^\d{4}-\d{2}$/.test(String(value)))
        : Array.from(new Set(normalized.day.values.map(value => value.slice(0, 7))));
    normalized.month.values = uniqueSortedStrings(rawMonthValues);
    normalized.month.values.forEach(monthValue => {
        const [yearText, monthText] = monthValue.split("-");
        if (normalized.month.monthsByYear[yearText] == null)
            normalized.month.monthsByYear[yearText] = [];
        normalized.month.monthsByYear[yearText].push(Number(monthText));
    });
    Object.keys(normalized.month.monthsByYear).forEach(yearKey => {
        normalized.month.monthsByYear[yearKey] = uniqueSortedNumbers(normalized.month.monthsByYear[yearKey]);
    });
    normalized.month.years = uniqueSortedNumbers(
        Object.keys(normalized.month.monthsByYear).map(value => Number(value))
    );
    normalized.month.min = normalized.month.values[0] || null;
    normalized.month.max = normalized.month.values[normalized.month.values.length - 1] || null;

    const rawYearValues = Array.isArray(dates?.available_years?.values)
        ? dates.available_years.values
        : normalized.month.years;
    normalized.year.values = uniqueSortedNumbers(rawYearValues);

    if (normalized.year.values.length === 0) {
        const yearMin = Number(dates?.year_min);
        const yearMax = Number(dates?.year_max);
        if (Number.isFinite(yearMin) && Number.isFinite(yearMax)) {
            for (let year = yearMin; year <= yearMax; year++)
                normalized.year.values.push(year);
        }
    }

    normalized.year.min = normalized.year.values[0] ?? null;
    normalized.year.max = normalized.year.values[normalized.year.values.length - 1] ?? null;
    return normalized;
}

function getDateAvailabilityForMode(mode) {
    switch (mode) {
        case histories.TODAY:
        case histories.DAY:
            return gDateAvailability?.day || null;
        case histories.MONTH:
            return gDateAvailability?.month || null;
        case histories.YEAR:
            return gDateAvailability?.year || null;
        default:
            return null;
    }
}

function getCsvRangeMode() {
    if (document.getElementById("csv_range_rad_day")?.checked === true)
        return histories.DAY;
    if (document.getElementById("csv_range_rad_month")?.checked === true)
        return histories.MONTH;
    if (document.getElementById("csv_range_rad_year")?.checked === true)
        return histories.YEAR;
    return histories.ALL;
}

function getSelectionControlId(prefix, name) {
    return prefix + "selection_" + name + "2";
}

function getSelectionValue(controlId) {
    const element = document.getElementById(controlId);
    return element?.value?.toString() || "";
}

function setSelectionOptions(controlId, options, selectedValue) {
    const select = document.getElementById(controlId);
    if (select == null)
        return;

    const normalizedSelectedValue = selectedValue == null ? "" : String(selectedValue);
    select.replaceChildren();

    options.forEach(option => {
        const node = document.createElement("option");
        node.value = String(option.value);
        node.textContent = String(option.label);
        select.appendChild(node);
    });

    if (options.length === 0) {
        select.value = "";
        select.setAttribute("disabled", "");
        return;
    }

    select.removeAttribute("disabled");
    const fallbackValue = String(options[0].value);
    const nextValue = options.some(option => String(option.value) === normalizedSelectedValue)
        ? normalizedSelectedValue
        : fallbackValue;
    select.value = nextValue;
}

function buildYearOptions(values) {
    return values.map(value => ({
        value: String(value),
        label: String(value),
    }));
}

function buildMonthOptions(values) {
    return values.map(value => ({
        value: String(value),
        label: getMonthName(Number(value) - 1),
    }));
}

function buildDayOptions(values) {
    return values.map(value => ({
        value: String(value),
        label: String(value),
    }));
}

function getPeriodKeyFromDate(mode, date) {
    if (!(date instanceof Date) || !Number.isFinite(date.getTime()))
        return null;

    const year = date.getFullYear();
    const month = padStr(date.getMonth() + 1);
    const day = padStr(date.getDate());

    switch (mode) {
        case histories.MONTH:
            return year + "-" + month;
        case histories.YEAR:
            return String(year);
        case histories.DAY:
        case histories.TODAY:
            return year + "-" + month + "-" + day;
        default:
            return null;
    }
}

function getPeriodKeyFromSelectors(mode, prefix = "") {
    if (mode === histories.ALL)
        return histories.ALL;

    const year = getSelectionValue(getSelectionControlId(prefix, "year"));
    const month = padStr(getSelectionValue(getSelectionControlId(prefix, "month")));
    const day = padStr(getSelectionValue(getSelectionControlId(prefix, "day")));

    if (!year)
        return null;

    switch (mode) {
        case histories.MONTH:
            return year + "-" + month;
        case histories.YEAR:
            return year;
        case histories.DAY:
        case histories.TODAY:
        default:
            return year + "-" + month + "-" + day;
    }
}

function resolveAvailableKey(values, desiredKey) {
    if (!Array.isArray(values) || values.length === 0)
        return null;

    if (desiredKey == null || desiredKey === "")
        return values[values.length - 1];

    const normalizedKey = String(desiredKey);
    if (values.includes(normalizedKey))
        return normalizedKey;

    if (normalizedKey <= values[0])
        return values[0];

    for (let i = values.length - 1; i >= 0; i--) {
        if (values[i] <= normalizedKey)
            return values[i];
    }

    return values[values.length - 1];
}

function parsePeriodKey(mode, key) {
    if (typeof key !== "string" || key === "")
        return null;

    if ((mode === histories.DAY || mode === histories.TODAY) && /^\d{4}-\d{2}-\d{2}$/.test(key)) {
        const [year, month, day] = key.split("-").map(Number);
        return { year, month, day };
    }

    if (mode === histories.MONTH && /^\d{4}-\d{2}$/.test(key)) {
        const [year, month] = key.split("-").map(Number);
        return { year, month, day: 1 };
    }

    if (mode === histories.YEAR && /^\d{4}$/.test(key))
        return { year: Number(key), month: 1, day: 1 };

    return null;
}

function applyPeriodKeyToSelectors(prefix, mode, desiredKey) {
    if (mode === histories.ALL)
        return histories.ALL;

    const availability = getDateAvailabilityForMode(mode);
    if (availability == null || !Array.isArray(availability.values) || availability.values.length === 0) {
        setSelectionOptions(getSelectionControlId(prefix, "year"), [], "");
        setSelectionOptions(getSelectionControlId(prefix, "month"), [], "");
        setSelectionOptions(getSelectionControlId(prefix, "day"), [], "");
        return null;
    }

    const resolvedKey = resolveAvailableKey(availability.values.map(String), desiredKey);
    const parts = parsePeriodKey(mode, String(resolvedKey));
    if (parts == null)
        return null;

    if (mode === histories.YEAR) {
        setSelectionOptions(
            getSelectionControlId(prefix, "year"),
            buildYearOptions(availability.values),
            parts.year
        );
        return resolvedKey;
    }

    setSelectionOptions(
        getSelectionControlId(prefix, "year"),
        buildYearOptions(availability.years || []),
        parts.year
    );

    const months = availability.monthsByYear?.[String(parts.year)] || [];
    setSelectionOptions(
        getSelectionControlId(prefix, "month"),
        buildMonthOptions(months),
        parts.month
    );

    if (mode === histories.MONTH)
        return resolvedKey;

    const monthKey = String(parts.year) + "-" + padStr(parts.month);
    const days = availability.daysByMonth?.[monthKey] || [];
    setSelectionOptions(
        getSelectionControlId(prefix, "day"),
        buildDayOptions(days),
        parts.day
    );
    return resolvedKey;
}

function updateHistoryNavigationState(currentKey = null) {
    const prevButton = document.getElementById("selection_prev");
    const nextButton = document.getElementById("selection_next");
    if (prevButton == null || nextButton == null)
        return;

    const availability = getDateAvailabilityForMode(gCurHistory);
    const values = Array.isArray(availability?.values) ? availability.values.map(String) : [];
    const resolvedKey = String(currentKey || getPeriodKeyFromSelectors(gCurHistory) || "");
    const index = values.indexOf(resolvedKey);
    const disableNavigation = values.length === 0 || index < 0;

    prevButton.disabled = disableNavigation || index === 0;
    nextButton.disabled = disableNavigation || index === values.length - 1;
}

function applyHistorySelectionKey(desiredKey) {
    const resolvedKey = applyPeriodKeyToSelectors("", gCurHistory, desiredKey);
    const parts = parsePeriodKey(gCurHistory, resolvedKey);

    if (parts != null)
        gCurDate = createSelectionDate(parts.year, parts.month, parts.day);

    updateHistoryNavigationState(resolvedKey);
    return resolvedKey;
}

function applyCsvSelectionKey(desiredKey) {
    const mode = getCsvRangeMode();
    if (mode === histories.ALL)
        return null;
    return applyPeriodKeyToSelectors("csv_", mode, desiredKey);
}

function applyDateBoundsToSelectors(dates) {
    if (gDateBoundsLoaded)
        return;

    gDateBoundsLoaded = true;
    gDateAvailability = normalizeDateAvailabilityPayload(dates);

    const latestDayKey = gDateAvailability?.day?.max || null;
    const latestDay = parsePeriodKey(histories.DAY, latestDayKey);
    if (latestDay != null)
        gCurDate = createSelectionDate(latestDay.year, latestDay.month, latestDay.day);

    applyHistorySelectionKey(getPeriodKeyFromDate(gCurHistory, gCurDate));
    updateCsvDateSelector();
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
    const includeHighRes = updateHighRes && !liveRefresh;

    if (liveRefresh && (gActiveInfoBadge != null || gInfoTooltipShowTimer != null))
        return;

    if (!liveRefresh)
        hideFloatingInfoTooltip(true);

    const currentPeriodKey = getPeriodKeyFromSelectors(gCurHistory);
    const currentPeriod = parsePeriodKey(gCurHistory, currentPeriodKey);
    if (currentPeriod != null)
        gCurDate = createSelectionDate(currentPeriod.year, currentPeriod.month, currentPeriod.day);

    if (!liveRefresh)
        persistCurrentViewState();
    const historySelectionKey = getCurrentHistorySelectionKey();
    const requestToken = ++gHistoryRequestToken;
    let abortController = null;
    if (!liveRefresh && typeof AbortController !== "undefined") {
        if (gHistoryAbortController != null)
            gHistoryAbortController.abort();
        gHistoryAbortController = new AbortController();
        abortController = gHistoryAbortController;
    }

    if (gCurHistory !== histories.ALL && currentPeriod == null) {
        if (!liveRefresh) {
            setHistoryLoadingState(false);
            setViewBusyState("view_history", false);
            setViewStatus("history_status", "info", getTextString("info_no_data"));
            setElementVisible("row_history_data", false);
            setElementVisible("row_error_banner", false);
        }
        return Promise.resolve();
    }

    if (!liveRefresh) {
        setViewBusyState("view_history", true);
        setHistoryLoadingState(true);
        setViewStatus("history_status", "loading", getGenericString("loading_history"));
        setHistoryAlertMessage(getTextString("info_no_data"));
        setElementVisible("row_error_banner", false);
        setElementVisible("row_history_data", true);
    }

    const detailsPromise = shouldFetchHistoryDetails(updateDetails)
        ? fetchHistoryDetailsJSON({ signal: abortController?.signal })
        : Promise.resolve(null);

    const request = Promise.all([
        fetchHistoryStatsJSON({
            includeHighRes,
            signal: abortController?.signal,
        }),
        detailsPromise,
    ])
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

            document.getElementById("history_stat_earned_feedin").innerHTML = formatReductionValue(stats["earned_feedin"]);
            document.getElementById("history_stat_earned_self").innerHTML = formatReductionValue(stats["earned_savings"]);
            const billTotal = stats["bill_estimated_total_eur"];
            const billNet = stats["bill_net_after_injection_eur"] ?? billTotal;
            const billWithoutSelfConsumption = stats["bill_without_self_consumption_eur"];
            const hasBillEstimate = Number.isFinite(parseFloat(billTotal));
            const hasGrossBillEstimate = Number.isFinite(parseFloat(billWithoutSelfConsumption));
            const grossBillEstimate = hasGrossBillEstimate
                ? billWithoutSelfConsumption
                : (hasBillEstimate
                    ? Number(billTotal) + Number(stats["earned_savings"] || 0.0)
                    : 0.0);
            document.getElementById("history_stat_bill_total").innerHTML = formatEarnedValue(
                grossBillEstimate);
            document.getElementById("history_stat_earned_total").innerHTML = formatEarnedValue(
                hasBillEstimate
                    ? billNet
                    : (showFeedIn ? stats["earned_total"] : stats["earned_savings"]));
            if (hasBillEstimate)
                updateBillingInfoBadges(stats, grossBillEstimate, billNet);

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
        .catch(error => {
            if (error?.name === "AbortError")
                return;
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
            if (abortController != null && gHistoryAbortController === abortController)
                gHistoryAbortController = null;
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

function formatReductionValue(value) {
    const numericValue = Number(value);
    if (!Number.isFinite(numericValue))
        return numFormat(value, 5);
    if (numericValue === 0)
        return numFormat(0, 5);
    return numFormat(-Math.abs(numericValue), 5);
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
        updateHighRes: false,
        updateDetails: false,
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
async function fetchHistoryStatsJSON(options = {}) {
    const includeHighRes = options.includeHighRes !== false;
    const signal = options.signal;
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
    if (!includeHighRes)
        query += "&include_high_res=0";
    const response = await fetch(gBaseUrl + query, { signal });
    if (!response.ok)
        throw new Error("Could not load history period");
    const stats = await response.json();
    return stats;
}

// Async function to get the current stats
async function fetchHistoryDetailsJSON(options = {}) {
    const signal = options.signal;
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
    const response = await fetch(gBaseUrl + query, { signal });
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

            document.getElementById("stats_highest_prod_value").textContent = numFormat(stats["highest_production_w"], 0) + " W";
            document.getElementById("stats_highest_prod_date").textContent = prettyPrintDateString(stats["highest_production_date"]);

            document.getElementById("stats_best_day_value").textContent = numFormat(stats["best_day_production_kwh"], 2) + " kWh";
            document.getElementById("stats_best_day_date").textContent = prettyPrintDateString(stats["best_day_date"]);

            document.getElementById("stats_best_month_value").textContent = numFormat(stats["best_month_production_kwh"], 2) + " kWh";
            document.getElementById("stats_best_month_date").textContent = prettyPrintDateStringWithoutDay(stats["best_month_date"]);

            document.getElementById("stats_best_year_value").textContent = numFormat(stats["best_year_production_kwh"], 2) + " kWh";
            document.getElementById("stats_best_year_date").textContent = getStatsBestYearPrefix() + stats["best_year_date"];

            document.getElementById("statistics_value_avg_daily_prod").textContent = numFormat(stats["average_daily_production_kwh"], 2);

            document.getElementById("statistics_value_start_date").textContent = prettyPrintDateString(stats["start_of_operation"]);
            document.getElementById("statistics_value_runtime").textContent = stats["days_of_operation"] + " " + getUnitDays();

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

    if (gDateBoundsLoaded) {
        if (gCurrentView === "history" && gCurHistory !== histories.ALL)
            applyHistorySelectionKey(getPeriodKeyFromSelectors(gCurHistory));
        updateCsvDateSelector();
    }

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
            const nextKey = getInitialHistorySelectionKey(mode, options.initialDate);
            const resolvedKey = applyHistorySelectionKey(nextKey);
            if (options.persist !== false)
                persistCurrentViewState();
            if (resolvedKey != null)
                updateHistoryStats();
            else {
                setHistoryLoadingState(false);
                setViewBusyState("view_history", false);
                setViewStatus("history_status", "info", getTextString("info_no_data"));
                setElementVisible("row_history_data", false);
            }
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

    if (gDateBoundsLoaded) {
        const mode = getCsvRangeMode();
        if (mode !== histories.ALL)
            applyCsvSelectionKey(getPeriodKeyFromSelectors(mode, "csv_"));
    }
}


function onHistorySelectorChange() {
    const resolvedKey = applyHistorySelectionKey(getPeriodKeyFromSelectors(gCurHistory));
    if (resolvedKey != null)
        updateHistoryStats();
}

function onCsvSelectorChange() {
    if (!gDateBoundsLoaded)
        return;
    const mode = getCsvRangeMode();
    if (mode === histories.ALL)
        return;
    applyCsvSelectionKey(getPeriodKeyFromSelectors(mode, "csv_"));
}

function datePrev() {
    const availability = getDateAvailabilityForMode(gCurHistory);
    const values = Array.isArray(availability?.values) ? availability.values.map(String) : [];
    const currentKey = String(getPeriodKeyFromSelectors(gCurHistory) || "");
    const currentIndex = values.indexOf(currentKey);
    if (currentIndex <= 0)
        return;

    applyHistorySelectionKey(values[currentIndex - 1]);
    updateHistoryStats();
}

function dateNext() {
    const availability = getDateAvailabilityForMode(gCurHistory);
    const values = Array.isArray(availability?.values) ? availability.values.map(String) : [];
    const currentKey = String(getPeriodKeyFromSelectors(gCurHistory) || "");
    const currentIndex = values.indexOf(currentKey);
    if (currentIndex < 0 || currentIndex >= values.length - 1)
        return;

    applyHistorySelectionKey(values[currentIndex + 1]);
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
