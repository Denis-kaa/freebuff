"""
Policy Engine — user-defined runtime selection policies for Freebuff.

Allows users to configure which Runtime should handle each capability,
with fallback chains, scoring weights, and constraints.

Spec: docs/core/RUNTIME_ABSTRACTION_SPECIFICATION.md
"""

from __future__ import annotations

from freebuff_plugin.policy.config import CapabilityPolicy, PolicyContext, PolicyRule
from freebuff_plugin.policy.engine import PolicyEngine

__all__ = [
    "CapabilityPolicy",
    "PolicyContext",
    "PolicyEngine",
    "PolicyRule",
***REMOVED***
