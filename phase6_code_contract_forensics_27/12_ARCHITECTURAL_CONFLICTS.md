# 12_ARCHITECTURAL_CONFLICTS — Архитектурные конфликты

> **Промт:** `pompts_11/087_19_phase6_code_contract_forensics.md` §18 (STOP CONDITIONS) + §6 (CONFLICT)
> **Метод:** каждый конфликт — документация vs код, с evidence. Для каждого — вердикт: DECISION REQUIRED / FIXED / ACCEPTED.

---

## 1. CONFLICT-1: Opportunity схема — §E design (15/16 полей) vs dataclass (24 поля)

- **Документация:** `INTELLIGENCE_FACTORY_CONTRACT_V1.md` §E (signal/hypothesis/rationale/related_knowledge/selected_scenario/resulting_artifact) + `FACTORY_FORGE_ARCHITECTURE_V1.md` §20 #10 («16 полей»).
- **Код:** `scripts_01/opportunity_engine.py::Opportunity` — 24 поля (title/description/roles/artifacts/source_path/evidence_path + lifecycle audit + related_whims + priority).
- **Статус:** зафиксирован в `CONTRACT_REGISTRY_V1.md` §C.6 drift #5 (2026-08-16, GAP-4/GAP-5 closure). НЕ закрыт.
- **Вердикт:** ⚠️ **DECISION REQUIRED** — reconcile §E с implementation ИЛИ пометить §E superseded. Не блокирует runtime (dataclass богаче), но документация вводит в заблуждение.

## 2. CONFLICT-2: Intelligence-доменные события не эмитятся (contract promises, code silent)

- **Документация:** `CONTRACT_REGISTRY_V1.md` #12 `opportunity.execute` produced `[opportunity.proposed/advanced/executed***REMOVED***`; #13 `whim.promote` produced `[whim.captured/classified/promoted/deferred***REMOVED***`; `INTELLIGENCE_FACTORY_CONTRACT_V1.md` §J (11 событий).
- **Код:** grep publish в `opportunity_engine.py` / `whim_capture.py` = 0. EventBus инфраструктурно есть, но эти события не публикуются.
- **Статус:** уже аннотирован в CONTRACT_REGISTRY (§C.6 #5: «NOT yet emitted»). 
- **Вердикт:** ⚠️ **DECISION REQUIRED (low effort)** — аддитивный emit в `advance()` закрывает §J + contracts #12/#13. Кандидат в следующий slice.

## 3. CONFLICT-3: Factory→Forge соединение не подключено в цикле

- **Документация:** `FACTORY_FORGE_ARCHITECTURE_V1.md` §15 Production Flow + §21 (Scenario → Factory → Forge); `INTELLIGENCE_FACTORY_CONTRACT_V1.md` §H.
- **Код:** `FactoryRegistry.select_forge()` реализован (v5.189.21), но `opportunity_engine.execute()` вызывает `ForgeFacade.run_chain` **напрямую**, минуя select_forge.
- **Вердикт:** ⚠️ **PARTIAL / DECISION REQUIRED** — либо подключить select_forge в execute (аддитивно), либо явно задокументировать прямой путь как канонический. Кандидат в следующий slice.

## 4. CONFLICT-4: Scenario Engine (оркестратор) DOCUMENTED_ONLY

- **Документация:** `SCENARIO_ENGINE_DESIGN_V1.md` §7-§9 (граф шагов, quality gates, resume).
- **Код:** только `ScenarioRegistry` (реестр). `scenario_engine` = design_ready в missing_registry.
- **Вердикт:** ⚠️ **ACCEPTED** (зарегистрирован как gap, НЕ конфликт) — оркестратор планируется, не обещан как существующий.

## 5. CONFLICT-5: Opportunity CLI не доступен через MCP/TG

- **Документация:** `AGENT_NAVIGATION_MAP_V1.md` §F.1 (capability→entrypoint); `INTELLIGENCE_FACTORY_CONTRACT` §M (vertical slice).
- **Код:** opportunity/whim доступны только через CLI; в `mcp_server.py` (40+ tools) и `telegram_bot.py` (7 команд) нет opportunity-инструментов.
- **Вердикт:** ⚠️ **DECISION REQUIRED (entrypoint-gap)** — добавить MCP-инструменты `opportunity_discover/run` + TG-команду `/opportunity` (или `/task` расширить). Не блокер для CLI-пути.

## 6. CONFLICT-6: Scheduler / Agent Runtime отсутствуют

- **Документация:** `WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md` §33 (Minimal v0.1) упоминает scheduler; distributed_agents.py — исполнители.
- **Код:** grep `class Scheduler`/`AgentRuntime` = 0.
- **Вердикт:** ✅ **ACCEPTED** (MISSING, roadmap-трек, НЕ конфликт — ничего не обещано как существующее).

## 7. Итоговая таблица

| # | Конфликт | Вердикт | Эффорт |
|---|----------|---------|--------|
| 1 | Opportunity §E vs 24-полевой dataclass | DECISION REQUIRED (reconcile) | S (docs) |
| 2 | Intelligence-события не эмитятся | DECISION REQUIRED (emit) | S |
| 3 | Factory→Forge не подключён в цикле | DECISION REQUIRED (подключить) | M |
| 4 | Scenario Engine DOCUMENTED_ONLY | ACCEPTED (gap) | — |
| 5 | Opportunity недоступен через MCP/TG | DECISION REQUIRED (entrypoint) | M |
| 6 | Scheduler/Agent Runtime отсутствуют | ACCEPTED (MISSING) | — |

**Рекомендация для следующего slice:** закрыть CONFLICT-2 (emit событий) + CONFLICT-3 (подключить select_forge) — оба аддитивные, минимальные, закрывают контрактные promises. См. 14_NEXT_VERTICAL_SLICE.

---

_Конец 12_ARCHITECTURAL_CONFLICTS. Переход к 13_DEAD_CODE_AND_UNVERIFIED._
