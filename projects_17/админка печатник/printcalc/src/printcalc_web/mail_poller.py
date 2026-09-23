"""Email-канал входящих — Hub v2 (§43 промта_4, RESEARCH_ADOPTION_PLAN §5-Б).

Дизайн — зеркально telegram.py (Adapter Pattern §47):
- ImapAdapter — единственное место, знающее imaplib/почтовый протокол.
- poll-loop в daemon-потоке при старте приложения; без кредов — тихий no-op
  (email-канал просто «не включён», остальное приложение работает).
- Идемпотентность §55: Message-ID = external_id; дубликат не создаёт строку
  (store.record_incoming_message проверяет (channel, external_id)).
- Архитектура §43: Incoming → Mailbox → Conversation → Message отображается
  на существующие таблицы: mailbox = IMAP-ящик (один), conversation =
  клиент/заявка, message = inbox_messages. Отдельной CRM-сущности НЕ создаём.
- Ответ клиенту — по контракту §45: email-адрес отправителя = recipient,
  sender_handle = адрес (client matching по нему уже есть в store).
- Все параметры — env (CODE_QUALITY 4.7):
    PRINTCALC_IMAP_HOST      — хост IMAP (пусто → канал выключен)
    PRINTCALC_IMAP_PORT      — порт (default 993, SSL)
    PRINTCALC_IMAP_USER      — логин ящика
    PRINTCALC_IMAP_PASSWORD  — пароль
    PRINTCALC_IMAP_FOLDER    — папка (default INBOX)
    PRINTCALC_IMAP_ENABLED   — «0» выключает даже с кредами (default 1)
    PRINTCALC_IMAP_POLL_SECONDS — пауза цикла (default 60)
"""

from __future__ import annotations

import email
import imaplib
import logging
import os
import threading
from email.header import decode_header, make_header
from email.message import Message
from email.utils import parseaddr
from typing import Any

from printcalc_web import store

log = logging.getLogger("uvicorn.error")

POLL_PAUSE_S = 60.0


def is_configured() -> bool:
    """Email-приём включён, если задан IMAP-хост и пользователь."""
    return bool(
        os.environ.get("PRINTCALC_IMAP_HOST", "").strip()
        and os.environ.get("PRINTCALC_IMAP_USER", "").strip()
    )


