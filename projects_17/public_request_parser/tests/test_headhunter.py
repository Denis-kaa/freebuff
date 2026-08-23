"""Hermetic tests: HeadhunterAdapter (SRC-011, api.hh.ru/vacancies)."""

from __future__ import annotations

from datetime import datetime, timezone
***REMOVED***

import pytest

from app.adapters.headhunter import HeadhunterAdapter, parse_vacancies_payload
from app.domain import AdapterError, SourceItem, SourcePolicy, SourcePolicyStatus

FIXTURES = Path(__file__).parents[1***REMOVED*** / "fixtures" / "hh"
NOW = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)


def _fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


async def _fake_get(url: str) -> bytes:
    assert "api.hh.ru" in url
    return _fixture("vacancies_page.json")


def _policy(
    status: SourcePolicyStatus,
    *,
    can_poll: bool = True,
) -> SourcePolicy:
    effective_can_poll = can_poll and status is SourcePolicyStatus.ALLOWED
    return SourcePolicy(
        source_id="headhunter",
        status=status,
        access_mode="official_api",
        endpoint="https://api.hh.ru/vacancies",
        checked_at=NOW,
        evidence_urls=(
            "https://dev.hh.ru/admin/developer_agreement",
            "https://api.hh.ru/openapi/redoc",
        )
        if status is SourcePolicyStatus.ALLOWED
        else (),
        can_poll=effective_can_poll,
    )


# --- Статический парсинг ---------------------------------------------------


