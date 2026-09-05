"""E2E: весь конвейер с Telegram web-preview fixture и профилем.

adapter (tgpreview) → normalize → SQLite → matcher → dry-run delivery.
Проверяется полный путь: спрос принят, предложение отклонено intent-gate,
checkpoint идемпотентен, карточки dry-run.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
***REMOVED***

import pytest

from app.delivery import TelegramDelivery
from app.domain import MatchOutcome, SearchProfile, SourcePolicy, SourcePolicyStatus
from app.pipeline import run_offline_slice
from app.storage import SqliteCheckpointStore, SqliteStorage
from app.tgpreview import TelegramWebPreviewAdapter

FIXTURES = Path(__file__).parents[1***REMOVED*** / "fixtures"
NOW = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)


def read_tg_fixture() -> str:
    return (FIXTURES / "telegram/sample_channel.html").read_text(encoding="utf-8")


def tg_adapter() -> TelegramWebPreviewAdapter:
    """Fixture-адаптер с policy-blocked (live запрещён даже для теста)."""
    policy = SourcePolicy(
        source_id="tg-fixture",
        status=SourcePolicyStatus.POLICY_BLOCKED,
        access_mode="telegram_web_preview",
        endpoint="https://t.me/s/demo_channel",
        checked_at=NOW,
    )
    return TelegramWebPreviewAdapter(
        "tg-fixture",
        read_tg_fixture(),
        policy=policy,
        base_url="https://t.me/s/demo_channel",
    )


def python_profile() -> SearchProfile:
    """Профиль «Python разработчик»: совпадает ровно с одним сообщением."""
    return SearchProfile(
        profile_id="profile-python",
        owner_scope="operator",
        version=1,
        service_name="Python разработка",
        required_terms=("python",),
        intent_terms=("ищу", "нужен", "need", "looking"),
    )


def copywriter_profile() -> SearchProfile:
    """Профиль «Копирайтинг»: совпадает с третьим сообщением."""
    return SearchProfile(
        profile_id="profile-copy",
        owner_scope="operator",
        version=1,
        service_name="Копирайтинг",
        required_terms=("копирайтер",),
        intent_terms=("нужен",),
    )


@pytest.fixture()
def storage(tmp_path: Path) -> Iterator[SqliteStorage***REMOVED***:
    db = SqliteStorage(tmp_path / "e2e_tg.db")
    yield db
    db.close()


@pytest.mark.asyncio
async def test_e2e_tg_fixture_python_profile(storage: SqliteStorage) -> None:
    """Сквозной путь: 3 сообщения → 1 accept (спрос), 2 reject, dry-run delivery."""
    adapter = tg_adapter()
    checkpoint = SqliteCheckpointStore(storage)
    delivery = TelegramDelivery(storage=storage, dry_run=True)

    result = await run_offline_slice(
        adapter=adapter,
        profile=python_profile(),
        storage=storage,
        checkpoint=checkpoint,
        delivery=delivery,
        owner_scope="operator",
        fetched_at=NOW,
    )

    assert result.fetched == 3
    assert result.new_publications == 3
    assert result.stored_decisions == 3
    assert result.accepted == 1
    assert result.pending == 0
    assert result.rejected == 2
    assert result.delivered == 1
    # Checkpoint зафиксирован на последнем сообщении.
    assert await checkpoint.get("tg-fixture") == "tg-2"

    # Принятое сообщение — «Ищу python…» (первая ссылка).
    accepted_key = "tg-fixture:tg-0"
    decision = storage.get_decision(accepted_key, "profile-python", 1)
    assert decision is not None
    assert decision.outcome is MatchOutcome.ACCEPT
    publication = storage.get_publication(accepted_key)
    assert publication is not None
    assert publication.canonical_url == "https://t.me/s/demo_channel/101"
    # Никаких полей автора в сохранённых данных.
    assert "author" not in publication.__dataclass_fields__

    # Offer-сообщение отклонено: для python-профиля не хватает required.
    offer_decision = storage.get_decision("tg-fixture:tg-1", "profile-python", 1)
    assert offer_decision is not None
    assert offer_decision.outcome is MatchOutcome.REJECT
    assert any(
        "required term missing" in reason or "offer wording" in reason
        for reason in offer_decision.reasons
    )


@pytest.mark.asyncio
async def test_e2e_tg_pipeline_repeat_is_idempotent(storage: SqliteStorage) -> None:
    """Повторный прогон: fetched=0 (checkpoint), данные не дублируются."""
    adapter = tg_adapter()
    checkpoint = SqliteCheckpointStore(storage)
    delivery = TelegramDelivery(storage=storage, dry_run=True)

    first = await run_offline_slice(
        adapter=adapter,
        profile=python_profile(),
        storage=storage,
        checkpoint=checkpoint,
        delivery=delivery,
        owner_scope="operator",
        fetched_at=NOW,
    )
    second = await run_offline_slice(
        adapter=adapter,
        profile=python_profile(),
        storage=storage,
        checkpoint=checkpoint,
        delivery=delivery,
        owner_scope="operator",
        fetched_at=NOW,
    )

    assert first.new_publications == 3
    assert second.fetched == 0
    assert second.new_publications == 0
    assert storage.count_publications() == 3
    assert storage.count_decisions() == 3


@pytest.mark.asyncio
async def test_e2e_tg_pipeline_second_profile_matches_third_message(
    storage: SqliteStorage,
) -> None:
    """Copywriter-профиль принимает только «Нужен копирайтер»."""
    adapter = tg_adapter()
    checkpoint = SqliteCheckpointStore(storage)
    delivery = TelegramDelivery(storage=storage, dry_run=True)

    result = await run_offline_slice(
        adapter=adapter,
        profile=copywriter_profile(),
        storage=storage,
        checkpoint=checkpoint,
        delivery=delivery,
        owner_scope="operator",
        fetched_at=NOW,
    )

    assert result.accepted == 1
    assert result.rejected == 2
    accepted_decision = storage.get_decision("tg-fixture:tg-2", "profile-copy", 1)
    assert accepted_decision is not None
    assert accepted_decision.outcome is MatchOutcome.ACCEPT
    assert "копирайтер" in accepted_decision.matched_terms

    # Первое сообщение (python) для этого профиля — несовпадение required.
    wrong = storage.get_decision("tg-fixture:tg-0", "profile-copy", 1)
    assert wrong is not None
    assert wrong.outcome is MatchOutcome.REJECT
    assert any("required term missing" in reason for reason in wrong.reasons)


@pytest.mark.asyncio
async def test_e2e_offer_gate_rejects_offer_post_in_pipeline(
    storage: SqliteStorage,
) -> None:
    """«Предлагаю услуги дизайна»: required совпал, но нет intent → REJECT offer gate."""
    design_profile = SearchProfile(
        profile_id="profile-design",
        owner_scope="operator",
        version=1,
        service_name="Дизайн",
        required_terms=("дизайна", "дизайн"),
        intent_terms=("ищу", "нужен"),
    )
    adapter = tg_adapter()
    checkpoint = SqliteCheckpointStore(storage)
    delivery = TelegramDelivery(storage=storage, dry_run=True)

    await run_offline_slice(
        adapter=adapter,
        profile=design_profile,
        storage=storage,
        checkpoint=checkpoint,
        delivery=delivery,
        owner_scope="operator",
        fetched_at=NOW,
    )

    offer = storage.get_decision("tg-fixture:tg-1", "profile-design", 1)
    assert offer is not None
    assert offer.outcome is MatchOutcome.REJECT
    assert any("offer wording" in reason for reason in offer.reasons)


@pytest.mark.asyncio
async def test_e2e_delivery_card_rendered_without_author(
    storage: SqliteStorage,
) -> None:
    """Dry-run доставка рендерит карточку; в тексте нет author-полей."""
    adapter = tg_adapter()
    checkpoint = SqliteCheckpointStore(storage)
    sent_cards: list[str***REMOVED*** = [***REMOVED***

    class CollectingTransport:
        """Захват готовых карточек (dry-run + capture для проверки)."""

        async def send(
            self,
            *,
            chat_id: str,
            text: str,
            disable_web_page_preview: bool = True,
        ) -> str:
            sent_cards.append(text)
            return f"msg-{len(sent_cards)***REMOVED***"

    delivery = TelegramDelivery(storage=storage, transport=CollectingTransport())

    result = await run_offline_slice(
        adapter=adapter,
        profile=python_profile(),
        storage=storage,
        checkpoint=checkpoint,
        delivery=delivery,
        owner_scope="operator",
        fetched_at=NOW,
    )

    assert result.delivered == 1
    assert len(sent_cards) == 1
    assert "Ищу python" in sent_cards[0***REMOVED***
    assert "author" not in sent_cards[0***REMOVED***.lower()
    assert "https://t.me/s/demo_channel/101" in sent_cards[0***REMOVED***