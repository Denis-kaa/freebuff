"""Intent parser, ступень 1 (Р6 v3) — детерминированный словарь.

Словарь строится ТОЛЬКО из существующих источников — жаргон не
выдумывается: названия позиций прайс-каталога + их синонимы (идея №5)
+ id/канонические слова калькуляторов (из CalculatorSpec.title).
Неизвестные токены возвращаются в unknown: UI показывает на их месте
форму «+» (идея №1), подтверждение «вы имели в виду X?» добавляет слово
в синонимы позиции (идея №5). Число рядом с услугой становится
количеством. LLM-ступень 2 сядет на этот же интерфейс.
"""

from __future__ import annotations

import json
import re
import sqlite3
from typing import Any

from printcalc_web.calculators import get_registry

#: Канонические слова калькуляторов — стемы из spec.title (не жаргон).
#: «ризограф/ризография» выведены из title «Калькулятор ризографии RISO RZ300EP».
CALC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "riso": ("ризограф", "ризография"),
    "digital": (
        "цифра",
        "цифровая",
        "цифровую",
        # Изделия DigitalConfig (стемы после флексий): «визитки/визитка» →
        # визитк; печатная продукция = цифровая печать (R-материал).
        "визитк",
        "листовк",
        "буклет",
        "открытк",
        "календар",
        "сертификат",
        "приглашени",
    ),
    "sign": ("вывеск", "буква", "буквы", "контражур"),
    # Изделия ЧПУ (стемы): фрезеровка/лазерная резка + материалы.
    "cnc": ("чпу", "фрезер", "лазер", "резк", "фанер", "акрил", "оргстекл", "композит"),
    # Дизайн: вёрстк(а/у) + макет + логотип (стемы после флексий).
    "design": ("дизайн", "вёрстк", "верстк", "макет", "логотип", "трассировк"),
    # Себестоимость — внутренний инструмент, в сообщениях клиентов почти
    # не встречается; ключ оставлен для ручного ввода оператором.
    "cost": ("себестоимост", "себестоимост"),
}

_TITLE_STOPWORDS = {"калькулятор"}
_NUMBER_RE = re.compile(r"^\d+([.,]\d+)?$")
_TOKEN_SPLIT = re.compile(r"[,;]+")
#: Склеенный размер «20×30»/«20х30»/«20x30» (PHASE_UNITS): один токен,
#: осмысленный фрагмент (размер) — в unknown не падает, уходит в result["sizes"].
_GLUED_SIZE_RE = re.compile(r"^\d+(?:[.,]\d+)?[xх×]\d+(?:[.,]\d+)?$")

#: Наивные русские флексии (ступень 1, без морфоанализа): «ксерокса» →
#: «ксерокс», «фотки» → «фотка». Применяются к токену, если сам токен
#: и его начальная форма не в словаре. Не для калькуляторных слов.
_FLEX_SUFFIXES = ("а", "ы", "у", "е", "и", "ой", "ов", "ам", "ами", "ах")

#: Служебные слова перечисления (правило 1 исследования,
#: 05_combined_orders.md): разбивают привязку параметров к услугам.
#: Запятая/точка с запятой уже разделители токенизации.
_ENUM_WORDS = frozenset({"и", "плюс", "ещё", "еще", "также", "а", "да"})

#: Слова-разделители РАЗМЕРА (PHASE_UNITS, репорт кейса 09-21): «20 на 30»,
#: «20 х 30», «20 x 30» — размер изделия, а НЕ перечисление и НЕ тираж.
#: Склейка «20×30»/«20х30» — один токен, числом не является (см. _NUMBER_RE).
_SIZE_WORDS = frozenset({"на", "х", "x", "×"})

#: Слова, делающие примыкающее число ТИРАЖОМ: «наклейка 100 шт», «20 листов».
#: Без них «наклейка 20 на 30» (размер) и «наклейка 20» (тираж) неразличимы.
_QTY_WORDS = frozenset({
    "шт", "шт.", "штук", "штуки", "штука", "экз", "экземпляр", "экземпляра",
    "экземпляров", "лист", "листа", "листов", "копия", "копии", "копий",
    "упак", "упаковка", "упаковки", "упаковок", "пачка", "пачки", "пачек",
    "рулон", "рулона", "рулонов", "компл", "комплект", "комплекта", "комплектов",
})


def _dimension_indices(tokens: list[str]) -> set[int]:
    """Индексы токенов, образующих размер «N на M» / «N х M» / «N x M».

    Размер ≠ тираж (PHASE_UNITS): число в размерном trio не съедается как
    количество, слова-коннекторы не попадают в unknown. Склейка «20×30»
    обрабатывается сама (токен не число — qty не получает).
    """
    dim: set[int] = set()
    for i in range(len(tokens) - 2):
        if _is_number(tokens[i]) and tokens[i + 1] in _SIZE_WORDS and _is_number(tokens[i + 2]):
            dim.update((i, i + 1, i + 2))
    return dim


