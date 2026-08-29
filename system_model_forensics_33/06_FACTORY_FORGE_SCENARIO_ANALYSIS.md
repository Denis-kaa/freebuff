# 06_FACTORY_FORGE_SCENARIO_ANALYSIS.md — Границы Factory / Forge / Scenario

> **Задача (§6):** НЕ предполагать, что Content Factory — центр. Определить реальные границы.

---

## Реально существующие Factory (по `runtime_05/factories/` + `FactoryRegistry`)

| Factory | Манифест | Forges (паспорта) | Status |
|---------|----------|-------------------|--------|
| `architecture` | `runtime_05/factories/architecture/factory.yaml` | `review.yaml`, `governance.yaml` (без `architecture.yaml`?) | design/material |
| `content` | `.../content/factory.yaml` | `writing.yaml` | design |
| `research` | `.../research/factory.yaml` | `analysis.yaml` | design |
| `test` | `.../test/factory.yaml` | `verifier.yaml` | production (code capability) |

> **Только 4 фабрики.** Целевая модель рисует Research/Code/Design/Content/Image/Video/Document/Data —
> **8+**, но в коде — **4**, и они частично «design» (не production). `CODE_RESOLUTION_POLICY`
> жёстко биндит `code → (test, verifier)` (Phase 13 G-11.6), НЕ `code → CodeFactory`.

## Что такое Factory в реальности?

**Factory = декларативный capability-каталог** (YAML-манифест + паспорт), НЕ исполняемый
движок. Исполнение делегируется `BaseFactory`-адаптерам (`scripts_01/content_factory.py`,
`research_factory.py`, `test_factory.py`) → `ForgeFacade.run_chain`.

```
Opportunity (capability token)
   → FactoryRegistry.select_forge(capability)   ← выбор по status-priority + tie-break
        → (FactoryPassport, ForgePassport)
             → BaseFactory.execute()
                  → ForgeFacade.run_chain()      ← единственный execution boundary
```

## Что такое Forge в реальности? (4 смысла — развести)

| Имя | Модуль | Семантика |
|-----|--------|-----------|
| ForgePassport | `core_02/forge_passport.py` | **декларация** кузни (mission/inputs/outputs/capabilities) |
| ForgeFacade | `core_02/forge_facade.py` | **исполнение**: chain-runner (14 ролей) |
| ForgePipeline | `core_02/forge_pipeline.py` | **валидация/сборка**: CI FORGE→CHECK→BUILD→TEST→DEPLOY→REPORT |
| ForgeRegistry | `core_02/forge_registry.py` | **состояние**: реестр статусов проектов |

**Вывод (§6):** Forge в целевой модели = «workflow внутри Factory». В коде этому
соответствует **ForgePassport + ForgeFacade.run_chain** (пара «декларация → исполнение»).
`ForgePipeline` — это **ортогональный CI-пайплайн сборки** (другое значение «Forge»),
а `ForgeRegistry` — вообще про статусы проектов, не про workflow.

## Что такое Scenario в реальности? (двойственен)

| Смысл | Модуль | Роль |
|-------|--------|------|
| корпус ролей (статический) | `core_02/scenario.py` + `scenario_registry.py` + `blueprint_v3.py` | «кто может выполнять» (BlueprintCorpus = 14+ ролей) |
| decision-слой (динамический) | `scripts_01/scenario_intelligence.py` | «что сделать и куда отправить» (Opportunity → capability → factory/forge) |

## Границы (ответы на §7)

1. **Factory принадлежит Project?** — НЕТ. Глобальная capability (`FactoryRegistry`
   грузит `runtime_05/factories/`, не `projects_17/`). Совпадает с целевой моделью.
2. **Forge принадлежит Factory?** — ДА (через `factory_id` в паспорте; `select_forge`
   возвращает пару). Совпадает.
3. **Scenario вызывает Factory?** — ДА, но через **два разных механизма**:
   (а) `opportunity_engine.propose` → `ScenarioIntelligence.select` → capability →
   `FactoryRegistry.select_forge`; (б) `forge_facade.run_chain` → 14 ролей напрямую
   (в обход Factory, если нет capability-токена — fallback).
4. **Scenario напрямую вызывает Forge?** — **НЕТ** (§7.3 boundary, CONFIRMED):
   `ForgeFacade` — единственный мост, `Scenario`/роли не трогают `ForgePipeline` напрямую.
5. **Agent вызывает Scenario или часть Forge?** — Роль (через `RoleExecutor`) — часть
   Forge chain; Orchestrator (агентный слой) — НЕ соединён с ForgeFacade.

## Схема реальных отношений

```
Whim ─→ Opportunity ─→ ScenarioIntelligence ─→ capability token
                                                  │
                                                  ▼
                                    FactoryRegistry.select_forge
                                                  │
                                         (FactoryPassport, ForgePassport)
                                                  │
                                                  ▼
                                    BaseFactory.execute ─→ ForgeFacade.run_chain
                                                              │
                                              ┌───────────────┴──────────────┐
                                              ▼                              ▼
                                    14 ролей (RoleExecutor)      ForgePipeline (CI, для HEAVY ролей)
                                              │
                                              ▼
                                        Artifact (файлы)
                                              │
                                              ▼
                                    MemoryStore + LearningLoop
```
