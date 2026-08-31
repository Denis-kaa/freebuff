"""tests_09/test_adr018_factory_forge_bridge.py — ADR-018 маппинг-тесты Factory→Forge.

Покрывает ADR-018 §4 (6 hermetic тестов маппинга) — официальный контракт
Factory→Forge execution bridge: BaseFactory.execute / opportunity_engine.execute
→ select_forge → ForgeFacade.run_chain.

Семантика под тестом (ADR-018 §2):
  - capability — закрытый токен; None → fail-safe fallback (не краш).
  - factory_id / forge_id — АДВИЗОРНЫЕ (traceability), НЕ управляют исполнением.
  - role_ids — единственный управляющий вход в run_chain.
  - dry_run=True → run_chain НЕ вызывается.

Hermetic: фейковые Registry/ForgeFacade/MemoryStore, tmp-директории,
monkeypatch _lazy_import (opportunity_engine) — без side-effect на data_13.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts_01.content_factory import (  # noqa: E402
    ContentFactory,
    CONTENT_CAPABILITIES,
    CONTENT_ROLE_IDS,
)
from scripts_01.opportunity_engine import (  # noqa: E402
    Opportunity,
    _derive_capability,
)


# ─── Fakes (hermetic, mirror test_content_factory.py) ─────────────────────────

class _FakeFactoryRegistry:
    """FactoryRegistry-фейк: capability → (factory_id, forge_id) строки."""

    def __init__(self, mapping: dict):
        self._mapping = mapping

    def select_forge(self, capability: str):
        pair = self._mapping.get(capability)
        if pair is None:
            return None
        fp, fg = pair
        return (type("FP", (), {"factory_id": fp})(), type("FG", (), {"forge_id": fg})())


class _FakeChainRun:
    def __init__(self, overall: str = "ok"):
        self.overall = overall
        self.validation_summary = {"ok": True}

    def to_dict(self) -> dict:
        return {"overall": self.overall, "stage_count": 1, "chain": []}


class _FakeForgeFacade:
    """ForgeFacade-фейк: перехватывает run_chain (BaseFactory path)."""

    def __init__(self, overall: str = "ok"):
        self.calls: list = []
        self.overall = overall

    def run_chain(self, project, role_ids=None, **kw):
        self.calls.append({"project_root": getattr(project, "root", None),
                           "role_ids": role_ids})
        return _FakeChainRun(self.overall)


class _FakeForgeFacadeClass:
    """ForgeFacade-фейк для opportunity_engine path (facade = ForgeFacade())."""

    def __init__(self, overall: str = "ok"):
        self.calls: list = []
        self.overall = overall

    def run_chain(self, project, role_ids=None, **kw):
        self.calls.append({"project_root": getattr(project, "root", None),
                           "role_ids": role_ids})
        return _FakeChainRun(self.overall)


class _FakeMemoryStore:
    def __init__(self):
        self.kos: list = []
        self.events: list = []

    def store_knowledge(self, **kw) -> str:
        kid = f"ko-{len(self.kos) + 1}"
        self.kos.append(kw)
        return kid

    def record_learning_event(self, **kw) -> str:
        eid = f"ev-{len(self.events) + 1}"
        self.events.append(kw)
        return eid


def _make_opp(opp_id="opp-adr018", project_id="proj-test", capability="article_generation",
              status="ACTIVE"):
    return type("Opp", (), {
        "id": opp_id,
        "project_id": project_id,
        "title": "ADR-018 mapping test",
        "description": "Factory→Forge execution bridge",
        "source": "hand",
        "status": status,
        "priority": 5,
        "provenance": {"source": "hand", "source_id": "h-1", "capability": capability},
        "scenario": {"capability": capability} if capability else None,
        "source_path": "",
        "evidence_path": "",
        "related_whims": [],
    })()


def _fake_project(root: Path = Path("/tmp/fake_project")):
    return type("Proj", (), {"root": root})()


# ─── Test 1: capability → (FactoryPassport, ForgePassport) ───────────────────

def test_execute_resolves_capability_to_factory_forge_pair():
    """capability → select_forge → пара (factory_id, forge_id) в request."""
    cf = ContentFactory(factory_registry=_FakeFactoryRegistry({
        "article_generation": ("content", "writing"),
    }))
    opp = _make_opp()
    req = cf.build_execution_request(opp, "article_generation")
    assert req is not None
    assert req.factory_id == "content"
    assert req.forge_id == "writing"
    assert req.capability == "article_generation"


# ─── Test 2: role_ids передаются в run_chain (единственный управляющий вход) ──

def test_execute_passes_role_ids_to_run_chain():
    """role_ids = ROLE_IDS — единственный управляющий вход в ForgeFacade.run_chain."""
    facade = _FakeForgeFacade()
    cf = ContentFactory(
        factory_registry=_FakeFactoryRegistry({"article_generation": ("content", "writing")}),
        forge_facade=facade,
        memory_store=_FakeMemoryStore(),
    )
    opp = _make_opp()
    cf._resolve_project = lambda opp, project_root=None: _fake_project()
    result = cf.execute(opp)
    assert result["ok"] is True
    assert facade.calls, "run_chain должен быть вызван"
    assert tuple(facade.calls[0]["role_ids"]) == tuple(CONTENT_ROLE_IDS)


# ─── Test 3: factory_selection записывается в provenance (traceability) ──────

def test_execute_records_factory_selection_provenance(tmp_path, monkeypatch):
    """opportunity_engine.execute: provenance['factory_selection'] = factory/forge/capability."""
    import scripts_01.opportunity_engine as oe

    fake_facade = _FakeForgeFacadeClass()
    real_lazy = oe._lazy_import

    def fake_lazy(module_name: str, attr: str):
        if module_name == "core_02.forge_facade" and attr == "ForgeFacade":
            return lambda: fake_facade  # ForgeFacade() → instance
        return real_lazy(module_name, attr)

    monkeypatch.setattr(oe, "_lazy_import", fake_lazy)

    fake_registry = _FakeFactoryRegistry({"article_generation": ("content", "writing")})
    opp = Opportunity(
        id="opp-adr018-3",
        project_id="proj-test",
        title="ADR-018 provenance",
        description="test",
        source="hand",
        status="ACTIVE",
        provenance={"source": "hand", "capability": "article_generation"},
        scenario={"capability": "article_generation"},
    )
    opp = oe.execute(
        opp,
        memory_store=_FakeMemoryStore(),
        project_root=tmp_path,
        factory_registry=fake_registry,
    )
    sel = opp.provenance.get("factory_selection")
    assert sel is not None
    assert sel["factory_id"] == "content"
    assert sel["forge_id"] == "writing"
    assert sel["capability"] == "article_generation"
    assert opp.status == "COMPLETED"


# ─── Test 4: без capability → fallback (не краш) ─────────────────────────────

def test_execute_fallback_when_capability_absent(tmp_path, monkeypatch):
    """Без capability: select_forge не вызывается, provenance.fallback=True, не краш."""
    import scripts_01.opportunity_engine as oe

    fake_facade = _FakeForgeFacadeClass()
    real_lazy = oe._lazy_import

    def fake_lazy(module_name: str, attr: str):
        if module_name == "core_02.forge_facade" and attr == "ForgeFacade":
            return lambda: fake_facade
        return real_lazy(module_name, attr)

    monkeypatch.setattr(oe, "_lazy_import", fake_lazy)

    opp = Opportunity(
        id="opp-adr018-4",
        project_id="proj-test",
        title="ADR-018 fallback",
        description="test",
        source="hand",
        status="ACTIVE",
        provenance={"source": "hand"},  # без capability
        scenario=None,
    )
    assert _derive_capability(opp) is None
    opp = oe.execute(
        opp,
        memory_store=_FakeMemoryStore(),
        project_root=tmp_path,
        factory_registry=_FakeFactoryRegistry({"article_generation": ("content", "writing")}),
    )
    sel = opp.provenance.get("factory_selection")
    assert sel is not None and sel.get("fallback") is True
    # run_chain всё равно вызывается (pipeline fallback) — не краш
    assert fake_facade.calls


# ─── Test 5: forge_id адвизорный — не управляет исполнением ──────────────────

def test_forge_id_advisory_not_driving_execution():
    """Разные forge_id при тех же role_ids → run_chain вызывается с одинаковыми role_ids."""
    facade = _FakeForgeFacade()
    cf = ContentFactory(
        factory_registry=_FakeFactoryRegistry({"article_generation": ("content", "writing")}),
        forge_facade=facade,
        memory_store=_FakeMemoryStore(),
    )
    opp = _make_opp()
    cf._resolve_project = lambda opp, project_root=None: _fake_project()
    result1 = cf.execute(opp)
    assert result1["artifact"]["forge_id"] == "writing"

    # Второй прогон с ДРУГОЙ кузней (analysis), те же роли
    facade2 = _FakeForgeFacade()
    cf2 = ContentFactory(
        factory_registry=_FakeFactoryRegistry({"article_generation": ("content", "analysis")}),
        forge_facade=facade2,
        memory_store=_FakeMemoryStore(),
    )
    cf2._resolve_project = lambda opp, project_root=None: _fake_project()
    result2 = cf2.execute(_make_opp(opp_id="opp-adr018-5"))
    assert result2["artifact"]["forge_id"] == "analysis"

    # role_ids идентичны, несмотря на разные forge_id → forge_id адвизорный
    assert tuple(facade.calls[0]["role_ids"]) == tuple(facade2.calls[0]["role_ids"])
    assert facade.calls[0]["role_ids"] == CONTENT_ROLE_IDS


# ─── Test 6: dry_run → run_chain НЕ вызывается ────────────────────────────────

def test_execute_dry_run_no_run_chain():
    """dry_run=True: request формируется, ForgeFacade.run_chain НЕ вызывается."""
    facade = _FakeForgeFacade()
    cf = ContentFactory(
        factory_registry=_FakeFactoryRegistry({"article_generation": ("content", "writing")}),
        forge_facade=facade,
        memory_store=_FakeMemoryStore(),
    )
    opp = _make_opp()
    result = cf.execute(opp, dry_run=True)
    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["request"]["factory_id"] == "content"
    assert result["request"]["forge_id"] == "writing"
    assert facade.calls == []  # ForgeFacade НЕ вызывался
