"""core_02/anchors_resolver.py — AnchorResolver (Artifact I §I.3, Phase C).

Полный 19-namespace резолвер семантических анкоров per SEMANTIC_ANCHOR_SPEC_V1.md:

    @entity @component @module @symbol @contract @event @storage @test
    @decision @requirement @scenario @factory @forge @opportunity @whim
    @lesson(CON|ANTI|CAN|R)  +  doc.<name>#<section>[.cN***REMOVED*** (extension, Artifact B)

Принципы (spec §I.3/§I.5):
  - REPOSITORY = SOURCE OF TRUTH: анкор резолвится к существующему коду/файлу/
    реестру, либо статус = UNVERIFIED (анти-галлюцинация: никакого silent
    fallthrough в CURRENT).
  - Line-number PROHIBITED: идентичность — по символу/секции, никогда по строке.
  - Stdlib only (re/ast/pathlib), зеркалит стиль core_02/forge_passport.py
    (frozen dataclass) и core_02/factory_registry.py (graceful-degrade).

Status taxonomy (§I.5):
  CURRENT      — анкор резолвится (файл/реестр/код найден).
  LESSON       — @lesson резолвится в core_02/LESSONS.md (спец-статус §I.3).
  DESIGN_ONLY  — namespace зарегистрирован как planned, но реестр/инфраструктура
                 не существует (requirement → REQ_REGISTRY_V1.md, scenario →
                 runtime_05/scenarios/*.yaml отсутствует). Не флагуется CI.
  UNVERIFIED   — резолв невозможен (дефолт при ошибке; флагуется CI).

Usage::
    python -m core_02.anchors_resolver docs_10/engineering-memory/PLATFORM_CODE_MAP_V1.md
    python -m core_02.anchors_resolver docs_10/ --json
    python -m core_02.anchors_resolver . --strict        # exit 1 при UNVERIFIED

Integración CI: scripts_01/consistency_check.py check #11 (ANCHORS).
"""

from __future__ import annotations

import argparse
import ast
import json
***REMOVED***
import sys
from dataclasses import dataclass
***REMOVED***
from typing import Any, Optional

