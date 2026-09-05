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
 10. MISSING REGISTRY   — §20 карты v1.1 (FACTORY_FORGE_ARCHITECTURE_V1.md) сверяется
                          с машиночитаемым MissingRegistry (data_13/missing_registry.yaml,
                          register-first принцип AGENTS.md §5): item_id в §20, но не в
                          реестре / в реестре, но не в §20 / статус реестра отстаёт от
                          §20 (lifecycle registered → design_ready → prompt_written → implemented)
 11. ANCHORS             — AnchorResolver (Artifact I §I.3, SEMANTIC_ANCHOR_SPEC_V1.md):
                          19-namespace семантические анкоры (@entity/@module/@symbol/@test/
                          @storage/@factory/@forge/@lesson/…, doc.*) резолвятся к коду/файлу/
                          реестру. HARD-namespaces (entity/component/module/symbol/test/
                          decision/storage/factory/forge/lesson/opportunity/whim) — UNVERIFIED
                          = drift (блокирует, реестры как данные). SOFT-namespaces
                          (event/contract/doc/requirement/scenario) — advisory (реестры
                          строятся инкрементально; зеркалит §J.4 WARN-философию doc_code_verify).
                          Мета-спека SEMANTIC_ANCHOR_SPEC_V1.md исключена из скана
                          (её примеры forge_unknown/StaleClass.old_method — педагогические).

Роль: инструмент Этапа 9 консолидации (promt32) — «реестры как данные для проверки».
Не изменяет код/документы автоматически.

Ограничения (осознанные):
  - check_module_areas / check_glossary_terms используют substring-поиск
    (область «Memory» находится внутри «MemoryEngine»). Это проверка ПОКРЫТИЯ,
    а не точного соответствия секций/строк таблиц — строгий разбор заголовков
    (например, `### A. Router`) будет усилением в будущем.
  - check_cross_references проверяет ВЗАИМНЫЕ УПОМИНАНИЯ имён документов,
    а не синтаксис markdown-ссылок `[...](...)` — битые ссылки как таковые
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
import re
import sys
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Прямой запуск `python scripts_01/consistency_check.py` не кладёт корень
# в sys.path → bootstrap для импортов core_02.* (missing_registry, anchors_resolver).
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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
}

# Обязательные термины глоссария (Этап 7, список из ROADMAP).
REQUIRED_GLOSSARY_TERMS = [
    "Workspace", "Project", "Module", "Agent", "Tool", "Plugin", "Connector",
    "Integration", "Knowledge", "Memory", "Project Book", "Engineering Memory",
    "Lifecycle", "Registry", "Decision Log", "Pulse",
]

# Схема именования (FINAL_STRUCTURE §2.1): каталоги `имя_NN`, промты `NNN_TT_имя`.
#   - Имя каталога: буквы/цифры/`_`/`-`, суффикс `_NN` (NN — двузначный ID).
#   - Промт: `NNN_TT_имя.md` (NNN — хронологический номер, TT — код темы 01..14).
_TOP_LEVEL_DIR_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*_\d{2}$")
_PROMPT_FILE_RE = re.compile(r"^(\d{3})_(\d{2})_[a-z0-9_]+\.md$")
_VALID_THEME_CODES = {f"{i:02d}" for i in range(1, 22)}  # 01..21: темы 15-21 добавлены (promt52-58: RFC/ARB/AG/Forge)
# Системные/скрытые каталоги, не подпадающие под схему именования.
_SKIP_DIR_PREFIXES = (".", "__")
# Legacy top-level redirect-shim'ы (Этап 4 консолидации, промт 32): существуют только
# как backward-compat forwarder'ы на канонические каталоги с NN-suffix'ом.
# Проверка naming_convention пропускает их, если указанный canonical_dir существует
# — закрывает ложное нарушение `имя_NN` от pre-rename shell history / tmux send-keys.
# Паттерн зеркалит scripts_01/drift_check.py::_LEGACY_TOP_LEVEL_REDIRECTS.
_LEGACY_TOP_LEVEL_REDIRECTS: dict[str, tuple[str, ...]] = {
    "freebuff_plugin": ("freebuff_plugin_03",),
}

# Evaluation-пакеты (prompt-based forensic): каноническое имя задано промтом-источником.
# Напр. promt104 §28 REQUIRED OUTPUT требует каталог `architecture_forensics_v2/` ИМЕННО
# с таким именем (без NN-suffix) — это требование источника, а не нарушение конвенции
# `имя_NN`. Переименование сломало бы имя пакета/архива
# (architecture_forensics_v2_vX.Y.Z.tar.gz) и противоречило бы промту.
# `FORENSICS_104_105_106_107` — сводный forensic-архив 4 проходов (v5.189.73): имя
# задано задачей пользователя/промтом как единый пакет; NN-suffix нарушил бы
# соответствие имени архиву FORENSICS_104_105_106_107_v5.189.73.tar.gz.
# Проверка naming_convention пропускает эти каталоги.
# ВАЖНО: добавлять сюда только каталоги, чьё имя жёстко задано внешним источником (промтом).
_EVALUATION_PACKAGE_DIRS: frozenset[str] = frozenset({
    "architecture_forensics_v2",
    "FORENSICS_104_105_106_107",
})


