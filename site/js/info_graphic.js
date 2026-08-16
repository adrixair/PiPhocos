var gInfoGraphicEnabled = false;
let gInfoGraphicLabelLayoutFrame = null;
let gInfoGraphicResizeObserver = null;
let gInfoGraphicArrowAnimationFrame = null;
let gInfoGraphicArrowAnimationStartedAt = null;

const INFO_GRAPHIC_ACTIVE_THRESHOLD_W = 20;
const INFO_GRAPHIC_PLACEHOLDER = "--";
const INFO_GRAPHIC_ARROW_COUNT = 10;
const INFO_GRAPHIC_ARROW_DURATION_MS = 3200;
const INFO_GRAPHIC_LINK_NAMES = [
    "solar_hub",
    "grid_hub",
    "hub_grid_export",
    "hub_house",
    "hub_battery_charge",
    "battery_hub_discharge",
];
const INFO_GRAPHIC_LABEL_LAYOUT = {
    solar_hub: { anchor: 0.5, offsetX: 0, offsetY: 0 },
    grid_hub: { anchor: 0.5, offsetX: 0, offsetY: 0 },
    hub_grid_export: { anchor: 0.5, offsetX: 0, offsetY: 0 },
    hub_house: { anchor: 0.5, offsetX: 0, offsetY: 0 },
    hub_battery_charge: { anchor: 0.5, offsetX: 0, offsetY: 0 },
    battery_hub_discharge: { anchor: 0.5, offsetX: 0, offsetY: 0 },
};

function getInfoGraphicRoot() {
    return document.getElementById("dashboard_power_flow");
}

function hasInfoGraphic() {
    return getInfoGraphicRoot() != null;
}

function getInfoGraphicArrowColorClass(link) {
    if (link.classList.contains("power-flow-link-solar"))
        return "power-flow-arrow-stream-solar";
    if (link.classList.contains("power-flow-link-grid"))
        return "power-flow-arrow-stream-grid";
    if (link.classList.contains("power-flow-link-house"))
        return "power-flow-arrow-stream-house";
    return "power-flow-arrow-stream-battery";
}

function ensureInfoGraphicArrowStreams() {
    const root = getInfoGraphicRoot();
    const svg = root?.querySelector(".power-flow-svg");
    if (svg == null)
        return;

    const svgNamespace = "http://www.w3.org/2000/svg";

    INFO_GRAPHIC_LINK_NAMES.forEach(name => {
        const link = document.getElementById("flow_link_" + name);
        if (link == null || document.getElementById("flow_arrows_" + name) != null)
            return;

        const stream = document.createElementNS(svgNamespace, "g");
        stream.id = "flow_arrows_" + name;
        stream.setAttribute(
            "class",
            "power-flow-arrow-stream " + getInfoGraphicArrowColorClass(link)
        );

        for (let index = 0; index < INFO_GRAPHIC_ARROW_COUNT; index++) {
            const arrow = document.createElementNS(svgNamespace, "path");
            arrow.setAttribute("class", "power-flow-arrow");
            arrow.setAttribute("d", "M -4.5 -3 L 0.75 0 L -4.5 3");
            arrow.setAttribute("vector-effect", "non-scaling-stroke");
            arrow.dataset.flowPhase = (index / INFO_GRAPHIC_ARROW_COUNT).toFixed(3);
            arrow.setAttribute("visibility", "hidden");
            stream.appendChild(arrow);
        }

        svg.appendChild(stream);
    });
}

function getInfoGraphicArrowProgress(timestamp) {
    if (gInfoGraphicArrowAnimationStartedAt == null)
        gInfoGraphicArrowAnimationStartedAt = timestamp;
    return ((timestamp - gInfoGraphicArrowAnimationStartedAt) % INFO_GRAPHIC_ARROW_DURATION_MS)
        / INFO_GRAPHIC_ARROW_DURATION_MS;
}

