"""services/notifications.py — порт отправки уведомлений и сервис.

Канал (Telegram) — `NotificationChannel`. Для тестов подменяется на фейк.
Сервис `NotificationService` всегда пишет в БД (журнал), плюс вызывает
канал отправки.
"""

from __future__ import annotations

import logging
from typing import Iterable, Optional, Protocol

from ..db.repository import Repository
from ..models import Notification, NotificationKind


class NotificationChannel(Protocol):
    """Контракт канала отправки. Реальная реализация использует aiogram.Bot.send_message."""

    async def send(self, user_id: int, text: str) -> None: ...

    async def broadcast(self, user_ids: Iterable[int], text: str) -> None: ...


class FakeChannel:
    """Канал-заглушка для тестов: ничего не отправляет, но запоминает вызовы."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple]] = []

    async def send(self, user_id: int, text: str) -> None:
        self.calls.append(("send", (user_id, text)))

    async def broadcast(self, user_ids: Iterable[int], text: str) -> None:
        self.calls.append(("broadcast", (list(user_ids), text)))


class NotificationService:
    def __init__(self, repo: Repository, channel: NotificationChannel) -> None:
        self._repo = repo
        self._channel = channel

    async def notify_user(
        self,
        user_id: int,
        kind: NotificationKind,
        text: str,
        *,
        payload: Optional[str] = None,
    ) -> Notification:
        n = self._repo.add_notification(
            text=text, kind=kind, user_id=user_id, payload=payload
        )
        # Защитный try/except: AiogramChannel ловит сам, но контракт
        # NotificationChannel этого не гарантирует (фикс ревью #7).
        try:
            await self._channel.send(user_id, text)
        except Exception as exc:
            logging.warning(
                "send to user=%s via channel failed: %r; db-log #%s сохранён.",
                user_id, exc, n.id,
            )
        return n

    async def notify_admins(
        self,
        admin_ids: list[int],
        kind: NotificationKind,
        text: str,
        *,
        payload: Optional[str] = None,
    ) -> Notification:
        n = self._repo.add_notification(
            text=text,
            kind=kind,
            broadcast_to_admins=True,
            payload=payload,
        )
        if admin_ids:
            try:
                await self._channel.broadcast(admin_ids, text)
            except Exception as exc:
                logging.warning(
                    "broadcast to admins=%s via channel failed: %r; db-log #%s сохранён.",
                    admin_ids, exc, n.id,
                )
        return n

    async def notify_seller(
        self,
        seller_id: int,
        kind: NotificationKind,
        text: str,
        *,
        payload: Optional[str] = None,
    ) -> Notification:
        return await self.notify_user(seller_id, kind, text, payload=payload)

    def list_for_user(self, user_id: int, limit: int = 10) -> list[Notification]:
        return self._repo.list_notifications_for_user(user_id, limit=limit)