# 10 областей консолидации (Этап 6).
CONSOLIDATION_AREAS = [
    "Router", "Telegram", "MCP", "Memory", "Knowledge", "Registry",
    "Context", "Tool Runtime", "Plugin API", "Event Bus",
]

# Заголовки секций реестра движков в ARCHITECTURE_CANONICAL.
_ENGINE_ROW_RE = re.compile(
    r"^\|\s*(C\d+|S\d+)\s*\|\s*`([A-Za-z]+)`\s*\|\s*`(scripts_01/[a-z0-9_]+\.py)`"
)

# §20 карты v1.1 (Missing Capabilities) ↔ MissingRegistry (register-first, AGENTS.md §5).
MISSING_CAPABILITIES_DOC = Path("docs_10/engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md")
MISSING_REGISTRY_YAML = Path("data_13/missing_registry.yaml")

from core_02.missing_registry import (  # noqa: E402 — статус-константы lifecycle
    IMPLEMENTED,
    DESIGN_READY,
    PROMPT_WRITTEN,
    REGISTERED,
    status_rank,
)

from core_02.anchors_resolver import (  # noqa: E402 — check #11 ANCHORS (Artifact I §I.3)
    AnchorResolver,
    STATUS_UNVERIFIED,
)

# HARD-namespaces: детерминированный резолв (файл/реестр/AST/enum) → UNVERIFIED блокирует.
HARD_ANCHOR_NAMESPACES: frozenset[str] = frozenset({
    "entity", "component", "module", "symbol", "test", "decision",
    "storage", "factory", "forge", "lesson", "opportunity", "whim",
})
# SOFT-namespaces: реестры строятся инкрементально (event/contract/doc/requirement/
# scenario) → advisory, НЕ блокируют (зеркалит §J.4 WARN-философию doc_code_verify).
SOFT_ANCHOR_NAMESPACES: frozenset[str] = frozenset({
    "event", "contract", "doc", "requirement", "scenario",
})
# Мета-спека (Artifact I §I.5) содержит ПЕДАГОГИЧЕСКИЕ примеры (forge_unknown,
# StaleClass.old_method) — не live-claims, исключается из скана. Имя файла
# вынесено в константу: если спека будет переименована/перенесена, обновить
# здесь, а не молча потерять исключение (иначе примеры начнут блокировать #11).
_ANCHOR_EXCLUDED_DOCS: tuple[str, ...] = ("SEMANTIC_ANCHOR_SPEC_V1.md",)

# Строки §20 без backtick-токена (1–5) → item_id реестра.
_S20_ITEM_ID_BY_KEYWORD = {
    "factory registry": "factory_registry",
    "scenario engine": "scenario_engine",
    "decision registry": "decision_registry",
    "conformance checker": "conformance_checker",
    "автогенерация моделей/диаграмм": "model_diagram_autogen",
}


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


def extract_engine_rows(text: str) -> list[dict[str, str]]:
    """Извлечь (id, engine, file) из таблиц реестра движков canonical."""
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        m = _ENGINE_ROW_RE.match(line)
        if m:
            rows.append({"id": m.group(1), "engine": m.group(2), "file": m.group(3)})
    return rows


def check_engine_files(workspace: Path) -> list[dict[str, Any]]:
    """Каждый движок из canonical имеет файл в scripts_01/."""
    issues: list[dict[str, Any]] = []
    text = _read(workspace, CANONICAL)
    if text is None:
        return [{"check": "engine_files", "issue": "ARCHITECTURE_CANONICAL.md missing"}]
    for row in extract_engine_rows(text):
        if not (workspace / row["file"]).exists():
            issues.append({
                "check": "engine_files",
                "engine": row["engine"],
                "file": row["file"],
                "issue": "registry references missing file",
            })
    return issues


# ═══════════════════════════════════════════════════════════════
# 2. Lifecycle coverage
# ═══════════════════════════════════════════════════════════════


def check_lifecycle_coverage(workspace: Path) -> list[dict[str, Any]]:
    """Каждый движок из canonical описан в LIFECYCLE.md."""
    issues: list[dict[str, Any]] = []
    canonical_text = _read(workspace, CANONICAL)
    lifecycle_text = _read(workspace, LIFECYCLE)
    if canonical_text is None or lifecycle_text is None:
        return [{
            "check": "lifecycle_coverage",
            "issue": "ARCHITECTURE_CANONICAL.md or LIFECYCLE.md missing",
        }]
    for row in extract_engine_rows(canonical_text):
        if f"`{row['engine']}`" not in lifecycle_text:
            issues.append({
                "check": "lifecycle_coverage",
                "engine": row["engine"],
                "issue": "engine not covered in LIFECYCLE.md",
            })
    return issues


