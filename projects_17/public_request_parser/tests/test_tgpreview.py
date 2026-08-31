"""Hermetic tests P9 Telegram web-preview fixture adapter."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.domain import AdapterError, SourceItem, SourcePolicy, SourcePolicyStatus
from app.rss_atom import normalize_source_item
from app.tgpreview import TelegramPreviewParser, TelegramWebPreviewAdapter

FIXTURES = Path(__file__).parents[1] / "fixtures"
NOW = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)


def read_fixture() -> str:
    return (FIXTURES / "telegram/sample_channel.html").read_text(encoding="utf-8")


def test_parser_extracts_items_without_author_fields() -> None:
    """3 ссылки → 3 SourceItem; авторские поля не извлекаются."""
    parser = TelegramPreviewParser("tg-fixture", base_url="https://t.me/s/demo_channel")
    items = parser.parse(read_fixture())

    assert len(items) == 3
    assert items[0].item_id == "tg-0"
    assert items[0].canonical_url == "https://t.me/s/demo_channel/101"
    assert "python" in items[0].title.lower()
    assert items[0].metadata["feed_format"] == "telegram_web_preview"
    assert items[0].metadata["channel"] == "demo_channel"
    assert "author" not in str(items[0]).lower()


def test_parser_skips_non_http_links() -> None:
    """Ссылки без http(s) пропускаются."""
    parser = TelegramPreviewParser("tg-fixture", base_url="https://t.me/s/demo_channel")
    items = parser.parse('<a href="javascript:void(0)">x</a><a href="tg://open">y</a>')

    assert items == ()


@pytest.mark.asyncio
async def test_adapter_refuses_allowed_policy() -> None:
    """Fixture-адаптер не может стать allowed live транспортом."""
    policy = SourcePolicy(
        source_id="tg-live",
        status=SourcePolicyStatus.ALLOWED,
        access_mode="telegram_web_preview",
        endpoint="https://t.me/s/demo_channel",
        checked_at=NOW,
        evidence_urls=("https://example.test/terms",),
        can_poll=True,
    )

    with pytest.raises(AdapterError, match="cannot be used as allowed live transport"):
        adapter = TelegramWebPreviewAdapter("tg-live", read_fixture(), policy=policy)
        [item async for item in adapter.fetch()]


@pytest.mark.asyncio
async def test_adapter_bounded_fetch_and_checkpoint() -> None:
    """Fetch ограничен limit и умеет resume по checkpoint."""
    adapter = TelegramWebPreviewAdapter(
        "tg-fixture", read_fixture(), base_url="https://t.me/s/demo_channel"
    )

    first = [item async for item in adapter.fetch(limit=1)]
    assert [item.item_id for item in first] == ["tg-0"]

    resumed = [item async for item in adapter.fetch(checkpoint="tg-0", limit=3)]
    assert [item.item_id for item in resumed] == ["tg-1", "tg-2"]
    assert await adapter.health() is True


def test_items_normalize_to_publication_without_author() -> None:
    """SourceItem → Publication: контрактная граница, авторских полей нет."""
    parser = TelegramPreviewParser("tg-fixture", base_url="https://t.me/s/demo_channel")
    item = parser.parse(read_fixture())[0]

    publication = normalize_source_item("tg-fixture", item, fetched_at=NOW)

    assert publication.item_key == "tg-fixture:tg-0"
    assert publication.canonical_url == "https://t.me/s/demo_channel/101"
    assert "author" not in publication.__dataclass_fields__


def test_policy_blocked_status_is_allowed_for_fixture() -> None:
    """POLICY_BLOCKED/None допустимы для fixture-адаптера (live остаётся закрыт)."""
    blocked = SourcePolicy(
        source_id="tg-fixture",
        status=SourcePolicyStatus.POLICY_BLOCKED,
        access_mode="telegram_web_preview",
        endpoint="https://t.me/s/demo_channel",
        checked_at=NOW,
    )
    adapter = TelegramWebPreviewAdapter("tg-fixture", read_fixture(), policy=blocked)
    assert adapter.source_id == "tg-fixture"