function positionInfoGraphicArrowStream(name, progress) {
    const link = document.getElementById("flow_link_" + name);
    const stream = document.getElementById("flow_arrows_" + name);
    if (link == null || stream == null)
        return;

    const length = link.getTotalLength();
    if (!Number.isFinite(length) || length <= 0)
        return;

    const tangentOffset = Math.max(0.75, Math.min(2.5, length * 0.015));
    stream.querySelectorAll(".power-flow-arrow").forEach(arrow => {
        const phase = Number(arrow.dataset.flowPhase || 0);
        const distance = ((progress + phase) % 1) * length;
        const before = link.getPointAtLength(Math.max(0, distance - tangentOffset));
        const after = link.getPointAtLength(Math.min(length, distance + tangentOffset));
        const point = link.getPointAtLength(distance);
        const angle = Math.atan2(after.y - before.y, after.x - before.x) * 180 / Math.PI;

        arrow.setAttribute(
            "transform",
            `translate(${point.x.toFixed(2)} ${point.y.toFixed(2)}) rotate(${angle.toFixed(2)})`
        );
        arrow.removeAttribute("visibility");
    });
}

function animateInfoGraphicArrows(timestamp) {
    gInfoGraphicArrowAnimationFrame = null;
    const root = getInfoGraphicRoot();
    if (root == null || root.offsetParent == null || document.hidden)
        return;

    const activeNames = INFO_GRAPHIC_LINK_NAMES.filter(name =>
        document.getElementById("flow_arrows_" + name)?.classList.contains("is-active")
    );
    if (activeNames.length === 0)
        return;

    const progress = getInfoGraphicArrowProgress(timestamp);
    activeNames.forEach(name => positionInfoGraphicArrowStream(name, progress));
    gInfoGraphicArrowAnimationFrame = requestAnimationFrame(animateInfoGraphicArrows);
}

function startInfoGraphicArrowAnimation() {
    if (gInfoGraphicArrowAnimationFrame != null)
        return;
    if (gInfoGraphicArrowAnimationStartedAt == null)
        gInfoGraphicArrowAnimationStartedAt = performance.now();
    gInfoGraphicArrowAnimationFrame = requestAnimationFrame(animateInfoGraphicArrows);
}

function getMetricValue(payload, key) {
    const value = payload?.live?.[key]?.value;
    const number = Number(value);
    return Number.isFinite(number) ? number : 0;
}

function getMetricValueOrNull(payload, key) {
    const value = payload?.live?.[key]?.value;
    if (value == null || value === "")
        return null;
    const number = Number(value);
    return Number.isFinite(number) ? number : null;
}

function getInfoGraphicString(id, fallback) {
    if (typeof getGenericString === "function")
        return getGenericString(id);
    return fallback;
}

function getInfoGraphicNodeAnchor(rootRect, nodeName, side, verticalRatio = 0.5) {
    const nodeRect = document.getElementById("flow_node_" + nodeName)?.getBoundingClientRect();
    if (nodeRect == null)
        return null;

    return {
        x: (side === "right" ? nodeRect.right : nodeRect.left) - rootRect.left,
        y: nodeRect.top - rootRect.top + nodeRect.height * verticalRatio,
    };
}

function buildInfoGraphicCurve(start, end) {
    const horizontalDistance = Math.abs(end.x - start.x);
    const direction = end.x >= start.x ? 1 : -1;
    const controlOffset = Math.max(24, Math.min(160, horizontalDistance * 0.42));

    return [
        "M", start.x.toFixed(2), start.y.toFixed(2),
        "C", (start.x + direction * controlOffset).toFixed(2), start.y.toFixed(2),
        (end.x - direction * controlOffset).toFixed(2), end.y.toFixed(2),
        end.x.toFixed(2), end.y.toFixed(2),
    ].join(" ");
}

function setInfoGraphicPath(pathId, start, end) {
    const path = document.getElementById(pathId);
    if (path == null || start == null || end == null)
        return;
    path.setAttribute("d", buildInfoGraphicCurve(start, end));
}

