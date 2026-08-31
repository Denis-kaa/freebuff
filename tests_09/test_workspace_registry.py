"""Tests for core_02/workspace_registry.py.

Covers Phase 5.4-OQ26-31 prototype:
- 3 default workspaces seeded idempotently
- workspace \u2194 projects mapping correctness
- privacy isolation guard (path belongs to AT MOST ONE workspace)

Tests use `tmp_path` fixtures + absolute paths to avoid CWD-relativity bugs
(see code-reviewer-minimax-m3 bugfix #1 in this iteration).
"""
from __future__ import annotations

import sys
import logging
from unittest.mock import patch

import pytest

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

from core_02.workspace_registry import (  # noqa: E402
    PrivacyViolationError,
    Workspace,
    WorkspaceRegistry,
    _slugify_name,
    get_default_registry,
)


# ── Fixtures ──


@pytest.fixture
def projects_root(tmp_path: Path) -> Path:
    """Stub projects_17/ tree with all 5 user-mapped subdirs (relative to tmp_path)."""
    root = tmp_path / "projects_17"
    root.mkdir(parents=True, exist_ok=True)
    for sub in (
        "interior_planner",
        "tg_terminal_messenger",
        "buffy-playground_19",
        "freebuff_flutter_app",
        "diet_platform",
    ):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def tmp_registry(tmp_path: Path) -> WorkspaceRegistry:
    """Registry backed by a fresh tmp database file (does NOT pollute real data_13/).

    Note (CAN-14): this fixture MUST NOT request `projects_root` (hidden dependency).
    If it did, pytest would auto-create the 5 default subdirs and `result.missing`
    in `seed_defaults` would always be empty (defeats test purpose). Tests that
    need the 5 subdirs should request `projects_root` explicitly.

    seed_defaults принимает `workspace_root` для relative-path resolution,
    иначе DEFAULT_WORKSPACES paths=['projects_17/X'] резолвятся в CWD-freebuff/.
    """
    db_path = tmp_path / "workspace_registry_test.db"
    return WorkspaceRegistry(db_path)


@pytest.fixture
def seeded_registry(
    tmp_registry: WorkspaceRegistry, projects_root: Path, tmp_path: Path
) -> WorkspaceRegistry:
    """Registry с 3 default workspaces уже seeded (CAN-14 explicit projects_root).

    IMPORTANT (CAN-14): this fixture explicitly requests `projects_root` so pytest
    creates the 5 subdirs BEFORE seed_defaults runs. Without this, the cascade
    breakage happens: tmp_registry no longer requests projects_root (severed in
    earlier fix), so seeded_registry would also lose the pre-creation.
    """
    tmp_registry.seed_defaults(workspace_root=tmp_path)
    return tmp_registry


def _p(tmp_path: Path, sub: str) -> str:
    """Helper: absolute path string для projects_17/<sub> относительно tmp_path."""
    return str((tmp_path / "projects_17" / sub).resolve())


# ── slug helper ──


def test_slugify_cyrillic_to_latin() -> None:
    assert _slugify_name("\u0420\u0430\u0431\u043e\u0442\u0430") == "rabota"
    # Учёба transliterates: у → u, ч → “ch”, ё → “yo”, б → b, а → a = “uchyo b a” → “uchyoba”
    assert _slugify_name("\u0423\u0447\u0451\u0431\u0430") == "uchyoba"
    assert _slugify_name("\u0425\u043e\u0431\u0431\u0438") == "hobbi"
    assert _slugify_name("My Project") == "my_project"


def test_slugify_collapses_multiple_underscores() -> None:
    assert _slugify_name("a  b") == "a_b"
    assert _slugify_name("a..b") == "a_b"
    # After strip and collapse, no triple underscores
    assert "___" not in _slugify_name("___")


def test_slugify_unknown_chars_pass_through() -> None:
    # If a non-Cyrillic non-Latin char looks through, it's kept as lowercase.
    assert _slugify_name("Project-42") == "project_42"


# ── seeding ──


