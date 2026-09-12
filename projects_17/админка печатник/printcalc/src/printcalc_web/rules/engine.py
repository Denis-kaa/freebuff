"""Движок правил — S2 (РОАДМАП_v7 §3, промт_печатник_6 PHASE R2).

ProductionRule (пак YAML, S0) + OrderDraft (нормализатор, S1) →
`RuleVerdict`: proposed_operations / missing / suggestions /
ready_for_calculator. Детерминированно, без LLM (анти-правило 2).

Контракт «распознать ≠ предложить» (промт_6 §1): **ничто** не попадает
в заказ автоматически — `OperationProposal.auto` всегда False в v1;
подтверждение — действие сотрудника (S4/S5).

Матчинг правил: пак выбирается по РЕЧЕВОМУ продукту черновика
(OrderDraft.product == RulePack.product_label, уникальность label
гарантирована load_packs). `when_facts` — equality-контракт v1: каждый
ключ правила сравнивается со строковым значением факта (OrderDraft.fact,
bool → "true"/"false"); отсутствие факта — правило НЕ матчится (не
матчится ложно). Пустой when_facts — правило уровня продукта.

Missing (промт_6 §2.3): поле, вопрос, blocking. БЛОКИРУЮТ расчёт только
quantity и size_mm (числовая основа любого калькулятора; CALCULATOR_MATRIX
п.4); layout/usage — производственные уточнения, расчёт не блокируют.
ready_for_calculator = нет blocking-missing. Блокирующие отсутствия
собираются ИЗ ФАКТОВ черновика (не из require правил: требование макета —
вопрос производства, а не вход калькулятора).

Идемпотентность: evaluate_order — чистая функция (черновик → вердикт);
повторный прогон на том же черновике даёт байт-в-байт тот же вердикт
(закреплено тестом).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from printcalc_web.rules.normalize import OrderDraft
from printcalc_web.rules.schema import (
    KNOWN_FINISHINGS,
    KNOWN_MISSING_FIELDS,
    RulePack,
)

#: Вопросы для недостающих полей (промт_6 §2.3 MissingItem.question).
#: Ключи = KNOWN_MISSING_FIELDS (закрытый набор schema.py).
MISSING_QUESTIONS: dict[str, str] = {
    "quantity": "Количество?",
    "size_mm": "Размер изделия?",
    "usage": "Где будет использоваться: помещение или улица?",
    "layout": "Готовый макет предоставлен?",
    "layout_with_cut_contour": "Макет с контуром резки готов?",
    "material": "Какой материал?",
    "mount_height": "Высота монтажа?",
}

#: Поля, БЛОКИРУЮЩИЕ расчёт (без них калькулятор не считает площадь/тираж).
#: Только числовая основа; всё остальное — производство/продажи (R-правила).
BLOCKING_FIELDS: frozenset[str] = frozenset({"quantity", "size_mm"})

#: Комментарий источника для каждого missing-поля (никакой магии: видно,
#: откуда взялся вопрос — факты черновика или правило пака).
_MISSING_SOURCES: dict[str, str] = {
    "quantity": "вход калькулятора (тираж)",
    "size_mm": "вход калькулятора (площадь)",
    "usage": "контекст подсказок R-03/R-04",
    "layout": "производство (макет)",
    "layout_with_cut_contour": "производство (контур резки)",
    "material": "материал по умолчанию из реестра",
    "mount_height": "цена монтажа по высоте",
}


@dataclass(frozen=True)
class OperationProposal:
    """Предложение операции (промт_6 §2.3). auto=False ВСЕГДА в v1."""

    operation_token: str  # код каталога операций (закрытый словарь OP-хх)
    label: str  # человеческое имя («Плоттерная резка»)
    reason: str  # какое правило сработало (rule_id)
    auto: bool = False  # False всегда в v1 — только предложить

    def __post_init__(self) -> None:
        if self.auto:
            raise ValueError("auto=True запрещён в v1 (промт_6 §1: только предложить)")


@dataclass(frozen=True)
class MissingItem:
    """Недостающее поле (промт_6 §2.3): поле, вопрос, блокирует ли расчёт."""

    field: str  # из KNOWN_MISSING_FIELDS
    question: str
    blocking: bool
    source: str = ""  # правило-источник / «вход калькулятора»

    def __post_init__(self) -> None:
        if self.field not in KNOWN_MISSING_FIELDS:
            raise ValueError(
                f"MissingItem.field {self.field!r} вне закрытого набора (ANTI-6b)"
            )


@dataclass(frozen=True)
class Suggestion:
    """Контекстная подсказка (промт_6 §2.3): kind/label/reason/options."""

    kind: str  # закрытый кортеж SUGGESTION_KINDS (schema.py)
    label: str
    reason: str  # правило-источник — ОБЯЗАТЕЛЬНО
    options: tuple[str, ...] = ()
    rule_id: str = ""  # правило-источник для UI «почему я это вижу»


@dataclass(frozen=True)
class RuleVerdict:
    """Итог разбора заказа правилами (промт_6 §2.2)."""

    draft: OrderDraft
    matched_pack: str  # имя пака («наклейка») или "" — продукт не распознан
    proposed_operations: tuple[OperationProposal, ...] = ()
    missing: tuple[MissingItem, ...] = ()
    suggestions: tuple[Suggestion, ...] = ()
    fired_rules: tuple[str, ...] = ()  # rule_id сработавших правил (аудит)
    ready_for_calculator: bool = True

    def to_json(self) -> dict[str, Any]:
        """Сериализация для API S3 (стабильный контракт, аддитивный)."""
        return {
            "product": self.draft.product,
            "matched_pack": self.matched_pack,
            "size_mm": list(self.draft.size_mm) if self.draft.size_mm else None,
            "quantity": self.draft.quantity,
            "finishings": list(self.draft.finishings),
            "facts": dict(self.draft.facts),
            "unknown_words": list(self.draft.unknown_words),
            "proposed_operations": [
                {
                    "operation_token": p.operation_token,
                    "label": p.label,
                    "reason": p.reason,
                    "auto": p.auto,
                }
                for p in self.proposed_operations
            ],
            "missing": [
                {"field": m.field, "question": m.question, "blocking": m.blocking, "source": m.source}
                for m in self.missing
            ],
            "suggestions": [
                {"kind": s.kind, "label": s.label, "reason": s.reason, "options": list(s.options), "rule_id": s.rule_id}
                for s in self.suggestions
            ],
            "fired_rules": list(self.fired_rules),
            "ready_for_calculator": self.ready_for_calculator,
        }


#: Имена операций каталога для предложений (человеческие label промт_6
#: §2.3). Сюда входят только операции, встречающиеся в паках v1; имя для
#: остальных кодов — сам код (не выдумываем): каталог живёт в БД и
#: подставит точное имя на S5.
OPERATION_LABELS: dict[str, str] = {
    "OP-22": "Плоттерная резка",
    "OP-15": "Накатка на основу",
    "OP-13": "Установить люверсы",
    "OP-14": "Загибка / карман",
    "OP-04": "Напечатать (широкоформат)",
}


def _operation_label(operation_token: str, finishings: tuple[str, ...]) -> str:
    """Человеческое имя операции: по токену обработки, иначе по коду каталога.

    Токен → код даёт KNOWN_FINISHINGS (закрытый маппинг schema.py), имя —
    OPERATION_LABELS. Для кода вне маппинга — сам код (не молчаливая
    выдумка): имя операции сотрудник увидит из каталога на S5.
    """
    for finishing_token, code in KNOWN_FINISHINGS.items():
        if code == operation_token and finishing_token in finishings:
            return OPERATION_LABELS.get(code, code)
    return OPERATION_LABELS.get(operation_token, operation_token)


def _facts_match(rule_facts: Mapping[str, str], draft: OrderDraft) -> bool:
    """Equality-матчинг when_facts (контракт v1, детерминизм).

    Каждый ключ правила обязан присутствовать в фактах черновика со
    СТРОГО равным строковым значением. Отсутствие факта → не матч
    («не указано» ≠ «ложь» — промт_6 §3.8).
    """
    for key, expected in rule_facts.items():
        actual = draft.fact(key)
        if actual is None or actual != expected:
            return False
    return True


def _missing_from_draft(draft: OrderDraft) -> list[MissingItem]:
    """Блокирующие отсутствия ИЗ ФАКТОВ черновика (основа калькулятора).

    require правил сюда не входит: «нужен макет с контуром» — вопрос
    производства (unblocking missing живёт в подсказках правил), а
    калькулятору нужны тираж и площадь.
    """
    missing: list[MissingItem] = []
    if draft.quantity is None:
        missing.append(
            MissingItem(
                field="quantity",
                question=MISSING_QUESTIONS["quantity"],
                blocking=True,
                source=_MISSING_SOURCES["quantity"],
            )
        )
    if draft.size_mm is None:
        missing.append(
            MissingItem(
                field="size_mm",
                question=MISSING_QUESTIONS["size_mm"],
                blocking=True,
                source=_MISSING_SOURCES["size_mm"],
            )
        )
    return missing


def evaluate_order(draft: OrderDraft, packs: Mapping[str, RulePack]) -> RuleVerdict:
    """OrderDraft + паки правил → RuleVerdict (чистая функция, идемпотентна).

    Пак матчится по product_label черновика (уникальность label между
    паками гарантирует load_packs). Продукт вне паков — вердикт без
    правил: missing от фактов, пустые предложения (не молчим: matched_pack=""
    и unknown черновика видны UI).
    """
    pack: RulePack | None = None
    if draft.product:
        for candidate in packs.values():
            if candidate.product_label == draft.product:
                pack = candidate
                break

    proposals: list[OperationProposal] = []
    suggestions: list[Suggestion] = []
    unblocking_missing: list[MissingItem] = []
    fired: list[str] = []

    if pack is not None:
        for rule in pack.rules:
            if not _facts_match(rule.when_facts, draft):
                continue
            fired.append(rule.rule_id)
            if rule.propose_operation is not None:
                proposals.append(
                    OperationProposal(
                        operation_token=rule.propose_operation,
                        label=_operation_label(rule.propose_operation, draft.finishings),
                        reason=rule.rule_id,
                    )
                )
            for raw in rule.suggest:
                suggestions.append(
                    Suggestion(
                        kind=str(raw.get("kind", "")),
                        label=str(raw.get("label", "")),
                        reason=str(raw.get("reason", "")),
                        options=tuple(str(option) for option in raw.get("options", ())),
                        rule_id=rule.rule_id,
                    )
                )
            for missing_field in rule.require:
                if draft.fact(missing_field) is not None:
                    continue
                # Требования правил не дублируют blocking-поля из фактов.
                if missing_field in BLOCKING_FIELDS:
                    continue
                unblocking_missing.append(
                    MissingItem(
                        field=missing_field,
                        question=MISSING_QUESTIONS.get(missing_field, f"{missing_field}?"),
                        blocking=False,
                        source=rule.rule_id,
                    )
                )

    missing = _missing_from_draft(draft) + unblocking_missing
    return RuleVerdict(
        draft=draft,
        matched_pack=pack.pack if pack is not None else "",
        proposed_operations=tuple(proposals),
        missing=tuple(missing),
        suggestions=tuple(suggestions),
        fired_rules=tuple(fired),
        ready_for_calculator=not any(item.blocking for item in missing),
    )


def evaluate_text(
    text: str,
    packs: Mapping[str, RulePack],
    parse_result: Mapping[str, Any] | None = None,
) -> RuleVerdict:
    """Удобство для API S3: текст → нормализация → вердикт (один вызов).

    parse_result — выход parser v2 (опционален, см. normalize_order).
    """
    from printcalc_web.rules.normalize import normalize_order

    return evaluate_order(normalize_order(text, parse_result=parse_result), packs)
