"""Шаблоны быстрых ответов R1/R2/R3 — Hub v2 (RESEARCH_ADOPTION_PLAN §5-Б п.11).

Источники:
- research/14_dialog_rules.md: R1 «один вопрос закрывает максимум дыр»,
  R2 «пакетные услуги объяснять», R3 «новичку — процедура, не цены»;
- RESEARCH_ADOPTION_PLAN §4: «Мини-диалоги — готовые шаблоны быстрых ответов
  для страницы Входящие (ответы одной кнопкой)»;
- §37 промта_4: текст клиенту — детерминированный, оператор видит перед
  отправкой. Поэтому шаблон = текст + подстановка РАСПОЗНАННЫХ фактов
  парсера (никакого перефразирования и никакой выдумки).

Закрытый словарь (ANTI-6b): template_id ∈ R1_GROUPED_QUESTION | R2_PACKAGE_EXPLAIN
| R3_HOW_TO_ORDER. Подстановка использует только ключи parsed_json, которых
нет — вставляется нейтральный placeholder «…» (не молча, не выдумка).
"""

from __future__ import annotations

import re
from typing import Any

#: Закрытый словарь шаблонов (ANTI-6b). Название = правило диалога.
REPLY_TEMPLATES: tuple[dict[str, str], ...] = (
    {
        "template_id": "R1_GROUPED_QUESTION",
        "title": "R1 — один вопрос на максимум дыр",
        "text": (
            "Здравствуйте!\n\n"
            "Чтобы посчитать точно, уточните, пожалуйста:\n"
            "• размер {sizes};\n"
            "• количество (шт);\n"
            "• материал/плотность, если важно;\n"
            "• файл готов или нужен макет?\n\n"
            "Ответьте одним сообщением — сразу пришлём расчёт."
        ),
    },
    {
        "template_id": "R2_PACKAGE_EXPLAIN",
        "title": "R2 — объяснить состав пакета",
        "text": (
            "Здравствуйте!\n\n"
            "По позиции «{item}»: это пакетная услуга, в стоимость входит: "
            "{package_parts}.\n"
            "Количество: {qty}.\n\n"
            "Если нужно что-то из этого убрать или добавить — скажите, "
            "пересчитаем."
        ),
    },
    {
        "template_id": "R3_HOW_TO_ORDER",
        "title": "R3 — новичку процедура, не цены",
        "text": (
            "Здравствуйте!\n\n"
            "Как заказать у нас:\n"
            "1. Опишите заказ: что именно, размер и количество.\n"
            "2. Пришлите файл макета (PDF/TIFF), если он есть.\n"
            "3. Мы посчитаем и пришлём смету сюда же.\n"
            "4. После подтверждения — производство, срок скажем вместе со сметой.\n\n"
            "Пишите прямо в этот чат/на эту почту — отвечим быстро."
        ),
    },
)

TEMPLATE_IDS: tuple[str, ...] = tuple(t["template_id"] for t in REPLY_TEMPLATES)

_PACKAGE_PARTS: dict[str, str] = {
    "фото": "съёмка/загрузка фото, обработка, печать",
    "документ": "съёмка/загрузка фото, обработка, печать",
    "брошюр": "печать страниц, фальцовка, скрепление",
    "визитк": "печать, нарезка",
}

_SIZE_RE = re.compile(r"\d+(?:[.,]\d+)?(?:\s*[xх×]\s*\d+(?:[.,]\d+)?)?")


def _extract_sizes(text: str) -> str:
    """Размеры из текста запроса (детерминированно): «20 на 30» → «20×30».

    Двухместные размеры (A×B) приоритетнее одиночных чисел (тираж).
    """
    pairs = re.findall(r"\d+(?:[.,]\d+)?\s*(?:[xх×]|на)\s*\d+(?:[.,]\d+)?", text, flags=re.IGNORECASE)
    if pairs:
        return ", ".join(p.replace("на", "×").replace("На", "×").replace(" НА ", "×") for p in pairs)
    return "…"


def _extract_item(text: str) -> str:
    """Первое распознанное имя позиции или placeholder (не выдумываем)."""
    m = re.search(r"[А-ЯЁ][а-яё\-]+", text or "")
    if m is None:
        return "…"
    return m.group(0)


def _package_parts_for(text: str) -> str:
    """Состав пакета — из закрытого словаря _PACKAGE_PARTS (не выдумываем)."""
    for key, parts in _PACKAGE_PARTS.items():
        if key in (text or "").lower():
            return parts
    return "уточните состав у оператора"


def render(template_id: str, *, parsed: dict[str, Any] | None = None) -> str:
    """Заполняет шаблон распознанными фактами. Неизвестное → «…» (не молча).

    parsed — parsed_json входящего сообщения (items, unknown, sizes).
    """
    if template_id not in TEMPLATE_IDS:
        raise ValueError(
            f"неизвестный шаблон {template_id!r}; допустимо: {', '.join(TEMPLATE_IDS)}"
        )
    tpl = next(t for t in REPLY_TEMPLATES if t["template_id"] == template_id)
    parsed = parsed or {}
    items = parsed.get("items") or []
    text = " ".join(
        str(item.get("name", "")) for item in items
    ) or ""
    first_item = str(items[0].get("name", "")) if items else _extract_item(text)
    qty_raw: Any = items[0].get("qty", "") if items else ""
    if isinstance(qty_raw, float) and qty_raw.is_integer():
        qty = str(int(qty_raw))  # «2.0» → «2» — клиентский текст без дробного мусора
    else:
        qty = str(qty_raw)
    sizes = _extract_sizes(str(parsed.get("sizes") or "")) or _extract_sizes(text)

    return tpl["text"].format(
        sizes=sizes or "…",
        item=first_item or "…",
        package_parts=_package_parts_for(first_item) if first_item else "…",
        qty=qty or "…",
    )