def test_three_default_workspaces_seeded(
    seeded_registry: WorkspaceRegistry, tmp_path: Path
) -> None:
    """init + seed_defaults yields 3 workspaces with project mappings."""
    workspaces = seeded_registry.list_workspaces()
    slugs = sorted(ws.slug for ws in workspaces)
    assert slugs == ["hobbi", "rabota", "uchyoba"]
    paths_by_slug = {ws.slug: ws.project_paths for ws in workspaces}

    # Работа binding — absolute paths
    rabota_paths = sorted(Path(p).name for p in paths_by_slug["rabota"])
    assert rabota_paths == ["interior_planner", "tg_terminal_messenger"]

    # Учёба binding
    assert len(paths_by_slug["uchyoba"]) == 1
    assert Path(paths_by_slug["uchyoba"][0]).name == "buffy-playground_19"

    # Хобби binding
    hobbi_paths = sorted(Path(p).name for p in paths_by_slug["hobbi"])
    assert hobbi_paths == ["diet_platform", "freebuff_flutter_app"]


def test_seed_defaults_is_idempotent(tmp_registry: WorkspaceRegistry, tmp_path: Path) -> None:
    """Calling seed_defaults twice produces 3 workspaces (not 6) — CAN-14 structured return."""
    from core_02.workspace_registry import SeedResult
    first = tmp_registry.seed_defaults(workspace_root=tmp_path)
    second = tmp_registry.seed_defaults(workspace_root=tmp_path)
    # Return type changed from int → SeedResult (CAN-14 fail-loud).
    assert isinstance(first, SeedResult)
    assert isinstance(second, SeedResult)
    assert first.created == 3
    assert second.created == 0  # idempotent re-seed adds 0 new workspaces
    # Second run: missing paths list is identical (still missing on FS).
    assert first.missing == second.missing
    assert len(tmp_registry.list_workspaces()) == 3


def test_seed_defaults_skips_missing_paths(tmp_path: Path) -> None:
    """Missing projects_17/ subdirs are skipped (not fatal) + reported in SeedResult.missing."""
    from core_02.workspace_registry import SeedResult
    projects_root = tmp_path / "projects_17"
    projects_root.mkdir(parents=True, exist_ok=True)
    # Only create 2 of the 5 default paths
    (projects_root / "interior_planner").mkdir(parents=True, exist_ok=True)
    (projects_root / "tg_terminal_messenger").mkdir(parents=True, exist_ok=True)
    reg = WorkspaceRegistry(tmp_path / "ws.db")
    result = reg.seed_defaults(workspace_root=tmp_path)
    # CAN-14: 3 workspaces seeded despite missing paths; .missing carries full FS gap report.
    assert isinstance(result, SeedResult)
    assert result.created == 3
    # 3 paths missing on FS: buffy-playground_19, freebuff_flutter_app, diet_platform.
    assert len(result.missing) == 3
    missing_names = sorted(Path(p).name for p in result.missing)
    assert missing_names == ["buffy-playground_19", "diet_platform", "freebuff_flutter_app"]
    # Workspaces are still inserted (idempotency-friendly) but only existing paths bound.
    slugs = sorted(ws.slug for ws in reg.list_workspaces())
    assert slugs == ["hobbi", "rabota", "uchyoba"]
    rabota_paths = [Path(p).name for p in reg.list_projects("rabota")]
    assert sorted(rabota_paths) == ["interior_planner", "tg_terminal_messenger"]
    # Учёба has NO bound paths (buffy-playground_19 missing)
    assert reg.list_projects("uchyoba") == []
    # Хобби has NO bound paths (both diet_platform + freebuff_flutter_app missing)
    assert reg.list_projects("hobbi") == []


def test_seed_defaults_uses_workspace_root_relative_paths(tmp_path: Path) -> None:
    """Переданный workspace_root корректно резолвит relative pathов.

    Bugfix #1: pytest CWD != freebuff project root, поэтому seed_defaults нужно
    явно передавать workspace_root.
    """
    reg = WorkspaceRegistry(tmp_path / "ws.db")
    reg.seed_defaults(workspace_root=tmp_path)
    # All 5 paths stored as absolute resolved paths (canonical form)
    all_paths = []
    for ws in reg.list_workspaces():
        all_paths.extend(ws.project_paths)
    # Every stored path is absolute
    assert all(Path(p).is_absolute() for p in all_paths)
    # They all live under tmp_path/projects_17/
    assert all(
        str(p).startswith(str(tmp_path / "projects_17")) for p in all_paths
    )


