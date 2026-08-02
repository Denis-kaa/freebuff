#!/usr/bin/env python3
"""
consistency_check.py — Stage 9: self-consistency audit (registries as data).

Проверяет, что канонические реестры (документы-источники истины) согласованы
между собой и с кодовой базой:

  1. ENGINE FILES       — каждый движок из ARCHITECTURE_CANONICAL §3 имеет файл в scripts_01/
  2. LIFECYCLE COVERAGE — каждый движок из реестра описан в LIFECYCLE.md
  3. MODULE AREAS       — все 10 областей консолидации покрыты в MODULE_CONSOLIDATION.md
  4. GLOSSARY TERMS     — все 16 обязательных терминов присутствуют в GLOSSARY.md
  5. ROADMAP REFS       — файлы, на которые ссылается ROADMAP_PROMT32, существуют
  6. CROSS REFERENCES   — канонические документы ссылаются друг на друга (взаимно)
  7. PROJECT BOOK       — PROJECT_BOOK.md существует и связан с реестрами (несоответствие
                          Roadmap/Registry/Project Book не проходит незамеченным)
  8. NAMING CONVENTION  — каталоги `имя_NN`, промты `NNN_TT_имя` (FINAL_STRUCTURE §2.1
                          + термин «Naming Convention» в GLOSSARY.md — два якоря);
                          само правило не может исчезнуть из документации
  9. TEST COUNTER       — счётчик тестов в CHANGELOG.md и CODE_QUALITY_STANDARD.md
                          (правило 11.6) совпадает с реальным числом test-функций
                          в tests_09/ (AST-подсчёт) — реестры не расходятся с кодом

Роль: инструмент Этапа 9 консолидации (promt32) — «реестры как данные для проверки».
Не изменяет код/документы автоматически.

Ограничения (осознанные):
  - check_module_areas / check_glossary_terms используют substring-поиск
    (область «Memory» находится внутри «MemoryEngine»). Это проверка ПОКРЫТИЯ,
    а не точного соответствия секций/строк таблиц — строгий разбор заголовков
    (например, `### A. Router`) будет усилением в будущем.
  - check_cross_references проверяет ВЗАИМНЫЕ УПОМИНАНИЯ имён документов,
    а не синтаксис markdown-ссылок `[...***REMOVED***(...)` — битые ссылки как таковые
    детектит scripts_01/drift_check.py (link checker).
  - check_project_book тоже mention-based: достаточно вхождения
    «PROJECT_BOOK»/«Project Book» в MANIFEST/ROADMAP (в т.ч. в таблицах
    запретов), а не обязательной markdown-ссылки на файл.

Использование:
    python scripts_01/consistency_check.py            # запуск, exit 0/1
    python scripts_01/consistency_check.py --report   # печать отчёта в stdout
    python scripts_01/consistency_check.py --json     # JSON-отчёт
"""
from __future__ import annotations

import argparse
import ast
import json
***REMOVED***
import sys
from datetime import datetime, timezone
***REMOVED***
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Канонические реестры (источники истины) ──────────────────────────
CANONICAL = Path("docs_10/core/ARCHITECTURE_CANONICAL.md")
LIFECYCLE = Path("docs_10/core/LIFECYCLE.md")
MODULE_CONSOLIDATION = Path("docs_10/core/MODULE_CONSOLIDATION.md")
GLOSSARY = Path("docs_10/core/GLOSSARY.md")
MANIFEST = Path("docs_10/core/ARCHITECTURE_MANIFEST.md")
ROADMAP = Path("docs_10/vision/ROADMAP_PROMT32_CONSOLIDATION.md")
PROJECT_BOOK = Path("docs_10/engineering-memory/PROJECT_BOOK.md")
FINAL_STRUCTURE = Path("docs_10/core/FINAL_STRUCTURE.md")
CHANGELOG = Path("CHANGELOG.md")
CODE_QUALITY_STANDARD = Path("docs_10/core/CODE_QUALITY_STANDARD.md")

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

