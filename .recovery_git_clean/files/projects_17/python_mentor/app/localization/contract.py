"""Contracts for versioned learner-facing localization.

English upstream remains canonical. Locales are projections that carry the
source hash they were translated from and can become stale after an upstream
change.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class TranslationStatus(str, Enum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    STALE = "stale"


@dataclass(frozen=True)
class SourceDocument:
    """One learner-facing source document from the approved upstream clone."""

    document_id: str
    source_relpath: str
    content_kind: str
    locale: str
    content_hash: str
    text: str

    def __post_init__(self) -> None:
        if self.locale != "en":
            raise ValueError("canonical source documents must use locale='en'")
        if not self.document_id or not self.source_relpath:
            raise ValueError("document identity and source path are required")
        if len(self.content_hash) != 64:
            raise ValueError("content_hash must be a SHA-256 hex digest")

    def to_dict(self) -> dict[str, Any***REMOVED***:
        return {
            "document_id": self.document_id,
            "source_relpath": self.source_relpath,
            "content_kind": self.content_kind,
            "locale": self.locale,
            "content_hash": self.content_hash,
            "characters": len(self.text),
        ***REMOVED***


@dataclass(frozen=True)
class TranslationDraft:
    """A proposed translation; it is not live content until reviewed."""

    document_id: str
    source_hash: str
    source_locale: str
    target_locale: str
    text: str
    provider: str
    model: str
    status: TranslationStatus = TranslationStatus.DRAFT

    def __post_init__(self) -> None:
        if self.source_locale != "en":
            raise ValueError("translation source_locale must be 'en'")
        if not self.target_locale or self.target_locale == self.source_locale:
            raise ValueError("target_locale must differ from source_locale")
        if not self.text.strip():
            raise ValueError("translation text must not be empty")
        if len(self.source_hash) != 64:
            raise ValueError("source_hash must be a SHA-256 hex digest")
        if self.status is TranslationStatus.REVIEWED and self.provider == "":
            raise ValueError("reviewed translations require provider provenance")

    def to_dict(self) -> dict[str, Any***REMOVED***:
        return {
            "document_id": self.document_id,
            "source_hash": self.source_hash,
            "source_locale": self.source_locale,
            "target_locale": self.target_locale,
            "provider": self.provider,
            "model": self.model,
            "status": self.status.value,
            "characters": len(self.text),
        ***REMOVED***


@dataclass(frozen=True)
class LocalizationPolicy:
    """Explicit policy for the optional translation projection."""

    source_locale: str = "en"
    target_locale: str = "ru"
    default_provider: str = "external_llm"
    require_review_before_publish: bool = True
    translate_code: bool = False
    translate_tests: bool = False
    translate_reference_solutions: bool = False

    def __post_init__(self) -> None:
        if self.source_locale == self.target_locale:
            raise ValueError("source and target locales must differ")
        if self.translate_code or self.translate_tests or self.translate_reference_solutions:
            raise ValueError("code, tests and reference solutions are never translated")
