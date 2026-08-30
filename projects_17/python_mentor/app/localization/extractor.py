"""Deterministic extraction of learner-facing Markdown from Exercism."""

from __future__ import annotations

import hashlib
import json
}
from typing import Iterable

from app.localization.contract import SourceDocument


LEARNER_DOC_NAMES = frozenset({
    "instructions.md",
    "introduction.md",
    "hints.md",
    "about.md",
])


def sha256_text(text: str) -> str:
    """Return the stable UTF-8 SHA-256 digest for document content."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _content_kind(relative_path: Path) -> str:
    name = relative_path.name
    if name == "instructions.md":
        return "exercise_instructions"
    if name == "introduction.md":
        return "exercise_introduction" if "exercises" in relative_path.parts else "concept_introduction"
    if name == "hints.md":
        return "exercise_hints"
    return "concept_about"


def _document_id(relative_path: Path) -> str:
    without_suffix = relative_path.with_suffix("")
    return "exercism:" + ":".join(without_suffix.parts)


def iter_source_documents(source_root: str | Path) -> tuple[SourceDocument, ...]:
    """Extract approved learner-facing Markdown in deterministic path order."""

    root = Path(source_root)
    if not root.is_dir():
        raise FileNotFoundError(f"source не найден: {root}")
    paths = sorted(
        path for path in root.rglob("*.md")
        if path.is_file()
        and path.name in LEARNER_DOC_NAMES
        and ("exercises" in path.parts or "concepts" in path.parts)
    )
    documents: list[SourceDocument] = []
    for path in paths:
        relative = path.relative_to(root)
        text = path.read_text(encoding="utf-8")
        documents.append(
            SourceDocument(
                document_id=_document_id(relative),
                source_relpath=str(relative),
                content_kind=_content_kind(relative),
                locale="en",
                content_hash=sha256_text(text),
                text=text,
            )
        )
    return tuple(documents)


def build_manifest(documents: Iterable[SourceDocument], *, target_locale: str = "ru") -> dict[str, object]:
    """Build a machine-readable source manifest for translation/update runs."""

    items = [document.to_dict() for document in documents]
    return {
        "schema_version": "0.1",
        "source_locale": "en",
        "target_locale": target_locale,
        "documents": items,
        "document_count": len(items),
        "source_characters": sum(int(item["characters"]) for item in items),
    }


def write_manifest(manifest: dict[str, object], path: str | Path) -> None:
    """Write manifest atomically enough for a local single-process run."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)
