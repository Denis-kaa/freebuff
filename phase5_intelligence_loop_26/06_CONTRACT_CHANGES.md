# PHASE5 CONTRACT CHANGES — v5.189.16

> §6/§8/§10/§12: минимальные расширения контрактов; CAN-16 ADDITIVE; контракт = код.

---

## 1. Контракт DISCOVER (новые поля provenance)

Расширение: каждый `OpportunityCandidate` теперь несёт полный provenance (поля уже поддерживались структурой кандидата — реализованы, не изобретены):

| Поле | Тип | Значение |
|---|---|---|
| `source` | str | `whims` / `pulse` / `events` / `knowledge` / `stub` |
| `source_id` | str | id исходной записи (whim id / event id / pulse entry id / KO id) |
| `project_id` | str | проект, к которому привязан сигнал |
| `timestamp` | str | ISO-время обнаружения |
| `reason` | str | почему сигнал стал кандидатом |
| `evidence` | str | фактическое содержимое источника |
| `confidence` | float | из источника (если поддерживает) или 0.5 |
| `stub` | bool | `False` для реальных источников; `True` ТОЛЬКО в явном fallback |

## 2. Контракт `source_paths` (единый словарь ключей)

```python
source_paths = {
    "whims":  Path,   # ← --whim-path  (WhimStore YAML)
    "pulse":  Path,   # ← --pulse-db   (ProjectPulse SQLite)
    "events": Path,   # ← --event-db  (EventBus SQLite)
    "memory": Path,   # ← --memory-db (MemoryStore SQLite)
***REMOVED***
```

- Ключи совпадают с CLI-флагами (исправлен рассинхрон "memory"/"knowledge" — ревью round-1).
- Отсутствующий ключ → дефолтный путь из `_SOURCE_DEFAULTS`.
- Несуществующий файл → источник даёт 0 кандидатов (не ошибка).

## 3. Контракт ACCUMULATE (lineage)

```python
accumulate(opp, memory_store=None, learning_loop=None) -> Optional[str***REMOVED***  # knowledge_id
```

- **kind**: `"candidate"` — существующий kind из `KNOWLEDGE_KINDS` (CAN-16: добавление `opportunity` потребовало бы правки memory_store + теста `len==10`; решение: тег `opportunity` + kind `candidate`).
- **tags**: `["opportunity", project_id***REMOVED***` — фильтрация по тегу вместо нового kind.
- **lineage**: `opp.provenance["memory_knowledge_id"***REMOVED*** = knowledge_id` — связь Opportunity → Artifact → Memory entry (§10) БЕЗ отдельной БД для lineage.
- **learning**: `record_learning_event(kind="opportunity", outcome="success"|"failure")` + `LearningLoop.record_feedback(knowledge_id, outcome)`.

## 4. Контракт execute() (status normalization)

```python
execute(opp, *, dry_run=False, memory_store=None, learning_loop=None) -> Opportunity
```

- Вход: `ACTIVE` (свежий кандидат) или `FAILED` (retry) → нормализация в `READY` ДО run_chain.
- Выход: `COMPLETED` (успех + accumulate success) / `FAILED` (сбой + accumulate failure).
- `dry_run=True` (прежнее поведение, НЕ менялось в этой фазе): мутирует статус `ACTIVE → READY` (существующая семантика), ставит `provenance["dry_run"***REMOVED***=True`, НЕ вызывает run_chain и НЕ делает accumulate.

## 5. Существующие контракты — БЕЗ изменений

| Контракт | Статус |
|---|---|
| `KNOWLEDGE_KINDS` (10 kinds, тест `len==10`) | НЕ изменён |
| Opportunity lifecycle states (ACTIVE/DEFERRED/REACTIVATED/READY/COMPLETED/FAILED) | НЕ изменён (DEFERRED ≠ DELETED, §13) |
| ScenarioRegistry / Scenario manifests | НЕ изменён (§14) |
| FactoryRegistry / Passport | НЕ изменён (§15) |
| ForgeFacade (единственный point для Forge) | НЕ изменён; вызывается через lazy-import (§16) |
| EventBus / Memory / Knowledge engines | НЕ продублированы, только читаются |
| Opportunity Contract #15 (16 полей §E) | уже в CONTRACT_REGISTRY_V1 (v5.189.15) |
| Whim Contract #16 (§17.1) | уже в CONTRACT_REGISTRY_V1 (v5.189.15) |

## 6. Контракт CLI discover

```
python -m scripts_01.opportunity_engine discover --project PROJECT_ID
    [--whim-path PATH***REMOVED*** [--pulse-db PATH***REMOVED*** [--event-db PATH***REMOVED*** [--memory-db PATH***REMOVED***
    [--max-results N***REMOVED*** [--store PATH***REMOVED***
```

Флаги необязательны; без них — реальные дефолтные пути (не stub).
