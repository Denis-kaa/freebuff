# SEMANTIC ANCHOR SPEC (Artifact I — Phase C Specification)

> **Goal:** Lock in a **machine-readable, line-number-independent anchor schema** for the Freebuff engineering memory so artifacts A/B/C/D/E/F/G/H/J/K/L interlock consistently.
> **Conforms to:** `projects_17/content_factory/promts/4.md` §5 (SEMANTIC ANCHORS), §6 (DOC ANCHORING), §7 (CODE ANCHORING), §14 (VECTOR + GRAPH), §17 (live documentation discipline).
> **Counterparts required:**
> - Artifact A `PLATFORM_CODE_MAP_V1.md` — defines `@entity` namespace (25 entries).
> - Artifact B `DOCUMENTATION_CODE_MAP_V1.md` — defines `doc.*#<section>[.cN***REMOVED***` cross-doc claim anchors (78 entries).
> - This artifact I — defines 19 namespaces (15 base + 4 `@lesson` subtypes CON/ANTI/CAN/R added Phase 1.5), format rules, AnchorResolver, status integration.
> **REPOSITORY = SOURCE OF TRUTH:** every anchor MUST resolve to either (a) existing code, file, or registry; (b) registered design (MissingRegistry or ARCHITECTURE_DECISION_REGISTRY); or (c) status=`UNVERIFIED` if no resolution exists.
> **Line-number PROHIBITED:** identity is anchored to symbol or section, never to a row in a file.

---

## §I.1 — Anchor Namespace Taxonomy (19 namespaces: 15 base + 4 `@lesson` subtypes)

All anchors represent a **node** in the Traceability Graph (Artifact E). Each namespace has a strict format (see §I.2) and a resolution target (see §I.3).

| # | Namespace     | Semantic role                                                            | Example                                                 | Resolution target                                          |
|---|---------------|--------------------------------------------------------------------------|---------------------------------------------------------|------------------------------------------------------------|
| 1 | `@entity`     | Core platform noun (Composable component)                               | `@entity forge.facade`                                  | Artifact A table — `ENTITY_ID` column                     |
| 2 | `@component`  | Internal sub-part of an `@entity` (Architectural piece)                 | `@component forge.facade.chain_runner`                  | sub-class / sub-section referenced in §I.4                |
| 3 | `@module`     | Python file abstraction                                                  | `@module forge.cli` (= `scripts_01/forge.py`)          | filesystem path `scripts_01/forge.py` (no .py)            |
| 4 | `@symbol`     | Code-level symbol (Class or function)                                   | `@symbol ScenarioRegistry.find_role`                    | static grep in `core_02/scenario_registry.py`             |
| 5 | `@contract`   | Interface pact — producer/consumer/IO schema                            | `@contract forge.execution`                             | Artifact C `CONTRACT_REGISTRY` row                          |
| 6 | `@event`      | Pub/Sub event type (event-bus dispatcher)                               | `@event forge.chain_started`                            | `scripts_01/event_bus.py` registered events                |
| 7 | `@storage`    | Persistence unit (data record or YAML store)                            | `@storage opportunities_yaml`                           | `data_13/opportunities.yaml`                              |
| 8 | `@test`       | Test path or test-class / test-function                                 | `@test test_scenario_registry`                          | `tests_09/test_scenario_registry.py` lookup               |
| 9 | `@decision`   | Architecture Decision Record (ADR)                                       | `@decision ADR_010`                                     | `docs_10/engineering-memory/decisions/ADR_010_*.md`       |
| 10| `@requirement`| Tracked requirement (REQ-XXX-NN slug)                                  | `@requirement REQ-OBSERVABILITY-03`                     | `docs_10/decisions/REQ_REGISTRY_V1.md` (planned)          |
| 11| `@scenario`   | Runtime scenario manifest (YAML)                                         | `@scenario create_product`                              | `runtime_05/scenarios/create_product.yaml` (planned)      |
| 12| `@factory`    | Future Factory entity (canonical Factories per `FACTORY_FORGE_ARCHITECTURE_V1 §3/§10-§12`, active `core_02/factory_registry.py` v5.188.2) | `@factory architecture_factory` / `@factory code_factory` / `@factory research_factory` / `@factory content_factory` | grep enum per verified list (4 canonical factories) |
| 13| `@forge`      | Execution stream (L0-L5 per `RFC_BUFFY_FORGE_V1 §3 classification table`) | `@forge forge_idea` / `@forge forge_knowledge` / `@forge forge_architecture` / `@forge forge_implementation` / `@forge forge_validation` / `@forge forge_evolution`     | enum (6 L0-L5 canonical forges) |
| 14| `@opportunity`| Live Opportunity instance                                                | `@opportunity opp_2793abf60a`                           | `data_13/opportunities.yaml` lookup                        |
| 15| `@whim`       | Live Whim capture instance                                               | `@whim whim_2793abf60a`                                 | `data_13/whims.yaml` lookup                                |
| 16| `@lesson CON`  | Architectural convention / hardened rule (from `core_02/LESSONS.md`)     | `@lesson CON_017`                                       | `core_02/LESSONS.md` (CON section) grep                   |
| 17| `@lesson ANTI` | Identified anti-pattern to prevent                                       | `@lesson ANTI_06b`                                      | `core_02/LESSONS.md` (ANTI section) grep                  |
| 18| `@lesson CAN`  | Canonical must-not-do / dogma                                            | `@lesson CAN_017`                                       | `core_02/LESSONS.md` (CAN section) grep                   |
| 19| `@lesson R`    | Hard operational rule / constraint                                        | `@lesson R_001`                                         | `core_02/LESSONS.md` (R section) grep                     |

