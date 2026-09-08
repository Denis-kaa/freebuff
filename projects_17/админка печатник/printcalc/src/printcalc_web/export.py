"""OrderExport (Р1 v3): представление заказа для РУЧНОГО переноса в WF.

Никакой записи в WF: только текст для копирования/файла — первая
реализация контракта из Р1. Формат подобран под перенос позиций
на экран WF-клиента (модель+параметры+тираж).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Mapping


def _fmt_qty(qty: float) -> str:
    return str(int(qty)) if float(qty).is_integer() else f"{qty:g}"


def order_to_text(
    order: Mapping[str, Any],
    sections: Sequence[Mapping[str, Any]] | None = None,
) -> str:
    """Строит текст заказа для копирования. Args: order — словарь из get_order().

    sections — значения разделов из get_order_sections() (пожелания и прочее);
    wishes выводятся отдельным блоком в свободной форме.
    """
    lines = [
        f"Заказ #{order['id']} — {str(order['created_at'])[:10]}",
        f"Статус: {order['status']} | Оплата: {order['payment_method']}",
        "Позиции:",
    ]
    for number, item in enumerate(order["items"], start=1):
        qty_suffix = f" × {_fmt_qty(item['qty'])}" if float(item["qty"]) != 1 else ""
        amount = item["price"] * item["qty"]
        lines.append(f"{number}. {item['name']}{qty_suffix} — {amount:.2f} ₽")
    lines.append(f"Итого: {order['total']:.2f} ₽")
    wishes = str(order.get("wishes", "")).strip()
    if wishes:
        lines.append("Пожелания заказчика:")
        lines.append(wishes)
    for section in sections or []:
        value = str(section.get("value", "")).strip()
        if value:
            lines.append(f"{section['title']}: {value}")
    return "\n".join(lines)