function layoutInfoGraphicPaths(root, svg, svgRect) {
    const rootRect = root.getBoundingClientRect();
    svg.setAttribute("viewBox", `0 0 ${svgRect.width.toFixed(2)} ${svgRect.height.toFixed(2)}`);
    svg.setAttribute("preserveAspectRatio", "none");

    const solar = getInfoGraphicNodeAnchor(rootRect, "solar", "right");
    const grid = getInfoGraphicNodeAnchor(rootRect, "grid", "right");
    const hubInputSolar = getInfoGraphicNodeAnchor(rootRect, "hub", "left", 0.32);
    const hubInputGrid = getInfoGraphicNodeAnchor(rootRect, "hub", "left", 0.68);
    const hubOutputHouse = getInfoGraphicNodeAnchor(rootRect, "hub", "right", 0.32);
    const hubOutputBattery = getInfoGraphicNodeAnchor(rootRect, "hub", "right", 0.68);
    const house = getInfoGraphicNodeAnchor(rootRect, "home", "left");
    const battery = getInfoGraphicNodeAnchor(rootRect, "battery", "left");

    setInfoGraphicPath("flow_track_solar_hub", solar, hubInputSolar);
    setInfoGraphicPath("flow_link_solar_hub", solar, hubInputSolar);

    setInfoGraphicPath("flow_track_grid_hub", grid, hubInputGrid);
    setInfoGraphicPath("flow_link_grid_hub", grid, hubInputGrid);
    setInfoGraphicPath("flow_link_hub_grid_export", hubInputGrid, grid);

    setInfoGraphicPath("flow_track_hub_house", hubOutputHouse, house);
    setInfoGraphicPath("flow_link_hub_house", hubOutputHouse, house);

    setInfoGraphicPath("flow_track_hub_battery", hubOutputBattery, battery);
    setInfoGraphicPath("flow_link_hub_battery_charge", hubOutputBattery, battery);
    setInfoGraphicPath("flow_link_battery_hub_discharge", battery, hubOutputBattery);
}

function layoutInfoGraphicLabels() {
    const root = getInfoGraphicRoot();
    const svg = root?.querySelector(".power-flow-svg");
    const svgRect = svg?.getBoundingClientRect();

    gInfoGraphicLabelLayoutFrame = null;

    if (root == null || svg == null || svgRect == null || svgRect.width <= 0 || svgRect.height <= 0)
        return;

    layoutInfoGraphicPaths(root, svg, svgRect);

    const viewBox = svg.viewBox.baseVal;

    const scaleX = svgRect.width / viewBox.width;
    const scaleY = svgRect.height / viewBox.height;

    Object.entries(INFO_GRAPHIC_LABEL_LAYOUT).forEach(([name, layout]) => {
        const path = document.getElementById("flow_link_" + name);
        const label = document.getElementById("flow_label_" + name);

        if (path == null || label == null)
            return;

        const anchor = Math.max(0, Math.min(1, layout.anchor ?? 0.5));
        const point = path.getPointAtLength(path.getTotalLength() * anchor);
        const left = (point.x - viewBox.x) * scaleX + (layout.offsetX ?? 0);
        const top = (point.y - viewBox.y) * scaleY + (layout.offsetY ?? 0);

        label.style.left = left.toFixed(2) + "px";
        label.style.top = top.toFixed(2) + "px";
    });
}

function queueInfoGraphicLabelLayout() {
    if (gInfoGraphicLabelLayoutFrame != null)
        cancelAnimationFrame(gInfoGraphicLabelLayoutFrame);

    gInfoGraphicLabelLayoutFrame = requestAnimationFrame(layoutInfoGraphicLabels);
}

function formatInfoGraphicPower(value) {
    if (!Number.isFinite(value))
        return INFO_GRAPHIC_PLACEHOLDER;

    const absolute = Math.abs(value);
    if (absolute >= 1000)
        return numFormat(absolute / 1000, absolute >= 10000 ? 1 : 2) + " kW";
    return numFormat(absolute, 0) + " W";
}

function formatInfoGraphicPercent(value) {
    if (!Number.isFinite(value))
        return INFO_GRAPHIC_PLACEHOLDER;
    return numFormat(value, 0) + " %";
}

function setInfoGraphicEnabled(enabled) {
    const root = getInfoGraphicRoot();
    if (root == null)
        return;

    ensureInfoGraphicArrowStreams();
    gInfoGraphicEnabled = enabled === true;
    root.classList.toggle("is-disabled", !gInfoGraphicEnabled);
    queueInfoGraphicLabelLayout();
}

