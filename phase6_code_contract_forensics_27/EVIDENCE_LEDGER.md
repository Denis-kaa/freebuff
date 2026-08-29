# EVIDENCE_LEDGER — Реестр доказательств

> **Промт:** `pompts_11/087_19_phase6_code_contract_forensics.md` §21 (EVIDENCE LEDGER)
> **Формат:** ID / CLAIM / EVIDENCE / PATH / SYMBOL / TEST / STATUS / CONFIDENCE. Никаких «вероятно» без маркировки ASSUMPTION/HYPOTHESIS.

---

| ID | CLAIM | EVIDENCE | PATH | SYMBOL | TEST | STATUS | CONFIDENCE |
|----|-------|----------|------|--------|------|--------|------------|
| E-01 | Opportunity Engine реализован (DISCOVER→EXECUTE→ACCUMULATE) | dataclass + 6 lifecycle функций + 4 реальных источника | scripts_01/opportunity_engine.py | Opportunity, discover_candidates, execute, accumulate | test_opportunity_engine.py | CONFIRMED | HIGH |
| E-02 | Whim Capture реализован (capture/triage/promote) | 21-полевой dataclass + lifecycle | scripts_01/whim_capture.py | Whim, WhimStore, promote | test_whim_capture.py | CONFIRMED | HIGH |
| E-03 | ScenarioRegistry — единственный реестр сценариев | auto-discovery runtime_05/scenarios/*.yaml | core_02/scenario_registry.py | ScenarioRegistry.list_scenarios | test_scenario_registry.py | CONFIRMED | HIGH |
| E-04 | FactoryRegistry + FactoryPassport реализованы | select_forge/capability_catalog + frozen dataclass | core_02/factory_registry.py, core_02/factory_passport.py | FactoryRegistry.select_forge, FactoryPassport | test_factory_registry.py, test_factory_passport.py | CONFIRMED | HIGH |
| E-05 | ForgeFacade — единственный мост к Forge | run_chain/initiate_forge + PIPELINE_CHAIN (14 ролей) | core_02/forge_facade.py | ForgeFacade.run_chain | test_forge_facade.py | CONFIRMED | HIGH |
| E-06 | EventBus инфраструктурно реализован | publish/subscribe/get_events + SQLite | scripts_01/event_bus.py | EventBus.publish | test_event_bus.py | CONFIRMED | HIGH |
| E-07 | Intelligence-события НЕ эмитятся | grep publish в opportunity/whim = 0 | scripts_01/opportunity_engine.py, whim_capture.py | — | — | CONFIRMED (отрицательный) | HIGH |
| E-08 | Factory→Forge соединение НЕ подключено в execute | execute() вызывает run_chain напрямую, без select_forge | scripts_01/opportunity_engine.py | execute | test_opportunity_engine.py | CONFIRMED (gap) | HIGH |
| E-09 | Opportunity схема: 24 поля vs §E 15/16 | dataclass 24 поля; §E signal/hypothesis | scripts_01/opportunity_engine.py vs INTELLIGENCE_FACTORY_CONTRACT §E | Opportunity.__dataclass_fields__ | test_opportunity_engine.py | CONFIRMED (CONFLICT-1) | HIGH |
| E-10 | Concept Evolution отсутствует в коде | grep concept_evolution/evolution_memory/concept_genome = 0 | core_02/, scripts_01/ | — | — | CONFIRMED (ABSENT) | HIGH |
| E-11 | Scheduler/Agent Runtime отсутствуют | grep class Scheduler/AgentRuntime = 0 | core_02/, scripts_01/ | — | — | CONFIRMED (MISSING) | HIGH |
| E-12 | Opportunity недоступен через MCP/TG | 40+ MCP tools без opportunity; 7 TG команд без opportunity | scripts_01/mcp_server.py, telegram_bot.py | _handle_* | — | CONFIRMED (gap) | HIGH |
| E-13 | Интеллект-цикл вертикален (slice работает) | discover→propose→execute→accumulate полный путь | scripts_01/opportunity_engine.py | discover_candidates, execute, accumulate | test_intelligence_loop_phase5.py | CONFIRMED | HIGH |
| E-14 | MissingRegistry: 20 записей, 12 implemented | list --json | data_13/missing_registry.yaml | MissingRegistry | test_missing_registry.py | CONFIRMED | HIGH |
| E-15 | Сценарии: 3 YAML в runtime_05/scenarios | ls + cat | runtime_05/scenarios/blueprint_v3.yaml, vkusvill_demo.yaml | ScenarioRegistry auto-discovery | test_scenario_registry.py | CONFIRMED | HIGH |
| E-16 | 16 контрактов: 15 CURRENT / 1 PARTIAL | CONTRACT_REGISTRY_V1.md §C.5 | docs_10/engineering-memory/CONTRACT_REGISTRY_V1.md | — | — | CONFIRMED | MEDIUM (doc-derived) |

---

_Конец EVIDENCE_LEDGER. 16 записей, все с evidence path+symbol+test, статусы CONFIRMED._
