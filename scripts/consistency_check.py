#!/usr/bin/env python3
"""
consistency_check.py — Stage 9: self-consistency audit (registries as data).

Проверяет, что канонические реестры (документы-источники истины) согласованы
между собой и с кодовой базой:

  1. ENGINE FILES       — каждый движок из ARCHITECTURE_CANONICAL §3 имеет файл в scripts/
  2. LIFECYCLE COVERAGE — каждый движок из реестра описан в LIFECYCLE.md
  3. MODULE AREAS       — все 10 областей консолидации покрыты в MODULE_CONSOLIDATION.md
  4. GLOSSARY TERMS     — все 16 обязательных терминов присутствуют в GLOSSARY.md
  5. ROADMAP REFS       — файлы, на которые ссылается ROADMAP_PROMT32, существуют
  6. CROSS REFERENCES   — канонические документы ссылаются друг на друга (взаимно)
  7. PROJECT BOOK       — PROJECT_BOOK.md существует и связан с реестрами (несоответствие
                          Roadmap/Registry/Project Book не проходит незамеченным)

Роль: инструмент Этапа 9 консолидации (promt32) — «реестры как данные для проверки».
Не изменяет код/документы автоматически.

Ограничения (осознанные):
  - check_module_areas / check_glossary_terms используют substring-поиск
    (область «Memory» находится внутри «MemoryEngine»). Это проверка ПОКРЫТИЯ,
    а не точного соответствия секций/строк таблиц — строгий разбор заголовков
    (например, `### A. Router`) будет усилением в будущем.
  - check_cross_references проверяет ВЗАИМНЫЕ УПОМИНАНИЯ имён документов,
    а не синтаксис markdown-ссылок `[...***REMOVED***(...)` — битые ссылки как таковые
    детектит scripts/drift_check.py (link checker).
  - check_project_book тоже mention-based: достаточно вхождения
    «PROJECT_BOOK»/«Project Book» в MANIFEST/ROADMAP (в т.ч. в таблицах
    запретов), а не обязательной markdown-ссылки на файл.

Использование:
    python scripts/consistency_check.py            # запуск, exit 0/1
    python scripts/consistency_check.py --report   # печать отчёта в stdout
    python scripts/consistency_check.py --json     # JSON-отчёт
"""
from __future__ import annotations

import argparse
import json
***REMOVED***
import sys
from datetime import datetime, timezone
***REMOVED***
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Канонические реестры (источники истины) ──────────────────────────
CANONICAL = Path("docs/core/ARCHITECTURE_CANONICAL.md")
LIFECYCLE = Path("docs/core/LIFECYCLE.md")
MODULE_CONSOLIDATION = Path("docs/core/MODULE_CONSOLIDATION.md")
GLOSSARY = Path("docs/core/GLOSSARY.md")
MANIFEST = Path("docs/core/ARCHITECTURE_MANIFEST.md")
ROADMAP = Path("docs/vision/ROADMAP_PROMT32_CONSOLIDATION.md")
PROJECT_BOOK = Path("docs/engineering-memory/PROJECT_BOOK.md")

