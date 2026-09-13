"""Ответы клиентам (Этап 6b): сборка письма из сметы + отправка.

Правила:
- Текст письма ДЕТЕРМИНИРОВАННЫЙ — строится из данных сметы (§37: ИИ не
  называет цену сам и не пишет клиенту; оператор видит текст перед отправкой).
- Отправка единым контрактом emailer.dispatch; результат честно пишется
  в outbox (sent/failed) — «не молча».
- Telegram-ответ идёт через тот же TelegramAdapter, что и поллер (§47).
"""

from __future__ import annotations

from typing import Any

from printcalc_web import emailer, store


def format_estimate_reply(estimate: dict[str, Any]) -> tuple[str, str]:
    """Детерминированный текст письма из сметы: (subject, body).

    Никакого AI и перефразирования — только данные сметы: позиции, суммы,
    срок действия. Пустые позиции невозможны (смета без позиций запрещена).
    """
    lines: list[str] = ["Здравствуйте!", "", "Смета по вашему запросу:", ""]
    for item in estimate.get("items", []):
        qty = item.get("qty", 1)
        price = item.get("price", 0)
        total = round(price * qty, 2)
        qty_part = f" × {qty:g}" if qty != 1 else ""
        lines.append(f"• {item.get('name', 'Позиция')}{qty_part} — {total:.2f} ₽")
    lines += [
        "",
        f"ИТОГО: {estimate.get('total', 0):.2f} ₽",
    ]
    valid_until = estimate.get("valid_until")
    if valid_until:
        lines.append(f"Смета действительна до: {valid_until[:10]}")
    note = (estimate.get("note") or "").strip()
    if note:
        lines += ["", f"Комментарий: {note}"]
    lines += ["", "С уважением,", "«Печатникъ»"]
    subject = f"Смета №{estimate.get('id', '?')} — «Печатникъ»"
    return subject, "\n".join(lines)


def send_estimate_reply(
    conn: Any, estimate: dict[str, Any], *, inquiry_id: int
) -> dict[str, Any]:
    """Собирает письмо из сметы, отправляет по адресу заявки, пишет факт в outbox.

    Возвращает запись outbox со статусом sent/failed. Исключение отправки
    не поднимается — неудача фиксируется в записи (not молча).
    """
    subject, body = format_estimate_reply(estimate)
    try:
        reply = store.create_reply(
            conn,
            inquiry_id=inquiry_id,
            subject=subject,
            body=body,
            status="draft",
        )
    except store.StoreError as exc:
        # Нет адресата (клиент без контактов) — фиксируем как failed-запись
        # без канала, чтобы оператор видел попытку и причину.
        return {
            "id": None,
            "inquiry_id": inquiry_id,
            "channel": None,
            "recipient": "",
            "subject": subject,
            "body": body,
            "status": "failed",
            "error": str(exc),
            "sent_at": None,
            "created_at": None,
        }
    ok, error = emailer.dispatch(reply["channel"], reply["recipient"], subject, body)
    return store.mark_reply_sent(conn, reply["id"], ok=ok, error=error)
