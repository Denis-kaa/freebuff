"""Operational localization workflow: scan, detect drift, publish reviewed drafts."""

from __future__ import annotations

import json
from dataclasses import dataclass
}

from app.localization.contract import SourceDocument, TranslationDraft, TranslationStatus
from app.localization.extractor import iter_source_documents, write_manifest
from app.localization.validator import validate_translation


def draft_path(source: SourceDocument, draft_root: str | Path) -> Path:
    """Return the non-live path used for a provider draft body."""

    target = target_path(source, draft_root)
    return target.with_suffix(target.suffix + ".draft.md")


def draft_metadata_path(source: SourceDocument, draft_root: str | Path) -> Path:
    """Return the sidecar path for a non-live draft."""

    target = target_path(source, draft_root)
    return target.with_suffix(target.suffix + ".draft.json")


def draft_is_current(source: SourceDocument, draft_root: str | Path) -> bool:
    """Return whether an existing draft belongs to the current source hash."""

    metadata_path = draft_metadata_path(source, draft_root)
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(metadata, dict):
        return False
    source_hash = metadata.get("source_hash")
    return isinstance(source_hash, str) and source_hash == source.content_hash


def write_translation_draft(
    source: SourceDocument,
    draft: TranslationDraft,
    draft_root: str | Path,
) -> Path:
    """Persist one provider draft outside the live locale projection.

    The Markdown body and a JSON metadata sidecar are written under a dedicated
    draft root. This function never writes source-hash sidecars used by the
    reviewed projection and therefore cannot make a draft look published.
    """

    if draft.status is not TranslationStatus.DRAFT:
        raise ValueError("only draft translations may be stored in the draft area")
    errors = validate_translation(source, draft)
    destination = draft_path(source, draft_root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(draft.text, encoding="utf-8")
    temporary.replace(destination)

    metadata_path = draft_metadata_path(source, draft_root)
    metadata = draft.to_dict()
    metadata["source_relpath"] = source.source_relpath
    metadata["validation_errors"] = list(errors)
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return destination


@dataclass(frozen=True)
class TranslationStatusRow:
    """Machine-readable status for one source document and target locale."""

    document_id: str
    source_relpath: str
    target_relpath: str
    status: TranslationStatus

    def to_dict(self) -> dict[str, str]:
        return {
            "document_id": self.document_id,
            "source_relpath": self.source_relpath,
            "target_relpath": self.target_relpath,
            "status": self.status.value,
        }


def target_path(source: SourceDocument, target_root: str | Path) -> Path:
    """Map an upstream relative path to the target locale projection."""

    return Path(target_root) / source.source_relpath


def scan_source(
    source_root: str | Path,
    manifest_path: str | Path,
    *,
    target_locale: str = "ru",
) -> dict[str, object]:
    """Extract source docs and write a deterministic manifest."""

    from app.localization.extractor import build_manifest

    documents = iter_source_documents(source_root)
    manifest = build_manifest(documents, target_locale=target_locale)
    write_manifest(manifest, manifest_path)
    return manifest


def translation_status_rows(
    documents: tuple[SourceDocument, ...],
    target_root: str | Path,
) -> tuple[TranslationStatusRow, ...]:
    """Classify target files by source-hash sidecar freshness."""

    rows: list[TranslationStatusRow] = []
    for source in documents:
        destination = target_path(source, target_root)
        sidecar = destination.with_suffix(destination.suffix + ".source_hash")
        if not destination.exists() or not sidecar.exists():
            status = TranslationStatus.DRAFT
        else:
            recorded = sidecar.read_text(encoding="utf-8").strip()
            status = (
                TranslationStatus.REVIEWED
                if recorded == source.content_hash
                else TranslationStatus.STALE
            )
        rows.append(
            TranslationStatusRow(
                document_id=source.document_id,
                source_relpath=source.source_relpath,
                target_relpath=str(destination),
                status=status,
            )
        )
    return tuple(rows)


def publish_reviewed_translation(
    source: SourceDocument,
    draft: TranslationDraft,
    target_root: str | Path,
) -> Path:
    """Publish one validated reviewed draft with provenance sidecars.

    This is the explicit human-controlled acceptance boundary. The function
    never calls an LLM and refuses stale or structurally invalid drafts.
    """

    if draft.status is not TranslationStatus.REVIEWED:
        raise ValueError("only reviewed translation drafts may be published")
    errors = validate_translation(source, draft)
    if errors:
        raise ValueError("translation validation failed: " + "; ".join(errors))

    destination = target_path(source, target_root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(draft.text, encoding="utf-8")
    temporary.replace(destination)

    hash_path = destination.with_suffix(destination.suffix + ".source_hash")
    hash_path.write_text(source.content_hash + "\n", encoding="utf-8")
    provenance_path = destination.with_suffix(destination.suffix + ".provenance.json")
    provenance_path.write_text(
        json.dumps(draft.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return destination