def _tokenize(text: str) -> list[str]:
    """Строчные токены: по пробелам и знакам-разделителям перечисления."""
    lowered = text.lower()
    return [token for token in _TOKEN_SPLIT.split(lowered) for token in token.split() if token]


def _is_number(token: str) -> bool:
    return bool(_NUMBER_RE.match(token))


def _to_number(token: str) -> float:
    return float(token.replace(",", "."))


def _build_dictionary(conn: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    """Словарь «фраза → позиция каталога / калькулятор»."""
    dictionary: dict[str, dict[str, Any]] = {}
    for row in conn.execute(
        "SELECT id, name, price, unit, synonyms FROM price_list_items WHERE archived = 0"
    ):
        entry = {
            "type": "price",
            "id": row["id"],
            "name": row["name"],
            "price": row["price"],
            "unit": row["unit"],  # PHASE_UNITS: единица едет в заказ (шт/м²/пачка…)
        }
        dictionary[row["name"].strip().lower()] = entry
        for synonym in json.loads(row["synonyms"]):
            clean = synonym.strip().lower()
            if clean:
                dictionary[clean] = entry
    registry = get_registry()
    for calculator_id in registry.ids():
        spec = registry.get(calculator_id).spec
        entry = {"type": "calculator", "id": calculator_id, "name": spec.title, "price": None}
        dictionary[spec.id.lower()] = entry
        words = [word for word in spec.title.lower().split() if len(word) >= 4]
        for word in words:
            dictionary.setdefault(word, entry)
        for keyword in CALC_KEYWORDS.get(calculator_id, ()):
            dictionary[keyword] = entry
    return dictionary


def _match_at(
    tokens: list[str], start: int, dictionary: dict[str, dict[str, Any]]
) -> tuple[dict[str, Any], int] | None:
    """Ищет самую длинную фразу-совпадение, начиная с токена start.

    Последний токен фразы пробуется также в «начальной форме» (отрезание
    частотных флексий): «2 ксерокса» находит «ксерокс».
    """
    for length in (3, 2, 1):
        if start + length > len(tokens):
            continue
        phrase = " ".join(tokens[start : start + length])
        entry = dictionary.get(phrase)
        if entry is not None:
            return entry, length
        # Флексия только на ПОСЛЕДНЕМ слове фразы (как в речи: «2 ксерокса»).
        last = tokens[start + length - 1]
        for suffix in _FLEX_SUFFIXES:
            if last.endswith(suffix) and len(last) > len(suffix) + 3:
                stem = last[: -len(suffix)]
                candidate = " ".join(tokens[start : start + length - 1] + [stem])
                entry = dictionary.get(candidate)
                if entry is not None:
                    return entry, length
    return None


def _volume_hints(items: list[dict[str, Any]]) -> list[str]:
    """Тиражные подсказки (Блок C п.6, RESEARCH_ADOPTION_PLAN §5-C):
    «от 101 шт — дешевле». Источник — канонические диапазоны прайса
    Digital (DigitalConfig.price_ranges): если тираж ниже ближайшего
    порога диапазона — подсказка. Плоские прайс-позиции подсказок не дают.
    """
    from printcalc.calculators.digital import DigitalConfig

    cfg = DigitalConfig()
    thresholds: set[int] = set()
    for ranges in cfg.product_prices.values():
        for r in ranges:
            if r.start > 1:
                thresholds.add(r.start)
    hints: list[str] = []
    for item in items:
        if item["type"] != "calculator" or item.get("calculator_id") != "digital":
            continue
        qty = float(item.get("qty", 1.0))
        bigger = sorted(t for t in thresholds if t > qty)
        if bigger:
            hints.append(f"от {bigger[0]} шт — дешевле")
    return hints


def _operator_signals(
    items: list[dict[str, Any]],
    unknown: list[str],
    text: str,
    sizes: list[str] | None = None,
) -> tuple[bool, list[str]]:
    """R10 (RESEARCH_ADOPTION_PLAN §5-Б.3): «передать оператору» + reasons.

    Детерминированные сигналы того, что машине не хватает контекста и заявку
    обязан принять человек (НЕ молча — §5-В.5):
    - есть нераспознанные токены (unknown);
    - текст указывает на файл/макет («прикрепил», «файл», «макет») — его
      качество и формат нужно проверять (Order v2, Блок E);
    - совместили несколько услуг в одном сообщении (мультизаказ, Блок C).
    """
    reasons: list[str] = []
    if unknown:
        reasons.append("не распознано: " + ", ".join(unknown))
    # Размер без услуги («30 на 40» без изделия) — не молча (PHASE_UNITS).
    if sizes and not items:
        reasons.append("указан размер без услуги: " + ", ".join(sizes))
    if any(item["type"] == "calculator" for item in items) and len(items) > 1:
        reasons.append("несколько позиций — параметры уточнит оператор")
    if re.search(r"файл|макет|прикрепил|вложени|ссылк", text.lower()):
        reasons.append("упомянут файл/макет — нужен приём файлов")
    return bool(reasons), reasons


def parse(conn: sqlite3.Connection, text: str) -> dict[str, Any]:
    """Разбирает свободный ввод на позиции заказа (ступень 1, Р6; v2 — мультизаказ).

    v2 (Блок C, RESEARCH_ADOPTION_PLAN §5-C + 05_combined_orders.md):
    - токены-перечисления («и», «плюс», «ещё») РАЗБИВАЮТ привязку чисел:
      после перечисления число относится к СЛЕДУЮЩЕЙ услуге (правило 2
      исследования — привязка к ближайшему intent слева);
    - каждая позиция знает свой индекс в тексте (segment_id — кластер между
      перечислениями, правило 1);
    - непонятые фрагменты НЕ съедаются: unknown + needs_operator (правило 5).

    Returns: {"items", "unknown", "needs_operator", "reasons"} — набор полей
    обратной совместимости сохранён, новые поля аддитивны.
    """
    tokens = _tokenize(text)
    dictionary = _build_dictionary(conn)
    dim_idx = _dimension_indices(tokens)
    glued_sizes = {i for i, tok in enumerate(tokens) if _GLUED_SIZE_RE.match(tok)}
    sizes: list[str] = []  # распознанные размеры (для UI и эскалации «без услуги»)
    items: list[dict[str, Any]] = []
    unknown: list[str] = []
    index = 0
    _consumed_number = False
    segment = 0
    while index < len(tokens):
        if tokens[index] in _ENUM_WORDS:
            # Перечисление: следующий параметр принадлежит следующей услуге.
            segment += 1
            _consumed_number = False
            index += 1
            continue
        if index in dim_idx:
            # Часть размера «20 на 30» (PHASE_UNITS): не тираж, не unknown.
            # Первое число тройки собирает размер целиком в result["sizes"].
            if index + 2 < len(tokens) and tokens[index + 1] in _SIZE_WORDS:
                sizes.append(f"{tokens[index]} {tokens[index + 1]} {tokens[index + 2]}")
            index += 1
            continue
        if index in glued_sizes:
            # Склеенный размер «20×30»: осмысленный фрагмент, не unknown.
            sizes.append(tokens[index])
            index += 1
            continue
        if tokens[index] in _QTY_WORDS and index > 0 and _is_number(tokens[index - 1]):
            # Слово-тираж после числа («наклейка 100 шт») — квалификатор числа.
            index += 1
            continue
        match = _match_at(tokens, index, dictionary)
        if match is None:
            if not _is_number(tokens[index]):
                unknown.append(tokens[index])
            index += 1
            continue
        entry, length = match
        qty = 1.0
        next_index = index + length
        # Продолжение той же услуги («цифровая печать» = одно intent, а не два):
        # следующий токен, ссылающийся на ТУ ЖЕ запись словаря, поглощается.
        while True:
            follow = _match_at(tokens, next_index, dictionary)
            if follow is None or follow[0] is not entry:
                break
            next_index += follow[1]
        if (
            next_index < len(tokens)
            and _is_number(tokens[next_index])
            and next_index not in dim_idx
        ):
            qty = _to_number(tokens[next_index])
            next_index += 1
            # Слово-тираж сразу после числа («наклейка 100 шт») поглощаем.
            if next_index < len(tokens) and tokens[next_index] in _QTY_WORDS:
                next_index += 1
        elif (
            index > 0
            and _is_number(tokens[index - 1])
            and not _consumed_number
            and (index - 1) not in dim_idx
        ):
            # Число ПЕРЕД услугой («2 ксерокса», R-материал: порядок свободный).
            # Числа размера («20 на 30 наклейка») тиражом НЕ становятся.
            qty = _to_number(tokens[index - 1])
            _consumed_number = True
        if entry["type"] == "price":
            items.append(
                {
                    "type": "price",
                    "price_list_item_id": entry["id"],
                    "name": entry["name"],
                    "price": entry["price"],
                    "qty": qty,
                    "segment_id": segment,
                    "unit": entry.get("unit"),  # PHASE_UNITS: единица из каталога
                }
            )
        else:
            items.append(
                {
                    "type": "calculator",
                    "calculator_id": entry["id"],
                    "name": entry["name"],
                    "qty": qty,
                    "segment_id": segment,
                }
            )
        index = next_index
    needs_operator, reasons = _operator_signals(items, unknown, text, sizes)
    return {
        "items": items,
        "unknown": unknown,
        "unassigned_fragments": list(unknown),  # JSON-модель 05_combined_orders.md
        "sizes": sizes,  # PHASE_UNITS: распознанные размеры («20×30», «20 на 30»)
        "volume_hints": _volume_hints(items),
        "needs_operator": needs_operator,
        "reasons": reasons,
    }
