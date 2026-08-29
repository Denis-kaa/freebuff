# 09_DOCUMENT_TAGGING_PROPOSAL — Предложение системы семантических тегов

> **Промт:** `pompts_11/087_19_phase6_code_contract_forensics.md` §10 (TAGGING / SEMANTIC ANCHORS)
> **Метод:** исследовать существующую документацию, предложить минимальную систему тегов. НЕ внедрять автоматически.

---

## 1. Что УЖЕ существует (не изобретаем заново)

`docs_10/engineering-memory/SEMANTIC_ANCHOR_SPEC_V1.md` (Artifact I) определяет **19 namespace-анкоров**:

| Namespace | Пример | Резолвится |
|-----------|--------|-----------|
| `@entity` | `@entity forge.facade` | PLATFORM_CODE_MAP_V1.md §A.1-A.5 |
| `@contract` | `@contract forge.execution` | CONTRACT_REGISTRY_V1.md §C.4 |
| `@decision` | `@decision ADR_001` | ARCHITECTURE_DECISION_REGISTRY_V1.md |
| `@lesson` | `@lesson CON-052` | core_02/LESSONS.md |
| `@module` | `@module core_02/forge_facade.py` | file path |
| `@symbol` | `@symbol ForgeFacade.run_chain` | AST symbol lookup |
| `@event` | `@event opportunity.discovered` | SEMANTIC_ANCHOR_SPEC + contract produced |
| `@storage` | `@storage opportunities_yaml` | data_13/*.yaml |
| `@test` | `@test test_opportunity_engine` | tests_09/*.py |
| `@factory` | `@factory content_factory` | FACTORY_FORGE_ARCHITECTURE_V1 §3 |
| ... (19 всего) | | |

**Реализация:** `core_02/anchors_resolver.py` (v5.189.4) — 19-namespace AnchorResolver, AST symbol lookup, hard/soft namespace split в consistency_check check #11.

## 2. Что предложить дополнительно (минимально)

Промт предлагает теги `@concept / @contract / @module / @symbol / @entrypoint / @event / @storage / @test / @decision / @invariant / @depends / @implements / @verified-by`. Из них **уже покрыты** 9: `@contract, @module, @symbol, @event, @storage, @test, @decision`. 

**Реально не хватает** (и дают пользу):

| Новый тег | Польза | Где |
|-----------|--------|-----|
| `@entrypoint` | CLI/API/TG/MCP точка входа → engine | forge.py, opportunity_engine.py, forge_api.py, telegram_bot.py, mcp_server.py |
| `@invariant` | инварианты (closed vocab, DEFERRED≠DELETED, atomic write) | core_02/LESSONS.md, контракты |
| `@depends` | зависимости компонентов | архитектурные доки |
| `@verified-by` | тест, верифицирующий поведение | контракты |

## 3. Что индексировать

- `@entrypoint` — индексировать в `AGENT_NAVIGATION_MAP_V1.md` §F.1 (уже есть capability-таблица, добавить entrypoint-колонку).
- `@invariant` — индексировать в `ARCHITECTURE_DECISION_REGISTRY_V1.md` (R-* правила) + `core_02/LESSONS.md` (CON/ANTI/CAN/R).
- `@depends` — индексировать в GraphIndex (edge `depends_on`).

## 4. Как использовать для Graph Index

```
DOCUMENT → @anchor (19 namespaces) → anchors_resolver.py → CODE SYMBOL
   ↓ add_edge(rel=implements/verifies/calls/...) 
GRAPH EDGE → GraphIndex → semantic search / navigation
```

`anchors_resolver.py` уже даёт резолвинг; GraphIndex уже принимает rel-строки. **Соединение** = аддитивный шаг: `traceability_graph.py` (bidirectional adjacency, TRACEABILITY_GRAPH §E.9 drift #3).

## 5. Как использовать для semantic search

- `knowledge_engine.py::KnowledgeEngine` индексирует `docs_10/` + `pompts_11/` — анкеры уже попадают в корпус.
- `semantic_layer.py::SemanticLayer.find_similar_patterns` — поиск по knowledge objects.
- Анкеры делают результаты search **кликабельными** (resolve → code symbol).

## 6. Как избежать мусора из тегов

1. **Закрытый словарь** — только 19+4 namespace, валидация через `anchors_resolver` (hard/soft split).
2. **Тег только при наличии реального кода** — DOCUMENTED_ONLY теги запрещены (репозиторий = source of truth).
3. **Не дублировать** — если тег уже покрыт существующим namespace, не вводить новый.
4. **consistency_check** — check #11 уже валидирует анкеры; расширить на новые namespace.

## 7. Вердикт

Предлагаю **НЕ вводить новую систему тегов**, а расширить существующую 19-namespace схему на 4 namespace (`@entrypoint`, `@invariant`, `@depends`, `@verified-by`). Это минимально, аддитивно, индексируемо, и не превращает документы в мусор.

---

_Конец 09_DOCUMENT_TAGGING_PROPOSAL. Переход к 10_CONTENT_INTELLIGENCE_STATUS._
