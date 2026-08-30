"""Доменные контракты Public Request Parser.

Модуль задаёт устойчивую границу между источниками, нормализованными
публикациями, профилями поиска, matching-решениями и инфраструктурой.
Контракты не выполняют сетевые операции и не импортируют платформенный код.

Пример:
    >>> from datetime import datetime, timezone
    >>> publication = Publication(
    ...     source_id="stackoverflow",
    ...     item_id="q-42",
    ...     canonical_url="https://example.test/q/42",
    ...     title="Need Python help",
    ...     published_at=datetime.now(timezone.utc),
    ... )
    >>> publication.item_key
    'stackoverflow:q-42'
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import AsyncIterator, Mapping, Protocol, TypeAlias
from urllib.parse import urlparse


Metadata: TypeAlias = Mapping[str, str]
RuleSnapshot: TypeAlias = Mapping[str, tuple[str, ...]]


class ContractValidationError(ValueError):
    """Некорректные данные на доменной границе."""


class AdapterError(RuntimeError):
    """Ошибка одного источника; не является отказом matching-правила."""


class PublicationStatus(StrEnum):
    """Жизненный статус найденной публикации в системе."""

    NEW = "new"
    VIEWED = "viewed"
    RELEVANT = "relevant"
    IRRELEVANT = "irrelevant"
    ARCHIVED = "archived"


class MatchOutcome(StrEnum):
    """Результат детерминированного сопоставления с профилем."""

    ACCEPT = "accept"
    PENDING = "pending"
    REJECT = "reject"


class SearchMode(StrEnum):
    """Направление поиска профиля: спрос или предложение."""

    # Классический режим: ищем публикации, где ЛЮДИ ищут услугу/работу.
    DEMAND = "demand"
    # Jobseek-режим: ищем публикации, где РАБОТОДАТЕЛИ/заказчики предлагают
    # работу/заказ (вакансии); intent-гейт инвертируется.
    SUPPLY = "supply"


class SourcePolicyStatus(StrEnum):
    """Статус разрешения конкретного режима доступа к источнику."""

    ALLOWED = "allowed"
    TECHNICAL_CANDIDATE = "technical_candidate"
    CONDITIONAL = "conditional"
    MANUAL_REVIEW = "manual_review"
    POLICY_BLOCKED = "policy_blocked"


class DeliveryStatus(StrEnum):
    """Результат попытки доставки карточки."""

    SENT = "sent"
    SKIPPED = "skipped"
    FAILED = "failed"


def _require_non_empty(value: str, field_name: str) -> str:
    """Проверить обязательную непустую строку."""
    if not isinstance(value, str) or not value.strip():
        raise ContractValidationError(f"{field_name} must be a non-empty string")
    return value.strip()


def _validate_url(value: str, field_name: str = "canonical_url") -> str:
    """Проверить абсолютный HTTP(S) URL без нормализации содержимого."""
    value = _require_non_empty(value, field_name)
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ContractValidationError(f"{field_name} must be an absolute HTTP(S) URL")
    return value


def _validate_utc(value: datetime, field_name: str) -> datetime:
    """Потребовать timezone-aware дату и привести её к UTC."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ContractValidationError(f"{field_name} must be timezone-aware")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class SourceItem:
    """Минимальный элемент, возвращаемый source adapter до нормализации."""

    item_id: str
    canonical_url: str
    title: str
    published_at: datetime | None = None
    summary: str = ""
    content: str | None = None
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "item_id", _require_non_empty(self.item_id, "item_id"))
        object.__setattr__(self, "canonical_url", _validate_url(self.canonical_url))
        object.__setattr__(self, "title", _require_non_empty(self.title, "title"))
        if self.published_at is not None:
            object.__setattr__(
                self,
                "published_at",
                _validate_utc(self.published_at, "published_at"),
            )
        if not isinstance(self.metadata, Mapping):
            raise ContractValidationError("metadata must be a mapping")


