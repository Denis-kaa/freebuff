# FORENSICS_CI_FOLLOWUP_V1.md — план реализации Minimal CI Layer (§I)

| Поле | Значение |
|------|----------|
| **Документ** | FORENSICS_CI_FOLLOWUP_V1.md |
| **Статус** | 🗺 ПЛАН РЕАЛИЗАЦИИ (ACTIVE) — «что строим и в каком порядке» |
| **Версия** | 1.0 |
| **Дата** | 2026-08-12 |
| **Источник задания** | FORENSICS_CI_REPORT_V1.md (§I Minimal Integration Model, §J First Vertical Slice, §K Readiness) |
| **Прецеденты** | ARB-REV-004 (RA2: маппинг G0–G4 + register-first), FORENSICS_CI_GAP_MAP_V1.md (G0–G4 карта, 2026-08-12) |
| **Место в цепочке** | Forensics (read-only) → **этот план** → промты (078_19/079_19/080_19) → реализация → mark-implemented |
| **Главное правило** | **Register-first (RA2 ARB-REV-004, AGENTS.md §5):** ничего не строим, пока сущность не зарегистрирована в `core_02/missing_registry.py` (YAML `data_13/missing_registry.yaml`); lifecycle `registered → design_ready → prompt_written → implemented` — только вперёд. |

---

## 1. Executive Summary

Целевой Minimal CI Layer (§I отчёта) состоит из **трёх новых сущностей**:

| # | Сущность | Класс | Kind | Factory | Реестровый статус (2026-08-12) |
|---|----------|-------|------|---------|-------------------------------|
| 1 | **Whim capture** | G3 (module) | `module` | content | `registered` (промт ещё не написан) |
| 2 | **Opportunity Engine** | G3 (engine) | `engine` | content | `prompt_written` (промт **079_19** готов) |
| 3 | **Factory Registry** | G2 (registry) | `registry` | — | `design_ready` (промт **078_19** уже существует на диске) |

**Вердикт плана:** первый вертикальный срез §J требует **только две «головы»** — `whim_capture` + `opportunity_engine` (весь «хвост» G0 уже работает). FactoryRegistry — **вторая фаза** (регистровый фундамент для масштабирования), не блокирует срез.

