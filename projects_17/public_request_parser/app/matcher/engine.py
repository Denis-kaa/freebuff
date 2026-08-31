"""Детерминированный explainable matcher для Public Request Parser.

P5 реализует сопоставление текста публикации с `SearchProfile`:

- exact phrases и отдельные слова (с простым word-form доступом по префиксу);
- required/optional термины: required обязаны совпасть, optional повышают score;
- synonyms: совпадение любого алиаса группы засчитывается как совпадение canonical;
- stopwords: слишком общие optional слова не влияют на score;
- exclusions: совпадение запрещённого термина даёт жёсткий REJECT;
- intent gate: без сигнала спроса ("ищу/нужен") publication с offer-формулировкой
  отклоняется, чтобы не путать «предлагает услугу» с «ищет услугу»;
- пороги `pending_threshold` / `accept_threshold` из профиля;
- каждый decision воспроизводим: profile snapshot, matched/rejected terms, reasons.

Модуль не выполняет сетевых операций и не импортирует платформенный код.
Word-form обработка намеренно простая (префиксный доступ) и заменяема.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Iterable, Sequence

from app.domain import (
    ContractValidationError,
    MatchDecision,
    MatchOutcome,
    Publication,
    SearchMode,
    SearchProfile,
)

#: Токены, слишком общие для оценки optional-терминов.
STOPWORDS: frozenset[str] = frozenset(
    {
        "и",
        "в",
        "на",
        "с",
        "по",
        "для",
        "из",
        "за",
        "не",
        "а",
        "но",
        "или",
        "the",
        "a",
        "an",
        "to",
        "of",
        "for",
        "in",
        "on",
        "with",
        "and",
    }
)

#: Offer-формулировки («предлагает услугу») для intent gate.
#: Список намеренно консервативный: маркер срабатывает только в сочетании с
#: отсутствием demand-сигнала из профиля.
OFFER_MARKERS: tuple[str, ...] = (
    "предлага",
    "оказыва",
    "окажу",
    "помог",
    "выполн",
    "сделаю",
    "сделаем",
    "прода",
    "предостав",
    "готов ",
    "готова ",
)

_TOKEN_RE = re.compile(r"[^\W_)+", re.UNICODE)


def normalize_text(value: str) -> str:
    """Привести текст к нижнему регистру и схлопнуть разделители."""
    return re.sub(r"\s+", " ", value.strip().lower())


def tokenize(value: str) -> tuple[str, ...]:
    """Разбить нормализованный текст на слова (поддерживает кириллицу)."""
    return tuple(match.group(0) for match in _TOKEN_RE.finditer(value))


def is_stopword(term: str) -> bool:
    """Является ли термин служебным словом (не участвует в scoring)."""
    return term.strip().lower() in STOPWORDS


def _matches_term(term: str, tokens: Sequence[str], text: str) -> bool:
    """Проверить совпадение одного термина (слово или точная фраза).

    Слово: полное совпадение, либо префиксный word-form доступ для терминов
    длиной >= 4 символов (юрист → юриста/юристов). Фраза: скользящее окно по
    токенам, чтобы «data engineer» не совпадал с «data analysis for engineers».
    """
    term = term.strip().lower()
    if not term or not tokens:
        return False
    parts = tuple(term.split())
    if len(parts) > 1:
        window = len(parts)
        return any(
            tokens[index : index + window] == parts
            for index in range(len(tokens) - window + 1)
        )
    word = parts[0]
    if len(word) < 4:
        return word in tokens
    return any(token == word or token.startswith(word) for token in tokens)


def _matched_terms(
    terms: Iterable[str],
    tokens: tuple[str, ...],
    text: str,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Разделить термины на совпавшие и не совпавшие, сохраняя порядок."""
    matched: list[str] = []
    missing: list[str] = []
    for term in terms:
        if _matches_term(term, tokens, text):
            matched.append(term)
        else:
            missing.append(term)
    return tuple(matched), tuple(missing)


