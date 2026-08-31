"""core_02/blueprint_v3.py — Blueprint v3 reader and creator.

Mirrors the Kwork Arbitr v3.0.0 pipeline schema (XML-tagged Markdown roles +
declarative registry.yaml). Two responsibilities:

1. Reader: load ``registry.yaml`` and parse any role blueprint .md into a
   structured ``Blueprint`` (XML sections → dict).
2. Creator: scaffold a new role .md following the v3 schema and register it in
   ``registry.yaml`` so the pipeline picks it up automatically.

The grand design: the creator is a stateful tool that grows with experience — every
missing role discovered during a real project gets a stub here, validated, and
then refined as the project teaches what the role needs to do (and not do).

Usage::

    from core_02.blueprint_v3 import BlueprintCorpus

    corpus = BlueprintCorpus()  # reads DEFAULT_BLUEPRINTS_DIR
    corpus.list_roles()
    dev = corpus.load_blueprint("developer")
    missing = corpus.validate_blueprint(dev)

    # path 3 (создать новую роль)
    new = corpus.create_blueprint(
        role_id="mobile_developer",
        file_name="17_mobile_developer.md",
        role_title="AI Mobile Developer (React Native)",
        role_type="implementation",
        extra_sections={
            "role": "Ты — AI Mobile Developer уровня Senior, специализирующийся на React Native + Skia...\\n",
            "main_objective": "Реализовать production-ready мобильное приложение под iOS + Android с производительным 60 FPS канвасом.",
        },
    )
    corpus.write_blueprint(new)
    corpus.register_in_registry(...)
"""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml


# DESIGN DECISION: user owns the canonical blueprints_v3/ tree outside the
# freebuff repo. We read it but never mutate without an explicit write call
# (write_blueprint / register_in_registry). Path is configurable so tests can
# point at a fixture copy.
DEFAULT_BLUEPRINTS_DIR = Path("/storage/emulated/0/PROJECTS/workstation/blueprints_v3")


# Required XML sections per v3 schema (any missing ⇒ blueprint is incomplete).
REQUIRED_SECTIONS: tuple[str, ...] = (
    "role",
    "system_role",
    "input",
    "main_objective",
    "priority_order",
    "implementation_scope_rules",
)

# Optional but recommended sections in v3 (validated, but absence is not an error).
OPTIONAL_SECTIONS: tuple[str, ...] = (
    "micro_architecture_canon",
    "immutable_vs_mutable",
    "decomposition_rules",
    "engineering_laws",
    "deterministic_delivery_rules",
    "atomic_commit_rules",
    "code_validity_requirements",
    "development_rules",
    "dependency_governance",
    "testing_requirements",
    "self_validation_loop",
    "output_format",
    "hard_rules",
    "response_style",
)

# Available role types (mirrors MANIFEST categories). New categories are allowed
# but must be added here so registry typing stays consistent.
ROLE_TYPES: tuple[str, ...] = (
    "management",
    "analysis",
    "estimation",
    "architecture",
    "communication",
    "implementation",
    "infrastructure",
    "validation",
    "delivery",
    "evolution",
)


# Capability strings per role_id. Used by ``routing_hint(role_id)`` to bridge
# Blueprint v3 → SmartRouter (``core_02.router.SmartRouter``).
#
# Why an override map instead of editing every blueprint .md:
# The canonical ``~/.../blueprints_v3/`` corpus lives OUTSIDE the freebuff
# workspace; this environment forbids writes outside the project root. So we
# keep the schema-level commitment (``<capabilities>`` XML section) intact for
# future migrations — a blueprint that DOES contain a ``<capabilities>``
# section wins over the override (parse-first). For roles where the canonical
# file does not yet have the section, we fall back to this curated mapping.
#
# Capability vocabulary MUST be a subset of ``KNOWN_CAPABILITIES`` (mirrors the
# real ``ModelCatalog`` in ``core_02/router.py``). The ``BlueprintCorpus``
# constructor validates this at init time; a stray token like ``"qa"``
# (which exists in role descriptions but NOT in ``ModelCatalog``) would
# silently demote routing to qwen2.5:1.5b (200ms latency) for tasks that
# deserve a cloud code-capable model — see ``LESSONS.md`` ANTI-6 / CON-8.