**Extension (Documentation claim anchor):** `doc.<short_name>#<section>[.cN***REMOVED***` (defined in Artifact B §D.4):

| #  | Namespace | Format | Example                                          | Resolution target                       |
|----|-----------|--------|--------------------------------------------------|------------------------------------------|
| EXT| `doc.*`   | `<short_name>#<section_anchor>[.claim_N***REMOVED***`       | `doc.factory_forge_arch#20.c4`                   | Artifact B §B.2 doc.factory_forge_arch row 12 (`@entity opportunity.engine`, FACT, `✅ реализовано v5.187.7`) |

**Why this taxonomy:** 13 namespaces cover the **architectural primitives** (entity / component / module / symbol / contract / event / storage / test / decision / requirement / scenario / factory / forge) + 2 **operational instance anchors** (`@opportunity`, `@whim`) that are concrete entities in `data_13/`. The extension `doc.*` is a hybrid: it's documented in Artifact B but follows Artifact I's anchor patterns.

---

## §I.2 — Format rules per namespace (Regex)

```
@entity          \s+ [a-z***REMOVED***[a-z0-9_***REMOVED**** (\.[a-z***REMOVED***[a-z0-9_***REMOVED****)+       e.g., forge.facade
@component       \s+ [a-z***REMOVED***[a-z0-9_***REMOVED**** (\.[a-z***REMOVED***[a-z0-9_***REMOVED****)*       e.g., forge.facade.chain_runner
@module          \s+ [a-z***REMOVED***[a-z0-9_***REMOVED**** (\.[a-z***REMOVED***[a-z0-9_***REMOVED****)+       e.g., forge.cli (= scripts_01/forge.py)
@symbol          \s+ [A-Z***REMOVED***[A-Za-z0-9_***REMOVED***+ \. [a-z_***REMOVED***[A-Za-z0-9_***REMOVED****   e.g., ScenarioRegistry.find_role
@contract        \s+ [a-z***REMOVED***[a-z0-9_***REMOVED**** (\.[a-z***REMOVED***[a-z0-9_***REMOVED****)+       e.g., forge.execution
@event           \s+ [a-z***REMOVED***[a-z0-9_***REMOVED**** (\.[a-z***REMOVED***[a-z0-9_***REMOVED****)+       e.g., forge.chain_started
@storage         \s+ [a-z***REMOVED***[a-z0-9_***REMOVED***+ (_[a-z***REMOVED***[a-z0-9_***REMOVED****)*        e.g., opportunities_yaml
@test            \s+ test_ [a-z***REMOVED***[a-z0-9_***REMOVED**** (\.[A-Za-z_***REMOVED***[\w***REMOVED****)?   e.g., test_scenario_registry.TestRegistry
@decision        \s+ ADR_\d{3***REMOVED***                                    e.g., ADR_010
@requirement     \s+ [a-z***REMOVED***[a-z0-9_***REMOVED***+(\.[a-z***REMOVED***[a-z0-9_***REMOVED****)+        e.g., project.runnability   (lowercase.dot — derived from docs_10/core/PROJECT_REQUIREMENTS.md + workspace.py + RUNTIME_ABSTRACTION_SPECIFICATION.md usage)
@scenario        \s+ [a-z***REMOVED***[a-z0-9_***REMOVED****(\.[a-z***REMOVED***[a-z0-9_***REMOVED****)*       e.g., create_product
@factory         \s+ [a-z***REMOVED***[a-z0-9_***REMOVED****_factory                    e.g., architecture_factory
@forge           \s+ forge_[a-z***REMOVED***[a-z0-9_***REMOVED****                       e.g., forge_idea
@opportunity     \s+ opp-[a-z0-9***REMOVED***+                               e.g., opp-2793abf60a
@whim            \s+ whim-[a-z0-9***REMOVED***+                              e.g., whim-2793abf60a
@lesson          \s+ (CON|ANTI|CAN|R)[-_***REMOVED***\d{2,3***REMOVED***[a-z***REMOVED***?           e.g., CON_017, ANTI_06b, CAN_017, R_001
doc.*            \s+ [a-z***REMOVED***[a-z0-9_***REMOVED****\.?[a-z0-9_***REMOVED****\#[\w\.-***REMOVED***+     e.g., doc.factory_forge_arch#20.c4
```