# ── privacy isolation — core guard ──


def test_workspace_slug_collision_detection_raises(
    seeded_registry: WorkspaceRegistry, tmp_path: Path
) -> None:
    """Adding projects_17/interior_planner to Учёба → PrivacyViolationError."""
    target = _p(tmp_path, "interior_planner")
    with pytest.raises(PrivacyViolationError) as exc_info:
        seeded_registry.add_project("uchyoba", target)
    assert exc_info.value.path == target
    assert exc_info.value.expected_slug == "uchyoba"
    assert exc_info.value.actual_slug == "rabota"


def test_add_project_to_same_workspace_is_idempotent(
    seeded_registry: WorkspaceRegistry, tmp_path: Path
) -> None:
    """Adding same absolute path to its OWNER workspace is a no-op (no error)."""
    target = _p(tmp_path, "interior_planner")
    seeded_registry.add_project("rabota", target)  # double-bind OK
    assert len(seeded_registry.list_projects("rabota")) == 2


def test_list_projects_isolated_per_workspace(
    seeded_registry: WorkspaceRegistry, tmp_path: Path
) -> None:
    """list_projects(rabota) MUST NOT contain buffy-playground_19 (which is in Учёба)."""
    rabota_paths = seeded_registry.list_projects("rabota")
    assert all("buffy" not in Path(p).name for p in rabota_paths), (
        "rabota workspace leaked Учёба's buffy-playground_19: %s" % rabota_paths
    )
    ucheba_paths = seeded_registry.list_projects("uchyoba")
    assert all(
        "interior_planner" not in Path(p).name for p in ucheba_paths
    ), "uchyoba leaked rabota's interior_planner: %s" % ucheba_paths


def test_add_project_missing_path_warns_no_raise(
    seeded_registry: WorkspaceRegistry, tmp_path: Path
) -> None:
    """FS-validation в add_project (CON-21 anti-fragility, RTX-default): missing path → return False."""
    ghost = str(tmp_path / "projects_17" / "ghost_project")
    # RTX-default behavior: warn-and-skip, returns False (CAN-14 fail-loud soft).
    result = seeded_registry.add_project("rabota", ghost)
    assert result is False
    # No projects added since path doesn't exist
    assert len(seeded_registry.list_projects("rabota")) == 2  # seeded default count


# ── find_workspace_for_project — reverse lookup ──


def test_find_workspace_for_project_returns_owner(
    seeded_registry: WorkspaceRegistry, tmp_path: Path
) -> None:
    ws = seeded_registry.find_workspace_for_project(_p(tmp_path, "interior_planner"))
    assert ws is not None
    assert ws.slug == "rabota"
    assert ws.name == "\u0420\u0430\u0431\u043e\u0442\u0430"


def test_find_workspace_for_unregistered_path_returns_none(
    seeded_registry: WorkspaceRegistry, tmp_path: Path
) -> None:
    ws = seeded_registry.find_workspace_for_project(
        _p(tmp_path, "ghost_project")
    )
    assert ws is None


def test_find_workspace_for_relative_path_returns_none(
    seeded_registry: WorkspaceRegistry,
) -> None:
    """Relative paths (vs absolute) — not in DB → None (privacy guard enforces abs canonical)."""
    ws = seeded_registry.find_workspace_for_project("projects_17/interior_planner")
    assert ws is None


# ── assert_path_privacy — explicit guard API ──


def test_assert_path_privacy_passes_for_owner(
    seeded_registry: WorkspaceRegistry, tmp_path: Path
) -> None:
    """Path registered to expected workspace → silent OK (no exception)."""
    seeded_registry.assert_path_privacy(
        _p(tmp_path, "buffy-playground_19"), "uchyoba"
    )
    seeded_registry.assert_path_privacy(
        _p(tmp_path, "freebuff_flutter_app"), "hobbi"
    )
    seeded_registry.assert_path_privacy(
        _p(tmp_path, "tg_terminal_messenger"), "rabota"
    )


