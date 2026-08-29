# ADR-018: Factory→Forge execution bridge — официальный контракт (BaseFactory.execute → select_forge → ForgeFacade)

> **Статус:** Proposed (дизайн зафиксирован; реализация — отдельный заход)
> **Дата:** 2026-08-22
> **Связанные:** ADR-013 (ForgeFacade Blueprint v3 bridge), ADR-017 (единая Workspace модель), ARCHITECTURAL_BASELINE_V1.md §1/§4, CON-19 (single-source-of-truth), §7.3 (Wizard↔Forge boundary), CON-16 (additive).

## Context

Forensic-проходы 104/105/106/107 изначально классифицировали Path B (`Opportunity → capability → FactoryRegistry.select_forge → ForgePassport`) как **PARTIAL** — «селекция есть, execution-мост к ForgeFacade не сшит». Верификация кодом (2026-08-22, зафиксирована в `EVIDENCE_LEDGER_MERGED.md` и `ARCHITECTURAL_BASELINE_V1.md`) **опровергла это**: мост СШИТ и существует в ТРЁХ независимых точках:

| Точка | Файл:строка | Поведение |
|-------|-------------|-----------|
| Opportunity Engine | `scripts_01/opportunity_engine.py:941` | `execute()`: `_select_factory_forge` → `select_forge(capability)` → запись `provenance['factory_selection'***REMOVED***` → `facade.run_chain(project, role_ids)` |
| BaseFactory | `core_02/factory_base.py:361` | `execute()`: `resolve()` → `select_forge` → `build_execution_request` → `facade.run_chain(project, role_ids=request.role_ids, project_read_only=True)` |
| chain-CLI | `scripts_01/forge.py:490` | `cmd_chain`: `facade.run_chain(...)` |

Проблема НЕ в отсутствии моста, а в том, что:
1. Контракт не зафиксирован официально (нет единого документа «как Factory отдаёт работу Forge»).
2. `forge_id` из паспорта — **адвизорный** (traceability в `provenance['factory_selection'***REMOVED***`), исполнение идёт по `role_ids` сценария; это не документировано и читается как «дыра».
3. Маппинг `forge_id → роль/executor` не покрыт тестами — риск дрейфа при добавлении новых фабрик.

## Decision

Зафиксировать **официальный контракт Factory→Forge** без изменения поведения (текущий код уже ему соответствует):

### 1. Канонический execution-path

```python
BaseFactory.execute(opp, *, dry_run, project_root, event_bus)
  → capability = _derive_capability(opp)                 # provenance.capability → scenario.capability → None
  → (FactoryPassport, ForgePassport) = FactoryRegistry.select_forge(capability)
  → ExecutionRequest(opportunity_id, project_id, capability,
                     factory_id, forge_id, role_ids, inputs, output_spec)
  → Project = _resolve_project(opp, project_root)         # Project.load(root)
  → ChainRun = ForgeFacade.run_chain(project, role_ids=request.role_ids,
                                     project_read_only=True)
  → artifact = normalize_output(run, opp, request)        # ChainRun → dict
  → _accumulate(opp, artifact, run, event_bus)            # MemoryStore kind=candidate + LearningLoop
```

### 2. Семантика полей (обязательная)

- **capability** — закрытый токен из KNOWN_CAPABILITIES (ANTI-6b); `None` → fail-safe fallback (не краш).
- **factory_id / forge_id** — из паспорта, **адвизорные**: пишутся в `provenance['factory_selection'***REMOVED***` и в artifact (traceability), НО не управляют исполнением напрямую.
- **role_ids** — из `ExecutionRequest.role_ids` (= `cls.ROLE_IDS` для BaseFactory, либо `opp.roles` для Opportunity Engine) — **единственный управляющий вход** в `run_chain`.
- **project_read_only=True** — Forge не мутирует артефакты Project (B2 R-124), только проверяет/производит.

### 3. Контракт маппинга (для тестов)

`forge_id` из паспорта обязан соответствовать одной из ролей/исполнителей, которых умеет исполнять `ForgeFacade.run_chain`:
- Маппинг: **passport.forge_id → разрешённый набор role_ids** (валидируется на стадии `build_execution_request`; при несоответствии — warn в `_import_warnings`/`provenance`, НЕ исключение — fail-safe).
- Гарантия единственной точки исполнения: `ForgeFacade` — единственный санкционированный мост (grep-инвариант §7.3: ни Scenario, ни роли НЕ вызывают ForgePipeline напрямую).

### 4. Тесты маппинга (реализация — отдельный заход)

В `tests_09/` добавить hermetic тесты (fixture-стиль, как `test_devil_advocate_pass_integration.py`):
- `test_execute_resolves_capability_to_factory_forge_pair` — fake FactoryRegistry возвращает паспорта; assert request.factory_id/forge_id.
- `test_execute_passes_role_ids_to_run_chain` — fake ForgeFacade перехватывает вызов; assert role_ids = ROLE_IDS.
- `test_execute_records_factory_selection_provenance` — после execute provenance['factory_selection'***REMOVED*** содержит factory_id/forge_id/capability.
- `test_execute_fallback_when_capability_absent` — без capability → fallback (не краш, provenance['factory_selection'***REMOVED***.fallback=True).
- `test_forge_id_advisory_not_driving_execution` — разные forge_id при тех же role_ids → run_chain вызывается с одинаковыми role_ids.
- `test_execute_dry_run_no_run_chain` — dry_run=True → run_chain НЕ вызывается, request в payload.

## Alternatives

- **(а) «Построить недостающий мост»** (прежний план по forensic-выводу PARTIAL) — отвергнуто: мост уже существует в трёх точках; «постройка» создала бы четвёртую, нарушив B-Rule 2 (граница = терпимость к отсутствию) и B-Rule 3 (разный lifecycle: эфемерная Opportunity vs долгоживущий Factory-адаптер).
- **(б) Слить Opportunity Engine и BaseFactory в единый execution-path** — отвергнуто: разные потребители (runtime-loop vs CLI/доменный адаптер); слияние ломает BC.
- **(в) Сделать forge_id управляющим** (передавать в run_chain) — отвергнуто: в системе единый ForgeFacade/ForgePipeline; физического выбора кузни нет; управление идёт через role_ids (существующая семантика).
- **(г) Зафиксировать существующий мост как официальный контракт + тесты маппинга** — **ВЫБРАНО**: нулевое изменение поведения, закрывает неопределённость «дыра vs не-дыра», тесты защищают от дрейфа.

## Trade-offs

- **Выигрываем:** официальный контракт (архитектор больше не читает «дыру»); тесты маппинга защищают от дрейфа при новых фабриках; traceability factory_selection фиксируется; нулевой риск регрессий (код не меняется).
- **Теряем:** адвизорный forge_id остаётся неочевидным (митигировано: явная секция «Семантика полей» + тест `test_forge_id_advisory_not_driving_execution`); три точки входа остаются (митигировано: этот ADR — их официальный манифест).

## Consequences

- **Реализация (отдельный заход, после утверждения):** только тесты маппинга (6 hermetic-тестов) + документирование семантики в docstring `BaseFactory.execute`/`opportunity_engine.execute` (адвизорный forge_id). Код исполнения НЕ меняется.
- **Документация:** `ARCHITECTURAL_BASELINE_V1.md` §4 строка «Factory→Forge execution-мост» — «✅ ЗАКРЫТ (Path B REAL), контракт фиксирует ADR-018».
- **Реестры:** DECISIONS.md + DOCUMENT_REGISTRY.md + CHANGELOG.
- **Backward compatibility:** полная — контракт описывает существующее поведение.
