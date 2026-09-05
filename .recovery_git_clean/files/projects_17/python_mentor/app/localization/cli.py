"""CLI operations for the localization projection."""

from __future__ import annotations

import argparse
import json
import sys
***REMOVED***

from app.localization import ExternalLLMTranslationProvider, GeminiKeyPool
from app.localization.contract import TranslationStatus
from app.localization.extractor import iter_source_documents
from app.localization.gemini import DEFAULT_MODEL, GeminiTranslationProvider
from app.localization.provider import TranslationProvider
from app.localization.workflow import (
    draft_is_current,
    scan_source,
    translation_status_rows,
    write_translation_draft,
)

DEFAULT_SOURCE = "data/exercism_src"
DEFAULT_MANIFEST = "data/localization/source_manifest.json"
DEFAULT_TARGET = "data/localization/ru"
DEFAULT_DRAFT_ROOT = "data/localization/drafts/ru"
DEFAULT_KEYS = str(Path(__file__).resolve().parents[4***REMOVED*** / ".keys" / "gemini_active.keys")


def add_localization_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser***REMOVED***) -> None:
    """Register ``localize`` CLI commands on the main app parser."""

    localize = subparsers.add_parser("localize", help="локализация learner-facing контента")
    commands = localize.add_subparsers(dest="localize_cmd", required=True)

    scan = commands.add_parser("scan", help="построить source manifest")
    scan.add_argument("--source", default=DEFAULT_SOURCE)
    scan.add_argument("--manifest", default=DEFAULT_MANIFEST)
    scan.add_argument("--target-locale", default="ru")
    scan.set_defaults(localize_func=_scan)

    status = commands.add_parser("status", help="показать missing/stale/reviewed переводы")
    status.add_argument("--source", default=DEFAULT_SOURCE)
    status.add_argument("--target", default=DEFAULT_TARGET)
    status.set_defaults(localize_func=_status)

    update = commands.add_parser("update", help="создать translation drafts через внешний provider")
    update.add_argument("--provider", choices=["external_llm", "gemini"***REMOVED***, default="external_llm")
    update.add_argument("--source", default=DEFAULT_SOURCE)
    update.add_argument("--target-locale", default="ru")
    update.add_argument("--keys", default=DEFAULT_KEYS, help="ignored local Gemini key file")
    update.add_argument("--model", default=DEFAULT_MODEL)
    update.add_argument("--draft-dir", default=DEFAULT_DRAFT_ROOT)
    update.add_argument("--limit", type=int, default=1, help="number of missing/stale documents (default: 1)")
    update.set_defaults(localize_func=_update)


def run_localization(args: argparse.Namespace) -> int:
    """Execute the selected localization subcommand with CLI-safe errors."""

    try:
        return int(args.localize_func(args))
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"localization error: {exc***REMOVED***", file=sys.stderr)
        return 2


def _scan(args: argparse.Namespace) -> int:
    manifest = scan_source(args.source, args.manifest, target_locale=args.target_locale)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


def _status(args: argparse.Namespace) -> int:
    documents = iter_source_documents(args.source)
    rows = translation_status_rows(documents, args.target)
    counts: dict[str, int***REMOVED*** = {***REMOVED***
    for row in rows:
        counts[row.status.value***REMOVED*** = counts.get(row.status.value, 0) + 1
    print(json.dumps({"counts": counts, "documents": [row.to_dict() for row in rows***REMOVED******REMOVED***, ensure_ascii=False, indent=2))
    return 0


def _update(args: argparse.Namespace) -> int:
    if args.limit < 1:
        raise ValueError("--limit must be at least 1")

    documents = iter_source_documents(args.source)
    rows = translation_status_rows(documents, DEFAULT_TARGET)
    pending_ids = {
        row.document_id for row in rows if row.status is not TranslationStatus.REVIEWED
    ***REMOVED***
    selected = tuple(
        document
        for document in documents
        if document.document_id in pending_ids
        and not draft_is_current(document, args.draft_dir)
    )[: args.limit***REMOVED***
    if not selected:
        print(json.dumps({"provider": args.provider, "drafts": [***REMOVED***, "message": "no missing/stale documents"***REMOVED***, ensure_ascii=False))
        return 0

    pool: GeminiKeyPool | None
    provider: TranslationProvider
    if args.provider == "gemini":
        pool = GeminiKeyPool(active_file=args.keys)
        provider = GeminiTranslationProvider(pool, model=args.model)
    else:
        pool = None
        provider = ExternalLLMTranslationProvider()

    drafts = provider.translate(selected, args.target_locale)
    written = [
        str(write_translation_draft(source, draft, args.draft_dir))
        for source, draft in zip(selected, drafts)
    ***REMOVED***
    result = {
        "provider": args.provider,
        "model": args.model if args.provider == "gemini" else None,
        "key_count": pool.key_count if pool is not None else None,
        "draft_count": len(written),
        "drafts": written,
        "published": False,
    ***REMOVED***
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
