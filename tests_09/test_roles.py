#!/usr/bin/env python3
"""
Tests for Role Engine (scripts_01/roles.py).

Tests:
  - STANDARD_ROLES definitions
  - RoleDefinition: from_dict / to_dict
  - Custom roles: add_role / list_roles / get_role
  - Assignments: assign / unassign / unassign_all / get_roles / list_by_role
  - Capabilities: per-role and per-agent
  - Collab role mapping
  - Integrations: sync to presence / collab
  - Stats
  - CLI commands
"""

from __future__ import annotations

import sys
***REMOVED***

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts_01.roles import (
    RoleEngine,
    RoleDefinition,
    AgentRole,
    STANDARD_ROLES,
)


# ═══════════════════════════════════════════════════════════════
# Helpers / fixtures
# ═══════════════════════════════════════════════════════════════


class _StubPresence:
    """Заглушка PresenceEngine: запоминает синхронизированные роли."""

    def __init__(self):
        self.calls = [***REMOVED***

    def update_status(self, agent_name, status, metadata=None):
        self.calls.append((agent_name, status, metadata or {***REMOVED***))
        return True


class _StubCollab:
    """Заглушка CollaborationEngine."""

    def __init__(self):
        self.calls = [***REMOVED***

    def update_participant_role(self, session_id, participant_name, new_role):
        self.calls.append((session_id, participant_name, new_role))
        return True


@pytest.fixture
def engine(tmp_path) -> RoleEngine:
    return RoleEngine(db_path=tmp_path / "roles_test.db")


@pytest.fixture
def custom_role() -> RoleDefinition:
    return RoleDefinition(
        name="devops",
        display_name="DevOps",
        description="CI/CD и инфраструктура",
        icon="⚙️",
        capabilities=["ci", "deploy"***REMOVED***,
        priority=6,
    )


# ═══════════════════════════════════════════════════════════════
# Standard roles
# ═══════════════════════════════════════════════════════════════


class TestStandardRoles:
    def test_six_standard_roles(self):
        assert set(STANDARD_ROLES.keys()) == {
            "developer", "reviewer", "documenter", "researcher", "archiver", "orchestrator",
        ***REMOVED***

    def test_role_definitions_have_capabilities(self):
        for name, data in STANDARD_ROLES.items():
            assert data["capabilities"***REMOVED***, f"Role {name***REMOVED*** has no capabilities"

    def test_list_roles_returns_definitions(self, engine: RoleEngine):
        roles = engine.list_roles()
        names = [r.name for r in roles***REMOVED***
        assert "developer" in names
        assert "orchestrator" in names

    def test_get_role_standard(self, engine: RoleEngine):
        role = engine.get_role("developer")
        assert role is not None
        assert role.display_name == "Developer"
        assert "coding" in role.capabilities

    def test_get_role_unknown(self, engine: RoleEngine):
        assert engine.get_role("nonexistent") is None

    def test_get_capabilities_for_role(self, engine: RoleEngine):
        caps = engine.get_capabilities_for_role("developer")
        assert "coding" in caps
        assert "testing" in caps

    def test_get_capabilities_unknown_role(self, engine: RoleEngine):
        assert engine.get_capabilities_for_role("nonexistent") == [***REMOVED***

    def test_role_definition_from_dict(self):
        role = RoleDefinition.from_dict("x", {"display_name": "X", "capabilities": ["a"***REMOVED******REMOVED***)
        assert role.name == "x"
        assert role.display_name == "X"
        assert role.capabilities == ["a"***REMOVED***
        assert role.priority == 10  # default

    def test_role_definition_to_dict(self):
        role = RoleDefinition(
            name="x", display_name="X", description="d", icon="?", capabilities=["a"***REMOVED***, priority=1
        )
        d = role.to_dict()
        assert d["name"***REMOVED*** == "x"
        assert d["capabilities"***REMOVED*** == ["a"***REMOVED***


# ═══════════════════════════════════════════════════════════════
# Custom roles
# ═══════════════════════════════════════════════════════════════


class TestCustomRoles:
    def test_add_custom_role(self, engine: RoleEngine, custom_role: RoleDefinition):
        assert engine.add_role(custom_role) is True
        role = engine.get_role("devops")
        assert role is not None
        assert role.capabilities == ["ci", "deploy"***REMOVED***

    def test_add_custom_role_duplicate(self, engine: RoleEngine, custom_role: RoleDefinition):
        engine.add_role(custom_role)
        assert engine.add_role(custom_role) is False

    def test_cannot_override_standard_role(self, engine: RoleEngine):
        role = RoleDefinition(
            name="developer", display_name="Hack", description="", icon="", capabilities=[***REMOVED***, priority=9
        )
        assert engine.add_role(role) is False

    def test_list_roles_includes_custom(self, engine: RoleEngine, custom_role: RoleDefinition):
        engine.add_role(custom_role)
        names = [r.name for r in engine.list_roles()***REMOVED***
        assert "devops" in names

    def test_assign_custom_role(self, engine: RoleEngine, custom_role: RoleDefinition):
        engine.add_role(custom_role)
        assert engine.assign_role("buffy", "devops") is True
        assert engine.get_roles("buffy") == ["devops"***REMOVED***


# ═══════════════════════════════════════════════════════════════
# Assignments
# ═══════════════════════════════════════════════════════════════


class TestAssignments:
    def test_assign_role(self, engine: RoleEngine):
        assert engine.assign_role("buffy", "developer") is True
        assert engine.get_roles("buffy") == ["developer"***REMOVED***

    def test_assign_unknown_role(self, engine: RoleEngine):
        assert engine.assign_role("buffy", "nonexistent") is False
        assert engine.get_roles("buffy") == [***REMOVED***

    def test_assign_duplicate_is_idempotent(self, engine: RoleEngine):
        engine.assign_role("buffy", "developer")
        engine.assign_role("buffy", "developer")
        assert engine.get_roles("buffy") == ["developer"***REMOVED***

    def test_assign_multiple_roles(self, engine: RoleEngine):
        engine.assign_role("buffy", "developer")
        engine.assign_role("buffy", "reviewer")
        assert set(engine.get_roles("buffy")) == {"developer", "reviewer"***REMOVED***

    def test_unassign_role(self, engine: RoleEngine):
        engine.assign_role("buffy", "developer")
        assert engine.unassign_role("buffy", "developer") is True
        assert engine.get_roles("buffy") == [***REMOVED***

    def test_unassign_missing_role(self, engine: RoleEngine):
        assert engine.unassign_role("buffy", "developer") is False

    def test_unassign_all(self, engine: RoleEngine):
        engine.assign_role("buffy", "developer")
        engine.assign_role("buffy", "reviewer")
        assert engine.unassign_all("buffy") == 2
        assert engine.get_roles("buffy") == [***REMOVED***

    def test_get_roles_empty(self, engine: RoleEngine):
        assert engine.get_roles("ghost") == [***REMOVED***

    def test_list_assignments(self, engine: RoleEngine):
        engine.assign_role("buffy", "developer")
        engine.assign_role("alice", "reviewer")
        assignments = engine.list_assignments()
        assert len(assignments) == 2
        assert all(isinstance(a, AgentRole) for a in assignments)

    def test_get_agent_roles_detailed(self, engine: RoleEngine):
        engine.assign_role("buffy", "developer", assigned_by="admin")
        details = engine.get_agent_roles_detailed("buffy")
        assert len(details) == 1
        assert details[0***REMOVED***.assigned_by == "admin"
        assert details[0***REMOVED***.to_dict()["role_name"***REMOVED*** == "developer"

    def test_list_by_role(self, engine: RoleEngine):
        engine.assign_role("buffy", "developer")
        engine.assign_role("alice", "developer")
        engine.assign_role("bob", "reviewer")
        assert set(engine.list_by_role("developer")) == {"buffy", "alice"***REMOVED***
        assert engine.list_by_role("reviewer") == ["bob"***REMOVED***


# ═══════════════════════════════════════════════════════════════
# Capabilities
# ═══════════════════════════════════════════════════════════════


class TestCapabilities:
    def test_agent_capabilities_union(self, engine: RoleEngine):
        engine.assign_role("buffy", "developer")
        engine.assign_role("buffy", "documenter")
        caps = engine.get_agent_capabilities("buffy")
        assert "coding" in caps
        assert "documentation" in caps

    def test_agent_capabilities_empty(self, engine: RoleEngine):
        assert engine.get_agent_capabilities("ghost") == [***REMOVED***

    def test_agent_capabilities_sorted(self, engine: RoleEngine):
        engine.assign_role("buffy", "developer")
        caps = engine.get_agent_capabilities("buffy")
        assert caps == sorted(caps)


# ═══════════════════════════════════════════════════════════════
# Collab role mapping
# ═══════════════════════════════════════════════════════════════


class TestCollabRoleMapping:
    def test_orchestrator_maps_to_owner(self, engine: RoleEngine):
        engine.assign_role("buffy", "orchestrator")
        assert engine.get_collab_role("buffy") == "owner"

    def test_developer_maps_to_editor(self, engine: RoleEngine):
        engine.assign_role("buffy", "developer")
        assert engine.get_collab_role("buffy") == "editor"

    def test_reviewer_maps_to_editor(self, engine: RoleEngine):
        engine.assign_role("buffy", "reviewer")
        assert engine.get_collab_role("buffy") == "editor"

    def test_other_roles_map_to_viewer(self, engine: RoleEngine):
        engine.assign_role("buffy", "documenter")
        assert engine.get_collab_role("buffy") == "viewer"

    def test_no_roles_map_to_viewer(self, engine: RoleEngine):
        assert engine.get_collab_role("ghost") == "viewer"


# ═══════════════════════════════════════════════════════════════
# Integrations
# ═══════════════════════════════════════════════════════════════


class TestIntegrations:
    def test_sync_to_presence(self, tmp_path):
        presence = _StubPresence()
        engine = RoleEngine(db_path=tmp_path / "r.db", presence_engine=presence)
        engine.assign_role("buffy", "developer")
        assert engine.sync_to_presence("buffy") is True
        assert presence.calls and presence.calls[0***REMOVED***[0***REMOVED*** == "buffy"
        assert presence.calls[0***REMOVED***[2***REMOVED***.get("roles") == ["developer"***REMOVED***

    def test_sync_to_presence_without_engine(self, engine: RoleEngine):
        assert engine.sync_to_presence("buffy") is False

    def test_sync_to_collab(self, tmp_path):
        collab = _StubCollab()
        engine = RoleEngine(db_path=tmp_path / "r.db", collaboration_engine=collab)
        engine.assign_role("buffy", "developer")
        assert engine.sync_to_collab_session("s1", "buffy") is True
        assert collab.calls == [("s1", "buffy", "editor")***REMOVED***

    def test_sync_to_collab_without_engine(self, engine: RoleEngine):
        assert engine.sync_to_collab_session("s1", "buffy") is False

    def test_sync_all_to_presence(self, tmp_path):
        presence = _StubPresence()
        engine = RoleEngine(db_path=tmp_path / "r.db", presence_engine=presence)
        engine.assign_role("buffy", "developer")
        engine.assign_role("alice", "reviewer")
        assert engine.sync_all_to_presence() == 2

    def test_sync_all_without_presence(self, engine: RoleEngine):
        engine.assign_role("buffy", "developer")
        assert engine.sync_all_to_presence() == 0


# ═══════════════════════════════════════════════════════════════
# Stats
# ═══════════════════════════════════════════════════════════════


class TestStats:
    def test_get_stats_empty(self, engine: RoleEngine):
        stats = engine.get_stats()
        assert stats["total_assignments"***REMOVED*** == 0
        assert stats["defined_roles"***REMOVED*** == 6
        assert stats["assigned_agents"***REMOVED*** == 0

    def test_get_stats_with_assignments(self, engine: RoleEngine):
        engine.assign_role("buffy", "developer")
        engine.assign_role("buffy", "reviewer")
        engine.assign_role("alice", "developer")
        stats = engine.get_stats()
        assert stats["total_assignments"***REMOVED*** == 3
        assert stats["assigned_agents"***REMOVED*** == 2
        assert stats["role_counts"***REMOVED***["developer"***REMOVED*** == 2
        assert stats["role_counts"***REMOVED***["reviewer"***REMOVED*** == 1

    def test_get_stats_with_custom_role(self, engine: RoleEngine, custom_role: RoleDefinition):
        engine.add_role(custom_role)
        assert engine.get_stats()["defined_roles"***REMOVED*** == 7


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════


class TestCLI:
    def test_main_help(self, monkeypatch):
        from scripts_01.roles import main

        monkeypatch.setattr(sys, "argv", ["roles.py", "--help"***REMOVED***)
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    def test_main_no_command(self, monkeypatch, capsys):
        from scripts_01.roles import main

        monkeypatch.setattr(sys, "argv", ["roles.py"***REMOVED***)
        code = main()
        assert code == 1
