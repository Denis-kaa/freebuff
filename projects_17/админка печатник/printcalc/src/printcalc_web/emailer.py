"""SMTP-адаптер Этапа 6b (роадмап v6, промт_4 §43/§44/§47).

Дизайн — зеркально telegram.py (Adapter Pattern §47): EmailSender —
единственное место, знающее SMTP. Сеть/креды — только env (CODE_QUALITY 4.7):

    PRINTCALC_SMTP_HOST   — хост SMTP (пусто → канал email выключен)
    PRINTCALC_SMTP_PORT   — порт (default 587, STARTTLS)
    PRINTCALC_SMTP_USER   — логин
    PRINTCALC_SMTP_PASSWORD — пароль
    PRINTCALC_SMTP_FROM   — адрес отправителя (default = user)
    PRINTCALC_SMTP_TLS    — «1» = STARTTLS (default), «0» = без TLS (локальные relay)

Без хоста send() возвращает False с понятной причиной — приложение работает,
email-канал просто «не включён» (та же философия, что у Telegram-поллера).
"""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import Any


def is_configured() -> bool:
    """Email-канал включён, если задан SMTP-хост."""
    return bool(os.environ.get("PRINTCALC_SMTP_HOST", "").strip())


class EmailSender:
    """Обёртка smtplib: send(). Ошибки не роняют вызывающий поток —
    возвращают (ok, error) для честной записи в outbox."""

    def __init__(self, *, host: str, port: int, user: str, password: str,
                 from_addr: str, use_tls: bool) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._from = from_addr
        self._use_tls = use_tls

    @classmethod
    def from_env(cls) -> "EmailSender | None":
        host = os.environ.get("PRINTCALC_SMTP_HOST", "").strip()
        if not host:
            return None
        return cls(
            host=host,
            port=int(os.environ.get("PRINTCALC_SMTP_PORT", "587")),
            user=os.environ.get("PRINTCALC_SMTP_USER", "").strip(),
            password=os.environ.get("PRINTCALC_SMTP_PASSWORD", ""),
            from_addr=os.environ.get("PRINTCALC_SMTP_FROM", "").strip()
            or os.environ.get("PRINTCALC_SMTP_USER", "").strip(),
            use_tls=os.environ.get("PRINTCALC_SMTP_TLS", "1").strip().lower()
            not in ("0", "false", "no"),
        )

    def send(self, to: str, subject: str, body: str) -> tuple[bool, str]:
        """Отправляет письмо; (False, причина) при любой ошибке — не исключение."""
        if not self._host:
            return False, "SMTP не настроен (PRINTCALC_SMTP_HOST пуст)"
        message = EmailMessage()
        message["From"] = self._from or self._user
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        try:
            with smtplib.SMTP(self._host, self._port, timeout=20) as server:
                server.ehlo()
                if self._use_tls:
                    server.starttls()
                    server.ehlo()
                if self._user:
                    server.login(self._user, self._password)
                server.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            return False, f"SMTP: {exc}"
        return True, ""


def _noop_sender(to: str, subject: str, body: str) -> tuple[bool, str]:
    """Заглушка для тестов/ручного канала: письмо не уходит, но запись честная."""
    return False, "канал manual не отправляет сообщения"


def dispatch(channel: str, recipient: str, subject: str, body: str) -> tuple[bool, str]:
    """Единая точка отправки по каналу (закрытый словарь §44)."""
    if channel == "email":
        sender = EmailSender.from_env()
        if sender is None:
            return False, "SMTP не настроен (PRINTCALC_SMTP_HOST пуст)"
        return sender.send(recipient, subject, body)
    if channel == "telegram":
        from printcalc_web import telegram

        token = os.environ.get("PRINTCALC_TG_TOKEN", "").strip()
        if not token:
            return False, "Telegram не настроен (PRINTCALC_TG_TOKEN пуст)"
        adapter: Any = telegram.TelegramAdapter(token)
        ok = adapter.send_message(recipient, f"{subject}\n\n{body}".strip())
        return ok, "" if ok else "Telegram API отклонил сообщение"
    return _noop_sender(recipient, subject, body)
