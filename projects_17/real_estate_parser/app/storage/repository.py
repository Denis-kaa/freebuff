"""storage/repository.py — upsert-логика и запись событий.

Идемпотентность: повторный прогон не создаёт дублей.
Natural key: (source, external_id); fallback — hash(url).
Изменение цены фиксируется событием price_changed.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Property, PropertyEvent


def url_hash(url: str) -> str:
    """MD5 нормализованного URL (без трекинг-параметров) — fallback-ключ."""
    parts = urlsplit(url)
    keep = [
        (k, v)
        for k, v in parse_qsl(parts.query)
        if not k.lower().startswith(("utm_", "yclid", "gclid", "fbclid"))
    ]
    clean = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(keep), ""))
    return hashlib.md5(clean.encode("utf-8")).hexdigest()


class PropertyRepository:
    """Идемпотентная запись объектов недвижимости.

    Сравнение по natural key (source, external_id): новый объект → created,
    та же цена → только last_seen_at, другая цена → price_changed событие.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        # Один AsyncSession нельзя использовать из нескольких корутин одновременно:
        # interleaved flush/add вызывает "Session is already flushing". Все операции
        # записи на этой сессии сериализуем локом; сетевой fetch остаётся параллельным.
        self._lock = asyncio.Lock()

    async def upsert_listing(self, listing) -> tuple[Property, str]:
        """Вставить или обновить объект из Listing адаптера.

        Возвращает (объект, исход) где исход — "created" | "price_changed" | "updated" | "unchanged".
        """
        async with self._lock:
            return await self._upsert_listing_locked(listing)

    async def _upsert_listing_locked(self, listing) -> tuple[Property, str]:
        result = await self.session.execute(
            select(Property).where(
                Property.source == listing.source,
                Property.external_id == listing.external_id,
            )
        )
        existing = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)

        if existing is None:
            prop = Property(
                source=listing.source,
                external_id=listing.external_id,
                url=listing.url,
                url_hash=url_hash(listing.url),
                title=listing.title,
                price=listing.price,
                currency=listing.currency,
                area_m2=listing.area_m2,
                rooms=listing.rooms,
                address=listing.address,
                property_type=listing.property_type,
                raw=json.dumps(listing.extra, ensure_ascii=False) if listing.extra else None,
                first_seen_at=now,
                last_seen_at=now,
                updated_at=now,
            )
            self.session.add(prop)
            await self.session.flush()
            await self.record_event(prop.id, "created", None, {"price": prop.price})
            return prop, "created"

        old_price = existing.price
        price_changed = listing.price is not None and str(old_price) != str(listing.price)
        outcome = "price_changed" if price_changed else ("updated" if _changed(existing, listing) else "unchanged")
        existing.url = listing.url
        existing.url_hash = url_hash(listing.url)
        existing.title = listing.title
        existing.price = listing.price if listing.price is not None else existing.price
        existing.currency = listing.currency or existing.currency
        existing.area_m2 = listing.area_m2 if listing.area_m2 is not None else existing.area_m2
        existing.rooms = listing.rooms if listing.rooms is not None else existing.rooms
        existing.address = listing.address or existing.address
        existing.property_type = listing.property_type or existing.property_type
        existing.raw = json.dumps(listing.extra, ensure_ascii=False) if listing.extra else existing.raw
        existing.last_seen_at = now
        existing.updated_at = now
        if price_changed:
            await self.record_event(
                existing.id, "price_changed", {"price": str(old_price)}, {"price": str(listing.price)}
            )
        return existing, outcome

    async def record_event(self, prop_id: int, kind: str, old: Any, new: Any) -> None:
        """Запись события (created/price_changed/removed/updated)."""
        event = PropertyEvent(
            property_id=prop_id,
            kind=kind,
            old_value=json.dumps(old, ensure_ascii=False) if old is not None else None,
            new_value=json.dumps(new, ensure_ascii=False) if new is not None else None,
        )
        self.session.add(event)

    async def count(self) -> int:
        result = await self.session.execute(select(Property.id))
        return len(result.scalars().all())


def _changed(existing: Property, listing) -> bool:
    """True если существенно изменились поля (кроме last_seen)."""
    if listing.price is not None and str(existing.price) != str(listing.price):
        return True
    if listing.area_m2 is not None and str(existing.area_m2) != str(listing.area_m2):
        return True
    if listing.rooms is not None and str(existing.rooms) != str(listing.rooms):
        return True
    if listing.title is not None and existing.title != listing.title:
        return True
    return False