# Cross-reference — Phase 12 / G-11.6 capability routing consensus.
# THIS file (CAPABILITIES_OVERRIDE) is the role-side D-1 (Model Router) view:
# a capability declared here governs which MODEL can fulfil a role that
# produces that capability. It is NOT authoritative on FACTORY-side routing.
# The authoritative `code` → (test, verifier) FACTORY mapping lives in
# docs_10/engineering-memory/CANONICAL_ENGINE_ROUTING_V1.md §D-2 (decided
# in Phase 12 G-11.6 workshop by ScenarioIntelligence author + TestFactory
# author + Blueprint v3 author). The two layers coexist by design (CON-7
# + D-3 invariant) and never collapse to make a single source of truth.
# See CANONICAL_ENGINE_ROUTING_V1.md for the full 3-layer routing model.
CAPABILITIES_OVERRIDE: dict[str, list[str]] = {
    "orchestrator":   ["reasoning", "plan", "explain", "summarize"],
    "context_keeper": ["summarize", "explain"],
    "explainer":      ["summarize", "explain", "classify"],
    "lisa":           ["summarize", "estimation"],
    "risk":           ["summarize", "explain", "reasoning"],
    "decomposer":     ["architecture", "explain", "plan"],
    "architect":      ["architecture", "explain", "summarize"],
    "auditor":        ["review", "architecture", "explain"],
    "response_writer": ["explain", "summarize"],
    "developer":      ["code", "refactor", "explain", "summarize"],
    "frontend":       ["code", "summarize", "explain"],
    "devops":         ["code", "summarize", "reasoning"],
    "tester":         ["code", "summarize", "review"],
    "fixer":          ["code", "refactor", "explain"],
    "acceptance":     ["review", "explain", "summarize"],
    "documenter":     ["summarize", "explain"],
    "retrospective":  ["summarize", "explain", "reasoning"],
    "environment_doctor": ["diagnose", "validate", "report"],
}


# Closed set of capability strings the SmartRouter understands. MUST stay in
# lockstep with the ``capabilities`` lists in
# ``ModelCatalog.default()`` (core_02/router.py). The regression test
# ``test_known_capabilities_subset_of_actual_catalog`` panics if drift is
# detected. New capability strings MUST be added both here and in the
# catalog before they can appear in CAPABILITIES_OVERRIDE.
KNOWN_CAPABILITIES: frozenset[str] = frozenset({
    "local", "fast", "code", "summarize",
    "router", "classify",
    "reasoning", "plan", "refactor", "explain",
    "deep", "architecture", "review",
    "vision", "tools", "long_context", "multimodal",
    "instruct",
    "diagnose", "validate", "report",
    "research",  # веб-исследование (research_web, Missing Capability #6)
    "estimation",  # оценка сложности LISA-3 (lisa_estimator, Missing Capability #7)
    "article_generation",  # Content Factory (Phase 9, промт 092)
    "book_generation",     # Content Factory (Phase 9, промт 092)
    "report_generation",   # Content Factory (Phase 9, промт 092)
})


@dataclass
class Blueprint:
    """Parsed role blueprint mirror of a v3 .md file."""

    file: str  # e.g. "09_developer.md"
    header_meta: dict[str, str] = field(default_factory=dict)
    sections: dict[str, str] = field(default_factory=dict)

    def to_markdown(self) -> str:
        """Render back to a v3-compliant Markdown string."""
        role_line = self.header_meta.get("ROLE", "ROLE: (unset)")
        version_line = self.header_meta.get("VERSION", "3.1.0")
        out: list[str] = [f"ROLE: {role_line}", f"VERSION: {version_line}", ""]
        # Required first, then optional, in declared order to keep diffs stable.
        order = list(REQUIRED_SECTIONS) + list(OPTIONAL_SECTIONS)
        for sec in order:
            if sec in self.sections:
                out.append(f"<{sec}>")
                out.append(self.sections[sec].rstrip())
                out.append(f"</{sec}>")
                out.append("")
        return "\n".join(out).rstrip() + "\n"