function setInfoGraphicNode(name, value, meta, active) {
    const node = document.getElementById("flow_node_" + name);
    const valueElement = document.getElementById("dash_flow_value_" + name);
    const metaElement = document.getElementById("dash_flow_meta_" + name);

    if (node == null || valueElement == null || metaElement == null)
        return;

    valueElement.textContent = value;
    metaElement.textContent = meta;
    node.classList.toggle("is-active", active);
}

function setInfoGraphicBatteryLevel(percent) {
    const batteryNode = document.getElementById("flow_node_battery");
    if (batteryNode == null)
        return;

    const numericPercent = Number(percent);
    if (percent == null || !Number.isFinite(numericPercent)) {
        batteryNode.style.setProperty("--battery-fill-level", "0");
        return;
    }

    const clampedPercent = Math.max(0, Math.min(100, numericPercent));
    batteryNode.style.setProperty("--battery-fill-level", (clampedPercent / 100).toFixed(3));
}

function setInfoGraphicInverterLoad(percent) {
    const inverterNode = document.getElementById("flow_node_hub");
    if (inverterNode == null)
        return;

    const numericPercent = Number(percent);
    if (percent == null || !Number.isFinite(numericPercent)) {
        inverterNode.style.setProperty("--inverter-load-level", "0");
        return;
    }

    const clampedPercent = Math.max(0, Math.min(100, numericPercent));
    inverterNode.style.setProperty("--inverter-load-level", (clampedPercent / 100).toFixed(3));
}

function setInfoGraphicLink(name, power, active) {
    ensureInfoGraphicArrowStreams();
    const link = document.getElementById("flow_link_" + name);
    const label = document.getElementById("flow_label_" + name);
    const arrows = document.getElementById("flow_arrows_" + name);
    if (link == null)
        return;

    const intensity = Math.min(1, Math.max(0.35, Math.abs(power) / 2600));
    const shouldShow = gInfoGraphicEnabled && active;

    if (shouldShow) {
        const progress = getInfoGraphicArrowProgress(performance.now());
        positionInfoGraphicArrowStream(name, progress);
    }

    link.classList.toggle("is-active", shouldShow);
    arrows?.classList.toggle("is-active", shouldShow);
    link.style.opacity = shouldShow ? intensity.toFixed(2) : "0";
    link.style.strokeWidth = shouldShow ? (1.9 + intensity * 0.55).toFixed(2) : "2";

    if (label != null) {
        label.textContent = shouldShow ? formatInfoGraphicPower(power) : "";
        label.classList.toggle("is-active", shouldShow);
    }

    if (shouldShow)
        startInfoGraphicArrowAnimation();
}

function resetInfoGraphic() {
    const root = getInfoGraphicRoot();
    if (root == null)
        return;

    root.classList.remove("is-stale");

    setInfoGraphicNode("solar", INFO_GRAPHIC_PLACEHOLDER, getInfoGraphicString("flow_state_idle", "Standby"), false);
    setInfoGraphicNode("grid", INFO_GRAPHIC_PLACEHOLDER, getInfoGraphicString("flow_state_idle", "Standby"), false);
    setInfoGraphicNode("hub", INFO_GRAPHIC_PLACEHOLDER, getInfoGraphicString("flow_state_idle", "Standby"), false);
    setInfoGraphicNode("home", INFO_GRAPHIC_PLACEHOLDER, getInfoGraphicString("flow_state_idle", "Standby"), false);
    setInfoGraphicNode("battery", INFO_GRAPHIC_PLACEHOLDER, getInfoGraphicString("flow_state_idle", "Standby"), false);
    setInfoGraphicBatteryLevel(null);
    setInfoGraphicInverterLoad(null);

    setInfoGraphicLink("solar_hub", 0, false);
    setInfoGraphicLink("grid_hub", 0, false);
    setInfoGraphicLink("hub_grid_export", 0, false);
    setInfoGraphicLink("hub_house", 0, false);
    setInfoGraphicLink("hub_battery_charge", 0, false);
    setInfoGraphicLink("battery_hub_discharge", 0, false);
    queueInfoGraphicLabelLayout();
}

