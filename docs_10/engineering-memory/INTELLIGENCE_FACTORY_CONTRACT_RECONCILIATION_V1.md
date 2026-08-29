# INTELLIGENCE_FACTORY_CONTRACT_RECONCILIATION_V1.md — Сверка контракта A–P с форензик-документами

| Поле | Значение |
|------|----------|
| **Документ** | INTELLIGENCE_FACTORY_CONTRACT_RECONCILIATION_V1.md |
| **Статус** | ✅ СОГЛАСОВАНО (reconciliation) — единый план Фаз 1–3, расхождения зафиксированы |
| **Версия** | 1.0 |
| **Дата** | 2026-08-12 |
| **Источник задания** | «Сверь контракт (A–P) с FORENSICS_CI_REPORT_V1.md и FORENSICS_CI_FOLLOWUP_V1.md: единый согласованный план Фаз 1–3 и зафиксируй расхождения» |
| **Метод** | Покомпонентная сверка по измерениям (жизненный цикл, фазы, персистентность, SELECT/EXECUTE, события, реестр) с evidence (path + секция). Факт-чек текущего состояния реестра (`python -m core_02.missing_registry list --json`). |
| **Сравниваемые документы** | ① `INTELLIGENCE_FACTORY_CONTRACT_V1.md` (A–P, 2026-08-12) · ② `FORENSICS_CI_REPORT_V1.md` (A–K, 2026-08-12) · ③ `FORENSICS_CI_FOLLOWUP_V1.md` (план Фаз 1–3, 2026-08-12) |
| **Главное правило** | Register-first (RA2 ARB-REV-004, AGENTS.md §5) — единый канон реализации всех трёх документов. |

---

## 1. Executive Summary

**Вердикт: три документа архитектурно согласованы.** Контракт A–P (Intelligence ↔ Factory), форензик-отчёт A–K (что существует / чего нет, G0–G4) и план FOLLOWUP (в каком порядке строить) не противоречат друг другу ни по одному из 10 сверенных измерений. Зафиксированы **2 расхождения — оба минорные и разрешённые** (см. §4): D1 — неполный список lifecycle-статусов в отчёте (§I), D2 — устаревший счётчик записей реестра в отчёте (B.2/B.5).

**Единый канонический план Фаз 1–3** (согласован всеми тремя документами) зафиксирован в §3. Фаза 1 (opportunity_engine + whim_capture) — первый вертикальный срез §J; Фаза 2 (factory_registry) — регистровый слой; Фаза 3 (scenario_engine) — оркестратор, не блокирует срез.

**Факт-чек (2026-08-12):** `opportunity_engine.py` и `data_13/opportunities.yaml` **не созданы** — реализация Фазы 1 ещё не начата, что соответствует финальной строке контракта «Repository verified. Intelligence ↔ Factory contract defined. Implementation not started.» Открытый пункт O1 (рассинхрон `factory_registry` реестр↔диск) также не закрыт.

---

## 2. Сверочная матрица (10 измерений)

