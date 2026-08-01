"""Conversational User-Choice Override (правило 11, promt37).

Рантайм-механизм переопределения «используй X вместо Y» в диалоге:
пользователь пишет фразу естественным языком, система распознаёт интент
(какой Runtime назначить на какую capability) и применяет его через
PolicyEngine.set_preference — предпочтение сохраняется в runtime_05/policies.json
и учитывается model_gateway / orchestrator / MCP при следующем resolve.

Примеры поддерживаемых фраз:
  "use deepseek instead of claude for coding"
  "use claude-code for review"
  "используй deepseek-v4-flash для research"
  "для planning используй freebuff"
  "switch coding to claude-code"
  "назначь coding на freebuff"
  "use openclaw instead of claude"        (capability → DEFAULT_CAPABILITY)
"""

from __future__ import annotations

***REMOVED***
from dataclasses import dataclass
from typing import Any, Dict, Optional

# Capability по умолчанию, если в фразе она не указана (напр. «use X instead of Y»)
DEFAULT_CAPABILITY = "coding"

# Токен Runtime/модели: буквы, цифры, _, -, ., :, / (модели вида qwen2.5:1.5b, deepseek/deepseek-chat)
_RT = r"(?P<rt>[a-zа-яё0-9_\-.:/***REMOVED***+)"
_CAP = r"(?P<cap>[a-zа-яё0-9_\-***REMOVED***+)"
_ANY = r"[a-zа-яё0-9_\-.:/***REMOVED***+"

# Паттерны в порядке приоритета. kind определяет порядок извлечения (rt, cap).
_PATTERNS = [
    # EN: "use X [instead of Y***REMOVED*** for Z"
    (re.compile(rf"use\s+{_RT***REMOVED***(?:\s+instead\s+of\s+{_ANY***REMOVED***)?\s+for\s+{_CAP***REMOVED***", re.IGNORECASE), "rt_cap"),
    # RU: "используй X [вместо Y***REMOVED*** для Z"
    (re.compile(rf"используй\s+{_RT***REMOVED***(?:\s+вместо\s+{_ANY***REMOVED***)?\s+для\s+{_CAP***REMOVED***", re.IGNORECASE), "rt_cap"),
    # RU: "для Z используй X" / "для Z ставь X"
    (re.compile(rf"для\s+{_CAP***REMOVED***\s+(?:используй|ставь|возьми|поставь)\s+{_RT***REMOVED***", re.IGNORECASE), "cap_rt"),
    # EN/RU: "switch/set Z to X" / "переключи/назначь/поставь Z на X"
    (re.compile(rf"(?:switch|set|переключи|назначь|поставь)\s+{_CAP***REMOVED***\s+(?:to|на)\s+{_RT***REMOVED***", re.IGNORECASE), "cap_rt"),
    # EN/RU: "use X instead of Y" / "используй X вместо Y" (capability → default)
    (re.compile(rf"(?:use|используй)\s+{_RT***REMOVED***\s+(?:instead\s+of|вместо)\s+{_ANY***REMOVED***", re.IGNORECASE), "rt_only"),
    # EN: "use X for Z" (уже покрыто первым, но оставляем на случай регистра/пунктуации)
    (re.compile(rf"use\s+{_RT***REMOVED***\s+for\s+{_CAP***REMOVED***", re.IGNORECASE), "rt_cap"),
***REMOVED***


@dataclass
class OverrideIntent:
    """Распознанный интент переопределения из диалоговой фразы."""

    capability: str
    runtime: str
    previous_runtime: Optional[str***REMOVED*** = None
    message: str = ""
    matched_pattern: str = ""


def _normalize_runtime(raw: str) -> str:
    """Нормализует имя Runtime/модели: кавычки/пунктуация убираются, пробелы → '-', lowercase."""
    s = raw.strip().strip('"\'`').strip(".,;:!?()")
    s = re.sub(r"\s+", "-", s)
    return s.lower()


def parse_override_intent(message: str) -> Optional[OverrideIntent***REMOVED***:
    """Разбирает диалоговую фразу и возвращает OverrideIntent или None.

    Args:
        message: фраза пользователя, напр. «use deepseek instead of claude for coding»

    Returns:
        OverrideIntent (capability, runtime) или None, если интент не распознан.
    """
    if not message or not isinstance(message, str):
        return None

    # Кавычки — акценты, убираем для упрощения парсинга
    cleaned = re.sub(r'["\'`***REMOVED***', "", message)

    for pattern, kind in _PATTERNS:
        match = pattern.search(cleaned)
        if not match:
            continue
        groups = match.groupdict()

        if kind == "rt_cap":
            runtime = groups.get("rt", "")
            capability = groups.get("cap", "")
        elif kind == "cap_rt":
            runtime = groups.get("rt", "")
            capability = groups.get("cap", "")
        else:  # rt_only — capability по умолчанию
            runtime = groups.get("rt", "")
            capability = DEFAULT_CAPABILITY

        runtime = _normalize_runtime(runtime)
        capability = _normalize_runtime(capability)
        if not runtime or not capability:
            continue

        return OverrideIntent(
            capability=capability,
            runtime=runtime,
            message=message.strip(),
            matched_pattern=pattern.pattern,
        )

    return None


def apply_override(
    message: str,
    engine: Any,
    capability: Optional[str***REMOVED*** = None,
    dry_run: bool = False,
) -> Optional[Dict[str, Any***REMOVED******REMOVED***:
    """Применяет диалоговое переопределение через PolicyEngine (правило 11).

    Распознаёт интент в message и вызывает engine.set_preference() —
    предпочтение сохраняется в runtime_05/policies.json. Возвращает словарь
    с результатом или None, если интент не распознан.

    Args:
        message: фраза пользователя, напр. «use deepseek instead of claude for coding»
        engine: экземпляр PolicyEngine (duck-typing: get_policy/set_preference)
        capability: опционально — принудительная capability, переопределяет
            распознанную из фразы (нормализуется как имя Runtime/модели)
        dry_run: если True — только распознать интент и вернуть результат
            БЕЗ вызова set_preference (ничего не пишется в policies.json);
            `applied` в ответе = False

    Returns:
        {"applied": bool, "dry_run": bool, "capability": ..., "runtime": ...,
         "previous_runtime": ..., "matched": ...***REMOVED*** или None
    """
    intent = parse_override_intent(message)
    if intent is None:
        return None

    if capability:
        normalized_capability = _normalize_runtime(capability)
        if not normalized_capability:
            return None
        intent.capability = normalized_capability

    previous_runtime: Optional[str***REMOVED*** = None
    try:
        policy = engine.get_policy(intent.capability)
        if policy is not None:
            previous_runtime = getattr(policy, "preferred_runtime", None)
    except Exception:
        previous_runtime = None

    if not dry_run:
        engine.set_preference(intent.capability, intent.runtime)

    return {
        "applied": not dry_run,
        "dry_run": dry_run,
        "capability": intent.capability,
        "runtime": intent.runtime,
        "previous_runtime": previous_runtime,
        "matched": intent.matched_pattern,
        "message": intent.message,
    ***REMOVED***