function renderInfoGraphicFromOverview(payload) {
    const root = getInfoGraphicRoot();
    if (root == null)
        return;

    const solarPower = Math.max(0, getMetricValue(payload, "pv_power_w"));
    const housePower = Math.max(0, getMetricValue(payload, "ac_output_active_power_w"));
    const inverterLoad = getMetricValueOrNull(payload, "ac_output_load_percent");
    const batteryChargePower = Math.max(0, getMetricValue(payload, "battery_charge_power_w"));
    const batteryDischargePower = Math.max(0, getMetricValue(payload, "battery_discharge_power_w"));
    const batterySoc = getMetricValueOrNull(payload, "battery_state_of_charge_percent");

    const gridToHousePower = Math.max(0, getMetricValue(payload, "grid_to_house_power_w"));
    const gridToBatteryPower = Math.max(0, getMetricValue(payload, "grid_to_battery_power_w"));
    const gridImportPower = gridToHousePower + gridToBatteryPower;
    const gridExportPower = Math.max(0, getMetricValue(payload, "solar_feed_to_grid_power_w"));

    const batteryToHousePower = Math.max(
        batteryDischargePower,
        Math.max(0, getMetricValue(payload, "battery_to_house_power_w"))
    );
    const batteryChargeFlow = Math.max(
        batteryChargePower,
        Math.max(0, getMetricValue(payload, "solar_to_battery_power_w")) + gridToBatteryPower
    );

    const solarActive = solarPower > INFO_GRAPHIC_ACTIVE_THRESHOLD_W;
    const gridImportActive = gridImportPower > INFO_GRAPHIC_ACTIVE_THRESHOLD_W;
    const gridExportActive = gridExportPower > INFO_GRAPHIC_ACTIVE_THRESHOLD_W;
    const homeActive = housePower > INFO_GRAPHIC_ACTIVE_THRESHOLD_W;
    const batteryChargeActive = batteryChargeFlow > INFO_GRAPHIC_ACTIVE_THRESHOLD_W;
    const batteryDischargeActive = batteryToHousePower > INFO_GRAPHIC_ACTIVE_THRESHOLD_W;

    let gridMeta = getInfoGraphicString("flow_state_idle", "Standby");
    let gridValue = INFO_GRAPHIC_PLACEHOLDER;
    let gridActive = false;

    if (gridExportActive) {
        gridMeta = getInfoGraphicString("flow_state_export", "Exporting");
        gridValue = formatInfoGraphicPower(gridExportPower);
        gridActive = true;
    }
    else if (gridImportActive) {
        gridMeta = getInfoGraphicString("flow_state_import", "Importing");
        gridValue = formatInfoGraphicPower(gridImportPower);
        gridActive = true;
    }
    else if (payload?.health?.ac_input_available === true) {
        gridMeta = getInfoGraphicString("flow_state_available", "Available");
        gridValue = "0 W";
        gridActive = true;
    }

    let batteryValue = INFO_GRAPHIC_PLACEHOLDER;
    let batteryMeta = getInfoGraphicString("flow_state_idle", "Standby");
    let batteryActive = false;

    if (batteryChargePower > INFO_GRAPHIC_ACTIVE_THRESHOLD_W) {
        batteryValue = formatInfoGraphicPower(batteryChargePower);
        batteryMeta = getInfoGraphicString("flow_state_charging", "Charging");
        batteryActive = true;
    }
    else if (batteryDischargePower > INFO_GRAPHIC_ACTIVE_THRESHOLD_W) {
        batteryValue = formatInfoGraphicPower(batteryDischargePower);
        batteryMeta = getInfoGraphicString("flow_state_discharging", "Discharging");
        batteryActive = true;
    }
    else if (batterySoc != null) {
        batteryValue = formatInfoGraphicPercent(batterySoc);
        batteryMeta = getInfoGraphicString("flow_state_idle", "Standby");
        batteryActive = batterySoc > 0;
    }

    if (batterySoc != null && batteryMeta !== getInfoGraphicString("flow_state_idle", "Standby"))
        batteryMeta += " · " + formatInfoGraphicPercent(batterySoc);

    root.classList.toggle("is-stale", payload?.current_data_stale === true);

    setInfoGraphicNode(
        "solar",
        solarActive ? formatInfoGraphicPower(solarPower) : "0 W",
        solarActive
            ? getInfoGraphicString("flow_state_production", "Production")
            : getInfoGraphicString("flow_state_idle", "Veille"),
        solarActive
    );
    setInfoGraphicNode("grid", gridValue, gridMeta, gridActive);
    setInfoGraphicNode(
        "hub",
        formatInfoGraphicPercent(inverterLoad),
        inverterLoad != null
            ? getInfoGraphicString("flow_state_inverter_load", "Charge")
            : getInfoGraphicString("flow_state_idle", "Veille"),
        inverterLoad != null
    );
    setInfoGraphicInverterLoad(inverterLoad);
    setInfoGraphicNode(
        "home",
        homeActive ? formatInfoGraphicPower(housePower) : "0 W",
        homeActive
            ? getInfoGraphicString("flow_state_consumption", "Consommation")
            : getInfoGraphicString("flow_state_idle", "Veille"),
        homeActive
    );
    setInfoGraphicNode("battery", batteryValue, batteryMeta, batteryActive);
    setInfoGraphicBatteryLevel(batterySoc);

    setInfoGraphicLink("solar_hub", solarPower, solarActive);
    setInfoGraphicLink("grid_hub", gridImportPower, gridImportActive);
    setInfoGraphicLink("hub_grid_export", gridExportPower, gridExportActive);
    setInfoGraphicLink("hub_house", housePower, homeActive);
    setInfoGraphicLink("hub_battery_charge", batteryChargeFlow, batteryChargeActive);
    setInfoGraphicLink("battery_hub_discharge", batteryToHousePower, batteryDischargeActive);
}