# Документы ядра, которые обязаны ссылаться друг на друга (взаимно).
CORE_DOCS = {
    "ARCHITECTURE_CANONICAL.md": CANONICAL,
    "ARCHITECTURE_MANIFEST.md": MANIFEST,
    "GLOSSARY.md": GLOSSARY,
    "LIFECYCLE.md": LIFECYCLE,
    "MODULE_CONSOLIDATION.md": MODULE_CONSOLIDATION,
***REMOVED***

# Обязательные термины глоссария (Этап 7, список из ROADMAP).
REQUIRED_GLOSSARY_TERMS = [
    "Workspace", "Project", "Module", "Agent", "Tool", "Plugin", "Connector",
    "Integration", "Knowledge", "Memory", "Project Book", "Engineering Memory",
    "Lifecycle", "Registry", "Decision Log", "Pulse",
***REMOVED***

# 10 областей консолидации (Этап 6).
CONSOLIDATION_AREAS = [
    "Router", "Telegram", "MCP", "Memory", "Knowledge", "Registry",
    "Context", "Tool Runtime", "Plugin API", "Event Bus",
***REMOVED***

# Заголовки секций реестра движков в ARCHITECTURE_CANONICAL.
_ENGINE_ROW_RE = re.compile(
    r"^\|\s*(C\d+|S\d+)\s*\|\s*`([A-Za-z***REMOVED***+)`\s*\|\s*`(scripts/[a-z0-9_***REMOVED***+\.py)`"
)


def _read(workspace: Path, rel: Path) -> str | None:
    """Прочитать текст файла относительно workspace; None если нет."""
    path = workspace / rel
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════
# 1. Engine files
# ═══════════════════════════════════════════════════════════════


def extract_engine_rows(text: str) -> list[dict[str, str***REMOVED******REMOVED***:
    """Извлечь (id, engine, file) из таблиц реестра движков canonical."""
    rows: list[dict[str, str***REMOVED******REMOVED*** = [***REMOVED***
    for line in text.splitlines():
        m = _ENGINE_ROW_RE.match(line)
        if m:
            rows.append({"id": m.group(1), "engine": m.group(2), "file": m.group(3)***REMOVED***)
    return rows


def check_engine_files(workspace: Path) -> list[dict[str, Any***REMOVED******REMOVED***:
    """Каждый движок из canonical имеет файл в scripts/."""
    issues: list[dict[str, Any***REMOVED******REMOVED*** = [***REMOVED***
    text = _read(workspace, CANONICAL)
    if text is None:
        return [{"check": "engine_files", "issue": "ARCHITECTURE_CANONICAL.md missing"***REMOVED******REMOVED***
    for row in extract_engine_rows(text):
        if not (workspace / row["file"***REMOVED***).exists():
            issues.append({
                "check": "engine_files",
                "engine": row["engine"***REMOVED***,
                "file": row["file"***REMOVED***,
                "issue": "registry references missing file",
            ***REMOVED***)
    return issues


# ═══════════════════════════════════════════════════════════════
# 2. Lifecycle coverage
# ═══════════════════════════════════════════════════════════════


def check_lifecycle_coverage(workspace: Path) -> list[dict[str, Any***REMOVED******REMOVED***:
    """Каждый движок из canonical описан в LIFECYCLE.md."""
    issues: list[dict[str, Any***REMOVED******REMOVED*** = [***REMOVED***
    canonical_text = _read(workspace, CANONICAL)
    lifecycle_text = _read(workspace, LIFECYCLE)
    if canonical_text is None or lifecycle_text is None:
        return [{
            "check": "lifecycle_coverage",
            "issue": "ARCHITECTURE_CANONICAL.md or LIFECYCLE.md missing",
        ***REMOVED******REMOVED***
    for row in extract_engine_rows(canonical_text):
        if f"`{row['engine'***REMOVED******REMOVED***`" not in lifecycle_text:
            issues.append({
                "check": "lifecycle_coverage",
                "engine": row["engine"***REMOVED***,
                "issue": "engine not covered in LIFECYCLE.md",
            ***REMOVED***)
    return issues


# ═══════════════════════════════════════════════════════════════
# 3. Module consolidation areas
# ═══════════════════════════════════════════════════════════════


def check_module_areas(workspace: Path) -> list[dict[str, Any***REMOVED******REMOVED***:
    """Все 10 областей консолидации покрыты в MODULE_CONSOLIDATION.md."""
    issues: list[dict[str, Any***REMOVED******REMOVED*** = [***REMOVED***
    text = _read(workspace, MODULE_CONSOLIDATION)
    if text is None:
        return [{"check": "module_areas", "issue": "MODULE_CONSOLIDATION.md missing"***REMOVED******REMOVED***
    for area in CONSOLIDATION_AREAS:
        if area not in text:
            issues.append({
                "check": "module_areas",
                "area": area,
                "issue": "area not covered in MODULE_CONSOLIDATION.md",
            ***REMOVED***)
    return issues


# ═══════════════════════════════════════════════════════════════
# 4. Glossary terms
# ═══════════════════════════════════════════════════════════════


def check_glossary_terms(workspace: Path) -> list[dict[str, Any***REMOVED******REMOVED***:
    """Все обязательные термины присутствуют в GLOSSARY.md."""
    issues: list[dict[str, Any***REMOVED******REMOVED*** = [***REMOVED***
    text = _read(workspace, GLOSSARY)
    if text is None:
        return [{"check": "glossary_terms", "issue": "GLOSSARY.md missing"***REMOVED******REMOVED***
    for term in REQUIRED_GLOSSARY_TERMS:
        if f"**{term***REMOVED*****" not in text:
            issues.append({
                "check": "glossary_terms",
                "term": term,
                "issue": "required term missing in GLOSSARY.md",
            ***REMOVED***)
    return issues


# ═══════════════════════════════════════════════════════════════
# 5. Roadmap references
# ═══════════════════════════════════════════════════════════════


def _extract_file_refs(text: str) -> set[str***REMOVED***:
    """Извлечь backtick-пути к файлам (.md/.py) из текста."""
    refs = set(re.findall(r"`([\w./\-***REMOVED***+\.(?:md|py))`", text))
    refs |= set(re.findall(r"(docs/[\w./\-***REMOVED***+\.md)", text))
    return refs


def check_roadmap_refs(workspace: Path) -> list[dict[str, Any***REMOVED******REMOVED***:
    """Файлы, на которые ссылается ROADMAP_PROMT32, существуют."""
    issues: list[dict[str, Any***REMOVED******REMOVED*** = [***REMOVED***
    text = _read(workspace, ROADMAP)
    if text is None:
        return [{"check": "roadmap_refs", "issue": "ROADMAP_PROMT32_CONSOLIDATION.md missing"***REMOVED******REMOVED***
    for ref in sorted(_extract_file_refs(text)):
        target = workspace / ref
        if not target.exists():
            issues.append({
                "check": "roadmap_refs",
                "ref": ref,
                "issue": "roadmap references missing file",
            ***REMOVED***)
    return issues


# ═══════════════════════════════════════════════════════════════
# 6. Cross references (canonical docs link each other)
# ═══════════════════════════════════════════════════════════════


def check_cross_references(workspace: Path) -> list[dict[str, Any***REMOVED******REMOVED***:
    """Каждый канонический документ упоминает остальные (взаимные ссылки)."""
    issues: list[dict[str, Any***REMOVED******REMOVED*** = [***REMOVED***
    texts: dict[str, str | None***REMOVED*** = {***REMOVED***
    for name, rel in CORE_DOCS.items():
        texts[name***REMOVED*** = _read(workspace, rel)
    for name, text in texts.items():
        if text is None:
            issues.append({"check": "cross_references", "doc": name, "issue": "document missing"***REMOVED***)
            continue
        for other in CORE_DOCS:
            if other == name:
                continue
            if other not in text:
                issues.append({
                    "check": "cross_references",
                    "doc": name,
                    "missing_ref": other,
                    "issue": "canonical doc does not reference its sibling",
                ***REMOVED***)
    return issues


# ═══════════════════════════════════════════════════════════════
# 7. Project Book consistency
# ═══════════════════════════════════════════════════════════════


def check_project_book(workspace: Path) -> list[dict[str, Any***REMOVED******REMOVED***:
    """Project Book существует и связан с каноническими реестрами.

    Проверяет три вещи (несоответствие Roadmap/Registry/Project Book):
      1. PROJECT_BOOK.md существует в docs/engineering-memory/
      2. На него ссылается ARCHITECTURE_MANIFEST (канонический реестр)
      3. Он упоминается в ROADMAP_PROMT32 (план работ)
    """
    issues: list[dict[str, Any***REMOVED******REMOVED*** = [***REMOVED***

    text = _read(workspace, PROJECT_BOOK)
    if text is None:
        return [{"check": "project_book", "issue": "PROJECT_BOOK.md missing in docs/engineering-memory/"***REMOVED******REMOVED***

    manifest_text = _read(workspace, MANIFEST) or ""
    if "PROJECT_BOOK" not in manifest_text and "Project Book" not in manifest_text:
        issues.append({
            "check": "project_book",
            "issue": "PROJECT_BOOK.md not referenced from ARCHITECTURE_MANIFEST.md",
        ***REMOVED***)

    roadmap_text = _read(workspace, ROADMAP) or ""
    if "PROJECT_BOOK" not in roadmap_text and "Project Book" not in roadmap_text:
        issues.append({
            "check": "project_book",
            "issue": "Project Book not mentioned in ROADMAP_PROMT32_CONSOLIDATION.md",
        ***REMOVED***)

    return issues


# ═══════════════════════════════════════════════════════════════
# Report
# ═══════════════════════════════════════════════════════════════


def build_report(workspace: Path) -> dict[str, Any***REMOVED***:
    """Собрать полный отчёт самоконсистентности."""
    report: dict[str, Any***REMOVED*** = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "engine_files": check_engine_files(workspace),
        "lifecycle_coverage": check_lifecycle_coverage(workspace),
        "module_areas": check_module_areas(workspace),
        "glossary_terms": check_glossary_terms(workspace),
        "roadmap_refs": check_roadmap_refs(workspace),
        "cross_references": check_cross_references(workspace),
        "project_book": check_project_book(workspace),
    ***REMOVED***
    all_issues = (
        report["engine_files"***REMOVED***
        + report["lifecycle_coverage"***REMOVED***
        + report["module_areas"***REMOVED***
        + report["glossary_terms"***REMOVED***
        + report["roadmap_refs"***REMOVED***
        + report["cross_references"***REMOVED***
        + report["project_book"***REMOVED***
    )
    report["total_issues"***REMOVED*** = len(all_issues)
    report["consistent"***REMOVED*** = not all_issues
    return report


def format_report(report: dict[str, Any***REMOVED***) -> str:
    lines: list[str***REMOVED*** = [
        "# Consistency Report (Stage 9)",
        "",
        f"_Generated at: {report['generated_at'***REMOVED******REMOVED***_",
        "",
        "> Реестры как данные: ARCHITECTURE_CANONICAL, LIFECYCLE, MODULE_CONSOLIDATION, "
        "GLOSSARY, ROADMAP_PROMT32.",
        "",
    ***REMOVED***
    if report["consistent"***REMOVED***:
        lines.extend(["## ✅ Consistent", "", "All canonical registries agree with the codebase."***REMOVED***)
        return "\n".join(lines)

    lines.append(f"## ⚠️ {report['total_issues'***REMOVED******REMOVED*** issue(s) found")
    sections = [
        ("engine_files", "Engine files (canonical registry → scripts/)"),
        ("lifecycle_coverage", "Lifecycle coverage (registry → LIFECYCLE.md)"),
        ("module_areas", "Module consolidation areas (MODULE_CONSOLIDATION.md)"),
        ("glossary_terms", "Glossary terms (GLOSSARY.md)"),
        ("roadmap_refs", "Roadmap references (ROADMAP_PROMT32)"),
        ("cross_references", "Cross references (canonical docs link each other)"),
        ("project_book", "Project Book consistency (docs/engineering-memory)"),
    ***REMOVED***
    for key, title in sections:
        items = report[key***REMOVED***
        if not items:
            continue
        lines.append("")
        lines.append(f"## {title***REMOVED***")
        for item in items:
            detail = " · ".join(f"{k***REMOVED***={v***REMOVED***" for k, v in item.items() if k != "check")
            lines.append(f"- `{item['check'***REMOVED******REMOVED***`: {detail***REMOVED***")
    return "\n".join(lines)


def run_consistency_check(workspace: Path | str) -> dict[str, Any***REMOVED***:
    """Запустить проверку и вернуть отчёт."""
    ws = Path(workspace) if isinstance(workspace, str) else workspace
    return build_report(ws)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stage 9 self-consistency audit (registries as data)"
    )
    parser.add_argument("--workspace", default=str(PROJECT_ROOT), help="Path to freebuff workspace")
    parser.add_argument("--report", action="store_true", help="Print report to stdout")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    report = run_consistency_check(workspace)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif args.report or not report["consistent"***REMOVED***:
        print(format_report(report))

    return 0 if report["consistent"***REMOVED*** else 1


if __name__ == "__main__":
    sys.exit(main())