# Схема именования (FINAL_STRUCTURE §2.1): каталоги `имя_NN`, промты `NNN_TT_имя`.
#   - Имя каталога: буквы/цифры/`_`/`-`, суффикс `_NN` (NN — двузначный ID).
#   - Промт: `NNN_TT_имя.md` (NNN — хронологический номер, TT — код темы 01..14).
_TOP_LEVEL_DIR_RE = re.compile(r"^[a-z0-9***REMOVED***[a-z0-9_-***REMOVED****_\d{2***REMOVED***$")
_PROMPT_FILE_RE = re.compile(r"^(\d{3***REMOVED***)_(\d{2***REMOVED***)_[a-z0-9_***REMOVED***+\.md$")
_VALID_THEME_CODES = {f"{i:02d***REMOVED***" for i in range(1, 15)***REMOVED***
# Системные/скрытые каталоги, не подпадающие под схему именования.
_SKIP_DIR_PREFIXES = (".", "__")
# Legacy top-level redirect-shim'ы (Этап 4 консолидации, промт 32): существуют только
# как backward-compat forwarder'ы на канонические каталоги с NN-suffix'ом.
# Проверка naming_convention пропускает их, если указанный canonical_dir существует
# — закрывает ложное нарушение `имя_NN` от pre-rename shell history / tmux send-keys.
# Паттерн зеркалит scripts_01/drift_check.py::_LEGACY_TOP_LEVEL_REDIRECTS.
_LEGACY_TOP_LEVEL_REDIRECTS: dict[str, tuple[str, ...***REMOVED******REMOVED*** = {
    "freebuff_plugin": ("freebuff_plugin_03",),
***REMOVED***


# 10 областей консолидации (Этап 6).
CONSOLIDATION_AREAS = [
    "Router", "Telegram", "MCP", "Memory", "Knowledge", "Registry",
    "Context", "Tool Runtime", "Plugin API", "Event Bus",
***REMOVED***

# Заголовки секций реестра движков в ARCHITECTURE_CANONICAL.
_ENGINE_ROW_RE = re.compile(
    r"^\|\s*(C\d+|S\d+)\s*\|\s*`([A-Za-z***REMOVED***+)`\s*\|\s*`(scripts_01/[a-z0-9_***REMOVED***+\.py)`"
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
    """Каждый движок из canonical имеет файл в scripts_01/."""
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
    refs |= set(re.findall(r"(docs_10/[\w./\-***REMOVED***+\.md)", text))
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
      1. PROJECT_BOOK.md существует в docs_10/engineering-memory/
      2. На него ссылается ARCHITECTURE_MANIFEST (канонический реестр)
      3. Он упоминается в ROADMAP_PROMT32 (план работ)
    """
    issues: list[dict[str, Any***REMOVED******REMOVED*** = [***REMOVED***

    text = _read(workspace, PROJECT_BOOK)
    if text is None:
        return [{"check": "project_book", "issue": "PROJECT_BOOK.md missing in docs_10/engineering-memory/"***REMOVED******REMOVED***

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
# 8. Naming convention
# ═══════════════════════════════════════════════════════════════


def _top_level_dir_names(workspace: Path) -> list[str***REMOVED***:
    """Имена top-level каталогов (без скрытых и системных)."""
    names: list[str***REMOVED*** = [***REMOVED***
    try:
        for child in workspace.iterdir():
            if not child.is_dir():
                continue
            name = child.name
            if name.startswith(_SKIP_DIR_PREFIXES):
                continue
            names.append(name)
    except OSError:
        pass
    return sorted(names)


def _is_legacy_redirect_satisfied(workspace: Path, top_dir: str) -> bool:
    """Top-level dir — backward-compat shim, если указан canonical существует.

    Паттерн зеркалит scripts_01/drift_check.py::_is_legacy_redirect_satisfied (5.37.1).
    Возвращает True, если `top_dir` в `_LEGACY_TOP_LEVEL_REDIRECTS` И хотя бы один
    из `canonical_targets` существует в workspace. Иначе — False (shim не
    функционален без canonical → должен быть заменён или удалён).
    """
    canonical_targets = _LEGACY_TOP_LEVEL_REDIRECTS.get(top_dir)
    if not canonical_targets:
        return False
    for target in canonical_targets:
        if (workspace / target).is_dir():
            return True
    return False


def check_naming_convention(workspace: Path) -> list[dict[str, Any***REMOVED******REMOVED***:
    """Схема именования (FINAL_STRUCTURE §2.1): каталоги `имя_NN`, промты `NNN_TT_имя`.

    Проверяет:
      1. Каждый top-level каталог (кроме скрытых/системных) следует `имя_NN`,
         суффикс-ID `_NN` уникален (FINAL_STRUCTURE присваивает номера 01..22).
      2. Каждый промт в pompts_11/ следует `NNN_TT_имя.md` с валидным кодом темы (01..14).
      3. Номера промтов уникальны (гэпы допустимы — 018–021/035 не существовали;
         дубли номеров — нарушение).
      4. Само правило задокументировано в FINAL_STRUCTURE.md §2.1 и закреплено
         термином «Naming Convention» в GLOSSARY.md (две точки якоря — не потеряется).
    """
    issues: list[dict[str, Any***REMOVED******REMOVED*** = [***REMOVED***

    # 1. Top-level каталоги: имя_NN + уникальность суффикса-ID
    seen_dir_suffixes: set[str***REMOVED*** = set()
    for name in _top_level_dir_names(workspace):
        # 1.0 Legacy top-level redirect-shim (Этап 4) — пропускаем, если canonical существует.
        #     Иначе (shim сирота) — флагуем как обычное нарушение `имя_NN`.
        if _is_legacy_redirect_satisfied(workspace, name):
            continue
        if not _TOP_LEVEL_DIR_RE.match(name):
            issues.append({
                "check": "naming_convention",
                "kind": "dir",
                "name": name,
                "issue": "top-level dir violates 'имя_NN' convention (FINAL_STRUCTURE §2.1)",
            ***REMOVED***)
            continue
        suffix = name.rsplit("_", 1)[1***REMOVED***
        if suffix in seen_dir_suffixes:
            issues.append({
                "check": "naming_convention",
                "kind": "dir",
                "name": name,
                "number": suffix,
                "issue": "duplicate dir suffix _NN (FINAL_STRUCTURE §2.1 assigns unique IDs)",
            ***REMOVED***)
        seen_dir_suffixes.add(suffix)

    # 2–3. Промты: формат NNN_TT_имя.md, код темы, уникальность номера
    prompts_dir = workspace / "pompts_11"
    seen_numbers: set[str***REMOVED*** = set()
    if prompts_dir.is_dir():
        for path in sorted(prompts_dir.glob("*.md")):
            name = path.name
            m = _PROMPT_FILE_RE.match(name)
            if not m:
                issues.append({
                    "check": "naming_convention",
                    "kind": "prompt",
                    "name": name,
                    "issue": "prompt violates 'NNN_TT_имя.md' convention (FINAL_STRUCTURE §2.1)",
                ***REMOVED***)
                continue
            number, theme = m.group(1), m.group(2)
            if theme not in _VALID_THEME_CODES:
                issues.append({
                    "check": "naming_convention",
                    "kind": "prompt",
                    "name": name,
                    "theme": theme,
                    "issue": "theme code TT outside canonical 01..14 (FINAL_STRUCTURE §2.1)",
                ***REMOVED***)
            if number in seen_numbers:
                issues.append({
                    "check": "naming_convention",
                    "kind": "prompt",
                    "name": name,
                    "number": number,
                    "issue": "duplicate prompt number NNN",
                ***REMOVED***)
            seen_numbers.add(number)

    # 4. Правило задокументировано: FINAL_STRUCTURE §2.1 + GLOSSARY (два якоря)
    structure_text = _read(workspace, FINAL_STRUCTURE) or ""
    if "Схема именования" not in structure_text:
        issues.append({
            "check": "naming_convention",
            "doc": "FINAL_STRUCTURE.md",
            "issue": "naming convention section §2.1 missing in FINAL_STRUCTURE.md",
        ***REMOVED***)

    glossary_text = _read(workspace, GLOSSARY) or ""
    if "**Naming Convention**" not in glossary_text:
        issues.append({
            "check": "naming_convention",
            "doc": "GLOSSARY.md",
            "issue": "Naming Convention term missing in GLOSSARY.md",
        ***REMOVED***)

    return issues


# ═══════════════════════════════════════════════════════════════
# 9. Test counter (CHANGELOG / CODE_QUALITY_STANDARD vs reality)
# ═══════════════════════════════════════════════════════════════

_FULL_SUITE_COUNT_RE = re.compile(r"pytest tests_09/ -q[\s\S***REMOVED***{0,120***REMOVED***?(\d+)\s+passed")
_TEST_TARGET_RE = re.compile(r"цель:\s*(\d+)\s*\+\s*passed")
_VERSION_HEADER_RE = re.compile(r"^## \[(\d+)\.(\d+)\.(\d+)\***REMOVED***", re.MULTILINE)


def count_test_functions(workspace: Path) -> int:
    """Число pytest-collectible test-функций в tests_09/ (ast.NodeVisitor).

    Зеркалит pytest collection rules БЕЗ runtime-зависимости на pytest:
      - module-level `def test_*()` или `async def test_*()` → counted
      - method `test_*(self)` inside class where class.name matches `^Test`
        или класса наследует `unittest.TestCase` / `TestCase` → counted
      - `@pytest.fixture` decorator → excluded (fixtures, not tests)
      - method inside helper class (e.g., `class IntegrationHelper`) with name
        starting `test_` → excluded
      - methods starting `_test_*` → excluded (private, name won't match)

    Tightened in [5.39.2***REMOVED***. Gap diagnostic: see `diagnose_test_count_gap`.
    """
    total, _excluded, _counted = diagnose_test_collection(workspace)
    return total


def diagnose_test_collection(workspace: Path) -> tuple[int, list[dict[str, Any***REMOVED******REMOVED***, list[dict[str, Any***REMOVED******REMOVED******REMOVED***:
    """Число pytest-collectible tests + exclusion-context'ы + counted-test'ы.

    Returns:
        (count, exclusions, counted)
        count = pytest-collectible test count (AST-based)
        exclusions = list of dict(file, function, line, reason) — функции,
            которые НЕ считаются (helper-class, fixture, private)
        counted = list of dict(file, function, line) — функции, которые
            считаются (для Set-A vs Set-B diff с pytest --collect-only)
    """
    tests_dir = workspace / "tests_09"
    if not tests_dir.is_dir():
        return 0, [***REMOVED***, [***REMOVED***
    total = 0
    exclusions: list[dict[str, Any***REMOVED******REMOVED*** = [***REMOVED***
    counted: list[dict[str, Any***REMOVED******REMOVED*** = [***REMOVED***
    for py in sorted(tests_dir.rglob("*.py")):
        try:
            source = py.read_text(encoding="utf-8")
        except OSError:
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        visitor = _PytestCollectionVisitor(py.name)
        visitor.visit(tree)
        total += visitor.count
        exclusions.extend(visitor.exclusions)
        counted.extend(visitor.counted)
    return total, exclusions, counted


def _chain_key(parts: list[str***REMOVED***) -> str:
    """Normalise a class-chain (list of class names) to a stable string key.

    '' для module-level test_* (chain пустая).
    'TestA' для метода inner-TestA class.
    'TestA::TestNested' для вложенного класса внутри TestA.
    """
    return "::".join(parts) if parts else ""


def diagnose_test_count_gap(workspace: Path) -> dict[str, Any***REMOVED***:
    """[5.39.2***REMOVED*** Ground-truth diagnostic: AST-set vs pytest-set разница.

    Реальные pytest collectible tests отличаются от AST-выводимого count
    по причинам, которые не видны в AST:
      - `pytest_collection_modifyitems` filter (плагины)
      - string-based type hint evaluation failures
      - classes с metaclass=ABC или другие хитрые паттерны
      - параметризация (parametrize maps 1 AST → N pytest items, обратная сторона gap)

    Этот diagnostic возвращает Set-A (AST) и Set-B (pytest --collect-only)
    с разницей — `ast_only` показывает функции, которые AST считает тестами,
    но pytest игнорирует; `pytest_only` показывает функции, которые pytest
    считает тестами, но AST пропустил (например, обернутые в метаклассы).

    [5.39.2 round-2***REMOVED*** Сигнатура элемента — (file, class_chain, function),
    где class_chain = 'TestA::TestNested' для method-of-class (или '' для
    module-level). Без class_chain одинаковые 'test_register_and_get' в
    разных классах одного файла (TestAgentRegistry и TestMCPRegistry)
    нормализуются в ОДИН tuple, и pytest_set теряет детализацию → ложный
    gap в десятки entries.

    Запускает `pytest --collect-only -q --no-header` (subprocess, stdlib).
    Args:
        workspace: корень workspace.
    SENTINEL contract: `pytest_count = -1` означает "неизвестно" — subprocess
    `pytest --collect-only` завершился по `subprocess.TimeoutExpired`. В этом
    случае `ast_only`/`pytest_only` = `[***REMOVED***` (а не полные непросмотренные set'ы —
    misleading разница с "точно пусто"). Отличает "I don't know" от
    "I think pytest collected 0 tests". Pre-Popen exception (OSError, FileNotFoundError) propagate.ят вверх. Non-zero exit silently swallowed (subprocess.run(check=False) — proc.returncode остаётся not-checked, consumer получает partial output). Расширенный contract (returncode check + pytest_count=-2 + error=stderr-excerpt) запланирован отдельным follow-up.
    `pytest_count = 0`, остальные поля попусту, `error: "..."` со stdout/stderr.

    Returns:
        dict с keys `ast_count`, `pytest_count`, `ast_only` (list),
        `pytest_only` (list), `parametrize_doubled` (int).
    """
    import subprocess

    _, _excluded, counted = diagnose_test_collection(workspace)
    ast_set: set[tuple[str, str, str***REMOVED******REMOVED*** = {
        (c["file"***REMOVED***, _chain_key(c["class_chain"***REMOVED***), c["function"***REMOVED***) for c in counted
    ***REMOVED***

    # Запустить pytest --collect-only, парсить output.
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "tests_09/", "--collect-only", "-q", "--no-header"***REMOVED***,
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
            shell=False,  # explicit: regression-guard (CQS §3.1 argv-list)
        )
    except subprocess.TimeoutExpired:
        # Sentinel: pytest_count=-1 означает «неизвестно» (не путать с 0 = «точно пусто»).
        return {
            "ast_count": len(ast_set),
            "pytest_count": -1,
            "ast_only": [***REMOVED***,
            "pytest_only": [***REMOVED***,
            "parametrize_doubled": 0,
            "error": "pytest --collect-only timed out",
        ***REMOVED***

    pytest_set: set[tuple[str, str, str***REMOVED******REMOVED*** = set()
    parametrize_count = 0
    for line in proc.stdout.splitlines():
        line = line.strip()
        if "::" not in line:
            continue
        # Format: tests_09/test_file.py::TestClass::test_method[param_value***REMOVED***
        # or tests_09/test_file.py::test_module_func
        parts = line.split("::")
        if len(parts) < 2:
            continue
        file_part = parts[0***REMOVED***
        test_parts = parts[1:***REMOVED***
        # Identity-level chain = test_parts без последнего элемента (= function name).
        # Last element может иметь parametrize brackets '[a,b***REMOVED***' — strip them.
        func_with_params = test_parts[-1***REMOVED***
        func_name = func_with_params.split("[", 1)[0***REMOVED*** if "[" in func_with_params else func_with_params
        chain = test_parts[:-1***REMOVED***  # class chain (может быть пусто для module-level)
        file_basename = Path(file_part).name
        pytest_set.add((file_basename, _chain_key(chain), func_name))
        # Count parametrize expansions.
        if "[" in func_with_params:
            parametrize_count += 1

    # Compute diff.
    ast_only = sorted(ast_set - pytest_set)
    pytest_only = sorted(pytest_set - ast_set)

    return {
        "ast_count": len(ast_set),
        "pytest_count": len(pytest_set),
        "ast_only": ast_only,
        "pytest_only": pytest_only,
        "parametrize_doubled": parametrize_count,
    ***REMOVED***




class _PytestCollectionVisitor(ast.NodeVisitor):
    """AST-visitor для pytest-collectible test-функций.

    Args:
        filename: имя .py файла (для diagnostics).

    Attributes:
        count: pytest-collectible test count для этого файла.
        exclusions: list of dict(file, function, line, reason) для каждой
            функции, имя которой начинается с `test_`, но которая не является
            pytest-collectible (helper-class, fixture, private).
        counted: list of dict(file, function, line) для каждого посчитанного
            теста (для Set-A vs Set-B diff с pytest --collect-only).
    """

    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.count = 0
        self.exclusions: list[dict[str, Any***REMOVED******REMOVED*** = [***REMOVED***
        # [5.39.2***REMOVED*** Set-A diff tracking: каждый посчитанный test_ сохраняем
        # с (file, line, function) для сверки с pytest --collect-only output.
        self.counted: list[dict[str, Any***REMOVED******REMOVED*** = [***REMOVED***
        # Stack текущих class-ов (для nested classes); верх — immediate parent.
        self._class_stack: list[ast.ClassDef***REMOVED*** = [***REMOVED***




    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # type: ignore[override***REMOVED***
        self._class_stack.append(node)
        self.generic_visit(node)
        self._class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # type: ignore[override***REMOVED***
        self._evaluate(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # type: ignore[override***REMOVED***
        self._evaluate(node)
        self.generic_visit(node)

    # ── helpers ────────────────────────────────────────────────────
    def _evaluate(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        if not node.name.startswith("test_"):
            return
        # _test_* — private, не считаем (имя начинается с `_` после `test`).
        # Covered by name.startswidth('test_') check above + the next check:
        if node.name.startswith("_test"):
            self._exclude(node, "private method (name starts with _test)")
            return
        # Check decorator list на pytest.fixture / @fixture.
        for dec in node.decorator_list:
            if self._decorator_is(dec, "fixture") or self._decorator_is(dec, "pytest.fixture"):
                self._exclude(node, "decorated with @fixture")
                return
        # Class context.
        if not self._class_stack:
            # module-level test_* — collectible.
            self._record_counted(node)
            return
        # Method of a class — count only if class is named Test* or inherits TestCase.
        parent = self._class_stack[-1***REMOVED***
        if parent.name.startswith("Test") or self._is_testcase_subclass(parent):
            self._record_counted(node)
        else:
            self._exclude(node, f"inside non-collectible class '{parent.name***REMOVED***'")

    def _record_counted(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Increment counter + запомнить для Set-A diff с pytest.

        [5.39.2***REMOVED*** class_chain хранит стек class-имён, в котором метод
        находится (e.g., ['TestAgentRegistry'***REMOVED***, ['TestBridge', 'TestNested'***REMOVED***).
        Нужен для однозначного diff с pytest --collect-only output, который
        выдаёт идентификаторы как 'tests_09/test_bridge_layer.py::TestA::test_x'
        — без class_chain парсер нормализует разные классы в один tuple
        и теряет детализацию.
        """
        self.count += 1
        self.counted.append({
            "file": self.filename,
            "function": node.name,
            "class_chain": tuple(c.name for c in self._class_stack),
            "line": node.lineno,
        ***REMOVED***)

    def _is_testcase_subclass(self, cls: ast.ClassDef) -> bool:
        """Return True если cls явно наследует TestCase (unittest.TestCase)."""
        for base in cls.bases:
            if isinstance(base, ast.Name) and base.id == "TestCase":
                return True
            # `unittest.TestCase` или `unitest_test_case.X.TestCase` (последний сегмент)
            if isinstance(base, ast.Attribute):
                attr_name = ".".join(self._attr_dotted(base))
                if attr_name.endswith(".TestCase") or attr_name == "TestCase":
                    return True
        return False

    @staticmethod
    def _attr_dotted(node: ast.Attribute) -> list[str***REMOVED***:
        """Восстановить dotted path у ast.Attribute (e.g., unittest.TestCase)."""
        parts: list[str***REMOVED*** = [***REMOVED***
        cur: ast.AST = node
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
        return list(reversed(parts))

    @staticmethod
    def _decorator_is(dec: ast.AST, target: str) -> bool:
        """dec — это `target` decorator? Поддерживает bare name и `decorator(...)` call."""
        # decorator(...): .func это сам decorator
        func = dec.func if isinstance(dec, ast.Call) else dec
        if isinstance(func, ast.Name) and func.id == target.split(".")[-1***REMOVED***:
            return target in (func.id, target)
        if isinstance(func, ast.Attribute):
            # dotted: pytest.fixture → ('pytest', 'fixture')
            dotted = ".".join(_PytestCollectionVisitor._attr_dotted(func))
            return dotted == target
        return False

    def _exclude(self, node: ast.FunctionDef | ast.AsyncFunctionDef, reason: str) -> None:
        self.exclusions.append({
            "file": self.filename,
            "function": node.name,
            "line": node.lineno,
            "reason": reason,
        ***REMOVED***)


def _full_suite_count(text: str) -> int | None:
    """Счётчик из САМОЙ СВЕЖЕЙ строки полного прогона CHANGELOG ('N passed').

    Разбивает CHANGELOG на секции по заголовкам `## [X.Y.Z***REMOVED***` и выбирает
    секцию с МАКСИМАЛЬНЫМ номером версии, содержащую full-suite строку
    `pytest tests_09/ -q`. Это устойчиво к случайному нарушению
    newest-first порядка (Keep a Changelog) — проверка не читает
    устаревший счётчик из более старой секции.
    """
    headers = list(_VERSION_HEADER_RE.finditer(text))
    best: tuple[tuple[int, int, int***REMOVED***, int***REMOVED*** | None = None
    for i, m in enumerate(headers):
        version = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        end = headers[i + 1***REMOVED***.start() if i + 1 < len(headers) else len(text)
        cm = _FULL_SUITE_COUNT_RE.search(text[m.start():end***REMOVED***)
        if cm and (best is None or version > best[0***REMOVED***):
            best = (version, int(cm.group(1)))
    return best[1***REMOVED*** if best else None


def _test_target_count(text: str) -> int | None:
    """Целевой счётчик из CODE_QUALITY_STANDARD (правило 11.6: 'цель: N+ passed')."""
    m = _TEST_TARGET_RE.search(text)
    return int(m.group(1)) if m else None


def check_test_counter(workspace: Path) -> list[dict[str, Any***REMOVED******REMOVED***:
    """Счётчик тестов в CHANGELOG/CODE_QUALITY_STANDARD не расходится с реальностью.

    Реальность = число test-функций в tests_09/ (AST). Сверяются оба якоря:
      - CHANGELOG.md: строка полного прогона `pytest tests_09/ -q` → 'N passed'
      - CODE_QUALITY_STANDARD.md: правило 11.6 → 'цель: N+ passed'
    """
    issues: list[dict[str, Any***REMOVED******REMOVED*** = [***REMOVED***
    actual = count_test_functions(workspace)

    changelog = _read(workspace, CHANGELOG)
    if changelog is not None:
        documented = _full_suite_count(changelog)
        if documented is None:
            issues.append({
                "check": "test_counter",
                "doc": "CHANGELOG.md",
                "issue": "full-suite 'N passed' line not found (pytest tests_09/ -q)",
            ***REMOVED***)
        elif documented != actual:
            issues.append({
                "check": "test_counter",
                "doc": "CHANGELOG.md",
                "documented": documented,
                "actual": actual,
                "issue": "test counter diverges from reality (tests_09)",
            ***REMOVED***)

    standard = _read(workspace, CODE_QUALITY_STANDARD)
    if standard is not None:
        target = _test_target_count(standard)
        if target is None:
            issues.append({
                "check": "test_counter",
                "doc": "CODE_QUALITY_STANDARD.md",
                "issue": "regression test target 'цель: N+ passed' not found (rule 11.6)",
            ***REMOVED***)
        elif target != actual:
            issues.append({
                "check": "test_counter",
                "doc": "CODE_QUALITY_STANDARD.md",
                "target": target,
                "actual": actual,
                "issue": "regression test target diverges from reality (tests_09)",
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
        "naming_convention": check_naming_convention(workspace),
        "test_counter": check_test_counter(workspace),
    ***REMOVED***
    all_issues = (
        report["engine_files"***REMOVED***
        + report["lifecycle_coverage"***REMOVED***
        + report["module_areas"***REMOVED***
        + report["glossary_terms"***REMOVED***
        + report["roadmap_refs"***REMOVED***
        + report["cross_references"***REMOVED***
        + report["project_book"***REMOVED***
        + report["naming_convention"***REMOVED***
        + report["test_counter"***REMOVED***
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
        ("engine_files", "Engine files (canonical registry → scripts_01/)"),
        ("lifecycle_coverage", "Lifecycle coverage (registry → LIFECYCLE.md)"),
        ("module_areas", "Module consolidation areas (MODULE_CONSOLIDATION.md)"),
        ("glossary_terms", "Glossary terms (GLOSSARY.md)"),
        ("roadmap_refs", "Roadmap references (ROADMAP_PROMT32)"),
        ("cross_references", "Cross references (canonical docs link each other)"),
        ("project_book", "Project Book consistency (docs_10/engineering-memory)"),
        ("naming_convention", "Naming convention (FINAL_STRUCTURE §2.1: dirs имя_NN, prompts NNN_TT_имя)"),
        ("test_counter", "Test counter (CHANGELOG / CODE_QUALITY_STANDARD vs tests_09 reality)"),
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
    parser.add_argument(
        "--diagnose-test-count", action="store_true",
        help="Run ground-truth AST vs pytest --collect-only diff diagnostic ([5.39.2***REMOVED***)",
    )
    args = parser.parse_args()

    workspace = Path(args.workspace)
    report = run_consistency_check(workspace)

    if args.diagnose_test_count:
        gap = diagnose_test_count_gap(workspace)
        print(json.dumps(gap, ensure_ascii=False, indent=2))
        return 0

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif args.report or not report["consistent"***REMOVED***:
        print(format_report(report))

    return 0 if report["consistent"***REMOVED*** else 1


if __name__ == "__main__":
    sys.exit(main())
