"""
test_forge_chain_real_integration.py — v5.166.0

Real integration smoke test для `forge chain` CLI на demo-проектах платформы.

Цель: зафиксировать РЕАЛЬНУЮ стоимость chain ×14 ролей на demo-проектах
(vkusvill_demo + interior_planner + vkusvill_research), закрывает FWD-1 +
FWD-2 из v5.158/v5.161/v5.162 OPEN_QUESTIONS.

Запускает `python scripts_01/forge.py chain <project> [--resume***REMOVED*** --json`
через subprocess.run, парсит JSON output, asserts на:
- exit code == 0
- JSON parse passes (well-formed)
- 9 schema keys присутствуют: project_id, project_root, stage_count,
  chain, overall, started_at, finished_at, validation_registry_status,
  validation_summary
- chain length >= 1 (in practice == 14 per PIPELINE_CHAIN)
- statuses ∈ {ok, run_ok, missing, run_failed, partial, skipped, init_error***REMOVED***
- project_id matches directory stem (case-insensitive, hyphen/underscore agnostic)
- duration < 90s per subprocess invocation (CI budget)
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
***REMOVED***

import pytest

# v5.170.0: PIPELINE_CHAIN импортирован для dynamic semantic проверки resume
# (тест test_chain_partial_resume_continues_from_last_ok вычисляет expected
# remaining roles относительно PIPELINE_CHAIN.index(last_ok) + 1).
from core_02.forge_facade import PIPELINE_CHAIN  # noqa: E402

# v5.189.11: весь файл — real-subprocess интеграция (forge chain на 3 demo-проектах,
# ~78s на прогон). Маркируем slow, чтобы полный прогон мог деселектить через
# `-m "not slow"`. Маркер зарегистрирован в pytest.ini.
# v5.189.12 (xdist race fix): group с test_forge_api/test_forge_chain_cli — все
# три пишут/читают реальный data_13/forge_registry.yaml (vkusvill-demo); под
# --dist loadgroup они идут на одном воркере последовательно.
pytestmark = [
    pytest.mark.slow,
    pytest.mark.xdist_group("forge_real_registry"),
***REMOVED***

# Project root = repo root (parent of tests_09/)
REPO_ROOT = Path(__file__).resolve().parent.parent
FORGE_CLI = REPO_ROOT / "scripts_01" / "forge.py"
VKUSVILL_DEMO = REPO_ROOT / "projects_17" / "vkusvill_demo"
INTERIOR_PLANNER = REPO_ROOT / "projects_17" / "interior_planner"
# v5.166.0: originally-specified FWD-1 target project (vkusvill_research).
# Note: project_id in registry = 'vkusvill-research' (HYPHEN form), даже though
# directory name uses underscore. Helper `_matches_project_id` нормализует.
VKUSVILL_RESEARCH = REPO_ROOT / "projects_17" / "vkusvill_research"

# Subprocess budget per chain invocation (CI-friendly)
SUBPROCESS_TIMEOUT_S = 90

# Expected JSON schema (canonical from v5.164.0 pre-flight):
# forge.py chain --json emits exactly these 9 top-level keys.
EXPECTED_JSON_KEYS = {
    "project_id",
    "project_root",
    "stage_count",
    "chain",
    "overall",
    "started_at",
    "finished_at",
    "validation_registry_status",
    "validation_summary",
***REMOVED***

# Status whitelist (per ForgeFacade.run_chain semantics).
ALLOWED_STATUSES = frozenset({
    "ok",
    "run_ok",
    "missing",
    "run_failed",
    "partial",
    "skipped",
    "init_error",
***REMOVED***)


def _project_id_canonical(directory: Path) -> str:
    """Normalize directory stem to canonical project_id form.

    Project directories can use either underscore (`vkusvill_demo`) or hyphen
    (`vkusvill-research`) in their names; registry.yaml may declare either form
    as canonical `project_id`. This helper introduces a single tolerance band:
    lowercase + unified separators (all hyphens treated as underscores).

    Example:
        interior_planner/  -> "interior_planner"
        interior-planner/  -> "interior_planner"
        vkusvill_demo/     -> "vkusvill_demo"
        vkusvill-research/ -> "vkusvill_research"
    """
    return directory.name.lower().replace("-", "_")


def _matches_project_id(declared: str, expected_dir: Path) -> bool:
    """Return True if `declared` project_id matches `expected_dir` stem form."""
    return _project_id_canonical(expected_dir) == _project_id_canonical(
        Path(declared)
    )


def _run_chain(
    project_path: Path,
    *,
    resume: bool = False,
    timeout_s: int = SUBPROCESS_TIMEOUT_S,
) -> subprocess.CompletedProcess:
    """Run `python scripts_01/forge.py chain <project> [--resume***REMOVED*** --json`.

    Returns CompletedProcess with stdout (JSON) + stderr + returncode.
    """
    cmd = [
        sys.executable,
        str(FORGE_CLI),
        "chain",
        str(project_path),
        "--json",
    ***REMOVED***
    if resume:
        cmd.append("--resume")

    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )


def _parse_chain_json(result: subprocess.CompletedProcess) -> dict:
    """Parse chain --json output. Handles optional informational preamble.

    `forge.py chain --resume` prints a diagnostical line in STDOUT BEFORE the
    JSON payload when there is no prior ok/run_ok в registry.last_pipeline
    (e.g. first-run project), вида:
        "  [resume***REMOVED*** нет prior ok/run_ok в last_pipeline; running from scratch\n"
    Such preamble breaks strict `json.loads(stdout)`, поэтому мы находим first
    JSON delimiter ("{" или "[") и slice stdout оттуда.
    """
    stdout = result.stdout
    # Find first '{' — JSON object delimiter — to skip any informational
    # preamble that forge.py may emit to stdout (e.g. --resume diagnostic
    # message prefixed with "[resume***REMOVED*** ...").
    #
    # IMPORTANT: do NOT also look for '['! Such a scan would falsely match
    # the leading '[' of the "[resume***REMOVED*** ..." preamble text itself, returning
    # a position BEFORE the actual JSON object opens (after '\n{'). Verified
    # in v5.164.0 third fix-up iteration: `find('[')` returned position of
    # `[resume***REMOVED***` bracket, slice returned preamble string, JSONDecodeError.
    #
    # We rely on object shape since forge.py chain --json always emits a
    # JSON object (not array) — confirmed by 9-key schema pre-flight.
    json_start = stdout.find("{")
    if json_start < 0:
        pytest.fail(
            f"No JSON object found in forge.py chain --json stdout:\n"
            f"  exitcode={result.returncode***REMOVED***\n"
            f"  stdout={stdout[:500***REMOVED***!r***REMOVED***\n"
            f"  stderr={result.stderr[:500***REMOVED***!r***REMOVED***"
        )
    json_payload = stdout[json_start:***REMOVED***
    try:
        return json.loads(json_payload)
    except json.JSONDecodeError as exc:
        pytest.fail(
            f"Malformed JSON stdout from forge.py chain --json:\n"
            f"  exitcode={result.returncode***REMOVED***\n"
            f"  json_start_offset={json_start***REMOVED***\n"
            f"  payload_first300={json_payload[:300***REMOVED***!r***REMOVED***\n"
            f"  stderr_first200={result.stderr[:200***REMOVED***!r***REMOVED***\n"
            f"  json_error={exc!r***REMOVED***"
        )


def _ensure_preconditions() -> None:
    if not FORGE_CLI.exists():
        pytest.skip(f"forge CLI not found at {FORGE_CLI***REMOVED***")
    if not VKUSVILL_DEMO.exists():
        pytest.skip(f"vkusvill_demo project missing at {VKUSVILL_DEMO***REMOVED***")
    if not INTERIOR_PLANNER.exists():
        pytest.skip(f"interior_planner project missing at {INTERIOR_PLANNER***REMOVED***")
    # v5.166.0: also verify vkusvill_research (originally-specified FWD-1 target).
    if not VKUSVILL_RESEARCH.exists():
        pytest.skip(f"vkusvill_research project missing at {VKUSVILL_RESEARCH***REMOVED***")


# Session-scoped autouse fixture: runs once at module setup to verify all
# required demo projects + forge CLI are available. Skips module if any missing.
@pytest.fixture(scope="session", autouse=True)
def _ensure_preconditions_session() -> None:
    _ensure_preconditions()


# ---------------------------------------------------------------------------
# Fixture: shared subprocess invocation cache (1× per module run, pytest-scoped)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def vkusvill_first_run() -> dict:
    """First-run subprocess for vkusvill_demo (no --resume). JSON-decoded."""
    result = _run_chain(VKUSVILL_DEMO, resume=False)
    assert result.returncode == 0, (
        f"forge chain exited {result.returncode***REMOVED*** on vkusvill_demo first-run:\n"
        f"  stdout={result.stdout[:300***REMOVED***!r***REMOVED***\n"
        f"  stderr={result.stderr[:300***REMOVED***!r***REMOVED***"
    )
    return _parse_chain_json(result)


@pytest.fixture(scope="module")
def vkusvill_resume_run(vkusvill_first_run: dict) -> dict:
    """--resume subprocess for vkusvill_demo. JSON-decoded.

    Семантика v5.162.0: на first-run проекте (no prior chain) --resume falls
    back к полному PIPELINE_CHAIN. Поэтому expected chain len == first-run.

    v5.170.0 (CR MUST-FIX): declares `vkusvill_first_run` as pytest fixture
    param dependency → pytest MUST evaluate first-run BEFORE resume-run,
    eliminates ordering flakiness for partial-resume semantic test.
    """
    result = _run_chain(VKUSVILL_DEMO, resume=True)
    assert result.returncode == 0, (
        f"forge chain --resume exited {result.returncode***REMOVED***:\n"
        f"  stdout={result.stdout[:300***REMOVED***!r***REMOVED***\n"
        f"  stderr={result.stderr[:300***REMOVED***!r***REMOVED***"
    )
    return _parse_chain_json(result)


@pytest.fixture(scope="module")
def interior_first_run() -> dict:
    """First-run subprocess for interior_planner (no --resume)."""
    result = _run_chain(INTERIOR_PLANNER, resume=False)
    assert result.returncode == 0, (
        f"forge chain exited {result.returncode***REMOVED*** on interior_planner first-run:\n"
        f"  stdout={result.stdout[:300***REMOVED***!r***REMOVED***\n"
        f"  stderr={result.stderr[:300***REMOVED***!r***REMOVED***"
    )
    return _parse_chain_json(result)


@pytest.fixture(scope="module")
def vkusvill_research_first_run() -> dict:
    """First-run subprocess for vkusvill_research (no --resume, originally-specified FWD-1 target)."""
    result = _run_chain(VKUSVILL_RESEARCH, resume=False)
    assert result.returncode == 0, (
        f"forge chain exited {result.returncode***REMOVED*** on vkusvill_research first-run:\n"
        f"  stdout={result.stdout[:300***REMOVED***!r***REMOVED***\n"
        f"  stderr={result.stderr[:300***REMOVED***!r***REMOVED***"
    )
    return _parse_chain_json(result)


@pytest.fixture(scope="module")
def vkusvill_research_resume_run(vkusvill_research_first_run: dict) -> dict:
    """--resume subprocess for vkusvill_research (originally-specified FWD-1 target).

    v5.170.0 (CR MUST-FIX, proactive): declares `vkusvill_research_first_run`
    as pytest fixture param dependency (same reason as vkusvill_resume_run).
    """
    result = _run_chain(VKUSVILL_RESEARCH, resume=True)
    assert result.returncode == 0, (
        f"forge chain --resume exited {result.returncode***REMOVED*** on vkusvill_research:\n"
        f"  stdout={result.stdout[:300***REMOVED***!r***REMOVED***\n"
        f"  stderr={result.stderr[:300***REMOVED***!r***REMOVED***"
    )
    return _parse_chain_json(result)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRealChainIntegration:
    """Real subprocess integration smoke для forge.py chain на demo проектах."""

    def test_vkusvill_demo_first_run_emits_well_formed_json(
        self, vkusvill_first_run: dict,
    ) -> None:
        """vkusvill_demo first-run: --json output parseable + schema-correct."""
        data = vkusvill_first_run

        missing_keys = EXPECTED_JSON_KEYS - set(data.keys())
        assert not missing_keys, (
            f"vkusvill_demo first-run JSON missing keys: {sorted(missing_keys)***REMOVED***"
        )

        chain = data.get("chain") or [***REMOVED***
        assert len(chain) >= 1, (
            f"vkusvill_demo first-run chain empty: {chain!r***REMOVED***"
        )

        statuses = Counter(r.get("status", "?") for r in chain)
        invalid = set(statuses.keys()) - ALLOWED_STATUSES
        assert not invalid, (
            f"vkusvill_demo first-run has invalid statuses: {invalid***REMOVED***\n"
            f"  full_counter={dict(statuses)***REMOVED***"
        )

        # Project identification: tolerate hyphen/underscore variant (registry.yaml
        # может объявлять `vkusvill-demo` или `vkusvill_demo` — обе OK).
        assert _matches_project_id(data["project_id"***REMOVED***, VKUSVILL_DEMO), (
            f"vkusvill_demo project_id mismatch: {data['project_id'***REMOVED***!r***REMOVED*** "
            f"(directory stem={VKUSVILL_DEMO.name!r***REMOVED***)"
        )

        assert data["stage_count"***REMOVED*** == len(chain), (
            f"vkusvill_demo stage_count={data['stage_count'***REMOVED******REMOVED*** != "
            f"len(chain)={len(chain)***REMOVED***"
        )

    def test_vkusvill_demo_resume_emits_well_formed_json(
        self,
        vkusvill_resume_run: dict,
        vkusvill_first_run: dict,
    ) -> None:
        """--resume после первого прогона → валидный JSON + subset-or-equal chain.

        v5.189.6 (FWD-1 bugfix): после того как cmd_chain начал персистить
        ChainRun в registry, --resume продолжает с курсора (partial), а НЕ
        full fallback. Инвариант: resume не превышает full chain
        (stage_count <= first) и не коллапсирует к пустой цепочке.
        Детальная проверка «continue from LAST ok» — в
        test_chain_partial_resume_continues_from_last_ok.
        """
        data_resume = vkusvill_resume_run
        data_first = vkusvill_first_run

        chain = data_resume.get("chain") or [***REMOVED***
        assert len(chain) >= 1, (
            f"--resume on vkusvill_demo collapsed to empty chain: {chain!r***REMOVED***"
        )

        # Schema correctness (same as first-run)
        missing_keys = EXPECTED_JSON_KEYS - set(data_resume.keys())
        assert not missing_keys, (
            f"--resume JSON missing keys: {sorted(missing_keys)***REMOVED***"
        )

        # Resume is a subset-or-equal of the full chain (partial continuation
        # after FWD-1 bugfix; full fallback only when no prior ok/run_ok).
        assert data_resume["stage_count"***REMOVED*** <= data_first["stage_count"***REMOVED***, (
            f"--resume produced MORE stages than first-run: "
            f"stage_count_resume={data_resume['stage_count'***REMOVED******REMOVED*** > "
            f"stage_count_first={data_first['stage_count'***REMOVED******REMOVED*** "
            f"(resume must be a subset-or-equal of the full chain)"
        )

    def test_interior_planner_first_run_emits_well_formed_json(
        self, interior_first_run: dict,
    ) -> None:
        """interior_planner first-run: JSON parseable + schema-correct."""
        data = interior_first_run

        missing_keys = EXPECTED_JSON_KEYS - set(data.keys())
        assert not missing_keys, (
            f"interior_planner first-run JSON missing keys: {sorted(missing_keys)***REMOVED***"
        )

        chain = data.get("chain") or [***REMOVED***
        assert len(chain) >= 1, (
            f"interior_planner first-run chain empty: {chain!r***REMOVED***"
        )

        statuses = Counter(r.get("status", "?") for r in chain)
        invalid = set(statuses.keys()) - ALLOWED_STATUSES
        assert not invalid, (
            f"interior_planner first-run has invalid statuses: {invalid***REMOVED***\n"
            f"  full_counter={dict(statuses)***REMOVED***"
        )

        # Project identification (interior_planner directory stem vs registry name).
        assert _matches_project_id(data["project_id"***REMOVED***, INTERIOR_PLANNER), (
            f"interior_planner project_id mismatch: {data['project_id'***REMOVED***!r***REMOVED*** "
            f"(directory stem={INTERIOR_PLANNER.name!r***REMOVED***)"
        )

        assert data["stage_count"***REMOVED*** == len(chain), (
            f"interior_planner stage_count={data['stage_count'***REMOVED******REMOVED*** != "
            f"len(chain)={len(chain)***REMOVED***"
        )

    def test_vkusvill_research_first_run_emits_well_formed_json(
        self, vkusvill_research_first_run: dict,
    ) -> None:
        """vkusvill_research first-run (FWD-1 originally-specified target).

        project_id объявляется registry как `vkusvill-research` (HYPHEN form),
        directory name = `vkusvill_research` (UNDERSCORE form). Helper
        `_matches_project_id` корректно нормализует оба варианта → unify.
        """
        data = vkusvill_research_first_run

        missing_keys = EXPECTED_JSON_KEYS - set(data.keys())
        assert not missing_keys, (
            f"vkusvill_research first-run JSON missing keys: {sorted(missing_keys)***REMOVED***"
        )

        chain = data.get("chain") or [***REMOVED***
        assert len(chain) >= 1, (
            f"vkusvill_research first-run chain empty: {chain!r***REMOVED***"
        )

        statuses = Counter(r.get("status", "?") for r in chain)
        invalid = set(statuses.keys()) - ALLOWED_STATUSES
        assert not invalid, (
            f"vkusvill_research first-run has invalid statuses: {invalid***REMOVED***\n"
            f"  full_counter={dict(statuses)***REMOVED***"
        )

        # Project identification (HYPHEN/UNDERSCORE agnostic).
        assert _matches_project_id(data["project_id"***REMOVED***, VKUSVILL_RESEARCH), (
            f"vkusvill_research project_id mismatch: {data['project_id'***REMOVED***!r***REMOVED*** "
            f"(directory stem={VKUSVILL_RESEARCH.name!r***REMOVED***)"
        )

        assert data["stage_count"***REMOVED*** == len(chain), (
            f"vkusvill_research stage_count={data['stage_count'***REMOVED******REMOVED*** != "
            f"len(chain)={len(chain)***REMOVED***"
        )

    def test_vkusvill_research_resume_emits_well_formed_json(
        self,
        vkusvill_research_resume_run: dict,
        vkusvill_research_first_run: dict,
    ) -> None:
        """--resume после первого прогона vkusvill_research → subset-or-equal chain.

        v5.189.6 (FWD-1 bugfix): partial continuation вместо full fallback.
        """
        data_resume = vkusvill_research_resume_run
        data_first = vkusvill_research_first_run

        chain = data_resume.get("chain") or [***REMOVED***
        assert len(chain) >= 1, (
            f"--resume on vkusvill_research collapsed: {chain!r***REMOVED***"
        )

        missing_keys = EXPECTED_JSON_KEYS - set(data_resume.keys())
        assert not missing_keys, (
            f"vkusvill_research --resume JSON missing keys: {sorted(missing_keys)***REMOVED***"
        )

        # Resume is a subset-or-equal of the full chain (partial continuation).
        assert data_resume["stage_count"***REMOVED*** <= data_first["stage_count"***REMOVED***, (
            f"vkusvill_research --resume produced MORE stages than first-run: "
            f"stage_count_resume={data_resume['stage_count'***REMOVED******REMOVED*** > "
            f"stage_count_first={data_first['stage_count'***REMOVED******REMOVED***"
        )

    def test_all_three_projects_share_canonical_schema(
        self,
        vkusvill_first_run: dict,
        interior_first_run: dict,
        vkusvill_research_first_run: dict,
    ) -> None:
        """Все 3 demo проекта возвращают identical top-level JSON schema.

        v5.166.0: схема drift между проектами → first natural indicator
        (расширен test_both_projects → test_all_three_projects).
        """
        vk_keys = set(vkusvill_first_run.keys())
        ip_keys = set(interior_first_run.keys())
        vr_keys = set(vkusvill_research_first_run.keys())

        assert vk_keys == ip_keys == vr_keys, (
            f"canonical schema divergence:\n"
            f"  vkusvill_demo={sorted(vk_keys)***REMOVED***\n"
            f"  interior_planner={sorted(ip_keys)***REMOVED***\n"
            f"  vkusvill_research={sorted(vr_keys)***REMOVED***\n"
            f"  diff_vk_minus_ip={sorted(vk_keys - ip_keys)***REMOVED***\n"
            f"  diff_ip_minus_vk={sorted(ip_keys - vk_keys)***REMOVED***\n"
            f"  diff_vr={sorted(vr_keys ^ (vk_keys | ip_keys))***REMOVED***"
        )

        # All 3 supersets of EXPECTED_JSON_KEYS.
        for name, keys in (
            ("vkusvill_demo", vk_keys),
            ("interior_planner", ip_keys),
            ("vkusvill_research", vr_keys),
        ):
            assert EXPECTED_JSON_KEYS <= keys, (
                f"{name***REMOVED*** schema missing core keys: "
                f"{sorted(EXPECTED_JSON_KEYS - keys)***REMOVED***"
            )

    def test_chain_partial_resume_continues_from_last_ok(
        self,
        vkusvill_first_run: dict,
        vkusvill_resume_run: dict,
    ) -> None:
        """Two-step semantic: forge chain TWICE with REGISTERED PARTIAL STATE.

        Sequence:
          1. `vkusvill_first_run` (forge chain vkusvill_demo) → JSON N stages,
             registry.last_pipeline['chain'***REMOVED*** populated with statuses.
          2. `vkusvill_resume_run` (forge chain vkusvill_demo --resume) → CLI
             reads registry.last_pipeline['chain'***REMOVED***, ищет LAST stage со status
             ∈ {\"ok\", \"run_ok\"***REMOVED*** (v5.162.0 FWD-1), вычисляет remaining =
             PIPELINE_CHAIN[last_ok_idx+1:***REMOVED*** и facade.run_chain(role_ids=remaining).

        Assert: resume JSON stage_count == len(remaining) И first stage role_id
        == expected_remaining[0***REMOVED*** (semantic continuity check).

        Если first run НЕ содержит ни одной ok/run_ok стадии (все missing /
        partial / failed / skipped) → resume должен full-fallback к полному
        PIPELINE_CHAIN (per `--resume фaлбэк семантикa v5.162.0/fallback behavior
        в second fallback branch of resume-logic). Этот случай тоже asserted
        через alias-сравнение `resume.stage_count == first.stage_count`.
        """
        from core_02.forge_facade import PIPELINE_CHAIN as _PC_RUN

        data_first = vkusvill_first_run
        data_resume = vkusvill_resume_run

        # Step 1: scan first run's chain В ОБРАТНОМ порядке — LAST ok/run_ok роль.
        # resume logic в forge.py cmd_chain делает то же самое (reversed iter),
        # так что test couples точно с production logic.
        last_ok_role_id: Optional[str***REMOVED*** = None
        last_ok_position_in_chain = None
        for idx_from_end, stage in enumerate(reversed(data_first["chain"***REMOVED***)):
            status = stage.get("status", "")
            if status in ("ok", "run_ok"):
                last_ok_role_id = stage.get("role_id")
                last_ok_position_in_chain = (
                    len(data_first["chain"***REMOVED***) - 1 - idx_from_end
                )
                break

        if last_ok_role_id is None:
            # ── Fallback path: ни одной completion-стадии в first run ─────────
            # resume logic падает в fallback (running from scratch) → resume
            # output должен иметь ту же длину chain, что и first.
            assert data_resume["stage_count"***REMOVED*** == data_first["stage_count"***REMOVED***, (
                f"No ok/run_ok в first run → expected resume full fallback "
                f"(running from scratch); but stage_count mismatch: "
                f"resume={data_resume['stage_count'***REMOVED******REMOVED*** != "
                f"first={data_first['stage_count'***REMOVED******REMOVED*** "
                f"(first run statuses="
                f"{Counter(r.get('status', '?') for r in data_first['chain'***REMOVED***)***REMOVED***)"
            )
            # Sanity: resume не должен collapsed к empty chain.
            assert data_resume["stage_count"***REMOVED*** >= 1, (
                f"Resume fallback collapsed to empty chain: "
                f"{data_resume.get('chain', [***REMOVED***)!r***REMOVED***"
            )
        else:
            # ── Partial semantic path: --resume picks LAST ok role ────────────
            # remaining = PIPELINE_CHAIN[last_ok_index_in_pipeline + 1:***REMOVED***
            try:
                last_ok_idx_in_pipeline = _PC_RUN.index(last_ok_role_id)
            except ValueError:
                pytest.fail(
                    f"last_ok_role_id={last_ok_role_id!r***REMOVED*** not found in "
                    f"PIPELINE_CHAIN ({list(_PC_RUN)***REMOVED***); "
                    f"resume logic should have rejected this scenario"
                )
            expected_remaining: tuple[str, ...***REMOVED*** = (
                _PC_RUN[last_ok_idx_in_pipeline + 1:***REMOVED***
            )
            expected_stage_count = len(expected_remaining)

            # PRIME ASSERTION: resume JSON stage_count == len(remaining)
            # Это confirms facade.run_chain получил role_ids = expected_remaining
            # (CLI маршалит --resume semantic в facade.run_chain correctly).
            assert data_resume["stage_count"***REMOVED*** == expected_stage_count, (
                f"--resume did NOT continue from LAST ok={last_ok_role_id!r***REMOVED*** "
                f"(PIPELINE_CHAIN idx={last_ok_idx_in_pipeline***REMOVED***/{len(_PC_RUN)-1***REMOVED***): "
                f"resume.stage_count={data_resume['stage_count'***REMOVED******REMOVED*** != "
                f"expected={expected_stage_count***REMOVED*** (remaining={expected_remaining***REMOVED***) "
                f"first.run.last_ok at chain position "
                f"{last_ok_position_in_chain***REMOVED***/{len(data_first['chain'***REMOVED***)***REMOVED***"
            )

            # Secondary assertion (semantic continuity): если есть remaining,
            # first stage of resume должен == expected_remaining[0***REMOVED***.
            if expected_remaining:
                resume_first_role_id = (
                    data_resume["chain"***REMOVED***[0***REMOVED***["role_id"***REMOVED***
                )
                assert resume_first_role_id == expected_remaining[0***REMOVED***, (
                    f"Resume first stage role continuity broken: "
                    f"{resume_first_role_id!r***REMOVED*** != expected "
                    f"{expected_remaining[0***REMOVED***!r***REMOVED*** "
                    f"(after LAST ok={last_ok_role_id!r***REMOVED***)"
                )

            # Tertiary invariant: resume всегда ≤ first (resume не добавляет
            # новые роли, только продолжает existing chain).
            assert data_resume["stage_count"***REMOVED*** <= data_first["stage_count"***REMOVED***, (
                f"Resume produced MORE stages than first run: "
                f"resume={data_resume['stage_count'***REMOVED******REMOVED*** > "
                f"first={data_first['stage_count'***REMOVED******REMOVED*** "
                f"(semantic violation: partial should be subset)"
            )
