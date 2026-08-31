"""Hermetic tests P7 Telegram delivery contract."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.domain import (
    ContractValidationError,
    DeliveryAttempt,
    DeliveryStatus,
    MatchDecision,
    MatchOutcome,
    Publication,
    SearchProfile,
)
from app.delivery import (
    DeliveryTransportError,
    TelegramDelivery,
    delivery_key_for,
    render_card,
)
from app.storage import SqliteStorage

NOW = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)


def make_publication(
    *,
    item_id: str = "item-1",
    title: str = "Need a <python> backend",
    summary: str = "Looking for & help",
) -> Publication:
    """Публикация с HTML-опасными символами для escape-тестов."""
    return Publication(
        source_id="fixture-source",
        item_id=item_id,
        canonical_url="https://example.test/items/1",
        title=title,
        summary=summary,
        published_at=NOW,
        fetched_at=NOW,
        metadata={"categories": "python,web"},
    )


def make_decision(
    *,
    profile_id: str = "operator",
    profile_version: int = 1,
) -> MatchDecision:
    """ACCEPT-decision с объяснением."""
    return MatchDecision(
        publication_key="fixture-source:item-1",
        profile_id=profile_id,
        profile_version=profile_version,
        outcome=MatchOutcome.ACCEPT,
        score=0.9,
        matched_terms=("python",),
        reasons=("required term matched: python",),
        decided_at=NOW,
    )


class FakeTransport:
    """Протокол-транспорт: записывает вызовы, умеет падать по команде."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []
        self.fail_next = False

    async def send(
        self,
        *,
        chat_id: str,
        text: str,
        disable_web_page_preview: bool = True,
    ) -> str:
        if self.fail_next:
            self.fail_next = False
            raise DeliveryTransportError("rate_limited")
        self.sent.append((chat_id, text))
        return f"msg-{len(self.sent)}"


@pytest.fixture()
def storage(tmp_path: Path) -> Iterator[SqliteStorage]:
    db = SqliteStorage(tmp_path / "delivery.db")
    yield db
    db.close()


def test_render_card_escapes_html_and_builds_link() -> None:
    """Карточка экранирует title/summary/categories, ссылка — источник."""
    card = render_card(
        make_publication(),
        make_decision(),
        score_label="0.90",
    )

    assert "&lt;python&gt;" in card.text
    assert "Looking for &amp; help" in card.text
    assert '"https://example.test/items/1"' in card.text
    assert "Категории: python, web" in card.text
    assert "author" not in card.text.lower()


def test_render_card_shows_apply_link_when_present() -> None:
    """Apply-ссылка площадки (jobseek) рендерится как кнопка «Откликнуться»."""
    publication = make_publication()
    # подменим metadata: добавим официальный apply_url
    from dataclasses import place

    publication = replace(
        publication,
        metadata={**publication.metadata, "apply_url": "https://hh.ru/applicant/vacancy_response/123"},
    )

    card = render_card(publication, make_decision(), score_label="0.90")

    assert "Откликнуться" in card.text
    assert "https://hh.ru/applicant/vacancy_response/123" in card.text


def test_delivery_key_is_owner_scoped_and_versioned() -> None:
    """Ключ уникален по owner, публикации и версии профиля."""
    publication = make_publication()
    decision = make_decision()

    key = delivery_key_for(publication, decision, owner_scope="operator")

    assert key == "operator:fixture-source:item-1:p1"
    assert (
        delivery_key_for(publication, decision, owner_scope="other")
        != key
    )
    assert (
        delivery_key_for(publication, make_decision(profile_version=2), owner_scope="operator")
        != key
    )


@pytest.mark.asyncio
async def test_dry_run_skips_without_transport() -> None:
    """Dry-run рендерит карточку, но не отправляет → SKIPPED."""
    delivery = TelegramDelivery(dry_run=True)
    publication = make_publication()
    decision = make_decision()

    attempt = await delivery.deliver(publication, decision, owner_scope="operator")

    assert attempt.status is DeliveryStatus.SKIPPED
    assert attempt.provider_message_id is None
    assert delivery.transport is None


