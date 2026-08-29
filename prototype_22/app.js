/* ─── app.js — Freebuff Forge Dashboard (v5.182.0-prototype) ──────────────
 * Vanilla JS + DOM. No framework. No build step.
 *
 * State model:
 *   apiBase        — string, resolved from ?api= or relative origin
 *   selectedSlug   — string|null — currently selected project in sidebar
 *   selectionToken — int — monotonic counter; bumped on every selection to drop stale responses
 *   autoRefresh    — bool — auto-refresh on/off
 *   lastFetch      — timestamp string from /health
 *   inFlightCtrl   — AbortController for current fetch round
 *   refreshTimer   — Timeout|null — setInterval handle for auto-refresh loop
 *
 * Fetch strategy:
 *   - On load: parallel Promise.all of /health, /, /api/v1/projects, /api/v1/metrics.
 *   - On project click: parallel fetch of /api/v1/projects/{slug***REMOVED*** + /api/v1/projects/{slug***REMOVED***/chain.
 *   - Every 10s: re-run the global 4-endpoint sweep.
 *
 * Error strategy:
 *   - Per-endpoint AbortController with 5s timeout (network fails fast on Termux).
 *   - 200 → render. 404 → render [404 NOT FOUND***REMOVED*** block in center. Other → render [ERROR***REMOVED*** + log.
 *   - Total connectivity loss → red border on #app-grid + 'OFFLINE' indicator.
 *
 * Mock-data indicators:
 *   - _mock: true from any endpoint → add #center-pipeline.mock-data for striped border.
 *   - Sidebar project item gets [MOCK***REMOVED*** prefix when its chain is synthetic.
 *
 * Defensive:
 *   - Strict .textContent usage for ALL data injection (no .innerHTML) → XSS-safe.
 *   - All render paths wrapped in try/catch → UI never dies.
 *   - Console log never throws.
 */

(function () {
    "use strict";

    // ─── Constants ─────────────────────────────────────────────────────────
    const REFRESH_INTERVAL_MS = 10_000;
    const FETCH_TIMEOUT_MS = 5_000;
    const MAX_LOG_LINES = 80;

    // ─── State ─────────────────────────────────────────────────────────────
    const state = {
        apiBase: resolveApiBase(),
        selectedSlug: null,
        selectionToken: 0,        // monotonic — bumped on every selection; stale fetches drop.
        autoRefresh: true,
        lastFetch: "—",
        inFlightCtrl: null,
        refreshTimer: null,
    ***REMOVED***;

    // ─── Resolvers ─────────────────────────────────────────────────────────
    function resolveApiBase() {
        try {
            const params = new URLSearchParams(window.location.search);
            const override = params.get("api");
            if (override) return override.replace(/\/+$/, "");
            // Default: same origin root + "/". Lets the static file be served by uvicorn /static/ or any reverse proxy.
            return window.location.origin ? window.location.origin + "/" : "/";
        ***REMOVED*** catch (_e) {
            return "/";
        ***REMOVED***
    ***REMOVED***

    // ─── DOM helpers ───────────────────────────────────────────────────────
    const $ = (id) => document.getElementById(id);

    function setText(id, val) {
        const el = $(id);
        if (el) el.textContent = val == null ? "—" : String(val);
    ***REMOVED***
    function setHTML(parentId, html) {
        const el = $(parentId);
        if (el) el.innerHTML = html;
    ***REMOVED***

    // ─── Time ─────────────────────────────────────────────────────────────
    function nowClock() {
        const d = new Date();
        const pad = (n) => String(n).padStart(2, "0");
        return pad(d.getHours()) + ":" + pad(d.getMinutes()) + ":" + pad(d.getSeconds());
    ***REMOVED***
    function nowIso() {
        return new Date().toISOString().replace("T", " ").slice(0, 19);
    ***REMOVED***

    // ─── Console logger ────────────────────────────────────────────────────
    function log(level, code, msg) {
        const list = $("log-list");
        if (!list) return;
        const li = document.createElement("li");
        li.className = "log-line log-" + level;
        const ts = document.createElement("span");
        ts.className = "log-time";
        ts.textContent = nowIso();
        const cd = document.createElement("span");
        cd.className = "log-code";
        cd.textContent = code == null ? "—" : String(code);
        const ms = document.createElement("span");
        ms.className = "log-msg";
        ms.textContent = msg;
        li.appendChild(ts);
        li.appendChild(cd);
        li.appendChild(ms);
        list.insertBefore(li, list.firstChild);
        // Trim
        while (list.children.length > MAX_LOG_LINES) {
            list.removeChild(list.lastChild);
        ***REMOVED***
    ***REMOVED***

    function setClock() {
        setText("m-clock", nowClock());
    ***REMOVED***

    // ─── Fetch with timeout ───────────────────────────────────────────────
    async function fetchJSON(path, opts) {
        const t0 = performance.now();
        const ctrl = new AbortController();
        const timer = setTimeout(() => ctrl.abort(), FETCH_TIMEOUT_MS);
        const url = state.apiBase.replace(/\/+$/, "") + path;
        try {
            const resp = await fetch(url, Object.assign({ signal: ctrl.signal ***REMOVED***, opts || {***REMOVED***));
            const tDelta = Math.round(performance.now() - t0);
            if (!resp.ok) {
                log(resp.status >= 500 ? "5xx" : "4xx", resp.status, "GET " + path + " (" + tDelta + "ms)");
                return { _error: "http-" + resp.status, _status: resp.status, _url: url ***REMOVED***;
            ***REMOVED***
            const data = await resp.json();
            log("2xx", resp.status, "GET " + path + " (" + tDelta + "ms)");
            return data;
        ***REMOVED*** catch (err) {
            const tDelta = Math.round(performance.now() - t0);
            const reason = err && err.name === "AbortError" ? "timeout" : (err && err.message) || "network-error";
            log(reason === "timeout" ? "warn" : "error", "—", "GET " + path + " FAILED [" + reason + "***REMOVED*** (" + tDelta + "ms)");
            // global connectivity marker:
            setOffline(true, reason);
            return { _error: reason, _url: url ***REMOVED***;
        ***REMOVED*** finally {
            clearTimeout(timer);
        ***REMOVED***
    ***REMOVED***

    // Use shared controller so global refresh cancels prior in-flight.
    async function fetchJSONBounded(path) {
        // Per-request controller; the global one is owned by setOffline lifecycle.
        return fetchJSON(path);
    ***REMOVED***

    // ─── Online / offline state ───────────────────────────────────────────
    function setOffline(off, reason) {
        const body = document.body;
        const cells = ["m-platform", "m-registry", "m-projects", "m-campaign", "m-p95"***REMOVED***;
        if (off) {
            body.style.borderTop = "4px solid var(--error)";
            cells.forEach((id) => {
                const el = $(id);
                if (el) {
                    el.classList.remove("degraded");
                    el.classList.add("offline");
                ***REMOVED***
            ***REMOVED***);
            setText("m-platform", "OFFLINE");
            log("error", "—", "connectivity lost: " + (reason || "?"));
        ***REMOVED*** else {
            body.style.borderTop = "";
            cells.forEach((id) => {
                const el = $(id);
                if (el) {
                    el.classList.remove("offline");
                ***REMOVED***
            ***REMOVED***);
        ***REMOVED***
    ***REMOVED***

    // ─── Renderers ─────────────────────────────────────────────────────────
    function renderLanding(rootData) {
        if (!rootData || rootData._error) {
            setText("m-platform", "—");
            return;
        ***REMOVED***
        const v = rootData.version || "—";
        setText("m-platform", v);
        setText("h-version", v);
        // Reset offline marker if previously set
        setOffline(false);
    ***REMOVED***

    function renderHealth(hData) {
        if (!hData || hData._error) {
            setText("m-registry", "—");
            setText("h-status", hData && hData._error ? hData._error : "—");
            $("h-status") && ($("h-status").className = "health-val offline");
            return;
        ***REMOVED***
        // /health → registry + cost summary
        const regState = hData.registry_present
            ? (hData.registry_violations > 0 ? "violations" : "ok")
            : "missing";
        setText("m-registry", regState.toUpperCase());
        setText("h-status", (hData.status || "—").toUpperCase());
        $("h-status") && ($("h-status").className = "health-val " + (hData.status === "ok" ? "ok" : "degraded"));
        setText("h-python", (hData.python || "—").split(" ")[0***REMOVED***);
        setText("h-regpath", hData.registry_path || "—");
        setText("h-violations", String(hData.registry_violations || 0));
        setText("h-loaderr", hData.registry_load_error || "—");
        setText("h-cost", hData.cost_metrics_present ? "loaded" : "missing");
        setText("h-lastfetch", nowIso());
    ***REMOVED***

    function renderProjects(pData) {
        const list = $("project-list");
        if (!list) return;
        list.textContent = ""; // clear
        if (!pData || pData._error) {
            const li = document.createElement("li");
            li.className = "placeholder";
            li.textContent = "projects unavailable";
            list.appendChild(li);
            setText("m-projects", "—");
            return;
        ***REMOVED***
        const items = Array.isArray(pData.projects) ? pData.projects : [***REMOVED***;
        setText("m-projects", String(items.length));
        if (items.length === 0) {
            const li = document.createElement("li");
            li.className = "placeholder";
            li.textContent = "no registered projects";
            list.appendChild(li);
            return;
        ***REMOVED***
        items.forEach((p) => {
            const li = document.createElement("li");
            li.className = "project-item";
            li.setAttribute("role", "option");
            li.setAttribute("tabindex", "0");
            li.dataset.slug = p.project_id;
            if (state.selectedSlug === p.project_id) li.classList.add("active");
            const id = document.createElement("span");
            id.className = "pi-id";
            id.textContent = p.project_id;
            const meta = document.createElement("span");
            meta.className = "pi-meta";
            const status = document.createElement("span");
            status.textContent = (p.status || "—").toUpperCase();
            const overall = document.createElement("span");
            overall.textContent = p.last_overall ? "· " + p.last_overall : "";
            const len = document.createElement("span");
            len.textContent = p.last_chain_len != null ? "· chain=" + p.last_chain_len : "";
            meta.appendChild(status);
            meta.appendChild(overall);
            meta.appendChild(len);
            li.appendChild(id);
            li.appendChild(meta);
            li.addEventListener("click", () => selectProject(p.project_id));
            li.addEventListener("keydown", (e) => {
                if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    selectProject(p.project_id);
                ***REMOVED***
            ***REMOVED***);
            list.appendChild(li);
        ***REMOVED***);
    ***REMOVED***

    function renderMetrics(metricData) {
        if (!metricData || !metricData.available) {
            setText("m-campaign", "—");
            setText("m-p95", "—");
            return;
        ***REMOVED***
        const ts = metricData.campaign_timestamp || "—";
        setText("m-campaign", ts.slice(0, 19));
        const summary = metricData.summary || {***REMOVED***;
        const p95 = summary.aggregate_p95_s != null ? summary.aggregate_p95_s + "s" : "—";
        setText("m-p95", p95);
    ***REMOVED***

    function clearCenter() {
        $("chain-empty") && ($("chain-empty").classList.remove("hidden"));
        $("project-detail") && ($("project-detail").classList.add("hidden"));
        $("chain-track-wrap") && ($("chain-track-wrap").classList.add("hidden"));
        $("project-header") && ($("project-header").className = "project-header-empty");
        const c = $("center-pipeline");
        if (c) c.classList.remove("mock-data");
    ***REMOVED***

    function renderProjectDetail(dData, chainData) {
        const center = $("center-pipeline");
        const hdr = $("project-header");
        const detail = $("project-detail");
        const chain = $("chain-track-wrap");
        const empty = $("chain-empty");
        if (!center || !hdr || !detail || !chain || !empty) return;
        empty.classList.add("hidden");
        hdr.classList.remove("project-header-empty");
        detail.classList.remove("hidden");
        chain.classList.remove("hidden");

        // Mock indicator
        const isMock = !!(chainData && chainData._mock);
        center.classList.toggle("mock-data", isMock);

        // header
        hdr.textContent = "";
        const t = document.createElement("h2");
        t.className = "panel-title";
        t.textContent = isMock ? "[MOCK***REMOVED*** " + (dData && dData.project_id ? dData.project_id : (chainData && chainData.project_id) || "?") : ((dData && dData.project_id) || (chainData && chainData.project_id) || "?");
        hdr.appendChild(t);
        const sub = document.createElement("p");
        sub.className = "hint";
        sub.textContent = isMock ? "synthetic data (no last_pipeline in registry)" : "real registry data";
        hdr.appendChild(sub);

        if (dData && !dData._error) {
            setText("d-id", dData.matched_as || dData.project_id || "—");
            setText("d-status", (dData.status || "—").toUpperCase());
            setText("d-root", dData.root || "—");
            $("d-root") && ($("d-root").title = dData.root || "");
            setText("d-registered", dData.registered_at || "—");
            setText("d-lastrun", dData.last_run_at || "—");
            setText("d-overall", dData.last_pipeline_overall || "—");
            setText("d-chainlen", String((dData.last_chain || [***REMOVED***).length));
        ***REMOVED*** else if (chainData && !chainData._error) {
            // Bare chain data — synthesize detail view from chain fields
            setText("d-id", chainData.project_id || "—");
            setText("d-status", "—");
            setText("d-root", chainData.project_root || "—");
            setText("d-registered", "—");
            setText("d-lastrun", "—");
            setText("d-overall", chainData.overall || "—");
            setText("d-chainlen", String((chainData.chain || [***REMOVED***).length));
        ***REMOVED*** else {
            // Both errored
            setText("d-id", "—");
            setText("d-status", "ERR");
            setText("d-root", "—");
            setText("d-registered", "—");
            setText("d-lastrun", "—");
            setText("d-overall", "—");
            setText("d-chainlen", "—");
        ***REMOVED***

        // Chain track
        const track = $("chain-track");
        if (track) {
            track.textContent = "";
            const arr = (chainData && chainData.chain) || [***REMOVED***;
            arr.forEach((stage) => {
                const div = document.createElement("div");
                div.className = "chain-stage mode-" + (stage.mode || "unknown_mode");
                div.setAttribute("role", "listitem");
                const role = document.createElement("div");
                role.className = "stage-role";
                role.textContent = stage.role_id || "?";
                const mode = document.createElement("div");
                mode.className = "stage-mode";
                mode.textContent = stage.mode || "?";
                const status = document.createElement("div");
                status.className = "stage-status status-" + (stage.status || "missing");
                status.textContent = stage.status || "missing";
                const dur = document.createElement("div");
                dur.className = "stage-duration";
                dur.textContent = (typeof stage.duration_s === "number" ? stage.duration_s.toFixed(2) : "?") + "s";
                div.appendChild(role);
                div.appendChild(mode);
                div.appendChild(status);
                div.appendChild(dur);
                div.title = stage.details || "";
                track.appendChild(div);
            ***REMOVED***);
        ***REMOVED***
    ***REMOVED***

    function selectProject(slug) {
        if (!slug || slug === state.selectedSlug) return;
        state.selectedSlug = slug;
        // Persist for next reload (overwrites previous selection).
        persistSelection(slug);
        // Stale-response guard: bump the token on every click; capture the
        // generation that owns THIS render. If the user picks another project
        // before the fetches resolve, the captured token will be stale and
        // we'll drop the late response to avoid UI flicker.
        const currentToken = ++state.selectionToken;
        // Mark active in sidebar
        const items = document.querySelectorAll(".project-item");
        items.forEach((li) => li.classList.toggle("active", li.dataset.slug === slug));
        // Render placeholder while loading
        $("chain-empty") && ($("chain-empty").classList.remove("hidden"));
        $("project-detail") && ($("project-detail").classList.add("hidden"));
        $("chain-track-wrap") && ($("chain-track-wrap").classList.add("hidden"));
        const hdr = $("project-header");
        if (hdr) {
            hdr.classList.add("project-header-empty");
            hdr.textContent = "";
            const t = document.createElement("h2");
            t.className = "panel-title";
            t.textContent = "LOADING " + slug + " …";
            hdr.appendChild(t);
        ***REMOVED***
        // Fetch detail + chain in parallel
        Promise.all([
            fetchJSONBounded("/api/v1/projects/" + encodeURIComponent(slug)),
            fetchJSONBounded("/api/v1/projects/" + encodeURIComponent(slug) + "/chain"),
        ***REMOVED***).then(([detail, chainData***REMOVED***) => {
            // Drop stale responses: another project was selected while we were fetching.
            if (state.selectionToken !== currentToken) {
                log("info", "—", "drop stale fetch for " + slug);
                return;
            ***REMOVED***
            try {
                renderProjectDetail(detail, chainData);
            ***REMOVED*** catch (e) {
                log("error", "—", "render center failed: " + (e && e.message));
            ***REMOVED***
        ***REMOVED***);
    ***REMOVED***

    // ─── Refresh loop ──────────────────────────────────────────────────────
    async function refreshGlobal() {
        try {
            const [root, health, projects, metrics***REMOVED*** = await Promise.all([
                fetchJSONBounded("/"),
                fetchJSONBounded("/health"),
                fetchJSONBounded("/api/v1/projects"),
                fetchJSONBounded("/api/v1/metrics"),
            ***REMOVED***);
            renderLanding(root);
            renderHealth(health);
            renderProjects(projects);
            renderMetrics(metrics);
            // Re-render selected project's chain (regenerate mock / refresh timestamps).
            if (state.selectedSlug) {
                // Capture token; if user changes selection during this async window, skip the render.
                const currentToken = state.selectionToken;
                const ch = await fetchJSONBounded("/api/v1/projects/" + encodeURIComponent(state.selectedSlug) + "/chain");
                const det = await fetchJSONBounded("/api/v1/projects/" + encodeURIComponent(state.selectedSlug));
                if (state.selectionToken !== currentToken) return;
                renderProjectDetail(det, ch);
            ***REMOVED***
            state.lastFetch = nowIso();
        ***REMOVED*** catch (e) {
            log("error", "—", "global refresh failed: " + (e && e.message));
        ***REMOVED***
    ***REMOVED***

    function startAutoRefresh() {
        if (state.refreshTimer) clearInterval(state.refreshTimer);
        state.refreshTimer = setInterval(() => {
            if (state.autoRefresh) refreshGlobal();
        ***REMOVED***, REFRESH_INTERVAL_MS);
    ***REMOVED***

    function toggleAutoRefresh() {
        state.autoRefresh = !state.autoRefresh;
        const btn = $("btn-pause");
        if (btn) btn.textContent = state.autoRefresh ? "⏸" : "▶";
        log("info", "—", "auto-refresh " + (state.autoRefresh ? "ON" : "OFF"));
    ***REMOVED***

    function clearLog() {
        const list = $("log-list");
        if (list) list.textContent = "";
    ***REMOVED***

    // ─── Design polish: mouse-follow glow (v5.187.1-redesign) ───
    // Sets --mx/--my CSS vars so body::before draws a soft lilac halo that
    // follows the cursor (CSS-only radial-gradient; no layout cost).
    function setupMouseGlow() {
        const doc = document.documentElement;
        let last = 0;
        const move = (ev) => {
            const now = performance.now();
            if (now - last >= 16) { // ~60fps throttle
                last = now;
                doc.style.setProperty("--mx", ev.clientX + "px");
                doc.style.setProperty("--my", ev.clientY + "px");
            ***REMOVED***
        ***REMOVED***;
        document.addEventListener("pointermove", move, { passive: true ***REMOVED***);
    ***REMOVED***

    // ─── Persistence (localStorage) ───
    // selectedSlug persists across reloads so the user returns to the same
    // project. All accesses try/catch because localStorage can throw in
    // private-mode browsers, file:// contexts, or security contexts without
    // the Storage API — falling back to in-memory only.
    const PERSIST_KEY = "selectedSlug";
    function loadPersistedSelection() {
        try {
            return (window.localStorage && window.localStorage.getItem(PERSIST_KEY)) || null;
        ***REMOVED*** catch (_e) {
            return null;
        ***REMOVED***
    ***REMOVED***
    function persistSelection(slug) {
        try {
            if (slug && window.localStorage) {
                window.localStorage.setItem(PERSIST_KEY, slug);
            ***REMOVED***
        ***REMOVED*** catch (_e) { /* private mode / quota exceeded — silently degrade */ ***REMOVED***
    ***REMOVED***
    function clearPersistedSelection() {
        try {
            if (window.localStorage) {
                window.localStorage.removeItem(PERSIST_KEY);
            ***REMOVED***
        ***REMOVED*** catch (_e) { /* same defensive fallback */ ***REMOVED***
    ***REMOVED***

    // ─── Wire up ───────────────────────────────────────────────────────────
    function init() {
        setupMouseGlow();
        // UI bindings
        $("btn-pause") && $("btn-pause").addEventListener("click", toggleAutoRefresh);
        $("btn-clear-log") && $("btn-clear-log").addEventListener("click", clearLog);
        // Clock
        setClock();
        setInterval(setClock, 1000);
        log("info", "—", "boot v5.182.0-prototype · api=" + state.apiBase);
        // Restore persisted selection BEFORE refreshGlobal so its per-selected-project
        // fetch + render branch auto-fires with state.selectedSlug already populated
        // (no second click required after refresh).
        const persisted = loadPersistedSelection();
        if (persisted) {
            state.selectedSlug = persisted;
            log("info", "—", "restored persisted selection: " + persisted);
        ***REMOVED***
        // First fetch
        refreshGlobal();
        // Auto-refresh
        startAutoRefresh();
    ***REMOVED***

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    ***REMOVED*** else {
        init();
    ***REMOVED***
***REMOVED***)();
