"""Hermetic tests P12 policy-gated HTTP feed transport."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.adapters import HttpFeedAdapter
from app.domain import AdapterError, SourcePolicy, SourcePolicyStatus

FIXTURES = Path(__file__).parents[1] / "fixtures"
NOW = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)


def _payload() -> bytes:
    return (FIXTURES / "rss/sample_rss.xml").read_bytes()


async def _fake_get(url: str) -> bytes:
    """Не выполняет сеть; возвращает fixture body."""
    assert url == "https://example.test/feed.xml"
    return _payload()


def _policy(status: SourcePolicyStatus, *, can_poll: bool = True) -> SourcePolicy:
    # Порт SourcePolicy: can_poll допустим только для ALLOWED.
    effective_can_poll = can_poll and status is SourcePolicyStatus.ALLOWED
    return SourcePolicy(
        source_id="http-source",
        status=status,
        access_mode="publisher_feed",
        endpoint="https://example.test/feed.xml",
        checked_at=NOW,
        evidence_urls=("https://example.test/terms",) if status is SourcePolicyStatus.ALLOWED else (),
        can_poll=effective_can_poll,
    )


@pytest.mark.asyncio
async def test_allowed_policy_can_fetch_items() -> None:
    """Allowed + can_poll → fetch возвращает items из ответа HTTP."""
    adapter = HttpFeedAdapter("http-source", policy=_policy(SourcePolicyStatus.ALLOWED), http_get=_fake_get)

    items = [item async for item in adapter.fetch()]

    assert len(items) == 2
    assert items[0].item_id == "request-1"
    assert await adapter.health() is True


@pytest.mark.asyncio
async def test_non_allowed_policy_is_hard_blocked() -> None:
    """technical_candidate/conditional/blocked → AdapterError без запроса."""
    for status in (
        SourcePolicyStatus.TECHNICAL_CANDIDATE,
        SourcePolicyStatus.CONDITIONAL,
        SourcePolicyStatus.MANUAL_REVIEW,
        SourcePolicyStatus.POLICY_BLOCKED,
    ):
        adapter = HttpFeedAdapter("http-source", policy=_policy(status), http_get=_fake_get)
        with pytest.raises(AdapterError, match="ALLOWED"):
            [item async for item in adapter.fetch()]


@pytest.mark.asyncio
async def test_can_poll_false_blocks_even_allowed() -> None:
    """allowed, но can_poll=False → live-запрос запрещён (двойной гейт)."""
    adapter = HttpFeedAdapter(
        "http-source",
        policy=_policy(SourcePolicyStatus.ALLOWED, can_poll=False),
        http_get=_fake_get,
    )

    with pytest.raises(AdapterError, match="can_poll"):
        [item async for item in adapter.fetch()]


@pytest.mark.asyncio
async def test_fetch_respects_limit_and_checkpoint() -> None:
    """Bounded batch и resume по checkpoint работают и для live-адаптера."""
    adapter = HttpFeedAdapter("http-source", policy=_policy(SourcePolicyStatus.ALLOWED), http_get=_fake_get)

    first = [item async for item in adapter.fetch(limit=1)]
    assert [item.item_id for item in first] == ["request-1"]

    resumed = [item async for item in adapter.fetch(checkpoint="request-1")]
    assert [item.item_id for item in resumed] == ["https://example.test/requests/2"]