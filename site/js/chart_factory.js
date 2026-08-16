// Chart IDs
let gChartConsumption = null
let gChartUsage = null
let gChartDashboard = null
let gChartHistoryDetailsProduced = null
let gChartHistoryDetailsConsumed = null
let gChartHistoryHighRes = null

function isChartInteractionActive(chart) {
    if (chart == null || chart.canvas == null)
        return false;

    if (typeof chart.canvas.matches === "function" && chart.canvas.matches(":hover"))
        return true;

    const activeElements = typeof chart.getActiveElements === "function"
        ? chart.getActiveElements()
        : [];
    if (Array.isArray(activeElements) && activeElements.length > 0)
        return true;

    const tooltipActiveElements = typeof chart.tooltip?.getActiveElements === "function"
        ? chart.tooltip.getActiveElements()
        : [];
    return Array.isArray(tooltipActiveElements) && tooltipActiveElements.length > 0;
}

function isDashboardChartInteractionActive() {
    return isChartInteractionActive(gChartDashboard);
}

function useTouchChartControls() {
    return typeof window !== "undefined"
        && typeof window.matchMedia === "function"
        && window.matchMedia("(max-width: 991.98px), (pointer: coarse)").matches;
}

function syncDashboardChartSeriesControls() {
    document.querySelectorAll("[data-dashboard-series]").forEach(button => {
        const datasetIndex = Number(button.dataset.dashboardSeries);
        const visible = gChartDashboard == null
            || typeof gChartDashboard.isDatasetVisible !== "function"
            || gChartDashboard.isDatasetVisible(datasetIndex);
        button.classList.toggle("is-active", visible);
        button.setAttribute("aria-pressed", visible ? "true" : "false");
    });
}

function applyDashboardChartResponsiveOptions(chart) {
    if (chart == null)
        return;

    const touchLayout = useTouchChartControls();
    chart.options.plugins.legend.display = !touchLayout;
    chart.options.plugins.zoom.zoom.wheel.enabled = !touchLayout;
    chart.options.plugins.zoom.zoom.pinch.enabled = !touchLayout;
    chart.options.plugins.zoom.pan.enabled = !touchLayout;
}

function toggleDashboardChartSeries(datasetIndex) {
    if (gChartDashboard == null || typeof gChartDashboard.setDatasetVisibility !== "function")
        return;

    const visible = gChartDashboard.isDatasetVisible(datasetIndex);
    gChartDashboard.setDatasetVisibility(datasetIndex, !visible);
    gChartDashboard.update("none");
    syncDashboardChartSeriesControls();
}

function getChartSeriesControlContainer(canvasId) {
    return document.querySelector('[data-chart-series-controls="' + canvasId + '"]');
}

function applyChartSeriesControlOptions(chart, canvasId) {
    if (chart == null)
        return;

    const touchLayout = useTouchChartControls();
    const hasExternalControls = getChartSeriesControlContainer(canvasId) != null;
    if (hasExternalControls)
        chart.options.plugins.legend.display = !touchLayout;

    if (canvasId === "chart_history_high_res") {
        chart.options.plugins.zoom.zoom.wheel.enabled = !touchLayout;
        chart.options.plugins.zoom.zoom.pinch.enabled = !touchLayout;
        chart.options.plugins.zoom.pan.enabled = !touchLayout;
    }
}

function syncChartSeriesControls(chart, canvasId) {
    const container = getChartSeriesControlContainer(canvasId);
    if (chart == null || container == null)
        return;

    const generateLabels = chart.options.plugins.legend.labels.generateLabels;
    const legendItems = typeof generateLabels === "function" ? generateLabels(chart) : [];
    container.replaceChildren();

    legendItems.forEach(item => {
        const isDoughnut = chart.config.type === "doughnut" || chart.config.type === "pie";
        const seriesColor = isDoughnut
            ? item.fillStyle
            : (item.strokeStyle || item.fillStyle);
        const button = document.createElement("button");
        button.type = "button";
        button.className = "chart-series-control-button" + (item.hidden ? "" : " is-active");
        button.setAttribute("aria-pressed", item.hidden ? "false" : "true");
        button.style.setProperty(
            "--dashboard-series-color",
            String(seriesColor || COLOR_CHART_TEXT)
        );

        const dot = document.createElement("span");
        dot.className = "dashboard-chart-series-dot";
        dot.setAttribute("aria-hidden", "true");
        const label = document.createElement("span");
        label.textContent = item.text;
        button.append(dot, label);

        button.addEventListener("click", () => {
            if (isDoughnut)
                chart.toggleDataVisibility(item.index);
            else
                chart.setDatasetVisibility(item.datasetIndex, !chart.isDatasetVisible(item.datasetIndex));
            chart.update("none");
            syncChartSeriesControls(chart, canvasId);
        });
        container.appendChild(button);
    });
}

