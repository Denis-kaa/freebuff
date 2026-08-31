from __future__ import annotations

from pathlib import Path

import pytest

from app.localization import (
    ExternalLLMTranslationProvider,
    SourceDocument,
    TranslationDraft,
    TranslationStatus,
    build_manifest,
    draft_is_current,
    iter_source_documents,
    publish_reviewed_translation,
    sha256_text,
    translation_status_rows,
    validate_translation,
    write_translation_draft,
)


def test_extractor_is_deterministic_and_classifies_learner_documents(fixture_root: Path) -> None:
    first = iter_source_documents(fixture_root)
    second = iter_source_documents(fixture_root)

    assert first == second
    assert first
    assert all(document.locale == "en" for document in first)
    assert {document.content_kind for document in first} <= {
        "exercise_instructions",
        "exercise_introduction",
        "exercise_hints",
        "concept_about",
        "concept_introduction",
    }
    manifest = build_manifest(first, target_locale="ru")
    assert manifest["source_locale"] == "en"
    assert manifest["target_locale"] == "ru"
    assert manifest["document_count"] == len(first)


def test_translation_validation_preserves_markdown_contract() -> None:
    source_text = """# Урок\n\nИспользуй `str.format()`:\n\n```python\nprint('hello')\n```\n\n[Документация](https://example.test/python)\n"""
    source = SourceDocument(
        document_id="exercism:concepts/demo/about",
        source_relpath="concepts/demo/about.md",
        content_kind="concept_about",
        locale="en",
        content_hash=sha256_text(source_text),
        text=source_text,
    )
    draft = TranslationDraft(
        document_id=source.document_id,
        source_hash=source.content_hash,
        source_locale="en",
        target_locale="ru",
        text="""# Урок\n\nИспользуй `str.format()`:\n\n```python\nprint('hello')\n```\n\n[Документация](https://example.test/python)\n""",
        provider="test",
        model="fixture",
        status=TranslationStatus.REVIEWED,
    )
    assert validate_translation(source, draft) == ()

    broken = TranslationDraft(
        document_id=source.document_id,
        source_hash=source.content_hash,
        source_locale="en",
        target_locale="ru",
        text="# Урок\n\nУдалена ссылка и code fence.",
        provider="test",
        model="fixture",
        status=TranslationStatus.REVIEWED,
    )
    errors = validate_translation(source, broken)
    assert "Markdown code-fence count changed" in errors
    assert "inline-code tokens changed" in errors
    assert "Markdown link targets changed" in errors


def test_stale_source_hash_is_rejected() -> None:
    source = SourceDocument(
        document_id="exercism:exercises/practice/demo/.docs/instructions",
        source_relpath="exercises/practice/demo/.docs/instructions.md",
        content_kind="exercise_instructions",
        locale="en",
        content_hash=sha256_text("# Original\n"),
        text="# Original\n",
    )
    draft = TranslationDraft(
        document_id=source.document_id,
        source_hash=sha256_text("# Previous\n"),
        source_locale="en",
        target_locale="ru",
        text="# Перевод\n",
        provider="test",
        model="fixture",
        status=TranslationStatus.REVIEWED,
    )
    assert "source_hash is stale" in validate_translation(source, draft)


def test_publish_requires_review_and_writes_provenance(tmp_path: Path) -> None:
    text = "# Original\n"
    source = SourceDocument(
        document_id="exercism:concepts/demo/about",
        source_relpath="concepts/demo/about.md",
        content_kind="concept_about",
        locale="en",
        content_hash=sha256_text(text),
        text=text,
    )
    draft = TranslationDraft(
        document_id=source.document_id,
        source_hash=source.content_hash,
        source_locale="en",
        target_locale="ru",
        text="# Перевод\n",
        provider="test",
        model="fixture",
        status=TranslationStatus.REVIEWED,
    )
    destination = publish_reviewed_translation(source, draft, tmp_path)
    assert destination.read_text(encoding="utf-8") == draft.text
    assert destination.with_suffix(".md.source_hash").read_text(encoding="utf-8").strip() == source.content_hash
    assert destination.with_suffix(".md.provenance.json").exists()

    draft_status = TranslationDraft(
        document_id=source.document_id,
        source_hash=source.content_hash,
        source_locale="en",
        target_locale="ru",
        text="# Черновик\n",
        provider="test",
        model="fixture",
        status=TranslationStatus.DRAFT,
    )
    with pytest.raises(ValueError, match="only reviewed"):
        publish_reviewed_translation(source, draft_status, tmp_path)


def test_draft_storage_never_marks_live_projection_reviewed(tmp_path: Path) -> None:
    text = "# Original\n\nUse `str.format()`.\n"
    source = SourceDocument(
        document_id="exercism:concepts/demo/about",
        source_relpath="concepts/demo/about.md",
        content_kind="concept_about",
        locale="en",
        content_hash=sha256_text(text),
        text=text,
    )
    draft = TranslationDraft(
        document_id=source.document_id,
        source_hash=source.content_hash,
        source_locale="en",
        target_locale="ru",
        text="# Перевод\n\nИспользуй `str.format()`.\n",
        provider="gemini",
        model="gemini-2.5-flash",
        status=TranslationStatus.DRAFT,
    )
    destination = write_translation_draft(source, draft, tmp_path / "drafts")
    assert destination.read_text(encoding="utf-8") == draft.text
    assert destination.name == "about.md.draft.md"
    assert not destination.with_suffix(".md.source_hash").exists()
    assert destination.with_name("about.md.draft.json").exists()
    assert draft_is_current(source, tmp_path / "drafts")

    changed_source = SourceDocument(
        document_id=source.document_id,
        source_relpath=source.source_relpath,
        content_kind=source.content_kind,
        locale="en",
        content_hash=sha256_text("# Changed\n"),
        text="# Changed\n",
    )
    assert not draft_is_current(changed_source, tmp_path / "drafts")


def test_translation_status_rows_detect_missing_and_stale(tmp_path: Path) -> None:
    source = SourceDocument(
        document_id="exercism:concepts/demo/about",
        source_relpath="concepts/demo/about.md",
        content_kind="concept_about",
        locale="en",
        content_hash=sha256_text("# Original\n"),
        text="# Original\n",
    )
    rows = translation_status_rows((source,), tmp_path)
    assert rows[0].status is TranslationStatus.DRAFT

    destination = tmp_path / source.source_relpath
    destination.parent.mkdir(parents=True)
    destination.write_text("# Old\n", encoding="utf-8")
    destination.with_suffix(".md.source_hash").write_text("stale\n", encoding="utf-8")
    rows = translation_status_rows((source,), tmp_path)
    assert rows[0].status is TranslationStatus.STALE


def test_external_llm_provider_fails_closed_without_configuration(fixture_root: Path) -> None:
    document = iter_source_documents(fixture_root)[0]
    provider = ExternalLLMTranslationProvider()
    with pytest.raises(RuntimeError, match="not configured"):
        provider.translate((document,), "ru")
