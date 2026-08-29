# 08_GRAPH_RELATIONSHIP_MAP — Граф отношений

> **Промт:** `pompts_11/087_19_phase6_code_contract_forensics.md` §11 (GRAPH MODEL)
> **Метод:** используем существующий `GraphIndex` (НЕ создаём новый engine). Определяем, какие отношения уже представимы.

---

## 1. Существующий GraphIndex

`scripts_01/graph_index.py::GraphIndex`:
- `add_node(node_id, node_type, ...)`, `remove_node`, `get_node`
- `add_edge(src, rel, dst)`, `PathResult`, `GraphStats`
- `link_artifact_to_kg(artifact_path, kg_node_id, relationship)` — связь артефакта с knowledge
- `interlink(workspace_root, file_extensions)` — авто-связывание файлов

**Хранилище:** in-memory deque + опциональный JSON snapshot. Тест: `tests_09/test_graph_index.py`.

## 2. Какие отношения уже представимы существующим GraphIndex

| Отношение | Edge type (rel) | Уже используется? |
|-----------|-----------------|-------------------|
| DOCUMENT --implements--> CONTRACT | `implements` | ⚠️ частично (anchor resolver) |
| CONTRACT --implemented_by--> MODULE | `implemented_by` | ⚠️ частично |
| MODULE --calls--> MODULE | `calls` | ⚠️ (через imports) |
| EVENT --published_by--> MODULE | `published_by` | ❌ не используется |
| EVENT --consumed_by--> MODULE | `consumed_by` | ❌ не используется |
| TEST --verifies--> CONTRACT | `verifies` | ⚠️ частично |
| ENTRYPOINT --invokes--> FUNCTION | `invokes` | ❌ не используется |
| CONCEPT --evolves_to--> CONCEPT | `evolves_to` | ❌ не используется |

## 3. Существующие edge types в GraphIndex (grep)

`TRACEABILITY_GRAPH_V1.md` §E.2 определяет 19 relation-types (E-1..E-19 + lesson-constraints). GraphIndex.add_edge принимает произвольный `rel` (строку), поэтому **все 19 типов представимы без изменений engine**. Ограничение: нет валидации rel-словаря (любая строка проходит).

## 4. Минимальный набор новых edge types

**НЕ требуются новые типы** — GraphIndex принимает произвольные rel-строки. Нужен только **словарь канонических rel** (closed set) для консистентности:

```
implements, implemented_by, calls, published_by, consumed_by,
verifies, invokes, evolves_to, depends_on, produces, stores,
documents, supersedes, contradicts, enforces, allows_by, denies_by
```

## 5. Рекомендация: DOCUMENT → SEMANTIC ANCHOR → CODE SYMBOL → GRAPH EDGE

```
DOCUMENT (markdown)
   ↓ @anchor (SEMANTIC_ANCHOR_SPEC_V1 §I.2)
SEMANTIC ANCHOR (namespace.id)
   ↓ resolve (core_02/anchors_resolver.py)
CODE SYMBOL (module::symbol)
   ↓ add_edge
GRAPH EDGE (src --rel--> dst)
```

`core_02/anchors_resolver.py` уже реализует namespace-резолвинг (19 namespaces). Соединение с GraphIndex — аддитивный шаг (см. 14_NEXT_VERTICAL_SLICE, кандидат).

## 6. Существующий graph для traceability

`TRACEABILITY_GRAPH_V1.md` §E.5 содержит `data_13/traceability_graph.yaml` (85 edges first slice) — **документальный артефакт**, НЕ заполнен в runtime GraphIndex. Инструмент `core_02/traceability_graph.py` (bidirectional adjacency) — **не реализован** (см. §E.9 drift #3).

---

_Конец 08_GRAPH_RELATIONSHIP_MAP. Переход к 09_DOCUMENT_TAGGING_PROPOSAL._