function isHistoryChartInteractionActive() {
    return [
        gChartConsumption,
        gChartUsage,
        gChartHistoryDetailsProduced,
        gChartHistoryDetailsConsumed,
        gChartHistoryHighRes,
    ].some(isChartInteractionActive);
}

if (typeof Chart !== "undefined") {
    Chart.defaults.color = "rgba(23, 19, 16, 0.72)";
    Chart.defaults.borderColor = "rgba(23, 19, 16, 0.08)";
    Chart.defaults.font.family = '"SF Pro Display", "SF Pro Text", "Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif';
    Chart.defaults.animation = false;
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    Chart.defaults.plugins.legend.labels.boxWidth = 8;
    Chart.defaults.plugins.legend.labels.boxHeight = 8;
}

function resetChartsForLanguageChange() {
    if (gChartConsumption != null) {
        gChartConsumption.destroy();
        gChartConsumption = null;
    }
    if (gChartUsage != null) {
        gChartUsage.destroy();
        gChartUsage = null;
    }
    if (gChartDashboard != null) {
        gChartDashboard.destroy();
        gChartDashboard = null;
    }
    if (gChartHistoryDetailsProduced != null) {
        gChartHistoryDetailsProduced.destroy();
        gChartHistoryDetailsProduced = null;
    }
    if (gChartHistoryDetailsConsumed != null) {
        gChartHistoryDetailsConsumed.destroy();
        gChartHistoryDetailsConsumed = null;
    }
    if (gChartHistoryHighRes != null) {
        gChartHistoryHighRes.destroy();
        gChartHistoryHighRes = null;
    }
}

function resizeVisibleCharts() {
    const chartEntries = [
        { chart: gChartConsumption, canvasId: "chart_consumption" },
        { chart: gChartUsage, canvasId: "chart_usage" },
        { chart: gChartDashboard, canvasId: "chart_dashboard" },
        { chart: gChartHistoryDetailsProduced, canvasId: "chart_history_details_production" },
        { chart: gChartHistoryDetailsConsumed, canvasId: "chart_history_details_consumption" },
        { chart: gChartHistoryHighRes, canvasId: "chart_history_high_res" },
    ];

    chartEntries.forEach(entry => {
        const canvas = document.getElementById(entry.canvasId);
        if (entry.chart == null || canvas == null || canvas.offsetParent == null)
            return;
        if (entry.chart === gChartDashboard) {
            entry.chart.options.scales.x = buildDashboardTimeScaleOptions(canvas.clientWidth);
            applyDashboardChartResponsiveOptions(entry.chart);
            syncDashboardChartSeriesControls();
        }
        else {
            applyChartSeriesControlOptions(entry.chart, entry.canvasId);
            syncChartSeriesControls(entry.chart, entry.canvasId);
        }
        if (entry.chart === gChartHistoryHighRes)
            entry.chart.options.scales.x = buildHistoryTimeScaleOptions(canvas.clientWidth);
        entry.chart.resize();
        entry.chart.update("none");
    });
}

// Colors
const FILL_OPACITY = "14";

function getAppColor(variableName, fallback) {
    if (typeof document === "undefined" || typeof getComputedStyle !== "function")
        return fallback;
    const value = getComputedStyle(document.documentElement).getPropertyValue(variableName).trim();
    return value || fallback;
}

const COLOR_FLOW_SOLAR = getAppColor("--app-flow-solar", "#ff7a00");
const COLOR_FLOW_GRID = getAppColor("--app-flow-grid", "#ef4444");
const COLOR_FLOW_BATTERY = getAppColor("--app-flow-battery", "#14b8a6");
const COLOR_FLOW_HOME = getAppColor("--app-flow-home", "#2563eb");
const COLOR_PRODUCTION_FED_IN = getAppColor("--app-flow-export", "#ef4444");
const COLOR_PRODUCTION_FED_IN_FILL = COLOR_PRODUCTION_FED_IN + FILL_OPACITY;

const COLOR_PRODUCTION_SELF_CONSUMED = COLOR_FLOW_HOME;
const COLOR_PRODUCTION_SELF_CONSUMED_FILL = COLOR_PRODUCTION_SELF_CONSUMED + FILL_OPACITY;
const COLOR_PRODUCTION_TO_BATTERY = COLOR_FLOW_BATTERY;

const COLOR_CONSUMED_FROM_GRID = COLOR_FLOW_GRID;
const COLOR_CONSUMED_FROM_GRID_FILL = COLOR_CONSUMED_FROM_GRID + FILL_OPACITY;

const COLOR_CONSUMED_FROM_PV = COLOR_FLOW_SOLAR;
const COLOR_CONSUMED_FROM_BATTERY = COLOR_FLOW_BATTERY;

const COLOR_PRODUCED = COLOR_FLOW_SOLAR;
const COLOR_CONSUMED = COLOR_FLOW_HOME;
const COLOR_CHART_TEXT = getAppColor("--app-text-soft", "#5a6169");
const COLOR_CHART_GRID = getAppColor("--app-border", "#e2e5e9");
const STACKED_BAR_STYLE = Object.freeze({
    borderRadius: 0,
    borderSkipped: false,
    maxBarThickness: 34,
});
const HISTORY_DETAILS_MIN_BAR_SLOTS = 10;

