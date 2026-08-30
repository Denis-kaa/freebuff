"""Hermetic integration tests P4 → P5.

Полный offline vertical slice: RSS/Atom fixture → SourceItem → Publication →
dedup → RuleMatcher → explainable MatchDecision. Никаких сетевых вызовов;
профиль и фикстуры синтетические.
"""

from __future__ import annotations

from datetime import datetime, timezone
}

import pytest

from app.domain import MatchDecision, MatchOutcome, Publication, SearchProfile
from app.matcher import RuleMatcher
from app.rss_atom import (
    FixtureFeedAdapter,
    RSSAtomParser,
    deduplicate_publications,
    normalize_source_item,
)

FIXTURES = Path(__file__).parents[1] / "fixtures"
NOW = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)


def _parse_and_normalize(relative_path: str, source_id: str) -> tuple[Publication, ...]:
    """Parsing + normalization без сети (sync срез pipeline)."""
    result = RSSAtomParser(source_id).parse((FIXTURES / relative_path).read_bytes())
    return deduplicate_publications(
        normalize_source_item(source_id, item, fetched_at=NOW)
        for item in result.items
    )


def _python_profile() -> SearchProfile:
    """Профиль, релевантный ровно одному item RSS-фикстуры."""
    return SearchProfile(
        profile_id="profile-python",
        owner_scope="operator",
        version=3,
        service_name="Python разработка",
        required_terms=("python",),
        optional_terms=("backend",),
        intent_terms=("нужен", "ищу", "need", "looking"),
        excluded_terms=("курс",),
    )


def test_full_slice_rss_fixture_to_match_decisions() -> None:
    """RSS → Publication → MatchDecision: только релевантный item принимается."""
    publications = _parse_and_normalize("rss/sample_rss.xml", "rss-fixture")
    assert len(publications) == 2

    matcher = RuleMatcher(_python_profile())
    decisions = [matcher.match(p, decided_at=NOW) for p in publications]

    accepted = [d for d in decisions if d.outcome is MatchOutcome.ACCEPT]
    assert [d.publication_key for d in accepted] == ["rss-fixture:request-1"]
    decision = accepted[0]
    assert decision.score >= 0.8
    assert "required term matched: python" in decision.reasons
    assert any(r.startswith("intent term matched") for r in decision.reasons)
    assert decision.profile_version == 3
    # Explenability: snapshot правил профиля в decision.
    assert decision.rules_snapshot["required_terms"] == ("python",)

    rejected = [d for d in decisions if d.outcome is MatchOutcome.REJECT]
    assert len(rejected) == 1
    assert rejected[0].publication_key == "rss-fixture:https://example.test/requests/2"


def test_atom_fixture_matches_different_profile_and_skips_missing_link() -> None:
    """Atom → другой профиль: copywriter принимается, untimed item остаётся SourceItem-пропуском."""
    result = RSSAtomParser("atom-fixture").parse((FIXTURES / "atom/sample_atom.xml").read_bytes())
    publications = deduplicate_publications(
        normalize_source_item("atom-fixture", item, fetched_at=NOW)
        for item in result.items
    )
    # Оба entry имеют абсолютные https-ссылки; request-4 без даты проходит
    # с invalid_date warning, но остаётся в pipeline (дата необязательна).
    assert len(publications) == 2
    assert publications[0].item_key == "atom-fixture:tag:example.test,2026:request-3"
    assert publications[1].published_at is None

    profile = SearchProfile(
        profile_id="profile-copy",
        owner_scope="operator",
        version=1,
        service_name="Копирайтинг",
        required_terms=("copywriter",),
        intent_terms=("нужен", "need"),
    )
    matcher = RuleMatcher(profile)
    decision = matcher.match(publications[0], decided_at=NOW)
    other = matcher.match(publications[1], decided_at=NOW)

    assert decision.outcome is MatchOutcome.ACCEPT
    assert decision.matched_terms == ("copywriter",)
    assert "required term matched: copywriter" in decision.reasons
    assert other.outcome is MatchOutcome.REJECT
    assert "required term missing: copywriter" in other.reasons


@pytest.mark.asyncio
async def test_fixture_adapter_async_pipeline_is_idempotent() -> None:
    """Async FixtureFeedAdapter → normalize → dedup → match: повторный прогон не создаёт дублей."""
    adapter = FixtureFeedAdapter("rss-fixture", (FIXTURES / "rss/sample_rss.xml").read_bytes())

    async def run() -> tuple[tuple[Publication, ...], tuple[MatchDecision, ...]]:
        items = [item async for item in adapter.fetch()]
        publications = deduplicate_publications(
            normalize_source_item("rss-fixture", item, fetched_at=NOW)
            for item in items
        )
        decisions = tuple(
            RuleMatcher(_python_profile()).match(p, decided_at=NOW) for p in publications
        )
        return publications, decisions

    first_publications, first_decisions = await run()
    second_publications, second_decisions = await run()

    assert len(first_publications) == 2
    assert len(second_publications) == 2
    assert [p.item_key for p in first_publications] == [p.item_key for p in second_publications]
    assert first_decisions == second_decisions
    assert sum(1 for d in first_decisions if d.outcome is MatchOutcome.ACCEPT) == 1


def test_exclusion_rule_filters_out_noise_in_pipeline() -> None:
    """Excluded term защищает pipeline от «курс/python», даже если required matched."""
    profile = _python_profile()
    noise = deduplicate_publications(
        (
            Publication(
                source_id="rss-fixture",
                item_id="noise-1",
                canonical_url="https://example.test/noise/1",
                title="Нужен python, но курс для начинающих",
                fetched_at=NOW,
            ),
        )
    )

    decision = RuleMatcher(profile).match(noise[0], decided_at=NOW)

    assert decision.outcome is MatchOutcome.REJECT
    assert decision.score == 0.0
    assert "excluded term matched: курс" in decision.reasons