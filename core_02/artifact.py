#!/usr/bin/env python3
"""core_02/artifact.py — Единый Artifact-контракт (файл ↔ dict ↔ ChainRun).

Дизайн: ``docs_10/engineering-memory/ARTIFACT_CONTRACT_DESIGN_V1.md``.
Закрывает GAP P2 из ``ARCHITECTURE_DECISION_108_V1.md`` §H: FORGE→ARTIFACT
был PARTIAL (3 несвязанных представления результата), становится CONFIRMED
через единый канонический dataclass + двусторонние адаптеры.

Три текущих представления (НЕ переписываются — WRAP, CAN-16 additive):
  A. ``ChainRun`` (core_02/forge_facade.py:258) — детали исполнения:
     chain/stage_count/validation_summary.
  B. Artifact-dict из ``factory_base.normalize_output`` (core_02/factory_base.py:401)
     — домен-трассировка: capability/factory_id/forge_id/target.
  C. Файлы на диске (forge_pipeline._ensure_artifacts + DEFAULT_ROLE_OUTPUTS) —
     RUNNABLE.md / CHECKLIST.md / role-outputs в ``target``.

``Artifact`` — каноническое представление; ``to_dict()`` — надмножество B
(обратная совместимость: содержит ВСЕ ключи старого dict normalize_output);
``to_chain_run_dict()`` — 1:1 с A (для opp.artifacts / event payloads);
``resolve_files()`` — проекция на C (существующие файлы в target).

Закрытые словари (ANTI-6b): ``OVERALL_VALUES`` — допустимые overall;
kind берётся из существующих ARTIFACT_KIND токенов фабрик
(generic_artifact | content_artifact | research_report | verifier_report).
Неизвестный токен → ValueError в __post_init__ (дрейф = ошибка, не молча).

REGISTER-FIRST: artifact_contract зарегистрирован в data_13/missing_registry.yaml
(kind=module) до реализации.
"""

from __future__ import annotations

import datetime as _dt
import uuid
from dataclasses import dataclass, field
}
from typing import Any, Dict, List, Optional, Tuple


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


# Закрытый словарь overall (ANTI-6b) — mirror ChainRun/ForgeFacadeResult.
OVERALL_VALUES: frozenset[str] = frozenset(
    {"ok", "partial", "failed", "degraded", "unknown"}
)


