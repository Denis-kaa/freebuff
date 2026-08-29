"""Validation for translation drafts and reviewed locale projections."""

from __future__ import annotations

***REMOVED***
***REMOVED***

from app.localization.contract import SourceDocument, TranslationDraft, TranslationStatus


_CODE_FENCE = re.compile(r"^\s*(```+|~~~+)", re.MULTILINE)
_INLINE_CODE = re.compile(r"`[^`\n***REMOVED***+`")
_LINK = re.compile(r"\[[^\***REMOVED******REMOVED***+\***REMOVED***\(([^)***REMOVED***+)\)")
_HEADING = re.compile(r"^\s{0,3***REMOVED***#{1,6***REMOVED***\s+", re.MULTILINE)


def _tokens(pattern: re.Pattern[str***REMOVED***, text: str) -> tuple[str, ...***REMOVED***:
    return tuple(pattern.findall(text))


def validate_translation(source: SourceDocument, draft: TranslationDraft) -> tuple[str, ...***REMOVED***:
    """Return deterministic validation errors; empty tuple means structurally valid."""

    errors: list[str***REMOVED*** = [***REMOVED***
    if draft.document_id != source.document_id:
        errors.append("document_id mismatch")
    if draft.source_hash != source.content_hash:
        errors.append("source_hash is stale")
    if draft.source_locale != source.locale:
        errors.append("source_locale mismatch")
    if draft.target_locale == draft.source_locale:
        errors.append("target locale equals source locale")
    if len(_tokens(_CODE_FENCE, source.text)) != len(_tokens(_CODE_FENCE, draft.text)):
        errors.append("Markdown code-fence count changed")
    if _tokens(_INLINE_CODE, source.text) != _tokens(_INLINE_CODE, draft.text):
        errors.append("inline-code tokens changed")
    if _tokens(_LINK, source.text) != _tokens(_LINK, draft.text):
        errors.append("Markdown link targets changed")
    if len(_tokens(_HEADING, source.text)) != len(_tokens(_HEADING, draft.text)):
        errors.append("heading structure changed")
    return tuple(errors)


def translation_status(source: SourceDocument, translation_path: str | Path) -> TranslationStatus:
    """Classify a stored translation by its sidecar source hash."""

    path = Path(translation_path)
    sidecar = path.with_suffix(path.suffix + ".source_hash")
    if not path.exists() or not sidecar.exists():
        return TranslationStatus.DRAFT
    recorded_hash = sidecar.read_text(encoding="utf-8").strip()
    return TranslationStatus.REVIEWED if recorded_hash == source.content_hash else TranslationStatus.STALE