const STACKED_BAR_HOVER_LIFT_PLUGIN = {
    id: "stackedBarHoverLift",
    beforeDatasetsDraw(chart) {
        if (chart.config.type !== "bar")
            return;

        const lifted = [];
        const seen = new Set();
        chart.getActiveElements().forEach(active => {
            const element = active.element;
            if (element == null || seen.has(element))
                return;
            seen.add(element);
            lifted.push({ element: element, y: element.y, base: element.base });
            element.y -= 2;
            element.base -= 2;
        });
        chart.$stackedBarHoverLift = lifted;
    },
    afterDatasetsDraw(chart) {
        (chart.$stackedBarHoverLift || []).forEach(original => {
            original.element.y = original.y;
            original.element.base = original.base;
        });
        chart.$stackedBarHoverLift = [];
    },
};

if (typeof Chart !== "undefined")
    Chart.register(STACKED_BAR_HOVER_LIFT_PLUGIN);

function getChartHoverColor(color) {
    const match = /^#([0-9a-f]{6})$/i.exec(String(color));
    if (match == null)
        return color;

    const value = Number.parseInt(match[1], 16);
    const channels = [value >> 16, (value >> 8) & 0xff, value & 0xff];
    const lifted = channels.map(channel => Math.round(channel + (255 - channel) * 0.14));
    return `rgb(${lifted[0]}, ${lifted[1]}, ${lifted[2]})`;
}

function buildStackedBarStyle(color) {
    return {
        ...STACKED_BAR_STYLE,
        backgroundColor: color,
        borderColor: color,
        borderWidth: 0,
        hoverBackgroundColor: getChartHoverColor(color),
        hoverBorderColor: color,
        hoverBorderWidth: 0,
    };
}

function buildCartesianChartInteraction() {
    return {
        mode: "index",
        intersect: false,
        axis: "x",
    };
}

function buildRadialChartInteraction() {
    return {
        mode: "nearest",
        intersect: true,
    };
}

function centerHistoryDetailsBars(chartData) {
    let slotCount = Math.max(
        HISTORY_DETAILS_MIN_BAR_SLOTS,
        chartData.labels.length
    );
    if ((slotCount - chartData.labels.length) % 2 !== 0)
        slotCount += 1;

    const paddingSlots = (slotCount - chartData.labels.length) / 2;
    if (paddingSlots === 0)
        return;

    chartData.labels.unshift(...Array(paddingSlots).fill(""));
    chartData.labels.push(...Array(paddingSlots).fill(""));
    chartData.datasets.forEach(dataset => {
        dataset.data.unshift(...Array(paddingSlots).fill(null));
        dataset.data.push(...Array(paddingSlots).fill(null));
    });
}

function configureChartDefaults() {
    if (typeof Chart === "undefined" || Chart.defaults == null)
        return;

    Chart.defaults.color = COLOR_CHART_TEXT;
    Chart.defaults.borderColor = COLOR_CHART_GRID;
    Chart.defaults.font.family = getAppColor(
        "--app-font-sans",
        'Inter, "Segoe UI", "Helvetica Neue", Arial, sans-serif'
    );
    Chart.defaults.font.size = 11;

    const legendLabels = Chart.defaults.plugins?.legend?.labels;
    if (legendLabels != null) {
        legendLabels.usePointStyle = true;
        legendLabels.pointStyle = "circle";
        legendLabels.boxWidth = 7;
        legendLabels.boxHeight = 7;
        legendLabels.padding = 14;
        legendLabels.color = COLOR_CHART_TEXT;
    }

    const tooltip = Chart.defaults.plugins?.tooltip;
    if (tooltip != null) {
        tooltip.backgroundColor = "rgba(23, 25, 28, 0.94)";
        tooltip.cornerRadius = 6;
        tooltip.padding = 10;
        tooltip.displayColors = true;
        tooltip.boxPadding = 4;
        tooltip.animation = false;
        tooltip.caretPadding = 8;
        tooltip.titleSpacing = 4;
        tooltip.bodySpacing = 4;
    }
}

configureChartDefaults();


// Utility function to beautify the given date
function utilBeautifyDate(date) {
    if (date.length == 10) {
        // Must be a day
        let day = date.slice(8);
        return parseInt(day).toString() + ".";
    }
    else if (date.length == 7) {
        // Must be a month
        let month = date.slice(5);
        return getMonthName(parseInt(month) - 1);
    }
    else {
        // Must be a year
        return date;
    }
}

