"""Слой производственных правил Smart Order Intelligence (S0–S2, РОАДМАП_v7).

Контракт (промт_печатник_6 §2): ParseResult → OrderDraft → RuleVerdict.
S0 даёт финализированную схему и валидатор YAML-паков правил
(`schema.py`) + встроенные паки v1 (`packs/*.yaml`). Нормализация (S1,
`normalize.py`) переводит свободный текст в OrderDraft; движок вердиктов
(S2, `engine.py`) превращает черновик + паки в RuleVerdict — детерминированно,
без LLM, ничего не применяется без подтверждения сотрудника.
"""

from __future__ import annotations

from pathlib import Path

from printcalc_web.rules.engine import (
    BLOCKING_FIELDS,
    MissingItem,
    OPERATION_LABELS,
    OperationProposal,
    RuleVerdict,
    Suggestion,
    evaluate_order,
    evaluate_text,
)
from printcalc_web.rules.normalize import (
    KNOWN_FINISHING_TOKENS,
    OrderDraft,
    PRODUCT_LABEL_PATTERNS,
    normalize_order,
)
from printcalc_web.rules.schema import (
    KNOWN_FACT_KEYS,
    KNOWN_FINISHINGS,
    KNOWN_MISSING_FIELDS,
    KNOWN_OPERATION_CODES,
    KNOWN_PRODUCTS,
    KNOWN_PRODUCT_LABELS,
    PackValidationError,
    RulePack,
    SUGGESTION_KINDS,
    load_pack,
    load_packs,
    validate_pack_document,
)

#: Каталог встроенных паков v1 (рядом с кодом, путь относительно пакета).
PACKS_DIR: Path = Path(__file__).resolve().parent / "packs"


def load_builtin_packs() -> dict[str, RulePack]:
    """Загружает все встроенные паки из PACKS_DIR (S0: sticker, banner; S1: + backlit)."""
    return load_packs(PACKS_DIR)


__all__ = [
    "BLOCKING_FIELDS",
    "KNOWN_FACT_KEYS",
    "KNOWN_FINISHINGS",
    "KNOWN_FINISHING_TOKENS",
    "KNOWN_MISSING_FIELDS",
    "KNOWN_OPERATION_CODES",
    "KNOWN_PRODUCTS",
    "KNOWN_PRODUCT_LABELS",
    "OPERATION_LABELS",
    "PACKS_DIR",
    "PRODUCT_LABEL_PATTERNS",
    "PackValidationError",
    "MissingItem",
    "OperationProposal",
    "OrderDraft",
    "RulePack",
    "RuleVerdict",
    "SUGGESTION_KINDS",
    "Suggestion",
    "evaluate_order",
    "evaluate_text",
    "load_builtin_packs",
    "load_pack",
    "load_packs",
    "normalize_order",
    "validate_pack_document",
]