class RuleMatcher:
    """Детерминированное сопоставление публикации с версией профиля."""

    def __init__(self, profile: SearchProfile) -> None:
        self.profile = profile
        self._synonym_map: dict[str, tuple[str, ...]] = {}
        for canonical, aliases in profile.synonyms:
            if not canonical.strip():
                raise ContractValidationError("synonym canonical must be non-empty")
            self._synonym_map[canonical.strip().lower()] = tuple(
                alias.strip().lower() for alias in aliases if alias.strip()
            )

    def match(
        self,
        publication: Publication,
        *,
        decided_at: datetime | None = None,
    ) -> MatchDecision:
        """Вернуть explainable decision для одной публикации."""
        when = decided_at or datetime.now(timezone.utc)
        if when.tzinfo is None or when.utcoffset() is None:
            raise ContractValidationError("decided_at must be timezone-aware")

        text = " ".join(
            part
            for part in (publication.title, publication.summary, publication.content or "")
            if part
        )
        normalized = normalize_text(text)
        tokens = tokenize(normalized)

        return self._decide(publication, tokens, normalized, when)

    # ------------------------------------------------------------------
    def _decide(
        self,
        publication: Publication,
        tokens: tuple[str, ...],
        text: str,
        decided_at: datetime,
    ) -> MatchDecision:
        profile = self.profile
        reasons: list[str] = []
        rejected_terms: list[str] = []

        matched_required, missing_required = _matched_terms(
            profile.required_terms, tokens, text
        )
        matched_optional, _ = _matched_terms(profile.optional_terms, tokens, text)
        matched_excluded, _ = _matched_terms(profile.excluded_terms, tokens, text)
        matched_intent, _ = _matched_terms(profile.intent_terms, tokens, text)

        # Синonimы: совпадение любого алиаса засчитывает canonical.
        matched_synonyms: list[str] = []
        for canonical, aliases in self._synonym_map.items():
            hits = tuple(
                alias for alias in aliases if _matches_term(alias, tokens, text)
            )
            if hits or _matches_term(canonical, tokens, text):
                matched_synonyms.append(canonical)
                if canonical in profile.required_terms and canonical not in matched_required:
                    matched_required += (canonical,)
                    missing_required = tuple(t for t in missing_required if t != canonical)
                if canonical in profile.optional_terms and canonical not in matched_optional:
                    matched_optional += (canonical,)

        for term in matched_required:
            reasons.append(f"required term matched: {term}")
        for term in matched_optional:
            reasons.append(f"optional term matched: {term}")
        for term in matched_synonyms:
            reasons.append(f"synonym group matched: {term}")
        for term in matched_intent:
            reasons.append(f"intent term matched: {term}")

        # 1. Жёсткие негативные правила.
        if matched_excluded:
            rejected_terms.extend(matched_excluded)
            for term in matched_excluded:
                reasons.append(f"excluded term matched: {term}")
            return self._hard_reject(
                publication, reasons, rejected_terms, decided_at
            )

        if missing_required:
            rejected_terms.extend(missing_required)
            for term in missing_required:
                reasons.append(f"required term missing: {term}")
            return self._hard_reject(
                publication, reasons, rejected_terms, decided_at
            )

        offer_hit = any(marker in text for marker in OFFER_MARKERS)
        intent_hit = bool(matched_intent)

        if profile.mode is SearchMode.DEMAND:
            # Классический режим: «предлагает услугу» без спроса — reject.
            if offer_hit and not intent_hit:
                reasons.append("offer wording detected without intent signal")
                return self._hard_reject(
                    publication, reasons, rejected_terms, decided_at
                )
        else:
            # Jobseek-режим (SUPPLY): мы ищем предложения работы/заказа;
            # offer-формулировка — это НЕ повод отклонять (вакансии часто
            # нейтральны). Маркер предложения даёт intent-бонус к score.
            if offer_hit:
                intent_hit = True
                if not matched_intent:
                    reasons.append("supply mode: offer wording counted as intent")
            # demand-маркеры в jobseek не являются причиной reject (в тексте
            # «ищем кандидата» может встретиться «нужен»).

        # 2. Score из доступных компонентов профиля.
        components: list[float] = []
        if profile.required_terms:
            components.append(len(matched_required) / len(profile.required_terms))
        scoring_optional = tuple(
            term for term in profile.optional_terms if not is_stopword(term)
        )
        if scoring_optional:
            matched_scoring = tuple(
                term for term in matched_optional if not is_stopword(term)
            )
            components.append(len(matched_scoring) / len(scoring_optional))
        elif profile.optional_terms:
            skipped = tuple(term for term in profile.optional_terms if is_stopword(term))
            for term in skipped:
                reasons.append(f"optional term ignored (stopword): {term}")
        if self._synonym_map:
            unique_groups = {canonical for canonical, _ in profile.synonyms}
            components.append(len(matched_synonyms) / max(1, len(unique_groups)))

        if not components:
            reasons.append("profile has no matching rules")
            return self._hard_reject(publication, reasons, rejected_terms, decided_at)

        score = min(1.0, sum(components) / len(components) * 0.9)
        if intent_hit:
            score = min(1.0, score + 0.1)
        outcome = self._outcome_for(score)

        return MatchDecision(
            publication_key=publication.item_key,
            profile_id=profile.profile_id,
            profile_version=profile.version,
            outcome=outcome,
            score=score,
            matched_terms=matched_required + matched_optional,
            matched_synonyms=tuple(matched_synonyms),
            rejected_terms=tuple(rejected_terms),
            reasons=tuple(reasons),
            rules_snapshot=profile.rules_snapshot,
            decided_at=decided_at,
        )

    # ------------------------------------------------------------------
    def _outcome_for(self, score: float) -> MatchOutcome:
        if score >= self.profile.accept_threshold:
            return MatchOutcome.ACCEPT
        if score >= self.profile.pending_threshold:
            return MatchOutcome.PENDING
        return MatchOutcome.REJECT

    def _hard_reject(
        self,
        publication: Publication,
        reasons: list[str],
        rejected_terms: list[str],
        decided_at: datetime,
    ) -> MatchDecision:
        return MatchDecision(
            publication_key=publication.item_key,
            profile_id=self.profile.profile_id,
            profile_version=self.profile.version,
            outcome=MatchOutcome.REJECT,
            score=0.0,
            matched_terms=(),
            matched_synonyms=(),
            rejected_terms=tuple(rejected_terms),
            reasons=tuple(reasons),
            rules_snapshot=self.profile.rules_snapshot,
            decided_at=decided_at,
        )


__all__ = [
    "OFFER_MARKERS",
    "STOPWORDS",
    "RuleMatcher",
    "is_stopword",
    "normalize_text",
    "tokenize",
]