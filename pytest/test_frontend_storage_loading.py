"""Exercise request deadlines, closed-day caching and storage rendering in JS."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")


def run_frontend(body):
    if NODE is None:
        pytest.skip("Node.js is required for frontend behavior checks")
    harness = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const elements = new Map();
function element(id) {
    if (!elements.has(id)) {
        const classes = new Set();
        elements.set(id, {
            id, value: '', textContent: '', style: {}, dataset: {}, attributes: {},
            classList: {
                contains: value => classes.has(value),
                add: value => classes.add(value),
                remove: value => classes.delete(value),
                toggle: (value, enabled) => enabled ? classes.add(value) : classes.delete(value),
            },
            setAttribute(name, value) { this.attributes[name] = String(value); },
            removeAttribute(name) { delete this.attributes[name]; },
        });
    }
    return elements.get(id);
}
const context = vm.createContext({
    assert, element, setTimeout, clearTimeout, AbortController, URL, URLSearchParams,
    Intl, console,
    window: { addEventListener() {}, getComputedStyle: element => ({display: element.style.display || 'block'}) },
    document: { addEventListener() {}, getElementById: element, querySelectorAll: () => [] },
    fetch: async () => { throw new Error('Unexpected fetch'); },
});
vm.runInContext(fs.readFileSync(ROOT + '/site/js/localization.js', 'utf8'), context);
vm.runInContext(fs.readFileSync(ROOT + '/site/js/main.js', 'utf8'), context);
vm.runInContext('(async () => {' + BODY + '})()', context).then(
    () => console.log('Frontend checks completed'),
    error => {
        console.error(error);
        process.exitCode = 1;
    },
);
"""
    script = "const ROOT = " + json.dumps(str(ROOT)) + ";\n"
    script += "const BODY = " + json.dumps(body) + ";\n" + harness
    result = subprocess.run(
        [NODE, "-e", script], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Frontend checks completed" in result.stdout, "Les assertions JavaScript ne se sont pas terminées"


def test_request_timeout_aborts_transport_and_ends_history_loading():
    run_frontend(
        r"""
let transportSignal;
fetch = async (url, options) => {
    transportSignal = options.signal;
    return new Promise(() => {});
};
await assert.rejects(fetchJSONWithTimeout('/api/period', { timeoutMs: 10 }), error => error.name === 'TimeoutError');
assert.equal(transportSignal.aborted, true);
const external = new AbortController();
external.abort();
await assert.rejects(fetchJSONWithTimeout('/api/period', { signal: external.signal }), error => error.name === 'AbortError');

element('selection_year2').value = '2000';
element('selection_month2').value = '11';
element('selection_day2').value = '11';
element('history_status').classList.add('app-view-status-compact');
hideFloatingInfoTooltip = () => {};
persistCurrentViewState = () => {};
const timeoutFetch = fetchJSONWithTimeout;
fetchJSONWithTimeout = (url, options) => timeoutFetch(url, { ...options, timeoutMs: 10 });
await updateHistoryStats();
assert.equal(element('view_history').classList.contains('is-loading'), false);
assert.equal(element('history_stat_produced').classList.contains('app-skeleton-text'), false);
assert.equal(element('history_status').attributes['data-state'], 'error');
assert.match(element('history_status').textContent, /30 secondes/);
assert.equal(element('history_status').classList.contains('visually-hidden'), false);
"""
    )


def test_closed_day_cache_is_bounded_expires_and_never_caches_today():
    run_frontend(
        r"""
let requests = 0;
fetch = async () => ({ ok: true, json: async () => ({ state: 'ok', high_res: '[]', request: ++requests }) });
gCurHistory = histories.DAY;
element('selection_year2').value = '2000';
element('selection_month2').value = '11';
element('selection_day2').value = '11';
await fetchHistoryStatsJSON();
await fetchHistoryStatsJSON();
assert.equal(requests, 1);
const entry = [...gHistoryDayCache.values()][0];
entry.savedAt -= HISTORY_DAY_CACHE_TTL_MS;
await fetchHistoryStatsJSON();
assert.equal(requests, 2);
for (let day = 1; day <= 15; day++) {
    element('selection_day2').value = String(day);
    await fetchHistoryStatsJSON();
}
assert.equal(gHistoryDayCache.size, HISTORY_DAY_CACHE_LIMIT);
const today = new Date();
element('selection_year2').value = String(today.getFullYear());
element('selection_month2').value = String(today.getMonth() + 1);
element('selection_day2').value = String(today.getDate());
const beforeToday = requests;
await fetchHistoryStatsJSON();
await fetchHistoryStatsJSON();
assert.equal(requests, beforeToday + 2);
"""
    )


def test_storage_deduplicates_refresh_and_keeps_missing_sizes_unknown():
    run_frontend(
        r"""
let requests = 0;
let resolveFetch;
fetch = () => { requests++; return new Promise(resolve => { resolveFetch = resolve; }); };
element('storage_status').classList.add('app-view-status-compact');
const first = updateStorage();
assert.equal(updateStorage(), first);
assert.equal(requests, 1);
assert.equal(element('storage_disk_free').classList.contains('app-skeleton-text'), true);
assert.equal(element('storage_status').style.display, 'none');
resolveFetch({ ok: true, json: async () => ({
    state: 'partial', generated_at: '2026-11-18T19:00:00+01:00',
    disk: { total_bytes: 100 * 1000 ** 3, used_bytes: 20 * 1000 ** 3, free_bytes: 75 * 1000 ** 3 },
    database: { total_bytes: 500 * 1000 ** 2 },
    retention: { raw_history_hours: 6, energy_interval_days: 45, history_resolution_minutes: 10, summary_retention: 'unlimited' },
    history: { first_day: '2026-04-01', last_day: '2026-11-18' },
    errors: ['database_metrics_unavailable'],
}) });
await first;
assert.equal(element('storage_disk_free').classList.contains('app-skeleton-text'), false);
assert.equal(element('view_storage').attributes['aria-busy'], 'false');
assert.equal(element('storage_disk_fill').style.width, '25%');
assert.match(element('storage_database_size').textContent, /500[.,]0 Mo/);
assert.equal(element('storage_status').attributes['data-state'], 'info');
assert.equal(normalizeViewState({ view: 'storage' }).view, 'storage');
assert.equal(formatStorageBytes(null), '—');
assert.match(formatStorageBytes(1000 ** 3), /1[.,]0 Go/);
"""
    )


def test_loading_only_shimmers_without_a_status_banner():
    run_frontend(
        r"""
setViewStatus('history_status', 'loading', 'Chargement...');
setHistoryLoadingState(true);
assert.equal(element('history_status').style.display, 'none');
assert.equal(element('history_status').textContent, '');
assert.equal(element('history_status').attributes['data-state'], undefined);
assert.equal(element('history_stat_produced').classList.contains('app-skeleton-text'), true);
setHistoryLoadingState(false);
setViewStatus('history_status', 'error', 'Impossible de charger cette période.');
assert.equal(element('history_status').attributes['data-state'], 'error');
assert.notEqual(element('history_status').style.display, 'none');
"""
    )


def test_storage_refreshes_quietly_only_while_visible_and_when_due():
    run_frontend(
        r"""
let requests = 0;
fetch = async () => ({ ok: true, json: async () => { requests++; return {
    state: 'ok', disk: {}, database: {},
}; } });
gCurrentView = 'storage';
document.hidden = false;
await updateStorage();
assert.equal(requests, 1);
refreshStorageIfVisible();
assert.equal(requests, 1);
gLastStorageRefreshAt -= STORAGE_REFRESH_INTERVAL_MS;
refreshStorageIfVisible();
assert.equal(element('storage_disk_free').classList.contains('app-skeleton-text'), false);
await gStorageRequest;
assert.equal(requests, 2);
gLastStorageRefreshAt -= STORAGE_REFRESH_INTERVAL_MS;
document.hidden = true;
refreshStorageIfVisible();
assert.equal(requests, 2);
document.hidden = false;
gCurrentView = 'history';
refreshStorageIfVisible();
assert.equal(requests, 2);
gCurrentView = 'storage';
refreshStorageIfVisible();
await gStorageRequest;
assert.equal(requests, 3);
"""
    )


def test_recording_pause_is_only_shown_when_active_and_clears_on_resume():
    run_frontend(
        r"""
let allowed = true;
fetch = async () => ({ ok: true, json: async () => ({
    state: 'ok', disk: {}, database: {},
    recording: { write_allowed: allowed, reason: allowed ? null : 'low_disk_space' },
}) });
await updateStorage();
assert.equal(element('storage_status').style.display, 'none');
assert.doesNotMatch(element('telemetry_detail').textContent, /pause/);
allowed = false;
await updateStorage();
assert.match(element('storage_status').textContent, /pause.*espace insuffisant/);
assert.match(element('telemetry_detail').textContent, /pause.*espace insuffisant/);
allowed = true;
await updateStorage();
assert.equal(element('storage_status').style.display, 'none');
assert.doesNotMatch(element('telemetry_detail').textContent, /pause/);
applyTelemetryStatusFromOverview({ recording: { write_allowed: false, reason: 'disk_usage_unavailable' } });
assert.match(element('telemetry_detail').textContent, /pause.*stockage indisponible/);
"""
    )