| # | Измерение | ② REPORT A–K | ① CONTRACT A–P | ③ FOLLOWUP | Вердикт |
|---|-----------|--------------|-----------------|------------|---------|
| 1 | **Новые сущности (G2/G3)** | §I: 3 сущности — Whim capture (G3, module), Opportunity Engine (G3, engine), FactoryRegistry (G2, registry) | §L: те же 3 (`whim_capture`, `opportunity_engine`, `factory_registry`) + `opportunities` persistence | §1: те же 3, та же классификация | ✅ Согласовано |
| 2 | **Порядок фаз** | §K: G3+G2 новые, но небольшие; срез реализуем read-only головой | §N: «Сейчас (Фаза 1)» = opportunity_engine + whim_capture; «Следующий этап» = factory_registry + scenario_engine | §1: Фаза 1 (OE→whim→e2e) → Фаза 2 (factory_registry) → Фаза 3 (scenario_engine) | ✅ Согласовано (контракт сжимает Фазы 2–3 в «следующий этап», порядок идентичен) |
| 3 | **Lifecycle-статусы opportunity** | §I: `ACTIVE/DEFERRED/READY/REACTIVATED` (4, без COMPLETED); §J: результат — «статус opportunity (COMPLETED)» | §E/§I/§P: `ACTIVE/DEFERRED/READY/REACTIVATED/COMPLETED` (5) | §3.1: `ACTIVE/DEFERRED/READY`; §3.3: «ACTIVE → DEFERRED → REACTIVATED → READY → COMPLETED» (5) | ⚠️ **D1** (разрешено, см. §4) — канон = 5 статусов |
| 4 | **Персистентность** | §G: Storage G0 (`data_13/*.yaml + *.db`) | §E/§I: lifecycle → `data_13/opportunities.yaml`; контент/знания → MemoryStore KO kind=`opportunity`; whim → `data_13/whims.yaml` | §3.2 шаг 1.1: `data_13/opportunities.yaml`; шаг 1.3: `data_13/whims.yaml` | ✅ Согласовано (контракт фиксирует dual-write решение, FOLLOWUP его подтверждает) |
| 5 | **SELECT сценария** | §J: через `ScenarioRegistry` (G0) | §F: `ScenarioRegistry.list_scenarios` + `propose_roles`, НЕ плодить второй реестр; `selected_scenario` в opportunity | §5: SELECT за интерфейсом `select_scenario()` (для будущей подмены на ScenarioEngine, CAN-16) | ✅ Согласовано (§N контракта упоминает тот же интерфейс) |
| 6 | **EXECUTE** | §J/§C.1: `ForgeFacade.run_chain` (14 ролей), единственный мост | §H: только `ForgeFacade.run_chain`/`initiate_forge`; `ForgeFacadeResult`/`ChainRun` переиспользуем | §3.1: `ForgeFacade.run_chain, 14 ролей` | ✅ Согласовано |
| 7 | **События** | §F: EventBus G0 (publish/subscribe) | §J: 11 событий (`opportunity.*`, `scenario.selected`, `execution.*`, `artifact.*`, `whim.created`) | — (не перечисляет) | ✅ Согласовано (контракт добавляет детализацию, не противоречит) |
| 8 | **Счётчик MissingRegistry** | B.2/B.5: «7 записей» | §A: opportunity_engine=prompt_written, whim_capture=registered, factory_registry=design_ready (без общего счётчика) | §2: «9 записей» + статусы сущностей | ⚠️ **D2** (разрешено, см. §4) — факт на сегодня = 9 записей |
| 9 | **Реестровый статус 3 сущностей** | §I: «оба G3» (OE + Whim) | §A: OE=`prompt_written` (промт 079_19), whim=`registered`, factory=`design_ready` | §2: те же статусы (таблица) | ✅ Согласовано (факт-чек реестра подтверждает: 9 записей, статусы совпадают) |
| 10 | **Закрытый словарь (ANTI-6b)** | §D: TOOL confirmed (research_web/lisa_estimator implemented) | §O R1: OE — Engine (kind: engine), НЕ в KNOWN_CAPABILITIES; drift-тест остаётся зелёным | §3.3: «KNOWN_CAPABILITIES/ModelCatalog не изменены» | ✅ Согласовано |

**Итог матрицы:** 8/10 измерений — полное согласие; 2 измерения содержат расхождения D1/D2 (оба — неточности отчёта, разрешены ниже).

---

## 3. Единый согласованный план Фаз 1–3 (канонический)

Согласован всеми тремя документами (REPORT §I/§J/§K · CONTRACT §M/§N · FOLLOWUP §3–§5). Register-first переходы — единственный канон продвижения (AGENTS.md §5).

### Фаза 1 — First Vertical Slice (§J): Whim → Opportunity → Artifact

