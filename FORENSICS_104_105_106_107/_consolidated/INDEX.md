# INDEX.md — Кросс-ссылки по 4 forensic-проходам (104/105/106/107)

> Назначение: «где какая тема покрыта» — карта тем → пакеты → файлы.

## Карта тем

| Тема | 104 (arch_forensics_v2) | 105 (repo_org_32) | 106 (system_model_33) | 107 (inventory_34) |
|------|------------------------|-------------------|----------------------|--------------------|
| **Workspace/Project модель** | CURRENT_ARCHITECTURE.md | REPOSITORY_ORGANIZATION_FORENSICS_V1.md | 03_ACTUAL_SYSTEM_MODEL.md | PLATFORM_ARCHITECTURAL_INVENTORY_V1.md §B/F |
| **Workspace ×2 дубль (YAML vs SQLite)** | GAP_MAP.md (косвенно) | — | 14_ARCHITECTURAL_GAPS.md | COMPETING_ABSTRACTIONS.md §1 |
| **Forge (pipeline/registry/facade)** | FACTORY_FORGE_ANALYSIS.md | — | 06_FACTORY_FORGE_SCENARIO_ANALYSIS.md | PLATFORM_ARCHITECTURAL_INVENTORY_V1.md §B/C/I |
| **Factory (manifest/base/registry)** | FACTORY_FORGE_ANALYSIS.md | — | 06_FACTORY_FORGE_SCENARIO_ANALYSIS.md | RESPONSIBILITY_MATRIX.md |
| **Scenario / ScenarioIntelligence** | INTELLIGENCE_ANALYSIS.md | — | 03_ACTUAL_SYSTEM_MODEL.md | PLATFORM_ARCHITECTURAL_INVENTORY_V1.md §C/G |
| **Agent / Model / Role / Runtime** | AGENT_ARCHITECTURE.md | — | 07_AGENT_RUNTIME_SKILL_TOOL_ANALYSIS.md | RESPONSIBILITY_MATRIX.md §E |
| **ROLE ≠ PROJECT ROLE** | AGENT_ARCHITECTURE.md (частично) | — | 07 (частично) | RESPONSIBILITY_MATRIX.md §E ⚠️ |
| **Task / Tool системы ×2** | — | — | 14_ARCHITECTURAL_GAPS.md | COMPETING_ABSTRACTIONS.md §3-4 |
| **Memory/Knowledge ×4** | — | — | 03_ACTUAL_SYSTEM_MODEL.md | COMPETING_ABSTRACTIONS.md §5 |
| **Whim / Opportunity** | — | — | 03_ACTUAL_SYSTEM_MODEL.md | PLATFORM_ARCHITECTURAL_INVENTORY_V1.md §B |
| **Integration / Connector слой** | — | — | 14_ARCHITECTURAL_GAPS.md | PLATFORM_ARCHITECTURAL_INVENTORY_V1.md §L |
| **Security / Trust Boundary** | — | — | 15_MIGRATION_RISK_REGISTER.md | SECURITY_TRUST_BOUNDARY_MAP.md |
| **Competing abstractions** | GAP_MAP.md | — | 14_ARCHITECTURAL_GAPS.md | COMPETING_ABSTRACTIONS.md |
| **Contract graph** | TRACEABILITY_MATRIX.md | — | 13_DEPENDENCY_GRAPH.md | CONTRACT_GRAPH.md |
| **Evidence ledger** | EVIDENCE_LEDGER.md | — | 12_EVIDENCE_LEDGER.md | EVIDENCE_LEDGER.md |
| **Repository structure** | — | REPOSITORY_ORGANIZATION_FORENSICS_V1.md | 08_REPOSITORY_STRUCTURE_AUDIT.md | REPOSITORY_TREE.md |
| **Target architecture** | TARGET_MODEL_MAPPING.md | — | 04_TARGET_SYSTEM_MODEL.md | TARGET_ARCHITECTURE.md |
| **Refactoring roadmap** | FORENSICS_CONSOLIDATED_REPORT.md | — | 10_REFACTORING_ROADMAP.md | TARGET_ARCHITECTURE.md §P0-P4 |
| **Traceability doc↔code↔tests** | TRACEABILITY_MATRIX.md | — | 05_CONCEPT_TRACEABILITY.md | TRACEABILITY_MAP.md |
| **Migration risk register** | — | — | 15_MIGRATION_RISK_REGISTER.md | TARGET_ARCHITECTURE.md §Risks |

## Временная линия (как пакеты строятся друг на друге)

1. **104 (arch_forensics_v2, v5.189.67)** — первый полный архитектурный forensic: слои,
   pipeline-роли stateless, invарианты (privacy, forge integrity, additive only).
2. **105 (repo_org_32, v5.189.68)** — границы Platform vs Project: «концептуальная граница
   есть, физической нет», импорты project→platform, историческая нумерация каталогов.
3. **106 (system_model_33)** — ACTUAL vs TARGET модель системы: полный 17-файловый пакет,
   dependency graph, migration risk register.
4. **107 (inventory_34, v5.189.72)** — полная инвентаризация: responsibility matrix,
   contract graph, security map, опровержение гипотезы `Project→Scenario→Factory→Forge`
   как единого конвейера (Path A REAL vs Path B PARTIAL).
5. **ADR-019 (Agent, v5.189.80)** — Agent base class + lifecycle: `core_02/agent_base.py` (ABC +
   forward-only DAG CREATED→ACTIVE→PAUSED→DONE/FAILED) + 29 hermetic тестов.
6. **ADR-020 (Integration, v5.189.81)** — Integration adapter boundary:
   `core_02/integration_base.py` (AuthSpec + INTENT_CAPABILITY_MAP + call_platform) +
   33 hermetic теста. **Все P1-контракты ЗАКРЫТЫ.**

## Главные кросс-подтверждения

| Утверждение | Подтверждено в |
|-------------|----------------|
| Forge-слой зрел и реален | 104 FACTORY_FORGE_ANALYSIS + 106 06 + 107 §B |
| Workspace модель дублируется ×2 | 107 COMPETING_ABSTRACTIONS §1 + 106 14 |
| `ROLE ≠ PROJECT ROLE` не разделено | 107 RESPONSIBILITY_MATRIX §E + 104 AGENT_ARCHITECTURE |
| Agent-класса нет (stateless pipeline-роли) | 104 AGENT_ARCHITECTURE + 107 §E |
| `Project→Scenario→Factory→Forge` = DOCUMENTED ONLY | 107 CONTRACT_GRAPH (главное опровержение 106) |
| Integration-слоя нет (мосты вшиты) | 107 §L + 106 14 |

## Как пользоваться

- **Хочешь полную картину компонента** → RESPONSIBILITY_MATRIX (107) + EVIDENCE_LEDGER_MERGED.
- **Хочешь границы/контракты** → CONTRACT_GRAPH (107) + 13_DEPENDENCY_GRAPH (106).
- **Хочешь целевое состояние** → TARGET_ARCHITECTURE (107) + 04_TARGET (106) + TARGET_MODEL (104).