def test_assert_path_privacy_raises_for_other_workspace(
    seeded_registry: WorkspaceRegistry, tmp_path: Path
) -> None:
    """Path registered to workspace A → assert with workspace B raises."""
    with pytest.raises(PrivacyViolationError):
        seeded_registry.assert_path_privacy(
            _p(tmp_path, "buffy-playground_19"), "hobbi"
        )
    with pytest.raises(PrivacyViolationError):
        seeded_registry.assert_path_privacy(
            _p(tmp_path, "diet_platform"), "rabota"
        )


def test_assert_path_privacy_passes_for_unregistered_path(
    seeded_registry: WorkspaceRegistry, tmp_path: Path
) -> None:
    """Unregistered path is NOT a privacy violation (just a no-op)."""
    seeded_registry.assert_path_privacy(
        _p(tmp_path, "ghost_project"), "rabota"
    )
    seeded_registry.assert_path_privacy(
        _p(tmp_path, "new_thing"), "uchyoba"
    )


# ── create_workspace / list_workspaces data integrity ──


def test_create_workspace_with_new_path(
    seeded_registry: WorkspaceRegistry, tmp_path: Path
) -> None:
    """New workspace + new path; new path is now found by that slug."""
    new_path = tmp_path / "_tmp_new_path"
    new_path.mkdir(parents=True, exist_ok=True)
    ws = seeded_registry.create_workspace(
        "Test Sandbox", project_paths=[str(new_path)]
    )
    assert ws.slug == "test_sandbox"
    found = seeded_registry.find_workspace_for_project(str(new_path))
    assert found is not None
    assert found.slug == "test_sandbox"


def test_create_workspace_collision_raises(
    seeded_registry: WorkspaceRegistry,
) -> None:
    """Same name → same slug → second create_workspace raises ValueError."""
    with pytest.raises(ValueError):
        seeded_registry.create_workspace("\u0420\u0430\u0431\u043e\u0442\u0430")


# ── get_default_registry_factory (with monkeypatch sandbox) ──


def test_get_default_registry_factory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Sanity-checks accessor; monkeypatch sandbox-isolated чтобы НЕ мутировать
    real data_13/context.db. Bugfix #6: factory test shouldn't pollute prod DB."""
    monkeypatch.setattr(
        WorkspaceRegistry, "DEFAULT_DB_PATH", tmp_path / "x.db"
    )
    reg = get_default_registry()
    assert isinstance(reg, WorkspaceRegistry)
    assert reg.db_path == (tmp_path / "x.db").resolve()


# ── CAN-14 strict-mode opt-in semantics (RTX-style fail-loud) ───
# ──────────────────────────────────────────────────────────────────


def test_seed_defaults_returns_seedresult_with_missing_paths(
    tmp_registry: WorkspaceRegistry, tmp_path: Path
) -> None:
    """seed_defaults() returns SeedResult dataclass with .created + .missing populated (CAN-14)."""
    from core_02.workspace_registry import SeedResult
    projects_root = tmp_path / "projects_17"
    projects_root.mkdir(parents=True, exist_ok=True)
    # Only create 1 of the 5 paths → 4 missing total
    (projects_root / "tg_terminal_messenger").mkdir(parents=True, exist_ok=True)
    result = tmp_registry.seed_defaults(workspace_root=tmp_path)
    assert isinstance(result, SeedResult)
    assert result.created == 3
    # 4 missing: interior_planner, buffy-playground_19, freebuff_flutter_app, diet_platform
    assert len(result.missing) == 4
    # missing_paths are absolute resolved (per seed_defaults contract)
    for mp in result.missing:
        assert Path(mp).is_absolute()


def test_add_project_returns_true_on_successful_insert(
    seeded_registry: WorkspaceRegistry, tmp_path: Path
) -> None:
    """add_project on existing FS path → returns True (CAN-14 explicit success signal)."""
    new_proj = tmp_path / "projects_17" / "fresh_project"
    new_proj.mkdir(parents=True, exist_ok=True)
    result = seeded_registry.add_project("rabota", str(new_proj))
    assert result is True
    # Verify bound
    projects_in_rabota = seeded_registry.list_projects("rabota")
    assert str(new_proj) in [str(Path(p).resolve()) for p in projects_in_rabota]