// Creates a chart showing the consumption distribution
function createConsumptionChart(canvasId, gridPercentage, pvPercentage, batteryPercentage) {
    const touchLayout = useTouchChartControls();
    var xValues = [
        getChartString("chart_from_pv"),
        getChartString("chart_from_battery"),
        getChartString("chart_from_grid"),
    ];
    var yValues = [pvPercentage, batteryPercentage, gridPercentage];
    var barColors = [
        COLOR_CONSUMED_FROM_PV,
        COLOR_CONSUMED_FROM_BATTERY,
        COLOR_CONSUMED_FROM_GRID,
    ];
    const chartConfig = {
        labels: xValues,
        datasets: [{
            backgroundColor: barColors,
            borderColor: "#ffffff",
            borderWidth: 2,
            hoverBackgroundColor: barColors,
            hoverBorderColor: "#ffffff",
            hoverBorderWidth: 2,
            hoverOffset: 4,
            spacing: 1,
            data: yValues
        }]
    };
    if (gChartConsumption == null) {
        gChartConsumption = new Chart(canvasId, {
            type: "doughnut",
            data: chartConfig,
            options: {
                animation: false,
                cutout: "70%",
                rotation: 180,
                maintainAspectRatio: false,
                resizeDelay: 0,
                interaction: buildRadialChartInteraction(),
                title: {
                    display: false
                },
                plugins: {
                    legend: {
                        display: !touchLayout,
                    },
                    labels: {
                        // render 'label', 'value', 'percentage', 'image' or custom function, default is 'percentage'
                        render: 'percentage',
                        fontSize: 16,
                        fontColor: '#ffffff',
                        textShadow: true
                    }
                }
            }
        });
        syncChartSeriesControls(gChartConsumption, canvasId);
        return;
    }

    gChartConsumption.data.labels = chartConfig.labels;
    gChartConsumption.data.datasets = chartConfig.datasets;
    gChartConsumption.options.locale = getLocale();
    applyChartSeriesControlOptions(gChartConsumption, canvasId);
    gChartConsumption.update("none");
    syncChartSeriesControls(gChartConsumption, canvasId);
}

// Creates a chart showing the power consumption distribution
function createUsageChart(canvasId, housePercentage, batteryPercentage, fedInPercentage) {
    const touchLayout = useTouchChartControls();
    if (fedInPercentage === null || fedInPercentage === undefined)
        fedInPercentage = 0.0;
    var xValues = [
        getChartString("chart_used_by_house"),
        getChartString("chart_to_battery"),
    ];
    var yValues = [housePercentage, batteryPercentage];
    var barColors = [
        COLOR_PRODUCTION_SELF_CONSUMED,
        COLOR_PRODUCTION_TO_BATTERY,
    ];
    if (fedInPercentage > 0.0) {
        xValues.push(getChartString("chart_fed_in"));
        yValues.push(fedInPercentage);
        barColors.push(COLOR_PRODUCTION_FED_IN);
    }
    const chartConfig = {
        labels: xValues,
        datasets: [{
            backgroundColor: barColors,
            borderColor: "#ffffff",
            borderWidth: 2,
            hoverBackgroundColor: barColors,
            hoverBorderColor: "#ffffff",
            hoverBorderWidth: 2,
            hoverOffset: 4,
            spacing: 1,
            data: yValues
        }]
    };
    if (gChartUsage != null && gChartUsage.data.datasets.length != chartConfig.datasets.length) {
        gChartUsage.destroy();
        gChartUsage = null;
    }

    if (gChartUsage == null) {
        gChartUsage = new Chart(canvasId, {
            type: "doughnut",
            data: chartConfig,
            options: {
                animation: false,
                cutout: "70%",
                rotation: 180,
                maintainAspectRatio: false,
                resizeDelay: 0,
                interaction: buildRadialChartInteraction(),
                title: {
                    display: false
                },
                plugins: {
                    legend: {
                        display: !touchLayout,
                    },
                    labels: {
                        // render 'label', 'value', 'percentage', 'image' or custom function, default is 'percentage'
                        render: 'percentage',
                        fontSize: 16,
                        fontColor: '#ffffff',
                        textShadow: true
                    }
                }
            }
        });
        syncChartSeriesControls(gChartUsage, canvasId);
        return;
    }

    gChartUsage.data.labels = chartConfig.labels;
    gChartUsage.data.datasets = chartConfig.datasets;
    gChartUsage.options.locale = getLocale();
    applyChartSeriesControlOptions(gChartUsage, canvasId);
    gChartUsage.update("none");
    syncChartSeriesControls(gChartUsage, canvasId);
}

function normalizePowerChartMax(value) {
    if (value <= 0.0)
        return 100.0;

    const padded = value * 1.12;
    let step = 100.0;

    if (padded <= 500.0)
        step = 50.0;
    else if (padded <= 2000.0)
        step = 100.0;
    else if (padded <= 5000.0)
        step = 200.0;
    else if (padded <= 10000.0)
        step = 500.0;
    else
        step = 1000.0;

    return Math.ceil(padded / step) * step;
}

function valueOrDefault(value, fallback) {
    if (value === null || value === undefined)
        return fallback;
    return value;
}