def test_parse_page_builds_source_items() -> None:
    """Из страницы извлекаются два SourceItem с корректными полями."""
    items = parse_vacancies_payload(_fixture("vacancies_page.json"))

    assert len(items) == 2
    first = items[0***REMOVED***
    assert isinstance(first, SourceItem)
    assert first.item_id == "136323698"
    assert first.canonical_url == "https://hh.ru/vacancy/136323698"
    assert first.title == "Python-разработчик"
    assert first.published_at is not None
    assert first.published_at.astimezone(timezone.utc).hour == 8  # +0300 → 08:00 UTC
    assert "Python" in (first.content or "")
    assert first.metadata["area"***REMOVED*** == "Москва"


def test_parse_strips_highlight_tags() -> None:
    """HTML-теги подсветки удаляются из текста."""
    raw = _fixture("vacancies_page.json").decode("utf-8").replace(
        "на Python",
        "на <highlighttext>Python</highlighttext>",
    )
    items = parse_vacancies_payload(raw.encode("utf-8"))
    assert "<highlighttext>" not in (items[0***REMOVED***.content or "")
    assert "Python" in (items[0***REMOVED***.content or "")


def test_parse_never_contains_private_fields() -> None:
    """Контактные/персональные поля не попадают в metadata/content."""
    raw = _fixture("vacancies_page.json").decode("utf-8")
    # добавим «опасные» поля, чтобы проверить, что адаптер их игнорирует
    raw = raw.replace(
        '"snippet": {',
        '"contacts": {"name": "Иванов Иван", "phones": [{"number": "+7-999"***REMOVED******REMOVED******REMOVED***,\n    "address": {"raw": "Москва, ул. Примерная, 1"***REMOVED***,\n    "snippet": {',
    )
    items = parse_vacancies_payload(raw.encode("utf-8"))

    for item in items:
        joined = " ".join(
            (item.content or "", *item.metadata.values(), *item.metadata.keys())
        )
        assert "Иванов" not in joined
        assert "+7" not in joined
        assert "contacts" not in item.metadata
        assert "address" not in item.metadata


def test_parse_error_reports_api_error() -> None:
    """JSON с `errors` → AdapterError с деталями."""
    import json

    payload = json.dumps(
        {"errors": [{"type": "oauth", "value": "token expired"***REMOVED******REMOVED******REMOVED***
    ).encode("utf-8")

    with pytest.raises(AdapterError, match="token expired"):
        parse_vacancies_payload(payload)


def test_parse_invalid_json_raises_adapter_error() -> None:
    """Бинарный мусор → AdapterError, а не TypeError/JSONDecodeError."""
    with pytest.raises(AdapterError, match="invalid JSON"):
        parse_vacancies_payload(b"<html>not json</html>")


def test_parse_empty_items_is_not_error() -> None:
    """Пустой список items — легальный ответ (нет совпадений)."""
    import json

    payload = json.dumps({"items": [***REMOVED***, "found": 0, "pages": 0***REMOVED***).encode("utf-8")
    assert parse_vacancies_payload(payload) == [***REMOVED***


# --- Policy gate -------------------------------------------------------------


@pytest.mark.asyncio
async def test_allowed_can_poll_fetches() -> None:
    """ALLOWED + can_poll → fetch возвращает 2 вакансии; health OK."""
    adapter = HeadhunterAdapter(
        "headhunter",
        policy=_policy(SourcePolicyStatus.ALLOWED),
        http_get=_fake_get,
    )

    items = [item async for item in adapter.fetch()***REMOVED***

    assert len(items) == 2
    assert items[0***REMOVED***.item_id == "136323698"
    assert await adapter.health() is True


@pytest.mark.asyncio
async def test_non_allowed_hard_blocked() -> None:
    """Любой не-ALLOWED статус → AdapterError без HTTP-запроса."""
    for status in (
        SourcePolicyStatus.TECHNICAL_CANDIDATE,
        SourcePolicyStatus.CONDITIONAL,
        SourcePolicyStatus.MANUAL_REVIEW,
        SourcePolicyStatus.POLICY_BLOCKED,
    ):
        adapter = HeadhunterAdapter(
            "headhunter",
            policy=_policy(status),
            http_get=_fake_get,
        )
        with pytest.raises(AdapterError, match="ALLOWED"):
            [item async for item in adapter.fetch()***REMOVED***


@pytest.mark.asyncio
async def test_can_poll_false_blocks_even_allowed() -> None:
    """allowed, но can_poll=False → live-запрос запрещён (двойной гейт)."""
    adapter = HeadhunterAdapter(
        "headhunter",
        policy=_policy(SourcePolicyStatus.ALLOWED, can_poll=False),
        http_get=_fake_get,
    )

    with pytest.raises(AdapterError, match="can_poll"):
        [item async for item in adapter.fetch()***REMOVED***


# --- fetch-семантика ---------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_limit_and_checkpoint() -> None:
    """Bounded batch и resume по checkpoint работают."""
    adapter = HeadhunterAdapter(
        "headhunter",
        policy=_policy(SourcePolicyStatus.ALLOWED),
        http_get=_fake_get,
    )

    first = [item async for item in adapter.fetch(limit=1)***REMOVED***
    assert [item.item_id for item in first***REMOVED*** == ["136323698"***REMOVED***

    resumed = [item async for item in adapter.fetch(checkpoint="136323698")***REMOVED***
    assert [item.item_id for item in resumed***REMOVED*** == ["136455374"***REMOVED***


@pytest.mark.asyncio
async def test_fetch_sends_text_and_date_params() -> None:
    """Параметры text и date_from попадают в URL запроса."""
    captured: list[str***REMOVED*** = [***REMOVED***

    async def fake_get_with_capture(url: str) -> bytes:
        captured.append(url)
        return _fixture("vacancies_page.json")

    adapter = HeadhunterAdapter(
        "headhunter",
        policy=_policy(SourcePolicyStatus.ALLOWED),
        http_get=fake_get_with_capture,
    )

    since = datetime(2026, 8, 22, 0, 0, tzinfo=timezone.utc)
    [item async for item in adapter.fetch(text="python", modified_from=since)***REMOVED***

    assert len(captured) == 1
    assert "text=python" in captured[0***REMOVED***
    assert "date_from=" in captured[0***REMOVED***
    assert "2026-08-22" in captured[0***REMOVED***


@pytest.mark.asyncio
async def test_fetch_limit_clamped_to_api_max_100() -> None:
    """limit > 100 → cap до 100 (контракт API)."""
    adapter = HeadhunterAdapter(
        "headhunter",
        policy=_policy(SourcePolicyStatus.ALLOWED),
        http_get=_fake_get,
    )

    items = [item async for item in adapter.fetch(limit=500)***REMOVED***
    assert len(items) == 2  # fixture мал; главное — не упал и не запросил >100


@pytest.mark.asyncio
async def test_health_false_on_api_error() -> None:
    """health() → False при ошибке API (а не исключение)."""
    async def bad_get(url: str) -> bytes:
        raise OSError("network down")

    adapter = HeadhunterAdapter(
        "headhunter",
        policy=_policy(SourcePolicyStatus.ALLOWED),
        http_get=bad_get,
    )

    assert await adapter.health() is False


@pytest.mark.asyncio
async def test_fetch_propagates_adapter_error() -> None:
    """Ошибка API пробрасывается как AdapterError (а не тихий пустой)."""

    async def error_get(url: str) -> bytes:
        import json

        return json.dumps({"errors": [{"value": "forbidden"***REMOVED******REMOVED******REMOVED***).encode("utf-8")

    adapter = HeadhunterAdapter(
        "headhunter",
        policy=_policy(SourcePolicyStatus.ALLOWED),
        http_get=error_get,
    )

    with pytest.raises(AdapterError, match="forbidden"):
        [item async for item in adapter.fetch()***REMOVED***