#!/usr/bin/env python3
"""tests_09/test_artifact.py — hermetic-тесты единого Artifact-контракта (ADR-021).

Проверяет core_02/artifact.py: round-trip dict↔Artifact, ChainRun→Artifact,
resolve_files, BC-ключи, закрытый словарь overall.

Hermetic: никакого side-effect на data_13/context.db, tmp_path, фейковые
ChainRun/ExecutionRequest (fixture-стиль, как test_adr018_factory_forge_bridge.py).
"""

from __future__ import annotations

}
from typing import Any, Dict

import pytest

from core_02.artifact import Artifact, OVERALL_VALUES
from core_02.factory_base import BaseFactory


# ─── Фейковые объекты (ChainRun-подобный + ExecutionRequest-подобный) ──────

class _FakeChainStage:
    def __init__(self, role_id: str, mode: str, status: str, details: str):
        self.role_id = role_id
        self.mode = mode
        self.status = status
        self.details = details

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role_id": self.role_id,
            "mode": self.mode,
            "status": self.status,
            "details": self.details,
        }


class _FakeChainRun:
    def __init__(self, **kw):
        self.project_id = kw.get("project_id", "p1")
        self.project_root = kw.get("project_root", "/tmp/p1")
        self.stage_count = kw.get("stage_count", 2)
        self.chain = kw.get("chain", (
            _FakeChainStage("explainer", "check_only", "ok", "done"),
            _FakeChainStage("developer", "full_cycle", "run_ok", "done"),
        ))
        self.overall = kw.get("overall", "ok")
        self.started_at = kw.get("started_at", "")
        self.finished_at = kw.get("finished_at", "")
        self.validation_registry_status = kw.get("validation_registry_status", "not_run")
        self.validation_summary = kw.get("validation_summary", None)


class _FakeRequest:
    def __init__(self, **kw):
        self.opportunity_id = kw.get("opportunity_id", "opp-1")
        self.project_id = kw.get("project_id", "p1")
        self.capability = kw.get("capability", "article_generation")
        self.factory_id = kw.get("factory_id", "content")
        self.forge_id = kw.get("forge_id", "writing")
        self.output_spec = kw.get("output_spec", {
            "artifact_kind": "content_artifact",
            "target": "projects_17/p1/forge/",
        ])


def _make_run(**kw) -> _FakeChainRun:
    return _FakeChainRun(**kw)


def _make_request(**kw) -> _FakeRequest:
    return _FakeRequest(**kw)


# ─── Тесты ──────────────────────────────────────────────────────────────────

def test_overall_closed_vocab_accepts_known_values():
    for v in ("ok", "partial", "failed", "degraded", "unknown"):
        a = Artifact(
            id="a", kind="generic_artifact", opportunity_id="o", project_id="p",
            capability="c", factory_id="f", forge_id="g", overall=v,
        )
        assert a.overall == v


def test_overall_closed_vocab_rejects_drift():
    with pytest.raises(ValueError):
        Artifact(
            id="a", kind="generic_artifact", opportunity_id="o", project_id="p",
            capability="c", factory_id="f", forge_id="g", overall="bogus",
        )


def test_from_chain_run_maps_all_fields():
    run = _make_run()
    req = _make_request()
    a = Artifact.from_chain_run(run, req, files=("RUNNABLE.md", "CHECKLIST.md"))
    assert a.overall == "ok"
    assert a.stage_count == 2
    assert len(a.chain) == 2
    assert a.chain[0]["role_id"] == "explainer"
    assert a.capability == "article_generation"
    assert a.factory_id == "content"
    assert a.forge_id == "writing"
    assert a.target == "projects_17/p1/forge/"
    assert a.kind == "content_artifact"
    assert a.files == ("RUNNABLE.md", "CHECKLIST.md")


def test_to_dict_is_superset_of_legacy_dict():
    """BC: to_dict() содержит ВСЕ ключи старого normalize_output dict."""
    run = _make_run()
    req = _make_request()
    a = Artifact.from_chain_run(run, req)
    d = a.to_dict()
    legacy_keys = {
        "id", "kind", "opportunity_id", "project_id", "capability",
        "factory_id", "forge_id", "target", "overall", "validation",
        "created_at",
    }
    assert legacy_keys <= set(d.keys())
    # новые ключи (надмножество)
    assert {"chain", "stage_count", "files", "project_root"} <= set(d.keys())