function formatTimeAxisLabel(label) {
    const text = String(label ?? "");
    const parts = text.split(":");
    if (parts.length >= 2)
        return parts[0] + ":" + parts[1];
    return text;
}

function buildAdaptiveTimeScaleOptions(canvasWidth, config = {}) {
    const width = Number(canvasWidth || 0);
    const maxVisibleTicks = Number(config.maxVisibleTicks || 0) > 0
        ? Number(config.maxVisibleTicks)
        : width >= 760 ? 10 : width >= 560 ? 8 : width >= 420 ? 6 : 5;
    const rotation = Number(config.rotation || 0);

    return {
        offset: false,
        ticks: {
            autoSkip: false,
            color: COLOR_CHART_TEXT,
            padding: width < 420 ? 10 : 8,
            maxRotation: rotation,
            minRotation: rotation,
            callback: function(value, index, ticks) {
                const label = formatTimeAxisLabel(
                    typeof this.getLabelForValue === "function" ? this.getLabelForValue(value) : value
                );
                if (!Array.isArray(ticks) || ticks.length <= maxVisibleTicks)
                    return label;

                const visibleSlots = Math.max(maxVisibleTicks - 1, 1);
                const step = Math.max(Math.ceil((ticks.length - 1) / visibleSlots), 1);
                return (index % step === 0 || index === ticks.length - 1) ? label : "";
            },
        },
        grid: {
            display: false,
        },
        border: {
            display: false,
        },
    };
}

function buildHistoryTimeScaleOptions(canvasWidth) {
    const width = Number(canvasWidth || 0);
    return buildAdaptiveTimeScaleOptions(width, {
        maxVisibleTicks: width >= 760 ? 10 : width >= 560 ? 8 : width >= 420 ? 6 : 5,
        rotation: width < 420 ? 52 : width < 768 ? 40 : 0,
    });
}

function buildDashboardTimeScaleOptions(canvasWidth) {
    const width = Number(canvasWidth || 0);
    return buildAdaptiveTimeScaleOptions(width, {
        maxVisibleTicks: width >= 960 ? 11 : width >= 760 ? 9 : width >= 560 ? 7 : width >= 420 ? 6 : 5,
        rotation: width < 420 ? 56 : width < 768 ? 48 : 36,
    });
}

function hasPositiveValueAtColumn(data, columnIndex) {
    for (let index = 0; index < data.length; index++) {
        if (Number(data[index][columnIndex] || 0) > 0.0)
            return true;
    }
    return false;
}

function hasPositiveValueAtKey(data, key) {
    for (let index = 0; index < data.length; index++) {
        if (Number(data[index][key] || 0) > 0.0)
            return true;
    }
    return false;
}

function buildLineDataset(label, options = {}) {
    return {
        label,
        data: [],
        fill: options.fill === true,
        hidden: options.hidden === true,
        borderColor: options.borderColor,
        backgroundColor: options.backgroundColor,
        borderWidth: options.borderWidth ?? 2,
        borderDash: options.borderDash || [],
        borderCapStyle: "round",
        borderJoinStyle: "round",
        pointRadius: 0,
        pointHoverRadius: 3,
        pointHitRadius: 12,
        spanGaps: false,
        tension: 0,
    };
}

function preserveChartDatasetVisibility(chart, datasets) {
    if (chart == null || typeof chart.isDatasetVisible !== "function")
        return datasets;

    const visibilityByLabel = new Map();
    chart.data.datasets.forEach((dataset, index) => {
        visibilityByLabel.set(dataset.label, chart.isDatasetVisible(index));
    });

    return datasets.map(dataset => ({
        ...dataset,
        hidden: visibilityByLabel.has(dataset.label)
            ? !visibilityByLabel.get(dataset.label)
            : Boolean(dataset.hidden),
    }));
}

function buildDashboardPowerChartData(data) {
    const labels = [];
    const datasets = [
        buildLineDataset(getChartString("chart_produced_w"), {
            fill: true,
            borderColor: COLOR_PRODUCED,
            backgroundColor: COLOR_PRODUCED + FILL_OPACITY,
        }),
        buildLineDataset(getChartString("chart_consumed_w"), {
            fill: true,
            borderColor: COLOR_CONSUMED,
            backgroundColor: COLOR_CONSUMED + FILL_OPACITY,
        }),
        buildLineDataset(getChartString("chart_from_battery"), {
            borderColor: COLOR_CONSUMED_FROM_BATTERY,
            backgroundColor: COLOR_CONSUMED_FROM_BATTERY,
            borderWidth: 1.6,
        }),
        buildLineDataset(getChartString("chart_from_grid"), {
            borderColor: COLOR_CONSUMED_FROM_GRID,
            backgroundColor: COLOR_CONSUMED_FROM_GRID,
            borderWidth: 1.6,
        }),
    ];

    let max = 0.0;
    for (index = data.length - 1; index >= 0; index--) {
        labels.push(data[index][1]);
        const values = [data[index][2], data[index][3], data[index][4], data[index][5]];
        for (i = 0; i < values.length; ++i) {
            let value = Number(values[i] || 0) * 1000.0;
            datasets[i].data.push(value);
            if (value > max) max = value;
        }
    }
    return {
        chartData: {
            labels: labels,
            datasets: datasets,
        },
        max: normalizePowerChartMax(max),
    };
}

