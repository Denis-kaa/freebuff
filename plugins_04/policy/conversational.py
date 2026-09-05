"""Conversational User-Choice Override (правило 11, promt37).

Распознавание фраз вида «use deepseek instead of claude for coding» /
«используй freebuff для research» / «для planning используй freebuff» /
«switch coding to claude-code» и применение через PolicyEngine.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Optional, Tuple

from . import PolicyEngine

DEFAULT_CAPABILITY = "coding"

# Токен runtime: слова с дефисами/точками (deepseek-v4-flash, claude-code).
# Capability: одиночное слово (\w включает кириллицу).
_TOKEN = r"[\w][\w.-]*"
_CAP = r"\w+"

# (pattern, extractor) — порядок важен: вместо-паттерн ДО простого "use X for Y".
_PATTERNS: list = [
    # use X instead of [Y] [for C]
    (
        re.compile(
            rf"use\s+({_TOKEN})\s+instead\s+of\s+{_TOKEN}(?:\s+for\s+({_CAP}))?",
            re.IGNORECASE,
        ),
        lambda m: (m.group(1), m.group(2) or DEFAULT_CAPABILITY),
    ),
    # use X for C
    (
        re.compile(rf"use\s+({_TOKEN})\s+for\s+({_CAP})", re.IGNORECASE),
        lambda m: (m.group(1), m.group(2)),
    ),
    # switch C to X
    (
        re.compile(rf"switch\s+({_CAP})\s+to\s+({_TOKEN})", re.IGNORECASE),
        lambda m: (m.group(2), m.group(1)),
    ),
    # используй X для C
    (
        re.compile(rf"используй\s+({_TOKEN})\s+для\s+({_CAP})", re.IGNORECASE),
        lambda m: (m.group(1), m.group(2)),
    ),
    # для C используй X
    (
        re.compile(rf"для\s+({_CAP})\s+используй\s+({_TOKEN})", re.IGNORECASE),
        lambda m: (m.group(2), m.group(1)),
    ),
]


@dataclass
class OverrideIntent:
    """Распознанный интент переопределения."""

    runtime: str
    capability: str


def parse_override_intent(message: Any) -> Optional[OverrideIntent]:
    """Распознать фразу переопределения. Не-фраза → None."""
    if not isinstance(message, str):
        return None
    text = message.strip()
    if not text:
        return None
    for pattern, extract in _PATTERNS:
        m = pattern.search(text)
        if m:
            runtime, capability = extract(m)  # type: Tuple[str, str]
            if runtime and capability:
                # Фолд регистра: «DEEPSEEK» и «deepseek» — один токен
                return OverrideIntent(runtime=runtime.lower(),
                                      capability=capability.lower())
            return OverrideIntent(runtime=runtime, capability=capability)
    return None


def apply_override(
    message: str,
    engine: Optional[PolicyEngine],
    capability: Optional[str] = None,
    dry_run: bool = False,
) -> Optional[dict]:
    """Применить диалоговое переопределение.

    Args:
        message: фраза пользователя.
        engine: PolicyEngine или None (None допустим только с dry_run=True).
        capability: форсировать capability вместо распознанной.
        dry_run: распознать и показать, НЕ записывать.

    Returns:
        dict {applied, dry_run, capability, runtime, previous_runtime, matched}
        или None если фраза не распознана / engine нет без dry_run.
    """
    intent = parse_override_intent(message)
    if intent is None:
        return None

    cap = capability or intent.capability

    previous: Optional[str] = None
    if engine is not None:
        try:
            existing = engine.get_policy(cap)
            previous = existing.preferred_runtime if existing else None
        except Exception:
            previous = None

    result = {
        "applied": False,
        "dry_run": bool(dry_run),
        "capability": cap,
        "runtime": intent.runtime,
        "previous_runtime": previous,
        "matched": True,
    }

    if dry_run:
        return result  # engine не требуется — ничего не пишем
    if engine is None:
        return None  # реальное применение без движка невозможно

    engine.set_preference(cap, intent.runtime)
    result["applied"] = True
    return result
