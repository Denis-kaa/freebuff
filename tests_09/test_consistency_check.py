#!/usr/bin/env python3
"""
Tests for consistency_check.py (Stage 9 self-consistency audit).

Tests:
  - extract_engine_rows: registry table parsing
  - check_engine_files: registry → scripts_01/ files exist
  - check_lifecycle_coverage: registry → LIFECYCLE.md
  - check_module_areas: MODULE_CONSOLIDATION.md areas
  - check_glossary_terms: GLOSSARY.md required terms
  - check_roadmap_refs: roadmap referenced files exist
  - check_cross_references: canonical docs link each other
  - check_naming_convention: dirs имя_NN, prompts NNN_TT_имя (FINAL_STRUCTURE §2.1
    + GLOSSARY «Naming Convention»)
  - build_report / CLI exit codes
"""

from __future__ import annotations

import ast
import sys
***REMOVED***

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts_01.consistency_check import (
    build_report,
    check_cross_references,
    check_engine_files,
    check_glossary_terms,
    check_lifecycle_coverage,
    check_module_areas,
    check_naming_convention,
    check_project_book,
    check_roadmap_refs,
    check_test_counter,
    count_test_functions,
    extract_engine_rows,
    run_consistency_check,
    _PytestCollectionVisitor as V,  # [5.39.3***REMOVED*** top-level: synthetic visitor regression-gate
    _chain_key,  # [5.39.3***REMOVED*** top-level: e2e Set-A vs Set-B parity helper
)

# ── Импорт должен работать и с фактическим проектом.
from scripts_01.consistency_check import (  # noqa: E402
    CANONICAL,
    CHANGELOG,
    CODE_QUALITY_STANDARD,
    FINAL_STRUCTURE,
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
| C1 | `MemoryEngine` | `scripts_01/memory_engine.py` |
| S1 | `RAGEngine` | `scripts_01/rag_engine.py` |

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
                       "Lifecycle", "Registry", "Decision Log", "Pulse", "Naming Convention"***REMOVED***)
    _write(ws / GLOSSARY, f"# GLOSSARY\n\n{terms***REMOVED***\n\n{core_links***REMOVED***\n")
    # MANIFEST ссылается на все документы ядра + PROJECT_BOOK.
    _write(
        ws / CANONICAL.parent / "ARCHITECTURE_MANIFEST.md",
        core_links + f"\nПроект: расширять {PROJECT_BOOK.name***REMOVED***\n",
    )
    # PROJECT_BOOK существует в каноническом месте.
    _write(ws / PROJECT_BOOK, "# Project Book\n\nНарратив проекта.\n")
    # Файлы движков существуют.
    _write(ws / "scripts_01/memory_engine.py", "class MemoryEngine:\n    pass\n")
    _write(ws / "scripts_01/rag_engine.py", "class RAGEngine:\n    pass\n")
    # Роадмап ссылается на существующие файлы + упоминает Project Book.
    _write(
        ws / ROADMAP,
        "Этап: `docs_10/core/ARCHITECTURE_CANONICAL.md` и `docs_10/core/GLOSSARY.md`. "
        "Project Book — нарратив инженерии.",
    )
    # FINAL_STRUCTURE фиксирует схему именования (проверка naming_convention).
    _write(ws / FINAL_STRUCTURE, "### 2.1 Схема именования (Naming Convention, канон)\n")
    return ws


# ═══════════════════════════════════════════════════════════════
# Registry parsing
# ═══════════════════════════════════════════════════════════════