class ImapAdapter:
    """Обёртка imaplib: fetch unseen. Ошибки сети не роняют поток."""

    def __init__(self, *, host: str, port: int, user: str, password: str,
                 folder: str) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._folder = folder

    @classmethod
    def from_env(cls) -> "ImapAdapter | None":
        host = os.environ.get("PRINTCALC_IMAP_HOST", "").strip()
        user = os.environ.get("PRINTCALC_IMAP_USER", "").strip()
        if not host or not user:
            return None
        return cls(
            host=host,
            port=int(os.environ.get("PRINTCALC_IMAP_PORT", "993")),
            user=user,
            password=os.environ.get("PRINTCALC_IMAP_PASSWORD", ""),
            folder=os.environ.get("PRINTCALC_IMAP_FOLDER", "INBOX").strip() or "INBOX",
        )

    # -- низкий уровень -----------------------------------------------------

    def _connect(self) -> imaplib.IMAP4_SSL:
        conn = imaplib.IMAP4_SSL(self._host, self._port)
        conn.login(self._user, self._password)
        conn.select(self._folder)
        return conn

    def fetch_unseen(self, limit: int = 20) -> list[dict[str, str]]:
        """Непрочитанные письма → payload-словари. Флаг \\Seen ставится только
        после успешной записи в inbox_messages (см. mark_seen) — ошибка записи
        не теряет письмо (перезаберётся в следующем цикле)."""
        try:
            with self._connect() as conn:  # type: ignore[attr-defined]
                status, data = conn.uid("search", None, "UNSEEN")  # type: ignore[arg-type]  # charset=None — RFC 3501 nil
                if status != "OK":
                    return []
                uids = (data[0] or b"").split()[-limit:]
                messages: list[dict[str, str]] = []
                for uid_bytes in uids:
                    uid = uid_bytes.decode("ascii", errors="replace")
                    st, msg_data = conn.uid("fetch", uid, "(RFC822)")
                    if st != "OK" or not msg_data or msg_data[0] is None:
                        continue
                    raw = msg_data[0][1] if isinstance(msg_data[0], tuple) else None
                    if not raw:
                        continue
                    parsed = email.message_from_bytes(raw)
                    messages.append(self._to_payload(parsed, uid))
        except (OSError, imaplib.IMAP4.error, imaplib.IMAP4_SSL.error) as exc:
            log.warning("imap fetch failed: %s", exc)
            return []
        return messages

    def mark_seen(self, uid: str) -> None:
        """Помечает письмо прочитанным (после успешной записи). Ошибка не
        критична: письмо перезаберётся, а store отфильтрует дубликат."""
        try:
            with self._connect() as conn:  # type: ignore[attr-defined]
                conn.uid("store", uid, "+FLAGS", "(\\Seen)")
        except (OSError, imaplib.IMAP4.error, imaplib.IMAP4_SSL.error) as exc:
            log.warning("imap mark_seen failed (uid=%s): %s", uid, exc)

    # -- разбор письма --------------------------------------------------------

    @staticmethod
    def _decode(value: str | None) -> str:
        """RFC 2047 (=?utf-8?B?...?=) и кодировки заголовков → читаемый текст."""
        if not value:
            return ""
        try:
            return str(make_header(decode_header(value)))
        except Exception:  # noqa: BLE001 — битый заголовок не роняет поток
            return value

    def _to_payload(self, message: Message, uid: str) -> dict[str, str]:
        """Извлекает Message-ID, отправителя, тему, текст.

        Текст: text/plain; при multipart — первый text/plain part.
        """
        msg_id = self._decode(message.get("Message-ID")) or f"<local-{uid}>"
        from_value = parseaddr(self._decode(message.get("From")) or "")
        subject = self._decode(message.get("Subject") or "")

        body = ""
        if message.is_multipart():
            for part in message.walk():
                if part.get_content_type() == "text/plain" and not part.get_filename():
                    payload = part.get_payload(decode=True)
                    if isinstance(payload, bytes) and payload:
                        charset = part.get_content_charset() or "utf-8"
                        body = payload.decode(charset, errors="replace")
                        break
        else:
            payload = message.get_payload(decode=True)
            if isinstance(payload, bytes) and payload:
                charset = message.get_content_charset() or "utf-8"
                body = payload.decode(charset, errors="replace")

        text = f"{subject}\n\n{body}".strip() if subject else body.strip()
        return {
            "external_id": msg_id,
            "uid": uid,
            "from_name": from_value[0],
            "from_addr": from_value[1].lower(),
            "text": text,
        }


def process_message(conn: Any, adapter: ImapAdapter, payload: dict[str, str]) -> None:  # noqa: ANN401
    """Одно письмо → inbox_messages (channel='email') + флаг \\Seen после успеха.

    Контракт §43: sender_handle = email-адрес — по нему match_client_for_message
    найдёт клиента (find_client_by_contact channel='email'); парсер v2
    запускается внутри record_incoming_message детерминированно.
    """
    message, created = store.record_incoming_message(
        conn,
        channel="email",
        external_id=payload["external_id"],
        chat_id="",
        sender_name=payload["from_name"],
        sender_handle=payload["from_addr"],
        text=payload["text"],
    )
    if created:
        adapter.mark_seen(payload["uid"])
    _ = message  # создан или дубль — оба случая означают «письмо обработано»


def _poll_loop(adapter: ImapAdapter, db_path: Any) -> None:  # noqa: ANN401
    while True:
        messages = adapter.fetch_unseen()
        if messages:
            for payload in messages:
                try:
                    from printcalc_web.db import connect

                    conn = connect(db_path)
                    try:
                        process_message(conn, adapter, payload)
                    finally:
                        conn.close()
                except Exception:  # noqa: BLE001 — ошибка одного письма не роняет поток
                    log.exception("email message processing failed")
        threading.Event().wait(
            float(os.environ.get("PRINTCALC_IMAP_POLL_SECONDS", str(int(POLL_PAUSE_S))))
        )


def start_poller(app: Any) -> None:  # noqa: ANN401
    """Запускает daemon-поток IMAP-поллинга, если задан хост и пользователь.

    Env: PRINTCALC_IMAP_HOST, PRINTCALC_IMAP_USER (обязательны), остальные —
    опциональны. Без них — тихий no-op (email-канал просто выключен).
    """
    if os.environ.get("PRINTCALC_IMAP_ENABLED", "1").strip().lower() in ("0", "false", "no"):
        return
    adapter = ImapAdapter.from_env()
    if adapter is None:
        return
    thread = threading.Thread(
        target=_poll_loop,
        args=(adapter, app.state.db_path),
        daemon=True,
        name="printcalc-email-poller",
    )
    thread.start()
    app.state.email_poller = thread
