"""Versioned learner-facing localization for the approved content corpus."""

from app.localization.contract import (
    LocalizationPolicy,
    SourceDocument,
    TranslationDraft,
    TranslationStatus,
)
from app.localization.extractor import (
    build_manifest,
    iter_source_documents,
    sha256_text,
    write_manifest,
)
from app.localization.gemini import GeminiTranslationProvider
from app.localization.keys import GeminiKeyPool
from app.localization.provider import ExternalLLMTranslationProvider, TranslationProvider
from app.localization.validator import translation_status, validate_translation
from app.localization.workflow import (
    TranslationStatusRow,
    draft_is_current,
    draft_metadata_path,
    draft_path,
    publish_reviewed_translation,
    scan_source,
    target_path,
    translation_status_rows,
    write_translation_draft,
)

__all__ = [
    "ExternalLLMTranslationProvider",
    "GeminiKeyPool",
    "GeminiTranslationProvider",
    "LocalizationPolicy",
    "SourceDocument",
    "TranslationDraft",
    "TranslationProvider",
    "TranslationStatus",
    "build_manifest",
    "iter_source_documents",
    "sha256_text",
    "translation_status",
    "validate_translation",
    "write_manifest",
    "TranslationStatusRow",
    "draft_is_current",
    "draft_metadata_path",
    "draft_path",
    "publish_reviewed_translation",
    "scan_source",
    "target_path",
    "translation_status_rows",
    "write_translation_draft",
]