@dataclass(frozen=True, slots=True)
class Publication:
    """Нормализованная открытая публикация без обязательной модели автора.

    `content` является временным полем и может быть удалено storage layer после
    истечения TTL. Авторские и контактные данные намеренно отсутствуют.
    """

    source_id: str
    item_id: str
    canonical_url: str
    title: str
    published_at: datetime | None = None
    summary: str = ""
    content: str | None = None
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Metadata = field(default_factory=dict)
    status: PublicationStatus = PublicationStatus.NEW

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _require_non_empty(self.source_id, "source_id"))
        object.__setattr__(self, "item_id", _require_non_empty(self.item_id, "item_id"))
        object.__setattr__(self, "canonical_url", _validate_url(self.canonical_url))
        object.__setattr__(self, "title", _require_non_empty(self.title, "title"))
        object.__setattr__(self, "fetched_at", _validate_utc(self.fetched_at, "fetched_at"))
        if self.published_at is not None:
            object.__setattr__(
                self,
                "published_at",
                _validate_utc(self.published_at, "published_at"),
            )
        if not isinstance(self.metadata, Mapping):
            raise ContractValidationError("metadata must be a mapping")

    @property
    def item_key(self) -> str:
        """Стабильный ключ источника для deduplication/checkpoint."""
        return f"{self.source_id}:{self.item_id}"


@dataclass(frozen=True, slots=True)
class SearchProfile:
    """Версионируемый профиль поиска пользователя/оператора."""

    profile_id: str
    owner_scope: str
    version: int
    service_name: str
    required_terms: tuple[str, ...] = ()
    optional_terms: tuple[str, ...] = ()
    synonyms: tuple[tuple[str, tuple[str, ...]], ...] = ()
    excluded_terms: tuple[str, ...] = ()
    intent_terms: tuple[str, ...] = ()
    accept_threshold: float = 0.8
    pending_threshold: float = 0.5
    source_ids: tuple[str, ...] = ()
    rules_snapshot: RuleSnapshot = field(default_factory=dict)
    mode: SearchMode = SearchMode.DEMAND

    def __post_init__(self) -> None:
        object.__setattr__(self, "profile_id", _require_non_empty(self.profile_id, "profile_id"))
        object.__setattr__(self, "owner_scope", _require_non_empty(self.owner_scope, "owner_scope"))
        object.__setattr__(self, "service_name", _require_non_empty(self.service_name, "service_name"))
        if self.version < 1:
            raise ContractValidationError("version must be >= 1")
        if not 0 <= self.pending_threshold <= self.accept_threshold <= 1:
            raise ContractValidationError(
                "thresholds must satisfy 0 <= pending <= accept <= 1"
            )
        if any(not isinstance(term, str) or not term.strip() for term in self.all_terms):
            raise ContractValidationError("profile terms must be non-empty strings")
        if not isinstance(self.mode, SearchMode):
            raise ContractValidationError("mode must be SearchMode.demand or SearchMode.supply")
        if not self.rules_snapshot:
            snapshot = {
                "required_terms": tuple(self.required_terms),
                "optional_terms": tuple(self.optional_terms),
                "excluded_terms": tuple(self.excluded_terms),
                "intent_terms": tuple(self.intent_terms),
            }
            object.__setattr__(self, "rules_snapshot", snapshot)

    @property
    def all_terms(self) -> tuple[str, ...]:
        """Все термины профиля в стабильном порядке."""
        synonym_terms = tuple(
            synonym
            for _, values in self.synonyms
            for synonym in values
        )
        return self.required_terms + self.optional_terms + synonym_terms + self.excluded_terms + self.intent_terms


@dataclass(frozen=True, slots=True)
class MatchDecision:
    """Объяснимое решение matcher для конкретной версии профиля."""

    publication_key: str
    profile_id: str
    profile_version: int
    outcome: MatchOutcome
    score: float
    matched_terms: tuple[str, ...] = ()
    matched_synonyms: tuple[str, ...] = ()
    rejected_terms: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()
    rules_snapshot: RuleSnapshot = field(default_factory=dict)
    decided_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        object.__setattr__(self, "publication_key", _require_non_empty(self.publication_key, "publication_key"))
        object.__setattr__(self, "profile_id", _require_non_empty(self.profile_id, "profile_id"))
        if self.profile_version < 1:
            raise ContractValidationError("profile_version must be >= 1")
        if not 0 <= self.score <= 1:
            raise ContractValidationError("score must be between 0 and 1")
        object.__setattr__(self, "decided_at", _validate_utc(self.decided_at, "decided_at"))
        if self.outcome is MatchOutcome.ACCEPT and not self.reasons:
            raise ContractValidationError("accepted decision must contain reasons")


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    """Политика хранения текста и metadata для конкретного source scope."""

    text_ttl: timedelta | None
    metadata_ttl: timedelta | None = None
    allow_full_text: bool = True
    max_text_chars: int = 20_000

    def __post_init__(self) -> None:
        for name, value in (("text_ttl", self.text_ttl), ("metadata_ttl", self.metadata_ttl)):
            if value is not None and value.total_seconds() < 0:
                raise ContractValidationError(f"{name} must not be negative")
        if self.max_text_chars < 0:
            raise ContractValidationError("max_text_chars must be >= 0")
        if not self.allow_full_text and self.text_ttl is not None:
            raise ContractValidationError(
                "text_ttl must be None when full text storage is disabled"
            )

    def effective_text_ttl(self, source_limit: timedelta | None) -> timedelta | None:
        """Вернуть более строгий TTL, никогда не ослабляя source policy."""
        if not self.allow_full_text or self.text_ttl is None:
            return None
        if source_limit is None:
            return self.text_ttl
        return min(self.text_ttl, source_limit)


