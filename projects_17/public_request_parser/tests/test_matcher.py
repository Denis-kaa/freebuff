"""Hermetic tests for P5 deterministic matcher."""

from __future__ import annotations

from datetime import datetime, timezone

from app.domain import MatchOutcome, Publication, SearchMode, SearchProfile
from app.matcher import OFFER_MARKERS, RuleMatcher, is_stopword, normalize_text

NOW = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)


def make_publication(
    *,
    title: str,
    summary: str = "",
    content: str | None = None,
    item_id: str = "item-1",
) -> Publication:
    """Создать публикацию без авторских полей для тестов matcher."""
    return Publication(
        source_id="fixture-source",
        item_id=item_id,
        canonical_url=f"https://example.test/items/{item_id}",
        title=title,
        summary=summary,
        content=content,
        published_at=NOW,
        fetched_at=NOW,
    )


def make_profile(**overrides: object) -> SearchProfile:
    """Профиль по умолчанию для тестов."""
    defaults: dict[str, object] = {
        "profile_id": "profile-1",
        "owner_scope": "operator",
        "version": 1,
        "service_name": "Python разработка",
        "required_terms": ("python",),
        "optional_terms": ("backend",),
        "intent_terms": ("ищу", "нужен"),
    }
    defaults.update(overrides)
    return SearchProfile(**defaults)  # type: ignore[arg-type]


def test_normalize_text_and_stopwords() -> None:
    """Нормализация и stopword-детекция работают для RU/EN."""
    assert normalize_text("  Нужен   Python-разработчик! ") == "нужен python-разработчик!"
    assert is_stopword("и")
    assert is_stopword("The")
    assert not is_stopword("python")


def test_required_match_accepts_with_explanation() -> None:
    """Полное совпадение → ACCEPT с видимыми reasons и snapshot профиля."""
    profile = make_profile()
    publication = make_publication(title="Ищу python backend разработчика")

    decision = RuleMatcher(profile).match(publication, decided_at=NOW)

    assert decision.outcome is MatchOutcome.ACCEPT
    assert decision.score >= profile.accept_threshold
    assert "required term matched: python" in decision.reasons
    assert decision.profile_version == profile.version
    assert decision.rules_snapshot == profile.rules_snapshot
    assert decision.publication_key == publication.item_key


def test_missing_required_rejects_hard() -> None:
    """Отсутствие обязательного термина — жёсткий REJECT с причиной."""
    profile = make_profile(required_terms=("python", "django"))
    publication = make_publication(title="Ищу backend разработчика")

    decision = RuleMatcher(profile).match(publication, decided_at=NOW)

    assert decision.outcome is MatchOutcome.REJECT
    assert decision.score == 0.0
    assert "required term missing: django" in decision.reasons
    assert "django" in decision.rejected_terms


def test_excluded_term_rejects_even_with_required_match() -> None:
    """Запрещённый термин сильнее обязательного совпадения."""
    profile = make_profile(excluded_terms=("курс",))
    publication = make_publication(
        title="Ищу python, но не курс, а исполнителя"
    )

    decision = RuleMatcher(profile).match(publication, decided_at=NOW)

    assert decision.outcome is MatchOutcome.REJECT
    assert decision.score == 0.0
    assert "excluded term matched: курс" in decision.reasons
    assert "курс" in decision.rejected_terms


def test_synonym_aliases_satisfy_required_term() -> None:
    """Алиас синонима засчитывается как required canonical."""
    profile = make_profile(
        required_terms=("python",),
        optional_terms=(),
        synonyms=(("python", ("django", "питон")),),
    )
    publication = make_publication(title="Ищу django разработчика")

    decision = RuleMatcher(profile).match(publication, decided_at=NOW)

    assert decision.outcome is MatchOutcome.ACCEPT
    assert "python" in decision.matched_terms
    assert decision.matched_synonyms == ("python",)
    assert "synonym group matched: python" in decision.reasons


def test_partial_optional_yields_pending() -> None:
    """Только половина optional терминов → PENDING (score между порогами)."""
    profile = make_profile(optional_terms=("backend", "api"))
    publication = make_publication(title="Нужен python backend")

    decision = RuleMatcher(profile).match(publication, decided_at=NOW)

    assert decision.outcome is MatchOutcome.PENDING
    assert profile.pending_threshold <= decision.score < profile.accept_threshold


def test_offer_wording_without_intent_rejects() -> None:
    """«Предлагаю услугу» без demand-сигнала — REJECT (граница спрос/предложение)."""
    profile = make_profile()
    publication = make_publication(
        title="Предлагаю услуги python backend разработки",
    )

    decision = RuleMatcher(profile).match(publication, decided_at=NOW)

    assert decision.outcome is MatchOutcome.REJECT
    assert decision.score == 0.0
    assert "offer wording" in " ".join(decision.reasons)