def test_to_chain_run_dict_is_1to1():
    run = _make_run(
        started_at="2026-08-22T12:00:00+00:00",
        finished_at="2026-08-22T12:01:00+00:00",
        validation_registry_status="loaded",
    )
    req = _make_request()
    a = Artifact.from_chain_run(run, req)
    cr = a.to_chain_run_dict()
    assert cr["project_id"] == "p1"
    assert cr["stage_count"] == 2
    assert cr["chain"][0]["role_id"] == "explainer"
    assert cr["validation_registry_status"] == "loaded"
    assert cr["started_at"] == "2026-08-22T12:00:00+00:00"
    assert cr["finished_at"] == "2026-08-22T12:01:00+00:00"
    assert cr["overall"] == "ok"


def test_round_trip_dict():
    run = _make_run()
    req = _make_request()
    a = Artifact.from_chain_run(run, req, files=("RUNNABLE.md",))
    d = a.to_dict()
    a2 = Artifact.from_dict(d)
    assert a2 == a
    assert a2.to_dict() == d


def test_artifact_dict_round_trip_preserves_chain_run_metadata():
    run = _make_run(
        started_at="2026-08-22T12:00:00+00:00",
        finished_at="2026-08-22T12:01:00+00:00",
        validation_registry_status="unreadable",
    )
    a = Artifact.from_chain_run(run, _make_request(), files=("RUNNABLE.md",))
    assert Artifact.from_dict(a.to_dict()) == a


def test_resolve_files_only_existing(tmp_path: Path):
    (tmp_path / "RUNNABLE.md").write_text("# r", encoding="utf-8")
    run = _make_run()
    req = _make_request()
    a = Artifact.from_chain_run(run, req, files=("RUNNABLE.md", "MISSING.md"))
    resolved = a.resolve_files(tmp_path)
    assert len(resolved) == 1
    assert resolved[0].name == "RUNNABLE.md"


def test_from_chain_run_accepts_dict_run():
    run_d = {
        "project_id": "p1",
        "project_root": "/tmp/p1",
        "stage_count": 1,
        "chain": [{"role_id": "explainer", "mode": "check_only", "status": "ok", "details": "d"}],
        "overall": "partial",
        "validation_summary": None,
    }
    req_d = {
        "opportunity_id": "opp-1",
        "project_id": "p1",
        "capability": "cap",
        "factory_id": "fac",
        "forge_id": "for",
        "output_spec": {"artifact_kind": "generic_artifact", "target": "t/"},
    }
    a = Artifact.from_chain_run(run_d, req_d)
    assert a.overall == "partial"
    assert a.stage_count == 1
    assert a.capability == "cap"
    assert a.kind == "generic_artifact"


def test_from_chain_run_unknown_overall_failsafe():
    run = _make_run(overall="weird-token")
    req = _make_request()
    a = Artifact.from_chain_run(run, req)
    # fail-safe: неизвестный токен → 'unknown', не краш
    assert a.overall == "unknown"


def test_resolve_files_rejects_path_traversal(tmp_path: Path):
    outside = tmp_path.parent / "outside-artifact.md"
    outside.write_text("outside", encoding="utf-8")
    a = Artifact(
        id="a", kind="generic_artifact", opportunity_id="o", project_id="p",
        capability="c", factory_id="f", forge_id="g", overall="ok",
        files=("../outside-artifact.md",),
    )
    assert a.resolve_files(tmp_path) == []


def test_factory_normalize_output_uses_artifact_contract():
    run = _make_run(
        started_at="2026-08-22T12:00:00+00:00",
        finished_at="2026-08-22T12:01:00+00:00",
        validation_registry_status="loaded",
    )
    result = BaseFactory().normalize_output(run, object(), _make_request())
    assert result["kind"] == "content_artifact"
    assert result["factory_id"] == "content"
    assert result["chain"][0]["role_id"] == "explainer"
    assert result["started_at"] == "2026-08-22T12:00:00+00:00"
    assert result["validation_registry_status"] == "loaded"


def test_from_chain_run_validation_summary_projection():
    class _VS:
        def to_dict(self):
            return {"overall": "ok", "role_reports": []}

    run = _make_run(validation_summary=_VS())
    req = _make_request()
    a = Artifact.from_chain_run(run, req)
    assert a.validation == {"overall": "ok", "role_reports": []}
