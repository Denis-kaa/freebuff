# PHASE8_REALITY_MAP.md — Current Reality Map (Universal Scenario Intelligence)

> Phase 8 (promt 91) §14. Repository-first forensics: только фактические
> API/symbols из кода. Дата: 2026-08-17 · Версия платформы: v5.189.24+.

## 1. Reality map — Component | Path | Symbol | Current Behavior | Reusable | Gap

> ⚠️ Temporal note: таблица фиксирует текущее состояние на момент forensics
> (реализация Phase 8 уже частично начата: `scenario_intelligence` создан,
> `propose()` делегирует с BC-fallback). Секции 2–5 описывают ПРЕ-реализационные
> пути (baseline), чтобы показать, что именно Phase 8 меняет.

| Component | Path | Symbol | Current Behavior | Reusable | Gap |
|-----------|------|--------|------------------|----------|-----|
| Scenario Registry | `core_02/scenario_registry.py` | `ScenarioRegistry` · `list_scenarios()` · `get()` · `filter()` · `find_role()` · `all_roles()` · `propose_roles(query, top_n=3)` · `validate_all()` · `warnings()` | Авто-дискавери `runtime_05/scenarios/*.yaml`; dispatch по `scenario_type` (`_SCENARIO_TYPES`); fuzzy-match `propose_roles` → `[(Scenario, Role, score)***REMOVED***`; fail-safe (пустой реестр → [***REMOVED***) | ✅ **каталог для discovery** | G1: нет domain-neutral ранжирования кандидатов (score = keyword overlap) |
| Scenario ABC | `core_02/scenario.py` | `Scenario` (ABC) · `Role` (frozen dataclass: scenario_id/role_id/title/role_type/file/routing_hint/extra) · `ScenarioManifest` (scenario_id/scenario_type/display_name/root/enabled/capabilities/metadata) | Универсальная абстракция: любой сценарий = источник ролей; `routing_hint` = capability-строки; `capabilities` = scenario-level токены | ✅ **универсален как есть** | G0: сущности уже domain-neutral |
| Factory Registry | `core_02/factory_registry.py` | `FactoryRegistry` · `get_factory()` · `factory_capabilities()` · `find_factories_by_capability()` · `select_forge(capability, prefer_status)` · `capability_catalog()` · `validate_all()` | capability-каталог (union factory.yaml + forge passports); status-priority селекция (production>material>design); детерминированный tie-break | ✅ **capability resolution готов** | G0: `select_forge` уже domain-neutral |
| Factory Passport | `core_02/factory_passport.py` | `FactoryPassport` (factory_id/display_name/version/status/description/capabilities/metadata) | Типизированный паспорт factory.yaml; ANTI-6b vocab guard | ✅ | G0 |
| Forge Passport | `core_02/forge_passport.py` | `ForgePassport` (forge_id/factory_id/version/status/display_name/capabilities/metadata/mission/inputs/production_workflow/engines/quality_gates/outputs/artifacts/interfaces/memory/knowledge) | Полный паспорт кузни | ✅ | G0 |
| Opportunity Engine | `scripts_01/opportunity_engine.py` | `Opportunity` (24f) · `OpportunityStore` · `advance()` · `discover_candidates()` · `propose()` · `execute()` · `accumulate()` · `rank_candidates()` | Phase 7: Opportunity → Factory → ForgeFacade; lifecycle FSM; EventBus events. **Baseline:** `propose()` = ScenarioRegistry.propose_roles → первый кандидат (топ-1, без evaluation/ranking). **Phase 8:** делегирует в ScenarioIntelligence (BC-fallback) | ✅ | G1: baseline брал топ-1 без evaluation/ranking — закрывается делегированием |
| Forge Facade | `core_02/forge_facade.py` | `ForgeFacade` · `run_chain(project, role_ids)` · `initiate_forge()` · `PIPELINE_CHAIN` (14 ролей) · `RoleArtifactValidator` · `ChainRun` | Единственный sanctioned execution bridge (§7.3); overall ok/partial/failed/degraded | ✅ **execution boundary** | G0 |
| Memory Store | `core_02/memory_store.py` | `MemoryStore` · `store_knowledge()` · `query_by_type(kind)` · `record_learning_event()` · `update_feedback()` · `find_related()` | SQLite knowledge objects + learning events; kind-модель (candidate/opportunity/…) | ✅ **feedback/history storage** | G0 |
| Semantic Layer | `core_02/semantic_layer.py` | `SemanticLayer` · `semantic_search()` · `search_related()` · `find_similar_patterns()` | TF-IDF/semantic поиск по knowledge | ✅ (опционально для evaluation) | G0 |
| Learning Loop | `core_02/learning_loop.py` | `LearningLoop` · `record_feedback()` · `capture()` · `analyze/formalize/codify` | Уроки CON/CAN/ANTI + feedback → confidence | ✅ **feedback v0** | G0 |
| Event Bus | `scripts_01/event_bus.py` | `EventBus` · `publish(Event)` · `get_events()` · `get_default_event_bus()` · `Event(type, source, data)` | SQLite event log; canonical schema; Phase 7 события (execution.*, opportunity.*, scenario.selected, whim.*) | ✅ | G1: нет `scenario.candidates.generated` / `scenario.evaluated` / `scenario.reselected` |
| Graph Index | `scripts_01/graph_index.py` | `GraphIndex` · `add_node/add_edge/get_related` | Граф знаний | ✅ (опционально) | G0 |
| Workspace / Project | `core_02/workspace.py` | `Project.load()` · `Workspace` | Project-объект для run_chain | ✅ | G0 |
| Scenario manifests | `runtime_05/scenarios/` | `blueprint_v3.yaml` (enabled, capabilities) · `vkusvill_demo.yaml` (unknown scenario_type 'teamwork' — warning) | 2 манифеста; auto-discovery | ✅ | G3: только 1 сценарий успешно инстанцируется (blueprint_v3) |
| Factory manifests | `runtime_05/factories/architecture/` | `factory.yaml` (capabilities: architecture/review/validate/report/explain) · `governance.yaml` (validate/report/explain) · `review.yaml` | 1 фабрика + 2 кузни; capability-каталог; **закрытый словарь**: все capabilities ⊆ `KNOWN_CAPABILITIES` (ANTI-6b — иначе select_forge не резолвит) | ✅ | G0 |
| Missing Registry | `core_02/missing_registry.py` | `MissingRegistry` (register/mark-prompt-written/mark-implemented/list_all/check) | 21 записей; `scenario_engine` = design_ready; `scenario_intelligence` = prompt_written (зарегистрирован) | ✅ | G2: `scenario_engine` design-ready, не реализован |
| Phase 7 package | `phase7_evaluation_28/` | 13 файлов (reports/json/manifest/next-phase) | Contract reconciliation + factory/event closure; traceability 19/20 CONFIRMED | ✅ baseline | G0 |

## 2. Current scenario discovery (фактическое)

```
opportunity_engine.propose(opp)                    [scripts_01/opportunity_engine.py***REMOVED***
  → ScenarioRegistry.propose_roles(opp.title + " " + opp.description, top_n=3)
      [core_02/scenario_registry.py — fuzzy keyword overlap***REMOVED***
  → proposals[0***REMOVED*** → opp.scenario = {scenario_id, role_id, score, title***REMOVED***
  → opp.roles = ForgeFacade.PIPELINE_CHAIN (probe)
  → event scenario.selected (Phase 7)
```

**Ограничения:** топ-1 без объяснений (reasons/evidence нет); score = keyword overlap (не композитный); нет evaluation (capability availability / history / feasibility); нет нескольких ранжированных кандидатов с причинами; нет capability resolution до Factory.

## 3. Current scenario selection

- Только **один** сценарий (top-1 от `propose_roles`).
- Нет lifecycle выбора (selected/deferred/superseded/unavailable) — вне Opportunity FSM.
- Нет re-selection после нового evidence.

## 4. Current factory routing

```
opportunity_engine.execute(opp)                    [Phase 7, GAP A closed***REMOVED***
  → _derive_capability(opp)   (provenance.capability → scenario.capability → None)
  → _select_factory_forge(opp)  → FactoryRegistry.select_forge(capability)
  → provenance['factory_selection'***REMOVED*** = {factory_id, forge_id, capability***REMOVED*** | {fallback***REMOVED***
  → ForgeFacade().run_chain(project, role_ids)   [EXECUTION BOUNDARY***REMOVED***
```

**Готово:** Opportunity → Factory → Forge доказан (Phase 7). **Недостаёт:** сценарий → capability (ScenarioIntelligence должен резолвить capability из выбранного сценария — сейчас `_derive_capability` берёт из scenario.capability, но `propose()` его не заполняет).

## 5. Current feedback path

```
execute() → _accumulate_best_effort() → accumulate()
  → MemoryStore.store_knowledge(kind="candidate", tags=["opportunity", ...***REMOVED***)
  → MemoryStore.record_learning_event()
  → LearningLoop.record_feedback()
```

**Готово:** artifact → memory/learning (Phase 5, promt 085). **Недостаёт:** scenario-уровневый feedback (outcome выбранного сценария → будущий ranking) — kind=scenario_decision не существует.

## 6. Итог (что Phase 8 переиспользует vs строит)

| Переиспользует (G0) | Строит (G1–G3) |
|---------------------|-----------------|
| ScenarioRegistry (каталог) | Scenario Intelligence decision layer (discovery→evaluation→ranking→selection) |
| FactoryRegistry.select_forge (capability) | ScenarioCandidate / ScenarioDecision / CapabilityRequirement |
| ForgeFacade.run_chain (execution) | Композитный score (relevance/capability/history/feasibility) |
| MemoryStore/LearningLoop (feedback) | feedback v0 для scenario (kind=scenario_decision) |
| EventBus (canonical) | события scenario.candidates.generated/evaluated/reselected |

---
_Repository verified. Phase 8 forensics complete — см. PHASE8_GAP_MAP.md._