def test_intent_boost_raises_score_when_demand_present() -> None:
    """Demand-сигнал поднимает score и различает «ищет» от нейтрального текста."""
    profile = make_profile(optional_terms=("backend",))
    plain = make_publication(title="python")
    with_intent = make_publication(title="Ищу python")

    decision_plain = RuleMatcher(profile).match(plain, decided_at=NOW)
    decision_intent = RuleMatcher(profile).match(with_intent, decided_at=NOW)

    assert decision_plain.score == 0.45
    assert decision_intent.score == 0.55
    assert "intent term matched: ищу" in decision_intent.reasons
    assert decision_intent.outcome is MatchOutcome.PENDING
    assert decision_plain.outcome is MatchOutcome.REJECT


def test_exact_phrase_does_not_cross_word_boundaries() -> None:
    """Фраза «data engineer» не совпадает с «data analysis for engineers»."""
    profile = make_profile(required_terms=("data engineer",))
    publication = make_publication(
        title="data analysis for engineers",
    )

    decision = RuleMatcher(profile).match(publication, decided_at=NOW)

    assert decision.outcome is MatchOutcome.REJECT
    assert "required term missing: data engineer" in decision.reasons


def test_prefix_word_forms_and_short_term_safety() -> None:
    """Юрист → юриста (префикс), но короткие термины не дают ложных совпадений."""
    profile = make_profile(required_terms=("юрист",), optional_terms=())
    publication = make_publication(title="Нужен юриста для сделки")

    decision = RuleMatcher(profile).match(publication, decided_at=NOW)

    assert decision.outcome is MatchOutcome.ACCEPT

    short_profile = make_profile(required_terms=("go",), optional_terms=())
    go_decision = RuleMatcher(short_profile).match(
        make_publication(title="goal oriented developer"),
        decided_at=NOW,
    )
    assert go_decision.outcome is MatchOutcome.REJECT


def test_stopword_optional_terms_do_not_pollute_score() -> None:
    """Optional-стопслово игнорируется и не занижает ratio."""
    profile = make_profile(optional_terms=("и",))  # stopword-only optional
    publication = make_publication(title="Нужен python")

    decision = RuleMatcher(profile).match(publication, decided_at=NOW)

    assert decision.outcome is MatchOutcome.ACCEPT
    assert "optional term ignored (stopword): и" in decision.reasons


def test_empty_profile_rejects_with_reason() -> None:
    """Профиль без правил не может принять публикацию молча."""
    profile = make_profile(required_terms=(), optional_terms=())
    publication = make_publication(title="python")

    decision = RuleMatcher(profile).match(publication, decided_at=NOW)

    assert decision.outcome is MatchOutcome.REJECT
    assert "profile has no matching rules" in decision.reasons


def test_match_is_deterministic() -> None:
    """Одинаковые входы дают побайтово одинаковый decision (кроме времени)."""
    profile = make_profile()
    publication = make_publication(title="Ищу python backend")

    first = RuleMatcher(profile).match(publication, decided_at=NOW)
    second = RuleMatcher(profile).match(publication, decided_at=NOW)

    assert first == second
    assert first.decided_at == second.decided_at == NOW


def test_offer_markers_are_documented_and_non_empty() -> None:
    """Константа маркеров существует и доступна для policy-обсуждения."""
    assert OFFER_MARKERS
    assert any("предлага" in marker for marker in OFFER_MARKERS)


# --- Jobseek-режим (SearchMode.SUPPLY) -------------------------------------


def test_supply_mode_accepts_vacancy_without_demand_markers() -> None:
    """В jobseek-режиме вакансия без «ищу/нужен» принимается (intent по offer)."""
    profile = make_profile(mode=SearchMode.SUPPLY)
    publication = make_publication(
        title="Python backend разработчик",
        summary="Компания ищет разработчика для проекта",
    )

    decision = RuleMatcher(profile).match(publication, decided_at=NOW)

    # Accept: required=python matched, optional=backend matched, demand markers not needed.
    assert decision.outcome is MatchOutcome.ACCEPT
    assert decision.score >= 0.70


def test_supply_mode_neutral_vacancy_accepted_with_optional() -> None:
    """Нейтральная формулировка (без offer-маркеров) тоже проходит по required."""
    profile = make_profile(mode=SearchMode.SUPPLY)
    publication = make_publication(title="Python backend (Django)")

    decision = RuleMatcher(profile).match(publication, decided_at=NOW)

    assert decision.outcome in (MatchOutcome.ACCEPT, MatchOutcome.PENDING)


def test_demand_mode_still_rejects_offer_without_intent() -> None:
    """Классический режим не затронут: offer без спроса — reject."""
    profile = make_profile(mode=SearchMode.DEMAND)  # default
    publication = make_publication(title="Предлагаю услуги python-разработки")

    decision = RuleMatcher(profile).match(publication, decided_at=NOW)

    assert decision.outcome is MatchOutcome.REJECT
    assert "offer wording detected without intent signal" in decision.reasons