| Шаг | Действие | register-first | Результат |
|-----|----------|----------------|-----------|
| **1.1** | Реализовать `opportunity_engine` по `pompts_11/079_19_opportunity_engine_capability.md`: `scripts_01/opportunity_engine.py` + `tests_09/test_opportunity_engine.py` + `data_13/opportunities.yaml`. DISCOVER→LIFECYCLE(5 статусов)→PROPOSE→SELECT(`select_scenario()` за интерфейсом)→EXECUTE(`ForgeFacade.run_chain`, project_read_only=True)→VALIDATE→ACCUMULATE→COMPLETED | `opportunity_engine`: prompt_written → **implemented** | Рабочий engine (контракт §E/§F/§H/§M) |
| **1.2** | Написать промт `whim_capture` → `pompts_11/080_19_whim_capture_capability.md` (вход: мысль; хранение: `data_13/whims.yaml`; интеграция: event_bus `whim.created` + project_pulse) | `whim_capture`: registered → **prompt_written** | Промт на реализацию |
| **1.3** | Реализовать `whim_capture` по промту 080_19 (лёгкий захват, `DEFERRED ≠ DELETED`, сигнал → OE) | `whim_capture`: prompt_written → **implemented** | Модуль входа |
| **1.4** | e2e §J: whim → OE run → артефакт + memory_store + COMPLETED | — | Срез подтверждён |

**Критерии приёмки Фазы 1 (из FOLLOWUP §3.3 + CONTRACT §M):** lifecycle ACTIVE→DEFERRED→REACTIVATED→READY→COMPLETED работает, DEFERRED не стирается; propose через `ScenarioRegistry.propose_roles`; run (не dry-run) → run_chain 14 ролей → RoleArtifactValidator → memory_store → COMPLETED; `--json` валиден; `test_opportunity_engine.py`/`test_whim_capture.py` зелёные; mypy чистый; KNOWN_CAPABILITIES не изменён (drift-тест зелёный).

### Фаза 2 — Factory Registry (Missing #1, G2)

| Шаг | Действие | register-first | Результат |
|-----|----------|----------------|-----------|
| **2.1** | Закрыть рассинхрон: `python -m core_02.missing_registry mark-prompt-written factory_registry --prompt pompts_11/078_19_factory_registry.md` (промт уже на диске) | `factory_registry`: design_ready → **prompt_written** | Реестр догоняет диск (**O1**) |
| **2.2** | Реализовать по `pompts_11/078_19_factory_registry.md` + `FORGE_PASSPORT_CODE_REPRESENTATION_V1.md`: реестр фабрик/паспортов по образцу ScenarioRegistry, YAML `runtime_05/factories/`; **не модифицировать** `scenario.py` (CAN-16 ADDITIVE) | `factory_registry`: prompt_written → **implemented** | Реестр фабрик/кузен |
| **2.3** | (Опционально) FactoryRegistry как резолвер в OE.PROPOSE — выбор Factory/Forge по паспорту | — | Улучшение выбора, не блокер §J |

### Фаза 3 — Scenario Engine (Missing #2, вне §I)

| Аспект | Деталь |
|--------|--------|
| Статус | `design_ready` (SCENARIO_ENGINE_DESIGN_V1.md) |
| Роль | Оркестратор-композитор: заменяет прямой вызов ScenarioRegistry в OE.SELECT на `ScenarioEngine.resolve(CapabilityRef)` за интерфейсом `select_scenario()` (требование FOLLOWUP §5, CONTRACT §N) |
| Когда | После Фаз 1–2; не блокирует вертикальный срез §J |
| Промт | Будет написан на этапе Фазы 3 (номер 08X_19) |

### Зависимости (согласовано FOLLOWUP §6)

- **FactoryRegistry → OE:** ❌ не блокирует Фазу 1 (срез идёт через G0 ScenarioRegistry напрямую);
- **ScenarioEngine → OE:** ❌ не блокирует Фазу 1 (SELECT за интерфейсом `select_scenario()`);
- **OE → Whim:** ⚠️ функционально, не по сборке (OE принимает готовый сигнал и без whim_capture — промт 079_19 §3.1.1).

---

## 4. Зарегистрированные расхождения

### D1 — Lifecycle-статусы opportunity: отчёт §I перечисляет 4, канон — 5

