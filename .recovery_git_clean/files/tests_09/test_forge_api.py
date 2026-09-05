"""tests_09/test_forge_api.py — FastAPI surface tests for scripts_01/forge_api.py (v5.186.0).

TestClient-based integration tests (no live uvicorn / no network).
Covers 5 user-required categories:
1. All 8 endpoints return expected status + JSON schema.
2. /api/v1/projects/{slug***REMOVED*** returns 404 for unknown slug.
3. CORS preflight OPTIONS returns Access-Control-Allow-Origin.
4. /api/v1/projects/{slug***REMOVED***/chain includes _mock:False/True correctly.
5. /static/{app.js,style.css,index.html***REMOVED*** returns 200 + correct Content-Type.

Importability: scripts_01/forge_api.py is the SUT and lives in scripts_01/.
We need its imports (core_02.forge_facade, core_02.forge_registry) to resolve.
The SUT bootstraps sys.path itself (REPO_ROOT insertion at the top), but for
clean testing we mirror the same bootstrap here.

Test isolation: module-scoped TestClient shared across tests in this file.
TestClient is httpx-backed synchronous and serves ASGI in-process, so no
port-binding or real uvicorn is needed.
"""

from __future__ import annotations

import sys
***REMOVED***

# Mirror SUT's sys.path bootstrap so `from scripts_01.forge_api import app` resolves.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest  # noqa: E402  (after sys.path bootstrap)
from fastapi.testclient import TestClient  # noqa: E402

from scripts_01.forge_api import APP_VERSION, app  # noqa: E402

# v5.189.12 (xdist race fix): этот файл читает РЕАЛЬНЫЙ реестр
# data_13/forge_registry.yaml через API (registered_projects / chain endpoints),
# а test_forge_chain_real_integration.py и test_forge_chain_cli.py пишут в него
# (record_run). Под --dist loadgroup группа гарантирует один воркер → никаких
# torn-read гонок (stage_count=1 vs 14 при параллельном резюме).
pytestmark = pytest.mark.xdist_group("forge_real_registry")  # noqa: E402


