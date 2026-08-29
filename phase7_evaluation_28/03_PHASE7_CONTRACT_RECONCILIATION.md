# 03_PHASE7_CONTRACT_RECONCILIATION.md — Contract Reconciliation (Task A)

> Phase 7 §5 (TASK A — CONTRACT RECONCILIATION).

## Решение

**CANONICAL SCHEMA = runtime implementation** (24 поля, `scripts_01/opportunity_engine.py::Opportunity`).

Обоснование (evidence): runtime dataclass + `OpportunityStore` (YAML persistence) +
lifecycle FSM + 26 targeted tests реально работают на 24-полевой схеме с v5.187.7.
Design-схема §E (15 полей) была **projection** — сигналы/гипотезы/рациональ свёрнуты
в title/description/provenance. Менять runtime под design = регресс без пользы.

## Каноническая схема (24 поля)

| # | Поле | Тип | Назначение |
|---|------|-----|------------|
| 1 | `id` | str | `opp-<hex>` (uuid4) |
| 2 | `project_id` | str | из WorkspaceRegistry |
| 3 | `title` | str | заголовок (сигнал/гипотеза свёрнуты) |
| 4 | `description` | str | расширенное описание |
| 5 | `source` | str | whim \| project_pulse \| event_bus \| knowledge \| hand |
| 6 | `status` | str | ACTIVE \| DEFERRED \| READY \| REACTIVATED \| COMPLETED \| FAILED |
| 7 | `priority` | int | 1-10 (default 5) |
| 8 | `created_at` | str | ISO |
| 9 | `updated_at` | str | ISO |
| 10 | `provenance` | dict | DISCOVER/ACCUMULATE-ключи + rank_score/rank_factors + factory_selection |
| 11 | `scenario` | dict\|None | выбранный scenario (scenario_id внутри) |
| 12 | `roles` | list[dict***REMOVED*** | выбранные роли |
| 13 | `artifacts` | list[dict***REMOVED*** | артефакты после run_chain |
| 14 | `source_path` | str | путь источника |
| 15 | `evidence_path` | str | путь evidence |
| 16 | `deferred_at` | str\|None | ISO |
| 17 | `deferred_reason` | str\|None | |
| 18 | `previous_status` | str\|None | audit-trail (advance) |
| 19 | `reactivated_at` | str\|None | ISO |
| 20 | `completed_at` | str\|None | ISO |
| 21 | `failed_at` | str\|None | ISO |
| 22 | `failure_reason` | str\|None | |
| 23 | `related_decisions` | list[str***REMOVED*** | id KO kind=`decision` (§14) |
| 24 | `related_whims` | list[str***REMOVED*** | id связанных whims (dedup) |

## Design → Runtime mapping (§E.1)

| Design (§E v1.0) | Runtime (canonical) | Mapping |
|-------------------|---------------------|---------|
| `id` | `id` | same |
| `project_id` | `project_id` | same |
| `source` | `source` | same (+ `hand`) |
| `signal` | `title` | сигнал → заголовок |
| `hypothesis` | `title`/`description` | свёрнута |
| `description` | `description` | same |
| `rationale` | `provenance` | DISCOVER-ключи |
| `status` | `status` | same (+ FAILED) |
| `provenance` | `provenance` | same + rank/ACCUMULATE |
| `created_at`/`updated_at` | same | same |
| `related_knowledge` | `provenance.memory_knowledge_id` + `related_whims` | ACCUMULATE-ключи |
| `selected_scenario` | `scenario` | str → dict |
| `resulting_artifact` | `artifacts` | str → list[dict***REMOVED*** |
| `related_decisions` | `related_decisions` | same |
| — | `priority`, `roles`, `source_path`, `evidence_path`, lifecycle audit-поля | новые |

## Файлы, обновлённые в Task A

| Файл | Что изменено |
|------|--------------|
| `docs_10/engineering-memory/INTELLIGENCE_FACTORY_CONTRACT_V1.md` | §E → 24-полевая каноническая схема + §E.1 mapping-таблица; статус документа обновлён |
| `docs_10/engineering-memory/CONTRACT_REGISTRY_V1.md` | Contract #15 status (drift CLOSED); §C.6 #5 → RESOLVED; events-статусы #12/#13/#15/#16 → emitted; §C.5 dedup-список (26→31 событий) |
| `docs_10/engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md` | §20 row #10 + сводка #10: «16 полей» → «24 поля (§E reconciled)» |

## Тесты (Task A)

- `test_opportunity_schema_all_fields_roundtrip` — 24 поля переживают store round-trip.
- `test_opportunity_schema_canonical_field_set` — канонический field set (design + runtime).

---
_Canonical schema = implementation. Drift #5 CLOSED. Одна схема, без дублирования._
