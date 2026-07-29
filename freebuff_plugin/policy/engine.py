"""Policy Engine — runtime selection logic for capabilities."""

from __future__ import annotations

import json
***REMOVED***
from typing import Any, Dict, List, Optional

from freebuff_plugin.policy.config import CapabilityPolicy, PolicyContext, PolicyRule
from freebuff_plugin.policy.rules import evaluate_rule


class PolicyEngine:
    """Selects the best Runtime for a capability using user-defined policies.

    Loads policies from a JSON file and merges them with
    RuntimeCapabilityRegistry confidence scores.
    """

    DEFAULT_POLICY_FILE = "runtime/policies.json"

    def __init__(
        self,
        registry: Any,
        cap_registry: Any,
        policy_file: Optional[str***REMOVED*** = None,
    ):
        self._registry = registry
        self._cap_registry = cap_registry
        self._policy_file = Path(policy_file or self.DEFAULT_POLICY_FILE)
        self._policies: Dict[str, CapabilityPolicy***REMOVED*** = {***REMOVED***
        self.load_policy()

    # ── Load / Save ──────────────────────────────────────────

    def load_policy(self) -> None:
        """Load policies from JSON file."""
        self._policies = {***REMOVED***
        if not self._policy_file.exists():
            return

        try:
            data = json.loads(self._policy_file.read_text(encoding="utf-8"))
        except Exception:
            return

        if not isinstance(data, dict):
            return

        policies = data.get("policies", {***REMOVED***)
        for cap_name, policy_data in policies.items():
            if isinstance(policy_data, dict):
                self._policies[cap_name***REMOVED*** = self._parse_capability_policy(policy_data)

    def save_policy(self) -> None:
        """Persist current policies to JSON file."""
        self._policy_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": "1.0",
            "policies": {
                name: self._dump_capability_policy(policy)
                for name, policy in self._policies.items()
            ***REMOVED***,
        ***REMOVED***
        self._policy_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ── Public API ───────────────────────────────────────────

    def select_runtime(
        self,
        capability: str,
        context: Optional[PolicyContext***REMOVED*** = None,
    ) -> Optional[str***REMOVED***:
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
            self._policies[capability***REMOVED*** = CapabilityPolicy()
        self._policies[capability***REMOVED***.preferred_runtime = runtime
        self.save_policy()

    def list_policies(self) -> Dict[str, CapabilityPolicy***REMOVED***:
        """Return a copy of all loaded policies."""
        return dict(self._policies)

    def get_policy(self, capability: str) -> Optional[CapabilityPolicy***REMOVED***:
        """Get policy for a specific capability."""
        return self._policies.get(capability)

    # ── Helpers ──────────────────────────────────────────────

    def _build_candidate_list(self, policy: CapabilityPolicy, capability: str) -> List[str***REMOVED***:
        """Ordered list of candidate runtimes to try."""
        candidates: List[str***REMOVED*** = [***REMOVED***
        if policy.preferred_runtime:
            candidates.append(policy.preferred_runtime)
        candidates.extend(policy.fallback_chain)

        try:
            cap_result = self._cap_registry.get_runtime_for_capability(capability)
            if cap_result and cap_result.get("runtime") and cap_result["runtime"***REMOVED*** not in candidates:
                candidates.append(cap_result["runtime"***REMOVED***)
        except Exception:
            pass

        return candidates

    def _fallback_select(self, capability: str) -> Optional[str***REMOVED***:
        """Fallback to RuntimeCapabilityRegistry scoring."""
        try:
            result = self._cap_registry.get_runtime_for_capability(capability)
            if result:
                return result.get("runtime")
        except Exception:
            pass
        return None

    def _runtime_info(self, runtime_name: str, capability: str) -> Dict[str, Any***REMOVED***:
        """Build a runtime descriptor for rule evaluation."""
        rt = self._registry.get(runtime_name)
        info: Dict[str, Any***REMOVED*** = {"name": runtime_name***REMOVED***
        if rt is not None:
            info["status"***REMOVED*** = rt.status.value if hasattr(rt.status, "value") else str(rt.status)
            info["capabilities"***REMOVED*** = rt.capabilities
            info["connected"***REMOVED*** = self._registry.is_connected(runtime_name)

        score = 0.5
        try:
            score = self._cap_registry.score_runtime(runtime_name, capability)
        except Exception:
            pass
        info["confidence"***REMOVED*** = score
        return info

    def _passes_constraints(
        self,
        constraints: List[PolicyRule***REMOVED***,
        runtime_info: Dict[str, Any***REMOVED***,
        context: PolicyContext,
    ) -> bool:
        """Return True if runtime passes all policy constraints."""
        for rule in constraints:
            if not evaluate_rule(rule, runtime_info, context):
                return False
        return True

    @staticmethod
    def _parse_capability_policy(data: Dict[str, Any***REMOVED***) -> CapabilityPolicy:
        """Parse raw policy dict into CapabilityPolicy."""
        raw_constraints = data.get("constraints", [***REMOVED***)
        constraints: List[PolicyRule***REMOVED*** = [***REMOVED***
        if isinstance(raw_constraints, list):
            for item in raw_constraints:
                if isinstance(item, dict):
                    constraints.append(PolicyRule(
                        rule_type=item.get("rule_type", ""),
                        params=item.get("params", {***REMOVED***),
                    ))

        return CapabilityPolicy(
            preferred_runtime=data.get("preferred_runtime"),
            fallback_chain=list(data.get("fallback_chain", [***REMOVED***) or [***REMOVED***),
            constraints=constraints,
        )

    @staticmethod
    def _dump_capability_policy(policy: CapabilityPolicy) -> Dict[str, Any***REMOVED***:
        """Serialize CapabilityPolicy to dict."""
        return {
            "preferred_runtime": policy.preferred_runtime,
            "fallback_chain": policy.fallback_chain,
            "constraints": [
                {"rule_type": rule.rule_type, "params": rule.params***REMOVED***
                for rule in policy.constraints
            ***REMOVED***,
        ***REMOVED***