@dataclass(frozen=True, slots=True)
class SourcePolicy:
    """Evidence-backed policy record для конкретного режима источника."""

    source_id: str
    status: SourcePolicyStatus
    access_mode: str
    endpoint: str
    checked_at: datetime
    allowed_fields: tuple[str, ...] = ()
    retention: RetentionPolicy = field(
        default_factory=lambda: RetentionPolicy(text_ttl=None, allow_full_text=False)
    )
    evidence_urls: tuple[str, ...] = ()
    attribution_required: bool = False
    user_facing: bool = False
    can_poll: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _require_non_empty(self.source_id, "source_id"))
        object.__setattr__(self, "access_mode", _require_non_empty(self.access_mode, "access_mode"))
        object.__setattr__(self, "endpoint", _validate_url(self.endpoint, "endpoint"))
        object.__setattr__(self, "checked_at", _validate_utc(self.checked_at, "checked_at"))
        if self.status is SourcePolicyStatus.ALLOWED and not self.evidence_urls:
            raise ContractValidationError("allowed source policy requires evidence_urls")
        if self.can_poll and self.status is not SourcePolicyStatus.ALLOWED:
            raise ContractValidationError("only allowed source policy may enable polling")
        if self.user_facing and self.status is not SourcePolicyStatus.ALLOWED:
            raise ContractValidationError("user-facing source must be allowed")


class SourceAdapter(Protocol):
    """Асинхронный read-only порт одного источника."""

    source_id: str

    async def fetch(self, *, limit: int = 50, checkpoint: str | None = None) -> AsyncIterator[SourceItem]:
        """Получить bounded batch элементов, не меняя источник."""
        ...

    async def health(self) -> bool:
        """Проверить техническую доступность без обхода policy gate."""
        ...


class CheckpointStore(Protocol):
    """Порт идемпотентного сохранения позиции обработки."""

    async def get(self, source_id: str) -> str | None:
        """Получить последний подтверждённый checkpoint."""
        ...

    async def commit(self, source_id: str, item_id: str) -> None:
        """Атомарно подтвердить обработанный item."""
        ...


@dataclass(frozen=True, slots=True)
class DeliveryAttempt:
    """Результат одной попытки доставки decision пользователю."""

    delivery_key: str
    status: DeliveryStatus
    attempted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    provider_message_id: str | None = None
    error_code: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "delivery_key", _require_non_empty(self.delivery_key, "delivery_key"))
        object.__setattr__(self, "attempted_at", _validate_utc(self.attempted_at, "attempted_at"))
        if self.status is DeliveryStatus.SENT and not self.provider_message_id:
            raise ContractValidationError("sent delivery requires provider_message_id")
        if self.status is DeliveryStatus.FAILED and not self.error_code:
            raise ContractValidationError("failed delivery requires error_code")


class Delivery(Protocol):
    """Порт доставки карточки без outbound к автору публикации."""

    async def send(
        self,
        publication: Publication,
        decision: MatchDecision,
        *,
        owner_scope: str,
    ) -> DeliveryAttempt:
        """Идемпотентно доставить результат в user-owned channel."""
        ...


__all__ = [
    "AdapterError",
    "CheckpointStore",
    "ContractValidationError",
    "Delivery",
    "DeliveryAttempt",
    "DeliveryStatus",
    "MatchDecision",
    "MatchOutcome",
    "Metadata",
    "Publication",
    "PublicationStatus",
    "RetentionPolicy",
    "RuleSnapshot",
    "SearchMode",
    "SearchProfile",
    "SourceAdapter",
    "SourceItem",
    "SourcePolicy",
    "SourcePolicyStatus",
]
