# ПРОМТ 78: РЕАЛИЗАЦИЯ Opportunity Engine (`opportunity_engine`, первый vertical slice CI)

> **Статус:** 🏗 ПРОМТ НА РЕАЛИЗАЦИЮ (Missing Capability #8, зарегистрирован в §20 карты v1.1 + data_13/missing_registry.yaml, G3 по FORENSICS_CI_REPORT_V1.md §I/§J)
> **Дата:** 2026-08-12
> **Источник:** FORENSICS_CI_REPORT_V1.md (§I Minimal Integration Model, §J First Vertical Slice — Whim → Opportunity → SELECT → EXECUTE → VALIDATE → ACCUMULATE), FORENSICS_CI_GAP_MAP_V1.md (G3: Opportunity Engine — DISCOVER + lifecycle + PROPOSE), ARB-REV-004 (RA2: маппинг G0–G4 на словарь платформы + register-first), FACTORY_FORGE_ARCHITECTURE_V1.md (§20 #8, §14 Scenario-композитор, §13 Cross-Factory Composition), SCENARIO_ENGINE_DESIGN_V1.md (§6 CapabilityRef, §13.2 сценарий «Создать продукт»)
> **Нумерация:** файл 079_19 → «ПРОМТ 78» (конвенция: файл NNN → заголовок ПРОМТ NNN−1, как 075_04→ПРОМТ 74, 076_13→ПРОМТ 75)
> **Принцип (register-first, RA2 ARB-REV-004):** недостающая capability — НЕ «несуществующий токен», а способность, которую нужно **построить**. Этот документ — шаг 2 цикла (registered → prompt_written → implemented). `opportunity_engine` уже зарегистрирован (kind=engine, factory=content) — этот промт переводит его в `prompt_written`.

---

## 1. Задача

Реализовать **`opportunity_engine`** — engine **Intelligence-слоя Content Intelligence (CI)**: первый вертикальный срез из §J FORENSICS_CI_REPORT_V1.md.

**Execution Path (§J):**

```
Whim-сигнал ИЛИ тема из project_pulse/knowledge
    ↓
OPPORTUNITY ENGINE (ЭТА РЕАЛИЗАЦИЯ)
    ├── DISCOVER   — сканирование источников (project_pulse / event_bus / knowledge_engine)
    ├── LIFECYCLE  — ACTIVE / DEFERRED / READY / REACTIVATED (→ COMPLETED)
    ├── PROPOSE    — формирование предложения (тема + тип + сценарий-кандидат)
    ├── SELECT     — через ScenarioRegistry (find_role / propose_roles) → выбрать сценарий
    └── EXECUTE    — через ForgeFacade.run_chain (14 ролей) → артефакт
                        ↓
                    VALIDATE (RoleArtifactValidator) → ACCUMULATE (memory_store)
```

**Результат:** Content-артефакт (статья/пост/план) + запись в `memory_store` + статус opportunity `COMPLETED`. Полный цикл «signal → opportunity → scenario → artifact → memory» работает **read-only на существующем «хвосте»** (ScenarioRegistry/ForgeFacade/memory_store — G0), новых сущностей на «голове» — **одна** (opportunity_engine).

**Что НЕ делаем в этой реализации:** не реализуем `whim_capture` (это отдельный модуль, Missing #9 — промт пойдёт следом), не реализуем FactoryRegistry (Missing #1), не создаём Content Factory целиком, не переписываем ScenarioRegistry/ForgeFacade (G0 — используем как есть).

---

## 2. Контекст и место в архитектуре

```
Content Factory (v1.1 §12, будущая) → Intelligence-слой CI (промт 1 content_factory)
└── Opportunity Engine (engine, G3)      ← ЭТА РЕАЛИЗАЦИЯ
        ├── DISCOVER-источники (G0): project_pulse / event_bus / knowledge_engine
        ├── SELECT (G0): ScenarioRegistry (list_scenarios / find_role / propose_roles)
        ├── EXECUTE (G0): ForgeFacade.run_chain (PIPELINE_CHAIN, 14 ролей)
        ├── VALIDATE (G0): RoleArtifactValidator (в ForgeFacade)
        └── ACCUMULATE (G0): memory_store / learning_loop
```

**Маппинг на существующий код:**

| Что | Где | Статус |
|-----|-----|--------|
| Capability-контракт | CapabilityRef `{kind: engine, engine: opportunity_engine, factory: content***REMOVED***` (SCENARIO_ENGINE_DESIGN §6) | проектируется в этом промте |
| DISCOVER-источники | `scripts_01/project_pulse.py`, `scripts_01/event_bus.py`, `core_02/knowledge_engine.py` | G0 (CONFIRMED) |
| SELECT-сценария | `core_02/scenario_registry.py` — `list_scenarios()`, `find_role()`, `propose_roles()` (fuzzy `wizard_lib.score_role_match`) | G0 (CONFIRMED) |
| EXECUTE-конвейера | `core_02/forge_facade.py` — `ForgeFacade.run_chain(project_id, role_ids=PIPELINE_CHAIN)` (14 ролей) | G0 (CONFIRMED) — **единственный мост** (B-rule §7.3: Direct Forge call из сценария — НЕТ) |
| VALIDATE-артефактов | `RoleArtifactValidator` (в `forge_facade.py`) + `drift_check.py`/`consistency_check.py` | G0 (CONFIRMED) |
| ACCUMULATE-памяти | `core_02/memory_store.py` (`store_knowledge`), `scripts_01/learning_loop.py` (`record_learning_event`) | G0 (CONFIRMED) |
| Register-first | `core_02/missing_registry.py` — запись `opportunity_engine` (kind=engine, factory=content, §20 #8) | **registered** → этот промт → `prompt_written` |

**Закрытый словарь (ANTI-6b/CON-8):** `opportunity_engine` — имя **Engine** (разрешение `kind: engine` → Engine Registry будущего Scenario Engine), НЕ модель-капабилити. В `KNOWN_CAPABILITIES` (`core_02/blueprint_v3.py`) НЕ добавляем — туда идут только genuine capability-токены, реально существующие в `ModelCatalog` (иначе drift-тест `test_known_capabilities_subset_of_actual_catalog` упадёт — это фича, не баг).

---

## 3. Требования к реализации

### 3.1 Функциональные

1. **Вход:** Whim-сигнал (текст мысли) ИЛИ тема, обнаруженная из `project_pulse`/`knowledge_engine` (CLI-аргумент или stdin);
2. **DISCOVER:** сканирование G0-источников → список кандидатов-opportunities (поля: `id`, `title`, `description`, `source` (whim/project_pulse/event_bus/knowledge), `evidence_path`, `priority`);
3. **LIFECYCLE:** состояние opportunity — `ACTIVE` (в работе) / `DEFERRED` (отложено, **≠ удалено**) / `READY` (готово к запуску) / `REACTIVATED` (возвращено из DEFERRED) → `COMPLETED` (после успешного цикла); персистентность — YAML (`data_13/opportunities.yaml`);
4. **PROPOSE:** формирование предложения (тема, тип контента, сценарий-кандидат);
5. **SELECT:** через `ScenarioRegistry.find_role` / `propose_roles` по тексту opportunity → выбор сценария/роли (default-сценарий при пустом результате: «Создать продукт» — `forge chain` 14 ролей);
6. **EXECUTE:** `ForgeFacade.run_chain` с артефактами opportunity (строго через фасад, не напрямую);
7. **VALIDATE:** `RoleArtifactValidator` проверяет артефакты → при провале opportunity → статус `FAILED` + retry-флаг;
8. **ACCUMULATE:** успешный цикл → запись в `memory_store` (результат/артефакт) + learning event + opportunity → `COMPLETED`.

### 3.2 Режимы CLI

- `opportunity_engine discover` — сканировать источники → кандидаты (YAML);
- `opportunity_engine propose <opportunity_id>` — сформировать предложение (SELECT через ScenarioRegistry);
- `opportunity_engine run <opportunity_id> [--dry-run***REMOVED***` — полный цикл PROPOSE → SELECT → EXECUTE → VALIDATE → ACCUMULATE; `--dry-run` — только план (не исполнять);
- `opportunity_engine status <opportunity_id>` — показать lifecycle-состояние;
- `opportunity_engine list [--status ACTIVE|DEFERRED|READY|COMPLETED***REMOVED***` — список;
- `opportunity_engine --json` — stdout JSON (для Scenario Engine / API).

### 3.3 Архитектурные (обязательные, не нарушать)

1. **ADDITIVE (CAN-16):** новый модуль `scripts_01/opportunity_engine.py`; существующие G0-модули (ScenarioRegistry, ForgeFacade, project_pulse, event_bus, knowledge_engine, memory_store) **НЕ модифицируются** — только вызываются;
2. **Единственный мост (§7.3):** EXECUTE — только через `ForgeFacade.run_chain`. Прямых вызовов Forge из сценария/engine — НЕТ;
3. **Безопасность (security-стандарт проекта):** никаких `exec`/`eval`, НЕ `shell=True`, НЕ `os.system`; входные файлы читаются только (read-only); валидация типов; YAML-записи — через безопасный dumper;
4. **Fail-safe:** нет источников / нет входных данных / битый YAML → degraded-отчёт `discovered: 0` / `status: failed-safe`, exit 0 (паттерн research_web `sources_checked: 0`);
5. **Determinism:** DISCOVER/PROPOSE/SELECT — детерминированные (эвристики + score_role_match), пригодны для unit-тестов; LLM-синтез предложений — будущий этап (не блокирует v1);
6. **Observability:** каждый переход lifecycle + каждый вызов EXECUTE логируются (EventBus + Learning Loop best-effort, паттерн `_emit_events` из research_web);
7. **Закрытый словарь (ANTI-6b/CON-8):** `opportunity_engine` — имя Engine (Engine Registry, `kind: engine`), в `KNOWN_CAPABILITIES` НЕ добавляется (genuine-токен — отдельный, только если появится в `ModelCatalog`).

### 3.4 Изменения в существующем коде (минимальные, аддитивные)

| Файл | Изменение |
|------|-----------|
| `scripts_01/opportunity_engine.py` | **НОВЫЙ** — CLI + класс/функции: `discover()`, `propose()`, `run()`, lifecycle-машина, `select_scenario()` (через ScenarioRegistry), `execute()` (через ForgeFacade) |
| `data_13/opportunities.yaml` | **НОВЫЙ** — персистентность lifecycle (создаётся автоматически; seed-пустой при первом запуске) |
| Engine Registry (список Engines для Scenario Engine §7) | `opportunity_engine` регистрируется как Engine (path: `kind: engine`, factory: content) |
| `core_02/blueprint_v3.py` | **НЕ ТРОГАЕМ** — `KNOWN_CAPABILITIES` не меняется (нет genuine capability-токена) |
| `tests_09/test_opportunity_engine.py` | **НОВЫЙ** — unit-тесты: discover/проpose/select/run (dry-run), lifecycle-переходы (ACTIVE→DEFERRED→REACTIVATED→READY→COMPLETED), fail-safe (пустой вход), vocabulary-drift (имя engine НЕ в KNOWN_CAPABILITIES) |

### 3.5 Качество (Code Quality Standard 040_13)

- docstrings, обработка ошибок, валидация входных данных, детерминизм;
- тесты: `python -m pytest tests_09/test_opportunity_engine.py -q` зелёные;
- mypy: `python -m mypy scripts_01/opportunity_engine.py --ignore-missing-imports`.

---

## 4. Что НЕ является частью реализации (scope)

- ❌ **`whim_capture`** (Missing #9, отдельный модуль) — вход в opportunity_engine принимается готовым сигналом;
- ❌ **FactoryRegistry** (Missing #1) — паспорта кузен, отдельный промт;
- ❌ Content Factory целиком (каркас — следующий этап);
- ❌ модификация ScenarioRegistry / ForgeFacade / project_pulse / event_bus / knowledge_engine / memory_store (G0 — только вызовы);
- ❌ LLM-синтез текста предложений (детерминированные эвристики — достаточно для v1);
- ❌ авто-запуск по расписанию (cron/scheduler-интеграция — отдельный этап; v1 — только CLI-вызовы).

---

## 5. Проверка приёмки (Definition of Done)

1. [ ***REMOVED*** `python scripts_01/opportunity_engine.py discover` → создаёт `data_13/opportunities.yaml` с кандидатами (поля id/title/source/priority), при пустых источниках — degraded `discovered: 0`, exit 0;
2. [ ***REMOVED*** `python scripts_01/opportunity_engine.py propose <id>` → предложение со сценарием-кандидатом (SELECT через `ScenarioRegistry.find_role`/`propose_roles`);
3. [ ***REMOVED*** `python scripts_01/opportunity_engine.py run <id> --dry-run` → печатает план (сценарий + роли PIPELINE_CHAIN) без исполнения;
4. [ ***REMOVED*** `run <id>` (не-dry-run) выполняет цикл EXECUTE через `ForgeFacade.run_chain` → VALIDATE (`RoleArtifactValidator`) → ACCUMULATE (`memory_store`) → статус `COMPLETED`;
5. [ ***REMOVED*** Lifecycle-переходы работают: `ACTIVE → DEFERRED → REACTIVATED → READY → COMPLETED`, DEFERRED не теряет запись;
6. [ ***REMOVED*** `--json` возвращает валидный JSON (Schema: `{opportunity_id, status, scenario, roles[***REMOVED***, artifacts[***REMOVED***, degraded***REMOVED***`);
7. [ ***REMOVED*** `pytest tests_09/test_opportunity_engine.py` зелёные; mypy чистый;
8. [ ***REMOVED*** `opportunity_engine` зарегистрирован в **Engine Registry** (путь `kind: engine`, factory=content); `KNOWN_CAPABILITIES`/`ModelCatalog` НЕ изменены; drift-тест `test_known_capabilities_subset_of_actual_catalog` остаётся зелёным;
9. [ ***REMOVED*** MissingRegistry: `opportunity_engine` переведён в `implemented` (mark-implemented) после реализации;
10. [ ***REMOVED*** После реализации обновить §20 карты v1.1: #8 `opportunity_engine` из «зарегистрировано» → «✅ реализовано».

---

## 6. Связные документы

- `docs_10/engineering-memory/FORENSICS_CI_REPORT_V1.md` — §I (Minimal Integration Model), §J (First Vertical Slice), §D (primitives), §K (readiness);
- `docs_10/engineering-memory/FORENSICS_CI_GAP_MAP_V1.md` — G3 (Opportunity Engine, Whim), §6 (register-first кандидаты);
- `docs_10/engineering-memory/ARB_REVIEW_PLATFORM_FORENSICS_PROMPT_V1.md` — ARB-REV-004, RA2 (G0–G4 маппинг + register-first);
- `docs_10/engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md` — §12 (Content Factory), §13 (Cross-Factory Composition), §14 (Scenario-композитор), §20 (#8);
- `docs_10/engineering-memory/SCENARIO_ENGINE_DESIGN_V1.md` — §6 (CapabilityRef), §13.2 (сценарий «Создать продукт»: research → estimate → …);
- `core_02/scenario_registry.py`, `core_02/forge_facade.py`, `core_02/memory_store.py`, `core_02/missing_registry.py`;
- `scripts_01/project_pulse.py`, `scripts_01/event_bus.py`, `core_02/knowledge_engine.py`, `scripts_01/learning_loop.py`;
- `pompts_11/040_13_code_quality_standard.md` — обязательный регламент.

---

*Промт на реализацию Missing Capability #8 (Opportunity Engine, первый vertical slice CI по §J FORENSICS_CI_REPORT_V1.md). Статус: шаг 2 register-first цикла — после утверждения переводит `opportunity_engine` в `prompt_written`, после реализации — в `implemented`.*
