"""Telegram-полллер Этапа 6 (роадмап v6, промт_4 §44/§47/§55).

Дизайн:
- Adapter Pattern (§47): TelegramAdapter — единственное место, знающее Bot API.
  Email/MAX/VK позже — тем же контрактом record_incoming_message.
- long polling в daemon-потоке при старте приложения; без токена — тихий no-op
  (Telegram просто не включён, остальное приложение работает).
- Идемпотентность §55: update_id = external_id; дубликат не создаёт строку.
- Ответ клиенту — короткое эхо-подтверждение (детерминированное, без AI).
- Все параметры — env (CODE_QUALITY 4.7): PRINTCALC_TG_TOKEN, PRINTCALC_TG_ENABLED,
  PRINTCALC_TG_POLL_SECONDS.
"""

from __future__ import annotations

import threading
from typing import Any

import httpx

from printcalc_web import store

TG_API = "https://api.telegram.org"

#: Сколько ждать ответа сервера Telegram на getUpdates (сек).
POLL_TIMEOUT_S = 25


class TelegramAdapter:
    """Обёртка Bot API: getUpdates/sendMessage. Ошибки сети не роняют поток."""

    def __init__(self, token: str) -> None:
        self._base = f"{TG_API}/bot{token}"

    def get_updates(self, offset: int) -> list[dict[str, Any]] | None:
        try:
            response = httpx.post(
                f"{self._base}/getUpdates",
                json={"offset": offset, "timeout": POLL_TIMEOUT_S - 5},
                timeout=POLL_TIMEOUT_S + 10,
            )
        except httpx.HTTPError:
            return None
        if response.status_code != 200:
            return None
        payload = response.json()
        if not payload.get("ok"):
            return None
        return list(payload.get("result", []))

    def send_message(self, chat_id: str, text: str) -> bool:
        try:
            response = httpx.post(
                f"{self._base}/sendMessage",
                json={"chat_id": chat_id, "text": text},
                timeout=15,
            )
        except httpx.HTTPError:
            return False
        return response.status_code == 200


def _update_to_message(update: dict[str, Any]) -> dict[str, Any] | None:
    """Извлекает текстовое сообщение из update (текстовые каналы — только они)."""
    message = update.get("message") or update.get("edited_message")
    if not message:
        return None
    text = message.get("text") or ""
    if not text.strip():
        return None
    sender = message.get("from") or {}
    chat = message.get("chat") or {}
    username = str(sender.get("username") or "")
    return {
        "external_id": str(update.get("update_id")),
        "chat_id": str(chat.get("id") or ""),
        "sender_name": " ".join(
            part for part in (sender.get("first_name"), sender.get("last_name")) if part
        ).strip(),
        "sender_handle": username,
        "text": text,
    }


def process_update(conn: Any, adapter: TelegramAdapter, update: dict[str, Any]) -> None:
    """Принимает один update: запись в inbox (идемпотентно) + эхо-ответ."""
    payload = _update_to_message(update)
    if payload is None:
        return
    message, created = store.record_incoming_message(
        conn,
        channel="telegram",
        external_id=payload["external_id"],
        chat_id=payload["chat_id"],
        sender_name=payload["sender_name"],
        sender_handle=payload["sender_handle"],
        text=payload["text"],
    )
    if created:
        adapter.send_message(
            payload["chat_id"],
            "Принял ваш запрос ✅ Оператор посмотрит и подготовит расчёт. "
            "Если нужно срочно — позвоните в мастерскую.",
        )


def _poll_loop(adapter: TelegramAdapter, db_path: Any) -> None:  # noqa: ANN401
    offset = 0
    while True:
        updates = adapter.get_updates(offset)
        if updates is None:
            threading.Event().wait(5.0)
            continue
        for update in updates:
            offset = max(offset, int(update.get("update_id", 0)) + 1)
            try:
                from printcalc_web.db import connect

                conn = connect(db_path)
                try:
                    process_update(conn, adapter, update)
                finally:
                    conn.close()
            except Exception:  # noqa: BLE001 — ошибка одного сообщения не роняет поток
                pass


def start_poller(app: Any) -> None:  # noqa: ANN401
    """Запускает daemon-поток поллинга, если задан токен и поллер включён.

    Env: PRINTCALC_TG_TOKEN (обязателен), PRINTCALC_TG_ENABLED (по умолч. 1),
    PRINTCALC_TG_POLL_SECONDS — пауза между циклами при ошибках.
    """
    import os

    token = os.environ.get("PRINTCALC_TG_TOKEN", "").strip()
    if not token:
        return
    if os.environ.get("PRINTCALC_TG_ENABLED", "1").strip().lower() in ("0", "false", "no"):
        return
    adapter = TelegramAdapter(token)
    thread = threading.Thread(
        target=_poll_loop,
        args=(adapter, app.state.db_path),
        daemon=True,
        name="printcalc-telegram-poller",
    )
    thread.start()
    app.state.telegram_poller = thread
