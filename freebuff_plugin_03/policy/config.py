"""Policy Engine — data classes and configuration types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PolicyRule:
    """Constraint rule applied when selecting a runtime."""

    rule_type: str  # e.g., 'max_latency', 'exclude', 'required_flags', 'min_confidence'
    params: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.rule_type:
            raise ValueError("PolicyRule.rule_type cannot be empty")


@dataclass
class CapabilityPolicy:
    """Policy for a single capability: which runtime to prefer and how to fall back."""

    preferred_runtime: Optional[str] = None
    fallback_chain: List[str] = field(default_factory=list)
    constraints: List[PolicyRule] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.fallback_chain is None:
            self.fallback_chain = []
        if self.constraints is None:
            self.constraints = []


@dataclass
class PolicyContext:
    """Runtime request context used to evaluate policies."""

    max_latency_ms: int = 5000
    required_flags: List[str] = field(default_factory=list)
    exclude: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.required_flags is None:
            self.required_flags = []
        if self.exclude is None:
            self.exclude = []
