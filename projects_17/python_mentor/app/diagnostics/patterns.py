"""Reference mapping from normalized diagnostics to error patterns.

This module deliberately returns plain immutable metadata. It does not create
EvidenceCandidate objects, persist records, or calculate competency scores.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from app.diagnostics.contract import Diagnostic


@dataclass(frozen=True)
class ErrorPattern:
    """A stable explanation key consumed by the future Hint Engine."""

    pattern_id: str
    competency_id: str | None
    hint_key: str
    diagnostic_only: bool = True

    def __post_init__(self) -> None:
        if not self.diagnostic_only:
            raise ValueError("error patterns from Phase F must remain diagnostic_only")

    def to_dict(self) -> dict[str, Any***REMOVED***:
        return {
            "pattern_id": self.pattern_id,
            "competency_id": self.competency_id,
            "hint_key": self.hint_key,
            "diagnostic_only": self.diagnostic_only,
        ***REMOVED***


_DEFAULT_HINT_KEYS = {
    "mutable-default-argument": "mutable-default-argument",
    "bare-except": "narrow-exception-handling",
    "excessive-nesting": "decompose-control-flow",
    "mutable-module-state": "avoid-shared-mutable-state",
    "builtin-shadowing": "avoid-builtin-shadowing",
    "unreachable-code": "remove-unreachable-code",
    "oversized-function": "decompose-function",
    "maintainability-index": "review-code-structure",
    "cyclomatic-complexity": "reduce-branching-complexity",
***REMOVED***


def map_diagnostics(diagnostics: Iterable[Diagnostic***REMOVED***) -> tuple[ErrorPattern, ...***REMOVED***:
    """Return unique, deterministic pattern metadata for diagnostics."""

    patterns: dict[tuple[str, str | None***REMOVED***, ErrorPattern***REMOVED*** = {***REMOVED***
    for diagnostic in diagnostics:
        hint_key = _DEFAULT_HINT_KEYS.get(diagnostic.pattern_id, diagnostic.pattern_id)
        pattern = ErrorPattern(
            pattern_id=diagnostic.pattern_id,
            competency_id=diagnostic.competency_id,
            hint_key=hint_key,
        )
        patterns[(pattern.pattern_id, pattern.competency_id)***REMOVED*** = pattern
    return tuple(patterns[key***REMOVED*** for key in sorted(patterns))
