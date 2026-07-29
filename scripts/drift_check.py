"""Drift check — daily self-audit of documentation vs. reality.

Runs once per day (rate-limited internally) and writes docs/audits/DRIFT_REPORT.md.
Does not modify code or docs automatically.

Usage:
    python scripts/drift_check.py              # run, but no more than once/day
    python scripts/drift_check.py --force      # ignore last-run throttle
    python scripts/drift_check.py --report -   # print report to stdout
"""
from __future__ import annotations

import argparse
import os
***REMOVED***
import sys
from datetime import datetime, timezone
***REMOVED***
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Known architectural blocks → expected files/directories.
# Used when BUFFY_PROJECT.md status table lists module names instead of paths.
BLOCK_TO_PATHS: dict[str, list[str***REMOVED******REMOVED*** = {
    "Streaming Context": ["scripts/context_manager.py", "scripts/stream_session.py"***REMOVED***,
    "Context Builder": ["scripts/context_builder.py"***REMOVED***,
    "Orchestrator": ["scripts/orchestrator.py"***REMOVED***,
    "Capability-based Router": ["core/router.py"***REMOVED***,
    "Tool Runtime": ["scripts/tool_runtime.py"***REMOVED***,
    "Knowledge Engine": ["scripts/knowledge_engine.py"***REMOVED***,
    "Memory Layers": ["scripts/memory_engine.py"***REMOVED***,
    "Event Bus": ["scripts/event_bus.py"***REMOVED***,
    "Streaming Context Layer": ["scripts/stream_bridge.py", "scripts/stream_session.py"***REMOVED***,
    "Plugin System": ["plugins/"***REMOVED***,
***REMOVED***


def _lines_of(path: Path) -> int:
    """Return non-empty source lines in a file; 0 if missing."""
    try:
        with path.open("r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())
    except Exception:
        return 0


def _is_status_row(row: list[str***REMOVED***) -> bool:
    return any(k in " ".join(row) for k in ("Статус", "Status"))


def _parse_markdown_tables(text: str) -> list[list[list[str***REMOVED******REMOVED******REMOVED***:
    """Return a list of parsed markdown tables cells."""
    tables: list[list[list[str***REMOVED******REMOVED******REMOVED*** = [***REMOVED***
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i***REMOVED***.strip()
        if line.startswith("|") and line.endswith("|"):
            rows: list[list[str***REMOVED******REMOVED*** = [***REMOVED***
            while i < len(lines) and lines[i***REMOVED***.strip().startswith("|"):
                row_text = lines[i***REMOVED***.strip()
                if row_text.strip("|-: "):
                    cells = [c.strip() for c in row_text.strip("|").split("|")***REMOVED***
                    rows.append(cells)
                i += 1
            if rows:
                tables.append(rows)
        else:
            i += 1
    return tables


def _status_emoji(status: str) -> str:
    status = status.lower()
    if any(k in status for k in ("🔴", "не начат", "not started")) or status.strip() == "план":
        return "🔴"
    if any(k in status for k in ("🟡", "mvp", "каркас", "в разработке", "сейчас")):
        return "🟡"
    if any(k in status for k in ("✅", "production", "готов", "done", "ready")):
        return "✅"
    return "❓"


def check_buffy_project_status(workspace: Path) -> list[dict[str, Any***REMOVED******REMOVED***:
    """Compare BUFFY_PROJECT.md status tables with real files/modules."""
    discrepancies: list[dict[str, Any***REMOVED******REMOVED*** = [***REMOVED***
    path = workspace / "BUFFY_PROJECT.md"
    if not path.exists():
        return [{"block": "BUFFY_PROJECT.md", "issue": "file missing"***REMOVED******REMOVED***

    text = path.read_text(encoding="utf-8")
    for table in _parse_markdown_tables(text):
        if not table or not _is_status_row(table[0***REMOVED***):
            continue

        header = [h.lower() for h in table[0***REMOVED******REMOVED***
        status_idx = next((i for i, h in enumerate(header) if "status" in h), None)
        impl_idx = next((i for i, h in enumerate(header) if h in ("реализация", "implementation", "realization")), None)
        block_idx = next((i for i, h in enumerate(header) if h and "блок" in h), 0)

        if status_idx is None or impl_idx is None:
            continue

        for row in table[1:***REMOVED***:
            if len(row) <= max(status_idx, impl_idx):
                continue
            block = row[block_idx***REMOVED*** if block_idx < len(row) else "?"
            status = row[status_idx***REMOVED***
            impl = row[impl_idx***REMOVED***
            emoji = _status_emoji(status)

            # Extract candidate file/dir references from implementation column
            refs = _extract_impl_refs(impl)

            # Fallback: known block names map to real files/directories
            if not refs and block in BLOCK_TO_PATHS:
                refs = BLOCK_TO_PATHS[block***REMOVED***

            # Last-resort heuristic for unknown blocks
            if not refs:
                slug = re.sub(r"\s+", "_", block.lower())
                refs = _guess_block_paths(workspace, slug)

            if emoji == "🔴":
                # Not started should have no substantial code
                for ref in refs:
                    candidate = workspace / ref
                    if candidate.exists() and _lines_of(candidate) > 30:
                        discrepancies.append({
                            "block": block,
                            "status_doc": status,
                            "issue": "marked not started but has substantial code",
                            "file": str(candidate.relative_to(workspace)),
                            "lines": _lines_of(candidate),
                        ***REMOVED***)
            elif emoji in ("🟡", "✅"):
                # MVP/Production should have at least one real artifact
                found = False
                for ref in refs:
                    candidate = workspace / ref
                    if candidate.exists():
                        found = True
                        break
                    # Maybe it's a directory
                    if (workspace / ref.split(".")[0***REMOVED***).exists():
                        found = True
                        break
                if not found and refs:
                    discrepancies.append({
                        "block": block,
                        "status_doc": status,
                        "issue": "status claims implementation but none of the referenced files exist",
                        "references": refs,
                    ***REMOVED***)

    return discrepancies


def _guess_block_paths(workspace: Path, slug: str) -> list[str***REMOVED***:
    """Return candidate file/directory paths for a block name slug."""
    candidates: list[str***REMOVED*** = [***REMOVED***
    for prefix in ("scripts", "core", "src"):
        candidates.append(f"{prefix***REMOVED***/{slug***REMOVED***.py")
        candidates.append(f"{prefix***REMOVED***/{slug***REMOVED***")
        # plural-ish directory, e.g. "memory_layers" -> "scripts/memory"
        if slug.endswith("s"):
            candidates.append(f"{prefix***REMOVED***/{slug[:-1***REMOVED******REMOVED***")
    return candidates


def _extract_impl_refs(impl: str) -> list[str***REMOVED***:
    """Extract candidate paths from the implementation/description column.

    Falls back to a block-name-to-directory heuristic when no explicit files
    are mentioned.
    """
    refs: list[str***REMOVED*** = [***REMOVED***
    refs += re.findall(r"[\w/\-***REMOVED***+(?:\.py|\.md)", impl)
    refs += re.findall(r"\b(core|scripts|src|plugins|docs)/[\w/\-***REMOVED***+", impl)
    return refs


def _collect_indexed_sources(workspace: Path) -> list[str***REMOVED***:
    """Return the list of docs seed_knowledge would index.

    Mirrors the public logic of `scripts.seed_knowledge` without importing a
    private helper, so drift_check stays decoupled from implementation details.
    """
    sources = {
        "README.md",
        "BUFFY.md",
        "BUFFY_PROJECT.md",
        "SPEC.md",
        "CHANGELOG.md",
        "TASK.md",
    ***REMOVED***
    docs_dir = workspace / "docs"
    if docs_dir.is_dir():
        for doc in docs_dir.rglob("*.md"):
            rel = str(doc.relative_to(workspace))
            if "task_archive" not in rel:
                sources.add(rel)
    return sorted(sources)


# Runtime/cache directories that should not be treated as project docs.
_KNOWLEDGE_IGNORE_DIRS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "context",
    "data",
    "logs",
    "sessions",
    "venv",
    ".venv",
    "node_modules",
    "build",
    "dist",
***REMOVED***


def _is_knowledge_doc(path: Path, workspace: Path) -> bool:
    """Return True if path is a project markdown doc worth indexing."""
    rel = path.relative_to(workspace)
    # Only root-level files or files inside docs/
    if len(rel.parts) > 1 and rel.parts[0***REMOVED*** != "docs":
        return False
    if any(part in _KNOWLEDGE_IGNORE_DIRS for part in rel.parts):
        return False
    rel_str = str(rel)
    if "task_archive" in rel_str:
        return False
    return True


def check_knowledge_index(workspace: Path) -> list[dict[str, Any***REMOVED******REMOVED***:
    """Find project docs that exist but are not indexed by seed_knowledge."""
    actual = {
        str(p.relative_to(workspace))
        for p in workspace.rglob("*.md")
        if _is_knowledge_doc(p, workspace)
    ***REMOVED***
    indexed = set(_collect_indexed_sources(workspace))
    missing = sorted(actual - indexed)

    result: list[dict[str, Any***REMOVED******REMOVED*** = [***REMOVED***
    if missing:
        result.append({
            "issue": "unindexed project docs",
            "count": len(missing),
            "files": missing[:20***REMOVED***,
        ***REMOVED***)
    return result


def _extract_code_blocks(text: str) -> list[str***REMOVED***:
    """Extract contents of markdown fenced code blocks.

    Uses line-oriented parsing so opening and closing fences are correctly
    paired regardless of whether a plain '```' line appears as a closing or
    opening fence.
    """
    blocks: list[str***REMOVED*** = [***REMOVED***
    inside: bool = False
    buffer: list[str***REMOVED*** = [***REMOVED***
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            if inside:
                blocks.append("\n".join(buffer))
                buffer = [***REMOVED***
            else:
                buffer = [***REMOVED***
            inside = not inside
            continue
        if inside:
            buffer.append(line)
    return blocks


def _extract_tree_paths(text: str) -> list[tuple[str, str***REMOVED******REMOVED***:
    """Extract file/directory paths from tree-like code blocks in markdown.

    Handles nested directory structures using indentation to reconstruct full
    relative paths. Returns a list of (path, source_label) tuples.
    """
    paths: list[tuple[str, str***REMOVED******REMOVED*** = [***REMOVED***
    for block in _extract_code_blocks(text):
        stack: list[tuple[int, str***REMOVED******REMOVED*** = [***REMOVED***
        for raw_line in block.splitlines():
            # Strip inline comments and trailing whitespace
            line = re.sub(r"\s+#.*$", "", raw_line).rstrip()
            # Match tree item: indentation prefix + ├/└ + name
            m = re.match(r"^([│\s***REMOVED****)(?:├|└)──\s*([\w\-.\-/***REMOVED***+)(?:\s+|$)", line)
            if not m:
                continue
            indent_part, name = m.group(1), m.group(2)
            # Standard tree diagrams use 4 characters per nesting level
            # (e.g. "│   " or "    ").
            depth = len(indent_part) // 4
            while stack and stack[-1***REMOVED***[0***REMOVED*** >= depth:
                stack.pop()
            parent = stack[-1***REMOVED***[1***REMOVED*** if stack else ""
            full_path = (parent + "/" + name if parent else name).rstrip("/")
            if full_path:
                paths.append((full_path, "tree"))
            # Directories keep their trailing slash for nesting children
            if name.endswith("/"):
                stack.append((depth, full_path))
    return paths


def check_directory_structure(workspace: Path) -> list[dict[str, Any***REMOVED******REMOVED***:
    """Compare directory structure described in BUFFY.md/RULES.md with reality."""
    issues: list[dict[str, Any***REMOVED******REMOVED*** = [***REMOVED***
    described_paths: set[str***REMOVED*** = set()

    for doc in ("BUFFY.md", "docs/core/RULES.md"):
        path = workspace / doc
        if not path.exists():
            continue
        for tree_path, _ in _extract_tree_paths(path.read_text(encoding="utf-8")):
            described_paths.add(tree_path)

    # Check described but missing/empty
    for d in sorted(described_paths):
        p = workspace / d
        if not p.exists():
            issues.append({"dir": d, "issue": "described but does not exist"***REMOVED***)
        elif p.is_dir() and not any(p.iterdir()):
            issues.append({"dir": d, "issue": "described but empty"***REMOVED***)

    # Check real top-level dirs not described
    real_dirs = {
        d.name for d in workspace.iterdir()
        if d.is_dir() and not d.name.startswith(".") and d.name not in ("__pycache__",)
    ***REMOVED***
    for d in sorted(real_dirs - described_paths):
        issues.append({"dir": d, "issue": "exists but not described in BUFFY.md/RULES.md"***REMOVED***)

    return issues


def _last_run_path(workspace: Path) -> Path:
    return workspace / "data" / ".drift_last_run"


def _should_run(workspace: Path, force: bool = False) -> bool:
    if force:
        return True
    last_run = _last_run_path(workspace)
    if not last_run.exists():
        return True
    try:
        last_date = last_run.read_text(encoding="utf-8").strip()
        return last_date != datetime.now(timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return True


def _record_run(workspace: Path) -> None:
    try:
        _last_run_path(workspace).write_text(
            datetime.now(timezone.utc).strftime("%Y-%m-%d"), encoding="utf-8"
        )
    except Exception:
        pass


def build_report(workspace: Path) -> dict[str, Any***REMOVED***:
    report: dict[str, Any***REMOVED*** = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status_tables": check_buffy_project_status(workspace),
        "knowledge_index": check_knowledge_index(workspace),
        "directory_structure": check_directory_structure(workspace),
    ***REMOVED***
    all_issues = report["status_tables"***REMOVED*** + report["knowledge_index"***REMOVED*** + report["directory_structure"***REMOVED***
    report["has_drift"***REMOVED*** = bool(all_issues)
    return report


def format_report(report: dict[str, Any***REMOVED***, workspace: Path) -> str:
    lines: list[str***REMOVED*** = [
        "# Drift Report",
        "",
        f"_Generated at: {report['generated_at'***REMOVED******REMOVED***_",
        "",
        "> This report is produced automatically by `scripts/drift_check.py`. "
        "> It lists discrepancies between documentation and the actual project state.",
        "",
    ***REMOVED***

    if not report["has_drift"***REMOVED***:
        lines.extend(["## ✅ No drift detected", "", "Documentation matches reality."***REMOVED***)
        return "\n".join(lines)

    lines.append("## Status table drift (BUFFY_PROJECT.md vs. code)")
    if not report["status_tables"***REMOVED***:
        lines.append("_No discrepancies found._")
    for item in report["status_tables"***REMOVED***:
        lines.append(f"- **{item['block'***REMOVED******REMOVED*****: {item['issue'***REMOVED******REMOVED***")
        if "file" in item:
            lines.append(f"  - file: `{item['file'***REMOVED******REMOVED***` ({item.get('lines', '?')***REMOVED*** lines)")
        if "references" in item:
            lines.append(f"  - missing refs: {', '.join(item['references'***REMOVED***)***REMOVED***")

    lines.append("")
    lines.append("## Knowledge index drift (seed_knowledge vs. real docs)")
    if not report["knowledge_index"***REMOVED***:
        lines.append("_No discrepancies found._")
    for item in report["knowledge_index"***REMOVED***:
        lines.append(f"- **{item['issue'***REMOVED******REMOVED*****: {item.get('count', '?')***REMOVED*** files")
        for f in item.get("files", [***REMOVED***):
            lines.append(f"  - `{f***REMOVED***`")

    lines.append("")
    lines.append("## Directory structure drift (docs vs. filesystem)")
    if not report["directory_structure"***REMOVED***:
        lines.append("_No discrepancies found._")
    for item in report["directory_structure"***REMOVED***:
        lines.append(f"- `{item['dir'***REMOVED******REMOVED***`: {item['issue'***REMOVED******REMOVED***")

    return "\n".join(lines)


def run_drift_check(workspace: Path | str, force: bool = False, write: bool = True) -> dict[str, Any***REMOVED***:
    """Run the daily drift check and optionally write docs/audits/DRIFT_REPORT.md."""
    ws = Path(workspace) if isinstance(workspace, str) else workspace
    report = build_report(ws)

    if write:
        try:
            report_path = ws / "docs" / "DRIFT_REPORT.md"
            report_path.write_text(format_report(report, ws), encoding="utf-8")
        except Exception:
            pass

    _record_run(ws)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Daily drift check for Freebuff")
    parser.add_argument("--workspace", default=str(PROJECT_ROOT), help="Path to freebuff workspace")
    parser.add_argument("--force", action="store_true", help="Run even if already ran today")
    parser.add_argument("--report", action="store_true", help="Print report to stdout")
    args = parser.parse_args()

    workspace = Path(args.workspace)

    if not _should_run(workspace, force=args.force):
        print("Drift check already ran today. Use --force to override.")
        return 0

    report = run_drift_check(workspace, force=args.force)

    if args.report or report["has_drift"***REMOVED***:
        print(format_report(report, workspace))

    return 0 if not report["has_drift"***REMOVED*** else 1


if __name__ == "__main__":
    sys.exit(main())