// Creates a chart for the dashboard view
function createDashboardChart(canvasId, data) {
    const canvas = document.getElementById(canvasId);
    const xScaleOptions = buildDashboardTimeScaleOptions(canvas?.clientWidth || window.innerWidth);
    const chart_data = buildDashboardPowerChartData(data);
    const touchLayout = useTouchChartControls();

    if (gChartDashboard != null && gChartDashboard.data.datasets.length != chart_data.chartData.datasets.length) {
        gChartDashboard.destroy();
        gChartDashboard = null;
    }

    if (gChartDashboard == null) {
        gChartDashboard = new Chart(canvasId, {
            type: "line",
            responsive: true,
            data: chart_data.chartData,
            options: {
                animation: false,
                maintainAspectRatio: false,
                resizeDelay: 0,
                layout: {
                    padding: {
                        bottom: 12,
                    },
                },
                title: {
                    display: false
                },
                elements: {
                    line: {
                        borderJoinStyle: "round"
                    },
                    point: {
                        radius: 0
                    }
                },
                interaction: buildCartesianChartInteraction(),
                scales: {
                    x: xScaleOptions,
                    y: {
                        min: 0.0,
                        max: chart_data.max,
                        border: {
                            display: false,
                        },
                        grid: {
                            color: COLOR_CHART_GRID,
                        },
                        ticks: {
                            color: COLOR_CHART_TEXT,
                            padding: 8,
                        },
                        title: {
                            display: true,
                            color: COLOR_CHART_TEXT,
                            text: 'Watt'
                        }
                    }
                },
                locale: getLocale(),
                plugins: {
                    legend: {
                        display: !touchLayout,
                    },
                    zoom: {
                        zoom: {
                            wheel: {
                                enabled: !touchLayout
                            },
                            pinch: {
                                enabled: !touchLayout
                            },
                            mode: 'x',
                        },
                        pan: {
                            enabled: !touchLayout,
                            mode: 'x',
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                var valueName = context.dataset.label;   
                                var value = Math.floor(context.parsed.y);
                                return valueName + ": " + value + " W";
                            },
                        }
                    },
                }
            }
        });
        syncDashboardChartSeriesControls();
    }
    else {
        gChartDashboard.data.labels = chart_data.chartData.labels;
        gChartDashboard.data.datasets = preserveChartDatasetVisibility(
            gChartDashboard,
            chart_data.chartData.datasets,
        );
        gChartDashboard.options.scales.x = xScaleOptions;
        gChartDashboard.options.scales.y.max = chart_data.max;
        applyDashboardChartResponsiveOptions(gChartDashboard);
        gChartDashboard.update("none");
        syncDashboardChartSeriesControls();
    }
}

function buildHighResPowerChartData(data) {
    const labels = [];
    const datasets = [
        buildLineDataset(getChartString("chart_produced_w"), {
            fill: true,
            borderColor: COLOR_PRODUCED,
            backgroundColor: COLOR_PRODUCED + FILL_OPACITY,
        }),
        buildLineDataset(getChartString("chart_consumed_w"), {
            fill: true,
            borderColor: COLOR_CONSUMED,
            backgroundColor: COLOR_CONSUMED + FILL_OPACITY,
        }),
        buildLineDataset(getChartString("chart_from_battery"), {
            borderColor: COLOR_CONSUMED_FROM_BATTERY,
            backgroundColor: COLOR_CONSUMED_FROM_BATTERY,
            borderWidth: 1.6,
        }),
        buildLineDataset(getChartString("chart_from_grid"), {
            borderColor: COLOR_CONSUMED_FROM_GRID,
            backgroundColor: COLOR_CONSUMED_FROM_GRID,
            borderWidth: 1.6,
        }),
    ];

    let max = 0.0;
    for (index = 0; index < data.length; index++) {
        labels.push(data[index][0]);
        const values = [data[index][1], data[index][2], data[index][3], data[index][4]];
        for (i = 0; i < values.length; ++i) {
            let value = Number(values[i] || 0) * 1000.0;
            datasets[i].data.push(value);
            if (value > max) max = value;
        }
    }
    return {
        chartData: {
            labels: labels,
            datasets: datasets,
        },
        max: normalizePowerChartMax(max),
    };
}

