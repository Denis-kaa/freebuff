# IDEA EXPLORER v2.0 — Прогон: ForgeFacade-фабрика (Blueprint v3 → исполняемый конвейер)

> **Промт:** `docs_10/templates/PIPELINE_TEMPLATE.md` Приложение B (встроенный IDEA EXPLORER v2.0, источник blob `44f6dd64…` / `pompts_11/071_02_prompt_architect_1_7.md` стр. 373–925)
> **Дата:** 2026-08-10 · **Агент:** Buffy (z-ai/glm-5.2)
> **Цель:** pre-flight гейт (W-14) к следующей задаче с развилками — **как превратить ForgeFacade (ADR-013, реализован: 14 pipeline-ролей, `initiate_forge`) в реальную исполняемую фабрику** из декларативной цепочки ролей. Результат — handoff в ПРОМТ АРХИТЕКТОР 1.7.
> **Эталон прогона:** `projects_17/lead_aggregator/IDEA_EXPLORER_RUN.md` (Attract, 7 веток → score → prune → depth-2 → cross-pollination → reframe → 3 кандидата).

---

## 1. CORE LOOP (выполнен)

```
RAW IDEA → EXTRACT → GENERATE BRANCHES → EVALUATE → PRUNE → DEEPEN
         → CROSS-POLLINATE → SYNTHESIZE → NEXT DIRECTIONS
```

## 2. IDEA EXTRACTION

| Поле | Значение |
|---|---|
| **CORE IDEA** | Сделать цепочку Blueprint v3 (14 pipeline-ролей) **исполняемой**: роль завершает артефакт → явный запрос → Forge-прогон через Facade → передача следующей роли |
| **PROBLEM** | `resolve_pipeline()` вызывается только из тестов; `wizard.py` выбирает одну роль; grep `forge` в scenario/wizard = 0 → цепочка декларативна, но не исполняется; нет механизма «роль закончила → дальше» |
| **USER / ACTOR** | Buffy (агент) + пользователь (оператор платформы) + 14 pipeline-ролей Blueprint v3 (developer, tester, …) |
| **DESIRED OUTCOME** | Фабрика: явный, пошаговый, проверяемый проход ролей с Forge-валидацией артефакта на каждом шаге — без нарушения §7.3 (Scenario≠Forge) и UNFORGED-семантики |
| **MECHANISM** | (а) chain-runner поверх `PIPELINE_CHAIN`; (б) оркестрация по dependency-graph; (в) EventBus-события «роль завершена»; (г) CLI `forge chain`; (д) Modes A-G |
| **CONSTRAINTS** | §7.3 boundary (Scenario НЕ вызывает Forge напрямую), UNFORGED-семантика неизменна, additive (только `core_02/forge_facade.py` расширяется, существующие модули не трогаем), «не автоматически, не молча» (промт 70 Задача 1 п.2), Termux/SQLite-only |
| **ASSUMPTIONS** | ForgeFacade — единственная точка входа (уже реализован); 14 ролей достаточны для v0.1-фабрики; артефакты ролей — файлы в проекте (валидируются Forge CHECK) |
| **UNKNOWN** | Формат артефактов ролей (registry.yaml outputs не имеет machine-readable схемы); готовность пользователя к автопередаче ролей; нужна ли фабрика до того, как ForgeFacade использован на реальном проекте |

## 3. BRANCH GENERATION (7 веток)

