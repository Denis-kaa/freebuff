"""Hermetic tests RSS/Atom engine P4."""

from __future__ import annotations

from datetime import datetime, timezone
***REMOVED***

import pytest

from app.domain import AdapterError, SourceItem, SourcePolicy, SourcePolicyStatus
from app.rss_atom import (
    FixtureFeedAdapter,
    InMemoryCheckpointStore,
    RSSAtomParser,
    deduplicate_publications,
    normalize_source_item,
)


FIXTURES = Path(__file__).parents[1***REMOVED*** / "fixtures"
NOW = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)


def read_fixture(relative_path: str) -> bytes:
    """Загрузить synthetic fixture из project-local каталога."""
    return (FIXTURES / relative_path).read_bytes()


def test_rss_parser_normalizes_items_and_categories() -> None:
    """RSS 2.x fields become stable SourceItems."""
    result = RSSAtomParser("rss-fixture").parse(read_fixture("rss/sample_rss.xml"))

    assert result.format == "rss"
    assert len(result.items) == 2
    assert result.items[0***REMOVED***.item_id == "request-1"
    assert result.items[0***REMOVED***.canonical_url == "https://example.test/requests/1"
    assert result.items[0***REMOVED***.published_at == datetime(2026, 8, 23, 10, 0, tzinfo=timezone.utc)
    assert result.items[0***REMOVED***.metadata["categories"***REMOVED*** == "python"
    assert result.warnings == ()


def test_atom_parser_handles_namespaces_and_invalid_date_warning() -> None:
    """Atom namespace and incomplete optional date must not break the feed."""
    result = RSSAtomParser("atom-fixture").parse(read_fixture("atom/sample_atom.xml"))

    assert result.format == "atom"
    assert len(result.items) == 2
    assert result.items[0***REMOVED***.item_id == "tag:example.test,2026:request-3"
    assert result.items[0***REMOVED***.canonical_url == "https://example.test/requests/3"
    assert result.items[0***REMOVED***.content == "Need a short product description."
    assert result.items[1***REMOVED***.published_at is None
    assert {warning.code for warning in result.warnings***REMOVED*** == {"invalid_date"***REMOVED***


def test_parser_skips_items_without_url_and_rejects_malformed_xml() -> None:
    """Неполный item пропускается, повреждённый документ считается adapter error."""
    payload = """<rss version=\"2.0\"><channel><item><title>No URL</title></item></channel></rss>"""
    result = RSSAtomParser("partial").parse(payload)
    assert result.items == ()
    assert result.warnings[0***REMOVED***.code == "missing_url"

    with pytest.raises(AdapterError, match="invalid RSS/Atom XML"):
        RSSAtomParser("broken").parse(b"<rss>")


def test_normalization_caps_temporary_content() -> None:
    """Normalization honours bounded temporary text storage."""
    item = RSSAtomParser("rss-fixture").parse(read_fixture("rss/sample_rss.xml")).items[0***REMOVED***

    publication = normalize_source_item("rss-fixture", item, fetched_at=NOW, max_text_chars=12)

    assert publication.item_key == "rss-fixture:request-1"
    assert publication.content == "Looking for "
    assert publication.fetched_at == NOW


def test_deduplication_keeps_first_item_by_key_and_url() -> None:
    """Повторная публикация не создаёт второй normalized record."""
    items = RSSAtomParser("rss-fixture").parse(read_fixture("rss/sample_rss.xml")).items
    first = normalize_source_item("rss-fixture", items[0***REMOVED***, fetched_at=NOW)
    same_key = normalize_source_item("rss-fixture", items[0***REMOVED***, fetched_at=NOW)
    same_url = normalize_source_item(
        "rss-fixture",
        SourceItem(
            item_id="different-id",
            canonical_url=items[0***REMOVED***.canonical_url,
            title="Updated title",
        ),
        fetched_at=NOW,
    )
    unique = deduplicate_publications((first, same_key, same_url))

    assert len(unique) == 1
    assert unique[0***REMOVED***.title == first.title


@pytest.mark.asyncio
async def test_fixture_adapter_resumes_after_checkpoint() -> None:
    """Checkpoint исключает уже подтверждённые items и сохраняется идемпотентно."""
    adapter = FixtureFeedAdapter("rss-fixture", read_fixture("rss/sample_rss.xml"))
    checkpoint = InMemoryCheckpointStore()

    first_batch = [item async for item in adapter.fetch(limit=1)***REMOVED***
    assert [item.item_id for item in first_batch***REMOVED*** == ["request-1"***REMOVED***
    await checkpoint.commit("rss-fixture", first_batch[-1***REMOVED***.item_id)

    resumed = [
        item
        async for item in adapter.fetch(
            checkpoint=await checkpoint.get("rss-fixture"),
        )
    ***REMOVED***
    assert [item.item_id for item in resumed***REMOVED*** == ["https://example.test/requests/2"***REMOVED***
    await checkpoint.commit("rss-fixture", first_batch[-1***REMOVED***.item_id)
    assert await checkpoint.get("rss-fixture") == "request-1"


@pytest.mark.asyncio
async def test_fixture_adapter_is_not_live_allowed_transport() -> None:
    """Fixture adapter cannot silently become an approved live transport."""
    policy = SourcePolicy(
        source_id="approved",
        status=SourcePolicyStatus.ALLOWED,
        access_mode="publisher_feed",
        endpoint="https://example.test/feed.xml",
        checked_at=NOW,
        evidence_urls=("https://example.test/terms",),
        can_poll=True,
    )
    adapter = FixtureFeedAdapter(
        "approved",
        read_fixture("rss/sample_rss.xml"),
        policy=policy,
    )

    with pytest.raises(AdapterError, match="live allowed transport"):
        [item async for item in adapter.fetch()***REMOVED***


@pytest.mark.asyncio
async def test_fixture_adapter_health_is_local_and_false_for_broken_payload() -> None:
    """Health описывает parseability fixture, не сетевую доступность."""
    healthy = FixtureFeedAdapter("healthy", read_fixture("rss/sample_rss.xml"))
    broken = FixtureFeedAdapter("broken", b"<rss>")

    assert await healthy.health() is True
    assert await broken.health() is False
