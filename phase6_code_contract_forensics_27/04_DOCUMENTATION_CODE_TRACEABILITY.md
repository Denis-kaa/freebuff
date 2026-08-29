# 04_DOCUMENTATION_CODE_TRACEABILITY — Связь документации и кода

> **Промт:** `pompts_11/087_19_phase6_code_contract_forensics.md` §3 (ИССЛЕДОВАНИЕ ДОКУМЕНТАЦИИ) + §6
> **Метод:** для каждого архитектурного утверждения — document + section + code evidence.

---

## 1. Канонические архитектурные документы (57 в engineering-memory)

| Документ | Роль | Ключевые секции |
|----------|------|-----------------|
| `FACTORY_FORGE_ARCHITECTURE_V1.md` | карта Factory/Forge v1.1 | §3 Factory, §5 Forge, §12 Content Factory, §15 Production Flow, §20 Missing Capabilities (20 rows), §21 Recommended Architecture |
| `WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md` | системное исследование v3.2 | §7 Scenario, §8 Factory, §15 Long-lived Project, §17/§21 gaps, §31.5 Definition, §32 границы B1-B14 |
| `PLATFORM_CODE_MAP_V1.md` | Artifact A — инвентарь кода | §A.1-A.5 (25 @entity), §A.6 provenance table |
| `SCENARIO_ENGINE_DESIGN_V1.md` | дизайн Scenario Engine | §3.1 ScenarioRegistry, §7-§9 оркестратор+resume, §11 эволюция |
| `CONTRACT_REGISTRY_V1.md` | Artifact C — 16 контрактов | §C.4 #1-#16, §C.6 drift |
| `INTELLIGENCE_FACTORY_CONTRACT_V1.md` | Intelligence↔Factory контракт | §E Opportunity, §F Scenario, §G Factory, §H Execution, §K Provenance, §M Vertical Slice |
| `FORENSICS_CI_REPORT_V1.md` | платформенная форензика (промт 1) | G0-G4, WHIM/OPPORTUNITY ABSENT (было) |
| `FORENSICS_CI_GAP_MAP_V1.md` | gap-карта CI | G-LL-1, G-CFO-1..5 |
| `RFC_BUFFY_FORGE_V1.md` | Forge-принципы | §2, §7.3, §12 |
| `RFC_DECISION_INTELLIGENCE_SYSTEM_V1.md` | Decision Intelligence | §4 ARE/CAE/TDA/Policy |
| `RFC_ORGANIZATIONAL_MEMORY_ENGINE_V1_EVOLUTION.md` | OME v1.1 | I-1..I-12 |
| `P3_IDEA_EXPLORER_RUN_FORGE_FACADE.md` | Idea Explorer v2.0 | CORE LOOP, BRANCH GENERATION |
| `TRACEABILITY_GRAPH_V1.md` | Artifact E | §E.1 nodes, §E.5 edges |
| `SEMANTIC_ANCHOR_SPEC_V1.md` | Artifact I | §I.1-I.6 (19 namespaces) |
| `AGENT_NAVIGATION_MAP_V1.md` | Artifact F | §F.1 capabilities |
| `ARCHITECTURE_DECISION_REGISTRY_V1.md` | Artifact D | ADR-NNN + lessons |

## 2. Документация, которая УЖЕ подтверждена кодом (из предыдущих пакетов)

- `intelligence_forensics_25/` — GAP-4/GAP-5 CLOSED (контракты Opportunity §E / Whim §17.1 зарегистрированы в CONTRACT_REGISTRY_V1 #15/#16).
- `phase5_intelligence_loop_26/` — GAP-1 (real DISCOVER) + GAP-2 (ACCUMULATE) реализованы в opportunity_engine.
- `phase4_evaluation_24/` — R-1 (degraded→FAILED) закрыт v5.189.10.

## 3. Расхождения документация ↔ код (обновлённые для Phase 6)

| Документ/секция | Утверждение | Код | Статус |
|---|---|---|---|
| INTELLIGENCE_FACTORY_CONTRACT §E | `provenance: str` | `opportunity_engine.py:146` `provenance: Dict[str, Any***REMOVED***` | ⚠️ CONFLICT → **исправлено v5.189.22** (`dict[str, Any***REMOVED***` + rank-поля) |
| INTELLIGENCE_FACTORY_CONTRACT §E | 15/16 полей design (signal/hypothesis/rationale) | 24-полевой dataclass (title/roles/artifacts) | ⚠️ CONFLICT (зафиксирован §C.6 drift #5, не закрыт) |
| FACTORY_FORGE §20 row #10 | opportunities_yaml «16 полей» | 24 поля фактически | ⚠️ CONFLICT (тот же drift) |
| SCENARIO_ENGINE_DESIGN §7-§9 | Scenario Engine оркестратор + resume | нет кода, только ScenarioRegistry | ⚠️ DOCUMENTED_ONLY |
| CONTRACT_REGISTRY §C.4 #12 | opportunity.execute emits `opportunity.*` events | НЕ публикует (planned §J) | ⚠️ DOCUMENTED_ONLY (см. 06) |
| FORENSICS_CI_REPORT | WHIM/OPPORTUNITY ABSENT | теперь реализованы (v5.187.7/8 + v5.189.16) | ✅ RESOLVED (исторический документ) |
| WORKSPACE_OS_RESEARCH §15 | Project registry (project.yaml) отсутствует | `workspace_registry.py` SQLite + forge_registry.yaml | ⚠️ PARTIAL (реестр есть, project.yaml-шаблона нет) |

## 4. Документация, не имеющая кода (DOCUMENTED_ONLY — полный список)

1. **Scenario Engine** (оркестратор) — `scenario_engine` design_ready в missing_registry.
2. **Content Intelligence** (отдельный content-specific слой) — только концепты `content_factory/concept*.md`; generic реализован как opportunity_engine.
3. **Concept Evolution** (C-A/C-B/C-C, Evolution Memory, Concept Genome, Population, Species, Operator, Fitness, Generation, Lineage, Experiment, Strategy, Hypothesis, Evidence) — только RFC_ORG_MEMORY_EVOLUTION + P3_IDEA_EXPLORER + 09_FUTURE_GAPS; **grep 0 в коде**.
4. **Decision Intelligence System** (ARE/CAE/TDA/Policy Checker) — RFC_DECISION_INTELLIGENCE_SYSTEM_V1.md; **grep 0 в коде** (частично покрыт `consistency_check.py`/`drift_check.py` как приближения).
5. **Scheduler** — не описан и не реализован (MISSING).
6. **Agent Runtime** — distributed_agents.py есть, но это исполнители, не планировщик.

---

_Конец 04_DOCUMENTATION_CODE_TRACEABILITY. Переход к 05_CONTRACT_FORENSICS._