**Constraints:**
- **No line numbers** as identity — anchors must NOT contain `:L123` or `:L42-L67`.
- **Case-sensitive** — `@entity Forge.Facade` (F capital) is invalid; use `@entity forge.facade`.
- **Stable** — namespace identifier (`@entity`, `@module`, ...) is fixed; only the payload after the namespace can vary.

---

## §I.3 — AnchorResolver logic (lookup algorithm)

AnchorResolver is the canonical reference resolver that all downstream artifacts (C/D/E/F) depend on. Implementation target (Python 3.10+ stdlib only):

```python
# core_02/anchors_resolver.py — proposed (Phase C → Artifact I → Phase C/Code)
***REMOVED***
***REMOVED***
from typing import Optional, Dict

ANCHOR_RE = {
    "entity":      re.compile(r"@entity\s+([a-z***REMOVED***[a-z0-9_***REMOVED****(\.[a-z***REMOVED***[a-z0-9_***REMOVED****)+)"),
    "component":   re.compile(r"@component\s+([a-z***REMOVED***[a-z0-9_***REMOVED****(\.[a-z***REMOVED***[a-z0-9_***REMOVED****)*)"),
    "module":      re.compile(r"@module\s+([a-z***REMOVED***[a-z0-9_***REMOVED****(\.[a-z***REMOVED***[a-z0-9_***REMOVED****)+)"),
    "symbol":      re.compile(r"@symbol\s+([A-Z***REMOVED***[A-Za-z0-9_***REMOVED***+\.[a-z_***REMOVED***[A-Za-z0-9_***REMOVED****)"),
    "contract":    re.compile(r"@contract\s+([a-z***REMOVED***[a-z0-9_***REMOVED****(\.[a-z***REMOVED***[a-z0-9_***REMOVED****)+)"),
    "event":       re.compile(r"@event\s+([a-z***REMOVED***[a-z0-9_***REMOVED****(\.[a-z***REMOVED***[a-z0-9_***REMOVED****)+)"),
    "storage":     re.compile(r"@storage\s+([a-z***REMOVED***[a-z0-9_***REMOVED***+(_[a-z***REMOVED***[a-z0-9_***REMOVED****)*)"),
    "test":        re.compile(r"@test\s+(test_[a-z***REMOVED***[a-z0-9_***REMOVED****)(\.[A-Za-z_***REMOVED***[\w***REMOVED****)?"),
    "decision":    re.compile(r"@decision\s+(ADR_\d{3***REMOVED***)"),
    "requirement": re.compile(r"@requirement\s+(REQ-[A-Z***REMOVED***[A-Z_***REMOVED****-\d{2***REMOVED***)"),
    "scenario":    re.compile(r"@scenario\s+([a-z***REMOVED***[a-z0-9_***REMOVED****(\.[a-z***REMOVED***[a-z0-9_***REMOVED****)*)"),
    "factory":     re.compile(r"@factory\s+([a-z***REMOVED***[a-z0-9_***REMOVED****_factory)"),
    "forge":       re.compile(r"@forge\s+((forge_[a-z***REMOVED***[a-z0-9_***REMOVED****))"),
    "opportunity": re.compile(r"@opportunity\s+(opp-[a-z0-9***REMOVED***+)"),
    "whim":        re.compile(r"@whim\s+(whim-[a-z0-9***REMOVED***+)"),
    "lesson":      re.compile(r"@lesson\s+((CON|ANTI|CAN|R)[-_***REMOVED***\d{2,3***REMOVED***[a-z***REMOVED***?)"),
    "doc":         re.compile(r"(doc\.[a-z***REMOVED***[a-z0-9_***REMOVED****\.?[a-z0-9_***REMOVED****#[\w\.-***REMOVED***+)"),
***REMOVED***

def resolve_anchor(text: str, env: Optional[Dict***REMOVED*** = None) -> dict:
    """
    Returns: {
        "raw": "@entity forge.facade",
        "namespace": "entity",
        "value": "forge.facade",
        "resolved": True/False,   # whether target exists in env
        "status": "CURRENT|DESIGN_ONLY|UNVERIFIED",  # default UNVERIFIED if not resolved
        "evidence": "core_02/forge_facade.py:ForgeFacade"  # file:symbol or None
    ***REMOVED***
    """
    for ns, regex in ANCHOR_RE.items():
        m = regex.search(text)
        if m:
            value = m.group(1)
            return {"raw": text.strip(), "namespace": ns, "value": value,
                    "resolved": ..., "status": ..., "evidence": ...***REMOVED***
    return {"raw": text.strip(), "namespace": None, "resolved": False,
            "status": "UNVERIFIED", "evidence": None***REMOVED***
```

