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
import json
import sys
***REMOVED***

import yaml


def _write_yaml(path: Path, data: dict) -> None:
    """v5.189.51: helper for backfill_signature tests — minimal registry YAML."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


# v5.189.51: import check under test + SEED list for the exemption test.
from scripts_01.consistency_check import (  # noqa: E402
    check_backfill_signatures as check_backfill_signature,
)
from core_02.missing_registry import _SEED as _MR_SEED  # noqa: E402

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts_01.consistency_check import (
    build_report,
    check_cross_references,
    check_engine_files,
    check_glossary_terms,
    check_lifecycle_coverage,
    check_missing_registry_sync,
    check_module_areas,
    check_naming_convention,
    check_project_book,
    check_roadmap_refs,
    check_test_counter,
    count_test_functions,
    extract_engine_rows,
    extract_missing_capabilities,
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


# ── pytest --collect-only cross-session cache (v5.189.10 speedup) ──────────
# Реальный `pytest --collect-only` на tests_09/ стоит 39.5s. Кэш в /tmp с
# fingerprint-ом (mtime/size тестовых файлов + conftest + pytest.ini):
# пересборка только когда тесты реально изменились, иначе — повторное
# использование из предыдущей сессии.

_COLLECT_CACHE_PREFIX = "freebuff_pytest_collect_ids"


def _collect_fingerprint() -> str:
    """SHA-256 по mtime/size тестовых файлов — ключ инвалидации кэша."""
    import hashlib

    # rglob — покрывает и tests_09/core/ (вложенные тест-модули): иначе
    # изменение там не инвалидировало бы кэш (reviewer CR v5.189.12).
    h = hashlib.sha256()
    targets = sorted((PROJECT_ROOT / "tests_09").rglob("*.py"))
    targets += [
        PROJECT_ROOT / "tests_09" / "conftest.py",
        PROJECT_ROOT / "pytest.ini",
    ***REMOVED***
    for p in targets:
        try:
            st = p.stat()
            h.update(f"{p.name***REMOVED***:{st.st_mtime_ns***REMOVED***:{st.st_size***REMOVED***;".encode("utf-8"))
        except OSError:
            h.update(f"{p.name***REMOVED***:missing;".encode("utf-8"))
    return h.hexdigest()[:16***REMOVED***


def _collect_only_stdout_lines() -> list[str***REMOVED***:
    """`pytest --collect-only -q` stdout lines (кэш в /tmp по fingerprint)."""
    cache_file = Path("/tmp") / f"{_COLLECT_CACHE_PREFIX***REMOVED***_{_collect_fingerprint()***REMOVED***.json"
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            pass  # битый кэш → пересборка

    import subprocess

    # Retry ×2: под параллельной нагрузкой (xdist/другие прогоны) collect может
    # транзиентно упасть (rc!=0, часть модулей не собралась) — повторяем один
    # раз; кэшируем ТОЛЬКО успешный прогон (v5.189.12 hardening).
    lines: list[str***REMOVED*** = [***REMOVED***
    result = None
    for _attempt in (1, 2):
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
        if result.returncode == 0:
            lines = result.stdout.splitlines()
            break
    if result is None or result.returncode != 0:
        raise RuntimeError(
            f"pytest --collect-only failed (rc={result.returncode if result else '?'***REMOVED***): "
            f"{result.stderr[:300***REMOVED*** if result else 'no run'!r***REMOVED***"
        )
    try:
        cache_file.write_text(json.dumps(lines, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass  # кэш best-effort
    return lines


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
    # §20 карты v1.1 + MissingRegistry — синхронизированы (проверка missing_registry_sync).
    _write(ws / "docs_10/engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md", _S20_DOC)
    from core_02.missing_registry import MissingRegistry, seed_defaults
    seed_defaults(MissingRegistry(ws / "data_13/missing_registry.yaml"))
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
# 10. Missing Registry sync (§20 карты v1.1 ↔ data_13/missing_registry.yaml)
# ═══════════════════════════════════════════════════════════════


_S20_DOC = """## 20. Missing Capabilities