| # | Тип | Ветка |
|---|---|---|
| B1 | **DIRECT** | Chain-runner: `ForgeFacade.run_chain(project, role_ids)` — проходит `PIPELINE_CHAIN` по порядку, каждый шаг: роль (артефакт) → `initiate_forge` → результат в registry → next |
| B2 | **ALTERNATIVE** | Оркестратор dependency-graph: `scripts_01/orchestrator.py` диспетчеризует роли по готовности их `dependencies` (параллельные ветки frontend/devops/fixer) — не линейная цепочка, а граф |
| B3 | **ADJACENT** | Wizard→Facade мост: `wizard_lib.py` выбирает роль → handoff в Facade с явным подтверждением (не автоматически) — интеграция с существующим выбором роли |
| B4 | **COMBINATION** | EventBus-события: роль публикует `role.completed` → подписчик-фабрика инициирует следующий Forge-шаг (событийный, не последовательный вызов) |
| B5 | **SIMPLIFICATION** | CLI `forge chain <project>`: ручной пошаговый проход с подтверждением оператора на каждом шаге — минимальная фабрика без оркестрации |
| B6 | **SCALE** | Modes A-G: фабрика как Mode B (человек-в-цикле) / Mode C (авто) — роли исполняются в разных режимах, фабрика маршрутизирует |
| B7 | **REFRAME** | Не «роли запускают Forge», а «Forge валидирует артефакты ролей»: Facade как **верификатор** (CHECK-only на каждом шаге), а не исполнитель полного цикла |

## 4. BRANCH DIFFERENTIATION

