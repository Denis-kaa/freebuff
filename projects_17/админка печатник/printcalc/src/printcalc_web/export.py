"""OrderExport (Р1 v3): представление заказа для РУЧНОГО переноса в WF.

Никакой записи в WF: только текст для копирования/файла — первая
реализация контракта из Р1. Формат подобран под перенос позиций
на экран WF-клиента (модель+параметры+тираж).
"""

from __future__ import annotations

from typing import Any, Mapping


def _fmt_qty(qty: float) -> str:
    return str(int(qty)) if float(qty).is_integer() else f"{qty:g}"


def order_to_text(order: Mapping[str, Any]) -> str:
    """Строит текст заказа для копирования. Args: order — словарь из get_order()."""
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
    return "\n".join(lines)
