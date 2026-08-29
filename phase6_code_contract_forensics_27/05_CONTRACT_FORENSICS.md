# 05_CONTRACT_FORENSICS — Контрактная форензика

> **Промт:** `pompts_11/087_19_phase6_code_contract_forensics.md` §7 (CONTRACT FORENSICS)
> **Метод:** сравнение документационных контрактов с реальными dataclass/schema. Каждое расхождение — зафиксировано.

---

## 1. Реестр контрактов (CONTRACT_REGISTRY_V1.md — 16 записей)

Все 16 контрактов имеют producer @entity (Artifact A) + тесты. Статусная карта:

| # | contract_id | Status | Примечание |
|---|---|---|---|
| 1 | forge.execution | CURRENT | 29 тестов, 4 пути |
| 2 | scenario.selection | **PARTIAL** | RoleNotFoundError не raised (возвращает None) |
| 3 | scenario.composition | CURRENT | |
| 4 | forge.lifecycle | CURRENT | FSM green |
| 5 | forge.run.record | CURRENT | |
| 6 | workspace.path_resolve | CURRENT | |
| 7 | memory.write | CURRENT | |
| 8 | memory.search | CURRENT | |
| 9 | knowledge.query | CURRENT | |
| 10 | graph.add_edge | CURRENT | |
| 11 | opportunity.discover | CURRENT | v5.187.7 |
| 12 | opportunity.execute | CURRENT | но events не emit (planned §J) |
| 13 | whim.promote | CURRENT | v5.187.8 |
| 14 | missing_registry.lifecycle | CURRENT | register-first |
| 15 | opportunity.schema | CURRENT | 24 поля (drift vs §E 15/16) |
| 16 | whim.schema | CURRENT | 21 поле |

**Итого:** 15 CURRENT / 1 PARTIAL (scenario.selection).

## 2. Документированный контракт vs реальный runtime object

### 2.1 Opportunity (§E vs dataclass) — CONFLICT (известный, §C.6 #5)

| §E design (15/16 полей) | Фактический dataclass (24 поля) |
|---|---|
| `signal` | `title` (нет signal) |
| `hypothesis` | — (нет) |
| `rationale` | `description` |
| `related_knowledge` | — (нет; provenance связан через memory_knowledge_id) |
| `selected_scenario` | `scenario: Optional[Dict***REMOVED***` |
| `resulting_artifact` | `artifacts: List[Dict***REMOVED***` |
| — | + `priority`, `roles`, `source_path`, `evidence_path`, `deferred_at/reason`, `previous_status`, `reactivated_at`, `completed_at`, `failed_at`, `failure_reason`, `related_decisions`, `related_whims` |

**Вердикт:** фактический dataclass **богаче** design-контракта. Design-поля signal/hypothesis/related_knowledge не существуют. Это НЕ блокер (документация отстала), но §C.6 #5 требует reconcile — зафиксировано как DECISION REQUIRED в 12_ARCHITECTURAL_CONFLICTS.

### 2.2 Whim (§17.1 vs dataclass) — CONFIRMED

`Whim` dataclass (21 поле) полностью покрывает §17.1 (NEW → TRIAGED → PROMOTED_TO_OPPORTUNITY/DISCARDED; DEFERRED ≠ DELETED). Статус CURRENT.

### 2.3 FactoryPassport (v5.189.21) — CONFIRMED

`core_02/factory_passport.py::FactoryPassport` — frozen dataclass, 7 полей (factory_id/display_name/version/status/description/capabilities/metadata), from_yaml/to_yaml/to_dict/validate, ANTI-6b vocab guard. Соответствует FACTORY_FORGE §3.

### 2.4 ForgePassport — CONFIRMED

`core_02/forge_passport.py::ForgePassport` — паспорт forge.yaml (зеркалит FactoryPassport).

## 3. Проверка по каждому контракту (схема/обязательные/дефолты/lifecycle/сериализация)

| Контракт | Schema | Required | Defaults | Lifecycle | Validation | Serialization | Storage | Callers |
|---|---|---|---|---|---|---|---|---|
| opportunity.schema | 24 поля dataclass | id/project_id/title/description/source | status=ACTIVE, priority=5 | 6 статусов, 8 переходов | `advance`+`_check_transition` | `to_dict` (asdict) | opportunities.yaml (atomic .tmp+replace) | whim.promote, forge.facade, CLI |
| whim.schema | 21 поле dataclass | id/project_id/body/source | status=NEW, priority=5 | 6 статусов | `advance`+`_check_transition` | `to_dict` | whims.yaml (atomic) | CLI, opportunity_engine |
| forge.lifecycle | ProjectRecord | project_id | status=UNFORGED | UNFORGED→FORGED→SHIPPED | `promote_status` FSM | YAML | forge_registry.yaml | forge.facade, forge.cli, forge.api |
| forge.run.record | RunRecord | slug+payload | — | append-only | `record_run` | YAML | forge_registry.yaml | forge.facade |
| memory.write | MemoryChunk | chunk_id+body+tags | version auto | version++ | ChunkTooLargeError | YAML+SQLite | memory/ + memory_index_sqlite | opportunity_engine, knowledge_engine |
| missing_registry.lifecycle | MissingItem | item_id+kind | status=registered | registered→design_ready→prompt_written→implemented | `validate_schema` (B10) | YAML | missing_registry.yaml | consistency_check, CI |

## 4. Расхождения, требующие внимания

1. **opportunity.schema:** 24 поля vs §E 15/16 — CONFLICT (см. §2.1).
2. **scenario.selection:** контракт требует raise `RoleNotFoundError`, код возвращает None — PARTIAL (P1.4).
3. **opportunity.execute / whim.promote:** контракты декларируют `produced: [opportunity.*, whim.****REMOVED***`, но события НЕ эмитятся — DOCUMENTED_ONLY (см. 06_EVENT_TRACEABILITY).
4. **Factory→Forge соединение:** контракт Factory (select_forge) реализован, но НЕ подключён к opportunity_engine.execute (прямой вызов run_chain) — PARTIAL (см. 14_NEXT_VERTICAL_SLICE).

---

_Конец 05_CONTRACT_FORENSICS. Переход к 06_EVENT_TRACEABILITY._
