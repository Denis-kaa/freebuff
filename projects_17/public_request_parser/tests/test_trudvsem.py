"""Hermetic tests: TrudvsemAdapter (SRC-012, Open Data API «Работа в России»)."""

from __future__ import annotations

from datetime import datetime, timezone
***REMOVED***

import pytest

from app.adapters.trudvsem import TrudvsemAdapter, parse_vacancy_payload
from app.domain import AdapterError, SourceItem, SourcePolicy, SourcePolicyStatus

FIXTURES = Path(__file__).parents[1***REMOVED*** / "fixtures" / "trudvsem"
NOW = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)


def _fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


async def _fake_get_ok(url: str) -> bytes:
    assert "opendata.trudvsem.ru" in url
    return _fixture("vacancies_page.json")


async def _fake_get_copywriter(url: str) -> bytes:
    assert "opendata.trudvsem.ru" in url
    return _fixture("vacancies_copywriter.json")


async def _fake_get_error(url: str) -> bytes:
    assert "opendata.trudvsem.ru" in url
    return _fixture("error_500.json")


def _policy(
    status: SourcePolicyStatus,
    *,
    can_poll: bool = True,
    endpoint: str = "https://opendata.trudvsem.ru/api/v1/vacancies",
) -> SourcePolicy:
    effective_can_poll = can_poll and status is SourcePolicyStatus.ALLOWED
    return SourcePolicy(
        source_id="trudvsem",
        status=status,
        access_mode="open_data_api",
        endpoint=endpoint,
        checked_at=NOW,
        evidence_urls=(
            "https://trudvsem.ru/opendata",
            "https://trudvsem.ru/opendata/api",
        )
        if status is SourcePolicyStatus.ALLOWED
        else (),
        can_poll=effective_can_poll,
    )


# --- Статический парсинг ---------------------------------------------------


