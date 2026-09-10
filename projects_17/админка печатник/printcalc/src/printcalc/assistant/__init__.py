"""Слой ассистента ресепшена: intents из исследования (research/).

Источник данных: «админка печатник/research/» (12_intents.json,
11_nefteyugansk.md TOP-20 MVP, 04_customer_requests.md, 14_dialog_rules.md).
Модуль аддитивный: ничего в существующих калькуляторах не меняет; связка с
ними — через calculator_id (может быть None, если калькулятора ещё нет).

Принципы (как в engine): закрытый реестр (ANTI-6b) — неизвестный/дубликат
intent id — ошибка, без silent fallback. Формулировки клиентов — только
реальные, с источником; у части intents верифицированных формулировок нет —
это честно помечено phrases_verified=False (промт §2 запрещает выдумывать).
"""

from __future__ import annotations

from printcalc.assistant.intents import (
    AssistantIntentRegistry,
    AssistantIntentSpec,
    MvpPriority,
    SynonymMatch,
    SynonymToken,
    UNMAPPED_RESEARCH_INTENTS,
    clarification_for,
    build_default_registry,
    intent_sources,
    match_intent,
    match_synonym,
    missing_required,
    warnings_for,
)
from printcalc.assistant.intents import INTENT_IDS_TOP20, SYNONYM_TABLE

__all__ = [
    "AssistantIntentRegistry",
    "AssistantIntentSpec",
    "MvpPriority",
    "INTENT_IDS_TOP20",
    "SYNONYM_TABLE",
    "SynonymMatch",
    "SynonymToken",
    "UNMAPPED_RESEARCH_INTENTS",
    "build_default_registry",
    "clarification_for",
    "intent_sources",
    "match_intent",
    "match_synonym",
    "missing_required",
    "warnings_for",
]
