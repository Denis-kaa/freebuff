"""
Policy Engine — user-defined runtime selection policies for Freebuff.

Allows users to configure which Runtime should handle each capability,
with fallback chains, scoring weights, and constraints.

Spec: docs_10/core/RUNTIME_ABSTRACTION_SPECIFICATION.md
"""

from __future__ import annotations

from freebuff_plugin_03.policy.config import CapabilityPolicy, PolicyContext, PolicyRule
from freebuff_plugin_03.policy.conversational import (
    OverrideIntent,
    apply_override,
    parse_override_intent,
)
from freebuff_plugin_03.policy.engine import PolicyEngine, is_policy_override

__all__ = [
    "CapabilityPolicy",
    "OverrideIntent",
    "PolicyContext",
    "PolicyEngine",
    "PolicyRule",
    "apply_override",
    "is_policy_override",
    "parse_override_intent",
]