**Resolution targets per namespace:**

| Namespace     | Resolution mechanism                                                                  |
|---------------|----------------------------------------------------------------------------------------|
| `@entity`     | `core_02/anchors_indexer.py` lookup against Artifact A `PLATFORM_CODE_MAP_V1.md` table. |
| `@component`  | Search `@entity <parent>` Artifact A row → "M1-M5 subcomponents" mentioned for `forge.facade`. |
| `@module`     | `Path("scripts_01/<name>.py").exists()`; fallback `Path("core_02/<name>.py").exists()`.    |
| `@symbol`     | `importlib` static-parse: `ast.parse(file).body` walk ClassDef → FuncDef → match `<ClassName>.<method>`. |
| `@contract`   | (Phase D) Lookup against `CONTRACT_REGISTRY.md` (Artifact C).                            |
| `@event`      | `scripts_01/event_bus.py::registered_events` table by @event_id substring.              |
| `@storage`    | `Path("data_13/<name>.yaml").exists()` or in-memory store.                              |
| `@test`       | `Path("tests_09/test_<name>.py").exists()` (or test_<name>.<func> exists).              |
| `@decision`   | `Path("docs_10/engineering-memory/decisions/ADR_<NNN>_*.md").exists()`.                  |
| `@requirement` | `Path("docs_10/decisions/REQ_REGISTRY_V1.md").exists()` + grep (planned).               |
| `@scenario`   | `Path("runtime_05/scenarios/<name>.yaml").exists()` (planned).                           |
| `@factory`    | (Phase 1.3) Static enum check against 4 canonical factories: `architecture_factory`, `code_factory`, `research_factory`, `content_factory` (per `FACTORY_FORGE_ARCHITECTURE_V1 §3`). |
| `@forge`      | Static enum check against 6 canonical forges per RFC_BUFFY_FORGE_V1 §3: `forge_idea`, `forge_knowledge`, `forge_architecture`, `forge_implementation`, `forge_validation`, `forge_evolution`. |
| `@requirement` | Static map from `docs_10/core/PROJECT_REQUIREMENTS.md` + workspace.py fields (e.g., `project.runnability`, `project.steps`); lowercase.dot enumeration. |
| `@opportunity`| `data_13/opportunities.yaml::ops_store.get(<id>)` → Optional[Opportunity***REMOVED***.               |
| `@whim`       | `data_13/whims.yaml::whim_store.get(<id>)` → Optional[Whim***REMOVED***.                            |
| `@lesson`     | Static grep in `core_02/LESSONS.md` for `@lesson (CON|ANTI|CAN|R)[-_***REMOVED***\d{2,3***REMOVED***` row match; `LESSON` status by default; 4 subtypes (CON/ANTI/CAN/R) distinguish semantic intent but share lifecycle state. Status UNVERIFIED if no matching row in LESSONS.md. |
| `doc.*`       | Lookup against Artifact B `DOCUMENTATION_CODE_MAP_V1.md` provenance table.              |

---

## §I.4 — Anchor usage rules

### Inline-text vs table-form

| Form | Use case                                | Example                                                    |
|------|-----------------------------------------|------------------------------------------------------------|
| Inline | Reading prose; becomes `(`@entity X`)` or `` `@entity X` `` | "The `forge.facade` runs the chain via `run_chain()` (see `forge.execution` contract and `forge.chain_started` event)." |
| Table | Map rows / cells / status columns        | \| doc.arch_canon#3.c1 \| FACT \| `@entity event.bus` \| CURRENT \| |

**Density rule:** 1–3 anchors per paragraph (or per row in a table). NOT 30. Corresponds to 4.md §6 "Один смысловой блок должен иметь минимально необходимый набор anchors."

**Syntax discipline:** Inline anchors MUST be wrapped in parens or backticks so `re.search` can extract them. Bare text ("the forge facade runs ...") is invalid for AnchorResolver.

**Cross-references:**
- `(@entity X)` resolves to Artifact A row.
- `(doc.<name>#<section>.cN)` resolves to Artifact B claim.
- `(@forge X)` resolves to static `RFC_BUFFY_FORGE_V1 §2` engine list.

### Anti-patterns

| Anti-pattern                                                        | Why wrong                                              |
|---------------------------------------------------------------------|--------------------------------------------------------|
| `ForgeFacade.run_chain` (bare class.method)                         | Needs `@symbol` prefix.                                |
| `@entity scenario_registry.py`                                     | 25 entries explicitly resolve to Artifact A lowercase.dot format. |
| `@entity forge-facade` (hyphen)                                     | Hyphen forbidden; use dot.                              |
| `@entity forge.facade:ForgeFacade` (mixed symbol)                   | One anchor = one dimension; combine via 2 anchors.      |
| `@forge.facade#M1` (no namespace)                                   | Each anchor has @namespace prefix — the only exception is `doc.<name>#<section>[.cN***REMOVED***` (Document claim anchor). |
| `@entity forge.facade ; @module forge.cli` (semicolon-separated)    | Use space-separated; semicolon-reserved for status ind.  |

---

## §I.5 — Status taxonomy integration

Every resolved anchor inherits the status of its target. Status taxonomy (per Artifact A §A.6 + Artifact B §B.7):

| Status         | Meaning                                                          | Example scenario                                          |
|----------------|------------------------------------------------------------------|------------------------------------------------------------|
| `CURRENT`      | Anchor resolves; target exists in codebase + tests green.       | `@entity forge.facade` → `✅ implemented (29 tests)`       |
| `PARTIAL`      | Anchor resolves; target exists but coverage incomplete.         | `@entity forge.interactive` → runtime-deployed, no unit tests. |
| `DESIGN_ONLY`  | Anchor resolves; target planned but not yet implemented.         | `@entity factory.registry` → `@module core_02/factory_registry.py` (active v5.188.2). |
| `UNVERIFIED`   | Anchor cannot resolve in current repo / registry.                | `@forge forge_unknown` → static catalog miss → UNVERIFIED.        |
| `STALE`        | Anchor resolved historically but evidence/policy changed.        | (Artifact A row marked STALE on codebase drift.)          |
| `SUPERSEDED`   | Anchor was resolved; now a newer evidence supersedes it.          | `@decision ADR_001` → `@decision ADR_007` (newer).        |

**Default:** if AnchorResolver fails for ANY reason, status = `UNVERIFIED`. Anti-hallucination: never silently fall-through to `CURRENT`.

---

## §I.6 — Cross-Artifact Compatibility

### Artifact A integration

Every `@entity` anchor in artifacts downstream MUST exactly match a row in `PLATFORM_CODE_MAP_V1.md` (`ENTITY_ID` column). The 25 confirmed entities:

```
@entity scenario.registry
@entity forge.registry
@entity missing.registry
@entity orchestrator.blueprint
@entity forge.facade
@entity role.validator
@entity forge.pipeline
@entity workspace.core
@entity wizard.lib
@entity memory.store
@entity knowledge.engine
@entity graph.index
@entity event.bus
@entity remote.sync
@entity forge.cli
@entity forge.api
@entity forge.interactive
@entity opportunity.engine
@entity whim.capture
@entity consistency.check
@entity drift.check
@entity research.web           (DESIGN_ONLY but registered per FACTORY_FORGE §20 row #6)
@entity lisa.estimator          (DESIGN_ONLY but registered per FACTORY_FORGE §20 row #7)
@entity factory.registry        (DESIGN_ONLY — Phase 1.3 implementation pending)
@entity scenario.engine         (DESIGN_ONLY — Phase 2 implementation pending)
```

### Artifact B integration

Documentation claim anchors (`doc.<short_name>#<section>[.cN***REMOVED***`) MUST map to Artifact B `DOCUMENTATION_CODE_MAP_V1.md` provenance table:

| doc anchor                          | Mapped @entity (per §B provenance)        |
|--------------------------------------|-------------------------------------------|
| `doc.arch_canon#3.c1`               | `@entity event.bus`, `@entity memory.store` |
| `doc.ffa#20.c4`                     | `@entity opportunity.engine`               |
| `doc.ffa#20.c5`                     | `@entity whim.capture`                     |
| `doc.ifc#H.c1`                      | `@entity whim.capture`, `@entity opportunity.engine`, `@entity factory.registry` |
| `doc.lifecycle#5.c1`                | `@entity missing.registry`                 |
| `doc.sed#17.1.c1`                   | `@entity whim.capture`                     |
| `doc.forensics#J.c1`                | All `@entity` chain (vertical slice)        |

### Downstream artifacts C/D/E/F/G/H/J/K/L

These artifacts are explicit consumers of this spec:

| Artifact | Inputs from this spec                            | Output                                    |
|----------|--------------------------------------------------|-------------------------------------------|
| C `CONTRACT_REGISTRY_V1`     | `@contract X` anchors from `@entity` rows              | Per-entity contract schema (consumer/producer/input/output) |
| D `ARCHITECTURE_DECISION_REGISTRY_V1` | `@decision ADR_NNN` anchors                  | Per-decision statement + reason + status  |
| E `TRACEABILITY_GRAPH_V1`    | ALL 19 namespace anchors as nodes           | Edge list (DOCUMENTS, IMPLEMENTS, CALLS, DEPENDS_ON, EMITS, CONSUMES, STORES, VALIDATED_BY, DEFINED_BY, DESCRIBES, CONTRADICTS, SUPERSEDES, DERIVED_FROM, USES, PRODUCES) |

**Note (added Phase 1.5):** Traceability Graph E also consumes `@lesson` anchors as constraint nodes — `(@lesson CON_NNN)` enforces `USES` edges in graph; `(@lesson ANTI_NNN)` enforces `CONTRADICTS` edges; `(@lesson CAN_NNN)` enforces allowed/denied design wedges; `(@lesson R_NNN)` enforces hard rule edges.
| F `AGENT_NAVIGATION_MAP_V1`  | `@entity` + `@module` + `@contract`              | "How do I run X?" query/return pairs       |
| G `ARCHITECTURE_GAP_MAP_V1`  | `@entity` + status                                | Gap identification (DESIGN_ONLY not yet implemented) |
| H `DOCUMENTATION_CONSISTENCY_REPORT_V1` | `doc.*` + `@entity` mappings              | Classification per claim (CONFIRMED / PARTIAL / DOC_ONLY / CODE_ONLY / CONTRADICTED / STALE / UNKNOWN) |
| J `CODE_DOCUMENTATION_SYNC_SPEC_V1`    | This entire spec (the spec of the spec)   | Operational CI rules                      |
| K `AI_REPOSITORY_NAVIGATION_SPEC_V1`    | This entire spec + Layers 1/2/3 (per 4.md §14)  | Vector+graph integration plan             |
| L `IMPLEMENTATION_PLAN_V1`   | Gap from G + Drift from H                         | Phased implementation roadmap (A-H correspondence to §20 of 4.md) |

---

## §I.7 — AnchorResolver anti-hallucination diagnostics

**High-risk drift namespaces (top 5):**

1. **`@symbol`** — could refer to renames; codebase grep is the only resolution. Mitigation: re-grep every consistency-check run; mark `@symbol StaleClass.old_method` → STALE if class absent.
2. **`@contract`** — interface may change without YAML update; mitigation: Artifact C registry must be CHANGELOG-linked.
3. **`@event`** — pub/sub event publish/subscribe drift; mitigation: `event_bus.py` registered_events table cross-check.
4. **`@scenario`** — runtime_05/scenarios/*.yaml drift; mitigation: dir-listing + YAML parse.
5. **`@requirement`** — REQ-XYZ-NN slugs may be invented; mitigation: REQ_REGISTRY_V1 must be the canonical list.

**Mitigation strategy — 4.md §17 live-documentation discipline:**

> "Если symbol исчез — STALE. Если implementation изменился — REVIEW_REQUIRED. Если документ противоречит коду — CONTRADICTION."

**CI integration (planned):** `core_02/anchors_resolver.py` will be hooked into `consistency_check.py::check_drift` (or new `check_anchors`). Plan:

- Stage A: parse all `.md` files in `docs_10/`, `runtime_05/`, `CHANGELOG.md` → extract anchors → resolve → emit report.
- Stage B: cross-reference with Artifact A table + filesystem → flag UNVERIFIED/STALE.
- Stage C: output `ANCHOR_DIFF_REPORT.md` (gitignored) with per-anchor resolution status.

---

## §I.8 — Examples (worked)

**Example 1 — Inline inline-text multi-anchor sentence (CORRECT):**

```
The forge facade (@entity forge.facade) runs the chain via (@symbol forge.facade.run_chain)
producing (@event forge.chain_started). Persistence is in (@storage opportunities_yaml)
(@storage whims_yaml) and validated by (@test test_forge_facade) per (@contract forge.execution).
```

This contains 6 anchors, all resolvable in Artifact A/Artifact I. AnchorResolver return: 6 × `CURRENT`. Each token wrapped in (`...`) per §I.4 syntax discipline.

**Example 2 — Table-row (CORRECT per Artifact B §B.7 format):**

| doc anchor                  | claim                                            | type   | entities                                  | status      |
|-----------------------------|--------------------------------------------------|--------|-------------------------------------------|-------------|
| `doc.ffa#20.c4`             | opportunity_engine → implemented (v5.187.7)      | FACT   | `@entity opportunity.engine`              | CURRENT     |
| `doc.ffa#20.c5`             | whim_capture → implemented (v5.187.8)            | FACT   | `@entity whim.capture`                    | CURRENT     |
| `doc.ffa#20.c7`             | whims_yaml → implemented (v5.187.8)              | FACT   | `@entity whim.capture`                    | CURRENT     |

**Example 3 — Counter-example (WRONG — anti-pattern):**

```
forge.facade executes the chain via @symbol ForgeFacade.run_chain producing forge.chain_started.
opportunities_yaml is the persistence unit.
```

Issues:
- Bare `forge.facade` (no `@entity` paren wrap) → not extractable.
- `@symbol ForgeFacade.run_chain` uses bare class.method without class disambiguation; should be `@symbol ForgeFacade.run_chain` (works actually) but interspersed with no `@` on other terms.
- `forge.chain_started` lacks `@event` prefix.
- `opportunities_yaml` bare → no `@storage` prefix.
- Mixed inline + table style in same context — not consistent.

Corrected:
```
(@entity forge.facade) executes the chain via (@symbol ForgeFacade.run_chain) producing (@event forge.chain_started).
(@storage opportunities_yaml) is the persistence unit.
```

---

## §I.9 — Self-state

- **Status of this spec itself:** `CURRENT` (this is the first slice; revised by Phase C+ as gaps emerge).
- **Cross-cutting dependencies:**
  - Phase C/D/E/F/G/H — must read this spec for namespace conformance.
  - Phase I (`@forge forge_X`) — only valid after `RFC_BUFFY_FORGE_V1 §2` ships (already done for 6 forges).
  - `@requirement REQ-XYZ-NN` — not yet available; placeholder until REQ_REGISTRY_V1 exists (planned Phase 1.4).
- **Self-deltas expected:**
  - After Phase 1.3 (factory_registry implementation) — `@entity factory.registry` → `CURRENT`.
  - After Phase 2 (scenario_engine implementation) — `@entity scenario.engine` → `CURRENT`.
  - After REQ_REGISTRY_V1 (§I.6) — `@requirement` anchors become resolvable.
  - **Phase 1.5 (already applied per §F.7 follow-up):** Artifact I extended 15 → 19 namespaces via `@lesson CON/ANTI/CAN/R` (4 subtypes). Resolution: static grep `core_02/LESSONS.md`. Status taxonomy: `LESSON` (mirrors `@decision`'s PROPOSED/ACCEPTED/SUPERSEDED states). Affected: §I.1 rows 16–19, §I.2 regex (`@lesson` line), §I.3 ANCHOR_RE pseudocode (added `lesson` key) + resolution target row, §I.6 row (E consumes all 19 namespaces), this self-state log, and the footer line. 126 lessons in `LESSONS.md` (CON: 80, ANTI: 12, CAN: 34, R: 0 at v0.1 sweep).
- **Known limitations (this spec):**
  - `@requirement` resolver is not implemented (planned).
  - `@scenario` resolver requires runtime_05/scenarios/ to exist (planned Phase 2).
  - `@factory` resolver requires Phase 1.3 factory_registry.
  - Cross-artifact resolver (Artifact E graph traversal) requires Artifact E to exist (planned Phase D).

---

_Phase C + 1.5-Phase extension closed. Implementation: 2026-08-12. Namespace count: 15 → 19 (added `@lesson CON/ANTI/CAN/R` per `ARCHITECTURE_DECISION_REGISTRY_V1.md §D.5` follow-up). Next: Phase D → Artifact C (CONTRACT_REGISTRY_V1.md) and Artifact D (ARCHITECTURE_DECISION_REGISTRY_V1.md) — both consume this 19-anchor namespace spec. After those, Phase E → Artifact E (TRACEABILITY_GRAPH_V1.md) which materializes the graph from all anchor types (now 19 nodes including 4 @lesson subtypes)._
