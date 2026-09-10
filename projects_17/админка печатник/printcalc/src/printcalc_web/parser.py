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
    "digital": ("цифра", "цифровая", "цифровую"),
}

_TITLE_STOPWORDS = {"калькулятор"}
_NUMBER_RE = re.compile(r"^\d+([.,]\d+)?$")
_TOKEN_SPLIT = re.compile(r"[,;]+")


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
    for row in conn.execute("SELECT id, name, price, synonyms FROM price_list_items WHERE archived = 0"):
        entry = {"type": "price", "id": row["id"], "name": row["name"], "price": row["price"]}
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
    """Ищет самую длинную фразу-совпадение, начиная с токена start."""
    for length in (3, 2, 1):
        if start + length > len(tokens):
            continue
        phrase = " ".join(tokens[start : start + length])
        entry = dictionary.get(phrase)
        if entry is not None:
            return entry, length
    return None


def parse(conn: sqlite3.Connection, text: str) -> dict[str, Any]:
    """Разбирает свободный ввод на позиции заказа (ступень 1, Р6).

    Returns: {"items": [{type, ...}], "unknown": [токены]}.
    """
    tokens = _tokenize(text)
    dictionary = _build_dictionary(conn)
    items: list[dict[str, Any]] = []
    unknown: list[str] = []
    index = 0
    while index < len(tokens):
        match = _match_at(tokens, index, dictionary)
        if match is None:
            if not _is_number(tokens[index]):
                unknown.append(tokens[index])
            index += 1
            continue
        entry, length = match
        qty = 1.0
        next_index = index + length
        if next_index < len(tokens) and _is_number(tokens[next_index]):
            qty = _to_number(tokens[next_index])
            next_index += 1
        if entry["type"] == "price":
            items.append(
                {
                    "type": "price",
                    "price_list_item_id": entry["id"],
                    "name": entry["name"],
                    "price": entry["price"],
                    "qty": qty,
                }
            )
        else:
            items.append(
                {
                    "type": "calculator",
                    "calculator_id": entry["id"],
                    "name": entry["name"],
                    "qty": qty,
                }
            )
        index = next_index
    return {"items": items, "unknown": unknown}