# ─── parsing primitives ──────────────────────────────────────────────────────

_SECTION_RE = re.compile(r"<(\w+)>([\s\S)*?)</\1>", re.MULTILINE)
_HEADER_RE = re.compile(r"^([A-Z)[A-Z0-9_]+):[ \t]+(.+?)$", re.MULTILINE)


def parse_blueprint_md(text: str) -> Blueprint:
    """Parse a v3 blueprint Markdown into structured sections (public API).

    Public so test fixtures and downstream tools can reuse the same parser
    without reaching into private symbols.
    """
    sections = {m.group(1).lower(): m.group(2).strip() for m in _SECTION_RE.finditer(text)}
    header_meta = {m.group(1): m.group(2).strip() for m in _HEADER_RE.finditer(text)}
    return Blueprint(file="", header_meta=header_meta, sections=sections)


def _insert_into_pipeline(text: str, block: str) -> str:
    """Insert ``block`` (a ``- id: ...`` list entry) into the ``pipeline:`` list.

    Fallback for ``register_in_registry`` when the ``# Project type routing``
    marker is missing — e.g. the user reformatted registry.yaml by hand
    (CAN-4). Locates the top-level ``pipeline:`` key and inserts the new entry
    before the next top-level section, keeping it inside the existing list
    (no duplicate ``pipeline:`` header created).
    """
    lines = text.splitlines()
    pipeline_idx = next(
        (i for i, ln in enumerate(lines) if ln.strip() == "pipeline:"),
        None,
    )
    if pipeline_idx is None:
        # No pipeline section at all — degrade to append (post-parse guard
        # will still validate the result before touching disk).
        return text.rstrip() + "\n\n" + block
    # Find the next top-level section (column 0, non-comment, non-empty).
    insert_at = len(lines)
    for j in range(pipeline_idx + 1, len(lines)):
        ln = lines[j]
        if ln and not ln.startswith((" ", "\t", "#")):
            insert_at = j
            break
    out = lines[:insert_at] + [block.rstrip("\n")] + lines[insert_at:]
    return "\n".join(out) + "\n"


# ─── corpus wrapper ───────────────────────────────────────────────────────────


