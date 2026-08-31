"""Drift check — daily self-audit of documentation vs. reality.

Runs once per day (rate-limited internally) and writes docs_10/audits/DRIFT_REPORT.md.
Does not modify code or docs automatically.

Usage:
    python scripts_01/drift_check.py              # run, but no more than once/day
    python scripts_01/drift_check.py --force      # ignore last-run throttle
    python scripts_01/drift_check.py --report -   # print report to stdout
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Known architectural blocks → expected files/directories.
# Used when BUFFY_PROJECT.md status table lists module names instead of paths.
BLOCK_TO_PATHS: dict[str, list[str]] = {
    "Streaming Context": ["scripts_01/context_manager.py", "scripts_01/stream_session.py"],
    "Context Builder": ["scripts_01/context_builder.py"],
    "Orchestrator": ["scripts_01/orchestrator.py"],
    "Capability-based Router": ["core_02/router.py"],
    "Tool Runtime": ["scripts_01/tool_runtime.py"],
    "Knowledge Engine": ["scripts_01/knowledge_engine.py"],
    "Memory Layers": ["scripts_01/memory_engine.py"],
    "Event Bus": ["scripts_01/event_bus.py"],
    "Streaming Context Layer": ["scripts_01/stream_bridge.py", "scripts_01/stream_session.py"],
    "Plugin System": ["plugins_04/"],
}


def _lines_of(path: Path) -> int:
    """Return non-empty source lines in a file; 0 if missing."""
    try:
        with path.open("r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())
    except Exception:
        return 0


def _is_status_row(row: list[str]) -> bool:
    return any(k in " ".join(row) for k in ("Статус", "Status"))


def _parse_markdown_tables(text: str) -> list[list[list[str]]]:
    """Return a list of parsed markdown tables cells."""
    tables: list[list[list[str]]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("|") and line.endswith("|"):
            rows: list[list[str]] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row_text = lines[i].strip()
                if row_text.strip("|-: "):
                    cells = [c.strip() for c in row_text.strip("|").split("|")]
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


def check_buffy_project_status(workspace: Path) -> list[dict[str, Any]]:
    """Compare BUFFY_PROJECT.md status tables with real files/modules."""
    discrepancies: list[dict[str, Any]] = []
    path = workspace / "BUFFY_PROJECT.md"
    if not path.exists():
        return [{"block": "BUFFY_PROJECT.md", "issue": "file missing"}]

    text = path.read_text(encoding="utf-8")
    for table in _parse_markdown_tables(text):
        if not table or not _is_status_row(table[0]):
            continue

        header = [h.lower() for h in table[0]]
        status_idx = next((i for i, h in enumerate(header) if "status" in h), None)
        impl_idx = next((i for i, h in enumerate(header) if h in ("реализация", "implementation", "realization")), None)
        block_idx = next((i for i, h in enumerate(header) if h and "блок" in h), 0)

        if status_idx is None or impl_idx is None:
            continue

        for row in table[1:]:
            if len(row) <= max(status_idx, impl_idx):
                continue
            block = row[block_idx] if block_idx < len(row) else "?"
            status = row[status_idx]
            impl = row[impl_idx]
            emoji = _status_emoji(status)

            # Extract candidate file/dir references from implementation column
            refs = _extract_impl_refs(impl)

            # Fallback: known block names map to real files/directories
            if not refs and block in BLOCK_TO_PATHS:
                refs = BLOCK_TO_PATHS[block]

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
                        })
            elif emoji in ("🟡", "✅"):
                # MVP/Production should have at least one real artifact
                found = False
                for ref in refs:
                    candidate = workspace / ref
                    if candidate.exists():
                        found = True
                        break
                    # Maybe it's a directory
                    if (workspace / ref.split(".")[0]).exists():
                        found = True
                        break
                if not found and refs:
                    discrepancies.append({
                        "block": block,
                        "status_doc": status,
                        "issue": "status claims implementation but none of the referenced files exist",
                        "references": refs,
                    })

    return discrepancies


def _guess_block_paths(workspace: Path, slug: str) -> list[str]:
    """Return candidate file/directory paths for a block name slug."""
    candidates: list[str] = []
    for prefix in ("scripts_01", "core_02", "src_06"):
        candidates.append(f"{prefix}/{slug}.py")
        candidates.append(f"{prefix}/{slug}")
        # plural-ish directory, e.g. "memory_layers" -> "scripts_01/memory"
        if slug.endswith("s"):
            candidates.append(f"{prefix}/{slug[:-1]}")
    return candidates


def _extract_impl_refs(impl: str) -> list[str]:
    """Extract candidate paths from the implementation/description column.

    Falls back to a block-name-to-directory heuristic when no explicit files
    are mentioned.
    """
    refs: list[str] = []
    refs += re.findall(r"[\w/\-)+(?:\.py|\.md)", impl)
    refs += re.findall(r"\b(core_02|scripts_01|src_06|plugins_04|docs_10|freebuff_plugin_03)/[\w/\-)+", impl)
    return refs


def _collect_indexed_sources(workspace: Path) -> list[str]:
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
        # Agent instruction files at workspace root (mirror of seed_knowledge)
        "AGENTS.md",
        "CLAUDE.md",
        "CODY.md",
    }
    docs_dir = workspace / "docs_10"
    if docs_dir.is_dir():
        for doc in docs_dir.rglob("*.md"):
            rel = str(doc.relative_to(workspace))
            if "task_archive" not in rel:
                sources.add(rel)
    return sorted(sources)


# Runtime/cache/archive directories that should not be treated as project docs.
_KNOWLEDGE_IGNORE_DIRS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "context_12",
    "data_13",
    "logs_14",
    "sessions_15",
    "trash_21",
    "venv",
    ".venv",
    "node_modules",
    "build",
    "dist",
    "buffy_history_full.md",
    "buffy_history_index.jsonl",
}

# ADR canonical location and legacy redirects.
_ADR_CANONICAL_DIR = Path("docs_10/engineering-memory/decisions")
_ADR_INDEX = Path("docs_10/decisions/DECISIONS.md")
# Described paths that historically pointed to ADRs but have moved.
_ADR_REDIRECTS: dict[str, tuple[str, ...]] = {
    "decisions": (str(_ADR_CANONICAL_DIR), str(_ADR_INDEX)),
    "docs_10/decisions": (str(_ADR_CANONICAL_DIR), str(_ADR_INDEX)),
}


def _is_legacy_redirect_satisfied(workspace: Path, top_dir: str) -> bool:
    """Return True if a top-level dir is a legacy compat shim pointing at a
    known canonical location.

    Used by ``check_directory_structure`` to silence "exists but not described"
    drift findings for backward-compat shells (e.g. ``freebuff_plugin/`` →
    ``freebuff_plugin_03/`` after the NN-name scheme rename).
    """
    targets = _LEGACY_TOP_LEVEL_REDIRECTS.get(top_dir, ())
    if not targets:
        return False
    return any((workspace / target).is_dir() for target in targets)


# Top-level dirs that exist only as backward-compat forwarders to a canonical
# location and MUST NOT be flagged as undeclared architecture components.
# Add an entry here whenever a rename leaves a thin compat shim behind.
# Values mirror `_ADR_REDIRECTS` style: each target is rendered via
# ``str(Path(...))`` so callers can append nested paths without re-stringifying.
_LEGACY_TOP_LEVEL_REDIRECTS: dict[str, tuple[str, ...]] = {
    # freebuff_plugin/ → freebuff_plugin_03/ (NN-name scheme, v5.25.x)
    "freebuff_plugin": (str(Path("freebuff_plugin_03")),),
}

# Markdown link patterns: [text](target) and ![alt](target)
_MARKDOWN_LINK_RE = re.compile(r"!?\[([^\*)]*)\*]\(([^)]+)\)")
# External URLs, anchors and other non-file targets we cannot/should not resolve.
_EXTERNAL_LINK_PREFIXES = (
    "http://",
    "https://",
    "ftp://",
    "ftps://",
    "mailto:",
    "tel:",
    "data:",
    "#",
    "javascript:",
)


def _is_knowledge_doc(path: Path, workspace: Path) -> bool:
    """Return True if path is a project markdown doc worth indexing."""
    rel = path.relative_to(workspace)
    # Only root-level files or files inside docs_10/
    if len(rel.parts) > 1 and rel.parts[0] != "docs_10":
        return False
    if any(part in _KNOWLEDGE_IGNORE_DIRS for part in rel.parts):
        return False
    rel_str = str(rel)
    if "task_archive" in rel_str:
        return False
    return True


def check_knowledge_index(workspace: Path) -> list[dict[str, Any]]:
    """Find project docs that exist but are not indexed by seed_knowledge."""
    actual = {
        str(p.relative_to(workspace))
        for p in workspace.rglob("*.md")
        if _is_knowledge_doc(p, workspace)
    }
    indexed = set(_collect_indexed_sources(workspace))
    missing = sorted(actual - indexed)

    result: list[dict[str, Any]] = []
    if missing:
        result.append({
            "issue": "unindexed project docs",
            "count": len(missing),
            "files": missing[:20],
        })
    return result


def _extract_code_blocks(text: str) -> list[str]:
    """Extract contents of markdown fenced code blocks.

    Uses line-oriented parsing so opening and closing fences are correctly
    paired regardless of whether a plain '```' line appears as a closing or
    opening fence.
    """
    blocks: list[str] = []
    inside: bool = False
    buffer: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            if inside:
                blocks.append("\n".join(buffer))
                buffer = []
            else:
                buffer = []
            inside = not inside
            continue
        if inside:
            buffer.append(line)
    return blocks


def _extract_tree_paths(text: str) -> list[tuple[str, str]]:
    """Extract file/directory paths from tree-like code blocks in markdown.

    Handles nested directory structures using indentation to reconstruct full
    relative paths. A leading bare root node (e.g. ``freebuff/`` or
    ``docs_10/``) is detected and returned as the second tuple element; child
    paths are returned relative to that root (or to the workspace root when the
    block has no bare root node).

    Returns a list of (path, root) tuples where ``root`` is the bare root node
    name (``""`` when the block starts directly with a branch item).
    """
    results: list[tuple[str, str]] = []
    for block in _extract_code_blocks(text):
        stack: list[tuple[int, str]] = []
        root = ""
        first = True
        for raw_line in block.splitlines():
            # Strip inline comments and trailing whitespace
            line = re.sub(r"\s+#.*$", "", raw_line).rstrip()
            # Skip blank lines and full-line comments without consuming the
            # "first" flag, so a comment header does not hide the root node.
            if not line or line.startswith("#"):
                continue
            # A bare root node is the first line without a branch character
            # and matching a plain path-like token, e.g. "freebuff/" or
            # "docs_10/" (full-line comments/prose are ignored).
            if first and not re.match(r"^[│\s)*(?:├|└)", line) and re.match(r"^[\w.\-/)+/?$", line):
                root = line.strip().rstrip("/")
                first = False
                continue
            first = False
            # Match tree item: indentation prefix + ├/└ + name
            m = re.match(r"^([│\s)*)(?:├|└)──\s*([\w\-.\-/]+)(?:\s+|$)", line)
            if not m:
                continue
            indent_part, name = m.group(1), m.group(2)
            # Standard tree diagrams use 4 characters per nesting level
            # (e.g. "│   " or "    ").
            depth = len(indent_part) // 4
            while stack and stack[-1][0] >= depth:
                stack.pop()
            parent = stack[-1][1] if stack else ""
            full_path = (parent + "/" + name if parent else name).rstrip("/")
            if full_path:
                results.append((full_path, root))
            # Directories keep their trailing slash for nesting children
            if name.endswith("/"):
                stack.append((depth, full_path))
    return results


def _is_external_link(target: str) -> bool:
    """Return True if target is an external URL, anchor-only or mailto link."""
    target_stripped = target.strip()
    return any(target_stripped.startswith(prefix) for prefix in _EXTERNAL_LINK_PREFIXES)


def _strip_code_blocks(text: str) -> str:
    """Replace fenced code blocks with blank lines to avoid false-positive links."""
    lines = text.splitlines()
    result: list[str] = []
    inside = False
    fence: str | None = None
    for line in lines:
        stripped = line.strip()
        if not inside and stripped.startswith("```"):
            inside = True
            fence = stripped
            result.append("")
            continue
        if inside:
            if stripped.startswith("```"):
                inside = False
                fence = None
            result.append("")
            continue
        result.append(line)
    return "\n".join(result)


def _extract_markdown_links(text: str) -> list[tuple[int, str, str]]:
    """Extract markdown links from text.

    Returns a list of (line_number, link_text, target) tuples.
    Content inside fenced code blocks is ignored.
    """
    links: list[tuple[int, str, str]] = []
    cleaned_text = _strip_code_blocks(text)
    for line_no, line in enumerate(cleaned_text.splitlines(), start=1):
        for match in _MARKDOWN_LINK_RE.finditer(line):
            link_text = match.group(1).strip()
            target = match.group(2).strip()
            links.append((line_no, link_text, target))
    return links


def _is_tolerated_historical_tmp_link(md_path: Path, target_clean: str) -> bool:
    """True если ссылка ведёт на исторический `/tmp/...` путь в CHANGELOG/e2e-логах.

    CAN-12 (§5.14 ARCHITECTURAL_DEBT): записи до v5.51.0 ссылались на
    `/tmp/interior_planner_e2e/...` — корректно для своего времени; после
    relocation скриптов в `/storage/...` эти пути больше не существуют,
    но переписывать историю запрещено (CAN-17). Такие ссылки — не broken link,
    а историческая достоверность, и должны толерироваться.
    """
    if not (target_clean.startswith("/tmp/") or target_clean.startswith("tmp/")):
        return False
    file_name = md_path.name
    return file_name == "CHANGELOG.md" or "e2e_logs" in str(md_path) or "task_archive" in str(md_path)


def check_markdown_links(workspace: Path) -> list[dict[str, Any]]:
    """Scan project markdown docs and report broken relative links.

    Checks only files under docs_10/ and root-level .md files.
    External URLs, anchors and mailto links are skipped.
    """
    issues: list[dict[str, Any]] = []
    if not workspace.exists():
        return issues

    markdown_files: list[Path] = []
    docs_dir = workspace / "docs_10"
    if docs_dir.is_dir():
        markdown_files.extend(docs_dir.rglob("*.md"))
    for root_md in workspace.glob("*.md"):
        markdown_files.append(root_md)

    for md_path in markdown_files:
        # Skip runtime_05/cache directories and task archive
        rel_parts = md_path.relative_to(workspace).parts
        if any(part in _KNOWLEDGE_IGNORE_DIRS for part in rel_parts):
            continue
        if "task_archive" in str(md_path):
            continue

        try:
            text = md_path.read_text(encoding="utf-8")
        except Exception:
            continue

        for line_no, link_text, target in _extract_markdown_links(text):
            if _is_external_link(target):
                continue
            if not target:
                continue
            # Resolve relative to the markdown file's directory
            base_dir = md_path.parent
            # Strip fragment and query from target for file existence check
            target_clean = target.split("#")[0].split("?")[0]
            if not target_clean:
                continue
            # CAN-12: исторические /tmp пути в CHANGELOG/e2e-логах — толерируем
            if _is_tolerated_historical_tmp_link(md_path, target_clean):
                continue
            # Absolute links (leading /) resolve against workspace root
            if target_clean.startswith("/"):
                target_path = workspace / target_clean.lstrip("/")
            else:
                target_path = base_dir / target_clean
            try:
                if not target_path.exists():
                    issues.append({
                        "file": str(md_path.relative_to(workspace)),
                        "line": line_no,
                        "text": link_text,
                        "target": target,
                        "issue": "broken relative link",
                    })
            except Exception:
                continue

    return issues


def _is_redirect_satisfied(workspace: Path, described_path: str) -> bool:
    """Return True if a described path has moved to a known canonical location."""
    if described_path not in _ADR_REDIRECTS:
        return False
    return any((workspace / target).exists() for target in _ADR_REDIRECTS[described_path])


def check_directory_structure(workspace: Path) -> list[dict[str, Any]]:
    """Compare directory structure described in BUFFY.md/RULES.md with reality."""
    issues: list[dict[str, Any]] = []
    described_paths: set[str] = set()

    for doc in ("BUFFY.md", "docs_10/core/RULES.md"):
        path = workspace / doc
        if not path.exists():
            continue
        for tree_path, root in _extract_tree_paths(path.read_text(encoding="utf-8")):
            # If the tree is rooted at a real subdirectory (e.g. a diagram
            # describing only the docs_10/ subtree), child paths resolve
            # relative to that root; the root dir itself is also described.
            if root and (workspace / root).is_dir():
                described_paths.add(root)
                described_paths.add(f"{root}/{tree_path}")
            else:
                # Bare root is the workspace itself (e.g. "freebuff/") —
                # children are workspace-relative.
                described_paths.add(tree_path)

    # Check described but missing/empty
    for d in sorted(described_paths):
        p = workspace / d
        if not p.exists():
            if _is_redirect_satisfied(workspace, d):
                # ADR location has been redirected to a canonical location.
                continue
            issues.append({"dir": d, "issue": "described but does not exist"})
        elif p.is_dir() and not any(p.iterdir()):
            if _is_redirect_satisfied(workspace, d):
                # Directory exists but is effectively superseded by canonical ADR location.
                continue
            issues.append({"dir": d, "issue": "described but empty"})

    # Check real top-level dirs not described
    real_dirs = {
        d.name for d in workspace.iterdir()
        if d.is_dir() and not d.name.startswith(".") and d.name not in ("__pycache__",)
    }
    for d in sorted(real_dirs - described_paths):
        # Legacy compat shims (e.g. `freebuff_plugin/` → `freebuff_plugin_03/`)
        # forward to a canonical location and are not architectural components.
        if _is_legacy_redirect_satisfied(workspace, d):
            continue
        issues.append({"dir": d, "issue": "exists but not described in BUFFY.md/RULES.md"})

    return issues


def check_adr_canonical_location(workspace: Path) -> list[dict[str, Any]]:
    """Verify the canonical ADR directory exists and contains ADR files.

    Returns issues if the canonical location is missing, empty, or contains
    no ADR-style files.
    """
    issues: list[dict[str, Any]] = []
    adr_dir = workspace / _ADR_CANONICAL_DIR
    if not adr_dir.exists():
        issues.append({
            "dir": str(_ADR_CANONICAL_DIR),
            "issue": "canonical ADR directory does not exist",
        })
        return issues
    if not adr_dir.is_dir():
        issues.append({
            "dir": str(_ADR_CANONICAL_DIR),
            "issue": "canonical ADR path is not a directory",
        })
        return issues

    adr_files = sorted(adr_dir.glob("ADR_*.md"))
    if not adr_files:
        issues.append({
            "dir": str(_ADR_CANONICAL_DIR),
            "issue": "canonical ADR directory is empty (no ADR_*.md files)",
        })

    # Also ensure the index still exists
    index = workspace / _ADR_INDEX
    if not index.exists():
        issues.append({
            "dir": str(_ADR_INDEX),
            "issue": "ADR index file is missing",
        })

    return issues


def _last_run_path(workspace: Path) -> Path:
    return workspace / "data_13" / ".drift_last_run"


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


def build_report(workspace: Path) -> dict[str, Any]:
    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status_tables": check_buffy_project_status(workspace),
        "knowledge_index": check_knowledge_index(workspace),
        "directory_structure": check_directory_structure(workspace),
        "adr_canonical_location": check_adr_canonical_location(workspace),
        "markdown_links": check_markdown_links(workspace),
    }
    all_issues = (
        report["status_tables"]
        + report["knowledge_index"]
        + report["directory_structure"]
        + report["adr_canonical_location"]
        + report["markdown_links"]
    )
    report["has_drift"] = bool(all_issues)
    return report


def format_report(report: dict[str, Any], workspace: Path) -> str:
    lines: list[str] = [
        "# Drift Report",
        "",
        f"_Generated at: {report['generated_at']}_",
        "",
        "> This report is produced automatically by `scripts_01/drift_check.py`. "
        "> It lists discrepancies between documentation and the actual project state.",
        "",
    ]

    if not report["has_drift"]:
        lines.extend(["## ✅ No drift detected", "", "Documentation matches reality."])
        return "\n".join(lines)

    lines.append("## Status table drift (BUFFY_PROJECT.md vs. code)")
    if not report["status_tables"]:
        lines.append("_No discrepancies found._")
    for item in report["status_tables"]:
        lines.append(f"- **{item['block']}**: {item['issue']}")
        if "file" in item:
            lines.append(f"  - file: `{item['file']}` ({item.get('lines', '?')} lines)")
        if "references" in item:
            lines.append(f"  - missing refs: {', '.join(item['references'])}")

    lines.append("")
    lines.append("## Knowledge index drift (seed_knowledge vs. real docs)")
    if not report["knowledge_index"]:
        lines.append("_No discrepancies found._")
    for item in report["knowledge_index"]:
        lines.append(f"- **{item['issue']}**: {item.get('count', '?')} files")
        for f in item.get("files", []):
            lines.append(f"  - `{f}`")

    lines.append("")
    lines.append("## Directory structure drift (docs vs. filesystem)")
    if not report["directory_structure"]:
        lines.append("_No discrepancies found._")
    for item in report["directory_structure"]:
        lines.append(f"- `{item['dir']}`: {item['issue']}")

    lines.append("")
    lines.append("## ADR canonical location drift")
    if not report["adr_canonical_location"]:
        lines.append("_No discrepancies found._")
    for item in report["adr_canonical_location"]:
        lines.append(f"- `{item['dir']}`: {item['issue']}")

    lines.append("")
    lines.append("## Markdown link drift (broken relative links)")
    if not report["markdown_links"]:
        lines.append("_No discrepancies found._")
    for item in report["markdown_links"]:
        lines.append(
            f"- `{item['file']}:{item['line']}` → `{item['target']}` "
            f"(text: _{item['text']}_)"
        )

    return "\n".join(lines)


def run_drift_check(workspace: Path | str, force: bool = False, write: bool = True) -> dict[str, Any]:
    """Run the daily drift check and optionally write docs_10/audits/DRIFT_REPORT.md."""
    ws = Path(workspace) if isinstance(workspace, str) else workspace
    report = build_report(ws)

    if write:
        try:
            report_path = ws / "docs_10" / "DRIFT_REPORT.md"
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

    if args.report or report["has_drift"]:
        print(format_report(report, workspace))

    return 0 if not report["has_drift"] else 1


if __name__ == "__main__":
    sys.exit(main())
