"""Интеграция с Email."""

from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText

from realtor_os.logger import setup_logger

_LOGGER = setup_logger("realtor_os.email")


class EmailError(Exception):
    """Ошибка отправки Email."""


class EmailClient:
    """Клиент для отправки Email через SMTP."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> None:
        self.host = host or os.environ.get("EMAIL_HOST", "smtp.yandex.ru")
        self.port = port or int(os.environ.get("EMAIL_PORT", "465"))
        self.user = user or os.environ.get("EMAIL_USER", "")
        self.password = password or os.environ.get("EMAIL_PASSWORD", "")

    def send(self, to: str, subject: str, body: str) -> dict[str, str***REMOVED***:
        """Отправить письмо.

        Args:
            to: Адрес получателя.
            subject: Тема.
            body: Текст письма.

        Returns:
            Статус отправки.
        """
        if not self.user or not self.password:
            raise EmailError("Email credentials are not configured")

        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"***REMOVED*** = subject
        msg["From"***REMOVED*** = self.user
        msg["To"***REMOVED*** = to

        try:
            with smtplib.SMTP_SSL(self.host, self.port, timeout=30) as server:
                server.login(self.user, self.password)
                server.sendmail(self.user, [to***REMOVED***, msg.as_string())
        except smtplib.SMTPException as exc:
            raise EmailError(f"SMTP error: {exc***REMOVED***") from exc

        return {"status": "ok", "to": to***REMOVED***