@pytest.mark.asyncio
async def test_transport_send_is_idempotent_by_key() -> None:
    """Повторная доставка того же ключа не создаёт второй вызов транспорта."""
    transport = FakeTransport()
    delivery = TelegramDelivery(transport=transport)
    publication = make_publication()
    decision = make_decision()

    first = await delivery.deliver(publication, decision, owner_scope="operator")
    second = await delivery.deliver(publication, decision, owner_scope="operator")

    assert first.status is DeliveryStatus.SENT
    assert second.status is DeliveryStatus.SENT
    assert second.provider_message_id == first.provider_message_id
    assert len(transport.sent) == 1


@pytest.mark.asyncio
async def test_transport_failure_records_failed_then_retry_sends() -> None:
    """FAILED сохраняется с error_code; retry после устранения сбоя — SENT."""
    transport = FakeTransport()
    delivery = TelegramDelivery(transport=transport)
    publication = make_publication()
    decision = make_decision()

    transport.fail_next = True
    failed = await delivery.deliver(publication, decision, owner_scope="operator")

    assert failed.status is DeliveryStatus.FAILED
    assert failed.error_code == "rate_limited"

    retried = await delivery.deliver(publication, decision, owner_scope="operator")
    assert retried.status is DeliveryStatus.SENT
    assert retried.provider_message_id is not None
    assert len(transport.sent) == 1


@pytest.mark.asyncio
async def test_owner_scope_mismatch_rejects() -> None:
    """Переданный owner обязан совпадать с владельцем decision."""
    delivery = TelegramDelivery()
    publication = make_publication()
    decision = make_decision(profile_id="operator-a")

    with pytest.raises(ContractValidationError, match="owner_scope"):
        await delivery.deliver(publication, decision, owner_scope="operator-b")


def test_empty_owner_scope_rejected_at_construction() -> None:
    """Пустой default_owner_scope запрещён на уровне конструктора."""
    with pytest.raises(ContractValidationError, match="owner_scope"):
        TelegramDelivery(default_owner_scope="  ")


def test_escaped_title_never_contains_raw_html() -> None:
    """HTML-escape обязателен: титул с тегами не попадает в карточку как разметка."""
    publication = make_publication(title="<script>alert(1)</script>")
    card = render_card(publication, make_decision(), score_label="0.90")

    assert "<script>" not in card.text
    assert "&lt;script&gt;" in card.text


@pytest.mark.asyncio
async def test_sqlite_persists_sent_attempt(storage: SqliteStorage) -> None:
    """SENT-попытка сохраняется в storage и отдаёт повторную отправку."""
    transport = FakeTransport()
    # Публикация должна существовать в БД (FK на delivery_attempts).
    storage.save_publication(make_publication())
    delivery = TelegramDelivery(transport=transport, storage=storage)
    publication = make_publication()
    decision = make_decision()

    first = await delivery.deliver(publication, decision, owner_scope="operator")

    assert first.status is DeliveryStatus.SENT
    assert storage.get_delivery_attempt(first.delivery_key) is not None

    # Пересоздаём delivery с тем же storage и транспортом: повторного send нет.
    fresh = TelegramDelivery(transport=transport, storage=storage)
    second = await fresh.deliver(publication, decision, owner_scope="operator")

    assert second.status is DeliveryStatus.SENT
    assert second.provider_message_id == first.provider_message_id
    assert len(transport.sent) == 1


@pytest.mark.asyncio
async def test_html_escape_is_used_not_markdown() -> None:
    """Карточка всегда HTML; никаких markdown-маркеров из контента."""
    publication = make_publication(title="Ищем *курс* по python")
    card = render_card(publication, make_decision(), score_label="0.9")

    assert "&quot;" not in card.text  # quote=False для атрибутов не требуется
    assert "*курс*" in card.text  # звёздочки остаются как текст (не markdown)


def test_card_never_contains_author_fields() -> None:
    """Контракт: в карточке нет полей автора (privacy)."""
    card = render_card(make_publication(), make_decision(), score_label="0.9")
    assert "author" not in card.text
    assert "email" not in card.text
    assert "phone" not in card.text