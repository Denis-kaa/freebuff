"""Optional external provider boundary for translation drafts.

The deterministic core depends only on this protocol. A provider may be an LLM,
local model, or human workflow, but it can never publish directly to live data.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from app.localization.contract import SourceDocument, TranslationDraft


class TranslationProvider(ABC):
    """Generate proposed translations without persistence or acceptance rights."""

    provider_id: str

    @abstractmethod
    def translate(self, documents: Iterable[SourceDocument], target_locale: str) -> tuple[TranslationDraft, ...]:
        raise NotImplementedError


class ExternalLLMTranslationProvider(TranslationProvider):
    """Provider shell for a future user-selected LLM integration.

    It intentionally fails closed until a concrete external client is injected.
    No API key, network call, or model dependency belongs in the core project.
    """

    provider_id = "external_llm"

    def translate(self, documents: Iterable[SourceDocument], target_locale: str) -> tuple[TranslationDraft, ...]:
        raise RuntimeError(
            "external LLM provider is not configured; inject a provider explicitly "
            "to create translation drafts"
        )
