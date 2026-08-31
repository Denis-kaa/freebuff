"""Адаптер HeadHunter API (SRC-011, `api.hh.ru/vacancies`).

Преобразует JSON-ответ публичного поиска вакансий в доменные `SourceItem`.
Поля — только из разрешённого набора ADR-011:
`id`, `name`, `description`, `alternate_url`, `published_at`, `employment`,
`experience`, `salary`, `area` (+ `snippet` как текст). Контактные и
персональные поля (`contacts`, `address`, `phone`, `email` и др.) намеренно
не извлекаются.

Live-запрос разрешён только при статусе `ALLOWED` и `can_poll=True`
(двойной гейт, как у `HttpFeedAdapter`/`TrudvsemAdapter`); иначе —
`AdapterError`. Токен приложения передаётся через `http_get` (обычно
заголовок `Authorization: Bearer ...`), никогда не хранится в коде.

Ограничения API (developer agreement + OpenAPI, проверено live 2026-08-23):
- `per_page` максимум 100; пагинация `page`/`pages`;
- поиск `text=`; сортировка по `?order_by=publication_time`;
- для авторизованного приложения ратификации нет в этом запросе;
- поля `snippet` могут содержать `<highlighttext>` — очищаются.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable, Mapping
from datetime import datetime, timezone
from typing import Any, AsyncIterator
from urllib.parse import urlencode, urlparse

from app.domain import AdapterError, SourceItem, SourcePolicy, SourcePolicyStatus

API_BASE = "https://api.hh.ru/vacancies"
DEFAULT_USER_AGENT = "public-request-parser/0.1 (read-only)"

HttpGetter = Callable[[str], Awaitable[bytes]]

_HIGHLIGHT_RE = re.compile(r"<[^>]+>")


async def _default_http_get(url: str) -> bytes:
    """Реальный transport (используется только для allowed-источников)."""
    import httpx

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content


def make_token_http_get(token: str) -> HttpGetter:
    """Создать http_get с Authorization: Bearer <token> для HH API.

    Токен не хранится в объекте адаптера/в коде — подставляется только в
    заголовок запроса. Использовать с env/secret storage (PRP_HH_APP_TOKEN).
    """
    if not token or not token.strip():
        raise AdapterError("HH app token must be non-empty")
    safe_token = token.strip()

    async def _get_with_token(url: str) -> bytes:
        import httpx

        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            response = await client.get(url, headers={"Authorization": f"Bearer {safe_token}"})
            response.raise_for_status()
            return response.content

    return _get_with_token


def _parse_iso(value: str | None) -> datetime | None:
    """ISO 8601 (включая `+0300` без двоеточия) → timezone-aware UTC."""
    if not value or not value.strip():
        return None
    raw = value.strip().replace("Z", "+00:00")
    if len(raw) > 6 and raw[-5] in "+-" and raw[-2] != ":":
        raw = raw[:-5] + raw[-5:-2] + ":" + raw[-2:]
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _strip_tags(value: str) -> str:
    """Убрать HTML-теги подсветки `<highlighttext>` → текстовый фрагмент."""
    return _HIGHLIGHT_RE.sub("", value).strip()


def _name_of(mapping: Mapping[str, Any] | None, key: str) -> str:
    if isinstance(mapping, Mapping):
        return str(mapping.get(key) or "").strip()
    return ""


def _title_from(item: Mapping[str, Any]) -> str:
    return str(item.get("name") or "").strip() or str(item.get("id") or "untitled")


def _text_from(item: Mapping[str, Any]) -> str:
    """Объединить snippet.requirement + responsibility (+description), без тегов."""
    snippet = item.get("snippet")
    parts: list[str] = []
    if isinstance(snippet, Mapping):
        for key in ("requirement", "responsibility"):
            value = snippet.get(key)
            if value:
                parts.append(_strip_tags(str(value)))
    description = item.get("description")
    if description:
        parts.append(_strip_tags(str(description)))
    return " ".join(part for part in parts if part).strip()


def _metadata_from(item: Mapping[str, Any]) -> dict[str, str]:
    """Безопасные технические metadata (без контактов/адресов)."""
    meta: dict[str, str] = {}
    area = _name_of(item.get("area"), "name")
    if area:
        meta["area"] = area
    employment = _name_of(item.get("employment"), "name")
    if employment:
        meta["employment"] = employment
    experience = _name_of(item.get("experience"), "name")
    if experience:
        meta["experience"] = experience
    schedule = _name_of(item.get("schedule"), "name")
    if schedule:
        meta["schedule"] = schedule
    employer = item.get("employer")
    if isinstance(employer, Mapping):
        ename = str(employer.get("name") or "").strip()
        if ename:
            meta["employer"] = ename
    salary = item.get("salary")
    if isinstance(salary, Mapping):
        for key in ("from", "to", "currency"):
            value = salary.get(key)
            if value is not None and str(value).strip():
                meta[f"salary_{key}"] = str(value)
    published = item.get("published_at") or item.get("created_at")
    if published:
        meta["published_at"] = str(published)
    apply_url = item.get("apply_alternate_url")
    if apply_url:
        # Официальная ссылка отклика площадки (не контактные данные):
        # jobseek-режим показывает её как кнопку «Откликнуться».
        meta["apply_url"] = str(apply_url)
    return meta


def _vacancy_to_source_item(item: Mapping[str, Any]) -> SourceItem | None:
    """Одна вакансия `item` → `SourceItem`; None если нельзя построить."""
    item_id = str(item.get("id") or "").strip()
    url = str(
        item.get("alternate_url") or item.get("url") or ""
    ).strip()
    if not item_id or not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    published = _parse_iso(
        item.get("published_at") or item.get("created_at")
    )
    text = _text_from(item)
    return SourceItem(
        item_id=item_id,
        canonical_url=url,
        title=_title_from(item),
        published_at=published,
        summary=text[:1000],
        content=text or None,
        metadata=_metadata_from(item),
    )


def parse_vacancies_payload(payload: bytes) -> list[SourceItem]:
    """Разобрать JSON-ответ `GET /vacancies` в список `SourceItem`.

    Поднимает `AdapterError` при ошибке API (не-JSON, `errors`, отсутствие
    `items`), чтобы вызывающий логировал сбой источника; записи без id/URL
    пропускаются.
    """
    import json

    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AdapterError(f"headhunter: invalid JSON payload: {exc}") from exc
    if not isinstance(data, Mapping):
        raise AdapterError("headhunter: unexpected payload structure")
    errors = data.get("errors")
    if isinstance(errors, list) and errors:
        detail = "; ".join(
            str(e.get("value") or e) if isinstance(e, Mapping) else str(e)
            for e in errors[:2]
        )
        raise AdapterError(f"headhunter: API error: {detail}")
    items = data.get("items")
    if not isinstance(items, list):
        raise AdapterError("headhunter: response missing 'items'")
    result: list[SourceItem] = []
    for raw in items:
        if not isinstance(raw, Mapping):
            continue
        item = _vacancy_to_source_item(raw)
        if item is not None:
            result.append(item)
    return result


class HeadhunterAdapter:
    """Live JSON-адаптер публичного поиска вакансий HeadHunter (SRC-011)."""

    source_id: str

    def __init__(
        self,
        source_id: str,
        *,
        policy: SourcePolicy,
        http_get: HttpGetter | None = None,
        base_url: str = API_BASE,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        if not source_id.strip():
            raise AdapterError("source_id must be non-empty")
        self.source_id = source_id.strip()
        self._policy = policy
        self._http_get = http_get or _default_http_get
        self._base_url = base_url.rstrip("/")
        self._user_agent = user_agent

    def _ensure_allowed_live(self) -> None:
        if self._policy.status is not SourcePolicyStatus.ALLOWED:
            raise AdapterError(
                "live polling requires ALLOWED source policy, "
                f"got {self._policy.status.value}"
            )
        if not self._policy.can_poll:
            raise AdapterError(
                "live polling disabled by source policy (can_poll=False)"
            )

    def _request_url(
        self,
        *,
        text: str | None,
        per_page: int,
        modified_from: datetime | None,
    ) -> str:
        params: dict[str, str] = {"per_page": str(per_page), "page": "0"}
        if text:
            params["text"] = text
        if modified_from is not None:
            # HH поддерживает фильтр по дате публикации
            params["date_from"] = modified_from.astimezone(timezone.utc).isoformat()
        return f"{self._base_url}?{urlencode(params)}"

    async def fetch(
        self,
        *,
        limit: int = 50,
        checkpoint: str | None = None,
        text: str = "",
        modified_from: datetime | None = None,
    ) -> AsyncIterator[SourceItem]:
        """Bounded batch вакансий; пропускает элементы до checkpoint.

        `per_page` максимум 100 (контракт API). Checkpoint-by-id + UNIQUE
        `item_key` в storage дают идемпотентный resume.
        """
        if limit < 1:
            raise AdapterError("limit must be >= 1")
        page_size = min(limit, 100)
        self._ensure_allowed_live()
        url = self._request_url(
            text=text,
            per_page=page_size,
            modified_from=modified_from,
        )
        payload = await self._http_get(url)
        items = parse_vacancies_payload(payload)
        start = 0
        if checkpoint is not None:
            for index, item in enumerate(items):
                if item.item_id == checkpoint:
                    start = index + 1
                    break
        for item in items[start : start + limit]:
            yield item

    async def health(self) -> bool:
        """Техническая доступность API; policy-гейт соблюдается."""
        self._ensure_allowed_live()
        try:
            payload = await self._http_get(self._base_url + "?per_page=1")
            parse_vacancies_payload(payload)
        except Exception:
            return False
        return True


__all__ = [
    "API_BASE",
    "DEFAULT_USER_AGENT",
    "HeadhunterAdapter",
    "make_token_http_get",
    "parse_vacancies_payload",
]