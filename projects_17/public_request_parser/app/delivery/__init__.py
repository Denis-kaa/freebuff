"""Delivery layer для Public Request Parser (P7).

P7 реализует:

- `render_card()` — HTML-карточка Telegram (HTML escaping обязателен,
  никакого Markdown-v2);
- `MessageTransport` — async-протокол одного канала (реальный Telegram
  transport — отдельный policy-aware adapter, здесь только контракт);
- `TelegramDelivery` — идемпотентная доставка поверх `SqliteStorage`:
  `delivery_key = owner:publish:decision`, dry-run, retry после failed,
  строгий owner-гейт, без outbound к автору.

Модуль не выполняет сетевых вызовов, не импортирует платформенный код
и не содержит live-credentials.
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from app.domain import (
    ContractValidationError,
    DeliveryAttempt,
    DeliveryStatus,
    MatchDecision,
    Publication,
)
from app.storage import SqliteStorage


@dataclass(frozen=True, slots=True)
class DeliveryTransportError(RuntimeError):
    """Сбой транспорта доставки (provider недоступен, rate limit и т.п.)."""

    code: str


def _escape(value: str) -> str:
    """HTML-escape для Telegram HTML-разметки."""
    return html.escape(value, quote=False)


def delivery_key_for(
    publication: Publication,
    decision: MatchDecision,
    *,
    owner_scope: str,
) -> str:
    """Идемпотентный ключ доставки: scope + публикация + версия профиля."""
    return f"{owner_scope***REMOVED***:{publication.item_key***REMOVED***:p{decision.profile_version***REMOVED***"


class MessageTransport(Protocol):
    """Async-протокол отправки одного сообщения (реальный adapter — отдельно)."""

    async def send(
        self,
        *,
        chat_id: str,
        text: str,
        disable_web_page_preview: bool = True,
    ) -> str:
        """Отправить сообщение и вернуть provider message id."""
        ...


@dataclass(frozen=True, slots=True)
class DeliveryCard:
    """Готовая HTML-карточка и метаданные для доставки."""

    text: str
    parse_mode: str = "HTML"


def render_card(
    publication: Publication,
    decision: MatchDecision,
    *,
    score_label: str | None = None,
) -> DeliveryCard:
    """Собрать HTML-карточку публикации и decision.

    Title/summary/категории экранируются; ссылка — только источник, никаких
    данных автора. `score_label` — display-строка, не влияет на логику.
    """
    title = _escape(publication.title)
    summary = _escape(publication.summary or "")
    categories = ", ".join(
        _escape(value)
        for value in publication.metadata.get("categories", "").split(",")
        if value.strip()
    )
    score_text = f" · score {score_label***REMOVED***" if score_label else ""
    categories_line = f"\nКатегории: {categories***REMOVED***" if categories else ""

    text = (
        f"<b>{title***REMOVED***</b>\n"
        f"{summary***REMOVED***\n"
        f"🔗 <a href=\"{_escape(publication.canonical_url)***REMOVED***\">Открыть источник</a>"
        f"{score_text***REMOVED***{categories_line***REMOVED***"
    )
    return DeliveryCard(text=text, parse_mode="HTML")


class TelegramDelivery:
    """Идемпотентная доставка карточек: dry-run, owner-гейт, retry."""

    def __init__(
        self,
        *,
        transport: MessageTransport | None = None,
        storage: SqliteStorage | None = None,
        default_owner_scope: str = "operator",
        dry_run: bool = False,
        default_chat_id: str = "",
    ) -> None:
        if not default_owner_scope.strip():
            raise ContractValidationError("default_owner_scope must be non-empty")
        self.transport = transport
        self.storage = storage
        self.default_owner_scope = default_owner_scope.strip()
        self.dry_run = dry_run
        self.default_chat_id = default_chat_id
        self.allowed_owner_scopes: frozenset[str***REMOVED*** = frozenset({self.default_owner_scope***REMOVED***)
        self._attempts: dict[str, DeliveryAttempt***REMOVED*** = {***REMOVED***

    # ------------------------------------------------------------------
    def _existing_sent(self, key: str) -> str | None:
        """provider_message_id сохранённой SENT-попытки (storage или cache)."""
        cached = self._attempts.get(key)
        if cached is not None and cached.status is DeliveryStatus.SENT:
            return cached.provider_message_id
        if self.storage is not None:
            attempt = self.storage.get_delivery_attempt(key)
            if attempt is not None and attempt.status is DeliveryStatus.SENT:
                return attempt.provider_message_id
        return None

    def _store(
        self,
        key: str,
        attempt: DeliveryAttempt,
        *,
        publication_key: str,
        profile_id: str,
        profile_version: int,
    ) -> None:
        self._attempts[key***REMOVED*** = attempt
        if self.storage is not None:
            self.storage.save_delivery_attempt(
                attempt,
                publication_key=publication_key,
                profile_id=profile_id,
                profile_version=profile_version,
            )

    # ------------------------------------------------------------------
    async def deliver(
        self,
        publication: Publication,
        decision: MatchDecision,
        *,
        owner_scope: str | None = None,
        chat_id: str | None = None,
    ) -> DeliveryAttempt:
        """Доставить карточку идемпотентно.

        - owner_scope обязан совпадать с владельцем decision (single-tenant guard);
        - dry_run: рендер без отправки → `SKIPPED`;
        - повторная доставка того же ключа → возвращает сохранённый SENT,
          дубль не создаётся;
        - сбой транспорта → `FAILED` с error_code; последующий retry заменит
          failed-попытку в storage (upsert).
        """
        effective_owner = (owner_scope or self.default_owner_scope).strip()
        if not effective_owner:
            raise ContractValidationError("owner_scope must be non-empty")
        if effective_owner not in self.allowed_owner_scopes:
            raise ContractValidationError("owner_scope is not allowed for this delivery")

        key = delivery_key_for(publication, decision, owner_scope=effective_owner)
        existing = self._existing_sent(key)
        if existing is not None:
            return DeliveryAttempt(
                delivery_key=key,
                status=DeliveryStatus.SENT,
                attempted_at=datetime.now(timezone.utc),
                provider_message_id=existing,
            )

        card = render_card(publication, decision, score_label=f"{decision.score:.2f***REMOVED***")

        if self.dry_run or self.transport is None:
            attempt = DeliveryAttempt(
                delivery_key=key,
                status=DeliveryStatus.SKIPPED,
                attempted_at=datetime.now(timezone.utc),
            )
            self._store(
                key,
                attempt,
                publication_key=publication.item_key,
                profile_id=decision.profile_id,
                profile_version=decision.profile_version,
            )
            return attempt

        try:
            message_id = await self.transport.send(
                chat_id=chat_id or self.default_chat_id,
                text=card.text,
            )
        except DeliveryTransportError as exc:
            attempt = DeliveryAttempt(
                delivery_key=key,
                status=DeliveryStatus.FAILED,
                attempted_at=datetime.now(timezone.utc),
                error_code=exc.code,
            )
        else:
            attempt = DeliveryAttempt(
                delivery_key=key,
                status=DeliveryStatus.SENT,
                attempted_at=datetime.now(timezone.utc),
                provider_message_id=message_id,
            )
        self._store(
            key,
            attempt,
            publication_key=publication.item_key,
            profile_id=decision.profile_id,
            profile_version=decision.profile_version,
        )
        return attempt


class CardTemplateError(ValueError):
    """Ошибка шаблона карточки (пока не используется, зарезервировано)."""


__all__ = [
    "CardTemplateError",
    "DeliveryCard",
    "DeliveryTransportError",
    "MessageTransport",
    "TelegramDelivery",
    "delivery_key_for",
    "render_card",
***REMOVED***