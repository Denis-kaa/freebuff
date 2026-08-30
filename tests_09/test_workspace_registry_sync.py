"""tests_09/test_workspace_registry_sync.py — Hermetic тесты sync_from_config() (ADR-017).

Покрывает:
- SyncReport dataclass: defaults, isolation, fields
- sync_from_config: YAML → SQLite one-way, idempotent, additive
- workspace creation / skip
- project binding / skip / conflict (privacy invariant)
- no-deletion invariant
- empty config / missing workspace.yaml
- one-way: SQLite never writes to YAML
"""

from __future__ import annotations

}

import pytest
import yaml

from core_02.workspace_registry import SyncReport, WorkspaceRegistry, _slugify_name


# ── Fixtures ──

@pytest.fixture
def tmp_registry(tmp_path: Path) -> WorkspaceRegistry:
    """Fresh registry backed by a tmp database file."""
    db_path = tmp_path / "sync_test.db"
    return WorkspaceRegistry(db_path)


@pytest.fixture
def config_ws_dir(tmp_path: Path) -> Path:
    """Minimal workspace tree: workspace.yaml + 2 project dirs with project.yaml."""
    root = tmp_path / "test_ws"
    root.mkdir()

    # workspace.yaml
    (root / "workspace.yaml").write_text(
        yaml.dump({
            "name": "Test Workspace",
            "description": "ADR-017 sync test workspace",
            "default_environment": "development",
            "steps_policy": "strict",
            "projects": [],
        ]),
        encoding="utf-8",
    )

    # project dirs
    for proj in ("proj_a", "proj_b"):
        pd = root / proj
        pd.mkdir()
        (pd / "project.yaml").write_text(
            yaml.dump({"name": f"Project {proj[-1].upper()}", "type": "python"}),
            encoding="utf-8",
        )

    return root


@pytest.fixture
def config_ws_with_projects(tmp_path: Path) -> Path:
    """Workspace tree with explicit project list in workspace.yaml."""
    root = tmp_path / "explicit_ws"
    root.mkdir()

    # Create project dirs
    for proj in ("p1", "p2"):
        (root / proj).mkdir()
        (root / proj / "README.md").write_text(f"# {proj}")

    (root / "workspace.yaml").write_text(
        yaml.dump({
            "name": "Explicit WS",
            "projects": ["p1", "p2"],
        ]),
        encoding="utf-8",
    )

    return root


# ── SyncReport dataclass ──

class TestSyncReport:
    """SyncReport dataclass: defaults, isolation, fields."""

    def test_defaults_are_empty(self) -> None:
        r = SyncReport()
        assert r.created_workspaces == []
        assert r.created_projects == []
        assert r.skipped_workspaces == []
        assert r.skipped_projects == []
        assert r.conflicts == []

    def test_mutable_isolation(self) -> None:
        """Mutating one SyncReport does not affect another."""
        r1 = SyncReport()
        r2 = SyncReport()
        r1.created_workspaces.append("ws1")
        assert r2.created_workspaces == []

    def test_conflict_tuple_structure(self) -> None:
        r = SyncReport()
        r.conflicts.append(("/abs/path", "current_slug", "expected_slug"))
        assert len(r.conflicts) == 1
        assert r.conflicts[0][0] == "/abs/path"


# ── sync_from_config: YAML → SQLite ──