# ═══════════════════════════════════════════════════════════════
# 3. Module consolidation areas
# ═══════════════════════════════════════════════════════════════


def check_module_areas(workspace: Path) -> list[dict[str, Any]]:
    """Все 10 областей консолидации покрыты в MODULE_CONSOLIDATION.md."""
    issues: list[dict[str, Any]] = []
    text = _read(workspace, MODULE_CONSOLIDATION)
    if text is None:
        return [{"check": "module_areas", "issue": "MODULE_CONSOLIDATION.md missing"}]
    for area in CONSOLIDATION_AREAS:
        if area not in text:
            issues.append({
                "check": "module_areas",
                "area": area,
                "issue": "area not covered in MODULE_CONSOLIDATION.md",
            })
    return issues


# ═══════════════════════════════════════════════════════════════
# 4. Glossary terms
# ═══════════════════════════════════════════════════════════════


def check_glossary_terms(workspace: Path) -> list[dict[str, Any]]:
    """Все обязательные термины присутствуют в GLOSSARY.md."""
    issues: list[dict[str, Any]] = []
    text = _read(workspace, GLOSSARY)
    if text is None:
        return [{"check": "glossary_terms", "issue": "GLOSSARY.md missing"}]
    for term in REQUIRED_GLOSSARY_TERMS:
        if f"**{term}**" not in text:
            issues.append({
                "check": "glossary_terms",
                "term": term,
                "issue": "required term missing in GLOSSARY.md",
            })
    return issues


# ═══════════════════════════════════════════════════════════════
# 5. Roadmap references
# ═══════════════════════════════════════════════════════════════


def _extract_file_refs(text: str) -> set[str]:
    """Извлечь backtick-пути к файлам (.md/.py) из текста."""
    refs = set(re.findall(r"`([\w./\-]+\.(?:md|py))`", text))
    refs |= set(re.findall(r"(docs_10/[\w./\-]+\.md)", text))
    return refs


def check_roadmap_refs(workspace: Path) -> list[dict[str, Any]]:
    """Файлы, на которые ссылается ROADMAP_PROMT32, существуют."""
    issues: list[dict[str, Any]] = []
    text = _read(workspace, ROADMAP)
    if text is None:
        return [{"check": "roadmap_refs", "issue": "ROADMAP_PROMT32_CONSOLIDATION.md missing"}]
    for ref in sorted(_extract_file_refs(text)):
        target = workspace / ref
        if not target.exists():
            issues.append({
                "check": "roadmap_refs",
                "ref": ref,
                "issue": "roadmap references missing file",
            })
    return issues


# ═══════════════════════════════════════════════════════════════
# 6. Cross references (canonical docs link each other)
# ═══════════════════════════════════════════════════════════════


def check_cross_references(workspace: Path) -> list[dict[str, Any]]:
    """Каждый канонический документ упоминает остальные (взаимные ссылки)."""
    issues: list[dict[str, Any]] = []
    texts: dict[str, str | None] = {}
    for name, rel in CORE_DOCS.items():
        texts[name] = _read(workspace, rel)
    for name, text in texts.items():
        if text is None:
            issues.append({"check": "cross_references", "doc": name, "issue": "document missing"})
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
                })
    return issues


# ═══════════════════════════════════════════════════════════════
# 7. Project Book consistency
# ═══════════════════════════════════════════════════════════════


def check_project_book(workspace: Path) -> list[dict[str, Any]]:
    """Project Book существует и связан с каноническими реестрами.

    Проверяет три вещи (несоответствие Roadmap/Registry/Project Book):
      1. PROJECT_BOOK.md существует в docs_10/engineering-memory/
      2. На него ссылается ARCHITECTURE_MANIFEST (канонический реестр)
      3. Он упоминается в ROADMAP_PROMT32 (план работ)
    """
    issues: list[dict[str, Any]] = []

    text = _read(workspace, PROJECT_BOOK)
    if text is None:
        return [{"check": "project_book", "issue": "PROJECT_BOOK.md missing in docs_10/engineering-memory/"}]

    manifest_text = _read(workspace, MANIFEST) or ""
    if "PROJECT_BOOK" not in manifest_text and "Project Book" not in manifest_text:
        issues.append({
            "check": "project_book",
            "issue": "PROJECT_BOOK.md not referenced from ARCHITECTURE_MANIFEST.md",
        })

    roadmap_text = _read(workspace, ROADMAP) or ""
    if "PROJECT_BOOK" not in roadmap_text and "Project Book" not in roadmap_text:
        issues.append({
            "check": "project_book",
            "issue": "Project Book not mentioned in ROADMAP_PROMT32_CONSOLIDATION.md",
        })

    return issues