@dataclass(frozen=True)
class Artifact:
    """Канонический артефакт Forge-исполнения. Проекция: файлы ↔ dict ↔ ChainRun.

    Поля сгруппированы по источнику (см. ARTIFACT_CONTRACT_DESIGN_V1.md §4):
      - Идентификация/домен — из B (factory_base.normalize_output).
      - Результат/исполнение — из A (ChainRun).
      - Физические файлы — из C (forge_pipeline / DEFAULT_ROLE_OUTPUTS).

    frozen=True: артефакт неизменяем после создания (traceability).
    """

    # ── Идентификация + домен (из B: factory_base.normalize_output) ────────
    id: str
    kind: str
    opportunity_id: str
    project_id: str
    capability: str               # closed-set токен (KNOWN_CAPABILITIES)
    factory_id: str               # адвизорный (traceability)
    forge_id: str                 # адвизорный (traceability)

    # ── Результат (из A: ChainRun) ─────────────────────────────────────────
    overall: str
    chain: Tuple[Dict[str, Any], ...] = ()          # ChainStage.to_dict() проекции
    stage_count: int = 0
    validation: Optional[Dict[str, Any] | str] = None  # ValidationSummary.to_dict()
    started_at: str = ""
    finished_at: str = ""
    validation_registry_status: str = "not_run"

    # ── Физические файлы (из C) ────────────────────────────────────────────
    target: str = ""              # "projects_17/<id>/forge/"
    files: Tuple[str, ...] = ()   # относительные пути созданных артефактов

    # ── Мета ───────────────────────────────────────────────────────────────
    created_at: str = field(default_factory=_now_iso)
    project_root: str = ""

    def __post_init__(self) -> None:
        """ANTI-6b: закрытый словарь overall. Дрейф = ValueError, не молча."""
        if self.overall not in OVERALL_VALUES:
            raise ValueError(
                f"overall={self.overall!r} вне закрытого словаря {sorted(OVERALL_VALUES)}"
            )

    # ── B: dict-проекция (надмножество factory_base.normalize_output) ──────

    def to_dict(self) -> Dict[str, Any]:
        """→ B. Содержит ВСЕ ключи старого dict normalize_output + chain/stage_count/files/project_root.

        BC-гарантия: существующие потребители (``_accumulate``, CLI) не ломаются.
        """
        return {
            "id": self.id,
            "kind": self.kind,
            "opportunity_id": self.opportunity_id,
            "project_id": self.project_id,
            "capability": self.capability,
            "factory_id": self.factory_id,
            "forge_id": self.forge_id,
            "target": self.target,
            "overall": self.overall,
            "validation": self.validation,
            # ── новые (надмножество) ──
            "chain": list(self.chain),
            "stage_count": self.stage_count,
            "files": list(self.files),
            "project_root": self.project_root,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "validation_registry_status": self.validation_registry_status,
            "created_at": self.created_at,
        }

    # ── A: ChainRun-dict-проекция (1:1) ─────────────────────────────────────

    def to_chain_run_dict(self) -> Dict[str, Any]:
        """→ A. 1:1 с ``ChainRun.to_dict()`` (для opp.artifacts / event payloads).

        Содержит все ключи ChainRun.to_dict() в том же виде; временные поля и
        статус registry сохраняются без потери.
        """
        return {
            "project_id": self.project_id,
            "project_root": self.project_root,
            "stage_count": self.stage_count,
            "chain": list(self.chain),
            "overall": self.overall,
            "started_at": self.started_at or self.created_at,
            "finished_at": self.finished_at or self.created_at,
            "validation_registry_status": self.validation_registry_status,
            "validation_summary": self.validation,
        }

    # ── C: файлы на диске ───────────────────────────────────────────────────

    def resolve_files(self, root: Path) -> List[Path]:
        """→ C. Существующие файлы из ``files`` относительно ``root``.

        Возвращает только реально существующие (Path.exists()); отсутствующие
        игнорируются — расхождение с диском видно через ``files`` vs результат.
        """
        base = Path(root).resolve()
        out: List[Path] = []
        for rel in self.files:
            candidate = (base / rel).resolve()
            try:
                candidate.relative_to(base)
            except ValueError:
                # Не допускаем абсолютные пути и path traversal в файловой проекции.
                continue
            if candidate.exists():
                out.append(candidate)
        return out

    # ── Фабрики ─────────────────────────────────────────────────────────────

    @classmethod
    def from_chain_run(
        cls,
        run: Any,
        request: Any,
        *,
        files: Tuple[str, ...] = (),
        artifact_id: str = "",
        created_at: str = "",
    ) -> "Artifact":
        """A+B+C → Artifact. Принимает ChainRun-подобный объект + ExecutionRequest.

        run: объект с атрибутами ChainRun (overall/chain/stage_count/
             validation_summary/project_id/project_root) ИЛИ dict (ChainRun.to_dict()).
        request: ExecutionRequest (или любой объект с полями opportunity_id/
                 project_id/capability/factory_id/forge_id/output_spec) ИЛИ dict.
        files: относительные пути созданных артефактов (C).
        artifact_id: явный id (если '' — генерируется ``art-<uuid10>``).
        created_at: явная метка (если '' — now_iso).
        """
        # ChainRun-объект или dict
        if isinstance(run, dict):
            run_d = run
        else:
            run_d = {
                "project_id": getattr(run, "project_id", ""),
                "project_root": getattr(run, "project_root", ""),
                "stage_count": getattr(run, "stage_count", 0),
                "chain": [
                    s.to_dict() if hasattr(s, "to_dict") else dict(s)
                    for s in (getattr(run, "chain", ()) or ())
                ],
                "overall": getattr(run, "overall", "unknown"),
                "started_at": getattr(run, "started_at", ""),
                "finished_at": getattr(run, "finished_at", ""),
                "validation_registry_status": getattr(run, "validation_registry_status", "not_run"),
                "validation_summary": getattr(run, "validation_summary", None),
            }
        # ExecutionRequest-объект или dict
        if isinstance(request, dict):
            req_d = request
        else:
            output_spec = getattr(request, "output_spec", {}) or {}
            req_d = {
                "opportunity_id": getattr(request, "opportunity_id", ""),
                "project_id": getattr(request, "project_id", ""),
                "capability": getattr(request, "capability", ""),
                "factory_id": getattr(request, "factory_id", ""),
                "forge_id": getattr(request, "forge_id", ""),
                "output_spec": output_spec,
            }

        vs = run_d.get("validation_summary")
        validation: Optional[Dict[str, Any] | str] = None
        if vs is not None:
            if isinstance(vs, dict):
                validation = dict(vs)
            elif hasattr(vs, "to_dict"):
                validation = vs.to_dict()
            else:
                validation = str(vs)

        chain_raw = run_d.get("chain", ()) or ()
        chain: Tuple[Dict[str, Any], ...] = tuple(
            dict(c) if isinstance(c, dict) else (c.to_dict() if hasattr(c, "to_dict") else {"raw": str(c)})
            for c in chain_raw
        )

        overall = str(run_d.get("overall") or "unknown")
        if overall not in OVERALL_VALUES:
            # fail-safe: unknown токен → 'unknown' (не краш); дрейф виден в validation
            overall = "unknown"

        output_spec = req_d.get("output_spec") or {}
        target = output_spec.get("target", "") if isinstance(output_spec, dict) else ""
        kind = (
            output_spec.get("artifact_kind", "generic_artifact")
            if isinstance(output_spec, dict)
            else "generic_artifact"
        )

        return cls(
            id=artifact_id or f"art-{_uuid10()}",
            kind=str(kind),
            opportunity_id=str(req_d.get("opportunity_id", "") or ""),
            project_id=str(req_d.get("project_id", "") or ""),
            capability=str(req_d.get("capability", "") or ""),
            factory_id=str(req_d.get("factory_id", "") or ""),
            forge_id=str(req_d.get("forge_id", "") or ""),
            overall=overall,
            chain=chain,
            stage_count=int(run_d.get("stage_count", len(chain)) or len(chain)),
            validation=validation,
            target=target,
            files=tuple(files),
            created_at=created_at or _now_iso(),
            project_root=str(run_d.get("project_root", "") or ""),
            started_at=str(run_d.get("started_at", "") or ""),
            finished_at=str(run_d.get("finished_at", "") or ""),
            validation_registry_status=str(
                run_d.get("validation_registry_status", "not_run") or "not_run"
            ),
        )

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Artifact":
        """B → Artifact (round-trip c to_dict()). Неизвестные ключи игнорируются."""
        known = {k: v for k, v in d.items() if k in {
            "id", "kind", "opportunity_id", "project_id", "capability",
            "factory_id", "forge_id", "overall", "chain", "stage_count",
            "validation", "target", "files", "created_at", "project_root",
            "started_at", "finished_at", "validation_registry_status",
        ]]
        # нормализация списков → кортежи
        if isinstance(known.get("chain"), list):
            known["chain"] = tuple(known["chain"])
        if isinstance(known.get("files"), list):
            known["files"] = tuple(known["files"])
        return cls(**known)


def _uuid10() -> str:
    return uuid.uuid4().hex[:10]