# ─── Canonical enums (spec §I.3 resolution targets) ─────────────────────────
CANONICAL_FACTORIES: tuple[str, ...***REMOVED*** = (
    "architecture_factory",
    "code_factory",
    "research_factory",
    "content_factory",
)

CANONICAL_FORGES: tuple[str, ...***REMOVED*** = (
    "forge_idea",
    "forge_knowledge",
    "forge_architecture",
    "forge_implementation",
    "forge_validation",
    "forge_evolution",
)

# ─── Namespace regexes (spec §I.2 / §I.3 ANCHOR_RE) ─────────────────────────
ANCHOR_RE: dict[str, re.Pattern[str***REMOVED******REMOVED*** = {
    "entity":      re.compile(r"@entity\s+([a-z***REMOVED***[a-z0-9_***REMOVED****(\.[a-z***REMOVED***[a-z0-9_***REMOVED****)+)"),
    "component":   re.compile(r"@component\s+([a-z***REMOVED***[a-z0-9_***REMOVED****(\.[a-z***REMOVED***[a-z0-9_***REMOVED****)*)"),
    "module":      re.compile(r"@module\s+([a-z***REMOVED***[a-z0-9_***REMOVED****(\.[a-z***REMOVED***[a-z0-9_***REMOVED****)+)"),
    "symbol":      re.compile(r"@symbol\s+([A-Z***REMOVED***[A-Za-z0-9_***REMOVED***+(\.[a-zA-Z_***REMOVED***[A-Za-z0-9_***REMOVED****)+)"),
    "contract":    re.compile(r"@contract\s+([a-z***REMOVED***[a-z0-9_***REMOVED****(\.[a-z***REMOVED***[a-z0-9_***REMOVED****)+)"),
    "event":       re.compile(r"@event\s+([a-z***REMOVED***[a-z0-9_***REMOVED****(\.[a-z***REMOVED***[a-z0-9_***REMOVED****)+)"),
    "storage":     re.compile(r"@storage\s+([a-z***REMOVED***[a-z0-9_***REMOVED***+(_[a-z***REMOVED***[a-z0-9_***REMOVED****)*)"),
    "test":        re.compile(r"@test\s+(test_[a-z***REMOVED***[a-z0-9_***REMOVED****)(\.[A-Za-z_***REMOVED***[\w***REMOVED****)*"),
    "decision":    re.compile(r"@decision\s+(ADR_\d{3***REMOVED***)"),
    "requirement": re.compile(r"@requirement\s+(REQ-[A-Z***REMOVED***[A-Z_***REMOVED****-?\d{2***REMOVED***)"),
    "scenario":    re.compile(r"@scenario\s+([a-z***REMOVED***[a-z0-9_***REMOVED****(\.?[a-z0-9_***REMOVED****)*)"),
    "factory":     re.compile(r"@factory\s+([a-z***REMOVED***[a-z0-9_***REMOVED****_factory)"),
    "forge":       re.compile(r"@forge\s+(forge_[a-z***REMOVED***[a-z0-9_***REMOVED****)"),
    "opportunity": re.compile(r"@opportunity\s+(opp-[a-z0-9***REMOVED***+)"),
    "whim":        re.compile(r"@whim\s+(whim-[a-z0-9***REMOVED***+)"),
    "lesson":      re.compile(r"@lesson\s+((?:CON|ANTI|CAN|R)[-_***REMOVED***\d{1,3***REMOVED***[a-z***REMOVED***?)"),
    "doc":         re.compile(r"(doc\.[a-z***REMOVED***[a-z0-9_***REMOVED****\.?[a-z0-9_***REMOVED****#[\w\.\-***REMOVED***+)"),
***REMOVED***

# Порядок поиска по строке: сначала префиксные @namespace (однозначны),
# doc.* без префикса — в конце (не пересекается с @-паттернами).
_NAMESPACE_ORDER: tuple[str, ...***REMOVED*** = tuple(ANCHOR_RE.keys())

# Namespace, чей резолв-реестр ещё не реализован (спец §I.3 / §I.9 known limitations)
# → при отсутствии резолва статус DESIGN_ONLY, а не UNVERIFIED.
_PLANNED_NAMESPACES: frozenset[str***REMOVED*** = frozenset({"requirement", "scenario"***REMOVED***)

# Status vocabulary (spec §I.5)
STATUS_CURRENT = "CURRENT"
STATUS_LESSON = "LESSON"
STATUS_DESIGN_ONLY = "DESIGN_ONLY"
STATUS_UNVERIFIED = "UNVERIFIED"
STATUS_STALE = "STALE"

_CODE_ROOTS: tuple[str, ...***REMOVED*** = ("scripts_01", "core_02", "freebuff_plugin_03")

_DEFAULT_DOC_ROOTS: tuple[str, ...***REMOVED*** = ("docs_10", "runtime_05", "CHANGELOG.md")


@dataclass(frozen=True)
class Anchor:
    """Извлечённый анкор (до резолва)."""
    namespace: str
    value: str
    raw: str
    line_num: int = 0


# ─── Extraction ──────────────────────────────────────────────────────────────

def extract_anchors(text: str, *, skip_fences: bool = True) -> list[Anchor***REMOVED***:
    """Извлечь все анкоры из текста (line-based, с учётом code fences).

    Построчно: строки внутри ```fences``` пропускаются (spec §J.2.1 зеркалит
    doc_code_verify.py). Для каждой строки — первый матч каждого namespace
    (несколько namespace в одной строке разрешены: §I.4 density 1–3 на абзац).
    """
    anchors: list[Anchor***REMOVED*** = [***REMOVED***
    in_fence = False
    for line_num, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for ns in _NAMESPACE_ORDER:
            for m in ANCHOR_RE[ns***REMOVED***.finditer(line):
                value = m.group(1)
                if ns == "test" and m.group(2):
                    value += m.group(2)
                if ns == "scenario":
                    value = m.group(1).rstrip(".")
                anchors.append(Anchor(
                    namespace=ns,
                    value=value,
                    raw=m.group(0),
                    line_num=line_num,
                ))
    return anchors


# ─── Resolver ────────────────────────────────────────────────────────────────

class AnchorResolver:
    """Резолвер анкоров с кэшами по workspace.

    Все lookup-механизмы — статические (filesystem/AST/regex), без import
    целевых модулей (CQS §3.1, безопасность).
    """

    def __init__(self, workspace: Path) -> None:
        self.workspace = Path(workspace)
        # Кэши (lazy). Имена с суффиксом _cache — НЕ пересекаются с методами.
        self._entity_ids_cache: Optional[set[str***REMOVED******REMOVED*** = None
        self._contract_text: Optional[str***REMOVED*** = None
        self._doc_map_text: Optional[str***REMOVED*** = None
        self._lessons_text: Optional[str***REMOVED*** = None
        self._event_text_cache: Optional[str***REMOVED*** = None
        self._symbol_index: Optional[dict[str, str***REMOVED******REMOVED*** = None
        self._read_cache: dict[str, Optional[str***REMOVED******REMOVED*** = {***REMOVED***

    # ── helpers ────────────────────────────────────────────────────────
    def _read(self, rel: str) -> Optional[str***REMOVED***:
        """Мемоизированное чтение файла (per-resolver; run() резолвит 1000+ анкоров)."""
        if rel in self._read_cache:
            return self._read_cache[rel***REMOVED***
        path = self.workspace / rel
        if not path.exists() or not path.is_file():
            self._read_cache[rel***REMOVED*** = None
            return None
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            text = None
        self._read_cache[rel***REMOVED*** = text
        return text

    def _entity_ids(self) -> set[str***REMOVED***:
        """Канонический набор entity-id из Artifact A (PLATFORM_CODE_MAP_V1.md).

        Источники: (1) заголовки `### @entity <id>`; (2) §A.6 provenance table
        (первая колонка). Объединение — реестр сущностей для @entity/@component.
        """
        if self._entity_ids_cache is not None:
            return self._entity_ids_cache
        ids: set[str***REMOVED*** = set()
        text = self._read("docs_10/engineering-memory/PLATFORM_CODE_MAP_V1.md") or ""
        for m in re.finditer(r"^###\s+@entity[: ***REMOVED***+([a-z***REMOVED***[a-z0-9_.***REMOVED***+)", text, re.MULTILINE):
            ids.add(m.group(1).strip().strip("`"))
        # §A.6 таблица: строки `| <id> | <file> | ...` — первая колонка.
        in_a6 = False
        for line in text.splitlines():
            if line.startswith("## §A.6"):
                in_a6 = True
                continue
            if in_a6 and line.startswith("## "):
                break
            if in_a6 and line.startswith("|"):
                cells = [c.strip() for c in line.strip("|").split("|")***REMOVED***
                if cells and re.match(r"^[a-z***REMOVED***[a-z0-9_.***REMOVED***+$", cells[0***REMOVED***) and len(cells) >= 3:
                    ids.add(cells[0***REMOVED***)
        self._entity_ids_cache = ids
        return ids

    def _symbol_lookup(self, value: str) -> Optional[str***REMOVED***:
        """Найти `ClassName.method` или `ClassName` в .py под _CODE_ROOTS (AST).

        Возвращает относительный путь файла (первое совпадение) или None.
        Индекс кэшируется (класс → файл) при первом обращении.
        """
        if self._symbol_index is None:
            index: dict[str, str***REMOVED*** = {***REMOVED***
            for root in _CODE_ROOTS:
                base = self.workspace / root
                if not base.is_dir():
                    continue
                for py in sorted(base.rglob("*.py")):
                    if "__pycache__" in py.parts:
                        continue
                    try:
                        tree = ast.parse(py.read_text(encoding="utf-8"))
                    except (SyntaxError, OSError, UnicodeDecodeError):
                        continue
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            index.setdefault(node.name, str(py.relative_to(self.workspace)))
                            for child in node.body:
                                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                    index.setdefault(
                                        f"{node.name***REMOVED***.{child.name***REMOVED***",
                                        str(py.relative_to(self.workspace)),
                                    )
                        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            index.setdefault(node.name, str(py.relative_to(self.workspace)))
            self._symbol_index = index
        return self._symbol_index.get(value)

    def _event_text(self) -> str:
        if self._event_text_cache is None:
            parts: list[str***REMOVED*** = [***REMOVED***
            for root in ("scripts_01", "core_02"):
                text = self._read(f"{root***REMOVED***/event_bus.py")
                if text:
                    parts.append(text)
            self._event_text_cache = "\n".join(parts)
        return self._event_text_cache

    # ── per-namespace resolution ───────────────────────────────────────
    def _resolve_entity(self, value: str) -> dict[str, Any***REMOVED***:
        # 1. Канонический Artifact A (спец §I.3: entity → Artifact A).
        if value in self._entity_ids():
            return {"resolved": True, "status": STATUS_CURRENT,
                    "evidence": "PLATFORM_CODE_MAP_V1.md §A.6"***REMOVED***
        # 2. Fallback: entity-имя → модуль-файл (dot→underscore, strip .py).
        #    Artifact A инвентаризует 25 сущностей, но кодовая база содержит больше
        #    реальных модулей (model.gateway → core_02/model_gateway.py).
        #    REPOSITORY = SOURCE OF TRUTH: файл существует → резолв честный.
        for cand in self._entity_module_candidates(value):
            for root in _CODE_ROOTS:
                rel = f"{root***REMOVED***/{cand***REMOVED***.py"
                if (self.workspace / rel).exists():
                    return {"resolved": True, "status": STATUS_CURRENT,
                            "evidence": rel***REMOVED***
        # 3. Fallback: entity зарегистрирован в MissingRegistry (register-first)
        #    → DESIGN_ONLY (спец §I.5: target planned).
        reg = self._read("data_13/missing_registry.yaml")
        item = value.replace(".", "_")
        if reg is not None and re.search(rf"^{re.escape(item)***REMOVED***:\s*$", reg, re.MULTILINE):
            return {"resolved": True, "status": STATUS_DESIGN_ONLY,
                    "evidence": "registered in data_13/missing_registry.yaml"***REMOVED***
        return {"resolved": False, "status": STATUS_UNVERIFIED,
                "evidence": "not in Artifact A / no module file / not in MissingRegistry"***REMOVED***

    @staticmethod
    def _entity_module_candidates(value: str) -> list[str***REMOVED***:
        """Варианты имени модуля из entity-id (dot→underscore, strip .py)."""
        base = value
        if base.endswith(".py"):
            base = base[:-3***REMOVED***
        cands: list[str***REMOVED*** = [base.replace(".", "_")***REMOVED***
        if "." in base:
            cands.append(base.split(".")[-1***REMOVED***)
        return cands

    def _resolve_component(self, value: str) -> dict[str, Any***REMOVED***:
        parts = value.split(".")
        parent = ".".join(parts[:2***REMOVED***) if len(parts) >= 2 else value
        if parent in self._entity_ids():
            return {"resolved": True, "status": STATUS_CURRENT,
                    "evidence": f"subcomponent of @entity {parent***REMOVED***"***REMOVED***
        return {"resolved": False, "status": STATUS_UNVERIFIED,
                "evidence": f"parent @entity {parent***REMOVED*** not in Artifact A"***REMOVED***

    def _resolve_module(self, value: str) -> dict[str, Any***REMOVED***:
        candidates = {value, value.split(".")[0***REMOVED***, value.split(".")[-1***REMOVED******REMOVED***
        for cand in sorted(candidates):
            for root in _CODE_ROOTS:
                rel = f"{root***REMOVED***/{cand***REMOVED***.py"
                if (self.workspace / rel).exists():
                    return {"resolved": True, "status": STATUS_CURRENT,
                            "evidence": rel***REMOVED***
        return {"resolved": False, "status": STATUS_UNVERIFIED,
                "evidence": "no scripts_01|core_02|freebuff_plugin_03/<name>.py"***REMOVED***

    @staticmethod
    def _module_candidates(value: str) -> list[str***REMOVED***:
        """Кандидаты имени модуля: полное имя, первый сегмент (domain), последний.

        `forge.cli` → `forge` (first segment = filename, спец §I.1 row 3).
        """
        parts = value.split(".")
        cands = [value, parts[0***REMOVED***, parts[-1***REMOVED******REMOVED*** if len(parts) > 1 else [value***REMOVED***
        # De-dup, preserve order.
        out: list[str***REMOVED*** = [***REMOVED***
        for c in cands:
            if c not in out:
                out.append(c)
        return out

    def _resolve_symbol(self, value: str) -> dict[str, Any***REMOVED***:
        hit = self._symbol_lookup(value)
        if hit:
            return {"resolved": True, "status": STATUS_CURRENT, "evidence": hit***REMOVED***
        # Fallback: ClassName → any method?
        if "." in value:
            cls = value.split(".")[0***REMOVED***
            for root in _CODE_ROOTS:
                for py in sorted((self.workspace / root).rglob("*.py")):
                    if "__pycache__" in py.parts:
                        continue
                    try:
                        tree = ast.parse(py.read_text(encoding="utf-8"))
                    except (SyntaxError, OSError, UnicodeDecodeError):
                        continue
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef) and node.name == cls:
                            rel = str(py.relative_to(self.workspace))
                            return {"resolved": True, "status": STATUS_CURRENT,
                                    "evidence": rel***REMOVED***
        # §I.7 anti-hallucination: отсутствующий символ — STALE, НЕ UNVERIFIED
        # („mark @symbol StaleClass.old_method → STALE if class absent“).
        return {"resolved": False, "status": STATUS_STALE,
                "evidence": "class/method absent from code roots → STALE (§I.7)"***REMOVED***

    def _resolve_contract(self, value: str) -> dict[str, Any***REMOVED***:
        if self._contract_text is None:
            self._contract_text = self._read(
                "docs_10/engineering-memory/CONTRACT_REGISTRY_V1.md") or ""
        if value in self._contract_text:
            return {"resolved": True, "status": STATUS_CURRENT,
                    "evidence": "CONTRACT_REGISTRY_V1.md"***REMOVED***
        return {"resolved": False, "status": STATUS_UNVERIFIED,
                "evidence": "not in CONTRACT_REGISTRY_V1.md"***REMOVED***

    def _resolve_event(self, value: str) -> dict[str, Any***REMOVED***:
        if value in self._event_text():
            return {"resolved": True, "status": STATUS_CURRENT,
                    "evidence": "scripts_01|core_02/event_bus.py"***REMOVED***
        # Fallback: event упомянут в entity-cards Artifact A (events_produced/
        # events_consumed) — канонический инвентарь событий.
        a_text = self._read("docs_10/engineering-memory/PLATFORM_CODE_MAP_V1.md") or ""
        if value in a_text:
            return {"resolved": True, "status": STATUS_CURRENT,
                    "evidence": "Artifact A entity-card event inventory"***REMOVED***
        return {"resolved": False, "status": STATUS_UNVERIFIED,
                "evidence": "not registered in event_bus.py / Artifact A"***REMOVED***

    def _resolve_storage(self, value: str) -> dict[str, Any***REMOVED***:
        # 1. Файл в data_13 (yaml/json/jsonl) — спец §I.3 `@storage`.
        base = self.workspace / "data_13"
        if base.is_dir():
            names = [value + ".yaml", value + ".json", value + ".jsonl"***REMOVED***
            if value.endswith("_yaml"):
                names.append(value[:-5***REMOVED*** + ".yaml")
            if value.endswith("_json"):
                names.append(value[:-5***REMOVED*** + ".json")
            for name in names:
                if (base / name).exists():
                    return {"resolved": True, "status": STATUS_CURRENT,
                            "evidence": f"data_13/{name***REMOVED***"***REMOVED***
            # 2. Каталог data_13/<value> (напр. memory/, knowledge_index/).
            if (base / value).is_dir():
                return {"resolved": True, "status": STATUS_CURRENT,
                        "evidence": f"data_13/{value***REMOVED***/ (dir)"***REMOVED***
        # 3. Известные shorthand'ы storage_used из Artifact A (§A.1-§A.5).
        #    Это ЛОГИЧЕСКИЕ имена хранилищ (memory_dir_yaml, knowledge_index…),
        #    путь материализуется в runtime owning-компонентом (memory_store.py
        #    создаёт data_13/memory/ лениво). Резолв: owning-модуль существует
        #    → CURRENT (runtime-материализуемое хранилище). Честно: способность
        #    хранить есть, файл создаётся при первом использовании.
        shorthand_modules: dict[str, tuple[str, ...***REMOVED******REMOVED*** = {
            # owning-модуль ищется по всем code roots (core_02/ или scripts_01/).
            "memory_dir_yaml": ("core_02/memory_store.py", "scripts_01/memory_store.py"),
            "memory_index_sqlite": ("core_02/memory_store.py", "scripts_01/memory_store.py"),
            "knowledge_index": ("core_02/knowledge_engine.py", "scripts_01/knowledge_engine.py"),
            "graph_index_json_snapshot": ("core_02/graph_index.py", "scripts_01/graph_index.py"),
        ***REMOVED***
        if value in shorthand_modules:
            for owner in shorthand_modules[value***REMOVED***:
                if (self.workspace / owner).exists():
                    return {"resolved": True, "status": STATUS_CURRENT,
                            "evidence": f"logical storage, owned by {owner***REMOVED*** (runtime dir)"***REMOVED***
        shorthands: dict[str, str***REMOVED*** = {
            "runtime_05_scenarios_yaml": "runtime_05/scenarios/",
            "projects_dir": "projects_17/",
        ***REMOVED***
        if value in shorthands:
            target = self.workspace / shorthands[value***REMOVED***
            if target.exists():
                return {"resolved": True, "status": STATUS_CURRENT,
                        "evidence": shorthands[value***REMOVED******REMOVED***
        # 4. Top-level каталог (data_13, core_02, docs_10, runtime_05…).
        if value and (self.workspace / value).is_dir():
            return {"resolved": True, "status": STATUS_CURRENT,
                    "evidence": f"{value***REMOVED***/ (dir)"***REMOVED***
        return {"resolved": False, "status": STATUS_UNVERIFIED,
                "evidence": "no data_13/<name>.{yaml,json,jsonl***REMOVED*** / dir / known shorthand"***REMOVED***

    def _resolve_test(self, value: str) -> dict[str, Any***REMOVED***:
        # 1. Файл tests_09/test_<name>.py (спец §I.3: @test → тест-файл).
        file_part = value.split(".")[0***REMOVED***.rstrip("_")
        test_file = self.workspace / "tests_09" / f"{file_part***REMOVED***.py"
        if test_file.exists():
            return {"resolved": True, "status": STATUS_CURRENT,
                    "evidence": f"tests_09/{file_part***REMOVED***.py"***REMOVED***
        # 2. Fallback: test-функция/класс где-либо в tests_09 (AST, без import).
        tests_dir = self.workspace / "tests_09"
        if tests_dir.is_dir():
            for py in sorted(tests_dir.rglob("*.py")):
                if "__pycache__" in py.parts:
                    continue
                try:
                    tree = ast.parse(py.read_text(encoding="utf-8"))
                except (SyntaxError, OSError, UnicodeDecodeError):
                    continue
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                            and node.name == value:
                        return {"resolved": True, "status": STATUS_CURRENT,
                                "evidence": str(py.relative_to(self.workspace))***REMOVED***
                    if isinstance(node, ast.ClassDef) and node.name == value:
                        return {"resolved": True, "status": STATUS_CURRENT,
                                "evidence": str(py.relative_to(self.workspace))***REMOVED***
        return {"resolved": False, "status": STATUS_UNVERIFIED,
                "evidence": f"tests_09/{file_part***REMOVED***.py missing (and no function/class match)"***REMOVED***

    def _resolve_decision(self, value: str) -> dict[str, Any***REMOVED***:
        number = value.split("_", 1)[1***REMOVED***
        for base in ("docs_10/engineering-memory/decisions",
                     "docs_10/decisions"):
            hits = sorted((self.workspace / base).glob(f"ADR_{number***REMOVED***_*.md")) if (
                self.workspace / base).is_dir() else [***REMOVED***
            if hits:
                return {"resolved": True, "status": STATUS_CURRENT,
                        "evidence": str(hits[0***REMOVED***.relative_to(self.workspace))***REMOVED***
        return {"resolved": False, "status": STATUS_UNVERIFIED,
                "evidence": f"no ADR_{number***REMOVED***_*.md under docs_10/**/decisions"***REMOVED***

    def _resolve_requirement(self, value: str) -> dict[str, Any***REMOVED***:
        reg = self._read("docs_10/decisions/REQ_REGISTRY_V1.md")
        if reg is not None and value in reg:
            return {"resolved": True, "status": STATUS_CURRENT,
                    "evidence": "docs_10/decisions/REQ_REGISTRY_V1.md"***REMOVED***
        return {"resolved": False, "status": STATUS_DESIGN_ONLY,
                "evidence": "planned: REQ_REGISTRY_V1.md not present (Phase 1.4)"***REMOVED***

    def _resolve_scenario(self, value: str) -> dict[str, Any***REMOVED***:
        for ext in (".yaml", ".yml"):
            rel = f"runtime_05/scenarios/{value***REMOVED***{ext***REMOVED***"
            if (self.workspace / rel).exists():
                return {"resolved": True, "status": STATUS_CURRENT,
                        "evidence": rel***REMOVED***
        return {"resolved": False, "status": STATUS_DESIGN_ONLY,
                "evidence": "planned: runtime_05/scenarios/<name>.yaml absent"***REMOVED***

    def _resolve_factory(self, value: str) -> dict[str, Any***REMOVED***:
        if value in CANONICAL_FACTORIES:
            return {"resolved": True, "status": STATUS_CURRENT,
                    "evidence": "canonical factory enum (§3 FACTORY_FORGE)"***REMOVED***
        return {"resolved": False, "status": STATUS_UNVERIFIED,
                "evidence": f"not in canonical factories {list(CANONICAL_FACTORIES)***REMOVED***"***REMOVED***

    def _resolve_forge(self, value: str) -> dict[str, Any***REMOVED***:
        if value in CANONICAL_FORGES:
            return {"resolved": True, "status": STATUS_CURRENT,
                    "evidence": "canonical forge enum (RFC_BUFFY_FORGE §3)"***REMOVED***
        return {"resolved": False, "status": STATUS_UNVERIFIED,
                "evidence": f"not in canonical forges {list(CANONICAL_FORGES)***REMOVED***"***REMOVED***

    def _resolve_store_id(self, value: str, rel: str) -> dict[str, Any***REMOVED***:
        """@opportunity/@whim: id присутствует в YAML-store (substring)."""
        text = self._read(rel)
        if text is not None and value in text:
            return {"resolved": True, "status": STATUS_CURRENT,
                    "evidence": rel***REMOVED***
        return {"resolved": False, "status": STATUS_UNVERIFIED,
                "evidence": f"{value***REMOVED*** not in {rel***REMOVED***"***REMOVED***

    def _resolve_opportunity(self, value: str) -> dict[str, Any***REMOVED***:
        return self._resolve_store_id(value, "data_13/opportunities.yaml")

    def _resolve_whim(self, value: str) -> dict[str, Any***REMOVED***:
        return self._resolve_store_id(value, "data_13/whims.yaml")

    def _resolve_lesson(self, value: str) -> dict[str, Any***REMOVED***:
        if self._lessons_text is None:
            self._lessons_text = self._read("core_02/LESSONS.md") or ""
        # Нормализация [-_***REMOVED*** и ведущих нулей: CON_017 ≡ CON-17 ≡ CON17 ≡ CON-017.
        # LESSONS.md использует CON-17, ANTI-6b, R-127; доки часто пишут CON_017.
        def norm(s: str) -> str:
            digits = re.sub(r"[^0-9a-zA-Z***REMOVED***", "", s)
            digits = re.sub(r"(?<=[A-Za-z***REMOVED***)0+(?=\d)", "", digits)
            return digits.lower()
        if norm(value) in norm(self._lessons_text) or value in self._lessons_text:
            return {"resolved": True, "status": STATUS_LESSON,
                    "evidence": "core_02/LESSONS.md"***REMOVED***
        return {"resolved": False, "status": STATUS_UNVERIFIED,
                "evidence": "not found in core_02/LESSONS.md"***REMOVED***

    def _resolve_doc(self, value: str) -> dict[str, Any***REMOVED***:
        if self._doc_map_text is None:
            self._doc_map_text = self._read(
                "docs_10/engineering-memory/DOCUMENTATION_CODE_MAP_V1.md") or ""
        # 1. Полное claim-имя (`doc.factory_forge_arch#20.c4`).
        if value in self._doc_map_text:
            return {"resolved": True, "status": STATUS_CURRENT,
                    "evidence": "DOCUMENTATION_CODE_MAP_V1.md"***REMOVED***
        # 2. Fallback: base short-name до `#` зарегистрирован в карте.
        base = value.split("#", 1)[0***REMOVED***
        if base and base in self._doc_map_text:
            return {"resolved": True, "status": STATUS_CURRENT,
                    "evidence": "DOCUMENTATION_CODE_MAP_V1.md (base)"***REMOVED***
        return {"resolved": False, "status": STATUS_UNVERIFIED,
                "evidence": f"not in DOCUMENTATION_CODE_MAP_V1.md (base={base!r***REMOVED***)"***REMOVED***

    _DISPATCH = {
        "entity": _resolve_entity, "component": _resolve_component,
        "module": _resolve_module, "symbol": _resolve_symbol,
        "contract": _resolve_contract, "event": _resolve_event,
        "storage": _resolve_storage, "test": _resolve_test,
        "decision": _resolve_decision, "requirement": _resolve_requirement,
        "scenario": _resolve_scenario, "factory": _resolve_factory,
        "forge": _resolve_forge, "opportunity": _resolve_opportunity,
        "whim": _resolve_whim, "lesson": _resolve_lesson,
        "doc": _resolve_doc,
    ***REMOVED***

    # ── public API ─────────────────────────────────────────────────────
    def resolve(self, raw: str) -> dict[str, Any***REMOVED***:
        """Spec §I.3 `resolve_anchor(text, env)` — резолв одной строки/анкора.

        Returns: {raw, namespace, value, resolved, status, evidence***REMOVED***.
        """
        for ns in _NAMESPACE_ORDER:
            m = ANCHOR_RE[ns***REMOVED***.search(raw)
            if m:
                value = m.group(1)
                if ns == "test" and m.group(2):
                    value += m.group(2)
                if ns == "scenario":
                    value = value.rstrip(".")
                handler = self._DISPATCH[ns***REMOVED***
                result = handler(self, value)  # type: ignore[operator***REMOVED***
                return {
                    "raw": raw.strip(),
                    "namespace": ns,
                    "value": value,
                    "resolved": result["resolved"***REMOVED***,
                    "status": result["status"***REMOVED***,
                    "evidence": result["evidence"***REMOVED***,
                ***REMOVED***
        return {"raw": raw.strip(), "namespace": None, "value": "",
                "resolved": False, "status": STATUS_UNVERIFIED, "evidence": None***REMOVED***

    def resolve_document(self, doc_path: Path) -> dict[str, Any***REMOVED***:
        """Резолв всех анкоров одного .md файла → агрегат."""
        try:
            text = doc_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return {"doc": str(doc_path), "total": 0, "by_status": {***REMOVED***,
                    "by_namespace": {***REMOVED***, "unresolved": [***REMOVED******REMOVED***
        anchors = extract_anchors(text)
        resolved_list: list[dict[str, Any***REMOVED******REMOVED*** = [***REMOVED***
        by_status: dict[str, int***REMOVED*** = {***REMOVED***
        by_namespace: dict[str, int***REMOVED*** = {***REMOVED***
        unresolved: list[dict[str, Any***REMOVED******REMOVED*** = [***REMOVED***
        for anchor in anchors:
            r = self.resolve(anchor.raw)
            r["doc"***REMOVED*** = str(doc_path)
            r["line"***REMOVED*** = anchor.line_num
            by_status[r["status"***REMOVED******REMOVED*** = by_status.get(r["status"***REMOVED***, 0) + 1
            by_namespace[r["namespace"***REMOVED******REMOVED*** = by_namespace.get(r["namespace"***REMOVED***, 0) + 1
            resolved_list.append(r)
            if r["status"***REMOVED*** == STATUS_UNVERIFIED:
                unresolved.append(r)
        return {
            "doc": str(doc_path),
            "total": len(anchors),
            "by_status": by_status,
            "by_namespace": by_namespace,
            "resolved": resolved_list,
            "unresolved": unresolved,
        ***REMOVED***

    def run(self, roots: tuple[str, ...***REMOVED*** = _DEFAULT_DOC_ROOTS,
            exclude: tuple[str, ...***REMOVED*** = ()) -> dict[str, Any***REMOVED***:
        """Прогнать резолвер по корням (docs_10/, runtime_05/, CHANGELOG.md).

        Args:
            roots: корни сканирования (*.md рекурсивно для каталогов).
            exclude: имена файлов для пропуска (basename) — напр. мета-спека
                SEMANTIC_ANCHOR_SPEC_V1.md, чьи примеры (forge_unknown,
                StaleClass.old_method) ПЕДАГОГИЧЕСКИЕ, а не live-claims.
        """
        files: list[Path***REMOVED*** = [***REMOVED***
        for root in roots:
            p = self.workspace / root
            if p.is_file() and p.suffix == ".md":
                files.append(p)
            elif p.is_dir():
                files.extend(sorted(p.rglob("*.md")))
        docs = [f for f in files if f.exists() and f.name not in exclude***REMOVED***
        total = 0
        by_status: dict[str, int***REMOVED*** = {***REMOVED***
        by_namespace: dict[str, int***REMOVED*** = {***REMOVED***
        unresolved: list[dict[str, Any***REMOVED******REMOVED*** = [***REMOVED***
        for doc in docs:
            report = self.resolve_document(doc)
            total += report["total"***REMOVED***
            for k, v in report["by_status"***REMOVED***.items():
                by_status[k***REMOVED*** = by_status.get(k, 0) + v
            for k, v in report["by_namespace"***REMOVED***.items():
                by_namespace[k***REMOVED*** = by_namespace.get(k, 0) + v
            unresolved.extend(report["unresolved"***REMOVED***)
        return {
            "docs_checked": len(docs),
            "total_anchors": total,
            "by_status": by_status,
            "by_namespace": by_namespace,
            "unresolved": unresolved,
            "unresolved_count": len(unresolved),
        ***REMOVED***


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main(argv: Optional[list[str***REMOVED******REMOVED*** = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m core_02.anchors_resolver",
        description="AnchorResolver — 19-namespace semantic anchor resolver (Artifact I §I.3).",
    )
    parser.add_argument("target", nargs="?", default=".",
                        help="File/dir to scan (default: workspace root)")
    parser.add_argument("--workspace", default=".",
                        help="Workspace root (default: .)")
    parser.add_argument("--strict", action="store_true",
                        help="Exit 1 if any UNVERIFIED anchor found")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args(argv)

    workspace = Path(args.workspace).resolve()
    resolver = AnchorResolver(workspace)
    target = Path(args.target)
    if target.is_file():
        report = resolver.resolve_document(target.resolve())
        summary = report
    elif target.is_dir():
        root = target.resolve()
        roots = tuple(
            [str(root.relative_to(workspace))***REMOVED*** if root != workspace else list(_DEFAULT_DOC_ROOTS)
        )
        summary = resolver.run(tuple(roots))
    else:
        print(f"Target not found: {target***REMOVED***", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    else:
        if "by_status" in summary:
            bs = summary["by_status"***REMOVED***
            print(f"Docs checked : {summary.get('docs_checked', 1)***REMOVED***")
            print(f"Total anchors: {summary.get('total_anchors', summary.get('total', 0))***REMOVED***")
            print("By status    : " + ", ".join(f"{k***REMOVED***={v***REMOVED***" for k, v in sorted(bs.items())))
            if "by_namespace" in summary:
                print("By namespace : " + ", ".join(
                    f"{k***REMOVED***={v***REMOVED***" for k, v in sorted(summary["by_namespace"***REMOVED***.items())))
        unresolved = summary.get("unresolved", [***REMOVED***)
        if unresolved:
            print(f"\nUNVERIFIED ({len(unresolved)***REMOVED***):")
            for u in unresolved[:40***REMOVED***:
                print(f"  {u.get('doc')***REMOVED***:{u.get('line')***REMOVED*** {u.get('raw')***REMOVED*** — {u.get('evidence')***REMOVED***")
            if len(unresolved) > 40:
                print(f"  … and {len(unresolved) - 40***REMOVED*** more")

    strict_exit = 1 if args.strict and summary.get("unresolved_count", 0) else 0
    return strict_exit


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "ANCHOR_RE",
    "CANONICAL_FACTORIES",
    "CANONICAL_FORGES",
    "Anchor",
    "AnchorResolver",
    "extract_anchors",
    "main",
***REMOVED***
