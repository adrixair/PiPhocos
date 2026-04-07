(function () {
    const params = new URLSearchParams(window.location.search);
    if (params.get("mock") !== "1")
        return;

    const originalFetch = window.fetch.bind(window);
    const snapshotCandidates = [];
    const requestedSnapshot = params.get("snapshot");
    if (requestedSnapshot)
        snapshotCandidates.push(requestedSnapshot);
    snapshotCandidates.push("mock/ui-snapshot.json", "mock/ui-snapshot.sample.json");

    const mockState = {
        enabled: true,
        csvUrl: new URL("mock/ui-snapshot.sample.csv", window.location.href).href,
        snapshotSource: null,
    };
    window.__PIPHOCOS_MOCK__ = mockState;

    let snapshotPromise = null;

    function clone(value) {
        return value == null ? value : JSON.parse(JSON.stringify(value));
    }

    function firstMapValue(value) {
        if (value == null || Array.isArray(value))
            return value;
        const entries = Object.values(value);
        return entries.length > 0 ? entries[0] : undefined;
    }

    function pickMapValue(value, key) {
        if (value == null)
            return undefined;
        if (key != null && Object.prototype.hasOwnProperty.call(value, key))
            return value[key];
        return firstMapValue(value);
    }

    function deriveRealTimePayload(realTimeMap, requestedHours) {
        if (realTimeMap == null)
            return undefined;

        const requestedKey = requestedHours != null ? String(requestedHours) : null;
        if (requestedKey != null && Object.prototype.hasOwnProperty.call(realTimeMap, requestedKey))
            return realTimeMap[requestedKey];

        const hours = Number(requestedHours || 0);
        const fullSeries = realTimeMap["24"] || firstMapValue(realTimeMap);
        if (!Array.isArray(fullSeries))
            return fullSeries;
        if (!Number.isFinite(hours) || hours <= 0)
            return fullSeries;

        const targetLength = Math.min(fullSeries.length, Math.max(1, hours));
        return fullSeries.slice(0, targetLength);
    }

    function deriveLivePayload(snapshot) {
        const overview = snapshot.apiOverview || {};
        const live = overview.live || {};
        const semantics = {};
        Object.keys(live).forEach(key => {
            if (live[key] != null && typeof live[key] === "object" && live[key].semantics)
                semantics[key] = live[key].semantics;
        });
        return {
            state: overview.state || "ok",
            recorded_at: overview.recorded_at || null,
            current_data_stale: Boolean(overview.current_data_stale),
            device: overview.device || {},
            health: overview.health || {},
            pricing: overview.pricing || {},
            live: live,
            metrics: live,
            semantics: semantics,
        };
    }

    function deriveTempoPayload(snapshot) {
        const pricing = snapshot.apiOverview?.pricing || {};
        return {
            state: pricing.tempo_available ? "ok" : "nodata",
            grid_price_eur_per_kwh: pricing.grid_price_eur_per_kwh || 0.0,
            feed_in_revenue_eur_per_kwh: pricing.feed_in_revenue_eur_per_kwh || 0.0,
            source: pricing.source || "mock",
            tempo_available: Boolean(pricing.tempo_available),
            tempo_tariff_label: pricing.tariff_label || "",
            tempo_color: pricing.color_label || "",
            tempo_tomorrow_color: pricing.tomorrow_color_label || "",
            tempo_display: pricing.display || "",
        };
    }

    function createJsonResponse(payload, status) {
        const responseStatus = status || 200;
        return {
            ok: responseStatus >= 200 && responseStatus < 300,
            status: responseStatus,
            headers: new Headers({ "Content-Type": "application/json" }),
            json: async function () {
                return clone(payload);
            },
            text: async function () {
                return JSON.stringify(payload);
            },
        };
    }

    async function loadSnapshot() {
        if (snapshotPromise != null)
            return snapshotPromise;

        snapshotPromise = (async function () {
            let lastError = null;

            for (let index = 0; index < snapshotCandidates.length; index++) {
                const candidate = snapshotCandidates[index];
                const candidateUrl = new URL(candidate, window.location.href).href;

                try {
                    const response = await originalFetch(candidateUrl, { cache: "no-store" });
                    if (!response.ok)
                        continue;

                    const payload = await response.json();
                    mockState.snapshotSource = candidate;
                    if (candidate.endsWith(".json"))
                        mockState.csvUrl = new URL(candidate.slice(0, -5) + ".csv", window.location.href).href;
                    return payload;
                }
                catch (error) {
                    lastError = error;
                }
            }

            throw (lastError || new Error("No UI snapshot file found."));
        })();

        return snapshotPromise;
    }

    function resolveMockPayload(snapshot, url) {
        if (url.pathname.endsWith("/name"))
            return snapshot.name || "PiPhocos";
        if (url.pathname.endsWith("/api/overview"))
            return snapshot.apiOverview;
        if (url.pathname.endsWith("/api/live"))
            return snapshot.apiLive || deriveLivePayload(snapshot);
        if (url.pathname.endsWith("/api/tempo"))
            return snapshot.apiTempo || deriveTempoPayload(snapshot);
        if (url.pathname.endsWith("/api/date-bounds"))
            return snapshot.dates;
        if (url.pathname.endsWith("/api/statistics"))
            return snapshot.statistics;
        if (url.pathname.endsWith("/api/chart/live"))
            return {
                state: "ok",
                series: deriveRealTimePayload(snapshot.realTime, url.searchParams.get("hours")),
            };
        if (url.pathname.endsWith("/api/period")) {
            const bucket = url.searchParams.get("bucket");
            const date = url.searchParams.get("date");
            if (bucket === "day")
                return pickMapValue(snapshot.historical?.days, date);
            if (bucket === "month")
                return pickMapValue(snapshot.historical?.months, date);
            if (bucket === "year")
                return pickMapValue(snapshot.historical?.years, date);
            if (bucket === "all")
                return pickMapValue(snapshot.historical?.all_time, "all_time");
            return undefined;
        }
        if (url.pathname.endsWith("/api/breakdown")) {
            const bucket = url.searchParams.get("bucket");
            const prefix = url.searchParams.get("prefix");
            if (bucket === "day")
                return { state: "ok", items: pickMapValue(snapshot.historyDetails?.days_in_month, prefix) || [] };
            if (bucket === "month")
                return { state: "ok", items: pickMapValue(snapshot.historyDetails?.months_in_year, prefix) || [] };
            if (bucket === "year")
                return { state: "ok", items: snapshot.historyDetails?.years_in_all_time || [] };
            return undefined;
        }

        return undefined;
    }

    window.fetch = async function (input, init) {
        const rawUrl = typeof input === "string" ? input : input.url;
        const url = new URL(rawUrl, window.location.href);

        const isMockedEndpoint = url.pathname.endsWith("/name")
            || url.pathname.endsWith("/api/overview")
            || url.pathname.endsWith("/api/live")
            || url.pathname.endsWith("/api/tempo")
            || url.pathname.endsWith("/api/date-bounds")
            || url.pathname.endsWith("/api/statistics")
            || url.pathname.endsWith("/api/chart/live")
            || url.pathname.endsWith("/api/period")
            || url.pathname.endsWith("/api/breakdown");
        if (!isMockedEndpoint)
            return originalFetch(input, init);

        try {
            const snapshot = await loadSnapshot();
            const payload = resolveMockPayload(snapshot, url);
            if (payload === undefined)
                return originalFetch(input, init);
            return createJsonResponse(payload, 200);
        }
        catch (error) {
            console.error("Mock mode failed to load a snapshot.", error);
            return originalFetch(input, init);
        }
    };

    loadSnapshot().catch(function (error) {
        console.error("Mock mode failed to load a snapshot.", error);
    });
})();