| Аспект | Деталь |
|--------|--------|
| **Где** | ② REPORT §I: «Opportunity lifecycle (ACTIVE/DEFERRED/READY/REACTIVATED)» |
| **vs** | ① CONTRACT §E/§I/§P и ③ FOLLOWUP §3.3: 5 статусов, включая **COMPLETED** |
| **Статус** | ⚠️ Минорное расхождение (неполнота списка в отчёте) — **разрешено** |
| **Разрешение** | §J самого отчёта требует результата «статус opportunity (**COMPLETED**)» — COMPLETED является терминальным статусом среза и подразумевается моделью §I, но не перечислен в списке. Канон фиксирует **5 статусов**: `ACTIVE / DEFERRED / READY / REACTIVATED / COMPLETED` (контракт §E). Отчёт не противоречит — список §I неполон. |
| **Действие** | Не менять отчёт (read-only-артефакт форензики). Канон — контракт §E и FOLLOWUP §3.3. При реализации 1.1 использовать 5 статусов. |

### D2 — Счётчик MissingRegistry: отчёт «7 записей», факт — 9

| Аспект | Деталь |
|--------|--------|
| **Где** | ② REPORT B.2: «Register-first реестр недостающих элементов (7 записей)» и B.5: «missing_registry.yaml (72 строки) — 7 записей register-first» |
| **vs** | ③ FOLLOWUP §2: «Текущее состояние register-first (факт, **9 записей**)»; факт-чек 2026-08-12: **9 записей** (conformance_checker, decision_registry, factory_registry, lisa_estimator, model_diagram_autogen, opportunity_engine, research_web, scenario_engine, whim_capture) |
| **Статус** | ⚠️ Минорное расхождение (устаревший снимок в отчёте) — **разрешено** |
| **Разрешение** | Отчёт фиксировал состояние на момент форензики (до регистрации 2 записей). Канон — **сам реестр** (`data_13/missing_registry.yaml`, источник истины) и FOLLOWUP §2 (9 записей). |
| **Действие** | Не менять отчёт. При любых операциях с реестром опираться на `python -m core_02.missing_registry list --json` (не на счётчики в док-снимках). |

---

## 5. Открытые пункты (не расхождения — незакрытые действия)

| # | Пункт | Статус (2026-08-12) | Откуда |
|---|-------|----------------------|--------|
| **O1** | `factory_registry` в реестре = `design_ready`, промт `pompts_11/078_19_factory_registry.md` уже на диске → рассинхрон реестр↔диск | Открыт (шаг 2.1 Фазы 2) | FOLLOWUP §2 наблюдение 3, §4.2 шаг 2.1 |
| **O2** | `opportunity_engine.py` / `data_13/opportunities.yaml` не созданы → Фаза 1 не начата | Открыт (соответствует финалу контракта) | CONTRACT финал «Implementation not started»; факт-чек |
| **O3** | `whim_capture` — нет промта 080_19 (статус `registered`) | Открыт (шаги 1.2–1.3 Фазы 1) | FOLLOWUP §3.2 |

---

## 6. Валидация и связные документы

**Валидация (2026-08-12):** факт-чек реестра — 9 записей, статусы сущностей совпадают с контрактом/планом · `python -m core_02.missing_registry check` → ok · реестр DOCUMENT_REGISTRY — bump 92 → 93 · консистентность платформы — `TestRealWorkspaceConsistent` + `build_report` (TOTAL 0, CONSISTENT True).

**Связные документы:**
- `docs_10/engineering-memory/INTELLIGENCE_FACTORY_CONTRACT_V1.md` — контракт A–P (канон дизайна);
- `docs_10/engineering-memory/FORENSICS_CI_REPORT_V1.md` — отчёт A–K (канон фактов, read-only);
- `docs_10/engineering-memory/FORENSICS_CI_FOLLOWUP_V1.md` — план Фаз 1–3 (канон порядка);
- `docs_10/engineering-memory/FORENSICS_CI_GAP_MAP_V1.md` — карта G0–G4;
- `docs_10/engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md` — §20 (Missing #1/#2/#8/#9), §21 (фазировка);
- `pompts_11/078_19_factory_registry.md`, `pompts_11/079_19_opportunity_engine_capability.md` — промты;
- `core_02/missing_registry.py` — register-first реестр (AGENTS.md §5).

---

*Сверка выполнена 2026-08-12: 10 измерений, 8 согласованы полностью, 2 расхождения (D1/D2) разрешены с фиксацией канона. Единый план Фаз 1–3 (§3) — обязательный порядок реализации всех трёх документов.*