class TestExtractEngineRows:
    def test_parses_registry_rows(self):
        text = "| C1 | `MemoryEngine` | `scripts_01/memory_engine.py` |\n" \
               "| S7 | `DriftCheck` | `scripts_01/drift_check.py` |\n"
        rows = extract_engine_rows(text)
        assert len(rows) == 2
        assert rows[0***REMOVED*** == {"id": "C1", "engine": "MemoryEngine", "file": "scripts_01/memory_engine.py"***REMOVED***

    def test_ignores_non_engine_rows(self):
        text = "| A | `ModelCatalog` | `core_02/router.py` |\n| S1 | `RAGEngine` | `scripts_01/rag_engine.py` |\n"
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
        _write(ws / CANONICAL, "| C1 | `MemoryEngine` | `scripts_01/memory_engine.py` |\n")
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
        _write(ws / CANONICAL, "| C1 | `MemoryEngine` | `scripts_01/memory_engine.py` |\n")
        _write(ws / LIFECYCLE, "### Something else\n")
        _write(ws / "scripts_01/memory_engine.py", "class MemoryEngine: pass\n")
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
        _write(ws / ROADMAP, "Этап: `docs_10/core/MISSING_DOC.md`")
        issues = check_roadmap_refs(ws)
        assert any(i["ref"***REMOVED*** == "docs_10/core/MISSING_DOC.md" for i in issues)


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


class TestNamingConventionLegacyRedirect:
    """Зеркалит scripts_01/drift_check.py::_is_legacy_redirect_satisfied (5.37.1).

    Legacy top-level redirect-shim (Этап 4 консолидации) пропускается
    проверкой naming_convention, если соответствующий канонический
    каталог с NN-suffix'ом существует. Не маскирует настоящие нарушения:
    если canonical отсутствует — shim считается "сиротой" и флагуется.
    """

    def test_legacy_redirect_satisfied_when_canonical_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Workspace: legacy shim + canonical существует → пропускаем.
        (tmp_path / "freebuff_plugin").mkdir()
        (tmp_path / "freebuff_plugin_03").mkdir()
        # pompts_11 + final_structure + glossary обязательны для двух оставшихся якорей;
        # создаём минимальный «approve-окружение» чтобы фокус был именно на legacy-redirect.
        (tmp_path / "pompts_11").mkdir()
        (tmp_path / "pompts_11" / "001_01_dummy.md").write_text("# dummy\n")
        (tmp_path / "docs_10").mkdir()
        (tmp_path / "docs_10" / "core").mkdir()
        (tmp_path / "docs_10" / "core" / "FINAL_STRUCTURE.md").write_text(
            "## §2.1 Схема именования\n"
        )
        (tmp_path / "docs_10" / "core" / "GLOSSARY.md").write_text(
            "## **Naming Convention**\n"
        )
        from scripts_01.consistency_check import check_naming_convention
        issues = check_naming_convention(tmp_path)
        legacy = [i for i in issues if i.get("kind") == "dir" and i.get("name") == "freebuff_plugin"***REMOVED***
        assert legacy == [***REMOVED***, f"legacy shim должен пропускаться когда canonical существует, issues={issues***REMOVED***"

    def test_legacy_redirect_flagged_when_canonical_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Workspace: legacy shim без canonical → нарушение (orphan shim).
        (tmp_path / "freebuff_plugin").mkdir()
        (tmp_path / "pompts_11").mkdir()
        (tmp_path / "pompts_11" / "001_01_dummy.md").write_text("# dummy\n")
        (tmp_path / "docs_10").mkdir()
        (tmp_path / "docs_10" / "core").mkdir()
        (tmp_path / "docs_10" / "core" / "FINAL_STRUCTURE.md").write_text(
            "## §2.1 Схема именования\n"
        )
        (tmp_path / "docs_10" / "core" / "GLOSSARY.md").write_text(
            "## **Naming Convention**\n"
        )
        from scripts_01.consistency_check import check_naming_convention
        issues = check_naming_convention(tmp_path)
        legacy = [
            i for i in issues
            if i.get("kind") == "dir" and i.get("name") == "freebuff_plugin"
        ***REMOVED***
        assert len(legacy) == 1, (
            f"orphan shim должен флагуться как нарушение, issues={issues***REMOVED***"
        )
        assert legacy[0***REMOVED***["issue"***REMOVED***.startswith("top-level dir violates")

    def test_non_legacy_undeclared_dir_still_flagged(
        self, tmp_path: Path
    ) -> None:
        # Workspace: произвольный top-level dir без NN-suffix → флагуется как обычно.
        (tmp_path / "garbage_dir").mkdir()
        (tmp_path / "pompts_11").mkdir()
        (tmp_path / "pompts_11" / "001_01_dummy.md").write_text("# dummy\n")
        (tmp_path / "docs_10").mkdir()
        (tmp_path / "docs_10" / "core").mkdir()
        (tmp_path / "docs_10" / "core" / "FINAL_STRUCTURE.md").write_text(
            "## §2.1 Схема именования\n"
        )
        (tmp_path / "docs_10" / "core" / "GLOSSARY.md").write_text(
            "## **Naming Convention**\n"
        )
        from scripts_01.consistency_check import check_naming_convention
        issues = check_naming_convention(tmp_path)
        garbage = [
            i for i in issues
            if i.get("kind") == "dir" and i.get("name") == "garbage_dir"
        ***REMOVED***
        assert len(garbage) == 1
        assert garbage[0***REMOVED***["issue"***REMOVED***.startswith("top-level dir violates")

    def test_legacy_redirect_helper_unit(self) -> None:
        # Unit-тест для _is_legacy_redirect_satisfied.
        from scripts_01.consistency_check import _is_legacy_redirect_satisfied
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            # unknown name → False
            assert _is_legacy_redirect_satisfied(ws, "no_such_legacy") is False
            # legacy name + missing canonical → False (orphan)
            (ws / "freebuff_plugin").mkdir()
            assert _is_legacy_redirect_satisfied(ws, "freebuff_plugin") is False
            # legacy name + present canonical → True (shim functional)
            (ws / "freebuff_plugin_03").mkdir()
            assert _is_legacy_redirect_satisfied(ws, "freebuff_plugin") is True


class TestRealProject:
    def test_conforming_workspace(self, workspace: Path):
        """Фикстура: каталоги имя_NN, FINAL_STRUCTURE с секцией → чисто."""
        assert check_naming_convention(workspace) == [***REMOVED***

    def test_bad_top_level_dir_name(self, tmp_path: Path):
        ws = tmp_path / "ws"
        _write(ws / FINAL_STRUCTURE, "### 2.1 Схема именования\n")
        (ws / "old_docs").mkdir()  # без суффикса _NN
        issues = check_naming_convention(ws)
        assert any(i["kind"***REMOVED*** == "dir" and i["name"***REMOVED*** == "old_docs" for i in issues)

    def test_system_and_hidden_dirs_skipped(self, tmp_path: Path):
        ws = tmp_path / "ws"
        _write(ws / FINAL_STRUCTURE, "### 2.1 Схема именования\n")
        _write(ws / GLOSSARY, "| **Naming Convention** | x |\n")
        (ws / "__pycache__").mkdir()
        (ws / ".git").mkdir()
        assert check_naming_convention(ws) == [***REMOVED***

    def test_duplicate_dir_suffix(self, tmp_path: Path):
        ws = tmp_path / "ws"
        _write(ws / FINAL_STRUCTURE, "### 2.1 Схема именования\n")
        (ws / "alpha_01").mkdir()
        (ws / "beta_01").mkdir()
        issues = check_naming_convention(ws)
        assert any(i["kind"***REMOVED*** == "dir" and i.get("number") == "01" for i in issues)

    def test_unique_dir_suffixes_ok(self, tmp_path: Path):
        ws = tmp_path / "ws"
        _write(ws / FINAL_STRUCTURE, "### 2.1 Схема именования\n")
        _write(ws / GLOSSARY, "| **Naming Convention** | x |\n")
        (ws / "alpha_01").mkdir()
        (ws / "beta_02").mkdir()
        assert check_naming_convention(ws) == [***REMOVED***

    def test_prompt_name_violation(self, tmp_path: Path):
        ws = tmp_path / "ws"
        _write(ws / FINAL_STRUCTURE, "### 2.1 Схема именования\n")
        prompts = ws / "pompts_11"
        prompts.mkdir()
        _write(prompts / "README.md", "# readme\n")
        issues = check_naming_convention(ws)
        assert any(i["kind"***REMOVED*** == "prompt" and i["name"***REMOVED*** == "README.md" for i in issues)

    def test_prompt_invalid_theme_code(self, tmp_path: Path):
        ws = tmp_path / "ws"
        _write(ws / FINAL_STRUCTURE, "### 2.1 Схема именования\n")
        prompts = ws / "pompts_11"
        prompts.mkdir()
        _write(prompts / "099_99_bad_theme.md", "# prompt\n")
        issues = check_naming_convention(ws)
        assert any(i["kind"***REMOVED*** == "prompt" and i["theme"***REMOVED*** == "99" for i in issues)

    def test_prompt_duplicate_number(self, tmp_path: Path):
        ws = tmp_path / "ws"
        _write(ws / FINAL_STRUCTURE, "### 2.1 Схема именования\n")
        prompts = ws / "pompts_11"
        prompts.mkdir()
        _write(prompts / "001_01_first.md", "# a\n")
        _write(prompts / "001_02_second.md", "# b\n")
        issues = check_naming_convention(ws)
        assert any(i["kind"***REMOVED*** == "prompt" and i.get("number") == "001" for i in issues)

    def test_prompt_gaps_allowed(self, tmp_path: Path):
        """Гэпы в номерах (018–021/035) — намеренные, не нарушение."""
        ws = tmp_path / "ws"
        _write(ws / FINAL_STRUCTURE, "### 2.1 Схема именования\n")
        _write(ws / GLOSSARY, "| **Naming Convention** | x |\n")
        prompts = ws / "pompts_11"
        prompts.mkdir()
        _write(prompts / "001_01_first.md", "# a\n")
        _write(prompts / "003_01_third.md", "# c\n")
        assert check_naming_convention(ws) == [***REMOVED***

    def test_missing_final_structure_section(self, tmp_path: Path):
        ws = tmp_path / "ws"
        _write(ws / FINAL_STRUCTURE, "# FINAL STRUCTURE без секции именования\n")
        issues = check_naming_convention(ws)
        assert any(i.get("doc") == "FINAL_STRUCTURE.md" for i in issues)

    def test_missing_final_structure_file(self, tmp_path: Path):
        issues = check_naming_convention(tmp_path)
        assert any(i.get("doc") == "FINAL_STRUCTURE.md" for i in issues)

    def test_missing_glossary_term(self, tmp_path: Path):
        """Второй якорь: термин «Naming Convention» обязан быть в GLOSSARY.md."""
        ws = tmp_path / "ws"
        _write(ws / FINAL_STRUCTURE, "### 2.1 Схема именования\n")
        _write(ws / GLOSSARY, "# GLOSSARY\n| **Workspace** | x |\n")
        issues = check_naming_convention(ws)
        assert any(i.get("doc") == "GLOSSARY.md" for i in issues)


class TestCountTestFunctions:
    def test_counts_test_functions(self, tmp_path: Path):
        ws = tmp_path / "ws"
        _write(ws / "tests_09/test_sample.py", "def test_one(): pass\ndef test_two(): pass\n")
        assert count_test_functions(ws) == 2

    def test_counts_recursively(self, tmp_path: Path):
        ws = tmp_path / "ws"
        _write(ws / "tests_09/test_sample.py", "def test_one(): pass\n")
        _write(ws / "tests_09/core/test_core.py", "def test_alpha(): pass\ndef test_beta(): pass\n")
        assert count_test_functions(ws) == 3

    def test_ignores_non_test_functions(self, tmp_path: Path):
        ws = tmp_path / "ws"
        _write(ws / "tests_09/test_sample.py", "def helper(): pass\ndef test_one(): pass\n")
        assert count_test_functions(ws) == 1

    def test_handles_async_tests(self, tmp_path: Path):
        ws = tmp_path / "ws"
        _write(ws / "tests_09/test_async.py", "async def test_async_one(): pass\n")
        assert count_test_functions(ws) == 1

    def test_no_tests_dir_returns_zero(self, tmp_path: Path):
        assert count_test_functions(tmp_path) == 0


class TestPytestCollectionVisitor:
    """[5.39.2***REMOVED*** Regression-gate для `_PytestCollectionVisitor` (consistency_check).

    Защищает от регрессии в фильтре AST test-functions
    (helper-class / fixture / private / TestCase subclass / async edges),
    плюс e2e invariant на реальном PROJECT_ROOT, чтобы gap не вернулся.

    Если кто-то завтра снова введёт `class TestX` дубликат в одном модуле или
    сломает `_decorator_is` для `@pytest.fixture`, e2e ловит на pre-commit / CI,
    а не на проде.
    """

    def test_visitor_counts_module_level_function(self) -> None:
        v = V("synthetic.py")
        v.visit(ast.parse("def test_one(): pass\ndef test_two():\n    pass\n"))
        assert v.count == 2
        assert v.exclusions == [***REMOVED***

    def test_visitor_counts_test_prefixed_class_method(self) -> None:
        v = V("synthetic.py")
        v.visit(ast.parse(
            "class TestHealth:\n"
            "    def test_endpoint_returns_200(self):\n        pass\n"
            "    def test_endpoint_returns_500(self):\n        pass\n"
        ))
        assert v.count == 2
        assert v.exclusions == [***REMOVED***

    def test_visitor_skips_helper_class_method(self) -> None:
        v = V("synthetic.py")
        v.visit(ast.parse(
            "class IntegrationHelper:\n"
            "    def test_internal_logic(self):\n        pass\n"
        ))
        assert v.count == 0
        assert len(v.exclusions) == 1
        assert "IntegrationHelper" in v.exclusions[0***REMOVED***["reason"***REMOVED***

    def test_visitor_skips_pytest_fixture_decorated(self) -> None:
        v = V("synthetic.py")
        v.visit(ast.parse(
            "import pytest\n"
            "@pytest.fixture\n"
            "def test_fixture_helper():\n    yield None\n"
        ))
        assert v.count == 0
        assert len(v.exclusions) == 1
        assert "fixture" in v.exclusions[0***REMOVED***["reason"***REMOVED***.lower()

    def test_visitor_counts_unittest_testcase_subclass(self) -> None:
        v = V("synthetic.py")
        v.visit(ast.parse(
            "import unittest\n"
            "class LegacyTC(unittest.TestCase):\n"
            "    def test_legacy_method(self):\n        pass\n"
        ))
        assert v.count == 1
        assert v.exclusions == [***REMOVED***

    def test_visitor_counts_async_module_level(self) -> None:
        v = V("synthetic.py")
        v.visit(ast.parse("async def test_async_one(): pass\n"))
        assert v.count == 1
        assert v.exclusions == [***REMOVED***

    def test_visitor_silently_skips_non_test_prefixed_methods(self) -> None:
        """Методы без префикса `test_` молча игнорируются (ни counted, ни excluded).

        Visitor занимается только pytest-collectible, не всеми `def`-ами. Имена
        `_test_*` тоже silent skip, потому что не начинаются с `test_`
        (начинаются с `_test`). Это OK — visitor не пишет шум про intent-not-test
        методы. Dead branch `_test` exclusion в `_evaluate` оставлен как
        стражение причинения (появится кто-то вытрет — этот тест докажет, что
        удаление безопасное).
        """
        v = V("synthetic.py")
        v.visit(ast.parse(
            "class TestOuter:\n"
            "    def test_collectible(self):\n        pass\n"
            "    def helper_method(self):\n        pass\n"
            "    def _test_private_helper(self):\n        pass\n"
        ))
        assert v.count == 1, f"only test_collectible должен считаться, got {v.count***REMOVED***"
        assert v.exclusions == [***REMOVED***, (
            f"non-test_-prefixed не должны попадать в exclusions, got {v.exclusions***REMOVED***"
        )

    def test_count_test_functions_matches_pytest_collect_only_on_real_project(self) -> None:
        """e2e invariant: для PROJECT_ROOT AST count == pytest --collect-only count (deduped).

        Парсит pytest output ТАК ЖЕ как `diagnose_test_count_gap` (strip `[...***REMOVED***` brackets,
        dedup by `(file_basename, class_chain, func_name)`). Это настоящий gap-closure
        contract: parametrize-экспансия не раздувает счётчик, потому что все
        расширения одного `test_x` dedup'ятся в одну set-entry. Это и есть
        то, что `[5.39.2***REMOVED***` закрыл.
        """
        import subprocess

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests_09/",
                "--collect-only",
                "-q",
                "--no-header",
            ***REMOVED***,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            shell=False,  # CQS §3.1 regression-guard (explicit even though default)
        )

        # Reproduce Set-A vs Set-B matching from diagnose_test_count_gap.
        pytest_set: set[tuple[str, str, str***REMOVED******REMOVED*** = set()
        for line in result.stdout.splitlines():
            line = line.strip()
            if "::" not in line:
                continue
            parts = line.split("::")
            if len(parts) < 2:
                continue
            file_basename = Path(parts[0***REMOVED***).name
            test_parts = parts[1:***REMOVED***
            func_with_params = test_parts[-1***REMOVED***
            func_name = (
                func_with_params.split("[", 1)[0***REMOVED***
                if "[" in func_with_params else func_with_params
            )
            chain = test_parts[:-1***REMOVED***
            pytest_set.add((file_basename, _chain_key(chain), func_name))

        ast_count = count_test_functions(PROJECT_ROOT)
        pytest_count = len(pytest_set)
        assert ast_count == pytest_count, (
            f"AST/pytest (deduped) gap в PROJECT_ROOT: AST={ast_count***REMOVED*** vs "
            f"pytest={pytest_count***REMOVED***. Типичные причины: (1) дубль class TestX в "
            f"одном модуле (pytest collects only last), (2) visitor regex bug, "
            f"(3) class_chain/string desync в _chain_key. Если это parametrize "
            f"inflation — вычисли AST/pytest по set, а не по raster lines."
        )


class TestCheckTestCounter:
    def _seed_consistent(self, ws: Path, n: int = 3) -> None:
        """tests_09 с n тестами + CHANGELOG/CQS с совпадающим счётчиком n."""
        tests = "\n".join(f"def test_{i***REMOVED***(): pass\n" for i in range(n))
        _write(ws / "tests_09/test_sample.py", tests)
        _write(
            ws / CHANGELOG,
            f"## [0.0.0***REMOVED***\n- `python -m pytest tests_09/ -q` — **{n***REMOVED*** passed, 0 failures**\n",
        )
        _write(
            ws / CODE_QUALITY_STANDARD,
            f"| 11.6 | Регрессионные тесты | (цель: {n***REMOVED***+ passed, 0 failures) |\n",
        )

    def test_all_clean(self, tmp_path: Path):
        ws = tmp_path / "ws"
        self._seed_consistent(ws, n=3)
        assert check_test_counter(ws) == [***REMOVED***

    def test_changelog_stale(self, tmp_path: Path):
        ws = tmp_path / "ws"
        self._seed_consistent(ws, n=3)
        _write(
            ws / CHANGELOG,
            "## [0.0.0***REMOVED***\n- `python -m pytest tests_09/ -q` — **2 passed, 0 failures**\n",
        )
        issues = check_test_counter(ws)
        assert any(i["doc"***REMOVED*** == "CHANGELOG.md" and i.get("documented") == 2 for i in issues)

    def test_picks_newest_version_even_if_order_broken(self, tmp_path: Path):
        """Keep a Changelog: счётчик берётся из секции с МАКСИМАЛЬНОЙ версией,
        даже если новейшая секция случайно расположена ниже (устойчивость)."""
        ws = tmp_path / "ws"
        self._seed_consistent(ws, n=3)
        _write(
            ws / CHANGELOG,
            "## [5.34.0***REMOVED***\n- `python -m pytest tests_09/ -q` — **2 passed, 0 failures**\n\n"
            "---\n\n"
            "## [5.35.0***REMOVED***\n- `python -m pytest tests_09/ -q` — **3 passed, 0 failures**\n",
        )
        assert check_test_counter(ws) == [***REMOVED***

    def test_target_stale(self, tmp_path: Path):
        ws = tmp_path / "ws"
        self._seed_consistent(ws, n=3)
        _write(
            ws / CODE_QUALITY_STANDARD,
            "| 11.6 | Регрессионные тесты | (цель: 2+ passed, 0 failures) |\n",
        )
        issues = check_test_counter(ws)
        assert any(i["doc"***REMOVED*** == "CODE_QUALITY_STANDARD.md" and i.get("target") == 2 for i in issues)

    def test_missing_changelog_line(self, tmp_path: Path):
        ws = tmp_path / "ws"
        self._seed_consistent(ws, n=3)
        _write(ws / CHANGELOG, "## [0.0.0***REMOVED***\n- Прочие изменения\n")
        issues = check_test_counter(ws)
        assert any(i["doc"***REMOVED*** == "CHANGELOG.md" and "not found" in i["issue"***REMOVED*** for i in issues)

    def test_missing_target_line(self, tmp_path: Path):
        ws = tmp_path / "ws"
        self._seed_consistent(ws, n=3)
        _write(ws / CODE_QUALITY_STANDARD, "| 11.6 | Регрессионные тесты | без цели |\n")
        issues = check_test_counter(ws)
        assert any(i["doc"***REMOVED*** == "CODE_QUALITY_STANDARD.md" and "not found" in i["issue"***REMOVED*** for i in issues)

    def test_missing_registries_skipped(self, tmp_path: Path):
        """Нет CHANGELOG/CQS — проверка пропускается (нет якорей для сверки)."""
        ws = tmp_path / "ws"
        _write(ws / "tests_09/test_sample.py", "def test_one(): pass\n")
        assert check_test_counter(ws) == [***REMOVED***

    def test_report_includes_test_counter_key(self, workspace: Path):
        report = build_report(workspace)
        assert "test_counter" in report


class TestReport:
    def test_build_report_consistent(self, workspace: Path):
        report = build_report(workspace)
        assert report["consistent"***REMOVED*** is True
        assert report["total_issues"***REMOVED*** == 0

    def test_build_report_detects_issues(self, tmp_path: Path):
        report = build_report(tmp_path)
        assert report["consistent"***REMOVED*** is False
        assert report["total_issues"***REMOVED*** > 0

    def test_build_report_includes_naming_convention_key(self, workspace: Path):
        report = build_report(workspace)
        assert "naming_convention" in report
        assert report["naming_convention"***REMOVED*** == [***REMOVED***

    def test_run_consistency_check_accepts_str(self, workspace: Path):
        report = run_consistency_check(str(workspace))
        assert report["consistent"***REMOVED*** is True

    def test_main_exit_zero_when_consistent(self, workspace: Path, monkeypatch):
        from scripts_01.consistency_check import main

        monkeypatch.setattr(sys, "argv", ["consistency_check.py", "--workspace", str(workspace)***REMOVED***)
        assert main() == 0

    def test_main_exit_one_when_inconsistent(self, tmp_path: Path, monkeypatch):
        from scripts_01.consistency_check import main

        monkeypatch.setattr(sys, "argv", ["consistency_check.py", "--workspace", str(tmp_path)***REMOVED***)
        assert main() == 1


# ═══════════════════════════════════════════════════════════════
# Real-project integration
# ═══════════════════════════════════════════════════════════════


class TestRealWorkspaceConsistent:
    """[5.39.2 rename***REMOVED*** вторая группа с именем TestRealProject теневая первой
    (TestRealProject на строке 381 несёт 12 test_* методов). pytest собирает
    только последний класс с уникальным именем в модуле → первая группа
    становилась ast_only phantom в [5.39.0***REMOVED*** consistency_check. Теперь обе
    группы под уникальными именами, pytest собирает все 13, gap == 0."""

    def test_real_project_consistent(self):
        """Фактический проект должен проходить проверку (все реестры согласованы)."""
        report = build_report(PROJECT_ROOT)
        assert report["consistent"***REMOVED*** is True, format(report["total_issues"***REMOVED***)