class BlueprintCorpus:
    """Reader + creator for the Kwork Arbitr v3 pipeline corpus."""

    def __init__(self, root: Optional[Path] = None, scenario_id: str = "blueprint_v3"):
        self.root = Path(root) if root is not None else DEFAULT_BLUEPRINTS_DIR
        if not (self.root / "registry.yaml").exists():
            raise FileNotFoundError(f"registry.yaml not found at {self.root}")
        self.registry = self._load_registry()
        self._index: dict[str, dict] = {e["id"]: e for e in self.registry.get("pipeline", [])}
        self._scenario_id = scenario_id
        # Vocabulary drift defense: any override token that doesn't overlap with
        # KNOWN_CAPABILITIES (the real catalog) silently demotes routing to
        # the lowest-latency model. Fail loudly here so we catch it on init,
        # not on the first ``run_wizard`` call. See LESSONS.md CON-8 / ANTI-6.
        # The validator is PUBLIC (no leading underscore) so unit tests can
        # call it directly — if a future refactor removes it, the test
        # ``tests_09/test_wizard.py::test_capabilities_override_init_rejects_unknown_token``
        # fails with AttributeError instead of silently passing.
        BlueprintCorpus.validate_override_vocabulary()

    # ─── Scenario ABC conformance (used by ScenarioRegistry) ────────────────
    #
    # These methods project the BlueprintCorpus into the uniform Role shape
    # used by core_02.scenario_registry. They DO NOT replace the legacy
    # ``list_roles`` (returns tuples), ``load_blueprint`` (returns Blueprint),
    # etc. — both APIs coexist; registry/Scenario ABC uses only the new ones.

    @property
    def scenario_id(self) -> str:
        """Unique id used by registry cross-references."""
        return self._scenario_id

    @property
    def display_name(self) -> str:
        """Human-readable label for UI."""
        return "Kwork Arbitr v3 — AI Engineering Pipeline"

    def role_objects(self) -> list["Role"]:
        """Project ``list_roles()`` tuples into :class:`Role` dataclasses.

        Used by :class:`core_02.scenario_registry.ScenarioRegistry` for
        cross-scenario discovery. Each row already carries its own
        routing_hint (computed lazily per role) so the registry has data
        in one pass.

        Uses ``role_objects()`` (not ``roles()``) to avoid shadowing the
        legacy ``def roles(self) -> list[dict]`` further down in this file
        that returns ``_index.values()``. See LESSONS ANTI-7b / PB-8.
        """
        from core_02.scenario import Role
        out: list[Role] = []
        for role_id, file_name, title, role_type in self.list_roles():
            try:
                hint = tuple(self.routing_hint(role_id))
            except KeyError:
                hint = ()
            out.append(
                Role(
                    scenario_id=self._scenario_id,
                    role_id=role_id,
                    title=title,
                    role_type=role_type,
                    file=file_name,
                    routing_hint=hint,
                )
            )
        return out

    def load_role_text(self, role_id: str) -> str:
        """Concatenate ROLE header + role/system_role/main_objective sections.

        Returns empty string on missing role so the registry's
        ``propose_roles`` treats it as 0-match-able (not as error).
        """
        try:
            bp = self.load_blueprint(role_id)
        except (FileNotFoundError, KeyError):
            return ""
        parts = [
            bp.header_meta.get("ROLE", ""),
            bp.sections.get("role", ""),
            bp.sections.get("system_role", ""),
            bp.sections.get("main_objective", ""),
        ]
        return " ".join(p for p in parts if p)

    def validate(self) -> list[str]:
        """Per-scenario validation gate called by ``ScenarioRegistry.validate_all``.

        Vocabulary drift defense is enforced at :meth:`__init__` already —
        this method exists for the ABC contract and reports lazy errors
        (corrupt blueprint sections discovered on demand).
        """
        errors: list[str] = []
        for role_id, _file, _title, _type in self.list_roles():
            try:
                bp = self.load_blueprint(role_id)
            except FileNotFoundError as exc:
                errors.append(f"role_id {role_id!r}: {exc}")
                continue
            missing = self.validate_blueprint(bp)
            if missing:
                errors.append(f"role_id {role_id!r}: missing sections {missing}")
        return errors

    @classmethod
    def validate_override_vocabulary(cls) -> None:
        """Public guard: declare it on the class so tests can ``hasattr``-check it.

        Renamed from the private ``_validate_override_vocabulary`` per
        testability review: if a future refactor removes this method,
        ``tests_09/test_wizard.py`` fails loudly with ``AttributeError``
        instead of silently passing through to a broken init.
        """
        unknown_by_role = {
            role_id: [c for c in caps if c not in KNOWN_CAPABILITIES]
            for role_id, caps in CAPABILITIES_OVERRIDE.items()
            if any(c not in KNOWN_CAPABILITIES for c in caps)
        }
        if unknown_by_role:
            raise ValueError(
                "CAPABILITIES_OVERRIDE содержит capability tokens, которых нет "
                "в ModelCatalog (core_02/router.py) — это вызывает silent fallback "
                "на qwen2.5:1.5b у SmartRouter: "
                f"{unknown_by_role}. "
                "Используй только строки из KNOWN_CAPABILITIES. "
                f"Закрытое множество: {sorted(KNOWN_CAPABILITIES)}."
            )

    # ─── reading ─────────────────────────────────────────────────────────────

    def _load_registry(self) -> dict:
        import yaml  # local import keeps import-time cheap for callers
        path = self.root / "registry.yaml"
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            # CAN-1: broken YAML must fail loudly with a section-hinted
            # ValueError, not a raw traceback (self-healing UX for the
            # "pipeline fell mid-project" scenario).
            raise ValueError(
                f"registry.yaml повреждён (невалидный YAML) в {path}: {exc}. "
                "Восстанови файл из .bak.* бэкапа или почини синтаксис "
                "секции перед повторным запуском."
            ) from exc
        if not isinstance(data, dict):
            # Empty file / null document — cannot build the pipeline index.
            raise ValueError(
                f"registry.yaml пуст или имеет неожиданную структуру в {path}: "
                "ожидался словарь с секцией 'pipeline'."
            )
        return data

    def role_entries(self) -> list[dict]:
        """Return all role entries as plain dicts (read-only view).

        Kept under a distinct name from ``role_objects()`` so the latter
        (Scenario ABC conformance) isn't shadowed by Python's last-def-wins
        class-body rule. See LESSONS ANTI-7b / PB-8.
        """
        return list(self._index.values())

    def list_roles(self) -> list[tuple[str, str, str, str]]:
        """Return (id, file, role_title, type) tuples — handy for human display."""
        return [
            (rid, e.get("file", ""), e.get("role", ""), e.get("type", ""))
            for rid, e in self._index.items()
        ]

    def list_by_type(self, role_type: str) -> list[tuple[str, str, str, str]]:
        return [r for r in self.list_roles() if r[3] == role_type]

    def load_blueprint(self, role_id: str) -> Blueprint:
        entry = self._index[role_id]
        path = self.root / entry["file"]
        if not path.exists():
            raise FileNotFoundError(f"blueprint missing on disk: {path}")
        bp = parse_blueprint_md(path.read_text(encoding="utf-8"))
        bp.file = entry["file"]
        return bp

    def validate_blueprint(self, bp: Blueprint) -> list[str]:
        """Return list of missing required section names (empty = valid)."""
        return [s for s in REQUIRED_SECTIONS if s not in bp.sections]

    def resolve_pipeline(self, project_type: Optional[str] = None,
                         complexity: Optional[str] = None) -> list[str]:
        """Compute canonical role order for the given project_type + complexity tier.

        Mirrors registry.yaml's project_types.* and complexity_routing.* tables.
        Both filters are optional; pass only one to apply a single constraint.
        """
        required = {rid for rid in self._index.keys()}
        skip: set[str] = set()
        if project_type:
            cfg = self.registry.get("project_types", {}).get(project_type, {})
            required &= set(cfg.get("required_roles", [])) or required
            skip |= set(cfg.get("skip_roles", []))
        if complexity:
            cfg = self.registry.get("complexity_routing", {}).get(complexity, {})
            required &= set(cfg.get("required_roles", [])) or required
            skip |= set(cfg.get("skip_roles", []))
        return sorted(required - skip)

    # ─── routing_hint bridge (Blueprint ↔ SmartRouter) ───────────────────────

    def routing_hint(self, role_id: str) -> list[str]:
        """Return capability strings for ``role_id``, ready for SmartRouter.route().

        Resolution priority:
        1. ``<capabilities>`` XML section in the role's blueprint (lines like
           ``- code`` or comma-separated values inside that section).
        2. ``CAPABILITIES_OVERRIDE`` mapping (curated fallback).
        3. Empty list (SmartRouter will fall back to BALANCED preference).

        See ``core_02/LESSONS.md`` ANTI-6 / CAN-5 for design rationale.
        """
        if role_id not in self._index:
            raise KeyError(f"role_id '{role_id}' not in registry")
        try:
            bp = self.load_blueprint(role_id)
        except FileNotFoundError:
            # Bare blueprint file missing — return override only.
            return list(CAPABILITIES_OVERRIDE.get(role_id, []))
        if "capabilities" in bp.sections:
            raw = bp.sections["capabilities"]
            caps = []
            for line in raw.splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                # Bullet-prefixed lines (- code), em-dash, or just bare terms.
                cleaned = stripped.lstrip("-*•·").strip()
                if cleaned:
                    caps.append(cleaned)
            if caps:
                return caps
        return list(CAPABILITIES_OVERRIDE.get(role_id, []))

    # ─── creation ────────────────────────────────────────────────────────────

    def _stubs_for_role(self, role_title: str) -> dict[str, str]:
        """Default stub content for required sections when caller leaves them blank."""
        return {
            "role": (
                f"# Кто ты и что отвечаешь\n"
                f"Ты — {role_title} внутри AI Engineering Pipeline.\n"
                f"# Обновить: добавить 2–3 предложения про область экспертизы."
            ),
            "system_role": (
                "Что ты ДЕЛАЕШЬ:\n"
                "- (project bullet 1)\n"
                "- (project bullet 2)\n\n"
                "Что ты НЕ ДЕЛАЕШЬ (категорически запрещено):\n"
                "- (out-of-scope bullet 1)"
            ),
            "input": "1. (input artifact 1)\n2. (input artifact 2)",
            "main_objective": (
                "Outcome statement: какой артефакт считается успехом после прогона."
            ),
            "priority_order": (
                "Correctness\nContract Compliance\nRuntime Safety\nFailure Handling\n"
                "Testability\nObservability\nMaintainability\nPerformance Optimization\n"
                "Code Elegance"
            ),
            "implementation_scope_rules": (
                "Разрешено:\n- (allowed action)\n\n"
                "Запрещено:\n- (forbidden action)"
            ),
        }

    def create_blueprint(
        self,
        role_id: str,
        file_name: str,
        role_title: str,
        role_type: str,
        extra_sections: Optional[dict[str, str]] = None,
        version: str = "3.1.0",
    ) -> Blueprint:
        """Scaffold a new Blueprint for ``role_id``.

        Required sections that caller didn't supply are auto-stubbed with TODO
        markers ("(project bullet)") so the role is structurally valid but
        semantically marked incomplete. The role_creator spirit: scaffold first,
        refine as experience grows.
        """
        if role_id in self._index:
            raise ValueError(f"role_id '{role_id}' уже зарегистрирован в registry.yaml")
        if role_type not in ROLE_TYPES:
            raise ValueError(f"role_type '{role_type}' не из списка {ROLE_TYPES}")
        if not file_name.endswith(".md"):
            raise ValueError("file_name должен заканчиваться на .md")

        sections = self._stubs_for_role(role_title)
        if extra_sections:
            sections.update(extra_sections)

        return Blueprint(
            file=file_name,
            header_meta={"ROLE": role_title, "VERSION": version},
            sections=sections,
        )

    def write_blueprint(self, bp: Blueprint) -> Path:
        """Persist a blueprint to the canonical directory. Returns target Path.

        Preview path is ``bp.to_markdown()`` (no dry_run here — keeping the
        return type stable per review feedback). Raises if the target file
        already exists or the directory isn't writable.
        """
        target = self.root / bp.file
        if target.exists():
            raise FileExistsError(
                f"{target} уже существует — не перезаписываем молча. "
                f"Передай новое имя файла или удали существующий перед записью."
            )
        if not os.access(self.root, os.W_OK):
            raise PermissionError(f"{self.root} не доступен на запись")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(bp.to_markdown(), encoding="utf-8")
        return target

    def register_in_registry(
        self,
        role_id: str,
        file_name: str,
        role_title: str,
        role_type: str,
        description: str,
        triggers: list[str],
        dependencies: Optional[list[str]] = None,
        outputs: Optional[list[str]] = None,
        condition: str = "always",
        dry_run: bool = False,
    ):
        """Append new role entry to ``registry.yaml``.

        Uses a textual splice before the ``# Project type routing`` marker to
        preserve human-friendly formatting. Validates the result parses as YAML
        before writing — if the splice produces unparseable YAML, the original
        file is restored from backup and the error is re-raised (no silent
        corruption of user-owned registry.yaml).
        """
        if role_id in self._index:
            raise ValueError(f"role_id '{role_id}' уже зарегистрирован")
        if role_type not in ROLE_TYPES:
            raise ValueError(f"role_type '{role_type}' не из списка {ROLE_TYPES}")

        dep = dependencies or []
        out = outputs or []
        block_lines = [
            f"  - id: {role_id}",
            f"    file: {file_name}",
            f"    type: {role_type}",
            f"    role: {role_title}",
            f"    description: {description}",
            f"    condition: {condition}",
            "    triggers:",
        ]
        for t in triggers:
            block_lines.append(f'      - "{t}"')
        if dep:
            block_lines.append("    dependencies:")
            for d in dep:
                block_lines.append(f"      - {d}")
        if out:
            block_lines.append("    outputs:")
            for o in out:
                block_lines.append(f"      - {o}")
        block = "\n".join(block_lines) + "\n"

        import yaml  # kept local so a missing PyYAML only fails when needed

        registry_path = self.root / "registry.yaml"
        text = registry_path.read_text(encoding="utf-8")
        marker = "# Project type routing"
        new_text = text.replace(marker, block + "\n" + marker)
        if new_text == text:
            # Marker missing (user reformatted registry.yaml) — CAN-4:
            # insert into the existing pipeline list instead of appending at
            # EOF (which would create a duplicate/corrupt section).
            new_text = _insert_into_pipeline(text, block)

        # Validate the spliced text parses as YAML before touching disk.
        try:
            parsed = yaml.safe_load(new_text)
        except yaml.YAMLError as exc:
            raise ValueError(
                f"Сплис реестра дал невалидный YAML — НЕ пишем на диск: {exc}"
            ) from exc
        if not isinstance(parsed, dict) or "pipeline" not in parsed:
            raise ValueError(
                "Сплис реестра дал валидный YAML, но без секции 'pipeline' — отменяем запись."
            )

        if dry_run:
            return new_text
        # Backup with timestamp (overwrite-collisions safe on multi-step edits).
        backup = registry_path.with_name(
            registry_path.name + f".bak.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
        )
        shutil.copy2(registry_path, backup)
        try:
            registry_path.write_text(new_text, encoding="utf-8")
        except OSError:
            # Restore from backup if write partially succeeded.
            shutil.copy2(backup, registry_path)
            raise
        # Reload in-memory so subsequent calls see the new role.
        self.__init__(self.root)
        return new_text


