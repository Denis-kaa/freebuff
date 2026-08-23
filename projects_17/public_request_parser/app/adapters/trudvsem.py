"""Адаптер Open Data API «Работа в России» (SRC-012, `opendata.trudvsem.ru`).

Преобразует JSON-ответ API в доменные `SourceItem` без контактных и
персональных полей (поля `contact_list`/`contact_person`/`addresses`
намеренно не извлекаются). Live-запрос разрешён только для `SourcePolicy`
со статусом `ALLOWED` и `can_poll=True` (тот же двойной гейт, что у
`HttpFeedAdapter`); иначе — `AdapterError` без тихого fallback.

Ограничения API (из официальной документации, проверены live 2026-08-23):
- GET, JSON, версия `v1`;
- пагинация `offset`/`limit` (<= 100 записей на страницу);
- поиск по тексту `?text=...`; дельта-обновление `modifiedFrom`/`modifiedTo`
  (ISO 8601);
- при ошибке ответ имеет `status != 200` и `meta.error`.

Сетевой вызов инжектируется через `http_get` для hermetic-тестов.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from datetime import datetime, timezone
from typing import Any, AsyncIterator
from urllib.parse import urlencode, urlparse

from app.domain import AdapterError, SourceItem, SourcePolicy, SourcePolicyStatus

API_BASE = "https://opendata.trudvsem.ru/api/v1/vacancies"
DEFAULT_USER_AGENT = "public-request-parser/0.1 (read-only)"

HttpGetter = Callable[[str***REMOVED***, Awaitable[bytes***REMOVED******REMOVED***


async def _default_http_get(url: str) -> bytes:
    """Реальный transport (используется только для allowed-источников)."""
    import httpx

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content


def _parse_iso(value: str | None) -> datetime | None:
    """ISO 8601 (включая `+0300` без двоеточия) → timezone-aware UTC."""
    if not value or not value.strip():
        return None
    raw = value.strip().replace("Z", "+00:00")
    # нормализовать "+0300" → "+03:00" для fromisoformat (Python 3.11)
    if len(raw) > 6 and raw[-5***REMOVED*** in "+-" and raw[-2***REMOVED*** != ":":
        raw = raw[:-5***REMOVED*** + raw[-5:-2***REMOVED*** + ":" + raw[-2:***REMOVED***
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _title_from(entry: Mapping[str, Any***REMOVED***) -> str:
    """Заголовок вакансии (`job-name`), fallback — id."""
    name = (entry.get("job-name") or "").strip()
    return name or str(entry.get("id") or "untitled")


def _region_name(entry: Mapping[str, Any***REMOVED***) -> str:
    """Название региона, если есть."""
    region = entry.get("region")
    if isinstance(region, Mapping):
        return str(region.get("name") or "")
    return ""


def _requirement_text(entry: Mapping[str, Any***REMOVED***) -> str:
    """Текстовое описание требования без персональных данных."""
    req = entry.get("requirement")
    parts: list[str***REMOVED*** = [***REMOVED***
    if isinstance(req, Mapping):
        education = req.get("education")
        experience = req.get("experience")
        if education:
            parts.append(f"Образование: {education***REMOVED***")
        if experience:
            parts.append(f"Опыт: {experience***REMOVED*** лет")
    skills = entry.get("skills")
    if isinstance(skills, list) and skills:
        parts.append("Навыки: " + ", ".join(str(s) for s in skills))
    return " ".join(parts)


def _metadata_from(entry: Mapping[str, Any***REMOVED***) -> dict[str, str***REMOVED***:
    """Безопасные технические metadata (без контактов и персональных данных)."""
    meta: dict[str, str***REMOVED*** = {***REMOVED***
    for key in ("salary_min", "salary_max", "currency", "schedule", "source"):
        value = entry.get(key)
        if value is not None and str(value).strip():
            meta[key***REMOVED*** = str(value)
    region = _region_name(entry)
    if region:
        meta["region"***REMOVED*** = region
    date_modify = entry.get("date_modify")
    if date_modify:
        meta["date_modify"***REMOVED*** = str(date_modify)
    category = entry.get("category")
    if isinstance(category, Mapping) and category.get("specialisation"):
        meta["category"***REMOVED*** = str(category["specialisation"***REMOVED***)
    skills = entry.get("skills")
    if isinstance(skills, list) and skills:
        meta["skills"***REMOVED*** = ", ".join(str(s) for s in skills if s)
    return meta


def _vacancy_to_source_item(entry: Mapping[str, Any***REMOVED***) -> SourceItem | None:
    """Одна запись `vacancy` → `SourceItem`; None если нельзя построить."""
    item_id = str(entry.get("id") or "").strip()
    url = str(entry.get("vac_url") or "").strip()
    if not item_id or not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"***REMOVED*** or not parsed.netloc:
        return None
    published = _parse_iso(entry.get("creation-date")) or _parse_iso(
        entry.get("date_modify")
    )
    duty = str(entry.get("duty") or "").strip()
    requirement = _requirement_text(entry)
    content = " ".join(part for part in (duty, requirement) if part).strip()
    return SourceItem(
        item_id=item_id,
        canonical_url=url,
        title=_title_from(entry),
        published_at=published,
        summary=duty[:1000***REMOVED***,
        content=content or None,
        metadata=_metadata_from(entry),
    )


def parse_vacancy_payload(payload: bytes) -> list[SourceItem***REMOVED***:
    """Разобрать байтовый JSON-ответ API в список `SourceItem`.

    Поднимает `AdapterError` при глобальной ошибке API (не-JSON, `status !=
    200`, отсутствие `results`), чтобы вызывающий логировал сбой источника,
    а не получал молчаливый пустой результат. Записи без id/vac_url
    пропускаются (невозможно построить канонический ключ).
    """
    import json

    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AdapterError(f"trudvsem: invalid JSON payload: {exc***REMOVED***") from exc
    return parse_payload_dict(data)


def parse_payload_dict(data: Any) -> list[SourceItem***REMOVED***:
    """Парсер словаря payload → список `SourceItem` (или `AdapterError`)."""
    if not isinstance(data, Mapping):
        raise AdapterError("trudvsem: unexpected payload structure")
    status = str(data.get("status") or "500")
    if status != "200":
        error = ""
        meta = data.get("meta")
        if isinstance(meta, Mapping):
            error = str(meta.get("error") or "")
        raise AdapterError(
            f"trudvsem: API reported {status***REMOVED***" + (f": {error***REMOVED***" if error else "")
        )
    results = data.get("results")
    if not isinstance(results, Mapping):
        raise AdapterError("trudvsem: response missing 'results'")
    vacancies = results.get("vacancies")
    if not isinstance(vacancies, list):
        return [***REMOVED***
    items: list[SourceItem***REMOVED*** = [***REMOVED***
    for raw in vacancies:
        if not isinstance(raw, Mapping):
            continue
        entry = raw.get("vacancy")
        if not isinstance(entry, Mapping):
            continue
        item = _vacancy_to_source_item(entry)
        if item is not None:
            items.append(item)
    return items


class TrudvsemAdapter:
    """Live JSON-адаптер Open Data API «Работа в России» (SRC-012)."""

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
                f"got {self._policy.status.value***REMOVED***"
            )
        if not self._policy.can_poll:
            raise AdapterError(
                "live polling disabled by source policy (can_poll=False)"
            )

    def _request_url(
        self,
        *,
        limit: int,
        modified_from: datetime | None,
    ) -> str:
        params: dict[str, str***REMOVED*** = {"limit": str(limit), "offset": "0"***REMOVED***
        if modified_from is not None:
            params["modifiedFrom"***REMOVED*** = modified_from.astimezone(timezone.utc).isoformat()
        return f"{self._base_url***REMOVED***?{urlencode(params)***REMOVED***"

    async def fetch(
        self,
        *,
        limit: int = 50,
        checkpoint: str | None = None,
        modified_from: datetime | None = None,
    ) -> AsyncIterator[SourceItem***REMOVED***:
        """Загрузить bounded batch вакансий, пропуская элементы до checkpoint.

        API-квоты: `limit` <= 100 на страницу; пагинация следующих страниц
        остаётся отдельным режимом P10. Checkpoint-by-id вместе с UNIQUE
        `item_key` в storage даёт идемпотентный resume.
        """
        if limit < 1:
            raise AdapterError("limit must be >= 1")
        page_limit = min(limit, 100)
        self._ensure_allowed_live()
        url = self._request_url(limit=page_limit, modified_from=modified_from)
        payload = await self._http_get(url)
        items = parse_vacancy_payload(payload)
        start = 0
        if checkpoint is not None:
            for index, item in enumerate(items):
                if item.item_id == checkpoint:
                    start = index + 1
                    break
        for item in items[start : start + limit***REMOVED***:
            yield item

    async def health(self) -> bool:
        """Техническая доступность API; policy-гейт соблюдается."""
        self._ensure_allowed_live()
        try:
            payload = await self._http_get(self._base_url + "?limit=1")
            parse_vacancy_payload(payload)
        except Exception:
            return False
        return True


__all__ = [
    "API_BASE",
    "DEFAULT_USER_AGENT",
    "TrudvsemAdapter",
    "parse_payload_dict",
    "parse_vacancy_payload",
***REMOVED***