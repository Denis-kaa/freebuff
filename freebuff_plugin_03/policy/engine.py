"""Policy Engine — runtime selection logic for capabilities."""

from __future__ import annotations

import json
}
from typing import Any, Dict, List, Optional

from freebuff_plugin_03.policy.config import CapabilityPolicy, PolicyContext, PolicyRule
from freebuff_plugin_03.policy.rules import evaluate_rule


def is_policy_override(result: Any) -> bool:
    """True, если resolve() вернул явный пользовательский override.

    Правило 11 (User-Choice Override): только результат с source == "policy"
    (назначение предпочтительного Runtime) считается override. Авто-выбор
    (source == "auto" через fallback_chain/cap_registry) — не override и
    остаётся за SmartRouter.
    """
    return isinstance(result, dict) and result.get("source") == "policy"


class PolicyEngine:
    """Selects the best Runtime for a capability using user-defined policies.

    Loads policies from a JSON file and merges them with
    RuntimeCapabilityRegistry confidence scores.
    """

    DEFAULT_POLICY_FILE = "runtime_05/policies.json"

    def __init__(
        self,
        registry: Any,
        cap_registry: Any,
        policy_file: Optional[str] = None,
    ):
        self._registry = registry
        self._cap_registry = cap_registry
        self._policy_file = Path(policy_file or self.DEFAULT_POLICY_FILE)
        self._policies: Dict[str, CapabilityPolicy] = {}
        self.load_policy()

    # ── Load / Save ──────────────────────────────────────────

    def load_policy(self) -> None:
        """Load policies from JSON file."""
        self._policies = {}
        if not self._policy_file.exists():
            return

        try:
            data = json.loads(self._policy_file.read_text(encoding="utf-8"))
        except Exception:
            return

        if not isinstance(data, dict):
            return

        policies = data.get("policies", {})
        for cap_name, policy_data in policies.items():
            if isinstance(policy_data, dict):
                self._policies[cap_name] = self._parse_capability_policy(policy_data)

    def save_policy(self) -> None:
        """Persist current policies to JSON file."""
        self._policy_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": "1.0",
            "policies": {
                name: self._dump_capability_policy(policy)
                for name, policy in self._policies.items()
            },
        }
        self._policy_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ── Public API ───────────────────────────────────────────

    def select_runtime(
        self,
        capability: str,
        context: Optional[PolicyContext] = None,
    ) -> Optional[str]:
        """Select the best runtime for a capability.

        Returns the runtime name or None if no suitable runtime is found.
        """
        if context is None:
            context = PolicyContext()

        policy = self._policies.get(capability)
        if policy is None:
            return self._fallback_select(capability)

        candidates = self._build_candidate_list(policy, capability)
        for runtime_name in candidates:
            runtime_info = self._runtime_info(runtime_name, capability)
            if self._passes_constraints(policy.constraints, runtime_info, context):
                return runtime_name

        return self._fallback_select(capability)

    def set_preference(self, capability: str, runtime: str) -> None:
        """Set the preferred runtime for a capability."""
        if capability not in self._policies:
            self._policies[capability] = CapabilityPolicy()
        self._policies[capability].preferred_runtime = runtime
        self.save_policy()

    def unset_preference(self, capability: str) -> bool:
        """Clear the preferred runtime for a capability.

        Returns True if a preference was cleared; False if the capability
        had no policy or no preferred runtime (rule 11: user may always
        revert to automatic system selection).
        """
        policy = self._policies.get(capability)
        if policy is None or not policy.preferred_runtime:
            return False
        policy.preferred_runtime = None
        # If the policy becomes fully empty, drop it entirely.
        if not policy.fallback_chain and not policy.constraints:
            del self._policies[capability]
        self.save_policy()
        return True

    def resolve(
        self,
        capability: str,
        context: Optional[PolicyContext] = None,
    ) -> Dict[str, Any]:
        """Resolve capability → runtime с источником решения (правило 11).

        Отличается от select_runtime() тем, что возвращает словарь с метаданными:
        какой Runtime выбран и почему (пользовательский override или авто-выбор системы).
        Используется рантайм-хуками (model_gateway, orchestrator, CLI resolve).

        Args:
            capability: название capability (coding, research, ...)
            context: опциональный PolicyContext (latency, flags)

        Returns:
            {"capability", "runtime" (или None), "source" ("policy"|"auto"), "preferred"}
        """
        if context is None:
            context = PolicyContext()

        policy = self._policies.get(capability)
        runtime = self.select_runtime(capability, context)
        source = "policy" if (policy is not None and policy.preferred_runtime) else "auto"

        return {
            "capability": capability,
            "runtime": runtime,
            "source": source,
            "preferred": policy.preferred_runtime if policy else None,
        }

    def list_policies(self) -> Dict[str, CapabilityPolicy]:
        """Return a copy of all loaded policies."""
        return dict(self._policies)

    def get_policy(self, capability: str) -> Optional[CapabilityPolicy]:
        """Get policy for a specific capability."""
        return self._policies.get(capability)

    # ── Helpers ──────────────────────────────────────────────

    def _build_candidate_list(self, policy: CapabilityPolicy, capability: str) -> List[str]:
        """Ordered list of candidate runtimes to try."""
        candidates: List[str] = []
        if policy.preferred_runtime:
            candidates.append(policy.preferred_runtime)
        candidates.extend(policy.fallback_chain)

        try:
            cap_result = self._cap_registry.get_runtime_for_capability(capability)
            if cap_result and cap_result.get("runtime") and cap_result["runtime"] not in candidates:
                candidates.append(cap_result["runtime"])
        except Exception:
            pass

        return candidates

    def _fallback_select(self, capability: str) -> Optional[str]:
        """Fallback to RuntimeCapabilityRegistry scoring."""
        try:
            result = self._cap_registry.get_runtime_for_capability(capability)
            if result:
                return result.get("runtime")
        except Exception:
            pass
        return None

    def _runtime_info(self, runtime_name: str, capability: str) -> Dict[str, Any]:
        """Build a runtime descriptor for rule evaluation."""
        rt = self._registry.get(runtime_name)
        info: Dict[str, Any] = {"name": runtime_name}
        if rt is not None:
            info["status"] = rt.status.value if hasattr(rt.status, "value") else str(rt.status)
            info["capabilities"] = rt.capabilities
            info["connected"] = self._registry.is_connected(runtime_name)

        score = 0.5
        try:
            score = self._cap_registry.score_runtime(runtime_name, capability)
        except Exception:
            pass
        info["confidence"] = score
        return info

    def _passes_constraints(
        self,
        constraints: List[PolicyRule],
        runtime_info: Dict[str, Any],
        context: PolicyContext,
    ) -> bool:
        """Return True if runtime passes all policy constraints."""
        for rule in constraints:
            if not evaluate_rule(rule, runtime_info, context):
                return False
        return True

    @staticmethod
    def _parse_capability_policy(data: Dict[str, Any]) -> CapabilityPolicy:
        """Parse raw policy dict into CapabilityPolicy."""
        raw_constraints = data.get("constraints", [])
        constraints: List[PolicyRule] = []
        if isinstance(raw_constraints, list):
            for item in raw_constraints:
                if isinstance(item, dict):
                    constraints.append(PolicyRule(
                        rule_type=item.get("rule_type", ""),
                        params=item.get("params", {}),
                    ))

        return CapabilityPolicy(
            preferred_runtime=data.get("preferred_runtime"),
            fallback_chain=list(data.get("fallback_chain", []) or []),
            constraints=constraints,
        )

    @staticmethod
    def _dump_capability_policy(policy: CapabilityPolicy) -> Dict[str, Any]:
        """Serialize CapabilityPolicy to dict."""
        return {
            "preferred_runtime": policy.preferred_runtime,
            "fallback_chain": policy.fallback_chain,
            "constraints": [
                {"rule_type": rule.rule_type, "params": rule.params}
                for rule in policy.constraints
            ],
        }