function updateInfoGraphic(payload, gridConsumptionW, fedInW, pvConsumptionW = null) {
    if (!hasInfoGraphic())
        return;

    if (payload != null && typeof payload === "object" && !Array.isArray(payload)) {
        if (payload["state"] === "ok")
            renderInfoGraphicFromOverview(payload);
        else
            resetInfoGraphic();
        return;
    }

    const generatedW = Number(payload);
    const gridW = Number(gridConsumptionW);
    const exportW = Number(fedInW);
    const pvToHomeW = pvConsumptionW == null ? generatedW - exportW : Number(pvConsumptionW);

    if (!Number.isFinite(generatedW) || !Number.isFinite(gridW) || !Number.isFinite(exportW)) {
        resetInfoGraphic();
        return;
    }

    renderInfoGraphicFromOverview({
        state: "ok",
        current_data_stale: false,
        device: {
            operation_mode: null,
        },
        health: {
            ac_input_available: gridW > INFO_GRAPHIC_ACTIVE_THRESHOLD_W,
        },
        live: {
            pv_power_w: { value: generatedW },
            ac_output_active_power_w: { value: Math.max(0, pvToHomeW) + Math.max(0, gridW) },
            ac_output_load_percent: { value: null },
            battery_charge_power_w: { value: 0 },
            battery_discharge_power_w: { value: 0 },
            battery_state_of_charge_percent: { value: null },
            grid_to_house_power_w: { value: Math.max(0, gridW) },
            grid_to_battery_power_w: { value: 0 },
            solar_feed_to_grid_power_w: { value: Math.max(0, exportW) },
            battery_to_house_power_w: { value: 0 },
            solar_to_battery_power_w: { value: 0 },
        },
    });
}

window.addEventListener("resize", queueInfoGraphicLabelLayout);
document.addEventListener("visibilitychange", () => {
    if (!document.hidden)
        startInfoGraphicArrowAnimation();
});
window.addEventListener("DOMContentLoaded", () => {
    ensureInfoGraphicArrowStreams();
    if (typeof ResizeObserver === "function") {
        gInfoGraphicResizeObserver?.disconnect();
        gInfoGraphicResizeObserver = new ResizeObserver(queueInfoGraphicLabelLayout);
        const root = getInfoGraphicRoot();
        if (root != null)
            gInfoGraphicResizeObserver.observe(root);
    }
    document.fonts?.ready.then(queueInfoGraphicLabelLayout);
    queueInfoGraphicLabelLayout();
});