def test_add_project_strict_mode_raises_filenotfound(
    seeded_registry: WorkspaceRegistry, tmp_path: Path
) -> None:
    """add_project(strict=True) on missing path → raises FileNotFoundError (RTX-style fail-loud)."""
    ghost = str(tmp_path / "projects_17" / "ghost_strict_does_not_exist")
    with pytest.raises(FileNotFoundError, match="strict=True"):
        seeded_registry.add_project("rabota", ghost, strict=True)
    # Verify NO insertion happened (transaction was not entered).
    projects_in_rabota_after = [Path(p).name for p in seeded_registry.list_projects("rabota")]
    assert "ghost_strict_does_not_exist" not in projects_in_rabota_after


def test_create_workspace_propagates_strict_to_add_project(
    tmp_registry: WorkspaceRegistry, tmp_path: Path
) -> None:
    """create_workspace(strict=True) with one valid + one ghost path → raises (propagated to add_project)."""
    valid = tmp_path / "valid_proj"
    valid.mkdir(parents=True, exist_ok=True)
    ghost = str(tmp_path / "ghost_proj_does_not_exist")
    # Mixed list: valid + ghost. create_workspace should iterate; first add_project succeeds,
    # second add_project(strict=True) raises → propagates to caller.
    with pytest.raises(FileNotFoundError, match="strict=True"):
        tmp_registry.create_workspace(
            name="Mixed",
            project_paths=[str(valid), ghost],
            description="strict propagation test",
            owner_chat_id=42,
            strict=True,
        )


def test_create_workspace_non_strict_skips_ghost_silently(
    tmp_registry: WorkspaceRegistry, tmp_path: Path
) -> None:
    """create_workspace(strict=False, default) with one valid + one ghost path → succeeds, workspace created."""
    valid = tmp_path / "valid_non_strict_proj"
    valid.mkdir(parents=True, exist_ok=True)
    ghost = str(tmp_path / "ghost_proj_non_strict_does_not_exist")
    ws = tmp_registry.create_workspace(
        name="MixedSilent",
        project_paths=[str(valid), ghost],
        description="silent skip test",
        owner_chat_id=99,
    )
    # Workspace created; valid path bound; ghost silently skipped (no raise).
    assert ws.name == "MixedSilent"
    bound = [Path(p).name for p in ws.project_paths]
    assert "valid_non_strict_proj" in bound
    assert "ghost_proj_non_strict_does_not_exist" not in bound


def test_seedresult_dataclass_default_field_factory() -> None:
    """SeedResult is a dataclass with default_factory=list on .missing (no shared mutable state)."""
    from core_02.workspace_registry import SeedResult
    r1 = SeedResult(created=1)
    r2 = SeedResult(created=2)
    # Critical: dataclass field(default_factory=list) ensures each instance has its own list.
    r1.missing.append("/x")
    assert r2.missing == []  # mutation isolation test


# ── Polish-followup regression tests (post code-reviewer APPROVE-WITH-NITS) ─


