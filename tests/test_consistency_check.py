#!/usr/bin/env python3
"""
Tests for consistency_check.py (Stage 9 self-consistency audit).

Tests:
  - extract_engine_rows: registry table parsing
  - check_engine_files: registry → scripts/ files exist
  - check_lifecycle_coverage: registry → LIFECYCLE.md
  - check_module_areas: MODULE_CONSOLIDATION.md areas
  - check_glossary_terms: GLOSSARY.md required terms
  - check_roadmap_refs: roadmap referenced files exist
  - check_cross_references: canonical docs link each other
  - build_report / CLI exit codes
"""

from __future__ import annotations

import sys
***REMOVED***

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.consistency_check import (
    build_report,
    check_cross_references,
    check_engine_files,
    check_glossary_terms,
    check_lifecycle_coverage,
    check_module_areas,
    check_project_book,
    check_roadmap_refs,
    extract_engine_rows,
    run_consistency_check,
)

# ── Импорт должен работать и с фактическим проектом.
from scripts.consistency_check import (  # noqa: E402
    CANONICAL,
    GLOSSARY,
    LIFECYCLE,
    MANIFEST,
    MODULE_CONSOLIDATION,
    PROJECT_BOOK,
    ROADMAP,
)


# ═══════════════════════════════════════════════════════════════
# Helpers / fixtures
# ═══════════════════════════════════════════════════════════════


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """Временный workspace с минимальным согласованным набором реестров."""
    ws = tmp_path / "ws"

    # Блок взаимных ссылок ядра — присутствует в КАЖДОМ каноническом документе.
    core_links = (
        "[ARCHITECTURE_MANIFEST.md***REMOVED***(ARCHITECTURE_MANIFEST.md) "
        "[ARCHITECTURE_CANONICAL.md***REMOVED***(ARCHITECTURE_CANONICAL.md) "
        "[GLOSSARY.md***REMOVED***(GLOSSARY.md) [LIFECYCLE.md***REMOVED***(LIFECYCLE.md) "
        "[MODULE_CONSOLIDATION.md***REMOVED***(MODULE_CONSOLIDATION.md)"
    )

    # Канонический реестр: 2 движка, оба с файлами.
    _write(
        ws / CANONICAL,
        f"""
| # | Движок | Файл |
|---|--------|------|
| C1 | `MemoryEngine` | `scripts/memory_engine.py` |
| S1 | `RAGEngine` | `scripts/rag_engine.py` |

{core_links***REMOVED***
""",
    )
    # LIFECYCLE покрывает оба движка.
    _write(
        ws / LIFECYCLE,
        f"""
### C1 `MemoryEngine`
| Стадия | Статус |
|--------|--------|
| Создание | ✅ |
### S1 `RAGEngine`
| Стадия | Статус |
|--------|--------|
| Создание | ✅ |

{core_links***REMOVED***
""",
    )
    # MODULE_CONSOLIDATION покрывает все области (+ перекрёстные ссылки).
    areas = "\n".join(f"### {letter***REMOVED***. {name***REMOVED***\n" for letter, name in
                      zip("ABCDEFGHIJ", ["Router", "Telegram", "MCP", "Memory", "Knowledge",
                                         "Registry", "Context", "Tool Runtime", "Plugin API",
                                         "Event Bus"***REMOVED***))
    _write(ws / MODULE_CONSOLIDATION, f"{areas***REMOVED***\n{core_links***REMOVED***\n")
    # GLOSSARY со всеми обязательными терминами (+ перекрёстные ссылки).
    terms = "\n".join(f"| **{t***REMOVED***** | определение |" for t in
                      ["Workspace", "Project", "Module", "Agent", "Tool", "Plugin", "Connector",
                       "Integration", "Knowledge", "Memory", "Project Book", "Engineering Memory",
                       "Lifecycle", "Registry", "Decision Log", "Pulse"***REMOVED***)
    _write(ws / GLOSSARY, f"# GLOSSARY\n\n{terms***REMOVED***\n\n{core_links***REMOVED***\n")
    # MANIFEST ссылается на все документы ядра + PROJECT_BOOK.
    _write(
        ws / CANONICAL.parent / "ARCHITECTURE_MANIFEST.md",
        core_links + f"\nПроект: расширять {PROJECT_BOOK.name***REMOVED***\n",
    )
    # PROJECT_BOOK существует в каноническом месте.
    _write(ws / PROJECT_BOOK, "# Project Book\n\nНарратив проекта.\n")
    # Файлы движков существуют.
    _write(ws / "scripts/memory_engine.py", "class MemoryEngine:\n    pass\n")
    _write(ws / "scripts/rag_engine.py", "class RAGEngine:\n    pass\n")
    # Роадмап ссылается на существующие файлы + упоминает Project Book.
    _write(
        ws / ROADMAP,
        "Этап: `docs/core/ARCHITECTURE_CANONICAL.md` и `docs/core/GLOSSARY.md`. "
        "Project Book — нарратив инженерии.",
    )
    return ws


# ═══════════════════════════════════════════════════════════════
# Registry parsing
# ═══════════════════════════════════════════════════════════════


class TestExtractEngineRows:
    def test_parses_registry_rows(self):
        text = "| C1 | `MemoryEngine` | `scripts/memory_engine.py` |\n" \
               "| S7 | `DriftCheck` | `scripts/drift_check.py` |\n"
        rows = extract_engine_rows(text)
        assert len(rows) == 2
        assert rows[0***REMOVED*** == {"id": "C1", "engine": "MemoryEngine", "file": "scripts/memory_engine.py"***REMOVED***

    def test_ignores_non_engine_rows(self):
        text = "| A | `ModelCatalog` | `core/router.py` |\n| S1 | `RAGEngine` | `scripts/rag_engine.py` |\n"
        rows = extract_engine_rows(text)
        assert len(rows) == 1
        assert rows[0***REMOVED***["engine"***REMOVED*** == "RAGEngine"

    def test_empty_text(self):
        assert extract_engine_rows("") == [***REMOVED***


# ═══════════════════════════════════════════════════════════════
# Check families
# ═══════════════════════════════════════════════════════════════


class TestCheckEngineFiles:
    def test_all_clean(self, workspace: Path):
        assert check_engine_files(workspace) == [***REMOVED***

    def test_missing_file_reported(self, tmp_path: Path):
        ws = tmp_path / "ws"
        _write(ws / CANONICAL, "| C1 | `MemoryEngine` | `scripts/memory_engine.py` |\n")
        issues = check_engine_files(ws)
        assert len(issues) == 1
        assert issues[0***REMOVED***["engine"***REMOVED*** == "MemoryEngine"
        assert issues[0***REMOVED***["check"***REMOVED*** == "engine_files"

    def test_missing_registry_reported(self, tmp_path: Path):
        issues = check_engine_files(tmp_path)
        assert issues and issues[0***REMOVED***["issue"***REMOVED*** == "ARCHITECTURE_CANONICAL.md missing"


class TestCheckLifecycleCoverage:
    def test_all_covered(self, workspace: Path):
        assert check_lifecycle_coverage(workspace) == [***REMOVED***

    def test_uncovered_engine(self, tmp_path: Path):
        ws = tmp_path / "ws"
        _write(ws / CANONICAL, "| C1 | `MemoryEngine` | `scripts/memory_engine.py` |\n")
        _write(ws / LIFECYCLE, "### Something else\n")
        _write(ws / "scripts/memory_engine.py", "class MemoryEngine: pass\n")
        issues = check_lifecycle_coverage(ws)
        assert any(i["engine"***REMOVED*** == "MemoryEngine" for i in issues)


class TestCheckModuleAreas:
    def test_all_areas(self, workspace: Path):
        assert check_module_areas(workspace) == [***REMOVED***

    def test_missing_area(self, tmp_path: Path):
        ws = tmp_path / "ws"
        _write(ws / MODULE_CONSOLIDATION, "### A. Router\n")
        issues = check_module_areas(ws)
        assert any(i["area"***REMOVED*** == "Telegram" for i in issues)


class TestCheckGlossaryTerms:
    def test_all_terms(self, workspace: Path):
        assert check_glossary_terms(workspace) == [***REMOVED***

    def test_missing_term(self, tmp_path: Path):
        ws = tmp_path / "ws"
        _write(ws / GLOSSARY, "# GLOSSARY\n| **Workspace** | x |\n")
        issues = check_glossary_terms(ws)
        assert any(i["term"***REMOVED*** == "Knowledge" for i in issues)


class TestCheckRoadmapRefs:
    def test_refs_resolve(self, workspace: Path):
        assert check_roadmap_refs(workspace) == [***REMOVED***

    def test_broken_ref(self, tmp_path: Path):
        ws = tmp_path / "ws"
        _write(ws / ROADMAP, "Этап: `docs/core/MISSING_DOC.md`")
        issues = check_roadmap_refs(ws)
        assert any(i["ref"***REMOVED*** == "docs/core/MISSING_DOC.md" for i in issues)


class TestCheckCrossReferences:
    def test_all_link_each_other(self, workspace: Path):
        assert check_cross_references(workspace) == [***REMOVED***

    def test_missing_sibling_link(self, tmp_path: Path):
        ws = tmp_path / "ws"
        for name, rel in [
            ("ARCHITECTURE_CANONICAL.md", CANONICAL),
            ("ARCHITECTURE_MANIFEST.md", CANONICAL.parent / "ARCHITECTURE_MANIFEST.md"),
            ("GLOSSARY.md", GLOSSARY),
            ("LIFECYCLE.md", LIFECYCLE),
            ("MODULE_CONSOLIDATION.md", MODULE_CONSOLIDATION),
        ***REMOVED***:
            _write(ws / rel, f"# {name***REMOVED***\n")
        issues = check_cross_references(ws)
        assert len(issues) >= 1
        assert issues[0***REMOVED***["check"***REMOVED*** == "cross_references"


# ═══════════════════════════════════════════════════════════════
# Report / CLI
# ═══════════════════════════════════════════════════════════════


class TestCheckProjectBook:
    def test_all_clean(self, workspace: Path):
        assert check_project_book(workspace) == [***REMOVED***

    def test_missing_book_reported(self, tmp_path: Path):
        issues = check_project_book(tmp_path)
        assert issues and issues[0***REMOVED***["check"***REMOVED*** == "project_book"
        assert "PROJECT_BOOK.md missing" in issues[0***REMOVED***["issue"***REMOVED***

    def test_missing_manifest_ref(self, tmp_path: Path):
        ws = tmp_path / "ws"
        _write(ws / PROJECT_BOOK, "# Project Book\n")
        _write(ws / MANIFEST, "# Manifest без упоминания книги проекта\n")
        issues = check_project_book(ws)
        assert any("ARCHITECTURE_MANIFEST" in i["issue"***REMOVED*** for i in issues)

    def test_missing_roadmap_ref(self, tmp_path: Path):
        ws = tmp_path / "ws"
        _write(ws / PROJECT_BOOK, "# Project Book\n")
        _write(ws / MANIFEST, "# Manifest\n| Запрещено | Вместо |\n| Второй Project Book | расширять PROJECT_BOOK.md |\n")
        _write(ws / ROADMAP, "# Roadmap без упоминания книги проекта\n")
        issues = check_project_book(ws)
        assert any("ROADMAP_PROMT32" in i["issue"***REMOVED*** for i in issues)


class TestReport:
    def test_build_report_consistent(self, workspace: Path):
        report = build_report(workspace)
        assert report["consistent"***REMOVED*** is True
        assert report["total_issues"***REMOVED*** == 0

    def test_build_report_detects_issues(self, tmp_path: Path):
        report = build_report(tmp_path)
        assert report["consistent"***REMOVED*** is False
        assert report["total_issues"***REMOVED*** > 0

    def test_run_consistency_check_accepts_str(self, workspace: Path):
        report = run_consistency_check(str(workspace))
        assert report["consistent"***REMOVED*** is True

    def test_main_exit_zero_when_consistent(self, workspace: Path, monkeypatch):
        from scripts.consistency_check import main

        monkeypatch.setattr(sys, "argv", ["consistency_check.py", "--workspace", str(workspace)***REMOVED***)
        assert main() == 0

    def test_main_exit_one_when_inconsistent(self, tmp_path: Path, monkeypatch):
        from scripts.consistency_check import main

        monkeypatch.setattr(sys, "argv", ["consistency_check.py", "--workspace", str(tmp_path)***REMOVED***)
        assert main() == 1


# ═══════════════════════════════════════════════════════════════
# Real-project integration
# ═══════════════════════════════════════════════════════════════


class TestRealProject:
    def test_real_project_consistent(self):
        """Фактический проект должен проходить проверку (все реестры согласованы)."""
        report = build_report(PROJECT_ROOT)
        assert report["consistent"***REMOVED*** is True, format(report["total_issues"***REMOVED***)
