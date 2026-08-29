# AI REPOSITORY NAVIGATION SPEC (Artifact K — Phase F/K Specification)

> **Source of Truth:** repository (Freebuff / Workspace OS codebase, 2026-08-12).
> **Conforms to:** `projects_17/content_factory/promts/4.md` §12 ("BUTTON → SCRIPT → INSTRUCTION" — capability → entrypoint → script → input → output), §13 (AGENT NAVIGATION MAP — query → canonical entity → implementation → entrypoint → contract → deps → tests → docs → events → storage → limitations), §14 (VECTOR SEARCH + GRAPH — 3 слоя), §19-K (AI_REPOSITORY_NAVIGATION_SPEC.md).
> **Anchor inheritance:** consumes `@entity`/`@module`/`@contract`/`@symbol`/`@test`/`@event` anchors from Artifact I; extends Artifact F `AGENT_NAVIGATION_MAP_V1.md` (query/return pairs) with the **3-layer retrieval model**.
> **REPOSITORY = SOURCE OF TRUTH:** все entrypoints — реальные файлы/CLI/API с 2026-08-12 эвиденсом. НЕ «архитектура предполагает, что X когда-нибудь будет делать Y» (промт-4 §12 anti-pattern).
> **Counterparts required:** Artifact F (навигационные пары), Artifact A (entities), Artifact C (contracts), Artifact E (traceability graph), Artifact I (anchors), Artifact J (sync verifier).

---

## §K.1 — Purpose

Спецификация того, как **любой последующий AI-agent** переходит от вопроса «как выполнить X?» к конкретному **entrypoint + входу + выходу + побочным эффектам + контракту + тестам** — с минимальной галлюцинацией. Ответ — НЕ абстрактное описание, а маршрут.

---

## §K.2 — 3-layer retrieval model (промт-4 §14)

```
QUERY
 ↓
LAYER 1 — STRUCTURED INDEX        точные anchors/entities/contracts (Artifacts A/C/D/E/I)
 ↓
LAYER 2 — VECTOR INDEX            семантическое содержимое docs/code/ADR (knowledge_engine FTS5+TF-IDF+SVD)
 ↓
LAYER 3 — GRAPH                   явные связи сущностей (graph_index, Artifact E)
 ↓
ANCHOR RESOLUTION                 @entity → file::symbol (Artifact J, doc_code_verify)
 ↓
CODE / DOC / TEST → EVIDENCE      конкретный файл + строка + тест
```

| Слой | Существующая реализация | Роль | Статус |
|------|------------------------|------|:------:|
| L1 Structured | Artifacts A/B/C/D/E/F/I + `doc_code_verify.py` | точный lookup | ✅ CURRENT |
| L2 Vector | `scripts_01/knowledge_engine.py` (FTS5+TF-IDF+SVD), RAG (`rag_engine.py`) | семантические кандидаты | ✅ CURRENT |
| L3 Graph | `scripts_01/graph_index.py` (nodes/edges, 7+ типов связей, BFS) + Artifact E | расширение от якоря | ✅ CURRENT |

**Ключевое правило (промт-4 §14):** L2/L3 НЕ заменяют L1 — vector/graph дают кандидатов, L1 (анкоры) даёт точное разрешение, `doc_code_verify` верифицирует (L1+AST). Три слоя комплементарны.

---

## §K.3 — Capability → Entrypoint navigation table

> Формат «BUTTON → SCRIPT → INSTRUCTION» (промт-4 §12). Для каждой capability: ENTRYPOINT → IMPLEMENTATION → INPUT → OUTPUT → SIDE EFFECTS → CONTRACT → DOCS → TESTS.