__all__ = [
    "DEFAULT_BLUEPRINTS_DIR",
    "REQUIRED_SECTIONS",
    "OPTIONAL_SECTIONS",
    "ROLE_TYPES",
    "CAPABILITIES_OVERRIDE",
    "KNOWN_CAPABILITIES",
    "Blueprint",
    "BlueprintCorpus",
    "BlueprintScenario",
]


# ─── virtual subclass registration (closes isinstance failures) ─────────────
# ScenarioRegistry + scenario_abc tests assert:
#   isinstance(sc, Scenario) is True where sc is a BlueprintCorpus instance.
# Concrete ABC inheritance would clash with our (scenario_id, root) kwargs
# kwargs signature. Use the abc virtual-subclass register() classmethod —
# BlueprintCorpus satisfies the Scenario ABC surface (scenario_id/display_name
# properties + roles/load_role_text/routing_hint/validate methods) so the
# virtual registration is safe.
from core_02.scenario import Scenario  # local import — pre-class-time safe
Scenario.register(BlueprintCorpus)


# BC alias: ``BlueprintScenario`` is the canonical name going forward (used by
# ``core_02/scenario_registry.py`` and future scenario types). ``BlueprintCorpus``
# remains for backward compatibility with existing tests / scripts that import
# it. Both names refer to the same concrete class.
BlueprintScenario = BlueprintCorpus
