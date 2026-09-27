"""Нормализация заказа — S1 (РОАДМАП_v7 §2, промт_печатник_6 PHASE R1).

Переводит свободный текст сотрудника в нормализованный черновик заказа
`OrderDraft` (промт_6 §2.1). Детерминированно, БЕЗ LLM (анти-правило 2):
только словари и регулярные выражения, каждое решение имеет источник
(интервью §4, PROJECT_STATUS_REPORT, UPSELL_RULES, QUESTION_FLOW).

ЧЕСТНАЯ ФИКСАЦИЯ (проверено живой пробой парсера v2 перед кодом): парсер
v2 не распознаёт широкоформатные продукты («наклейка», «баннер», «бэклит»
падают в unknown; «резка» ложечно матчится с калькулятором cnc). Поэтому
нормализатор работает на ТЕКСТЕ сообщения напрямую, а ParseResult
использует только как источник qty (когда парсер распознал тот же
продукт) и unknown — который прозрачно проходит в OrderDraft
(«неизвестное не теряется», DoD РОАДМАП_v7 §2).

Закрытые словари (ANTI-6b): product — KNOWN_PRODUCT_LABELS (schema.py),
факты — KNOWN_FACT_KEYS, обработки — KNOWN_FINISHING_TOKENS (ключи
KNOWN_FINISHINGS). Распознавание пополняется только редакцией словаря:
факт вне словаря не извлекается молча, а остаётся в unknown_words.

Единицы размера (промт_2 §пользовательский ввод; CALCULATOR_MATRIX п.4):
внутренняя единица — мм (как consumption/units.py). Каскад для размеров
без единицы закреплён golden-примерами интервью §4.1–4.4: обе стороны
≤ 10 → метры («баннер 3×6» = 3000×6000 мм, §4.3); обе ≤ 100 → сантиметры
(«наклейка 50×30» = 500×300 мм §4.1, «бэклит 80×60» = 800×600 мм §4.4);
иначе мм. Хвостовое обозначение «(мм/см/м)» перекрывает каскад.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from printcalc_web.rules.schema import (
    KNOWN_FINISHINGS,
    KNOWN_PRODUCT_LABELS,
)

#: Токены обработок — ключи KNOWN_FINISHINGS (закрытый словарь schema.py).
KNOWN_FINISHING_TOKENS: frozenset[str] = frozenset(KNOWN_FINISHINGS)

#: Паттерны продуктов: канонический product_label (KNOWN_PRODUCT_LABELS) →
#: regex. Семантика порядка: КОНКРЕТНЫЙ продукт в тексте сильнее контекстной
#: услуги — «наклейка для оформления витрины» = наклейка (+ факт vitrine),
#: поэтому «оформление витрины» проверяется ПОСЛЕДНИМ и достаётся тексту
#: без конкретного продукта («оформление витрины плёнкой»).
PRODUCT_LABEL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (label, re.compile(pattern, re.IGNORECASE))
    for label, pattern in (
        ("бэклит", r"б[эе]клит[а-я]*"),
        ("баннер", r"баннер[а-я]*"),
        ("наклейка", r"(?:наклейк[а-я]*|стикер[а-я]*)"),
        ("табличка", r"(?:табличк[а-я]*|табл[её]тк[а-я]*)"),
        ("фото на документы", r"(?:фото\s+на\s+(?:документ|паспорт)[а-я]*|фот[оа-я]*\s+на\s+документ[а-я]*)"),
        ("оформление витрины", r"оформлени[а-я]*\s+витрин[а-я]*"),
    )
)

#: Размер: слитный «50×30» ИЛИ словесный «3 на 6» (ТЗ Assistant §8/§12:
#: «баннер 3 на 6, люверсы через 30» — сотрудник говорит «на», а не «×»).
#: Склейка «x/×/х» — но НЕ кириллическая Х в составе слова (см. _UNIT_TAIL_RE).
_SIZE_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(?:[x×]\s*(\d+(?:[.,]\d+)?)|\bна\s+(\d+(?:[.,]\d+)?))",
    re.IGNORECASE,
)
_DPI_RE = re.compile(r"(\d{3,4})\s*dpi", re.IGNORECASE)
_QTY_RE = re.compile(r"(\d+)\s*(?:шт|штук|штуки|экз)\b")
_GROMMETS_STEP_RE = re.compile(
    r"люверс[а-я]*\s*(?:с\s+шагом\s*)?(\d+(?:[.,]\d+)?)\s*(мм|см|м)\b"
)
#: «люверсы через 30» — шаг БЕЗ единицы (ТЗ §8: «через 30» = 30 см,
#: QUESTION_FLOW S-01 #8: шаг люверсов по умолчанию в см).
_GROMMETS_STEP_BARE_RE = re.compile(r"(?:люверс[а-я]*\s*)?через\s+(\d+(?:[.,]\d+)?)")
#: Хвостовая единица после размера: «80×35 мм», «50 см × 50 см». Разделитель —
#: ТОЛЬКО латинский x/символ × (кириллическая «х» из слов типа «ПВХ» НЕ матчится:
#: баг пробы 09-27 — «ПВХ 4 мм» превращался в единицу размера). Хвост привязан
#: К КОНКРЕТНОМУ размеру: число+единица, стоящее СРАЗУ после второй стороны
#: («80×35 мм») — иначе «люверсы 30 см» после «3×6» превращал бы метры баннера
#: в сантиметры (регресс golden §4.3, пойман тестом).
#: Хвостовая единица — число+единица, стоящее СРАЗУ после второй стороны
#: размера («80×35 мм», «50 см × 50 см» — единица перед × тоже допустима).
#: Проверяется на отрезке «сразу после match» в коде (см. _parse_size),
#: чтобы «люверсы 30 см» после «3×6» не превращал метры в сантиметры.
#: КИРИЛЛИЧЕСКАЯ «х» в разделителе НЕ матчится: «ПВХ 4 мм» больше не
#: распознаётся как единица размера (баг пробы 09-27).
_UNIT_TAIL_RE = re.compile(r"(?:\d+(?:[.,]\d+)?)?\s*(мм|см|м)\b")
#: Толщина листа: «ПВХ 4 мм», «4 мм ПВХ» (ТЗ §11 — fact thickness_mm).
_THICKNESS_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*мм\b")
#: Подсказка материала из текста (ТЗ §11: существующий Material Registry —
#: только распознавание слова, не новый справочник).
_MATERIAL_HINTS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (token, re.compile(pattern, re.IGNORECASE))
    for token, pattern in (
        ("пвх", r"\bпвх\b|пластик[а-я]*"),
        ("композит", r"композит[а-я]*|акп\b"),
        ("плёнка", r"пл[её]нк[а-я]*"),
        ("баннер 440", r"баннер\s*440"),
        ("баннер 510", r"баннер\s*510|баннер\s*лит[а-я]*"),
    )
)
#: Словесные размеры-числительные «полметра» (ТЗ §6: «табличка пластиковая
#: полметра на полметра») — детерминированный словарь.
_WORD_METRICS: dict[str, float] = {"полметра": 0.5, "полметров": 0.5, "метр": 1.0, "метра": 1.0, "метров": 1.0}
_USAGE_OUTDOOR_RE = re.compile(r"(?:на\s+улицу|для\s+улицы|уличн[а-я]*|экстерьер[а-я]*)")
_USAGE_INDOOR_RE = re.compile(r"(?:в\s+помещени[а-я]*|для\s+помещени[а-я]*|интерьер[а-я]*)")

_CUT_RE = re.compile(r"резк[а-я]*|резать|порезать|порезк[а-я]*|разрезать|вырезать")
_CONTOUR_RE = re.compile(r"по\s*контур[а-я]*")
_INDIVIDUAL_RE = re.compile(r"поштучн[а-я]*")
_DUPLEX_RE = re.compile(r"двусторонн[а-я]*|с\s+двух\s+сторон")
_MOUNTING_FILM_RE = re.compile(r"монтажн[а-я]*\s+пл[её]нк[а-я]*|с\s+монтажной")
_VITRINE_RE = re.compile(r"витрин[а-я]*")

#: Слова-распознаватели, которые НЕ становятся фактами, но и не unknown
#: (служебная лексика интервью-примеров: «с монтажной», «по контуру»…).
_KNOWN_SERVICE_RE = re.compile(
    r"|".join(
        (
            r"монтажн[а-я]*",
            r"пл[её]нк[а-я]*",
            r"контур[а-я]*",
            r"люверс[а-я]*",
            r"поштучн[а-я]*",  # распознаётся как cutting_mode=individual
            r"уличн[а-я]*",
            r"улиц[а-яу]*",  # «на улицу» → usage=улица
            r"помещени[а-я]*",
            r"интерьер[а-я]*",
            r"экстерьер[а-я]*",
            r"шаг[а-я]*",  # «с шагом 30 см»
            r"через\b",  # «люверсы через 30» (ТЗ §8) — шаг берёт _GROMMETS_STEP_BARE_RE
            r"dpi",
            r"макет[а-я]*",
            r"печать[а-я]*",
            # ТЗ Assistant v2 (ред. 2026-09-27): лексика новых продуктов
            r"табличк[а-я]*",
            r"табл[её]тк[а-я]*",
            r"пластик[а-я]*",
            r"паспорт[а-я]*",
            r"документ[а-я]*",
            r"фото\b",
            r"плоттерн[а-я]*",  # технология резки (факт cutting уже в S1)
            r"качество[а-я]*",  # «качество 1440 dpi»
        )
    ),
    re.IGNORECASE,
)

_STOP_WORDS = frozenset(
    {
        "и", "плюс", "ещё", "еще", "также", "а", "да", "нет", "с", "со",
        "для", "на", "в", "по", "шт", "штук", "штуки", "экз", "см", "мм",
        "м", "себя", "свою", "дм", "км", "dpi",  # единицы/качество — не тираж, не unknown
    }
)

_UNIT_TO_MM: dict[str, float] = {"мм": 1.0, "см": 10.0, "м": 1000.0}


@dataclass(frozen=True)
class OrderDraft:
    """Нормализованный черновик заказа (промт_6 §2.1, контракт S1).

    Отсутствие факта = None/пустой кортеж; «не указано» ≠ «ложь» —
    например grommets в facts попадает только если люверсы упомянуты.
    """

    text: str  # исходное сообщение (аудит + блок UI «Распознано»)
    product: str = ""  # токен KNOWN_PRODUCT_LABELS, "" = продукт не распознан
    size_mm: tuple[float, float] | None = None  # единая внутренняя единица — мм
    quantity: int | None = None
    finishings: tuple[str, ...] = ()  # ТОЛЬКО токены KNOWN_FINISHING_TOKENS
    material_hint: str | None = None  # подсказка материала из текста, если была
    facts: Mapping[str, Any] = field(default_factory=dict)  # ключи KNOWN_FACT_KEYS
    unknown_words: tuple[str, ...] = ()  # фрагменты вне всех словарей (не молча)

    def fact(self, key: str) -> str | None:
        """Строковое значение факта для when_facts (equality-контракт паков).

        Bool-факты сериализуются как "true"/"false"; отсутствие факта —
        None: правило с when_facts НЕ матчится (а не матчится ложно).
        """
        value = self.facts.get(key)
        if value is None:
            return None
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)


def _parse_size(text: str) -> tuple[tuple[float, float], str] | None:
    """«50×30» → ((500.0, 300.0), "мм"); «3×6»/«3 на 6» → ((3000.0, 6000.0), "м").

    Единица: хвостовое «(мм/см/м)» после размера перекрывает всё; иначе
    эвристика — обе стороны ≤ 10 → метры (баннер «3×6»), иначе мм
    («наклейка 50×30» = 50×30 мм). Возвращает None, если размера нет.

    Десятичная запятая/точка («0,5×0,5» = 500×500 мм) — ТЗ Assistant §12.
    """
    match = _SIZE_RE.search(text)
    if match is None:
        return None
    a_txt = match.group(1)
    b_txt = match.group(2) or match.group(3) or ""
    a = float(a_txt.replace(",", "."))
    b = float(b_txt.replace(",", "."))
    # Хвостовая единица — ТОЛЬКО сразу после второй стороны (зазор ≤ 4 символа:
    # пробелы/скобки). «Баннер 3×6 + люверсы 30 см»: после «3×6» идёт « + л…» —
    # зазор до «30 см» большой, хвост не наш (регресс golden §4.3). А «80×35 мм» —
    # зазор 1 пробел, хвост наш. Кириллическая «х» из «ПВХ» в разделителе не
    # участвует (см. комментарий к _UNIT_TAIL_RE).
    tail_match = _UNIT_TAIL_RE.match(text, match.end())
    if tail_match is not None and tail_match.end() - match.end() <= 4:
        unit = tail_match.group(1)
    elif a <= 10.0 and b <= 10.0:
        unit = "м"  # «баннер 3×6» = 3×6 м (промт_6 §4.3)
    elif a <= 100.0 and b <= 100.0:
        unit = "см"  # «наклейка 50×30» = 50×30 см (§4.1/§4.2), «бэклит 80×60» (§4.4)
    else:
        unit = "мм"
    factor = _UNIT_TO_MM[unit]
    return (a * factor, b * factor), unit


def _parse_word_size(text: str) -> tuple[tuple[float, float], str] | None:
    """Словесные метры: «полметра на полметра» → ((500.0, 500.0), "мм").

    ТЗ §6: «табличка пластиковая полметра на полметра» — сотрудник говорит
    словами; детерминированный словарь _WORD_METRICS, без догадок.
    """
    lowered = text.lower()
    m = re.search(
        r"(полметра|полметров|метр|метра|метров)\s+на\s+(полметра|полметров|метр|метра|метров)",
        lowered,
    )
    if m is None:
        return None
    a = _WORD_METRICS[m.group(1)] * 1000.0
    b = _WORD_METRICS[m.group(2)] * 1000.0
    return (a, b), "м"


def _parse_all_sizes(text: str) -> tuple[tuple[tuple[float, float], str], ...]:
    """ВСЕ размеры текста по порядку (ТЗ §15: «баннер 2×2 и 3×12» —
    вторая пара наследует изделие). Каждая пара проходит ту же единичную
    эвристику, что и _parse_size. Словесный вариант добавляется, если
    цифровой не нашёл ничего.
    """
    found: list[tuple[tuple[float, float], str]] = []
    for match in _SIZE_RE.finditer(text):
        a_txt = match.group(1)
        b_txt = match.group(2) or match.group(3) or ""
        a = float(a_txt.replace(",", "."))
        b = float(b_txt.replace(",", "."))
        tail_match = _UNIT_TAIL_RE.match(text, match.end())
        if tail_match is not None and tail_match.end() - match.end() <= 4:
            unit = tail_match.group(1)
        elif a <= 10.0 and b <= 10.0:
            unit = "м"
        elif a <= 100.0 and b <= 100.0:
            unit = "см"
        else:
            unit = "мм"
        factor = _UNIT_TO_MM[unit]
        found.append(((a * factor, b * factor), unit))
    if not found:
        word = _parse_word_size(text)
        if word is not None:
            found.append(word)
    return tuple(found)


def _detect_cutting(text: str) -> tuple[bool, str | None]:
    """(упомянута ли резка, cutting_mode: contour|individual|None).

    «Резка по контуру» и «порезать поштучно» — разные режимы (§4.1/§4.2).
    «Поштучно» без слова резки резкой НЕ считается (ничего не выдумываем).
    """
    if _CUT_RE.search(text) is None:
        return False, None
    if _INDIVIDUAL_RE.search(text) is not None:
        return True, "individual"
    if _CONTOUR_RE.search(text) is not None:
        return True, "contour"
    return True, None


def _detect_finishings(text: str) -> tuple[str, ...]:
    """Токены обработок из текста — ТОЛЬКО ключи KNOWN_FINISHINGS."""
    finishings: list[str] = []
    has_cut, _mode = _detect_cutting(text)
    if has_cut:
        finishings.append("плоттерная_резка")
    if "люверс" in text.lower():
        finishings.append("люверсы")
    if _MOUNTING_FILM_RE.search(text) is not None:
        finishings.append("накатка")
    if re.search(r"загибк[а-я]*|карман[а-я]*", text, re.IGNORECASE) is not None:
        finishings.append("загибка")
    return tuple(finishings)


def _extract_facts(text: str, size: tuple[tuple[float, float], str] | None) -> dict[str, Any]:
    """Факты текста — ключи ТОЛЬКО из KNOWN_FACT_KEYS (ANTI-6b)."""
    facts: dict[str, Any] = {}
    if size is not None:
        (a, b), unit = size
        facts["size"] = f"{a:g}x{b:g}"  # мм — канонический строковый формат
        facts["size_unit"] = unit
    dpi = _DPI_RE.search(text)
    if dpi is not None:
        facts["dpi"] = int(dpi.group(1))
    has_cut, cut_mode = _detect_cutting(text)
    if has_cut:
        facts["cutting"] = True
        if cut_mode is not None:
            facts["cutting_mode"] = cut_mode
    if "люверс" in text.lower():
        facts["grommets"] = True
        step = _GROMMETS_STEP_RE.search(text)
        if step is not None:
            value = float(step.group(1).replace(",", "."))
            facts["grommets_step_cm"] = int(value * _UNIT_TO_MM[step.group(2)] / 10.0)
        else:
            bare = _GROMMETS_STEP_BARE_RE.search(text)
            if bare is not None:
                # «через 30» без единицы = см (QUESTION_FLOW S-01 #8: шаг
                # люверсов по умолчанию в см; золотой пример ТЗ §8).
                facts["grommets_step_cm"] = int(
                    float(bare.group(1).replace(",", "."))
                )
    if _MOUNTING_FILM_RE.search(text) is not None:
        facts["mounting_film"] = True
    if _DUPLEX_RE.search(text) is not None:
        facts["duplex"] = True
    if _USAGE_OUTDOOR_RE.search(text) is not None:
        facts["usage"] = "улица"
    elif _USAGE_INDOOR_RE.search(text) is not None:
        facts["usage"] = "помещение"
    if _VITRINE_RE.search(text) is not None:
        facts["vitrine"] = True
    # ТЗ Assistant §11: «Табличка ПВХ 4 мм» → thickness_mm. Внимание к
    # двусмысленности: толщина — число+мм НЕ рядом с размером (4 мм из
    # «80×35 мм» — единица размера, а не толщина). Правило: толщиной
    # считаем число+мм, стоящее ПЕРЕД первым размером текста.
    size_match = _SIZE_RE.search(text)
    thickness_zone = text[: size_match.start()] if size_match is not None else text
    thickness = _THICKNESS_RE.search(thickness_zone)
    if thickness is not None:
        facts["thickness_mm"] = float(thickness.group(1).replace(",", "."))
    for token, pattern in _MATERIAL_HINTS:
        if pattern.search(text) is not None:
            facts["material_hint"] = token
            break
    return facts


def _unknown_fragments(text: str) -> tuple[str, ...]:
    """Слова вне всех словарей распознавания (не молча — правило 5 промт_6).

    Вычитаются: продукты, размеры/числа, единицы, лексика фактов и
    обработок, стоп-слова перечисления. Оставшееся — честный unknown.
    """
    lowered = text.lower()
    cleaned = lowered
    for _label, pattern in PRODUCT_LABEL_PATTERNS:
        cleaned = pattern.sub(" ", cleaned)
    cleaned = _KNOWN_SERVICE_RE.sub(" ", cleaned)
    for _token, pattern in _MATERIAL_HINTS:
        # Подсказка материала («пвх») — РАСПОЗНАННЫЙ факт (material_hint),
        # а не неизвестное слово (согласованность с _recognized_words).
        cleaned = pattern.sub(" ", cleaned)
    cleaned = _CUT_RE.sub(" ", cleaned)
    cleaned = _SIZE_RE.sub(" ", cleaned)
    cleaned = re.sub(r"\d+(?:[.,]\d+)?", " ", cleaned)
    cleaned = re.sub(r"[^\wа-яё ]+", " ", cleaned)
    words = [w for w in cleaned.split() if len(w) >= 2]
    return tuple(
        w
        for w in words
        if w not in _STOP_WORDS
        and w.rstrip("уеаыи") not in _STOP_WORDS  # «люверсов» → «люверс» уже вычтен паттерном
    )


def _recognized_words(text: str) -> frozenset[str]:
    """Однословные фрагменты, распознанные словарями нормализатора.

    Фильтр passthrough unknown парсера (аддитивно, R1-контракт не ломается):
    слово, которое вердикт-слой САМ распознал как факт/продукт/обработку
    («резка по контуру», «качество 1440 dpi», «с монтажной»), не должно
    дублироваться как «неизвестное» — оператор видит противоречие: факт
    есть, а слово «неизвестно». Реально непознанное («фольга») проходит.
    """
    lowered = text.lower()
    recognized: set[str] = set()
    for _label, pattern in PRODUCT_LABEL_PATTERNS:
        for match in pattern.finditer(lowered):
            recognized.update(match.group(0).split())
    for pattern in (
        _CUT_RE,
        _CONTOUR_RE,
        _INDIVIDUAL_RE,
        _DUPLEX_RE,
        _MOUNTING_FILM_RE,
        _VITRINE_RE,
        _USAGE_OUTDOOR_RE,
        _USAGE_INDOOR_RE,
        _SIZE_RE,
        _DPI_RE,
        _QTY_RE,
        _THICKNESS_RE,
        _GROMMETS_STEP_RE,
        _GROMMETS_STEP_BARE_RE,
        _KNOWN_SERVICE_RE,
    ):
        for match in pattern.finditer(lowered):
            recognized.update(match.group(0).split())
    for _token, pattern in _MATERIAL_HINTS:
        for match in pattern.finditer(lowered):
            recognized.update(match.group(0).split())
    return frozenset(w for w in recognized if len(w) >= 2 and w not in _STOP_WORDS)


def _qty_from_text(text: str) -> int | None:
    qty = _QTY_RE.search(text)
    return int(qty.group(1)) if qty is not None else None


def _qty_from_parse_result(
    parse_result: Mapping[str, Any], product: str
) -> int | None:
    """qty парсера — только если парсер распознал ТОТ ЖЕ продукт (проба R1:
    парсер не знает wide-продуктов, поэтому обычно это не срабатывает) И
    число явно названо в тексте. Дефолт qty=1.0 парсера (для м²-позиций —
    площадь-минимум, не тираж) тиражом НЕ считается: «Бэклит 80×60» без
    тиража обязан остаться без количества (DoD S2, ТЗ «без выдуманных
    значений»)."""
    if product == "":
        return None
    for item in parse_result.get("items", []):
        name = str(item.get("name", ""))
        for label, pattern in PRODUCT_LABEL_PATTERNS:
            if label == product and pattern.search(name) is not None:
                if not item.get("qty_explicit", False):
                    continue  # дефолтная единица парсера — не тираж
                raw_qty = item.get("qty")
                if raw_qty is not None and float(raw_qty) > 0:
                    return int(float(raw_qty))
    return None


def normalize_order(text: str, parse_result: Mapping[str, Any] | None = None) -> OrderDraft:
    """Свободный текст → OrderDraft (детерминированно, без LLM).

    parse_result (выход parser v2) опционален: используется как источник
    qty (если парсер распознал тот же продукт) и unknown (не теряем).
    """
    size = _parse_size(text)
    facts = _extract_facts(text, size)
    # Мультиразмеры (ТЗ §15): ВСЕ пары текста с наследованием изделия —
    # в отдельный факт (аддитивно; первая пара — основной size). Ключ
    # известен схеме (S1-редакция 2026-09-27, REGISTER-FIRST).
    all_sizes = _parse_all_sizes(text)
    if len(all_sizes) > 1:
        facts["extra_sizes"] = [
            f"{a:g}x{b:g}" for (a, b), _unit in all_sizes[1:]
        ]

    product = ""
    for label, pattern in PRODUCT_LABEL_PATTERNS:
        if pattern.search(text) is not None:
            product = label
            break

    finishings = _detect_finishings(text)

    quantity = _qty_from_text(text)
    if quantity is None and parse_result is not None:
        quantity = _qty_from_parse_result(parse_result, product)
    if quantity is not None:
        facts["qty"] = quantity

    unknown: tuple[str, ...] = ()
    if parse_result is not None:
        # Passthrough unknown парсера (R1) с аддитивным фильтром: слово,
        # распознанное вердикт-слоем («резка по контуру», «качество dpi»),
        # не дублируется как «неизвестное»; реально непознанное («фольга»)
        # сохраняется (не молча).
        recognized = _recognized_words(text)
        unknown = tuple(
            str(word)
            for word in parse_result.get("unknown", [])
            if str(word) not in recognized and str(word) not in _STOP_WORDS
        )
    unknown = unknown + _unknown_fragments(text)
    unknown = tuple(dict.fromkeys(unknown))  # дедупликация с сохранением порядка

    return OrderDraft(
        text=text,
        product=product,
        size_mm=size[0] if size is not None else None,
        quantity=quantity,
        finishings=finishings,
        material_hint=None,
        facts=facts,
        unknown_words=unknown,
    )


#: Экспорт закрытого набора продуктов для тестов зеркальности (S1):
#: нормализатор распознаёт ровно те labels, что разрешены схемой паков.
assert set(label for label, _ in PRODUCT_LABEL_PATTERNS) == set(KNOWN_PRODUCT_LABELS), (
    "PRODUCT_LABEL_PATTERNS должен зеркалить KNOWN_PRODUCT_LABELS (ANTI-6b)"
)