| CAPABILITY | ENTRYPOINT | IMPLEMENTATION | INPUT | OUTPUT | SIDE EFFECTS | CONTRACT | TESTS |
|------------|-----------|----------------|-------|--------|--------------|----------|-------|
| **Сценарий (Scenario)** | `scripts_01/wizard.py --scenario <id>` | `core_02/scenario_registry.py::find_role/propose_roles` | строка запроса | ScenarioManifest / роли | — | `scenario.selection` | `tests_09/test_scenario_registry.py` |
| **Forge chain (14 ролей)** | `scripts_01/forge.py chain <slug> --json` | `core_02/forge_facade.py::ForgeFacade.run_chain` | project slug | ChainRun (stage_count, overall) | `ForgeRegistry.record_run` → `data_13/forge_registry.yaml` | `forge.execution` | `tests_09/test_forge_chain_*.py` |
| **Forge pipeline (build)** | `scripts_01/forge.py forge <slug>` | `core_02/forge_pipeline.py::ForgePipeline.run` (FORGE→CHECK→BUILD→TEST→DEPLOY→REPORT) | project | артефакты ролей | статусы UNFORGED→DEPLOYED | `forge.execution` | `tests_09/test_forge_pipeline.py` |
| **Роли / валидация** | `scripts_01/forge.py check <slug>` | `core_02/forge_facade.py::RoleArtifactValidator.validate` | project | validation_summary | — | `role.artifacts` | `tests_09/test_role_artifact_validator.py` |
| **Проект** | `python -c "from core_02.workspace import Project; Project.load(...)"` | `core_02/workspace.py::Project` | путь проекта | Project (root/name/type) | — | `project.state` | `tests_09/test_workspace.py` |
| **Отправить промт в очередь** | `pompts_11/user/<file>.md` | `scripts_01/prompt_dispatcher.py::dispatch_one/dispatch_all` | markdown-промт | выполнение → `running/` → `.freebuff_result` | обновление очереди | (task queue) | `tests_09/test_prompt_dispatcher.py` |
| **Web research** | `python -m scripts_01.research_web ...` | `scripts_01/research_web.py` | тема | research_report.md | — | (tool) | `tests_09/test_research_web.py` |
| **LISA-оценка** | `python -m scripts_01.lisa_estimator ...` | `scripts_01/lisa_estimator.py` | проект | lisa_report.md + метрики | — | (tool) | `tests_09/test_lisa_estimator.py` |
| **Opportunity** | `python -m scripts_01.opportunity_engine ...` | `scripts_01/opportunity_engine.py` (lifecycle ACTIVE/DEFERRED/READY/…) | сигнал/тема | opportunity + `data_13/opportunities.yaml` | запись в store | (Intelligence) | `tests_09/test_opportunity_engine.py` |
| **Whim-захват** | `python -m scripts_01.whim_capture capture "<мысль>"` | `scripts_01/whim_capture.py` | текст мысли | whim + `data_13/whims.yaml` | опциональный promote → opportunity | (Intelligence) | `tests_09/test_whim_capture.py` |
| **Проверка консистентности** | `python scripts_01/consistency_check.py --report` | `scripts_01/consistency_check.py::build_report` | workspace | отчёт 10 checks | — | (canon) | `tests_09/test_consistency_check.py` |
| **Док-код верификация** | `python -m core_02.doc_code_verify docs_10/engineering-memory/ --json` | `core_02/doc_code_verify.py::run_verification` | docs dir | JSON-агрегат CONFIRMED/STALE/DOC_ONLY | — | (Artifact J) | `tests_09/test_doc_code_verify.py` |
| **Реестр недостающего** | `python -m core_02.missing_registry list` | `core_02/missing_registry.py::MissingRegistry` | — | lifecycle-статусы | регистрация/статусы | `missing.lifecycle` | `tests_09/test_missing_registry.py` |
| **MCP API (52 тула)** | `scripts_01/mcp_fastapi.py` (:8765) → `mcp_server.py` | `scripts_01/mcp_server.py` | JSON-RPC | инструменты event/policy/runtime/knowledge/memory/roles/presence/collab/rag/pulse | events.db | (MCP) | `tests_09/test_mcp_server.py` |

---

## §K.4 — Query → Answer templates (как отвечать на «Как выполнить X?»)

Шаблон ответа агента для любой capability (промт-4 §13):

```
Q: "Как запустить <X>?"
A:
1. canonical entity:  @entity <id>            (Artifact A)
2. implementation:   <file>::<symbol>         (Artifact A §A, AST-подтверждено)
3. entrypoint:       <CLI / API / путь>       (Artifact F / K §K.3)
4. contract:         @contract <id>           (Artifact C)
5. dependencies:     <импорты / реестры>
6. tests:            @test <file>             (tests_09/)
7. documentation:    <doc.* anchor>           (Artifact B)
8. related events:   @event <id>              (event_bus registered_events)
9. storage:          @storage <unit>          (data_13/context_12)
10. known limitations: <статус/пробел>         (Artifact G gap map)
```

---

## §K.5 — Anti-hallucination rules (обязательные)

1. **Entrypoint — только реальные** файлы/CLI: проверка `Path.exists()` или `ast` перед цитированием (промт-4 §0 REPOSITORY = SOURCE OF TRUTH).
2. **FACT vs DESIGN:** «реализовано в v5.x» (эвиденс) ≠ «в roadmap» (промт-4 §4). DESIGN_ONLY сущности помечаются явно (Artifact G).
3. **Anchor discipline:** ссылки на код — только через `@entity`/`@symbol`/`@module`/`@test` (Artifact I regex), не через номера строк (line numbers запрещены, §I.2).
4. **Verification gate:** если существует `doc_code_verify` CONFIRMED для анкора — цитируем уверенно; если STALE/DOC_ONLY — агент обязан пометить неопределённость.
5. **Проверяемый ответ:** каждый ответ на «как сделать X» обязан содержать минимум: entrypoint + implementation + tests (3 из 10 полей §K.4 — минимальный набор для runnable инструкции).

---

## §K.6 — Integration with vector/graph (промт-4 §14)

| Сценарий | Путь | Механизм |
|----------|------|----------|
| «Найди всё про Opportunity Engine» | L2 vector: `knowledge_engine.search("opportunity engine")` → кандидаты → L1 anchor `@entity opportunity.engine` → L3 graph expansion → файлы | knowledge_engine + doc_code_verify + graph_index |
| «Куда пишется состояние сценария?» | L1 `@storage` → `data_13/forge_registry.yaml` / `context.db` | Artifact A storage колонки |
| «Есть ли тесты на chain?» | L1 `@test test_forge_chain_cli` → `tests_09/test_forge_chain_cli.py` | Artifact A tests |

**Будущее (DESIGN_ONLY):** полный AnchorResolver (`core_02/anchors_resolver.py`, Artifact I §I.3) объединит L1-L3 в один запрос. Сейчас — композиция существующих механизмов (аддитивно, CAN-16).

---

*Artifact K closed. Все entrypoints подтверждены кодом (2026-08-12): scripts_01/, core_02/, tests_09/. Модель: 3 слоя (§K.2), capability→entrypoint таблица (§K.3), шаблон ответа (§K.4), anti-hallucination (§K.5). Связано: Artifact F, A, C, E, I, J; `knowledge_engine.py`; `graph_index.py`.*