# ═══════════════════════════════════════════════════════════════
# 8. Naming convention
# ═══════════════════════════════════════════════════════════════


def _top_level_dir_names(workspace: Path) -> list[str]:
    """Имена top-level каталогов (без скрытых и системных)."""
    names: list[str] = []
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


def check_naming_convention(workspace: Path) -> list[dict[str, Any]]:
    """Схема именования (FINAL_STRUCTURE §2.1): каталоги `имя_NN`, промты `NNN_TT_имя`.

    Проверяет:
      1. Каждый top-level каталог (кроме скрытых/системных) следует `имя_NN`,
         суффикс-ID `_NN` уникален (FINAL_STRUCTURE присваивает номера 01..22).
         Исключение: evaluation-пакеты с каноническим именем от промта-источника
         (_EVALUATION_PACKAGE_DIRS, напр. `architecture_forensics_v2` от promt104 §28).
      2. Каждый промт в pompts_11/ следует `NNN_TT_имя.md` с валидным кодом темы (01..14).
      3. Номера промтов уникальны (гэпы допустимы — 018–021/035 не существовали;
         дубли номеров — нарушение).
      4. Само правило задокументировано в FINAL_STRUCTURE.md §2.1 и закреплено
         термином «Naming Convention» в GLOSSARY.md (две точки якоря — не потеряется).
    """
    issues: list[dict[str, Any]] = []

    # 1. Top-level каталоги: имя_NN + уникальность суффикса-ID
    seen_dir_suffixes: set[str] = set()
    for name in _top_level_dir_names(workspace):
        # 1.0a Evaluation-пакеты (promt104 §28 REQUIRED OUTPUT) — каноническое имя
        #      задано промтом-источником; пропускаем (не нарушение конвенции,
        #      см. _EVALUATION_PACKAGE_DIRS).
        if name in _EVALUATION_PACKAGE_DIRS:
            continue
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
            })
            continue
        suffix = name.rsplit("_", 1)[1]
        if suffix in seen_dir_suffixes:
            issues.append({
                "check": "naming_convention",
                "kind": "dir",
                "name": name,
                "number": suffix,
                "issue": "duplicate dir suffix _NN (FINAL_STRUCTURE §2.1 assigns unique IDs)",
            })
        seen_dir_suffixes.add(suffix)

    # 2–3. Промты: формат NNN_TT_имя.md, код темы, уникальность номера
    prompts_dir = workspace / "pompts_11"
    seen_numbers: set[str] = set()
    if prompts_dir.is_dir():
        for path in sorted(prompts_dir.glob("*.md")):
            name = path.name
            if name in ("README.md", "errors.md"):
                continue  # служебные файлы очереди pompts_11 (индекс/лог), не промты
            m = _PROMPT_FILE_RE.match(name)
            if not m:
                issues.append({
                    "check": "naming_convention",
                    "kind": "prompt",
                    "name": name,
                    "issue": "prompt violates 'NNN_TT_имя.md' convention (FINAL_STRUCTURE §2.1)",
                })
                continue
            number, theme = m.group(1), m.group(2)
            if theme not in _VALID_THEME_CODES:
                issues.append({
                    "check": "naming_convention",
                    "kind": "prompt",
                    "name": name,
                    "theme": theme,
                    "issue": "theme code TT outside canonical 01..14 (FINAL_STRUCTURE §2.1)",
                })
            if number in seen_numbers:
                issues.append({
                    "check": "naming_convention",
                    "kind": "prompt",
                    "name": name,
                    "number": number,
                    "issue": "duplicate prompt number NNN",
                })
            seen_numbers.add(number)

    # 4. Правило задокументировано: FINAL_STRUCTURE §2.1 + GLOSSARY (два якоря)
    structure_text = _read(workspace, FINAL_STRUCTURE) or ""
    if "Схема именования" not in structure_text:
        issues.append({
            "check": "naming_convention",
            "doc": "FINAL_STRUCTURE.md",
            "issue": "naming convention section §2.1 missing in FINAL_STRUCTURE.md",
        })

    glossary_text = _read(workspace, GLOSSARY) or ""
    if "**Naming Convention**" not in glossary_text:
        issues.append({
            "check": "naming_convention",
            "doc": "GLOSSARY.md",
            "issue": "Naming Convention term missing in GLOSSARY.md",
        })

    return issues


# ═══════════════════════════════════════════════════════════════
# 9. Test counter (CHANGELOG / CODE_QUALITY_STANDARD vs reality)
# ═══════════════════════════════════════════════════════════════