**Порядок (3 фазы):**
1. **Фаза 1 — First Vertical Slice (§J):** `opportunity_engine` (промт готов → реализация) → `whim_capture` (промт 080_19 → реализация) → e2e-прогон полного цикла.
2. **Фаза 2 — Registry-слой:** `factory_registry` (mark-prompt-written по **078_19** → реализация).
3. **Фаза 3 — Будущее (вне §I):** `scenario_engine` (Missing #2, design_ready) — оркестратор, в который позже делегируются PROPOSE/SELECT.

---

## 2. Текущее состояние register-first (факт, 9 записей)

Источник: `python -m core_02.missing_registry list --json` (data_13/missing_registry.yaml).

| item_id | status | kind | factory | prompt_path |
|---------|--------|------|---------|-------------|
| conformance_checker | registered | tool | governance | — |
| decision_registry | registered | registry | decision | — |
| **factory_registry** | **design_ready** | registry | — | `docs_10/engineering-memory/FORGE_PASSPORT_CODE_REPRESENTATION_V1.md` |
| lisa_estimator | ✅ implemented | tool | research | `pompts_11/076_13_lisa_estimator_capability.md` |
| model_diagram_autogen | registered | tool | modeling | — |
| **opportunity_engine** | **prompt_written** | engine | content | `pompts_11/079_19_opportunity_engine_capability.md` |
| research_web | ✅ implemented | tool | research | `pompts_11/075_04_research_web_capability.md` |
| scenario_engine | design_ready | system | — | `docs_10/engineering-memory/SCENARIO_ENGINE_DESIGN_V1.md` |
| **whim_capture** | **registered** | module | content | — |

**Ключевые наблюдения (evidence):**

1. **`opportunity_engine` на шаге 2** (`prompt_written`) — промт `079_19_opportunity_engine_capability.md` («ПРОМТ 78») готов и покрывает §J: DISCOVER → LIFECYCLE → PROPOSE → SELECT (ScenarioRegistry) → EXECUTE (ForgeFacade.run_chain) → VALIDATE (RoleArtifactValidator) → ACCUMULATE (memory_store). **Первый кандидат на реализацию.**
2. **`whim_capture` на шаге 1** (`registered`) — промта нет. Нужен новый `pompts_11/080_19_whim_capture_capability.md` (следующий номер по конвенции: 078_19 → 079_19 → 080_19).
3. **`factory_registry` на шаге 1.5** (`design_ready`) — промт **уже существует** (`078_19_factory_registry.md`), но **в реестре не помечен `prompt_written`** → рассинхрон (промт на диске, статус в реестре отстаёт). Исправление: `mark-prompt-written factory_registry --prompt pompts_11/078_19_factory_registry.md`.

---

## 3. Фаза 1 — First Vertical Slice (§J): Whim → Opportunity → Artifact

### 3.1 Цель

Полный цикл «signal → opportunity → scenario → artifact → memory» (критерий §J) на существующем G0-хвосте:

```
Whim (вход) → opportunity_engine.DISCOVER → LIFECYCLE (ACTIVE/DEFERRED/READY)
    → PROPOSE → SELECT (ScenarioRegistry) → EXECUTE (ForgeFacade.run_chain, 14 ролей)
    → VALIDATE (RoleArtifactValidator) → ACCUMULATE (memory_store) → COMPLETED
```

### 3.2 Шаги и register-first переходы

| Шаг | Действие | register-first | Результат |
|-----|----------|----------------|-----------|
| **1.1** | Реализовать `opportunity_engine` по `pompts_11/079_19_opportunity_engine_capability.md` (ПРОМТ 78): `scripts_01/opportunity_engine.py` + `tests_09/test_opportunity_engine.py` + `data_13/opportunities.yaml` | `opportunity_engine`: prompt_written → **implemented** | Рабочий engine: discover/propose/select/run/status/list, lifecycle, fail-safe |
| **1.2** | Написать промт `whim_capture` → `pompts_11/080_19_whim_capture_capability.md` (заголовок «ПРОМТ 79» — конвенция файл NNN → ПРОМТ NNN−1; вход: мысль; хранение: `data_13/whims.yaml`; интеграция: event_bus + project_pulse) | `whim_capture`: registered → **prompt_written** | Промт на реализацию |
| **1.3** | Реализовать `whim_capture` по промту 080_19: лёгкий захват мысли, `DEFERRED ≠ DELETED`, шлёт сигнал в `opportunity_engine` | `whim_capture`: prompt_written → **implemented** | Модуль входа |
| **1.4** | e2e-прогон §J: `whim_capture` → `opportunity_engine run` → артефакт + memory_store + COMPLETED | — | Срез подтверждён |

### 3.3 Критерии приёмки Фазы 1 (суммарно по §J)

- [ ***REMOVED*** `whim_capture "мысль"` фиксирует whim (YAML), статус READY, повторная фиксация не теряет запись;
- [ ***REMOVED*** `opportunity_engine discover` находит кандидатов (в т.ч. из зафиксированного whim) — пустые источники → degraded `discovered: 0`, exit 0;
- [ ***REMOVED*** `opportunity_engine propose <id>` → предложение со сценарием-кандидатом через `ScenarioRegistry.find_role`/`propose_roles`;
- [ ***REMOVED*** `opportunity_engine run <id>` (не dry-run) → `ForgeFacade.run_chain` (14 ролей) → `RoleArtifactValidator` → `memory_store` → статус `COMPLETED`;
- [ ***REMOVED*** Lifecycle: ACTIVE → DEFERRED → REACTIVATED → READY → COMPLETED работает, DEFERRED не стирается;
- [ ***REMOVED*** `--json` возвращает валидный JSON; `pytest tests_09/test_opportunity_engine.py` + `test_whim_capture.py` зелёные; mypy чистый;
- [ ***REMOVED*** `KNOWN_CAPABILITIES`/`ModelCatalog` **не изменены** (closed vocabulary, ANTI-6b) — drift-тест `test_known_capabilities_subset_of_actual_catalog` зелёный.

---

## 4. Фаза 2 — Factory Registry (Missing #1, G2)

### 4.1 Цель

Машиночитаемые паспорта кузен (ForgePassport) по дизайну `FORGE_PASSPORT_CODE_REPRESENTATION_V1.md` — регистровый фундамент для масштабирования CI-слоя (opportunity → резолвинг правильной Factory/Forge по паспорту).

### 4.2 Шаги

| Шаг | Действие | register-first | Результат |
|-----|----------|----------------|-----------|
| **2.1** | **Исправить рассинхрон реестра:** `python -m core_02.missing_registry mark-prompt-written factory_registry --prompt pompts_11/078_19_factory_registry.md` (промт уже на диске; дизайн-документ `FORGE_PASSPORT_CODE_REPRESENTATION_V1.md` остаётся источником дизайна — §20 #1 карты продолжает на него ссылаться, ссылка не теряется) | `factory_registry`: design_ready → **prompt_written** | Реестр догоняет диск |
| **2.2** | Реализовать Factory Registry по `pompts_11/078_19_factory_registry.md`: реестр фабрик + паспортов (по образцу `ScenarioRegistry`), YAML-манифесты `runtime_05/factories/`, НЕ модифицировать `scenario.py` (CAN-16 ADDITIVE) | `factory_registry`: prompt_written → **implemented** | Реестр фабрик/кузен |
| **2.3** | (Опционально) подключить FactoryRegistry как резолвер в `opportunity_engine.PROPOSE` — выбор Factory/Forge по паспорту вместо только ScenarioRegistry | — | Улучшение выбора, не блокер §J |

### 4.3 Критерии приёмки Фазы 2

- [ ***REMOVED*** `factory_registry` в реестре на статусе `implemented`; §20 карты #1 → «✅ реализовано»;
- [ ***REMOVED*** Паспорта кузен (7 кузен Architecture Factory + предварительные Research/Code/Content) машиночитаемы (YAML/dataclass `ForgePassport`);
- [ ***REMOVED*** `python -m core_02.missing_registry check` → ok; `pytest tests_09/test_factory_registry.py` зелёные;
- [ ***REMOVED*** Существующие модули (`scenario.py`, `scenario_registry.py`) **не модифицированы** (additive).

---

## 5. Фаза 3 — Scenario Engine (Missing #2, вне §I)

| Аспект | Деталь |
|--------|--------|
| Статус | `design_ready` (SCENARIO_ENGINE_DESIGN_V1.md: ScenarioRun state machine, CapabilityRef §6.1, Vocabulary Validator, closed dictionary) |
| Роль | Оркестратор-композитор: заменяет прямой вызов ScenarioRegistry в `opportunity_engine.SELECT` на `ScenarioEngine.resolve(CapabilityRef)` |
| Когда | После Фаз 1–2; **не блокирует** вертикальный срез §J (в §J SELECT идёт через G0 ScenarioRegistry напрямую) |
| Зависимость входа | `opportunity_engine` проектировать так, чтобы `SELECT` был за интерфейсом (легко подменить на ScenarioEngine позже) — **требование этого плана** |
| Промт | Будет написан на этапе Фазы 3 (номер 08X_19) |

**Ключевое требование к Фазе 1 (анти-переписывание):** в `opportunity_engine` SELECT вынести за интерфейс (функция/резолвер `select_scenario()`), чтобы в Фазе 3 подключить ScenarioEngine без изменения остального кода (additive, CAN-16).

---

## 6. Зависимости от Missing Capability #1/#2 (сводно)

| Зависимость | Блокирует? | Обоснование (evidence) |
|-------------|-----------|------------------------|
| **Missing #1 (FactoryRegistry)** → Opportunity Engine | ❌ НЕ блокирует Фазу 1 | §J-срез использует G0 `ScenarioRegistry`/`ForgeFacade` напрямую; FactoryRegistry — улучшение выбора (Фаза 2) |
| **Missing #1 (FactoryRegistry)** → Whim capture | ❌ НЕ блокирует | whim_capture — автономный модуль входа |
| **Missing #2 (Scenario Engine)** → Opportunity Engine | ❌ НЕ блокирует Фазу 1 | §J SELECT — через существующий ScenarioRegistry; ScenarioEngine — будущая замена за интерфейсом |
| **Opportunity Engine** → Whim capture | ⚠️ Функционально, не по сборке | Срез §J работает от обоих входов (whim ИЛИ project_pulse/knowledge); whim_capture — удобный вход, но opportunity_engine принимает готовый сигнал и без него (промт 079_19 §3.1.1) |
| **FactoryRegistry** → существующие реестры | ❌ | Аддитивный, по образцу ForgeRegistry/ScenarioRegistry (промт 078_19) |

---

## 7. Соответствие фазировке §21 карты v1.1

Карта §21: 1) Architecture Review Forge → 2) Governance Forge → 3) каркас Factory → 4) Code Factory → 5) Scenario Engine → 6) Factory Registry.

**Позиция этого плана:** CI-слой (§I) — **параллельный трек**, а не шаг §21. Он строится аддитивно поверх G0 и не ждёт полной последовательности §21. Пересечение: `factory_registry` (Фаза 2 здесь) ≈ шаг 6 §21 — но здесь он **раньше**, потому что нужен как фундамент резолвинга для CI-слоя; `scenario_engine` (Фаза 3 здесь) ≈ шаг 5 §21 — синхронизирован.

---

## 8. Валидация (для каждой фазы)

```bash
# Реестр и дрейф
python -m core_02.missing_registry check
python -m pytest tests_09/test_consistency_check.py::TestRealWorkspaceConsistent -q
python -c "import sys; sys.path.insert(0,'.'); ***REMOVED***; from scripts_01.consistency_check import build_report; r=build_report(Path('.')); print('TOTAL', r['total_issues'***REMOVED***, 'CONSISTENT', r['consistent'***REMOVED***)"

# Целевые тесты фазы
python -m pytest tests_09/test_opportunity_engine.py tests_09/test_whim_capture.py -q   # Фаза 1
python -m pytest tests_09/test_factory_registry.py -q                                   # Фаза 2
python -m mypy scripts_01/opportunity_engine.py scripts_01/whim_capture.py --ignore-missing-imports
```

**Ожидание:** `check` → ok; `TestRealWorkspaceConsistent` → 1 passed; `build_report` → TOTAL 0, CONSISTENT True.

---

## 9. Чек-лист закрытия

- [ ***REMOVED*** §20 карты v1.1: #8 `opportunity_engine` → «✅ реализовано»; #9 `whim_capture` → «✅ реализовано»; #1 `factory_registry` → «✅ реализовано»;
- [ ***REMOVED*** `data_13/missing_registry.yaml`: все три на `implemented`;
- [ ***REMOVED*** Промты: 078_19 (есть), 079_19 (есть), 080_19 (создать);
- [ ***REMOVED*** `KNOWN_CAPABILITIES`/`ModelCatalog` не расширены (closed vocabulary);
- [ ***REMOVED*** e2e §J-срез подтверждён: whim → артефакт → memory → COMPLETED;
- [ ***REMOVED*** build_report TOTAL 0, CONSISTENT True; ревью code-reviewer-glm.

---

## 10. Связные документы

- `docs_10/engineering-memory/FORENSICS_CI_REPORT_V1.md` — §I (модель), §J (срез), §K (readiness);
- `docs_10/engineering-memory/FORENSICS_CI_GAP_MAP_V1.md` — G0–G4 карта, §6 (register-first кандидаты);
- `docs_10/engineering-memory/ARB_REVIEW_PLATFORM_FORENSICS_PROMPT_V1.md` — ARB-REV-004, RA2;
- `docs_10/engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md` — §20 (Missing Capabilities #1/#2/#8/#9), §21 (фазировка);
- `docs_10/engineering-memory/SCENARIO_ENGINE_DESIGN_V1.md` — дизайн Scenario Engine (Missing #2);
- `docs_10/engineering-memory/FORGE_PASSPORT_CODE_REPRESENTATION_V1.md` — дизайн FactoryRegistry (Missing #1);
- `pompts_11/078_19_factory_registry.md`, `pompts_11/079_19_opportunity_engine_capability.md` — промты;
- `core_02/missing_registry.py` — register-first реестр (AGENTS.md §5).

---

*План реализации Minimal CI Layer (§I FORENSICS_CI_REPORT_V1.md) в порядке register-first. Фаза 1 (opportunity_engine + whim_capture) — первый вертикальный срез §J; Фаза 2 (factory_registry) — регистровый фундамент; Фаза 3 (scenario_engine) — будущий оркестратор, не блокирует срез.*
