# 10_CONTENT_INTELLIGENCE_STATUS — Статус Content Intelligence

> **Промт:** `pompts_11/087_19_phase6_code_contract_forensics.md` §13 (CONTENT INTELLIGENCE)
> **Метод:** разделить GENERIC PLATFORM / CONTENT FACTORY / CONTENT INTELLIGENCE / CONCEPT EVOLUTION. Не смешивать уровни.

---

## 1. Четыре уровня (не смешивать)

| Уровень | Что это | Статус |
|---------|---------|--------|
| **GENERIC PLATFORM** | EventBus, Memory, Knowledge, Graph, Workspace, Forge | ✅ IMPLEMENTED (базовые primitives) |
| **CONTENT FACTORY** | концепты `projects_17/content_factory/concept*.md` — фабрика контента | ⚠️ DOCUMENTED_ONLY (концепты; отдельного content-движка нет) |
| **CONTENT INTELLIGENCE (CI)** | Intelligence-слой: DISCOVER→PROPOSE→SELECT→EXECUTE→ACCUMULATE→LEARN | ✅ PARTIAL → реализован как `opportunity_engine` + `whim_capture` (v5.187.7/8 + v5.189.16) |
| **CONCEPT EVOLUTION** | C-A/C-B/C-C, Evolution Memory, Concept Genome, Population, Species, Operator, Fitness | ❌ ABSENT (только RFC/дизайн, см. 11) |

## 2. Что из CI уже существует фактически (generic infrastructure)

- **DISCOVER** — `discover_candidates()` читает 4 реальных источника (whim/pulse/event/knowledge) с provenance + dedup (GAP-1, v5.189.16).
- **PROPOSE/SELECT** — `propose()` через `ScenarioRegistry.propose_roles`.
- **EXECUTE** — `execute()` через `ForgeFacade.run_chain` (единственный мост).
- **VALIDATE** — `RoleArtifactValidator` внутри run_chain.
- **ACCUMULATE** — `accumulate()` → `MemoryStore.store_knowledge(kind=candidate)` + `LearningLoop.record_feedback` (GAP-2, v5.189.16).
- **RANK** — `rank_score()`/`rank_candidates()` (v5.189.18) — композитный score поверх provenance confidence.
- **WHIM-вход** — `whim_capture` (capture/triage/promote/defer).

## 3. Что существует как content-specific implementation

**Ничего.** Нет content-specific движка (нет модуля, который пишет «контент» как артефакт фабрики). `opportunity_engine` — generic Intelligence-слой над проектом, НЕ content-specific. Content Factory (писать статьи/отчёты/контент через фабричный процесс) — только концепты в `projects_17/content_factory/concept*.md`.

## 4. Что только концептуально описано

- Content Factory как продукт (концепты `content_factory/concept.md`, `concept_1.md`, `concept_2.md`).
- Content Intelligence как отдельная подсистема (в промтах 1/2/3/4 content_factory).
- Concept Evolution (см. 11).

## 5. Ключевой вывод (граница)

**Content Intelligence НЕ существует как самостоятельная подсистема.** Есть **generic Intelligence-слой** (`opportunity_engine` + `whim_capture`), который является реализацией CI-примитивов (OBSERVE→DISCOVER→PROPOSE→EXECUTE→ACCUMULATE→LEARN). Content-specific слой (фабрика контента: генерация/форматирование/полировка артефактов) отсутствует. 

**Следующий минимальный шаг CI** (если нужен) — НЕ строить новый Content Engine, а подключить существующий Factory-путь (select_forge) к opportunity_engine (см. 14_NEXT_VERTICAL_SLICE).

---

_Конец 10_CONTENT_INTELLIGENCE_STATUS. Переход к 11_CONCEPT_EVOLUTION_STATUS._