_FULL_SUITE_COUNT_RE = re.compile(r"pytest tests_09/ -q[\s\S]{0,120}?(\d+)\s+passed")
_TEST_TARGET_RE = re.compile(r"цель:\s*(\d+)\s*\+\s*passed")
_VERSION_HEADER_RE = re.compile(r"^## \[(\d+)\.(\d+)\.(\d+)(?:\]|\*\*\*REMOVED\*\*\*)", re.MULTILINE)


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

    Tightened in [5.39.2]. Gap diagnostic: see `diagnose_test_count_gap`.
    """
    total, _excluded, _counted = diagnose_test_collection(workspace)
    return total


def diagnose_test_collection(workspace: Path) -> tuple[int, list[dict[str, Any]], list[dict[str, Any]]]:
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
        return 0, [], []
    total = 0
    exclusions: list[dict[str, Any]] = []
    counted: list[dict[str, Any]] = []
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


def _chain_key(parts: list[str]) -> str:
    """Normalise a class-chain (list of class names) to a stable string key.

    '' для module-level test_* (chain пустая).
    'TestA' для метода inner-TestA class.
    'TestA::TestNested' для вложенного класса внутри TestA.
    """
    return "::".join(parts) if parts else ""


def diagnose_test_count_gap(workspace: Path) -> dict[str, Any]:
    """[5.39.2] Ground-truth diagnostic: AST-set vs pytest-set разница.

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

    [5.39.2 round-2] Сигнатура элемента — (file, class_chain, function),
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
    случае `ast_only`/`pytest_only` = `[]` (а не полные непросмотренные set'ы —
    misleading разница с "точно пусто"). Отличает "I don't know" от
    "I think pytest collected 0 tests". Pre-Popen exception (OSError, FileNotFoundError) propagate.ят вверх. Non-zero exit silently swallowed (subprocess.run(check=False) — proc.returncode остаётся not-checked, consumer получает partial output). Расширенный contract (returncode check + pytest_count=-2 + error=stderr-excerpt) запланирован отдельным follow-up.
    `pytest_count = 0`, остальные поля попусту, `error: "..."` со stdout/stderr.

    Returns:
        dict с keys `ast_count`, `pytest_count`, `ast_only` (list),
        `pytest_only` (list), `parametrize_doubled` (int).
    """
    import subprocess

    _, _excluded, counted = diagnose_test_collection(workspace)
    ast_set: set[tuple[str, str, str]] = {
        (c["file"], _chain_key(c["class_chain"]), c["function"]) for c in counted
    }

    # Запустить pytest --collect-only, парсить output.
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "tests_09/", "--collect-only", "-q", "--no-header"],
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
            "ast_only": [],
            "pytest_only": [],
            "parametrize_doubled": 0,
            "error": "pytest --collect-only timed out",
        }

    pytest_set: set[tuple[str, str, str]] = set()
    parametrize_count = 0
    for line in proc.stdout.splitlines():
        line = line.strip()
        if "::" not in line:
            continue
        # Format: tests_09/test_file.py::TestClass::test_method[param_value]
        # or tests_09/test_file.py::test_module_func
        parts = line.split("::")
        if len(parts) < 2:
            continue
        file_part = parts[0]
        test_parts = parts[1:]
        # Identity-level chain = test_parts без последнего элемента (= function name).
        # Last element может иметь parametrize brackets '[a,b]' — strip them.
        func_with_params = test_parts[-1]
        func_name = func_with_params.split("[", 1)[0] if "[" in func_with_params else func_with_params
        chain = test_parts[:-1]  # class chain (может быть пусто для module-level)
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
    }




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
        self.exclusions: list[dict[str, Any]] = []
        # [5.39.2] Set-A diff tracking: каждый посчитанный test_ сохраняем
        # с (file, line, function) для сверки с pytest --collect-only output.
        self.counted: list[dict[str, Any]] = []
        # Stack текущих class-ов (для nested classes); верх — immediate parent.
        self._class_stack: list[ast.ClassDef] = []




    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # type: ignore[override]
        self._class_stack.append(node)
        self.generic_visit(node)
        self._class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # type: ignore[override]
        self._evaluate(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # type: ignore[override]
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
        parent = self._class_stack[-1]
        if parent.name.startswith("Test") or self._is_testcase_subclass(parent):
            self._record_counted(node)
        else:
            self._exclude(node, f"inside non-collectible class '{parent.name}'")

    def _record_counted(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Increment counter + запомнить для Set-A diff с pytest.

        [5.39.2] class_chain хранит стек class-имён, в котором метод
        находится (e.g., ['TestAgentRegistry'], ['TestBridge', 'TestNested']).
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
        })

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
    def _attr_dotted(node: ast.Attribute) -> list[str]:
        """Восстановить dotted path у ast.Attribute (e.g., unittest.TestCase)."""
        parts: list[str] = []
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
        if isinstance(func, ast.Name) and func.id == target.split(".")[-1]:
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
        })


def _full_suite_count(text: str) -> int | None:
    """Счётчик из САМОЙ СВЕЖЕЙ строки полного прогона CHANGELOG ('N passed').

    Разбивает CHANGELOG на секции по заголовкам `## [X.Y.Z]` и выбирает
    секцию с МАКСИМАЛЬНЫМ номером версии, содержащую full-suite строку
    `pytest tests_09/ -q`. Это устойчиво к случайному нарушению
    newest-first порядка (Keep a Changelog) — проверка не читает
    устаревший счётчик из более старой секции.
    """
    headers = list(_VERSION_HEADER_RE.finditer(text))
    best: tuple[tuple[int, int, int], int] | None = None
    for i, m in enumerate(headers):
        version = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        cm = _FULL_SUITE_COUNT_RE.search(text[m.start():end])
        if cm and (best is None or version > best[0]):
            best = (version, int(cm.group(1)))
    return best[1] if best else None


def _test_target_count(text: str) -> int | None:
    """Целевой счётчик из CODE_QUALITY_STANDARD (правило 11.6: 'цель: N+ passed')."""
    m = _TEST_TARGET_RE.search(text)
    return int(m.group(1)) if m else None


def check_test_counter(workspace: Path) -> list[dict[str, Any]]:
    """Счётчик тестов в CHANGELOG/CODE_QUALITY_STANDARD не расходится с реальностью.

    Реальность = число test-функций в tests_09/ (AST). Сверяются оба якоря:
      - CHANGELOG.md: строка полного прогона `pytest tests_09/ -q` → 'N passed'
      - CODE_QUALITY_STANDARD.md: правило 11.6 → 'цель: N+ passed'
    """
    issues: list[dict[str, Any]] = []
    actual = count_test_functions(workspace)

    changelog = _read(workspace, CHANGELOG)
    if changelog is not None:
        documented = _full_suite_count(changelog)
        if documented is None:
            issues.append({
                "check": "test_counter",
                "doc": "CHANGELOG.md",
                "issue": "full-suite 'N passed' line not found (pytest tests_09/ -q)",
            })
        elif documented != actual:
            issues.append({
                "check": "test_counter",
                "doc": "CHANGELOG.md",
                "documented": documented,
                "actual": actual,
                "issue": "test counter diverges from reality (tests_09)",
            })

    standard = _read(workspace, CODE_QUALITY_STANDARD)
    if standard is not None:
        target = _test_target_count(standard)
        if target is None:
            issues.append({
                "check": "test_counter",
                "doc": "CODE_QUALITY_STANDARD.md",
                "issue": "regression test target 'цель: N+ passed' not found (rule 11.6)",
            })
        elif target != actual:
            issues.append({
                "check": "test_counter",
                "doc": "CODE_QUALITY_STANDARD.md",
                "target": target,
                "actual": actual,
                "issue": "regression test target diverges from reality (tests_09)",
            })

    return issues


# ═══════════════════════════════════════════════════════════════
# 10. Missing Registry sync (§20 карты v1.1 ↔ data_13/missing_registry.yaml)
# ═══════════════════════════════════════════════════════════════


def _s20_status_from_cell(cell: str) -> str:
    """Маппинг последней колонки §20 (приоритет/статус) → lifecycle реестра.

    Порядок важен: «✅/реализовано» → implemented; «дизайн готов» → design_ready;
    «промт на реализацию» → prompt_written; иначе registered.
    """
    if "✅" in cell or "реализовано" in cell:
        return IMPLEMENTED
    if "дизайн готов" in cell:
        return DESIGN_READY
    if "промт на реализацию" in cell:
        return PROMPT_WRITTEN
    return REGISTERED


def extract_missing_capabilities(text: str) -> list[dict[str, str]]:
    """Разобрать §20-таблицу карты v1.1 → [{item_id, status]].

    item_id берётся из backtick-токена (``research_web``) либо keyword-маппинга
    строк 1–5 (Factory Registry → factory_registry и т.п.). status — из последней
    колонки через :func:`_s20_status_from_cell`.
    """
    out: list[dict[str, str]] = []
    m = re.search(r"## 20\. Missing Capabilities\n(.*?)(?=\n---|\n## |\Z)", text, re.DOTALL)
    if not m:
        return out
    section = m.group(1)
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 4:
            continue
        desc, priority = cells[1], cells[3]
        bt = re.search(r"`([a-z)[a-z0-9_]+)`", desc)
        if bt:
            item_id = bt.group(1)
        else:
            low = desc.lower()
            item_id = next((v for k, v in _S20_ITEM_ID_BY_KEYWORD.items() if k in low), None)
        if not item_id:
            continue
        out.append({"item_id": item_id, "status": _s20_status_from_cell(priority)})
    return out


def check_missing_registry_sync(workspace: Path) -> list[dict[str, Any]]:
    """§20 карты v1.1 ↔ MissingRegistry не расходятся (register-first, AGENTS.md §5).

    Три класса расхождений:
      1. item_id в §20, но отсутствует в реестре → register-first нарушен;
      2. item_id в реестре, но отсутствует в §20 → док не обновлён;
      3. статус реестра отстаёт/обгоняет §20 → lifecycle рассинхронизирован.
    Плюс schema_violations самого реестра (B10/R-127).
    """
    issues: list[dict[str, Any]] = []
    text = _read(workspace, MISSING_CAPABILITIES_DOC)
    if text is None:
        return [{
            "check": "missing_registry_sync",
            "issue": "FACTORY_FORGE_ARCHITECTURE_V1.md missing (§20)",
        }]

    reg_path = workspace / MISSING_REGISTRY_YAML
    if not reg_path.exists():
        return [{
            "check": "missing_registry_sync",
            "issue": f"{MISSING_REGISTRY_YAML} missing (run: python -m core_02.missing_registry seed)",
        }]

    from core_02.missing_registry import MissingRegistry  # local import — держит модуль независимым

    try:
        reg = MissingRegistry(reg_path)
    except Exception as exc:  # noqa: BLE001 — fail-safe
        return [{"check": "missing_registry_sync", "issue": f"MissingRegistry load failed: {exc}"}]

    for v in reg.schema_violations:
        issues.append({"check": "missing_registry_sync", "issue": f"registry schema violation: {v}"})

    doc_items = extract_missing_capabilities(text)
    doc_by_id = {i["item_id"]: i["status"] for i in doc_items}
    reg_items = {i.item_id: i.status for i in reg.list_all()}

    for item_id, doc_status in sorted(doc_by_id.items()):
        if item_id not in reg_items:
            issues.append({
                "check": "missing_registry_sync",
                "item": item_id,
                "issue": "in §20 map but missing from MissingRegistry (register-first)",
            })
            continue
        doc_rank = status_rank(doc_status)
        reg_rank = status_rank(reg_items[item_id])
        if reg_rank < doc_rank:
            issues.append({
                "check": "missing_registry_sync",
                "item": item_id,
                "doc_status": doc_status,
                "registry_status": reg_items[item_id],
                "issue": "registry lags behind §20 map (register-first: реестр — источник истины)",
            })
        elif reg_rank > doc_rank:
            issues.append({
                "check": "missing_registry_sync",
                "item": item_id,
                "doc_status": doc_status,
                "registry_status": reg_items[item_id],
                "issue": "§20 map lags behind registry (update §20 row)",
            })

    for item_id in sorted(reg_items):
        if item_id not in doc_by_id:
            issues.append({
                "check": "missing_registry_sync",
                "item": item_id,
                "issue": "in MissingRegistry but missing from §20 map (update §20)",
            })

    return issues


# ═══════════════════════════════════════════════════════════════
# 11. Anchors (AnchorResolver — Artifact I §I.3)
# ═══════════════════════════════════════════════════════════════


def check_anchors(workspace: Path) -> list[dict[str, Any]]:
    """[5.189.4] Семантические анкоры резолвятся к коду/файлу/реестру (§I.3).

    Прогоняет AnchorResolver по каноническим корням (engineering-memory,
    runtime_05, CHANGELOG.md), исключая мета-спеку SEMANTIC_ANCHOR_SPEC_V1.md
    (педагогические примеры forge_unknown/StaleClass.old_method).

    Блокирующие (hard) namespaces: entity/component/module/symbol/test/decision/
    storage/factory/forge/lesson/opportunity/whim — UNVERIFIED = drift.
    Advisory (soft) namespaces: event/contract/doc/requirement/scenario — не
    блокируют (реестры строятся инкрементально, зеркалит §J.4 WARN-философию
    doc_code_verify).
    """
    resolver = AnchorResolver(workspace)
    summary = resolver.run(
        roots=("docs_10/engineering-memory", "runtime_05", "CHANGELOG.md"),
        exclude=_ANCHOR_EXCLUDED_DOCS,
    )
    issues: list[dict[str, Any]] = []
    for u in summary.get("unresolved", []):
        if u.get("namespace") in HARD_ANCHOR_NAMESPACES:
            issues.append({
                "check": "anchors",
                "namespace": u.get("namespace"),
                "value": u.get("value"),
                "doc": u.get("doc"),
                "line": u.get("line"),
                "issue": (
                    f"UNVERIFIED anchor {u.get('raw', '')} — {u.get('evidence', '')}"
                ),
            })
    return issues


# ═══════════════════════════════════════════════════════════════
# Report
# ═══════════════════════════════════════════════════════════════


def check_backfill_signatures(workspace: Path) -> list[dict[str, Any]]:
    """v5.189.51: scan ``data_13/missing_registry.yaml`` for retroactive-signature
    entries: ``status=implemented`` + ``registered_at==updated_at`` +
    ``backfill=False`` (or missing).

    Why: developers sometimes run ``register X --status implemented`` directly
    without realising the entry LOOKS retroactive (no lifecycle evolution,
    timestamps identical). This breaks CON-63 / CON-64 register-first discipline
    ephemerally because downstream queries filter on ``backfill=true`` and
    silently skip the unflagged retroactive ones. Surfacing them here forces
    an explicit choice: re-register with ``--backfill`` OR fix the lifecycle
    timestamps.

    Severity: WARNING (not violation). Heuristic is timestamp-string equality
    (ISO 8601, second-precision); legitimate single-shot updates could collide
    and will appear as warnings (acceptable noise — better to over-warn than
    silent miss). Seed defaults (canonical entries from ``_SEED`` in
    ``core_02.missing_registry``) are exempt — they pre-date the backfill:bool
    instrument and flagging them would be historical-cleanup noise.

    Returns:
        list[dict[str, Any]] of warning dicts (may be empty).
    """
    registry_path = workspace / "data_13" / "missing_registry.yaml"
    if not registry_path.exists():
        return []
    try:
        data = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return []
    if not isinstance(data, dict):
        return []
    # Exempt canonical SEED items (those predate backfill:bool discipline).
    exempt_ids: set[str] = set()
    try:
        from core_02.missing_registry import _SEED as _MR_SEED  # type: ignore[import-not-found]
        for item in _MR_SEED or []:
            if isinstance(item, dict) and "item_id" in item:
                exempt_ids.add(str(item["item_id"]))
    except Exception:  # noqa: BLE001 — defensive: missing module/path drift
        pass
    warnings: list[dict[str, Any]] = []
    for item_id, entry in data.items():
        if not isinstance(entry, dict):
            continue
        if item_id in exempt_ids:
            continue
        if entry.get("status") != "implemented":
            continue
        registered_at = entry.get("registered_at")
        updated_at = entry.get("updated_at")
        if not (registered_at and updated_at):
            continue
        if registered_at != updated_at:
            continue
        if entry.get("backfill", False) is True:
            continue
        warnings.append({
            "check": "backfill_signature",
            "severity": "warning",
            "doc": "data_13/missing_registry.yaml",
            "item_id": str(item_id),
            "reason": (
                "status=implemented + registered_at==updated_at without "
                "backfill:true — looks retroactive. Re-register with "
                "`--backfill` (or bump updated_at to differ from registered_at)."
            ),
        })
    return warnings


def build_report(workspace: Path) -> dict[str, Any]:
    """Собрать полный отчёт самоконсистентности."""
    report: dict[str, Any] = {
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
        "missing_registry_sync": check_missing_registry_sync(workspace),
        "backfill_signature": check_backfill_signatures(workspace),
        "anchors": check_anchors(workspace),
    }
    all_issues = (
        report["engine_files"]
        + report["lifecycle_coverage"]
        + report["module_areas"]
        + report["glossary_terms"]
        + report["roadmap_refs"]
        + report["cross_references"]
        + report["project_book"]
        + report["naming_convention"]
        + report["test_counter"]
        + report["missing_registry_sync"]
        # NOTE: backfill_signature kept in report["backfill_signature"] for
        # visibility but NOT aggregated into all_issues (soft discipline signal,
        # per user 'предупреждение' intent — see v5.189.51 docstring).
        + report["anchors"]
    )
    report["total_issues"] = len(all_issues)
    report["consistent"] = not all_issues
    return report


def format_report(report: dict[str, Any]) -> str:
    lines: list[str] = [
        "# Consistency Report (Stage 9)",
        "",
        f"_Generated at: {report['generated_at']}_",
        "",
        "> Реестры как данные: ARCHITECTURE_CANONICAL, LIFECYCLE, MODULE_CONSOLIDATION, "
        "GLOSSARY, ROADMAP_PROMT32.",
        "",
    ]
    if report["consistent"]:
        lines.extend(["## ✅ Consistent", "", "All canonical registries agree with the codebase."])
        return "\n".join(lines)

    lines.append(f"## ⚠️ {report['total_issues']} issue(s) found")
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
        ("missing_registry_sync", "Missing Registry sync (§20 карты v1.1 ↔ data_13/missing_registry.yaml, register-first)"),
        ("anchors", "Anchors (AnchorResolver §I.3: hard namespaces → code/file/registry)"),
    ]
    for key, title in sections:
        items = report[key]
        if not items:
            continue
        lines.append("")
        lines.append(f"## {title}")
        for item in items:
            detail = " · ".join(f"{k}={v}" for k, v in item.items() if k != "check")
            lines.append(f"- `{item['check']}`: {detail}")
    return "\n".join(lines)


def run_consistency_check(workspace: Path | str) -> dict[str, Any]:
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
        help="Run ground-truth AST vs pytest --collect-only diff diagnostic ([5.39.2])",
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
    elif args.report or not report["consistent"]:
        print(format_report(report))

    return 0 if report["consistent"] else 1


if __name__ == "__main__":
    sys.exit(main())