class TestSyncFromConfig:
    """One-way, idempotent, additive sync (ADR-017 §2)."""

    def test_initial_sync_creates_workspace_and_projects(
        self, tmp_registry: WorkspaceRegistry, config_ws_dir: Path,
    ) -> None:
        """First sync: workspace + projects created."""
        report = tmp_registry.sync_from_config(workspace_root=config_ws_dir)

        slug = _slugify_name("Test Workspace")
        assert slug == "test_workspace"
        assert slug in report.created_workspaces
        assert len(report.created_projects) == 2
        assert len(report.skipped_workspaces) == 0
        assert len(report.conflicts) == 0

        # Verify in DB
        wss = tmp_registry.list_workspaces()
        assert len(wss) == 1
        assert wss[0].slug == slug
        assert wss[0].name == "Test Workspace"

        bound = [Path(p).name for p in wss[0].project_paths]
        assert sorted(bound) == ["proj_a", "proj_b"]

    def test_idempotent_second_sync_all_skipped(
        self, tmp_registry: WorkspaceRegistry, config_ws_dir: Path,
    ) -> None:
        """Second sync: workspace + all projects skipped (idempotent)."""
        tmp_registry.sync_from_config(workspace_root=config_ws_dir)
        report = tmp_registry.sync_from_config(workspace_root=config_ws_dir)

        assert len(report.created_workspaces) == 0
        assert len(report.created_projects) == 0
        assert len(report.skipped_workspaces) == 1
        assert len(report.skipped_projects) == 2
        assert len(report.conflicts) == 0

    def test_sync_does_not_overwrite_owner_or_status(
        self, tmp_registry: WorkspaceRegistry, config_ws_dir: Path,
    ) -> None:
        """Sync doesn't touch owner_chat_id/status (runtime state, not config)."""
        # Pre-populate with a custom owner/status
        ws = tmp_registry.create_workspace(
            "Test Workspace",
            project_paths=[str(config_ws_dir / "proj_a")],
            owner_chat_id=42,
        )
        assert ws.owner_chat_id == 42

        # Sync should skip workspace
        report = tmp_registry.sync_from_config(workspace_root=config_ws_dir)
        assert _slugify_name("Test Workspace") in report.skipped_workspaces

        # Owner remains 42 (not overwritten to 0)
        updated = tmp_registry.list_workspaces()
        assert len(updated) == 1
        assert updated[0].owner_chat_id == 42
        assert updated[0].status == "active"

    def test_privacy_conflict_when_path_in_other_workspace(
        self, tmp_registry: WorkspaceRegistry, config_ws_dir: Path,
    ) -> None:
        """Path already in another workspace → conflict, not bound, not crash."""
        # Register proj_a under a different workspace first
        other_ws = tmp_registry.create_workspace(
            "Other WS",
            project_paths=[str(config_ws_dir / "proj_a")],
        )
        assert other_ws.slug == "other_ws"

        # Now sync Test Workspace — proj_a should conflict
        report = tmp_registry.sync_from_config(workspace_root=config_ws_dir)

        assert _slugify_name("Test Workspace") in report.created_workspaces
        assert len(report.conflicts) == 1
        conflict_path, current_slug, expected_slug = report.conflicts[0]
        assert Path(conflict_path).name == "proj_a"
        assert current_slug == "other_ws"
        assert expected_slug == "test_workspace"

        # proj_b should still be bound (uncontested)
        bound = [Path(p).name for p in report.created_projects]
        assert "proj_b" in bound

    def test_no_deletion_absent_project_in_yaml_keeps_db_row(
        self, tmp_registry: WorkspaceRegistry, config_ws_dir: Path,
    ) -> None:
        """Absent project in YAML does NOT delete DB row (additive only)."""
        # First sync: both projects bound
        tmp_registry.sync_from_config(workspace_root=config_ws_dir)

        # Remove proj_a from YAML (physically stays on FS)
        cfg = yaml.safe_load((config_ws_dir / "workspace.yaml").read_text()) or {}
        cfg["projects"] = ["proj_b"]  # proj_a excluded
        (config_ws_dir / "workspace.yaml").write_text(yaml.dump(cfg), encoding="utf-8")

        # Second sync
        report = tmp_registry.sync_from_config(workspace_root=config_ws_dir)

        # proj_a still in DB (not deleted)
        slug = _slugify_name("Test Workspace")
        bound = [Path(p).name for p in tmp_registry.list_projects(slug)]
        assert "proj_a" in bound
        assert "proj_b" in bound

        # proj_b is skipped, nothing deleted
        assert len(report.created_projects) == 0

    def test_missing_workspace_yaml_falls_back_to_dir_name(
        self, tmp_registry: WorkspaceRegistry, tmp_path: Path,
    ) -> None:
        """No workspace.yaml → fallback: slug comes from directory name."""
        root = tmp_path / "no_yaml_ws"
        root.mkdir()

        report = tmp_registry.sync_from_config(workspace_root=root)
        assert "no_yaml_ws" in report.created_workspaces

    def test_sync_sets_description_from_yaml(
        self, tmp_registry: WorkspaceRegistry, config_ws_dir: Path,
    ) -> None:
        """Description from workspace.yaml is stored in SQLite."""
        report = tmp_registry.sync_from_config(workspace_root=config_ws_dir)
        slug = _slugify_name("Test Workspace")

        wss = tmp_registry.list_workspaces()
        ws = next(w for w in wss if w.slug == slug)
        assert ws.description == "ADR-017 sync test workspace"

    def test_sync_with_explicit_project_list(
        self, tmp_registry: WorkspaceRegistry, config_ws_with_projects: Path,
    ) -> None:
        """Explicit 'projects' list in workspace.yaml used for binding."""
        report = tmp_registry.sync_from_config(workspace_root=config_ws_with_projects)

        assert _slugify_name("Explicit WS") in report.created_workspaces
        assert len(report.created_projects) == 2
        bound = [Path(p).name for p in report.created_projects]
        assert sorted(bound) == ["p1", "p2"]


# ── One-way invariant ──

class TestOneWayInvariant:
    """SQLite NEVER writes to YAML (one-way: YAML → SQLite only)."""

    def test_sync_does_not_modify_workspace_yaml(
        self, tmp_registry: WorkspaceRegistry, config_ws_dir: Path,
    ) -> None:
        """sync_from_config does not write to workspace.yaml."""
        original_mtime = (config_ws_dir / "workspace.yaml").stat().st_mtime

        tmp_registry.sync_from_config(workspace_root=config_ws_dir)

        new_mtime = (config_ws_dir / "workspace.yaml").stat().st_mtime
        assert new_mtime == original_mtime, (
            "sync_from_config modified workspace.yaml — violates one-way invariant"
        )

    def test_sync_does_not_modify_project_yaml(
        self, tmp_registry: WorkspaceRegistry, config_ws_dir: Path,
    ) -> None:
        """sync_from_config does not write to project.yaml."""
        original_mtime = (config_ws_dir / "proj_a" / "project.yaml").stat().st_mtime

        tmp_registry.sync_from_config(workspace_root=config_ws_dir)

        new_mtime = (config_ws_dir / "proj_a" / "project.yaml").stat().st_mtime
        assert new_mtime == original_mtime, (
            "sync_from_config modified project.yaml — violates one-way invariant"
        )