// Creates a chart for the history daily/high res view
function createHighResChart(canvasId, data) {
    const canvas = document.getElementById(canvasId);
    const xScaleOptions = buildHistoryTimeScaleOptions(canvas?.clientWidth || window.innerWidth);
    const touchLayout = useTouchChartControls();

    const chart_data = buildHighResPowerChartData(data);

    if (gChartHistoryHighRes != null && gChartHistoryHighRes.data.datasets.length != chart_data.chartData.datasets.length) {
        gChartHistoryHighRes.destroy();
        gChartHistoryHighRes = null;
    }

    if (gChartHistoryHighRes == null) {
        gChartHistoryHighRes = new Chart(canvasId, {
            type: "line",
            responsive: true,
            data: chart_data.chartData,
            options: {
                animation: false,
                maintainAspectRatio: false,
                resizeDelay: 0,
                layout: {
                    padding: {
                        bottom: 10,
                    },
                },
                title: {
                    display: false
                },
                elements: {
                    line: {
                        borderJoinStyle: "round"
                    },
                    point: {
                        radius: 0
                    }
                },
                interaction: buildCartesianChartInteraction(),
                scales: {
                    x: xScaleOptions,
                    y: {
                        min: 0.0,
                        max: chart_data.max,
                        border: {
                            display: false,
                        },
                        grid: {
                            color: COLOR_CHART_GRID,
                        },
                        ticks: {
                            color: COLOR_CHART_TEXT,
                            padding: 8,
                        },
                        title: {
                            display: true,
                            color: COLOR_CHART_TEXT,
                            text: 'Watt'
                        }
                    }
                },
                locale: getLocale(),
                plugins: {
                    legend: {
                        display: !touchLayout,
                    },
                    decimation: {
                        enabled: false,
                        algorithm: 'min-max',
                    },
                    zoom: {
                        zoom: {
                            wheel: {
                                enabled: !touchLayout
                            },
                            pinch: {
                                enabled: !touchLayout
                            },
                            mode: 'x',
                        },
                        pan: {
                            enabled: !touchLayout,
                            mode: 'x',
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                var valueName = context.dataset.label;   
                                var value = Math.floor(context.parsed.y);
                                return valueName + ": " + value + " W";
                            },
                        }
                    },
                }
            }
        });
    }
    else {
        gChartHistoryHighRes.data.labels = chart_data.chartData.labels;
        gChartHistoryHighRes.data.datasets = preserveChartDatasetVisibility(
            gChartHistoryHighRes,
            chart_data.chartData.datasets,
        );
        gChartHistoryHighRes.options.scales.x = xScaleOptions;
        gChartHistoryHighRes.options.scales.y.max = chart_data.max;
        gChartHistoryHighRes.resize();
        gChartHistoryHighRes.update("none");
    }
    applyChartSeriesControlOptions(gChartHistoryHighRes, canvasId);
    syncChartSeriesControls(gChartHistoryHighRes, canvasId);
}

// Creates a chart showing history details
function createHistoryDetailsChartProduction(canvasId, data) {
    const touchLayout = useTouchChartControls();
    const labels = [];
    const showFeedIn = hasPositiveValueAtKey(data, "produced_feed_in");
    const chart_data = {
        labels: labels,
        datasets: [{
            label: getChartString("chart_produced_self_kwh"),
            data: [],
            ...buildStackedBarStyle(COLOR_PRODUCTION_SELF_CONSUMED),
            stack: 'Stack 0'
        },
        {
            label: getChartString("chart_produced_battery_kwh"),
            data: [],
            ...buildStackedBarStyle(COLOR_PRODUCTION_TO_BATTERY),
            stack: 'Stack 0'
        }]
    };
    if (showFeedIn) {
        chart_data.datasets.push({
            label: getChartString("chart_produced_grid_kwh"),
            data: [],
            ...buildStackedBarStyle(COLOR_PRODUCTION_FED_IN),
            stack: 'Stack 0'
        });
    }

    for (index = 0; index < data.length; index++) {
        labels.push(utilBeautifyDate(data[index]["date"])); // Element 1 = time
        chart_data.datasets[0].data.push(valueOrDefault(data[index]["produced_to_house"], data[index]["produced_self"]));
        chart_data.datasets[1].data.push(valueOrDefault(data[index]["produced_to_battery"], 0.0));
        if (showFeedIn)
            chart_data.datasets[2].data.push(data[index]["produced_feed_in"]);
    }

    centerHistoryDetailsBars(chart_data);

    if (gChartHistoryDetailsProduced == null) {
        gChartHistoryDetailsProduced = new Chart(canvasId, {
            type: "bar",
            responsive: true,
            data: chart_data,
            options: {
                animation: false,
                maintainAspectRatio: false,
                resizeDelay: 0,
                title: {
                    display: false
                },
                plugins: {
                    legend: {
                        display: !touchLayout,
                    },
                    labels: false,
                    tooltip: {
                        callbacks: {
                            afterTitle: function() {
                                window.total = 0;
                            },
                            label: function(context) {
                                var valueName = context.dataset.label;
                                var value = Number(context.parsed.y || 0);
                                window.total += value;
                                return valueName + ": " + numFormat(value, 2) + " kWh";
                            },
                            footer: function() {
                                return getChartString("chart_total") + ": " + numFormat(window.total, 2) + " kWh";
                            }
                        }
                    },
                },
                tooltips: {
                    enabled: true,
                    mode: 'label'
                },
                interaction: buildCartesianChartInteraction(),
                locale: getLocale(),
                scales: {
                    x: {
                        stacked: true,
                        border: {
                            display: false,
                        },
                        grid: {
                            display: false,
                        },
                        ticks: {
                            color: COLOR_CHART_TEXT,
                        },
                    },
                    y: {
                        stacked: true,
                        border: {
                            display: false,
                        },
                        grid: {
                            color: COLOR_CHART_GRID,
                        },
                        ticks: {
                            color: COLOR_CHART_TEXT,
                            padding: 8,
                        },
                        title: {
                            display: true,
                            color: COLOR_CHART_TEXT,
                            text: 'kWh'
                        }
                    },
                }
            }
        });
        syncChartSeriesControls(gChartHistoryDetailsProduced, canvasId);
        return;
    }

    gChartHistoryDetailsProduced.data.labels = chart_data.labels;
    gChartHistoryDetailsProduced.data.datasets = chart_data.datasets;
    gChartHistoryDetailsProduced.options.locale = getLocale();
    applyChartSeriesControlOptions(gChartHistoryDetailsProduced, canvasId);
    gChartHistoryDetailsProduced.resize();
    gChartHistoryDetailsProduced.update("none");
    syncChartSeriesControls(gChartHistoryDetailsProduced, canvasId);
}

