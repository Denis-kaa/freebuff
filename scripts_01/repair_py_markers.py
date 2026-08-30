#!/usr/bin/env python3
"""Conservative repair helper for literal ] markers in Python.

Default is dry-run. A file is changed only with --apply and only if a
candidate replacement parses successfully. Ambiguous files remain untouched.
"""
from __future__ import annotations

import argparse
import ast
import pathlib
import subprocess
from collections import Counter
from dataclasses import dataclass

MARKER = "]"
ROOT = pathlib.Path(__file__).resolve().parent.parent


@dataclass
class Result:
    path: str
    markers: int
    status: str
    replacement: str = ""
    diagnosis: str = ""


def diagnose_marker(text: str, offset: int) -> str:
    """Classify likely deleted material from immediate lexical context.

    This is diagnostic only. It intentionally reports hypotheses rather than
    modifying source: the marker may have replaced one token or many tokens.
    """
    before = text[max(0, offset - 100):offset]
    after = text[offset + len(MARKER):offset + len(MARKER) + 100]
    line_before = before.rsplit("\\n", 1)[-1]
    line_after = after.split("\\n", 1)[0]
    if line_before.rstrip().endswith(("[", "(", "{")):
        return "likely-opening-context"
    if line_after.lstrip().startswith(("]", "}", ")")):
        return "likely-deleted-expression-before-closer"
    if line_before.strip().startswith(("import ", "from ")) or line_after.lstrip().startswith(("import ", "from ")):
        return "likely-deleted-import-line"
    if line_before.rstrip().endswith(("Optional[str", "Optional[Dict[str, Any", "List[Dict[str, Any")):
        return "likely-deleted-type-closer"
    if line_before.rstrip().endswith(("or", "=", ",")):
        return "likely-deleted-expression-fragment"
    return "unknown-context"


def token_diagnostics(text: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    start = 0
    while True:
        pos = text.find(MARKER, start)
        if pos < 0:
            break
        counts[diagnose_marker(text, pos)] += 1
        start = pos + len(MARKER)
    return counts


def tracked_python_files() -> list[pathlib.Path]:
    raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    return [ROOT / x for x in raw.decode().split("\0") if x.endswith(".py")]


def candidates(text: str) -> list[str]:
    # Candidate sets are deliberately small. The marker commonly replaced a
    # closing delimiter or a complete import line. Never silently guess code.
    out: list[str] = []
    for replacement in ("]", "}", ")", "", "\n"):
        value = text.replace(MARKER, replacement)
        if value not in out:
            out.append(value)
    return out


def repair(path: pathlib.Path, apply: bool, diagnose: bool = False) -> Result:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return Result(str(path.relative_to(ROOT)), 0, "unreadable")
    count = text.count(MARKER)
    if not count:
        return Result(str(path.relative_to(ROOT)), 0, "clean")
    diagnosis = ",".join(f"{k}:{v}" for k, v in token_diagnostics(text).most_common())
    valid: list[tuple[str, str]] = []
    for replacement in ("]", "}", ")", "", "\n"):
        candidate = text.replace(MARKER, replacement)
        try:
            ast.parse(candidate, filename=str(path))
        except SyntaxError:
            continue
        valid.append((candidate, replacement))
    if len(valid) != 1:
        return Result(str(path.relative_to(ROOT)), count,
                      "ambiguous" if valid else "failed", diagnosis=diagnosis)
    candidate, replacement = valid[0]
    if apply:
        path.write_text(candidate, encoding="utf-8")
    return Result(str(path.relative_to(ROOT)), count,
                  "repaired" if apply else "repairable", replacement, diagnosis)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=False)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--diagnose", action="store_true", help="show lexical diagnoses; never writes")
    args = parser.parse_args()
    if args.dry_run and args.apply:
        parser.error("use either --dry-run or --apply")
    if args.diagnose:
        apply = False
    else:
        apply = args.apply
    results = [repair(p, apply, args.diagnose) for p in tracked_python_files()]
    affected = [r for r in results if r.markers]
    for r in affected:
        if r.status in {"repairable", "repaired"}:
            print(f"{r.status}\t{r.markers}\t{r.replacement!r}\t{r.diagnosis}\t{r.path}")
        else:
            print(f"{r.status}\t{r.markers}\t{r.diagnosis}\t{r.path}")
    from collections import Counter
    counts = Counter(r.status for r in affected)
    print("SUMMARY", dict(counts), "affected", len(affected),
          "markers", sum(r.markers for r in affected))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