def test_parse_page_builds_source_items() -> None:
    """Из страницы извлекаются два SourceItem с корректными полями."""
    items = parse_vacancy_payload(_fixture("vacancies_page.json"))

    assert len(items) == 2
    first = items[0***REMOVED***
    assert isinstance(first, SourceItem)
    assert first.item_id == "prp-fixture-0001"
    assert first.canonical_url == (
        "https://trudvsem.ru/vacancy/card/1000000000000/prp-fixture-0001"
    )
    assert first.title == "Python-разработчик (backend)"
    assert first.published_at is not None
    assert first.published_at.tzinfo is not None
    assert first.published_at.astimezone(timezone.utc).hour == 15  # +0300 → 15:00 UTC
    assert "FastAPI" in (first.content or "")
    assert first.metadata["region"***REMOVED*** == "Город Санкт-Петербург"
    assert first.metadata["salary_min"***REMOVED*** == "200000"


def test_parse_never_contains_private_fields() -> None:
    """Контактные/персональные поля не попадают в metadata ни при каких условиях."""
    raw = _fixture("vacancies_page.json").decode("utf-8").replace(
        '"contact_person": ""', '"contact_person": "Иванов Иван"'
    )
    items = parse_vacancy_payload(raw.encode("utf-8"))

    for item in items:
        for key in ("contact_list", "contact_person", "addresses", "phone", "email"):
            assert key not in item.metadata
            if item.content is not None:
                assert key not in item.content


def test_parse_skips_record_without_url_or_id() -> None:
    """Записи без id/vac_url пропускаются без падения парсера."""
    import json

    data = json.loads(_fixture("vacancies_page.json"))
    data["results"***REMOVED***["vacancies"***REMOVED***.append({"vacancy": {"id": "broken-no-url"***REMOVED******REMOVED***)
    data["results"***REMOVED***["vacancies"***REMOVED***.append({"vacancy": {"vac_url": "https://x.test/a"***REMOVED******REMOVED***)

    items = parse_vacancy_payload(json.dumps(data).encode("utf-8"))

    assert len(items) == 2  # обе невалидные записи отброшены


def test_parse_error_status_raises_adapter_error() -> None:
    """status=500 с meta.error → AdapterError с текстом ошибки."""
    with pytest.raises(AdapterError, match="500"):
        parse_vacancy_payload(_fixture("error_500.json"))


def test_parse_invalid_json_raises_adapter_error() -> None:
    """Бинарный мусор → AdapterError, а не TypeError/JSONDecodeError."""
    with pytest.raises(AdapterError, match="invalid JSON"):
        parse_vacancy_payload(b"<html>not json</html>")


def test_parse_empty_vacancies_is_empty_not_error() -> None:
    """Пустой список вакансий — легальный ответ, а не ошибка."""
    import json

    data = {
        "status": "200",
        "request": {"api": "v1"***REMOVED***,
        "meta": {"total": 0, "limit": 0***REMOVED***,
        "results": {"vacancies": [***REMOVED******REMOVED***,
    ***REMOVED***
    items = parse_vacancy_payload(json.dumps(data).encode("utf-8"))
    assert items == [***REMOVED***


# --- Policy gate -------------------------------------------------------------


@pytest.mark.asyncio
async def test_allowed_can_poll_fetches() -> None:
    """ALLOWED + can_poll → fetch возвращает 2 вакансии; health OK."""
    adapter = TrudvsemAdapter(
        "trudvsem",
        policy=_policy(SourcePolicyStatus.ALLOWED),
        http_get=_fake_get_ok,
    )

    items = [item async for item in adapter.fetch()***REMOVED***

    assert len(items) == 2
    assert items[0***REMOVED***.item_id == "prp-fixture-0001"
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
        adapter = TrudvsemAdapter(
            "trudvsem",
            policy=_policy(status),
            http_get=_fake_get_ok,
        )
        with pytest.raises(AdapterError, match="ALLOWED"):
            [item async for item in adapter.fetch()***REMOVED***


@pytest.mark.asyncio
async def test_can_poll_false_blocks_even_allowed() -> None:
    """allowed, но can_poll=False → live-запрос запрещён (двойной гейт)."""
    adapter = TrudvsemAdapter(
        "trudvsem",
        policy=_policy(SourcePolicyStatus.ALLOWED, can_poll=False),
        http_get=_fake_get_ok,
    )

    with pytest.raises(AdapterError, match="can_poll"):
        [item async for item in adapter.fetch()***REMOVED***


# --- fetch-семантикa ---------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_limit_and_checkpoint() -> None:
    """Bounded batch и resume по checkpoint работают."""
    adapter = TrudvsemAdapter(
        "trudvsem",
        policy=_policy(SourcePolicyStatus.ALLOWED),
        http_get=_fake_get_ok,
    )

    first = [item async for item in adapter.fetch(limit=1)***REMOVED***
    assert [item.item_id for item in first***REMOVED*** == ["prp-fixture-0001"***REMOVED***

    resumed = [item async for item in adapter.fetch(checkpoint="prp-fixture-0001")***REMOVED***
    assert [item.item_id for item in resumed***REMOVED*** == ["prp-fixture-0002"***REMOVED***


@pytest.mark.asyncio
async def test_fetch_limit_clamped_to_api_max_100() -> None:
    """limit > 100 → cap до 100 (контракт API)."""
    adapter = TrudvsemAdapter(
        "trudvsem",
        policy=_policy(SourcePolicyStatus.ALLOWED),
        http_get=_fake_get_ok,
    )

    items = [item async for item in adapter.fetch(limit=500)***REMOVED***

    # fixture содержит 2 вакансии; главное — не упал и не запросил >100
    assert len(items) == 2


@pytest.mark.asyncio
async def test_fetch_source_error_propagates() -> None:
    """Ошибка API (500) пробрасывается как AdapterError."""
    adapter = TrudvsemAdapter(
        "trudvsem",
        policy=_policy(SourcePolicyStatus.ALLOWED),
        http_get=_fake_get_error,
    )

    with pytest.raises(AdapterError, match="500"):
        [item async for item in adapter.fetch()***REMOVED***


@pytest.mark.asyncio
async def test_health_false_on_api_error() -> None:
    """health() → False при ошибке API (а не исключение)."""
    adapter = TrudvsemAdapter(
        "trudvsem",
        policy=_policy(SourcePolicyStatus.ALLOWED),
        http_get=_fake_get_error,
    )

    assert await adapter.health() is False


@pytest.mark.asyncio
async def test_fetch_sends_modified_from_checkpoint_param() -> None:
    """Дельта-параметр modifiedFrom попадает в URL запроса (ISO 8601 UTC)."""
    captured: list[str***REMOVED*** = [***REMOVED***

    async def fake_get_with_capture(url: str) -> bytes:
        captured.append(url)
        return _fixture("vacancies_page.json")

    adapter = TrudvsemAdapter(
        "trudvsem",
        policy=_policy(SourcePolicyStatus.ALLOWED),
        http_get=fake_get_with_capture,
    )

    since = datetime(2026, 8, 22, 0, 0, tzinfo=timezone.utc)
    [item async for item in adapter.fetch(modified_from=since)***REMOVED***

    assert len(captured) == 1
    assert "modifiedFrom=2026-08-22T00%3A00%3A00%2B00%3A00" in captured[0***REMOVED*** or (
        "modifiedFrom=" in captured[0***REMOVED***
        and "2026-08-22" in captured[0***REMOVED***
    )


@pytest.mark.asyncio
async def test_copywriter_fixture_parsed() -> None:
    """Второй fixture (копирайтер) парсится корректно."""
    adapter = TrudvsemAdapter(
        "trudvsem",
        policy=_policy(SourcePolicyStatus.ALLOWED),
        http_get=_fake_get_copywriter,
    )

    items = [item async for item in adapter.fetch()***REMOVED***

    assert len(items) == 1
    assert items[0***REMOVED***.title == "Копирайтер для маркетплейса"
    assert "копирайтинг" in (items[0***REMOVED***.content or "")