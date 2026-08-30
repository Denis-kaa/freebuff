"""Hermetic tests для доменных контрактов P3."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.domain import (
    ContractValidationError,
    DeliveryAttempt,
    DeliveryStatus,
    MatchDecision,
    MatchOutcome,
    Publication,
    RetentionPolicy,
    SearchProfile,
    SourcePolicy,
    SourcePolicyStatus,
)

NOW = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)


def make_publication() -> Publication:
    """Создать минимальную валидную публикацию без авторских полей."""
    return Publication(
        source_id="fixture-source",
        item_id="item-42",
        canonical_url="https://example.test/items/42",
        title="Need Python service",
        published_at=NOW,
        content="Full text is temporary",
        fetched_at=NOW,
    )


def test_publication_has_stable_source_scoped_key() -> None:
    """Dedup key должен различать одинаковые item id у разных источников."""
    publication = make_publication()

    assert publication.item_key == "fixture-source:item-42"
    assert "author" not in publication.__dataclass_fields__


def test_publication_rejects_naive_datetime() -> None:
    """Неявная timezone приводит к неоднозначному TTL и запрещается."""
    with pytest.raises(ContractValidationError, match="timezone-aware"):
        Publication(
            source_id="source",
            item_id="item",
            canonical_url="https://example.test/item",
            title="Title",
            fetched_at=datetime(2026, 8, 23),
        )


def test_profile_builds_reproducible_rules_snapshot() -> None:
    """Decision должен ссылаться на неизменяемый снимок правил профиля."""
    profile = SearchProfile(
        profile_id="profile-1",
        owner_scope="operator",
        version=2,
        service_name="Python",
        required_terms=("python",),
        optional_terms=("backend",),
        synonyms=(("python", ("py", "django")),),
        excluded_terms=("курс",),
        intent_terms=("нужен",),
    )

    assert profile.rules_snapshot["required_terms"] == ("python",)
    assert "django" in profile.all_terms
    assert profile.version == 2


def test_profile_rejects_inverted_thresholds() -> None:
    """Порог pending не может быть выше accept."""
    with pytest.raises(ContractValidationError, match="thresholds"):
        SearchProfile(
            profile_id="profile-1",
            owner_scope="operator",
            version=1,
            service_name="Python",
            accept_threshold=0.4,
            pending_threshold=0.5,
        )


def test_match_decision_requires_explanation_for_accept() -> None:
    """Принятое совпадение обязано быть explainable."""
    with pytest.raises(ContractValidationError, match="reasons"):
        MatchDecision(
            publication_key="source:item",
            profile_id="profile-1",
            profile_version=1,
            outcome=MatchOutcome.ACCEPT,
            score=0.9,
        )


def test_match_decision_keeps_profile_version_and_reason() -> None:
    """Decision хранит provenance профиля и matched terms."""
    decision = MatchDecision(
        publication_key=make_publication().item_key,
        profile_id="profile-1",
        profile_version=2,
        outcome=MatchOutcome.ACCEPT,
        score=0.9,
        matched_terms=("python",),
        reasons=("required term matched",),
        rules_snapshot={"required_terms": ("python",)},
        decided_at=NOW,
    )

    assert decision.profile_version == 2
    assert decision.matched_terms == ("python",)


def test_retention_never_relaxes_source_limit() -> None:
    """Пользовательская политика не может превысить source maximum TTL."""
    policy = RetentionPolicy(text_ttl=timedelta(days=30), max_text_chars=1_000)

    assert policy.effective_text_ttl(timedelta(days=7)) == timedelta(days=7)
    assert policy.effective_text_ttl(None) == timedelta(days=30)


def test_retention_rejects_ttl_when_full_text_disabled() -> None:
    """Для policy без полного текста TTL текста не должен маскировать хранение."""
    with pytest.raises(ContractValidationError, match="text_ttl"):
        RetentionPolicy(text_ttl=timedelta(days=1), allow_full_text=False)


def test_only_allowed_policy_can_poll_or_be_user_facing() -> None:
    """Technical candidate не может случайно стать live source."""
    with pytest.raises(ContractValidationError, match="allowed"):
        SourcePolicy(
            source_id="fixture-source",
            status=SourcePolicyStatus.TECHNICAL_CANDIDATE,
            access_mode="publisher_feed",
            endpoint="https://example.test/feed.xml",
            checked_at=NOW,
            can_poll=True,
        )

    allowed = SourcePolicy(
        source_id="approved-source",
        status=SourcePolicyStatus.ALLOWED,
        access_mode="publisher_feed",
        endpoint="https://example.test/feed.xml",
        checked_at=NOW,
        evidence_urls=("https://example.test/terms",),
        can_poll=True,
        user_facing=True,
    )
    assert allowed.can_poll is True


def test_delivery_attempt_requires_provider_evidence() -> None:
    """Статус доставки должен быть согласован с доказательством результата."""
    with pytest.raises(ContractValidationError, match="provider_message_id"):
        DeliveryAttempt(delivery_key="p:d", status=DeliveryStatus.SENT)

    sent = DeliveryAttempt(
        delivery_key="p:d",
        status=DeliveryStatus.SENT,
        provider_message_id="telegram-message-1",
        attempted_at=NOW,
    )
    assert sent.status is DeliveryStatus.SENT
