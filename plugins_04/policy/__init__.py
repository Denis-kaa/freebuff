"""Policy Engine — User-Choice Override (правило 11, promt37, ADR-009).

Восстановлен v5.189.87 по контракту тестов tests_09/test_policy_*.py
(исходник утрачен при консолидации freebuff_plugin_03 → plugins_04).

API:
    PolicyRule(rule_type, params)          — constraint-правило
    CapabilityPolicy(preferred_runtime,    — политика одной capability
                      fallback_chain, constraints)
    PolicyContext(max_latency_ms, required_flags, exclude)
    PolicyEngine(runtime_registry,         — движок: load/select/resolve/
                capability_registry,         set_preference/unset_preference
                policy_file=None)
    is_policy_override(resolve_result)     — source == "policy"
    apply_override / parse_override_intent — см. conversational.py

Хранение: policies.json вида
    {"version": "1.0",
     "policies": {"coding": {"preferred_runtime": "claude-code",
                             "fallback_chain": [...],
                             "constraints": [{"rule_type": ...,
                                              "params": {...}}]}}}
Отсутствующий/битый файл → пустой набор политик (graceful).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

WORKSPACE = Path(__file__).resolve().parent.parent.parent
DEFAULT_POLICY_FILE = WORKSPACE / "runtime_05" / "policies.json"


# ═══════════════════════════════════════════════════════════════
# Data types
# ═══════════════════════════════════════════════════════════════


class PolicyRule:
    """Constraint-правило: rule_type + params (см. rules.evaluate_rule)."""

    def __init__(self, rule_type: str, params: Optional[Dict[str, Any]] = None):
        if not rule_type or not isinstance(rule_type, str):
            raise ValueError("rule_type must be a non-empty string")
        self.rule_type = rule_type
        self.params = dict(params or {})

    def to_dict(self) -> Dict[str, Any]:
        return {"rule_type": self.rule_type, "params": dict(self.params)}

    def __repr__(self) -> str:  # pragma: no cover — debug helper
        return f"PolicyRule({self.rule_type!r}, {self.params!r})"


@dataclass
class CapabilityPolicy:
    """Политика одной capability."""

    preferred_runtime: Optional[str] = None
    fallback_chain: list = field(default_factory=list)
    constraints: list = field(default_factory=list)  # PolicyRule | dict

    @property
    def is_empty(self) -> bool:
        return (
            not self.preferred_runtime
            and not self.fallback_chain
            and not self.constraints
        )


@dataclass
class PolicyContext:
    """Контекст запроса для constraint-оценки."""

    max_latency_ms: int = 5000
    required_flags: list = field(default_factory=list)
    exclude: list = field(default_factory=list)


def is_policy_override(resolve_result: Any) -> bool:
    """True если resolve() вернул явно пользовательский override."""
    return bool(resolve_result) and resolve_result.get("source") == "policy"


# ═══════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════


class PolicyEngine:
    """Резолв capability → runtime с приоритетом пользовательского выбора.

    Порядок (select_runtime):
      1. preferred_runtime политики, ЕСЛИ проходит все constraints;
      2. иначе fallback_chain по порядку (с той же проверкой);
      3. иначе auto-выбор через capability_registry.
    """

    def __init__(
        self,
        runtime_registry: Any,
        capability_registry: Any,
        policy_file: str | Path | None = None,
    ):
        self._runtime_registry = runtime_registry
        self._cap_registry = capability_registry
        self.policy_file = Path(policy_file) if policy_file else DEFAULT_POLICY_FILE
        self._policies: Dict[str, CapabilityPolicy] = {}
        self._load()

    # ---- persistence -------------------------------------------------

    def _load(self) -> None:
        """Загрузить policies.json. Missing/malformed → {} (graceful)."""
        self._policies = {}
        try:
            raw = self.policy_file.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (OSError, ValueError):
            return
        if not isinstance(data, dict):
            return
        for cap, spec in (data.get("policies") or {}).items():
            if not isinstance(spec, dict):
                continue
            self._policies[cap] = CapabilityPolicy(
                preferred_runtime=spec.get("preferred_runtime"),
                fallback_chain=list(spec.get("fallback_chain") or []),
                constraints=list(spec.get("constraints") or []),
            )

    def _save(self) -> None:
        serialized = {
            cap: self._dump_capability_policy(p)
            for cap, p in self._policies.items()
        }
        self.policy_file.parent.mkdir(parents=True, exist_ok=True)
        self.policy_file.write_text(
            json.dumps(
                {"version": "1.0", "policies": serialized},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        try:
            self._load()  # reload из канонического файла (single source of truth)
        except Exception:  # pragma: no cover — defensive
            pass

    @staticmethod
    def _dump_capability_policy(policy: CapabilityPolicy) -> Dict[str, Any]:
        def _dump_constraint(c: Any) -> Dict[str, Any]:
            return c.to_dict() if isinstance(c, PolicyRule) else dict(c)

        return {
            "preferred_runtime": policy.preferred_runtime,
            "fallback_chain": list(policy.fallback_chain),
            "constraints": [_dump_constraint(c) for c in policy.constraints],
        }

    # ---- read API ----------------------------------------------------

    def list_policies(self) -> Dict[str, CapabilityPolicy]:
        return dict(self._policies)

    def get_policy(self, capability: str) -> Optional[CapabilityPolicy]:
        return self._policies.get(capability)

    def select_runtime(self, capability: str) -> Optional[str]:
        from .rules import evaluate_all

        ctx = PolicyContext()
        policy = self._policies.get(capability)

        candidates: List[str] = []
        if policy and policy.preferred_runtime:
            candidates.append(policy.preferred_runtime)
        if policy:
            candidates.extend(policy.fallback_chain)

        for runtime in candidates:
            info = self._runtime_info(runtime, capability)
            if evaluate_all(policy.constraints if policy else [], info, ctx):
                return runtime

        # auto-выбор через capability registry
        try:
            res = self._cap_registry.get_runtime_for_capability(capability) or {}
            auto_runtime = res.get("runtime")
            return str(auto_runtime) if auto_runtime is not None else None
        except Exception:
            return None

    def resolve(self, capability: str) -> Dict[str, Any]:
        """Source-aware резолв: "policy" (явный override) или "auto"."""
        policy = self._policies.get(capability)
        if policy and policy.preferred_runtime:
            return {
                "capability": capability,
                "runtime": policy.preferred_runtime,
                "source": "policy",
                "preferred": policy.preferred_runtime,
            }
        return {
            "capability": capability,
            "runtime": self.select_runtime(capability),
            "source": "auto",
            "preferred": None,
        }

    def score_runtime(self, runtime_name: str, capability: str) -> float:
        """Прокси к capability registry (0.0 при недоступности)."""
        try:
            return float(self._cap_registry.score_runtime(runtime_name, capability))
        except Exception:
            return 0.0

    def _runtime_info(self, runtime_name: str, capability: str) -> Dict[str, Any]:
        info: Dict[str, Any] = {
            "name": runtime_name,
            "confidence": self.score_runtime(runtime_name, capability),
        }
        try:
            rt = self._runtime_registry.get(runtime_name)
            if rt is not None:
                status = getattr(getattr(rt, "status", None), "value", None)
                info["connected"] = status == "connected"
        except Exception:
            pass
        return info

    # ---- write API -----------------------------------------------------

    def set_preference(self, capability: str, runtime: str) -> None:
        policy = self._policies.setdefault(capability, CapabilityPolicy())
        policy.preferred_runtime = runtime
        self._save()

    def unset_preference(self, capability: str) -> bool:
        """Снять preferred_runtime. Политика без chain/constraints удаляется.

        Returns False если политики нет или preferred уже снят.
        """
        policy = self._policies.get(capability)
        if policy is None or not policy.preferred_runtime:
            return False
        policy.preferred_runtime = None
        if policy.is_empty:
            del self._policies[capability]
        self._save()
        return True


# Реэкспорт conversational API (импорт В КОНЦЕ — движок уже определён,
# поэтому `from . import PolicyEngine` в conversational не циклит).
from .conversational import apply_override, parse_override_intent  # noqa: E402,F401