Ветки различаются по фундаментальным параметрам:
- B1/B2 — **MECHANISM** (линейная цепочка vs dependency-граф)
- B3 — **INTEGRATION** (мост с wizard'ом)
- B4 — **TRANSPORT** (событийная шина vs прямой вызов)
- B5 — **CONTROL** (ручной, operator-in-the-loop)
- B6 — **ARCHITECTURE** (Modes A-G маршрутизация)
- B7 — **PROBLEM** (переформулировка: исполнитель → верификатор)

B1 и B2 не дублируют: B1 — порядок из `PIPELINE_CHAIN` (линейный), B2 — из `dependencies` ролей (граф, допускает параллельность).

## 5. BRANCH SCORE (1–10)

| Ветка | VALUE | FEAS | NOVEL | LEVER | EXPAN | RISK | Σ |
|---|---|---|---|---|---|---|---|
| B1 Chain-runner | 9 | 8 | 4 | 9 | 8 | 3 | 41 |
| B2 Dependency-graph оркестратор | 8 | 5 | 6 | 8 | 9 | 6 | 42 |
| B3 Wizard→Facade мост | 7 | 8 | 4 | 6 | 5 | 3 | 33 |
| B4 EventBus-фабрика | 8 | 6 | 7 | 8 | 8 | 5 | 42 |
| B5 CLI chain (ручной) | 6 | 9 | 3 | 5 | 4 | 2 | 29 |
| B6 Modes A-G фабрика | 8 | 4 | 6 | 7 | 9 | 7 | 41 |
| B7 Forge-верификатор | 8 | 7 | 7 | 8 | 7 | 4 | 41 |

## 6. BRANCH STATUS

- **DEEPEN:** B1 (прямой путь, минимальный риск), B4 (событийный, высокий upside)
- **MERGE:** B3 → B1 (wizard выбирает стартовую роль, дальше chain-runner), B5 → B1 (CLI — обёртка chain-runner)
- **PARK:** B6 (требует Modes A-G зрелости), B7 (reframe — вторая итерация после B1)
- **DROP:** B2 (dependency-graph избыточен для v0.1: frontend/devops/fixer — условные ветки, НО они статичны (выбор фиксирован конфигом) и не требуют оркестратора-графа — линейный chain-runner с skip условных веток достаточен; граф = overengineering, несмотря на балл 42)

## 7. EXPLORATION BUDGET

4–8 первичных веток ✅ (7) · углубление: 2 (B1, B4) · дочерние: 1–3 на ветку ✅ · глубина: 2 уровня ✅

## 8. DEPTH-2 EXPLORATION

### B1 — Chain-runner (DEEPEN)
- **MECHANISM:** `ForgeFacade.run_chain(project, role_ids)` — для каждой роли: (1) `can_initiate(role)` gate; (2) `initiate_forge(project, role)` — Forge-прогон с артефактом роли; (3) результат в registry; (4) если failed — stop (fail-fast, R-3 статус failed queryable). **CHECK-режим на ролях = reuse существующего `ForgePipeline.stage_check()`** (без нового кода), полный цикл только на тяжёлых стадиях (developer/tester).
- **VARIANTS:** (a) полный цикл FORGE→REPORT на каждый шаг (тяжело); (b) CHECK-only на шагах ролей + полный цикл в конце (легко); (c) полный цикл только на «тяжёлых» ролях (developer/tester), CHECK на остальных.
- **CONSEQUENCES:** фабрика получает пошаговую валидацию; каждый шаг явный (не молча); chain-runner — единственное новое в Facade (additive).
- **SECOND-ORDER:** история шагов в registry (`pipeline_history`) → полный аудит-трейл прохода; LEARNING_EVENTS через `_record_learning_event` на каждом шаге → фабрика «помнит» где падает.
- **FAILURE MODE:** если роль не имеет machine-readable артефакта — CHECK не найдёт, что валидировать (UNKNOWN: формат outputs); 14 шагов × полный цикл = медленно (нужен вариант (b)/(c)).

### B4 — EventBus-фабрика (DEEPEN)
- **MECHANISM:** роль публикует `role.completed {role_id, project_id, artifact***REMOVED***` → фабрика-подписчик получает → `initiate_forge` → публикует `forge.done {status***REMOVED***` → следующий подписант. Использует существующий `scripts_01/event_bus.py` (уже в платформе, CON-19 reuse).
- **VARIANTS:** (a) синхронная шина (простой pub/sub в процессе); (b) async (очередь); (c) гибрид (EventBus + direct fallback).
- **CONSEQUENCES:** развязывает роли и фабрику (роли не знают, кто их слушает); согласуется с B15 (Collaboration = EventBus-mediated, DOCTRINE).
- **SECOND-ORDER:** фабрика становится наблюдаемой (все события в EventBus); future: распределённая фабрика (distributed_agents) без изменения ролей.
- **FAILURE MODE:** потеря события (нет гарантии доставки у простого pub/sub); сложнее отладка последовательности; B15 всё ещё DOCTRINE (не ENFORCED) — шина не проверена на production-нагрузке.

## 9. CROSS-POLLINATION ENGINE

- **B1 + B4 →** «Что из механизма B4 устраняет ограничение B1?»: chain-runner жёстко последователен → EventBus делает шаги наблюдаемыми и допускает будущую параллельность. **B1+B4 → NEW CONCEPT: событийный chain-runner** (последовательность ролей + события на каждый шаг).
- **B1 + B7 →** верификатор как режим chain-runner: `run_chain(check_only=True)` — фабрика сначала «проходит» роли CHECK-only, потом полный цикл — CORRECTIVE (B7 устраняет медленность B1 вариант (b)).
- **B1 + B3 →** wizard выбирает стартовую роль → chain-runner продолжает цепочку — COMPLEMENTARY (используем существующий выбор роли).
- **B4 + B6 →** EventBus-фабрика в Mode C (авто) — EMERGENT: «роль завершена» → авто-следующий шаг в автономном режиме, но гейт «не автоматически, не молча» требует явного разрешения оператора на авто-режим.

## 10. REFRAME ENGINE

- **USER REFRAME:** основной пользователь — не только человек-оператор, но и **другие агенты платформы** (Scenario-потоки могут «заказывать» фабричный проход как сервис).
- **PROBLEM REFRAME:** проблема не «как исполнять цепочку», а **«как гарантировать, что каждый артефакт роли валиден до передачи следующей»** → B7 (Forge-верификатор) становится ядром.
- **MECHANISM REFRAME:** отказаться от идеи «роль запускает Forge» → **Forge проверяет, а не исполняет** на этапе ролей; полный BUILD/TEST — только на финальных стадиях (B1 вариант (b)/(c)).
- **VALUE REFRAME:** ценность фабрики — не «автоматизация 14 шагов», а **«конвейер качества: каждый шаг валидирован, полный трейл, fail-fast»** — Forge как quality-gate между ролями.

## 11. BLIND-SPOT DETECTOR

- **HYPOTHESIS 1:** артефакты ролей (registry.yaml outputs: brief.md, lisa_report.md, risk_matrix.md…) существуют как файлы в реальных проектах → CHECK может валидировать их наличие (проверить на 2 инстансах: vkusvill_demo, interior_planner).
- **HYPOTHESIS 2:** `pipeline_history` в registry + LEARNING_EVENTS дают достаточно данных, чтобы фабрика сама выбирала «тяжёлые» роли по факту падений (адаптивная фабрика).
- **HYPOTHESIS 3:** EventBus уже используется production-потоками (collaboration, presence) — фабрика может reuse его без новых зависимостей (проверить подписчиков `event_bus.py`).
- **HYPOTHESIS 4:** UNFORGED-семантика на 14 шагах может «застревать» (роль завершена, но Forge не запущен) — нужен явный статус «role_done, forge_pending» в registry (расширение STATUSES — отдельное решение).

> ✅ **H4 STATUS UPDATE (2026-08-10, v5.158.0 docs-only) — REFUTED.**
>
> **Вердикт:** расширять `forge_registry.STATUSES` (`UNFORGED`, `CHECKING`, `BUILDING`, `TESTING`, `DEPLOYED`, `FAILED`) НЕ нужно. Добавлять `role_done`/`forge_pending`/`CHAIN_PARTIAL` НЕ корректно — нарушит SRP-границу между orchestrator (run_chain) и state-store (registry).
>
> **Три аргумента обоснования (по аналогии с P3_FORGE_FACADE_DESIGN.md §6.5 H4 REBUTTAL):**
>
> 1. **SRP (Single Responsibility Principle).** Существующие 6 значений `STATUSES` фиксируют **глобальное состояние артефакта проекта** (НЕ курсор оркестратора). `forge_registry` не должен знать о внутренней детализации `run_chain` per-role — это violates separation of concerns и SOLID. Per-role прогресс = domainFacade/ChainRun, не registry.
> 2. **B10 invariant (UNFORGED ≠ UNTESTED) + R-127 machine-checkable.** `validate_schema()` ForgeRegistry (закрыт в v5.155.0) требует строгий инвариант: `UNFORGED ⇒ last_run_at=None, last_pipeline пуст`, `DEPLOYED/FAILED ⇒ last_run_at есть`. Расширение `STATUSES` размывает эти invariants (появляются переходные состояния, которые сложнее проверять автоматически). KISS + minimum-viable per ADR-013.
> 3. **Existing `ChainRun.chain` (+ seриализация в `last_pipeline["chain"***REMOVED***`) достаточен.** `ChainStage` (frozen dataclass, v5.157.0) уже фиксирует per-role прогресс: `role_id` + `mode` + `status` + `details` + `duration_s`. Каждый HEAVY-role `initiate_forge()` вызывает `record_run()` → автоматически сохраняется в `ForgeStatus.last_pipeline["chain"***REMOVED***` через `defaultdict`-accumulation. H4 use-case «узнать, на чём прервалась цепочка для resume» (CLI `forge chain --resume`, v5.162+) закрывается чтением существующего `last_pipeline["chain"***REMOVED***` без новых STATUSES.
>
> **Cross-references:**
> - Подробное обоснование с детальной decision tree → [`P3_FORGE_FACADE_DESIGN.md` §6.5 H4 REBUTTAL***REMOVED***(P3_FORGE_FACADE_DESIGN.md) (v5.158.0 docs-only).
> - Reference в audit-RECAP trail → [`AUDIT_WS_OS_P65_RECAP_V2.md`***REMOVED***(AUDIT_WS_OS_P65_RECAP_V2.md) (cross-link в §33.11.2 5 cross-cutting meta-audit themes; H4 не входит в RECAP, но per-role state-management принцип зафиксирован в R-23..R-27 RECAP_v2).
> - Forward reference в release specification → [`WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md` §36.x UPDATE 2026-08-10***REMOVED***(WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md) (forward-to-v0.1; H4 REFUTED в составе 19/23 quality gates метрик).

## 12. PRUNING

- DROP B2 (граф избыточен: цепочка фактически линейна; граф = overengineering для v0.1), MERGE B3→B1, MERGE B5→B1 (CLI-обёртка).
- KEEP B1 (ядро фабрики), KEEP B4 (событийный слой — future), PARK B6, PARK B7 (вторая итерация).

## 13. CONVERGENCE

```
MANY IDEAS (7) → FEWER STRONG (B1, B4) → BEST COMBINATION (B1+B4 событийный chain)
              → CANDIDATE CONCEPTS → SYNTHESIS
```

## 14. FINAL CANDIDATES

- **CANDIDATE A — PRACTICAL:** **Chain-runner v1** (B1+B3+B5): `ForgeFacade.run_chain(project, role_ids)` — пошаговый проход `PIPELINE_CHAIN`, CHECK-режим на ролях + полный цикл на тяжёлых, wizard выбирает старт, CLI `forge chain` как обёртка. Реалистичный, additive, минимальный риск.
- **CANDIDATE B — HIGH UPSIDE:** **Событийный chain-runner** (B1+B4): цепочка ролей + EventBus-события на каждый шаг (`role.completed`/`forge.done`). Наблюдаемость, будущая параллельность, reuse event_bus (B15 DOCTRINE → шаг к ENFORCED).
- **CANDIDATE C — UNEXPECTED:** **Forge-верификатор** (B7-ядро): фабрика = quality-gate между ролями (CHECK-only до финала), полный BUILD/TEST только на финальных стадиях. Переформулирует «роль запускает Forge» → «Forge подтверждает роль». Быстро (CHECK дешевле полного цикла), но меняет ментальную модель.

## 15. CONCEPT COMPARISON

| Concept | Value | Feas | Novel | Risk | Expansion |
|---|---|---|---|---|---|
| A Chain-runner v1 | 9 | 8 | 4 | 3 | 8 |
| B Событийный chain | 9 | 6 | 7 | 5 | 9 |
| C Forge-верификатор | 8 | 7 | 7 | 4 | 7 |

**BEST PRACTICAL:** A · **BEST UPSIDE:** B · **BEST EXPERIMENT:** C (проверка H1: артефакты ролей валидируются CHECK — самый дешёвый способ доказать ценность фабрики)

## 16. CRITICAL DECISION POINT

«Критическая развилка: **валидируются ли артефакты ролей существующим Forge CHECK?**

Если H1 подтверждён (CHECK находит brief.md/lisa_report.md/risk_matrix.md по outputs ролей) → развиваем **A (chain-runner v1)** — пошаговая фабрика с quality-gate, минимальный риск.
Если H1 опровергнут (артефакты ролей не в проекте / CHECK не знает о них) → **сначала аддитивный RoleArtifactValidator** на артефакты ролей (ядро C/верификатор-режим; расширение = НОВЫЙ класс внутри `core_02/forge_facade.py`, существующие модули `workspace.py`/`forge_pipeline.py` НЕ изменяются — CONSTRAINT additive соблюдён), затем строить chain-runner поверх.»

**Решение по данным на 2026-08-10:** H1 не проверен (артефакты ролей в реальных проектах не аудированы). → **Эксперимент C первым** (проверка H1: grep outputs ролей в vkusvill_demo/interior_planner, 15 минут, 0 нового кода); по результату — A (chain-runner) или расширение CHECK.

> ✅ **ЭКСПЕРИМЕНТ H1 ВЫПОЛНЕН 2026-08-10 (v5.155.0) — H1 ОПРОВЕРГНУТ.**
>
> Метод: полный аудит registry.yaml (17 ролей, outputs каждого) + проверка файловой системы 2 инстансов + инспекция `Project.get_requirements()`.
>
> **Факты (evidence):**
> 1. `registry.yaml` `pipeline:` — 17 ролей; 15 объявляют outputs (explainer: brief.md/parsed_requirements.md, lisa: lisa_report.md, risk: risk_matrix.md, decomposer: decomposition.md/module_list.md/integration_topology.md, architect: architecture.md/adr/*.md/contracts.yaml, auditor: audit_report.md, developer: src/**/*.py, tester: mutation_test_results.md, documenter: README.md/PORTFOLIO_CASE.md/TG_POST.md/API_DOCS.md/ARCHITECTURE.md, retrospective: retrospective_report.md/LESSONS.md/lisa_calibration.yaml и т.д.).
> 2. **Ни один артефакт ролей не существует на диске** в vkusvill_demo (17 файлов: README/LESSONS/STEPS/business_logic.md/parity_report.md/model_forecast.xlsx — НИ ОДНОГО brief.md/lisa_report.md/risk_matrix.md) и interior_planner (CHECKLIST/README/RUNNABLE + подпапки app/seed/web — артефактов ролей нет). grep по 11 типовым outputs (brief.md, parsed_requirements.md, lisa_report.md, risk_matrix.md, architecture.md, acceptance.md…) → все **NOT FOUND**.
> 3. `Project.get_requirements()` валидирует **только** README.md, RUNNABLE.md, CHECKLIST.md, STEPS.md (4 missing.append-строки); слово «brief» в коде CHECK отсутствует (0 упоминаний). CHECK на vkusvill_demo: `missing: RUNNABLE.md, CHECKLIST.md` — валидирует стандартный набор, НЕ outputs ролей.
>
> **Вердикт:** существующий Forge CHECK **НЕ валидирует артефакты ролей** (они даже не производятся ролями в реальных проектах). → Развилка §16: **путь C активирован** — сначала **RoleArtifactValidator** (верификатор-режим), затем строить chain-runner поверх. **Уточнение по CONSTRAINT additive (CON-16/CON-21):** «расширить CHECK» = НЕ правка существующих `Project.get_requirements()`/`ForgePipeline.stage_check()` (это нарушило бы additive), а **новый аддитивный класс `RoleArtifactValidator` внутри `core_02/forge_facade.py`**, который КОМПОЗИРУЕТ существующий CHECK (`stage_check()` как есть, без изменений) + сверяет outputs ролей из `registry.yaml`. **Scope валидатора = наличие файлов-артефактов (existence)**, НЕ content-схема (формат контента артефактов остаётся UNKNOWN из §2 — при реализации шага 2 фиксировать это явно). Существующие модули не модифицируются. H1 из «UNKNOWN» переведён в «REFUTED (fact)»; blind-spot-гипотеза 1 закрыта фактом.

## 17. USER INTERACTION (пропущен — автономный режим, выбор по данным: эксперимент C дешевле всего и даёт факт для A)

## 18. HANDOFF TO PROMPT ARCHITECT

**SELECTED CONCEPT:** Candidate A (chain-runner v1) с ПРОЙДЕННЫМ гейтом-экспериментом C (H1 выполнен 2026-08-10 → REFUTED → путь C: RoleArtifactValidator аддитивно первым).
**CORE OBJECTIVE:** исполняемая фабрика из 14 pipeline-ролей Blueprint v3 с Forge-валидацией на каждом шаге.
**PROBLEM:** цепочка ролей декларативна, но не исполняется (`resolve_pipeline()` только в тестах; wizard выбирает одну роль).
**TARGET:** платформа Workspace OS (core_02/forge_facade.py — существующий, additive-расширение), Termux/SQLite-only.
**MECHANISM:** `run_chain(project, role_ids)` поверх `PIPELINE_CHAIN` + `initiate_forge`; CHECK-режим на ролях, полный цикл на тяжёлых (developer/tester); CLI `forge chain`; опционально EventBus-события (B4).
**CONSTRAINTS:** §7.3 boundary (Scenario≠Forge, только Facade), «не автоматически, не молча» (явный запрос роли/оператора), UNFORGED-семантика неизменна, additive, без новых зависимостей.
**ASSUMPTIONS:** 14 ролей достаточны; артефакты ролей валидируются CHECK — **H1 проверен 2026-08-10: ОПРОВЕРГНУТ** (CHECK не знает outputs ролей → нужен аддитивный RoleArtifactValidator в forge_facade.py); фабрика не нужна до первого боевого использования ForgeFacade.
**DECISIONS:** A принят; C — эксперимент-гейт (H1); B4 — опциональный слой (future); B2 (граф) отклонён; B6 (Modes) — park.
**REJECTED ALTERNATIVES:** B2 (dependency-graph overengineering), B6 (Modes A-G преждевременно).
**OPEN QUESTIONS:**

- â **H1 â закрыт** (REFUTED 2026-08-10 v5.155.0): см. Â§16 критическая развилка + H1 RESULTS блок ниже. Артефакты ролей НЕ валидируются CHECK â путь C: RoleArtifactValidator аддитивно первым.
- â **H4 â закрыт** (REFUTED 2026-08-10 v5.158.0/v5.161.0): см. Â§11 H4 REBUTTAL блок выше. Расширять forge_registry.STATUSES НЕ нужно (SRP + B10 invariant + existing ChainRun.chain достаточен), resume-семантика закрывается через existing last_pipeline[chain***REMOVED*** (CLI forge chain --resume, v5.162+).
- ✅ **FWD-1 — закрыт** (CLOSED v5.166.0 через vkusvill_research): первое боевое использование ForgeFacade успешно прогнано на всех 3 demo-проектах (vkusvill_research + vkusvill_demo + interior_planner) через `forge.py chain --json` + `forge.py chain --resume --json` (tests_09/test_forge_chain_real_integration.py: 6/6 PASS, validation фиксировано v5.164.0 + v5.166.0). Originally-specified project vkusvill_research подтверждён елегибльным (директория underscore, project_id в регистри 'vkusvill-research' hyphen-form). cwd-fallback resolution работает. Ответ: фабрика может быть полезна до боевого ForgeFacade.

**RECOMMENDED APPROACH:** шаг 1 = H1 — **выполнен (2026-08-10, REFUTED)**; шаг 2 = `RoleArtifactValidator` (аддитивный класс в `forge_facade.py`: существующий CHECK без изменений + outputs ролей из registry.yaml); шаг 3 = `run_chain` с CHECK-режимом; шаг 4 = CLI `forge chain`; шаг 5 = EventBus-события (по желанию).

---

## 19–23. ANTI-ANCHORING / ANTI-HALLUCINATION / OUTPUT / STYLE / GATE

- **ANTI-ANCHORING соблюдён:** исходная «автоматизация цепочки ролей» оспорена reframe (B7: Forge-верификатор, quality-gate) без изменения цели — конвейер качества.
- **FACT vs ASSUMPTION vs HYPOTHESIS разделены:** факты — ADR-013 (Facade реализован, 14 ролей, PIPELINE_CHAIN, §7.3); гипотезы — H1-H4 явно помечены; «артефакты ролей валидируются» = UNKNOWN (H1), не FACT.
- **FINAL QUALITY GATE:** ✅ альтернативы реальные (7, механизм/транспорт/контроль различаются) · ✅ соседние возможности (wizard, EventBus, Modes) · ✅ reframe есть (B7: исполнитель → верификатор) · ✅ сильные ветки углублены (B1, B4) · ✅ слабые отброшены (B2, B6 parked) · ✅ комбинации найдены (B1+B4 EMERGENT, B1+B7 CORRECTIVE) · ✅ факты отделены от гипотез (H1 = UNKNOWN → REFUTED фактом 2026-08-10) · ✅ пространство сужено (7 → 3 кандидата → A) · ✅ понятный следующий шаг (эксперимент H1 + run_chain).

**Вывод:** ForgeFacade-фабрика = **chain-runner v1** (Candidate A) как основной путь, с **экспериментом H1** (валидируются ли артефакты ролей CHECK) как самым дешёвым первым шагом; EventBus-слой (B4) — опциональный upgrade; dependency-graph (B2) отклонён как overengineering; рефрейм «Forge-верификатор» (B7) — вторая итерация. §7.3 boundary и UNFORGED-семантика сохраняются во всех кандидатах.
