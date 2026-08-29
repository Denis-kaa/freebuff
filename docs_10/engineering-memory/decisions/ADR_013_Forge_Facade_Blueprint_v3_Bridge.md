# ADR_013: ForgeFacade — явный мост Blueprint v3 → Forge (закрытие §7.6 gap 2)

**Status:** Accepted (Proposed 2026-08-10, encoded v5.145.0 — решение вступило в силу с ForgeFacade-кодом; ADR-файл создан в документационном слое v5.146.0)
**Component:** `core_02/forge_facade.py` — bridge layer между Blueprint v3 (17 ролей) и Forge Pipeline (L-4)
**Deciders:** Buffy (autonomous, per CORE_PROMPT §3), User (operator)
**Supersedes:** N/A (закрывает открытый gap §7.6 п.2 «No direct Forge invocation» — см. `WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md`)
**Related:** [WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md §7.3/§7.6***REMOVED***(../WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md), [pompts_11/071_02_prompt_architect_1_7.md***REMOVED***(../../../pompts_11/071_02_prompt_architect_1_7.md) Миссия 2, ADR-012 (identity), [P3_FORGE_FACADE_DESIGN.md***REMOVED***(../P3_FORGE_FACADE_DESIGN.md), [P3_BLUEPRINT_FORGE_FACADE_RESEARCH.md***REMOVED***(../P3_BLUEPRINT_FORGE_FACADE_RESEARCH.md)

---

## 1. Context

`WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md` §7 эмпирически верифицировал Hypothesis C: **Scenario и Forge Pipeline — ортогональные state-домены**, не последовательность. §7.3: *«Direct Forge call из Scenario — НЕТ (по дизайну)... Scenario НЕ вызывает Forge напрямую — только через Project/Facade»*. Доказано на 2 реальных инстансах (vkusvill_demo, interior_planner) — оба работают при UNFORGED.

Одновременно §7.6 зафиксировал открытый gap п.2: **«No direct Forge invocation — Scenario не может вызывать ForgePipeline напрямую»**. Blueprint v3 — набор из 17 статичных ролей (registry.yaml, routing_hint → SmartRouter), которые декларативно образуют pipeline (15/17 — производственные стадии с dependencies+outputs), но цепочка **не исполняется**: `resolve_pipeline()` вызывается только из тестов, `wizard.py` выбирает одну роль, grep `forge` в scenario/wizard → 0.

Задача 071_02_prompt_architect_1_7 Миссия 2 — закрыть gap: построить явный, управляемый Facade, через который роли могут по желанию инициировать Forge-прогон, оставаясь архитектурно отдельным доменом состояния.

## 2. Decision

Создан **ForgeFacade** (`core_02/forge_facade.py`) — единственная санкционированная точка входа «роль → Forge-прогон»:

1. **§7.3 boundary сохранён:** `ForgePipeline` импортируется ТОЛЬКО в `forge_facade.py`; `scenario_registry.py`/`wizard_lib.py` не тронуты (0 новых импортов; grep-инвариант закреплён тестами).
2. **Явный opt-in переход:** `initiate_forge(project, requested_by_role)` — не вызывается автоматически, требует роль; результат `ForgeFacadeResult.initiated_explicitly=True` (фиксация «не молча»).
3. **Gate:** `can_initiate(role_id)` — только **14 pipeline-ролей** (12 ядро + frontend + devops). Справочные роли (orchestrator, context_keeper) и presale-трек (response_writer) — вне scope → `ValueError`.
4. **UNFORGED-семантика не меняется:** статус вычисляет `forge_registry.record_run()` (та же логика, что `scripts_01/forge.py:151`); Facade лишь даёт путь его изменить через явный вызов.
5. **Пропорционально находке (Задача 0):** 14 ролей, показавших pipeline-природу, а не все 17.

## 3. Альтернативы, которые рассматривались

1. **Прямой вызов ForgePipeline из Scenario/ролей** — **rejected**. Прямое нарушение §7.3 (верифицированный boundary, стоил времени в прошлом — Forge/Scenario слияние).
2. **Автоматический запуск Forge после завершения роли** — **rejected**. «Не автоматически, не молча» (требование 071_02_prompt_architect_1_7 Задача 1 п.2): скрытый CI-прогон ломает ортогональность и UNFORGED-семантику.
3. **ForgeFacade (принято)** — явный фасад с gate + opt-in + record_run; единственная новая связь между доменами.
4. **Переименовать 17 ролей в «кузни»** — **rejected** (граница промт 70 «НЕ делать»): терминология сама по себе не делает роль производственной стадией.

## 4. Consequences

### Положительные
- §7.6 gap 2 закрыт без нарушения §7.3: роли получили легальный, явный путь к Forge.
- UNFORGED-статус остаётся честным индикатором (не «зрелость», а «прошёл CI»).
- Узкий scope (14 ролей) — расширение пропорционально находке, не тотальное.
- Тестируемость: gate-тесты, explicit-инициация, record_run-история, grep-инвариант §7.3 (12 тестов, 126 в регрессии P3-набора).

### Отрицательные / риски
- Facade — единственная точка входа: любой будущий код, которому нужен Forge, обязан идти через неё (дисциплина, не техника).
- response_writer (presale-трек) вне scope — если presale-конвейер понадобится, потребуется расширение (отдельное решение).
- Слагификация project_id (`web_app` → `web-app` через `_slug()`) — вызывает путаницу при хардкоде имён; документировано в тестах.

## 5. Implementation notes (v5.145.0)

- `core_02/forge_facade.py`: `PIPELINE_ROLES` (14) · `PIPELINE_CHAIN` (порядок) · `REFERENCE_ROLES` · `ForgeFacadeResult` (frozen dataclass) · `ForgeFacade` (`can_initiate` / `initiate_forge` / `get_status`).
- `tests_09/test_forge_facade.py`: 12 тестов (включая §7.3 grep-инвариант).
- Регрессия: `test_forge_facade + test_scenario_registry + test_forge_pipeline + test_blueprint_v3 + test_workspace + test_wizard` = **126 passed**.
- Ревью-цикл: исправлены 2 бага — недосчёт 15 vs 14 ролей (response_writer исключён из Facade-scope); `_slug()` в get_status-тесте.
