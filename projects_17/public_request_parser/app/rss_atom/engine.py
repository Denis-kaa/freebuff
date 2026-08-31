"""Автономный RSS/Atom engine для Public Request Parser.

P4 намеренно ограничен разбором переданного документа. Сетевой transport,
ETag/Last-Modified и live polling остаются отдельными policy-aware слоями.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import AsyncIterator, Iterable
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

from app.domain import (
    AdapterError,
    CheckpointStore,
    Publication,
    SourceAdapter,
    SourceItem,
    SourcePolicy,
    SourcePolicyStatus,
)


@dataclass(frozen=True, slots=True)
class FeedWarning:
    """Контролируемое предупреждение о пропущенном или неполном item."""

    code: str
    message: str
    item_hint: str | None = None


@dataclass(frozen=True, slots=True)
class FeedParseResult:
    """Результат разбора с сохранением порядка и warnings."""

    format: str
    items: tuple[SourceItem, ...]
    warnings: tuple[FeedWarning, ...] = ()


_XML_NAME_RE = re.compile(r"\{[^)]+\*]")


def _local_name(tag: str) -> str:
    """Убрать namespace из XML tag."""
    return _XML_NAME_RE.sub("", tag)


def _text(element: ElementTree.Element | None) -> str:
    """Собрать текст элемента вместе с CDATA/вложенными nodes."""
    if element is None:
        return ""
    return "".join(element.itertext()).strip()


def _first_child(element: ElementTree.Element, *names: str) -> ElementTree.Element | None:
    """Найти первого прямого ребёнка по local-name."""
    wanted = set(names)
    return next(
        (child for child in list(element) if _local_name(child.tag) in wanted),
        None,
    )


def _parse_datetime(value: str | None) -> datetime | None:
    """Разобрать RFC 2822 или ISO-8601 дату и привести её к UTC."""
    if not value or not value.strip():
        return None
    raw = value.strip()
    parsed: datetime
    try:
        parsed = parsedate_to_datetime(raw)
    except (TypeError, ValueError, IndexError):
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _absolute_url(value: str, base_url: str | None) -> str | None:
    """Получить абсолютный HTTP(S) URL."""
    if base_url:
        value = urljoin(base_url, value)
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return value


def _entry_url(entry: ElementTree.Element, base_url: str | None) -> str | None:
    """Извлечь canonical URL из RSS link или Atom alternate link."""
    direct = _first_child(entry, "link")
    if direct is not None:
        href = direct.attrib.get("href", "").strip()
        if href and direct.attrib.get("rel", "alternate") in {"alternate", ""}:
            result = _absolute_url(href, base_url)
            if result:
                return result
        link_text = _text(direct)
        if link_text:
            result = _absolute_url(link_text, base_url)
            if result:
                return result
    return None


def _item_id(entry: ElementTree.Element, canonical_url: str) -> str:
    """Извлечь стабильный source ID или детерминированно вывести его из URL."""
    raw_id = _text(_first_child(entry, "guid", "id"))
    if raw_id:
        return raw_id
    digest = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()[:24]
    return f"url-{digest}"


def _content(entry: ElementTree.Element) -> str | None:
    """Выбрать полный content, затем summary/description."""
    full = _first_child(entry, "encoded", "content")
    summary = _first_child(entry, "summary", "description")
    value = _text(full) or _text(summary)
    return value or None


def _published_at(entry: ElementTree.Element) -> datetime | None:
    """Выбрать published/pubDate, затем updated."""
    for name in ("published", "pubDate", "updated"):
        value = _parse_datetime(_text(_first_child(entry, name)))
        if value is not None:
            return value
    return None


class RSSAtomParser:
    """Разобрать RSS 2.x или Atom 1.0 bytes/string без сети."""

    def __init__(self, source_id: str, *, base_url: str | None = None) -> None:
        if not source_id.strip():
            raise ValueError("source_id must be non-empty")
        self.source_id = source_id.strip()
        self.base_url = base_url

    def parse(self, payload: bytes | str) -> FeedParseResult:
        """Вернуть нормализованные source items и controlled warnings."""
        try:
            root = ElementTree.fromstring(payload)
        except (ElementTree.ParseError, TypeError, ValueError) as exc:
            raise AdapterError(f"invalid RSS/Atom XML: {exc}") from exc

        root_name = _local_name(root.tag).lower()
        if root_name == "rss":
            entries = _first_child(root, "channel")
            if entries is None:
                raise AdapterError("RSS document has no channel")
            raw_entries = [child for child in list(entries) if _local_name(child.tag) == "item"]
            feed_format = "rss"
        elif root_name == "feed":
            raw_entries = [child for child in list(root) if _local_name(child.tag) == "entry"]
            feed_format = "atom"
        else:
            raise AdapterError(f"unsupported feed root: {root_name}")

        items: list[SourceItem] = []
        warnings: list[FeedWarning] = []
        for index, entry in enumerate(raw_entries):
            canonical_url = _entry_url(entry, self.base_url)
            title = _text(_first_child(entry, "title"))
            if canonical_url is None:
                warnings.append(FeedWarning("missing_url", "item skipped: no absolute link", str(index)))
                continue
            if not title:
                warnings.append(FeedWarning("missing_title", "item skipped: empty title", canonical_url))
                continue
            item = SourceItem(
                item_id=_item_id(entry, canonical_url),
                canonical_url=canonical_url,
                title=title,
                published_at=_published_at(entry),
                summary=_text(_first_child(entry, "summary", "description")),
                content=_content(entry),
                metadata={
                    "feed_format": feed_format,
                    "categories": ",".join(
                        value
                        for child in list(entry)
                        if _local_name(child.tag) == "category"
                        for value in (child.attrib.get("term", "") or _text(child),)
                        if value
                    ),
                },
            )
            items.append(item)
            if _first_child(entry, "published", "pubDate", "updated") is not None and item.published_at is None:
                warnings.append(FeedWarning("invalid_date", "date ignored: unsupported format", canonical_url))

        return FeedParseResult(feed_format, tuple(items), tuple(warnings))


def normalize_source_item(
    source_id: str,
    item: SourceItem,
    *,
    fetched_at: datetime | None = None,
    max_text_chars: int | None = None,
) -> Publication:
    """Преобразовать SourceItem в доменную Publication и применить text cap."""
    when = fetched_at or datetime.now(timezone.utc)
    if when.tzinfo is None or when.utcoffset() is None:
        raise AdapterError("fetched_at must be timezone-aware")
    content = item.content
    if max_text_chars is not None:
        if max_text_chars < 0:
            raise ValueError("max_text_chars must be >= 0")
        content = content[:max_text_chars] if content is not None else None
    return Publication(
        source_id=source_id,
        item_id=item.item_id,
        canonical_url=item.canonical_url,
        title=item.title,
        published_at=item.published_at,
        summary=item.summary,
        content=content,
        fetched_at=when,
        metadata=item.metadata,
    )


def deduplicate_publications(publications: Iterable[Publication]) -> tuple[Publication, ...]:
    """Оставить первый item по source-scoped key и canonical URL."""
    seen_keys: set[str] = set()
    seen_urls: set[str] = set()
    unique: list[Publication] = []
    for publication in publications:
        if publication.item_key in seen_keys or publication.canonical_url in seen_urls:
            continue
        seen_keys.add(publication.item_key)
        seen_urls.add(publication.canonical_url)
        unique.append(publication)
    return tuple(unique)


class InMemoryCheckpointStore:
    """Hermetic async checkpoint store; SQLite реализация относится к P6."""

    def __init__(self) -> None:
        self._values: dict[str, str] = {}

    async def get(self, source_id: str) -> str | None:
        """Получить последний committed item ID."""
        return self._values.get(source_id)

    async def commit(self, source_id: str, item_id: str) -> None:
        """Идемпотентно сохранить item ID."""
        self._values[source_id] = item_id


class FixtureFeedAdapter:
    """SourceAdapter для bytes/string fixture без live polling."""

    def __init__(
        self,
        source_id: str,
        payload: bytes | str,
        *,
        policy: SourcePolicy | None = None,
        base_url: str | None = None,
    ) -> None:
        self.source_id = source_id
        self._payload = payload
        self._parser = RSSAtomParser(source_id, base_url=base_url)
        self._policy = policy

    async def fetch(
        self,
        *,
        limit: int = 50,
        checkpoint: str | None = None,
    ) -> AsyncIterator[SourceItem]:
        """Отдать bounded items после checkpoint; adapter не обращается к сети."""
        if limit < 1:
            raise AdapterError("limit must be >= 1")
        if self._policy is not None and self._policy.status is SourcePolicyStatus.ALLOWED:
            raise AdapterError("FixtureFeedAdapter cannot be used as live allowed transport")
        result = self._parser.parse(self._payload)
        start = 0
        if checkpoint is not None:
            for index, item in enumerate(result.items):
                if item.item_id == checkpoint:
                    start = index + 1
                    break
        for item in result.items[start : start + limit]:
            yield item

    async def health(self) -> bool:
        """Проверить, что fixture парсится; это не live source health."""
        try:
            self._parser.parse(self._payload)
        except AdapterError:
            return False
        return True


__all__ = [
    "FeedParseResult",
    "FeedWarning",
    "FixtureFeedAdapter",
    "InMemoryCheckpointStore",
    "RSSAtomParser",
    "deduplicate_publications",
    "normalize_source_item",
]