| # | Отсутствующая способность | Где нужна | Приоритет |
|---|---------------------------|-----------|-----------|
| 1 | **Factory Registry** (реестр фабрик и кузен, статусы, паспорта) | Каждая Factory | 🟡 Medium — 📋 **дизайн готов** (FORGE_PASSPORT_CODE_REPRESENTATION_V1.md) |
| 2 | **Scenario Engine** (исполнение сценариев-композиторов поверх Factory) | Workspace OS | 🟡 Medium — 📋 **дизайн готов** (SCENARIO_ENGINE_DESIGN_V1.md) |
| 3 | **ADR-реестр как структура данных** (Decision Registry) | Decision Forge | 🟡 Medium |
| 4 | **Машиночитаемый Conformance checker** | Governance Forge | 🟡 Medium |
| 5 | **Автогенерация моделей/диаграмм** | Modeling Forge | 🟢 Low |
| 6 | **Web Research (`research_web`)** — веб-исследование | Research Factory | 🟢 Low — ✅ **реализовано** (scripts_01/research_web.py) |
| 7 | **Estimation (`lisa_estimator`)** — оценка сложности | Research Factory | 🟡 Medium — ✅ **реализовано** (scripts_01/lisa_estimator.py, по промту pompts_11/076_13_lisa_estimator_capability.md) |
"""


class TestExtractMissingCapabilities:
    def test_parses_all_rows(self):
        items = extract_missing_capabilities(_S20_DOC)
        assert len(items) == 7
        ids = {i["item_id"***REMOVED*** for i in items***REMOVED***
        assert ids == {
            "factory_registry", "scenario_engine", "decision_registry",
            "conformance_checker", "model_diagram_autogen",
            "research_web", "lisa_estimator",
        ***REMOVED***

    def test_status_mapping(self):
        items = {i["item_id"***REMOVED***: i["status"***REMOVED*** for i in extract_missing_capabilities(_S20_DOC)***REMOVED***
        assert items["research_web"***REMOVED*** == "implemented"
        assert items["lisa_estimator"***REMOVED*** == "implemented"
        assert items["factory_registry"***REMOVED*** == "design_ready"
        assert items["decision_registry"***REMOVED*** == "registered"

    def test_no_section_returns_empty(self):
        assert extract_missing_capabilities("# No §20 here") == [***REMOVED***


class TestCheckMissingRegistrySync:
    def _workspace(self, tmp_path: Path, doc: str = _S20_DOC) -> Path:
        ws = tmp_path / "ws"
        _write(ws / "docs_10/engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md", doc)
        from core_02.missing_registry import MissingRegistry, seed_defaults
        reg = MissingRegistry(ws / "data_13/missing_registry.yaml")
        seed_defaults(reg)
        return ws

    def test_all_synced(self, tmp_path: Path):
        assert check_missing_registry_sync(self._workspace(tmp_path)) == [***REMOVED***

    def test_missing_doc(self, tmp_path: Path):
        ws = tmp_path / "ws"
        issues = check_missing_registry_sync(ws)
        assert issues and issues[0***REMOVED***["check"***REMOVED*** == "missing_registry_sync"
        assert "missing" in issues[0***REMOVED***["issue"***REMOVED***.lower()

    def test_missing_registry_file(self, tmp_path: Path):
        ws = tmp_path / "ws"
        _write(ws / "docs_10/engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md", _S20_DOC)
        issues = check_missing_registry_sync(ws)
        assert any("missing_registry.yaml" in i["issue"***REMOVED*** for i in issues)

    def test_doc_item_missing_from_registry(self, tmp_path: Path):
        doc = _S20_DOC + "| 8 | **Ghost Tool (`ghost_tool`)** | Research Factory | 🟡 Medium |\n"
        issues = check_missing_registry_sync(self._workspace(tmp_path, doc))
        ghost = [i for i in issues if i.get("item") == "ghost_tool"***REMOVED***
        assert len(ghost) == 1
        assert "register-first" in ghost[0***REMOVED***["issue"***REMOVED***

    def test_registry_item_missing_from_doc(self, tmp_path: Path):
        ws = self._workspace(tmp_path)
        from core_02.missing_registry import MissingRegistry
        reg = MissingRegistry(ws / "data_13/missing_registry.yaml")
        reg.register_missing("extra_tool", kind="tool", factory="code")
        issues = check_missing_registry_sync(ws)
        extra = [i for i in issues if i.get("item") == "extra_tool"***REMOVED***
        assert len(extra) == 1
        assert "§20" in extra[0***REMOVED***["issue"***REMOVED***

    def test_registry_lags_behind_doc(self, tmp_path: Path):
        ws = tmp_path / "ws"
        _write(ws / "docs_10/engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md", _S20_DOC)
        from core_02.missing_registry import MissingRegistry
        reg = MissingRegistry(ws / "data_13/missing_registry.yaml")
        reg.register_missing("research_web", kind="tool", factory="research",
                             status="registered")  # §20 говорит «реализовано»
        issues = check_missing_registry_sync(ws)
        lag = [i for i in issues if i.get("item") == "research_web"***REMOVED***
        assert any("lags behind" in i["issue"***REMOVED*** for i in lag)


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


class TestNamingConventionEvaluationPackage:
    """[v5.189.68***REMOVED*** Evaluation-пакеты с каноническим именем от промта-источника.

    Каталог `architecture_forensics_v2/` назван ИМЕННО так по требованию
    promt104 §28 REQUIRED OUTPUT (без NN-suffix). Переименование сломало бы
    имя пакета/архива и противоречило бы промту — поэтому naming_convention
    пропускает его через _EVALUATION_PACKAGE_DIRS. Не маскирует настоящие
    нарушения: произвольный bare-dir вне списка по-прежнему флагуется.
    """

    def _approve_env(self, root: Path) -> None:
        """Минимальное окружение для naming-проверки (два якоря + pompts_11)."""
        (root / "pompts_11").mkdir()
        (root / "pompts_11" / "001_01_dummy.md").write_text("# dummy\n")
        docs = root / "docs_10" / "core"
        docs.mkdir(parents=True)
        (docs / "FINAL_STRUCTURE.md").write_text("## §2.1 Схема именования\n")
        (docs / "GLOSSARY.md").write_text("## **Naming Convention**\n")

    def test_evaluation_package_dir_skipped(self, tmp_path: Path) -> None:
        self._approve_env(tmp_path)
        (tmp_path / "architecture_forensics_v2").mkdir()
        from scripts_01.consistency_check import check_naming_convention
        issues = check_naming_convention(tmp_path)
        pkg = [i for i in issues if i.get("kind") == "dir" and i.get("name") == "architecture_forensics_v2"***REMOVED***
        assert pkg == [***REMOVED***, (
            f"evaluation-package dir должен пропускаться (имя от промта), issues={issues***REMOVED***"
        )

    def test_non_declared_bare_dir_still_flagged(self, tmp_path: Path) -> None:
        """Произвольный bare-dir вне _EVALUATION_PACKAGE_DIRS — обычное нарушение."""
        self._approve_env(tmp_path)
        (tmp_path / "random_package_v2").mkdir()
        from scripts_01.consistency_check import check_naming_convention
        issues = check_naming_convention(tmp_path)
        flagged = [i for i in issues if i.get("kind") == "dir" and i.get("name") == "random_package_v2"***REMOVED***
        assert len(flagged) == 1, (
            f"недекларированный bare-dir должен флагуться, issues={issues***REMOVED***"
        )
        assert flagged[0***REMOVED***["issue"***REMOVED***.startswith("top-level dir violates")

    def test_evaluation_package_dirs_constant_defined(self) -> None:
        """Константа _EVALUATION_PACKAGE_DIRS существует и содержит пакет promt104."""
        from scripts_01.consistency_check import _EVALUATION_PACKAGE_DIRS
        assert "architecture_forensics_v2" in _EVALUATION_PACKAGE_DIRS

    def test_consolidated_forensics_dir_skipped(self, tmp_path: Path) -> None:
        """[v5.189.73***REMOVED*** Сводный forensic-архив FORENSICS_104_105_106_107 пропускается.

        Имя задано задачей (единый пакет 4 проходов); NN-suffix нарушил бы
        соответствие имени архиву FORENSICS_104_105_106_107_v5.189.73.tar.gz.
        Аналогично architecture_forensics_v2 (promt104 §28).
        """
        self._approve_env(tmp_path)
        (tmp_path / "FORENSICS_104_105_106_107").mkdir()
        from scripts_01.consistency_check import check_naming_convention
        issues = check_naming_convention(tmp_path)
        pkg = [
            i for i in issues
            if i.get("kind") == "dir" and i.get("name") == "FORENSICS_104_105_106_107"
        ***REMOVED***
        assert pkg == [***REMOVED***, (
            f"consolidated forensics dir должен пропускаться, issues={issues***REMOVED***"
        )


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
        # README.md/errors.md — служебные файлы очереди (exempt, см. skip в consistency_check)
        _write(prompts / "README.md", "# readme\n")
        _write(prompts / "errors.md", "# log\n")
        # Нарушение конвенции ловим на обычном «голом» промте
        _write(prompts / "bad_name.md", "# bare prompt\n")
        issues = check_naming_convention(ws)
        assert any(i.get("kind") == "prompt" and i.get("name") == "bad_name.md" for i in issues)
        # Служебные файлы не должны флагиться
        assert not any(i.get("name") in ("README.md", "errors.md") for i in issues)

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

    @pytest.mark.slow  # v5.189.10: cross-session кэш; первый прогон платит 39.5s
    def test_count_test_functions_matches_pytest_collect_only_on_real_project(self) -> None:
        """e2e invariant: для PROJECT_ROOT AST count == pytest --collect-only count (deduped).

        Парсит pytest output ТАК ЖЕ как `diagnose_test_count_gap` (strip `[...***REMOVED***` brackets,
        dedup by `(file_basename, class_chain, func_name)`). Это настоящий gap-closure
        contract: parametrize-экспансия не раздувает счётчик, потому что все
        расширения одного `test_x` dedup'ятся в одну set-entry. Это и есть
        то, что `[5.39.2***REMOVED***` закрыл.
        v5.189.10: subprocess заменён на `_collect_only_stdout_lines()` —
        cross-session кэш с mtime-инвалидацией (39.5s → ~0 на повторных прогонах).
        """
        # Reproduce Set-A vs Set-B matching from diagnose_test_count_gap.
        pytest_set: set[tuple[str, str, str***REMOVED******REMOVED*** = set()
        for line in _collect_only_stdout_lines():
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

    def test_build_report_includes_anchors_key(self, workspace: Path):
        """[5.189.4***REMOVED*** check #11 ANCHORS: ключ есть, на пустом workspace — пусто."""
        report = build_report(workspace)
        assert "anchors" in report
        assert report["anchors"***REMOVED*** == [***REMOVED***

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

    @pytest.mark.slow  # v5.189.10: полный AST-скан репозитория (~11s)
    def test_real_project_consistent(self):
        """Фактический проект должен проходить проверку (все реестры согласованы)."""
        report = build_report(PROJECT_ROOT)
        assert report["consistent"***REMOVED*** is True, format(report["total_issues"***REMOVED***)
    @pytest.mark.slow  # v5.189.63 drift-closure guard
    def test_build_report_idempotent_under_repeat(self) -> None:
        """[5.189.63***REMOVED*** `build_report(workspace)` MUST be idempotent: N повторных
        вызовов возвращают ОДИНАКОВЫЙ total_issues / consistent / per-check dicts.

        Защита от double-application regression (re-run loop, retry-on-fail hook):
        если consistency_check гонять в цикле, состояние gate должно оставаться
        СТАБИЛЬНЫМ — иначе closure либо улучшает (ложный успех), либо деградирует
        (ложный fail) от количества прогонов.

        Catches monotonic-drift bugs:
          (a) registry YAML file mtime changes on read → doc_by_id/version drift
          (b) AST visitor accumulates exclusions list BETWEEN calls (state leak)
          (c) backfill_signature timestamps drift across calls (timestamps != stable)
          (d) anchors resolver accumulates unverified-set between runs
        """
        reports = [build_report(PROJECT_ROOT) for _ in range(5)***REMOVED***
        first = reports[0***REMOVED***
        for nth, r in enumerate(reports[1:***REMOVED***, start=2):
            # 1. Cardinal invariant: total_issues stable.
            assert r["total_issues"***REMOVED*** == first["total_issues"***REMOVED***, (
                f"build_report not idempotent on repeat #{nth***REMOVED***: "
                f"first total_issues={first['total_issues'***REMOVED******REMOVED***, "
                f"repeat #{nth***REMOVED*** total_issues={r['total_issues'***REMOVED******REMOVED***. "
                f"Hint: check registry YAML mtime, AST cache, or "
                f"monotonic dedupe counter across calls."
            )
            # 2. Boolean consistent flag must match.
            assert r["consistent"***REMOVED*** == first["consistent"***REMOVED***, (
                f"consistent flag flipped between call 1 and call #{nth***REMOVED***: "
                f"first={first['consistent'***REMOVED******REMOVED***, repeat={r['consistent'***REMOVED******REMOVED***"
            )
            # 3. Per-check dicts MUST be deep-equal — no row accumulation/dropout.
            for check_key in ("test_counter", "missing_registry_sync",
                              "backfill_signature", "engine_files",
                              "lifecycle_coverage", "module_areas",
                              "glossary_terms", "roadmap_refs",
                              "cross_references", "project_book",
                              "naming_convention", "anchors"):
                assert r[check_key***REMOVED*** == first[check_key***REMOVED***, (
                    f"check '{check_key***REMOVED***' diverged on repeat #{nth***REMOVED***: "
                    f"first={first[check_key***REMOVED***!r***REMOVED***, repeat=#{nth***REMOVED***={r[check_key***REMOVED***!r***REMOVED***"
                )



# ─── v5.189.51: backfill_signature check — retroactive-registration heuristic ─
#
# Heuristic: scan `data_13/missing_registry.yaml` for entries that LOOK retroactive
# (status=implemented + registered_at == updated_at) WITHOUT `backfill:true`.
# Severity: WARNING (not violation) — emitted into a standalone `backfill_signature`
# key in build_report(); `consistent=True` if total_issues==0 AFTER `consistent=True`
# filter. SEED items exempt.

class TestBackfillSignature:
    """v5.189.51: contract tests for check_backfill_signatures().

    Heuristic coverage:
      - clean retroactive (status=implemented + backfill=True + same ts) → silent
      - normal lifecycle (registered_at < updated_at) → silent
      - missing `backfill` marker on retroactive signature → WARNING
      - SEED items exempt (canonical entries pre-date backfill:bool discipline)
      - non-implemented status → silent even with same ts
    """

    def test_clean_retroregistered_with_backfill_is_silent(self, tmp_path: Path) -> None:
        """Status=implemented + backfill:true + identical ts → 0 warnings (correct usage)."""
        _write_yaml(
            tmp_path / "data_13" / "missing_registry.yaml",
            {
                "retro_module": {
                    "kind": "tool",
                    "status": "implemented",
                    "factory": "test",
                    "registered_at": "2026-08-11T22:00:00+00:00",
                    "updated_at": "2026-08-11T22:00:00+00:00",
                    "backfill": True,
                ***REMOVED***
            ***REMOVED***,
        )
        warnings = check_backfill_signature(tmp_path)
        assert warnings == [***REMOVED***, f"expected silent, got: {warnings***REMOVED***"

    def test_missing_backfill_marker_on_retroactive_signature_flagged(
        self, tmp_path: Path
    ) -> None:
        """Status=implemented + no backfill + identical ts → 1 WARNING emitted."""
        _write_yaml(
            tmp_path / "data_13" / "missing_registry.yaml",
            {
                "retro_omitted": {
                    "kind": "tool",
                    "status": "implemented",
                    "factory": "test",
                    "description": "Created via `register --status implemented` (forgot --backfill).",
                    "registered_at": "2026-08-11T22:00:00+00:00",
                    "updated_at": "2026-08-11T22:00:00+00:00",
                    # backfill field explicitly absent → flagged.
                ***REMOVED***
            ***REMOVED***,
        )
        warnings = check_backfill_signature(tmp_path)
        assert len(warnings) == 1, f"expected 1 warning, got: {warnings***REMOVED***"
        w = warnings[0***REMOVED***
        assert w["check"***REMOVED*** == "backfill_signature"
        assert w["severity"***REMOVED*** == "warning"
        assert w["doc"***REMOVED*** == "data_13/missing_registry.yaml"
        assert w["item_id"***REMOVED*** == "retro_omitted"
        assert "registered_at==updated_at" in w["reason"***REMOVED***
        assert "backfill:true" in w["reason"***REMOVED***

    def test_normal_lifecycle_with_divergent_timestamps_is_silent(
        self, tmp_path: Path
    ) -> None:
        """Genuine lifecycle evolution (registered_at < updated_at) → 0 warnings."""
        _write_yaml(
            tmp_path / "data_13" / "missing_registry.yaml",
            {
                "legit_lifecycle": {
                    "kind": "tool",
                    "status": "implemented",
                    "factory": "test",
                    "registered_at": "2026-08-10T22:00:00+00:00",
                    "updated_at": "2026-08-11T22:00:00+00:00",  # +1 day → genuine lifecycle
                    "backfill": False,
                ***REMOVED***
            ***REMOVED***,
        )
        warnings = check_backfill_signature(tmp_path)
        assert warnings == [***REMOVED***, f"expected silent, got: {warnings***REMOVED***"

    def test_seed_entries_are_exempt(self, tmp_path: Path) -> None:
        """SEED items pre-date backfill:bool discipline — must NOT be flagged.

        Uses an authoritative item_id from core_02.missing_registry._SEED so
        the test follows platform evolution (we don't hardcode names).
        """
        seed_ids = [
            str(item["item_id"***REMOVED***)
            for item in (_MR_SEED or [***REMOVED***)
            if isinstance(item, dict) and "item_id" in item
        ***REMOVED***
        assert seed_ids, "test assumes _SEED is non-empty"
        sample_seed_id = seed_ids[0***REMOVED***
        _write_yaml(
            tmp_path / "data_13" / "missing_registry.yaml",
            {
                sample_seed_id: {  # canonical SEED name → exempt
                    "kind": "tool",
                    "status": "implemented",
                    "factory": "seed",
                    "registered_at": "2026-08-11T22:00:00+00:00",
                    "updated_at": "2026-08-11T22:00:00+00:00",
                    "backfill": False,
                ***REMOVED***
            ***REMOVED***,
        )
        warnings = check_backfill_signature(tmp_path)
        assert warnings == [***REMOVED***, (
            f"SEED entry {sample_seed_id!r***REMOVED*** must be exempt; got: {warnings***REMOVED***"
        )

    def test_non_implemented_status_never_flagged(self, tmp_path: Path) -> None:
        """If status != implemented (even with identical ts + no backfill), silent.

        Defensive: protects `registered`, `design_ready`, `prompt_written` entries
        from false positives (they’re IN-PROGRESS, not retroactive).
        """
        _write_yaml(
            tmp_path / "data_13" / "missing_registry.yaml",
            {
                "in_progress": {
                    "kind": "tool",
                    "status": "prompt_written",
                    "factory": "test",
                    "registered_at": "2026-08-11T22:00:00+00:00",
                    "updated_at": "2026-08-11T22:00:00+00:00",
                    "backfill": False,
                ***REMOVED***
            ***REMOVED***,
        )
        warnings = check_backfill_signature(tmp_path)
        assert warnings == [***REMOVED***, f"non-implemented must NOT be flagged; got: {warnings***REMOVED***"

    def test_aggregated_into_build_report_json(self, tmp_path: Path) -> None:
        """check_backfill_signatures() result appears as `backfill_signature` key
        in build_report() output AND contributes to total_issues count.

        Integration: ensures wiring (report dict + all_issues aggregation) works.
        """
        _write_yaml(
            tmp_path / "data_13" / "missing_registry.yaml",
            {
                "real_retro_suspect": {
                    "kind": "tool",
                    "status": "implemented",
                    "factory": "test",
                    "registered_at": "2026-08-11T22:00:00+00:00",
                    "updated_at": "2026-08-11T22:00:00+00:00",
                    "backfill": False,  # WILL be flagged
                ***REMOVED***
            ***REMOVED***,
        )
        report = build_report(tmp_path)
        assert "backfill_signature" in report, (
            f"build_report missing backfill_signature key; keys: {sorted(report)***REMOVED***"
        )
        sigs = report["backfill_signature"***REMOVED***
        assert len(sigs) == 1
        assert sigs[0***REMOVED***["item_id"***REMOVED*** == "real_retro_suspect"
        # WARNING counted as issue (consistent with severity='warning' convention).
        assert report["total_issues"***REMOVED*** >= 1
        assert report["consistent"***REMOVED*** is False  # warning flips consistent