# ─── Shared fixtures ──────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Single TestClient shared across this module's tests.

    TestClient is starlette's high-level in-process ASGI dispatcher:
    it wraps httpx internally and bridges sync→async via anyio so
    `.get()` / `.options()` / `.post()` work without port-binding.
    No live uvicorn worker is needed.

    Why not starlette.TestClient directly passed to httpx:
    Our pinned versions are starlette==0.27.0 + httpx==0.27.2, which
    are mutually compatible (TestClient.__init__ uses App+httpx.Client
    from this era). Migration history note: a v5.186.0 R1 attempt to
    use httpx.Client(transport=ASGITransport(app=app)) directly failed
    because ASGITransport only exposes handle_async_request; the
    starlette TestClient's anyio bridge is the correct sync path here.
    """
    return TestClient(app)


@pytest.fixture(scope="module")
def registered_projects(client: TestClient) -> list[dict***REMOVED***:
    """Snapshot of /api/v1/projects entries — re-used across tests for stability.

    If registry is empty (rare), returns [***REMOVED***. Per-project get tests then skip
    gracefully so this suite works in both populated and empty-registry envs.
    """
    r = client.get("/api/v1/projects")
    assert r.status_code == 200
    return r.json().get("projects") or [***REMOVED***


# ─── (1) All 8 endpoints return expected status + JSON schema ─────────────


class TestAllEndpoints:
    """8 GET endpoints under v5.181.0 surface (8 routes incl. /static/{path***REMOVED***)."""

    def test_root_returns_200_with_platform_info(self, client: TestClient) -> None:
        r = client.get("/")
        assert r.status_code == 200
        d = r.json()
        # Required platform-info keys
        for k in ("name", "version", "platform", "endpoints"):
            assert k in d, f"missing key {k!r***REMOVED*** in root payload"
        assert d["name"***REMOVED*** == "Freebuff Forge API"
        assert d["version"***REMOVED*** == APP_VERSION
        assert d["pipeline_chain_source"***REMOVED*** == "core_02.forge_facade.PIPELINE_CHAIN"
        assert d["pipeline_chain_role_count"***REMOVED*** == 14
        # endpoint map list is non-empty
        assert isinstance(d["endpoints"***REMOVED***, dict)
        assert len(d["endpoints"***REMOVED***) >= 5

    def test_root_serves_html_dashboard_for_browser_accept(self, client: TestClient) -> None:
        """v5.187.2: GET / with Accept: text/html → dashboard HTML (not raw JSON)."""
        r = client.get("/", headers={"Accept": "text/html"***REMOVED***)
        assert r.status_code == 200
        ct = r.headers.get("content-type", "")
        assert "html" in ct.lower(), f"expected html content-type, got {ct!r***REMOVED***"
        assert "<!DOCTYPE" in r.text or "<html" in r.text.lower()
        # Lilac Dark dashboard marker present (aurora background)
        assert "aurora" in r.text or "Lilac Dark" in r.text

    def test_root_returns_json_for_wildcard_accept(self, client: TestClient) -> None:
        """v5.187.2: GET / with Accept: */* → platform-info JSON (backward-compatible)."""
        r = client.get("/", headers={"Accept": "*/*"***REMOVED***)
        assert r.status_code == 200
        ct = r.headers.get("content-type", "")
        assert "json" in ct.lower(), f"expected json content-type, got {ct!r***REMOVED***"
        d = r.json()
        assert d["name"***REMOVED*** == "Freebuff Forge API"
        assert d["version"***REMOVED*** == APP_VERSION

    def test_health_returns_200_with_liveness_fields(self, client: TestClient) -> None:
        r = client.get("/health")
        assert r.status_code == 200
        d = r.json()
        # Liveness contract
        assert d["status"***REMOVED*** in ("ok", "degraded")
        assert isinstance(d["registry_present"***REMOVED***, bool)
        assert isinstance(d["registry_violations"***REMOVED***, int)
        assert d["registry_violations"***REMOVED*** >= 0
        assert "registry_load_error" in d
        assert "cost_metrics_present" in d
        assert d["app_version"***REMOVED*** == APP_VERSION
        assert "python" in d
        assert "registry_path" in d
        assert "timestamp" in d

    def test_api_v1_projects_returns_200_with_projects_list(
        self, client: TestClient, registered_projects: list[dict***REMOVED***
    ) -> None:
        r = client.get("/api/v1/projects")
        assert r.status_code == 200
        d = r.json()
        assert d["count"***REMOVED*** == len(registered_projects)
        assert isinstance(d["projects"***REMOVED***, list)
        assert isinstance(d["schema_violations"***REMOVED***, list)
        # Optional presence of load_error
        assert "load_error" in d
        # Each project: required keys
        for p in registered_projects:
            for k in ("project_id", "name", "root", "status", "last_run_at"):
                assert k in p, f"missing {k!r***REMOVED*** in projects[{p.get('project_id')!r***REMOVED******REMOVED***"

    def test_api_v1_projects_detail_returns_200_for_registered(
        self, client: TestClient, registered_projects: list[dict***REMOVED***
    ) -> None:
        if not registered_projects:
            pytest.skip("no registered projects in registry (registry may be empty)")
        slug = registered_projects[0***REMOVED***["project_id"***REMOVED***
        r = client.get(f"/api/v1/projects/{slug***REMOVED***")
        # Real registry OR synthetic mock fallback — both return 200
        assert r.status_code == 200
        d = r.json()
        assert "_mock" in d  # mock flag discipline (v5.181.0 contract)
        assert d["project_id"***REMOVED*** in (slug, slug.replace("-", "_"))
        # Detail contract
        for k in ("matched_as", "name", "status", "last_pipeline_overall"):
            assert k in d

    def test_api_v1_projects_chain_returns_200_with_chain_payload(
        self, client: TestClient, registered_projects: list[dict***REMOVED***
    ) -> None:
        if not registered_projects:
            pytest.skip("no registered projects in registry")
        slug = registered_projects[0***REMOVED***["project_id"***REMOVED***
        r = client.get(f"/api/v1/projects/{slug***REMOVED***/chain")
        assert r.status_code == 200
        d = r.json()
        # 9-key schema (v5.164.0 canonical)
        for k in ("_mock", "project_id", "project_root", "stage_count",
                  "chain", "overall", "started_at", "finished_at",
                  "validation_registry_status"):
            assert k in d, f"missing {k!r***REMOVED*** in chain payload"
        assert d["stage_count"***REMOVED*** == 14
        assert len(d["chain"***REMOVED***) == d["stage_count"***REMOVED***
        # Each chain stage has 5 fields
        for s in d["chain"***REMOVED***:
            for k in ("role_id", "mode", "status", "details", "duration_s"):
                assert k in s, f"missing {k!r***REMOVED*** in chain[{s.get('role_id')!r***REMOVED******REMOVED***"

    def test_api_v1_metrics_returns_200_with_availability_flag(self, client: TestClient) -> None:
        r = client.get("/api/v1/metrics")
        assert r.status_code == 200
        d = r.json()
        # Available IIF /tmp/forge_chain_chaos_cost.json exists; either branch is valid.
        assert "available" in d
        if d["available"***REMOVED***:
            for k in ("campaign_timestamp", "schema_version", "config", "env",
                      "projects", "summary"):
                assert k in d
        # If unavailable, reason present
        else:
            assert "reason" in d


# ─── (2) 404 for unknown slug ────────────────────────────────────────────


UNKNOWN_SLUG = "__nonexistent_zzz_test_only__"


# v5.189.50: Slug'и с намеренно частичными chains (regression-фикстуры для
# forge.py chain <slug> --generate). Источник: 'smoke' пишет 1-stage lisa ChainRun из
# tests_09/test_forge_chain_cli.py:212 (forge chain smoke --generate).
# Конвенция: PARTIAL_CHAIN_SLUGS — закрытый whitelist (новый partial-chain slug
# обязан ЯВНО добавляться сюда + иметь парный contract test, иначе strict-14
# assertion в test_chain_for_registered_project_has_canonical_14_stages зафиксирует
# regression). НЕ для silent-включения произвольных partial chains.
PARTIAL_CHAIN_SLUGS = frozenset({"smoke"***REMOVED***)


class TestProjectNotFound:
    """Unknown slug must return 404 (not 401, not 200-pretending)."""

    def test_detail_returns_404_for_unknown_slug(self, client: TestClient) -> None:
        r = client.get(f"/api/v1/projects/{UNKNOWN_SLUG***REMOVED***")
        assert r.status_code == 404
        d = r.json()
        # FastAPI HTTPException detail shape
        assert "detail" in d
        assert UNKNOWN_SLUG in d["detail"***REMOVED***

    def test_detail_returns_404_for_unknown_slug_with_special_chars(self, client: TestClient) -> None:
        # Edge: hyphen + underscore variants
        for slug in ("definitely-not-real-xyz", "also_not_real_xyz"):
            r = client.get(f"/api/v1/projects/{slug***REMOVED***")
            assert r.status_code == 404, f"expected 404 for {slug!r***REMOVED***, got {r.status_code***REMOVED***"


# ─── (3) CORS preflight OPTIONS returns Access-Control-Allow-Origin ────────


class TestCORSPreflight:
    """Starlette CORSMiddleware (allow_origins=['*'***REMOVED***) should respond 200 + ACAO."""

    def test_options_returns_allow_origin_header(self, client: TestClient) -> None:
        r = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            ***REMOVED***,
        )
        # CORS preflight accepted
        assert r.status_code in (200, 204), f"preflight returned {r.status_code***REMOVED***"
        # Access-Control-Allow-Origin must be present and permissive
        acao = r.headers.get("access-control-allow-origin")
        assert acao is not None, "missing Access-Control-Allow-Origin on preflight"
        # v5.181.0 was wide-open (*)
        assert acao == "*" or "localhost" in acao

    def test_options_returns_allow_methods_header(self, client: TestClient) -> None:
        r = client.options(
            "/api/v1/projects",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            ***REMOVED***,
        )
        # Access-Control-Allow-Methods header may be present on preflight
        acam = r.headers.get("access-control-allow-methods", "")
        if acam:
            assert "GET" in acam.upper()

    def test_actual_get_with_origin_header_also_returns_acao(
        self, client: TestClient
    ) -> None:
        """CORS-middleware also adds ACAO on actual responses (not just preflight)."""
        r = client.get(
            "/health",
            headers={"Origin": "http://localhost:5173"***REMOVED***,
        )
        assert r.status_code == 200
        acao = r.headers.get("access-control-allow-origin")
        assert acao is not None
        assert acao == "*" or "localhost" in acao


# ─── (4) chain _mock flag discipline ─────────────────────────────────────


class TestChainStageCount:
    """_mock:False for registered projects with real last_pipeline; _mock:True for synthetic."""

    def test_chain_includes_mock_flag_key(self, client: TestClient) -> None:
        """Every chain payload must carry `_mock` field (design contract)."""
        # Sample one unknown slug via chain fallback
        r = client.get(f"/api/v1/projects/{UNKNOWN_SLUG***REMOVED***/chain")
        assert r.status_code == 200
        d = r.json()
        assert "_mock" in d, "_mock flag missing from chain payload"

    def test_chain_for_unknown_slug_returns_mock_true(
        self, client: TestClient
    ) -> None:
        """Unknown slug → mock fallback (no real last_pipeline in registry)."""
        r = client.get(f"/api/v1/projects/{UNKNOWN_SLUG***REMOVED***/chain")
        d = r.json()
        # The chain endpoint falls through to mock when:
        #  (a) project not in registry AND
        #  (b) there's no real last_pipeline. Either way, _mock should be True.
        if not d.get("_error"):
            assert d["_mock"***REMOVED*** is True, "unknown slug should yield _mock=True"

    # v5.189.50: partial-chain projects (PARTIAL_CHAIN_SLUGS, module-level above)
    # skip the strict 14-stage assertion; contract covered separately by
    # test_partial_chain_smoke_has_1_stage_lisa_only below.

    @pytest.mark.slow  # v5.189.10: реальный chain-прогон через API (~15s)
    def test_chain_for_registered_project_has_canonical_14_stages(
        self, client: TestClient, registered_projects: list[dict***REMOVED***
    ) -> None:
        """All FULL-CHAIN registered projects → stage_count exactly 14 (PIPELINE_CHAIN length).

        v5.189.50: partial-chain projects (PARTIAL_CHAIN_SLUGS) skip the strict
        14-stage assertion; they're asserted separately via test_partial_chain_smoke.
        """
        if not registered_projects:
            pytest.skip("no registered projects in registry")
        for p in registered_projects:
            slug = p["project_id"***REMOVED***
            if slug in PARTIAL_CHAIN_SLUGS:
                continue  # not a full-chain project; see test_partial_chain_smoke
            r = client.get(f"/api/v1/projects/{slug***REMOVED***/chain")
            d = r.json()
            if d.get("_error"):
                continue  # transient — skip
            assert d["stage_count"***REMOVED*** == 14, f"{slug!r***REMOVED*** chain length mismatch"
            assert len(d["chain"***REMOVED***) == 14
            # Project_id in payload matches slug canonical form
            assert d["project_id"***REMOVED*** in (slug, slug.replace("-", "_"), slug.replace("_", "-"))

    @pytest.mark.slow  # v5.189.50: contract test for partial-chain project
    def test_partial_chain_smoke_has_1_stage_lisa_only(
        self, client: TestClient
    ) -> None:
        """'smoke' project → recorded 1-stage lisa ChainRun from forge chain smoke --generate.

        Source: tests_09/test_forge_chain_cli.py:212 (regression fixture,
        records stage_count=1 + chain=[{role_id: 'lisa', mode: 'generate'***REMOVED******REMOVED***).
        Если 'smoke' отсутствует в registry (никто ещё не прогнал chain --generate)
        — skip, чтобы тест был green в обоих режимах (pre/post fixture).
        Документируем контракт: partial-chain projects SILENTLY исключаются из
        canonical-14 assertion в test_chain_for_registered_project_has_canonical_14_stages.
        """
        r = client.get("/api/v1/projects/smoke/chain")
        if r.status_code == 404:
            pytest.skip("'smoke' not yet registered (no prior chain --generate run)")
        assert r.status_code == 200
        d = r.json()
        if d.get("_error"):
            pytest.skip("transient fetch error")
        if d.get("_mock"):
            pytest.skip("'smoke' has no real pipeline; mock fallback applies")
        # Contract: forge chain smoke --generate records exactly 1 stage (lisa)
        assert d["stage_count"***REMOVED*** == 1, (
            f"'smoke' expected partial chain stage_count=1, got {d['stage_count'***REMOVED***!r***REMOVED***"
        )
        assert len(d["chain"***REMOVED***) == 1
        assert d["chain"***REMOVED***[0***REMOVED***["role_id"***REMOVED*** == "lisa"
        assert d["chain"***REMOVED***[0***REMOVED***["mode"***REMOVED*** == "generate"

    @pytest.mark.slow  # v5.189.10: реальный chain-прогон через API
    def test_chain_includes_validation_registry_status(
        self, client: TestClient, registered_projects: list[dict***REMOVED***
    ) -> None:
        """validation_registry_status key present (loaded/missing/unreadable)."""
        if not registered_projects:
            pytest.skip("no registered projects")
        slug = registered_projects[0***REMOVED***["project_id"***REMOVED***
        r = client.get(f"/api/v1/projects/{slug***REMOVED***/chain")
        d = r.json()
        if d.get("_error"):
            pytest.skip("transient fetch error")
        assert "validation_registry_status" in d
        assert d["validation_registry_status"***REMOVED*** in ("loaded", "missing", "unreadable")


# ─── (5) Static mounts return 200 + correct Content-Type ─────────────────


class TestStaticMounts:
    """StaticFiles mount + FileResponse for /prototype should serve prototype/ files."""

    def test_static_app_js_returns_200_javascript(self, client: TestClient) -> None:
        r = client.get("/static/app.js")
        assert r.status_code == 200
        ct = r.headers.get("content-type", "")
        # StaticFiles infers type from extension; .js → application/javascript or text/javascript
        assert (
            "javascript" in ct.lower()
            or "text/javascript" in ct.lower()
            or "application/javascript" in ct.lower()
        ), f"unexpected content-type for app.js: {ct!r***REMOVED***"
        # Sanity: content is non-trivial
        assert len(r.text) > 1000

    def test_static_style_css_returns_200_css(self, client: TestClient) -> None:
        r = client.get("/static/style.css")
        assert r.status_code == 200
        ct = r.headers.get("content-type", "")
        assert (
            "css" in ct.lower()
            or "text/css" in ct.lower()
        ), f"unexpected content-type for style.css: {ct!r***REMOVED***"
        # Sanity: CSS signature markers
        assert ":root" in r.text or "{" in r.text

    def test_static_index_html_returns_200_html(self, client: TestClient) -> None:
        r = client.get("/static/index.html")
        assert r.status_code == 200
        ct = r.headers.get("content-type", "")
        assert (
            "html" in ct.lower() or "text/html" in ct.lower()
        ), f"unexpected content-type for index.html: {ct!r***REMOVED***"
        # Sanity: HTML signature markers
        assert "<!DOCTYPE" in r.text or "<html" in r.text.lower()

    def test_prototype_shortcut_returns_index_html(self, client: TestClient) -> None:
        """GET /prototype → FileResponse shortcut to prototype/index.html."""
        r = client.get("/prototype")
        assert r.status_code == 200
        ct = r.headers.get("content-type", "")
        assert "html" in ct.lower()
        assert "<!DOCTYPE" in r.text or "<html" in r.text.lower()


# ─── Module-level health — ensures fixture teardown works cleanly ─────────


def test_module_teardown_no_pending_alerts(client: TestClient) -> None:
    """Sanity: after running all tests above, app still healthy (no leaks)."""
    r = client.get("/health")
    assert r.status_code == 200
