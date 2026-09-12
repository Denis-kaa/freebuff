"""Схема YAML-паков производственных правил — S0 (РОАДМАП_v7 Приложение A, промт_печатник_6).

Пак = один YAML на КАЛЬКУЛЯТОР (pack == product = id реестра движка).
Правила декларативны: когда нормализованные факты заказа совпали
(`when_facts`) — предложить операцию (`propose_operation`), потребовать
недостающее (`require`) и подсказать (`suggest`). Ничего не добавляется
в заказ автоматически: предложение подтверждает сотрудник
(промт_6 §1 «распознать» ≠ «предложить»).

Закрытые словари (ANTI-6b, CON-8): все токены — из закрытых наборов.
  * products  — зеркалят реестр калькуляторов (engine registry ids);
  * operations — коды каталога операций (store.DEFAULT_OPERATIONS, ключ code);
  * missing   — закрытый набор полей MissingItem (промт_6 §2.3);
  * kinds     — закрытый кортеж типов подсказок Suggestion.
Drift любого словаря → PackValidationError при валидации пака (фича,
не баг: тихий фолбэк запрещён). `propose_operation: null` разрешён —
правило только задаёт вопросы/подсказки (пример BANNER_MONTAGE_OFFER).

Финализация S0 относительно черновика Приложения A (решения зафиксированы
в PHASE_RULES_R0_REPORT): (1) `when_facts: {}` разрешён — правило уровня
продукта («баннеру вообще» предложить монтаж); (2) `product_label` —
необязательное имя речевого продукта («наклейка», «баннер»): паки
стикеров и баннеров оба сидят на калькуляторе wide, нормализатор S1
выводит label из текста; (3) OP-22 «Плоттерная резка» — новый код,
OP-15 каталогом зарезервирован («Накатка на основу») и не переиспользуется.

S1 (PHASE R1): словарь product_label стал закрытым (KNOWN_PRODUCT_LABELS:
+«бэклит», +«оформление витрины» — решения R0 §6.2/6.3); появился
KNOWN_FINISHINGS (токен обработки → код каталога) для OrderDraft.finishings;
факт `vitrine` добавлен в KNOWN_FACT_KEYS.

PyYAML — опциональная зависимость как у TG-поллера (урок Этапа 6:
отсутствие опциональной библиотеки не должно ронять импорт модуля);
без yaml импорт проходит, а load_* поднимает понятную ошибку.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

#: --- Закрытые словари (единый источник истины для валидатора) ---

#: Продукты = id калькуляторов реестра (engine registry). Пак привязан
#: к продукту; новые продукты регистрируются вместе с калькулятором.
KNOWN_PRODUCTS: frozenset[str] = frozenset(
    {
        "riso",
        "tablichki",
        "wide",
        "digital",
        "sign",
        "cnc",
        "design",
        "cost",
    }
)

#: Коды операций — дословно из store.DEFAULT_OPERATIONS (сид) плюс
#: документированные НЕПосеянные операции OPERATIONS_CATALOG.md §2.
#: ВАЖНО (фиксация S0): OP-15 = «Накатка на основу» — ЗАРЕЗЕРВИРОВАН
#: каталогом, не переиспользуем; плоттерная резка — НОВЫЙ код OP-22
#: (основание: TERMS_GLOSSARY «Плоттерная резка» = M1 прайс EXISTING;
#: PRODUCTION_CHECKLISTS «контур резки отдельным слоем для плоттера»).
KNOWN_OPERATION_CODES: frozenset[str] = frozenset(
    {
        "OP-01",  # Проверить макет
        "OP-02",  # Подготовить файл к печати
        "OP-03",  # Подготовить файл к резке (каталог §2, не посеян)
        "OP-04",  # Напечатать (широкоформат)
        "OP-05",  # Напечатать (ризограф)
        "OP-06",  # Напечатать (цифровая) (каталог §2, не посеян)
        "OP-07",  # УФ-печать на жёстком
        "OP-08",  # Ламинировать (work_laminate_mount)
        "OP-09",  # Резать/подрезать
        "OP-10",  # Фальцевать (каталог §2, не посеян)
        "OP-11",  # Скрепить (каталог §2, не посеян)
        "OP-12",  # Скруглить углы (каталог §2, не посеян)
        "OP-13",  # Установить люверсы (work_eyelets)
        "OP-14",  # Загибка / карман (work_hemming)
        "OP-15",  # Накатка на основу (каталог §2, НЕ переиспользуем)
        "OP-16",  # Резка ЧПУ (каталог §2, не посеян)
        "OP-17",  # Сборка объёмной буквы (каталог §2, не посеян)
        "OP-18",  # Электрика (каталог §2, не посеян)
        "OP-19",  # Монтаж на объекте (install)
        "OP-20",  # Контроль качества
        "OP-21",  # Упаковать и выдать
        "OP-22",  # Плоттерная резка (НОВЫЙ, S0: TERMS_GLOSSARY + чеклисты)
    }
)

#: Закрытый набор полей MissingItem (промт_6 §2.3). Расширение набора —
#: отдельная редакция схемы (schema_version++), не тихое добавление.
KNOWN_MISSING_FIELDS: frozenset[str] = frozenset(
    {
        "quantity",
        "size_mm",
        "usage",
        "layout",
        "layout_with_cut_contour",
        "material",
        "mount_height",
    }
)

#: Закрытый кортеж типов Suggestion (промт_6 §2.3, как INQUIRY_STATUSES).
SUGGESTION_KINDS: tuple[str, ...] = (
    "question",
    "finishing",
    "material",
    "upsell",
    "layout",
)

#: Ключи нормализованных фактов заказа (OrderDraft, промт_6 §2.1/§4) —
#: контракт S1. ЧЕСТНАЯ ФИКСАЦИЯ (анти-галлюцинация): парсер v2 сегодня
#: извлекает только type/calculator_id/name/qty/segment_id; извлечение
#: остальных фактов («50×30», «порезать поштучно», «с монтажной»,
#: «люверсы 30 см», «1440 dpi») — задача нормализатора PHASE R1 (S1).
#: Правила пишутся против нормализованных фактов, поэтому словарь ключей
#: закрыт уже в S0: факт вне набора не матчится молча, а падает валидацией.
KNOWN_FACT_KEYS: frozenset[str] = frozenset(
    {
        "size",  # «50×30» / «3×6» (значения — строки equality, S1 нормализует)
        "size_unit",  # мм|см|м
        "qty",  # число рядом с услугой (парсер v2 уже даёт)
        "dpi",  # «1440 dpi»
        "grommets",  # «+ люверсы» (QUESTION_FLOW S-01 #7 — bool)
        "grommets_step_cm",  # «люверсы 30 см» (S-01 #8, отдельное поле)
        "cutting",  # «резка по контуру» / «порезать»
        "cutting_mode",  # contour|individual
        "mounting_film",  # «с монтажной»
        "duplex",  # «двусторонняя»
        "usage",  # помещение|улица («на улицу» → R-03)
        "vitrine",  # «оформление витрины» (решение Дениса 2026-09-12: R0 §6.2 — факт в S1)
    }
)

#: Речевые имена продуктов (product_label) — ЗАКРЫТЫЙ словарь нормализатора
#: (S1, решение Дениса 2026-09-12): «наклейка», «баннер» (S0) + «бэклит» и
#: «оформление витрины» (S1, отчёт R0 §6). Нормализатор выводит label из
#: текста ТОЛЬКО из этого набора; «наклейки»/«стикеры» — флексии/синонимы
#: label, а не новые токены. Новый label = новая редакция набора + регистрация
#: (REGISTER-FIRST), не тихое добавление.
KNOWN_PRODUCT_LABELS: frozenset[str] = frozenset(
    {
        "наклейка",
        "баннер",
        "бэклит",
        "оформление витрины",
    }
)

#: Нормализованные обработки — закрытый словарь: токен обработки → код
#: каталога операций (KNOWN_OPERATION_CODES). Контракт промт_6 §2.1
#: (OrderDraft.finishings) + §3.2 (operation_token ТОЛЬКО из каталога):
#: нормализатор кладёт в draft.finishings ТОКЕН, а не код операции —
#: маппинг в операцию делает движок правил (S2). «плоттерная_резка» →
#: OP-22 (S0), «накатка» → OP-15 (монтажная плёнка), «люверсы» → OP-13,
#: «загибка» → OP-14. Токен вне словаря → ValueError валидатора.
KNOWN_FINISHINGS: dict[str, str] = {
    "плоттерная_резка": "OP-22",
    "накатка": "OP-15",
    "люверсы": "OP-13",
    "загибка": "OP-14",
}

_MAX_OPTIONS = 4
_RULE_ID_RE = re.compile(r"^[A-Z][A-Z0-9]+(_[A-Z0-9]+)*$")
_SCHEMA_VERSION = 1


class PackValidationError(ValueError):
    """Схема пака нарушена (ANTI-6b: drift → ValueError, не тихий пропуск)."""


@dataclass(frozen=True)
class ProductionRule:
    """Иммутабельное правило пака (контракт промт_6 §2.4)."""

    rule_id: str
    when_facts: Mapping[str, str]
    propose_operation: str | None
    require: tuple[str, ...]
    suggest: tuple[Mapping[str, Any], ...]


@dataclass(frozen=True)
class RulePack:
    """Валидированный пак правил одного продукта (калькулятора)."""

    schema_version: int
    pack: str
    product: str
    product_label: str = ""  # речевое имя продукта («наклейка», «баннер»); "" = не задано
    rules: tuple[ProductionRule, ...] = field(default=())

    def rule_ids(self) -> tuple[str, ...]:
        return tuple(rule.rule_id for rule in self.rules)


def _fail(errors: list[str], where: str, message: str) -> None:
    errors.append(f"{where}: {message}")


def _check_known(
    errors: list[str], where: str, value: str, vocabulary: frozenset[str], what: str
) -> None:
    if value not in vocabulary:
        _fail(
            errors,
            where,
            f"токен {value!r} вне закрытого словаря {what} "
            f"(ANTI-6b; допустимо: {', '.join(sorted(vocabulary))})",
        )


def validate_pack_document(document: Mapping[str, Any], *, source: str = "<inline>") -> RulePack:
    """Валидирует YAML-документ пака по 8 правилам РОАДМАП_v7 §Приложение A.

    Бросает PackValidationError со СПИСКОМ всех ошибок (не первой) —
    чтобы владелец правил видел весь drift за один прогон.
    """
    errors: list[str] = []

    schema_version = document.get("schema_version")
    if schema_version != _SCHEMA_VERSION:
        _fail(errors, source, f"schema_version должен быть {_SCHEMA_VERSION}, получено {schema_version!r}")

    pack_name = document.get("pack")
    product = document.get("product")
    if not isinstance(pack_name, str) or not pack_name:
        _fail(errors, source, "pack обязателен (непустая строка)")
        pack_name = ""
    if not isinstance(product, str) or not product:
        _fail(errors, source, "product обязателен (непустая строка)")
        product = ""
    # Финализация S0: pack — имя РЕЧЕВОГО продукта (sticker/banner),
    # product — калькулятор (wide). Равенство больше не требуется:
    # несколько речевых продуктов могут сидеть на одном калькуляторе.
    # Уникальность имён паков проверяет load_packs.
    if product:
        _check_known(errors, source, product, KNOWN_PRODUCTS, "products (реестр калькуляторов)")

    raw_label = document.get("product_label", "")
    product_label = ""
    if raw_label is None:
        raw_label = ""
    if not isinstance(raw_label, str):
        _fail(errors, source, f"product_label должен быть строкой, получено {raw_label!r}")
    else:
        product_label = raw_label.strip()

    raw_rules = document.get("rules")
    if not isinstance(raw_rules, list) or not raw_rules:
        _fail(errors, source, "rules обязателен (непустой список правил)")
        raw_rules = []

    seen_ids: set[str] = set()
    rules: list[ProductionRule] = []
    for index, raw in enumerate(raw_rules, start=1):
        where = f"{source}#rules[{index}]"
        if not isinstance(raw, Mapping):
            _fail(errors, where, "правило должно быть отображением (dict)")
            continue

        rule_id = raw.get("rule_id")
        if not isinstance(rule_id, str) or not _RULE_ID_RE.match(rule_id):
            _fail(errors, where, f"rule_id {rule_id!r} не подходит по формату ВЕРХНИЙ_РЕГИСТР_ПОДЧЁРКИВАНИЯ")
        elif rule_id in seen_ids:
            _fail(errors, where, f"rule_id {rule_id!r} дублируется (уникален глобально)")
        else:
            seen_ids.add(rule_id)

        when_facts = raw.get("when_facts")
        facts: dict[str, str] = {}
        if isinstance(when_facts, Mapping):
            for key, value in when_facts.items():
                str_key = str(key)
                if str_key not in KNOWN_FACT_KEYS:
                    _fail(
                        errors,
                        where,
                        f"when_facts-ключ {str_key!r} вне закрытого набора нормализованных фактов (OrderDraft, S1)",
                    )
                else:
                    facts[str_key] = str(value).lower() if isinstance(value, bool) else str(value)
        else:
            _fail(errors, where, "when_facts должен быть отображением equality-условий (пустой {} разрешён)")

        propose = raw.get("propose_operation", None)
        if propose is not None:
            if isinstance(propose, str) and propose:
                _check_known(errors, where, propose, KNOWN_OPERATION_CODES, "operations (каталог)")
            else:
                _fail(errors, where, f"propose_operation должен быть строкой-кодом каталога или null, получено {propose!r}")

        raw_require = raw.get("require", [])
        require: list[str] = []
        if isinstance(raw_require, list):
            for item in raw_require:
                token = str(item)
                _check_known(errors, where, token, KNOWN_MISSING_FIELDS, "missing-полей")
                require.append(token)
        else:
            _fail(errors, where, "require должен быть списком токенов missing-полей")

        raw_suggest = raw.get("suggest", [])
        suggest: list[dict[str, Any]] = []
        if isinstance(raw_suggest, list):
            if len(raw_suggest) > 2:
                _fail(
                    errors,
                    where,
                    f"suggest содержит {len(raw_suggest)} подсказок — максимум 2 на шаг (UPSELL_RULES §3, анти-анкета)",
                )
            for s_index, item in enumerate(raw_suggest, start=1):
                s_where = f"{where}.suggest[{s_index}]"
                if not isinstance(item, Mapping):
                    _fail(errors, s_where, "подсказка должна быть отображением")
                    continue
                kind = item.get("kind")
                if not isinstance(kind, str) or kind not in SUGGESTION_KINDS:
                    _fail(
                        errors,
                        s_where,
                        f"kind {kind!r} вне закрытого кортежа {SUGGESTION_KINDS}",
                    )
                label = item.get("label")
                if not isinstance(label, str) or not label.strip():
                    _fail(errors, s_where, "label обязателен (непустая строка)")
                reason = item.get("reason")
                if not isinstance(reason, str) or not reason.strip():
                    _fail(errors, s_where, "reason обязателен (у подсказки видно правило-источник, никакой магии)")
                options = item.get("options", [])
                if not isinstance(options, list) or not (1 <= len(options) <= _MAX_OPTIONS):
                    _fail(errors, s_where, f"options — 1..{_MAX_OPTIONS} строк, получено {options!r}")
                suggest.append(
                    {
                        "kind": kind if isinstance(kind, str) else "",
                        "label": label if isinstance(label, str) else "",
                        "reason": reason if isinstance(reason, str) else "",
                        "options": [str(o) for o in options] if isinstance(options, list) else [],
                    }
                )
        else:
            _fail(errors, where, "suggest должен быть списком подсказок")

        if propose is None and not suggest:
            _fail(errors, where, "правило обязано предлагать операцию или хотя бы одну подсказку (правило 6)")

        rules.append(
            ProductionRule(
                rule_id=rule_id if isinstance(rule_id, str) else "",
                when_facts=facts,
                propose_operation=propose if isinstance(propose, str) else None,
                require=tuple(require),
                suggest=tuple(suggest),
            )
        )

    if errors:
        pack_label = str(document.get("pack", "?"))
        raise PackValidationError(
            f"Пак правил не валиден ({source}, pack={pack_label}):\n  — " + "\n  — ".join(errors)
        )

    assert isinstance(pack_name, str) and isinstance(product, str)
    return RulePack(
        schema_version=_SCHEMA_VERSION,
        pack=pack_name,
        product=product,
        product_label=product_label,
        rules=tuple(rules),
    )


def _require_yaml() -> Any:
    """PyYAML — опциональная зависимость (урок Этапа 6, TG-поллер)."""
    try:
        import yaml  # noqa: PLC0415 — локальный импорт, чтобы без PyYAML импорт модуля жил
    except ImportError as exc:  # pragma: no cover — среда без yaml
        raise PackValidationError(
            "PyYAML не установлен: pip install pyyaml (или extras: pip install -e '.[rules]')"
        ) from exc
    return yaml


def load_pack(path: str | Path) -> RulePack:
    """Загружает и валидирует один пак-файл."""
    yaml = _require_yaml()
    path = Path(path)
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, Mapping):
        raise PackValidationError(f"{path}: YAML-документ пака должен быть отображением")
    return validate_pack_document(document, source=str(path))


def load_packs(directory: str | Path) -> dict[str, RulePack]:
    """Загружает все *.yaml пака каталога; возвращает {pack: RulePack}.

    Финализация S0: ключ — ИМЯ пака (речевой продукт), не product:
    sticker и banner оба сидят на калькуляторе wide. Дубли имён паков,
    дубли product_label (неоднозначность нормализации S1) и дубли
    rule_id между паками ловятся здесь же (уникальность глобальна).
    """
    directory = Path(directory)
    packs: dict[str, RulePack] = {}
    seen_ids: dict[str, str] = {}
    seen_labels: dict[str, str] = {}
    for path in sorted(directory.glob("*.yaml")):
        pack = load_pack(path)
        if pack.pack in packs:
            raise PackValidationError(f"{path}: пак {pack.pack!r} уже загружен (имена паков уникальны)")
        if pack.product_label:
            other = seen_labels.get(pack.product_label)
            if other is not None:
                raise PackValidationError(
                    f"{path}: product_label {pack.product_label!r} уже занят паком {other} — нормализатор S1 не различит"
                )
            seen_labels[pack.product_label] = str(path)
        for rule_id in pack.rule_ids():
            if rule_id in seen_ids:
                raise PackValidationError(
                    f"{path}: rule_id {rule_id!r} дублируется с {seen_ids[rule_id]} (уникален глобально)"
                )
            seen_ids[rule_id] = str(path)
        packs[pack.pack] = pack
    return packs
