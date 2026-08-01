#!/usr/bin/env python3
"""Buffy Auto-Doc — auto-trigger documentation maintenance helper.

Scans the current git working tree (or a provided diff) and produces a checklist
of documentation updates required by the project rules in docs_10/core/RULES.md.

Usage:
    python scripts_01/buffy_autodoc.py
    python scripts_01/buffy_autodoc.py --apply  # attempt light updates
"""

from __future__ import annotations

import argparse
import os
import subprocess
from dataclasses import dataclass, field
***REMOVED***
from typing import Iterable, List, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1***REMOVED***
DOCS_DIR = REPO_ROOT / "docs_10"


@dataclass
class Trigger:
    name: str
    doc_files: Sequence[str***REMOVED***
    file_patterns: Sequence[str***REMOVED*** = field(default_factory=tuple)
    file_suffixes: Sequence[str***REMOVED*** = field(default_factory=tuple)
    always: bool = False
    severity: str = "warn"  # "warn" or "block" (strict mode only fails on "block")

    def matches(self, changed_path: str) -> bool:
        if self.always:
            return True
        lower = changed_path.lower()
        for pat in self.file_patterns:
            if pat in lower:
                return True
        for suffix in self.file_suffixes:
            if lower.endswith(suffix):
                return True
        return False


TRIGGERS: Tuple[Trigger, ...***REMOVED*** = (
    Trigger("New task", ["TASK.md"***REMOVED***, always=True, severity="warn"),
    Trigger("Code change", ["CHANGELOG.md", "TASK.md"***REMOVED***, file_suffixes=(".py", ".sh", ".js", ".ts", ".html", ".css"), severity="block"),
    Trigger("Architecture change", ["docs_10/core/ARCHITECTURE_3.0.md"***REMOVED***, file_patterns=["src_06/", "scripts_01/", "freebuff_cli.py"***REMOVED***),
    Trigger("README feature", ["README.md"***REMOVED***, file_patterns=["freebuff_cli.py", "scripts_01/", "src_06/"***REMOVED***),
    Trigger("Architectural decision", ["docs_10/decisions/DECISIONS.md", "docs_10/engineering-memory/decisions/"***REMOVED***, file_patterns=["decision", "adr", "architecture"***REMOVED***),
    Trigger("Research / spike", ["docs_10/decisions/IDEAS.md"***REMOVED***, file_patterns=["research", "spike", "experiment"***REMOVED***),
    Trigger("Bug fix", ["docs_10/ops/TROUBLESHOOTING.md"***REMOVED***, file_patterns=["bug", "fix", "error"***REMOVED***),
    Trigger("API change", ["docs_10/ops/API.md"***REMOVED***, file_patterns=["api", "mcp_server", "endpoint"***REMOVED***),
    Trigger("Worker / tool", ["docs_10/projects_meta/WORKERS.md"***REMOVED***, file_patterns=["workers", "tool_runtime"***REMOVED***),
    Trigger("Documentation change", ["docs_10/core/RULES.md"***REMOVED***, file_suffixes=(".md",)),
)


def run_git_diff(*, cached: bool = False, base: str = "HEAD") -> str:
    cmd = ["git", "diff", "--name-status"***REMOVED***
    if cached:
        cmd.append("--cached")
    if base:
        cmd.append(base)
    try:
        return subprocess.check_output(cmd, cwd=REPO_ROOT, text=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def parse_changed_files(diff_text: str) -> List[str***REMOVED***:
    files: List[str***REMOVED*** = [***REMOVED***
    for line in diff_text.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split(maxsplit=1)
        if len(parts) == 2:
            files.append(parts[1***REMOVED***.strip())
        elif len(parts) == 1:
            files.append(parts[0***REMOVED***.strip())
    return files


def determine_triggers(changed_files: Sequence[str***REMOVED***) -> List[Tuple[Trigger, List[str***REMOVED******REMOVED******REMOVED***:
    results: List[Tuple[Trigger, List[str***REMOVED******REMOVED******REMOVED*** = [***REMOVED***
    for trigger in TRIGGERS:
        matched = [f for f in changed_files if trigger.matches(f)***REMOVED***
        if matched or trigger.always:
            results.append((trigger, matched))
    return results


def build_checklist(results: Sequence[Tuple[Trigger, List[str***REMOVED******REMOVED******REMOVED***) -> str:
    lines = ["# Auto-Doc Checklist\n", f"Project root: {REPO_ROOT***REMOVED***\n"***REMOVED***
    for trigger, matched in results:
        lines.append(f"\n## {trigger.name***REMOVED***\n")
        lines.append(f"  Required docs: {', '.join(trigger.doc_files)***REMOVED***\n")
        if matched:
            lines.append("  Matched files:\n")
            for f in matched[:10***REMOVED***:
                lines.append(f"    - {f***REMOVED***\n")
            if len(matched) > 10:
                lines.append(f"    ... and {len(matched) - 10***REMOVED*** more\n")
    return "".join(lines)


def touch_missing_docs(results: Sequence[Tuple[Trigger, List[str***REMOVED******REMOVED******REMOVED***) -> List[str***REMOVED***:
    created: List[str***REMOVED*** = [***REMOVED***
    for trigger, _ in results:
        for doc in trigger.doc_files:
            path = REPO_ROOT / doc
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"# {path.stem***REMOVED***\n\nAuto-created by buffy_autodoc.py\n")
                created.append(str(path))
    return created


def _docs_only_commit(changed: Sequence[str***REMOVED***) -> bool:
    """Return True if every changed file is a Markdown document."""
    return all(Path(f).suffix.lower() == ".md" for f in changed)


def main(argv: Sequence[str***REMOVED*** | None = None) -> int:
    parser = argparse.ArgumentParser(description="Buffy Auto-Doc trigger helper")
    parser.add_argument("--cached", action="store_true", help="use staged diff")
    parser.add_argument("--apply", action="store_true", help="create missing doc stubs")
    parser.add_argument("--strict", action="store_true", help="exit non-zero if required docs are missing from the diff")
    parser.add_argument("--input", help="path to a diff file to read instead of git diff")
    args = parser.parse_args(argv)

    if args.input:
        diff_text = Path(args.input).read_text()
    else:
        diff_text = run_git_diff(cached=args.cached)

    changed = parse_changed_files(diff_text)
    if not changed:
        print("No changed files detected. Nothing to do.")
        return 0

    results = determine_triggers(changed)
    print(build_checklist(results))

    if args.strict:
        # Docs-only commits shouldn't fail because of documentation triggers.
        if _docs_only_commit(changed):
            print("\nDocs-only commit detected. Passing strict checks.")
            return 0

        blockers: List[Tuple[str, Sequence[str***REMOVED******REMOVED******REMOVED*** = [***REMOVED***
        warnings: List[Tuple[str, Sequence[str***REMOVED******REMOVED******REMOVED*** = [***REMOVED***
        for trigger, matched in results:
            if not matched and not trigger.always:
                continue
            # always=True triggers (e.g. "New task") are not tied to file changes,
            # so they are not actionable from a pre-commit diff. Skip them in strict mode.
            if trigger.always:
                continue
            if not any(req_doc in changed for req_doc in trigger.doc_files):
                if trigger.severity == "block":
                    blockers.append((trigger.name, trigger.doc_files))
                else:
                    warnings.append((trigger.name, trigger.doc_files))

        if warnings:
            print("\n⚠️  Consider updating the following docs:")
            for trigger_name, doc_files in warnings:
                print(f"   [{trigger_name***REMOVED******REMOVED*** -> {', '.join(doc_files)***REMOVED***")

        if blockers:
            print("\n❌ Strict mode: the following required docs are missing:")
            for trigger_name, doc_files in blockers:
                print(f"   [{trigger_name***REMOVED******REMOVED*** -> {', '.join(doc_files)***REMOVED***")
            print("\n🛑 Commit blocked! Update the required docs or bypass with:")
            print("     git commit --no-verify")
            print("   or SKIP_AUTODOC=1 git commit ...")
            return 1

    if args.apply:
        created = touch_missing_docs(results)
        if created:
            print("\nCreated missing doc stubs:")
            for c in created:
                print(f"  - {c***REMOVED***")
        else:
            print("\nNo missing doc stubs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
