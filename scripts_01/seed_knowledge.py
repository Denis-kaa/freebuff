#!/usr/bin/env python3
"""
seed_knowledge.py — Наполнение Knowledge Memory из проектных документов.

Сканирует ключевые Markdown-документы проекта Freebuff, сохраняет их
в MemoryLevel.KNOWLEDGE, после чего перестраивает индекс KnowledgeEngine.

Использование:
    python scripts_01/seed_knowledge.py              # проектный workspace
    python scripts_01/seed_knowledge.py --workspace /path/to/freebuff
"""

from __future__ import annotations

import argparse
import hashlib
***REMOVED***
import sys
***REMOVED***
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts_01.memory_engine import MemoryEngine, MemoryLevel, ContentType
from scripts_01.knowledge_engine import KnowledgeEngine


# ═══════════════════════════════════════════════════════════════
# Document sources to seed into Knowledge Memory
# ═══════════════════════════════════════════════════════════════

DEFAULT_DOC_SOURCES = [
    # Core manifests (always indexed, even if no docs_10/ folder exists yet)
    "README.md",
    "BUFFY.md",
    "BUFFY_PROJECT.md",
    "SPEC.md",
    "CHANGELOG.md",
    "TASK.md",
    # Agent instruction files at workspace root (knowledge sources)
    "AGENTS.md",
    "CLAUDE.md",
    "CODY.md",
***REMOVED***

# Patterns that generate noise or are not useful for knowledge retrieval.
# Unix shell-style wildcards are supported via fnmatch.
EXCLUDED_DOC_PATTERNS = [
    "docs_10/audits/AUDIT_*.md",
    "docs_10/ops/TASK_TEMPLATE.md",
***REMOVED***


def _is_excluded(rel_path: str) -> bool:
    """Return True if a doc path should be skipped during auto-discovery."""
    from fnmatch import fnmatch

    for pattern in EXCLUDED_DOC_PATTERNS:
        if fnmatch(rel_path, pattern):
            return True
    return False


def _collect_doc_sources(ws: Path) -> list[str***REMOVED***:
    """Return all Markdown docs that should be seeded into Knowledge Memory.

    Combines core project manifests with every *.md file inside docs_10/,
    except explicitly excluded patterns (AUDIT files, templates, etc.).
    """
    sources: list[str***REMOVED*** = list(DEFAULT_DOC_SOURCES)
    docs_dir = ws / "docs_10"
    if docs_dir.exists() and docs_dir.is_dir():
        for md_file in sorted(docs_dir.rglob("*.md")):
            rel = str(md_file.relative_to(ws))
            if _is_excluded(rel):
                continue
            if rel not in sources:
                sources.append(rel)
    return sources

# Knowledge "best practice" cards that are not tied to a single file
DEFAULT_KNOWLEDGE_CARDS = {
    "best_practices_coding": """# Best practices: coding

- Prefer simple solutions and minimal changes.
- Reuse existing helpers and components before reimplementing.
- Follow existing project conventions.
- Always check tests, mypy, and code-review before finishing.
- Never hardcode secrets; use .env and key pools.
""",
    "best_practices_context": """# Best practices: context management

- Save checkpoints every ~10 messages.
- Use auto-conspect at session end.
- Keep working memory small and focused on the current task.
- Archive old sessions to avoid context bloat.
""",
    "best_practices_llm": """# Best practices: LLM usage

- Route by capability, not by model name.
- Keep prompts under token thresholds; use rollups on CONTEXT_FULL.
- Validate model responses and provide fallbacks.
- Use local models for simple tasks and cloud models for complex ones.
""",
***REMOVED***


# ══════════════════════════════════════════════════════════════
# Seed logic
# ═══════════════════════════════════════════════════════════════

def seed(
    workspace_root: str | Path | None = None,
    event_bus: Any | None = None,
    rebuild: bool | None = None,
    force: bool = False,
) -> int:
    """Seeds Knowledge Memory from project docs and best-practice cards.

    Args:
        workspace_root: path to the freebuff workspace (default: project root)
        event_bus: optional EventBus for auto-indexing (avoids manual rebuild)
        rebuild: whether to rebuild the knowledge index after seeding.
            Defaults to True only when no event_bus is provided.
        force: re-seed even if the content hash hasn't changed

    Returns:
        Number of MemoryEngine entries created/updated.
    """
    ws = Path(workspace_root) if workspace_root else Path(__file__).resolve().parent.parent
    me = MemoryEngine(workspace_root=str(ws), event_bus=event_bus)

    # When an EventBus is injected, auto-indexing will handle incremental
    # updates, so we skip the heavy full rebuild by default.
    if rebuild is None:
        rebuild = event_bus is None

    stored = 0

    # 1. Project docs (core manifests + auto-discovered docs_10/*.md)
    for rel_path in _collect_doc_sources(ws):
        path = ws / rel_path
        if not path.exists():
            continue

        content = path.read_text(encoding="utf-8")
        if not content.strip():
            continue

        key = _safe_key(path.name)
        content_hash = _content_hash(content)

        if not force and _already_seeded(me, key, content_hash):
            continue

        summary = content.strip().splitlines()[0***REMOVED***[:200***REMOVED*** if content.strip() else ""

        me.store(
            MemoryLevel.KNOWLEDGE,
            key=key,
            content=content,
            content_type=ContentType.MARKDOWN,
            summary=summary,
            metadata={
                "source": str(rel_path),
                "doc_type": "markdown",
                "seeded": True,
                "content_hash": content_hash,
            ***REMOVED***,
        )
        stored += 1

    # 2. Best-practice cards
    for key, content in DEFAULT_KNOWLEDGE_CARDS.items():
        content_hash = _content_hash(content)

        if not force and _already_seeded(me, key, content_hash):
            continue

        me.store(
            MemoryLevel.KNOWLEDGE,
            key=key,
            content=content,
            content_type=ContentType.MARKDOWN,
            summary=content.strip().splitlines()[0***REMOVED***[:200***REMOVED***,
            metadata={
                "source": "seed_knowledge.py",
                "doc_type": "markdown",
                "seeded": True,
                "content_hash": content_hash,
            ***REMOVED***,
        )
        stored += 1

    # 3. Rebuild index so everything is searchable (only when no EventBus)
    if rebuild:
        ke = KnowledgeEngine(workspace_root=str(ws))
        ke.rebuild_index()

    return stored


def _safe_key(name: str) -> str:
    """Convert a filename or title into a valid MemoryEngine key."""
    # Split into words on any non-alphanumeric characters and join with underscores
    words = re.split(r"[^a-zA-Z0-9***REMOVED***+", name.strip().lower())
    words = [w for w in words if w***REMOVED***
    key = "_".join(words)
    return key or "untitled"


def _content_hash(content: str) -> str:
    """Return a stable hash for content comparison."""
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def _already_seeded(me: MemoryEngine, key: str, content_hash: str) -> bool:
    """Check whether an identical seeded entry already exists."""
    existing = me.retrieve(MemoryLevel.KNOWLEDGE, key)
    if existing is None:
        return False
    if not existing.metadata.get("seeded"):
        return False
    return existing.metadata.get("content_hash") == content_hash


# ═══════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed Knowledge Memory from project documents and best practices",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python scripts_01/seed_knowledge.py
  python scripts_01/seed_knowledge.py --workspace /path/to/freebuff
  python scripts_01/seed_knowledge.py --no-rebuild
        """,
    )
    parser.add_argument("--workspace", default=None, help="Path to freebuff workspace")
    parser.add_argument("--no-rebuild", action="store_true", help="Don't rebuild knowledge index")
    parser.add_argument("--force", action="store_true", help="Re-seed even if content hashes match")

    args = parser.parse_args()

    count = seed(
        workspace_root=args.workspace,
        rebuild=not args.no_rebuild,
        force=args.force,
    )
    print(f"✅ Seeded {count***REMOVED*** knowledge entries")


if __name__ == "__main__":
    main()