def test_seed_defaults_integrity_error_logs_warning(
    tmp_registry: WorkspaceRegistry, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Lock CAN-14 race-loser contract (fix #2 polish):

    IntegrityError on workspace INSERT must be logged as WARNING
    (NOT silent pass). Verifies the operator gets observability on concurrent seed.

    Implementation: use sqlite3.connect's `factory` parameter to inject a
    Connection subclass that raises IntegrityError once on the FIRST
    `INSERT INTO workspaces` execution. Avoids C-level read-only on
    `sqlite3.Connection.execute` (which disallows runtime attribute set).

    Realistic race-loser semantics (Option A per code-reviewer 2026-08-04):
    the factory invokes `super().execute(sql, parameters)` BEFORE raising
    IntegrityError, simulating "the concurrent winner's commit was visible
    to us when our INSERT arrived; we lose the race on commit semantics".
    This matches real WAL behavior: the winner's row IS in DB when our
    IntegrityError fires. Subsequent `INSERT INTO workspace_projects` for
    the race-loser workspace passes FK check (workspace row exists). The
    test asserts WARNING + 3 workspaces in DB + order-independent seed count.
    """
    import logging
    import sqlite3 as _sqlite3
    from core_02.workspace_registry import DEFAULT_WORKSPACES, SeedResult
    # Setup projects_17/ tree so seed_defaults can complete both workspace + project inserts.
    projects_root = tmp_path / "projects_17"
    projects_root.mkdir(parents=True, exist_ok=True)
    for sub in (
        "interior_planner",
        "tg_terminal_messenger",
        "buffy-playground_19",
        "freebuff_flutter_app",
        "diet_platform",
    ):
        (projects_root / sub).mkdir(parents=True, exist_ok=True)

    # Connection subclass (factory-injected): on FIRST INSERT INTO workspaces,
    # simulates "winner's commit visible; our INSERT collides".
    class _RaceLoserConn(_sqlite3.Connection):
        _race_fired = False

        def execute(self, sql, parameters=()):
            if (
                isinstance(sql, str)
                and "INSERT INTO workspaces" in sql
                and not _RaceLoserConn._race_fired
            ):
                _RaceLoserConn._race_fired = True
                # Write the row first (simulating winner's commit), then raise
                # so our caller's except branch fires. Mirrors real WAL where
                # the winner's row is committed before the loser's IntegrityError
                # fires (winner happens-before loser in WAL ordering).
                if parameters:
                    super().execute(sql, parameters)
                else:
                    super().execute(sql)
                raise _sqlite3.IntegrityError(
                    "UNIQUE constraint failed: workspaces.slug (simulated race-loser)"
                )
            if parameters:
                return super().execute(sql, parameters)
            return super().execute(sql)

    _RaceLoserConn._race_fired = False  # reset for clean test

    def racing_connect(self):
        return _sqlite3.connect(str(self.db_path), factory=_RaceLoserConn)

    with patch.object(WorkspaceRegistry, "_connect", racing_connect):
        with caplog.at_level(logging.WARNING, logger="core_02.workspace_registry"):
            result = tmp_registry.seed_defaults(workspace_root=tmp_path)

    # Verify: WARNING logged for race-loser (NOT silent pass).
    race_warnings = [
        r
        for r in caplog.records
        if "race-loser" in r.message or "concurrent connection" in r.message
    ]
    assert len(race_warnings) >= 1, (
        f"Expected race-loser WARNING; got: "
        f"{[r.message for r in caplog.records if r.levelno >= logging.WARNING]}"
    )
    # Verify: SeedResult contract preserved (created is an int, missing is a list).
    assert isinstance(result, SeedResult)
    assert isinstance(result.created, int)
    assert isinstance(result.missing, list)
    # Verify: race-loser didn't lose data — 3 workspaces in DB (winner committed).
    assert len(tmp_registry.list_workspaces()) == 3
    # Verify: race-loser workspace's seed counter was NOT incremented (we lost).
    # Order-independent: exactly one INSERT raised IntegrityError; rest succeeded.
    assert result.created == len(DEFAULT_WORKSPACES) - 1, (
        f"Expected created = len(DEFAULT_WORKSPACES) - 1 = {len(DEFAULT_WORKSPACES) - 1}; "
        f"got {result.created}"
    )


def test_create_workspace_strict_no_partial_state_on_ghost_path(
    tmp_registry: WorkspaceRegistry, tmp_path: Path
) -> None:
    """Lock CAN-14 strict-mode partial-state fix (fix #3 polish):

    create_workspace(strict=True, [valid, ghost]) raises BEFORE workspace INSERT.
    No orphan workspace + no orphan project binding.
    """
    valid = tmp_path / "valid_partial_state_test"
    valid.mkdir(parents=True, exist_ok=True)
    ghost = str(tmp_path / "ghost_does_not_exist_for_partial_state")

    with pytest.raises(FileNotFoundError, match="create_workspace"):
        tmp_registry.create_workspace(
            name="Should Not Exist After PreValidate",
            project_paths=[str(valid), ghost],
            description="partial-state regression test",
            owner_chat_id=42,
            strict=True,
        )
    # Critical assertion 1: NO orphan workspace inserted (pre-validate blocked it).
    slugs = [ws.slug for ws in tmp_registry.list_workspaces()]
    assert "should_not_exist_after_prevalidate" not in slugs, (
        f"PARTIAL STATE BUG: workspace was inserted despite strict-mode ghost path. "
        f"Pre-validate fix not working. slugs={slugs}"
    )
    # Critical assertion 2: NO orphan project binding (valid path was NOT bound).
    assert tmp_registry.list_projects(
        "should_not_exist_after_prevalidate"
    ) == [], "PARTIAL STATE BUG: valid path was bound to non-existent workspace"