// Creates a chart showing history details
function createHistoryDetailsChartConsumption(canvasId, data) {
    const touchLayout = useTouchChartControls();

    const labels = [];
    const chart_data = {
        labels: labels,
        datasets: [{
            label: getChartString("chart_consumed_pv_kwh"),
            data: [],
            ...buildStackedBarStyle(COLOR_CONSUMED_FROM_PV),
            stack: 'Stack 0'
        },
        {
            label: getChartString("chart_consumed_battery_kwh"),
            data: [],
            ...buildStackedBarStyle(COLOR_CONSUMED_FROM_BATTERY),
            stack: 'Stack 0'
        },
        {
            label: getChartString("chart_consumed_grid_kwh"),
            data: [],
            ...buildStackedBarStyle(COLOR_CONSUMED_FROM_GRID),
            stack: 'Stack 0'
        }]
    };

    for (index = 0; index < data.length; index++) {
        labels.push(utilBeautifyDate(data[index]["date"])); // Element 1 = time
        chart_data.datasets[0].data.push(data[index]["consumed_from_pv"]);
        chart_data.datasets[1].data.push(data[index]["consumed_from_battery"]);
        chart_data.datasets[2].data.push(data[index]["consumed_from_grid"]);
    }

    centerHistoryDetailsBars(chart_data);

    if (gChartHistoryDetailsConsumed == null) {
        gChartHistoryDetailsConsumed = new Chart(canvasId, {
            type: "bar",
            responsive: true,
            data: chart_data,
            options: {
                animation: false,
                maintainAspectRatio: false,
                resizeDelay: 0,
                title: {
                    display: false
                },
                plugins: {
                    legend: {
                        display: !touchLayout,
                    },
                    labels: false,
                    tooltip: {
                        callbacks: {
                            afterTitle: function() {
                                window.total = 0;
                            },
                            label: function(context) {
                                var valueName = context.dataset.label;
                                var value = Number(context.parsed.y || 0);
                                window.total += value;
                                return valueName + ": " + numFormat(value, 2) + " kWh";
                            },
                            footer: function() {
                                return getChartString("chart_total") + ": " + numFormat(window.total, 2) + " kWh";
                            }
                        }
                    },
                },
                interaction: buildCartesianChartInteraction(),
                locale: getLocale(),
                scales: {
                    x: {
                        stacked: true,
                        border: {
                            display: false,
                        },
                        grid: {
                            display: false,
                        },
                        ticks: {
                            color: COLOR_CHART_TEXT,
                        },
                    },
                    y: {
                        stacked: true,
                        border: {
                            display: false,
                        },
                        grid: {
                            color: COLOR_CHART_GRID,
                        },
                        ticks: {
                            color: COLOR_CHART_TEXT,
                            padding: 8,
                        },
                        title: {
                            display: true,
                            color: COLOR_CHART_TEXT,
                            text: 'kWh'
                        }
                    }
                }
            }
        });
        syncChartSeriesControls(gChartHistoryDetailsConsumed, canvasId);
        return;
    }

    gChartHistoryDetailsConsumed.data.labels = chart_data.labels;
    gChartHistoryDetailsConsumed.data.datasets = chart_data.datasets;
    gChartHistoryDetailsConsumed.options.locale = getLocale();
    applyChartSeriesControlOptions(gChartHistoryDetailsConsumed, canvasId);
    gChartHistoryDetailsConsumed.resize();
    gChartHistoryDetailsConsumed.update("none");
    syncChartSeriesControls(gChartHistoryDetailsConsumed, canvasId);
}
