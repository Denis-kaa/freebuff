"""core_02/doc_code_verify.py — Code-Documentation Sync verifier (PHASE J).

Per promt 4 §19 artifact J (CODE_DOCUMENTATION_SYNC_SPEC). Closes register-first
cycle for missing capability `doc_code_verify` per AGENTS.md §5.

What it does:
1. extract_claims(doc): regex-extract @entity/@contract/@symbol/@test/@event anchors
   from docs_10/engineering-memory/*.md (skips ```code fences```).
2. load_code_map(workspace): parse PLATFORM_CODE_MAP_V1.md §A SECTION blocks
   (state machine: `### @entity <id>` followed by `- **type/file/symbol:**` bullets).
3. check_symbol_exists(workspace, file, symbol): AST-verify file::symbol (no import).
4. verify_claim(claim, code_map, workspace): classify into CONFIRMED/STALE/DOC_ONLY/UNKNOWN.
5. run_verification(target, workspace, strict): aggregate JSON for CLI.

Default mode: WARN (exit 0, prints findings). Opt-in --strict exits 1 on STALE/DOC_ONLY.

Pattern mirrors:
- core_02/forge_passport.py (frozen dataclass + _from_dict-style parsing)
- core_02/factory_registry.py (_reload graceful-degrade with yaml.YAMLError)
- scripts_01/consistency_check.py (CLI argparse + --json aggregate output)

CAN-16 ADDITIVE: NEW file, NO modifications to existing modules.

Usage::
    python -m core_02.doc_code_verify docs_10/engineering-memory/PLATFORM_CODE_MAP_V1.md
    python -m core_02.doc_code_verify docs_10/engineering-memory/ --json
    python -m core_02.doc_code_verify docs_10/engineering-memory/ --strict
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


# ─── Closed vocab (ANTI-6b) — mirror SEMANTIC_ANCHOR_SPEC_V1.md §I.1 rows 1-19 ───
ANCHOR_NAMESPACES: tuple[str, ...] = (
    "entity", "contract", "symbol", "test", "event",
    "module", "component",
)

# Regex: @<namespace> <target> | @<namespace>:<target>
# target = word chars + dot + colon + hyphen.
_ANCHOR_RE = re.compile(
    r"@(entity|contract|symbol|test|event|module|component)\s+([\w\.\:\-]+)"
)

# Section header: `### @entity <id>` OR `### @entity: <id>`
_ENTITY_HEADER_RE = re.compile(
    r"^###\s+@entity[:\s]+(.+)$"
)

# Lifecycle state machine (Anti-5 minimum useful set).
CLASSIFICATIONS: tuple[str, ...] = (
    "CONFIRMED",   # anchor in PLATFORM_CODE_MAP + file::symbol AST-verified
    "STALE",       # anchor in Map, but file/symbol missing on disk
    "DOC_ONLY",    # anchor in doc but missing from Map
    "UNKNOWN",     # classification failed (catch-all, defensive)
)


@dataclass(frozen=True)
class Claim:
    """Single semantic anchor extracted from a doc."""
    doc_path: str       # absolute or relative path to the doc
    line_num: int       # 1-based
    namespace: str      # "@entity" / "@contract" / ...
    target: str         # "scenario.registry" / "ScenarioRegistry.find_role"


@dataclass(frozen=True)
class VerificationResult:
    """Classification of one Claim + evidence."""
    claim: Claim
    classification: str  # CONFIRMED | STALE | DOC_ONLY | UNKNOWN
    mapped_file: str = ""
    mapped_symbol: str = ""
    evidence: str = ""


# ─── Markdown helpers ─────────────────────────────────────────────────────────


def _strip_md_marker(value: str) -> str:
    """Strip markdown bold markers and backticks from a value."""
    return value.strip().strip("*").strip("`").strip()


def _extract_first_backtick(value: str) -> str:
    """Extract content of first backticked span in value."""
    m = re.search(r"`([^`)+)`", value)
    return m.group(1).strip() if m else _strip_md_marker(value)


# ─── Step 1: Claim extraction ─────────────────────────────────────────────────


def extract_claims(doc_path: Path) -> list[Claim]:
    """Regex-extract anchors from a doc, skipping ```code fences```.

    Edge cases handled:
    - Code fence state machine: ``in_fence`` toggles on ``` lines.
    - Empty / missing doc → [] (no exception).
    - ReadError (encoding) → [].
    """
    if not doc_path.exists() or not doc_path.is_file():
        return []
    try:
        text = doc_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    claims: list[Claim] = []
    in_fence = False
    for line_num, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for m in _ANCHOR_RE.finditer(line):
            ns = "@" + m.group(1)
            target = m.group(2).strip()
            if not target:
                continue
            claims.append(Claim(
                doc_path=str(doc_path),
                line_num=line_num,
                namespace=ns,
                target=target,
            ))
    return claims


# ─── Step 2: Code map loader (PLATFORM_CODE_MAP_V1.md §A) ──────────────────────


def load_code_map(workspace: Path) -> dict[str, dict[str, Any]]:
    """Parse PLATFORM_CODE_MAP_V1.md §A SECTION blocks via state machine.

    Format (per reality, NOT markdown table):
        ### @entity <id>
        - **type:** <text>
        - **file:** `<path>`
        - **symbol:** `<ClassOrFunc>`

    Returns: dict[entity_id] -> {type, file, symbol}

    Edge cases:
    - File missing → {} (silently — caller handles NONE-of-map case via DOC_ONLY).
    - ReadError → {}.
    - Duplicate `### @entity <id>` → first-wins (anti-6b closed vocab).
    - Section without `- **symbol:**` → register entity with empty symbol (caller
      marks it STALE).
    """
    map_path = workspace / "docs_10" / "engineering-memory" / "PLATFORM_CODE_MAP_V1.md"
    if not map_path.exists():
        return {}

    try:
        text = map_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}

    result: dict[str, dict[str, Any]] = {}
    current: Optional[str] = None

    for line in text.splitlines():
        s = line.strip()

        # Detect section header.
        if s.startswith("### @entity"):
            m = _ENTITY_HEADER_RE.match(s)
            if m:
                candidate = m.group(1).strip().strip("`").strip()
                # Strip optional trailing backticks / parens commentary.
                candidate = re.sub(r"\s*\(.*?\)\s*$", "", candidate).strip()  # non-greedy paren strip
                if candidate and candidate not in result:
                    result[candidate] = {"type": "", "file": "", "symbol": ""}
                    current = candidate
                else:
                    current = None  # already registered, skip
            else:
                current = None
            continue

        # Non-bullet paragraph break → reset current (bullet continuation allowed).
        if s and not s.startswith("- ") and not s.startswith("#"):
            current = None
            continue

        if current is None:
            continue

        # Bullet parsing.
        if s.startswith("- **type:**"):
            result[current]["type"] = _strip_md_marker(s.split(":", 1)[1])
        elif s.startswith("- **file:**"):
            result[current]["file"] = _extract_first_backtick(s.split(":", 1)[1])
        elif s.startswith("- **symbol:**"):
            val = _extract_first_backtick(s.split(":", 1)[1])
            if val and not result[current]["symbol"]:
                result[current]["symbol"] = val
        elif s.startswith("- **public_api:**"):
            # public_api sometimes contains the primary symbol as first backtick.
            val = _extract_first_backtick(s.split(":", 1)[1])
            if val and not result[current]["symbol"]:
                result[current]["symbol"] = val

    return result


# ─── Step 3: AST verifier (no import) ─────────────────────────────────────────


def check_symbol_exists(workspace: Path, file_rel: str, symbol: str) -> bool:
    """AST-verify file::symbol exists at module level (or Class.method).

    Edge cases:
    - File missing → False.
    - Parse error → False.
    - Class.method → walk into class body for FunctionDef/AsyncFunctionDef.
    """
    full = workspace / file_rel
    if not full.exists() or not full.is_file():
        return False
    try:
        tree = ast.parse(full.read_text(encoding="utf-8"))
    except (SyntaxError, OSError, UnicodeDecodeError):
        return False

    # Direct match: top-level ClassDef or FunctionDef.
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == symbol:
            return True
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == symbol:
            return True

    # Class.method dot notation.
    if "." in symbol:
        cls, _, method = symbol.partition(".")
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == cls:
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == method:
                        return True
    return False


# ─── Step 4: Claim classifier ─────────────────────────────────────────────────


def verify_claim(
    claim: Claim,
    code_map: dict[str, dict[str, Any]],
    workspace: Path,
) -> VerificationResult:
    """Classify one Claim against code_map + AST."""
    if claim.target not in code_map:
        return VerificationResult(
            claim=claim,
            classification="DOC_ONLY",
            evidence="target not in PLATFORM_CODE_MAP_V1.md §A",
        )

    mapped = code_map[claim.target]
    file_rel = mapped.get("file", "")
    symbol = mapped.get("symbol", "")

    if not file_rel or not symbol:
        return VerificationResult(
            claim=claim,
            classification="STALE",
            mapped_file=file_rel,
            mapped_symbol=symbol,
            evidence="PLATFORM_CODE_MAP §A entry missing file or symbol",
        )

    if check_symbol_exists(workspace, file_rel, symbol):
        return VerificationResult(
            claim=claim,
            classification="CONFIRMED",
            mapped_file=file_rel,
            mapped_symbol=symbol,
            evidence=f"{file_rel}::{symbol}",
        )

    return VerificationResult(
        claim=claim,
        classification="STALE",
        mapped_file=file_rel,
        mapped_symbol=symbol,
        evidence=f"{file_rel}::{symbol} not found via AST",
    )


# ─── Step 5: Aggregate runner (CLI entry) ─────────────────────────────────────


def run_verification(
    target_path: Path,
    workspace: Path,
    *,
    strict: bool = False,
) -> dict[str, Any]:
    """Run verification on a single doc or all *.md under a directory."""
    docs_checked = 0
    findings: list[dict[str, Any]] = []
    by_classification: dict[str, int] = {c: 0 for c in CLASSIFICATIONS}

    code_map = load_code_map(workspace)

    if target_path.is_file():
        docs = [target_path]
    elif target_path.is_dir():
        docs = sorted(target_path.rglob("*.md"))
    else:
        return {
            "error": f"not found: {target_path}",
            "docs_checked": 0,
            "total_claims": 0,
            "by_classification": by_classification,
            "findings": [],
            "strict_exit_code": 2,
        }

    for doc in docs:
        if not doc.exists():
            continue
        if "engineering-memory" not in str(doc):
            continue
        docs_checked += 1
        for claim in extract_claims(doc):
            result = verify_claim(claim, code_map, workspace)
            by_classification[result.classification] += 1
            try:
                doc_rel = str(doc.relative_to(workspace))
            except ValueError:
                doc_rel = str(doc)
            findings.append({
                "doc": doc_rel,
                "line": claim.line_num,
                "namespace": claim.namespace,
                "target": claim.target,
                "classification": result.classification,
                "mapped_file": result.mapped_file,
                "mapped_symbol": result.mapped_symbol,
                "evidence": result.evidence,
            })

    total_claims = sum(by_classification.values())
    strict_exit_code = 1 if (
        strict
        and (by_classification["STALE"] > 0 or by_classification["DOC_ONLY"] > 0)
    ) else 0

    return {
        "docs_checked": docs_checked,
        "total_claims": total_claims,
        "by_classification": by_classification,
        "findings": findings,
        "strict_exit_code": strict_exit_code,
    }


# ─── CLI ───────────────────────────────────────────────────────────────────────


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m core_02.doc_code_verify",
        description="Code-Documentation Sync verifier (PHASE J).",
    )
    parser.add_argument("target", help="Doc file or directory of docs")
    parser.add_argument(
        "--workspace", default=".",
        help="Workspace root (default: .)"
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit 1 on any STALE/DOC_ONLY finding"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output JSON only"
    )
    args = parser.parse_args(argv)

    workspace = Path(args.workspace).resolve()
    target = Path(args.target)
    if not target.exists():
        print(f"Target not found: {target}", file=sys.stderr)
        return 2

    summary = run_verification(target, workspace, strict=args.strict)

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        bc = summary["by_classification"]
        print(f"Docs checked  : {summary['docs_checked']}")
        print(f"Total claims  : {summary['total_claims']}")
        for c in CLASSIFICATIONS:
            print(f"  {c:<11}  : {bc[c]}")
        if summary["findings"]:
            print("\nFindings:")
            for f in summary["findings"]:
                marker = {
                    "CONFIRMED": "[OK]",
                    "STALE":     "[!!]",
                    "DOC_ONLY":  "[??]",
                    "UNKNOWN":   "[??]",
                }.get(f["classification"], "[??)")
                line = (
                    f"  {marker} {f['classification']:<9} "
                    f"{f['doc']}:{f['line']} "
                    f"{f['namespace']} {f['target']}"
                )
                print(line)
                if f["evidence"]:
                    print(f"           -> {f['evidence']}")

    return int(summary["strict_exit_code"])


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "ANCHOR_NAMESPACES",
    "CLASSIFICATIONS",
    "Claim",
    "VerificationResult",
    "extract_claims",
    "load_code_map",
    "check_symbol_exists",
    "verify_claim",
    "run_verification",
    "main",
]
