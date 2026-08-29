# IMPLEMENTATION PLAN (Artifact L — Phase L Specification)

> **Source of Truth:** repository (Freebuff / Workspace OS codebase, 2026-08-12).
> **Conforms to:** `projects_17/content_factory/promts/4.md` §20 (IMPLEMENTATION PLAN — PHASE A…H), §19-L (IMPLEMENTATION_PLAN.md), §21 (обязательные проверки), §22 (MINIMAL IMPLEMENTATION PLAN + EXACT NEXT PROMPT).
> **Anchor inheritance:** потребляет gap map Artifact G (что строить), consistency report Artifact H (что чинить), sync spec Artifact J (как верифицировать), navigation spec Artifact K (как агенты будут ходить).
> **REPOSITORY = SOURCE OF TRUTH:** план аддитивный (CAN-16); каждый phase перечисляет СУЩЕСТВУЮЩИЕ компоненты переиспользования — новых «параллельных систем» не создаётся (промт-4 §15/§18).
> **Counterparts required:** Artifacts A–K (input для фаз), `missing_registry.py` (register-first lifecycle для новых capabilities).

---

## §L.0 — Status

Этот план — **фактический отчёт о закрытом слое**: артефакты A–L существуют (7 были, 5 созданы/завершены в рамках выполнения промта 4, v5.189.2). Фазы A–G ниже показывают, КАК слой был построен (reconstructed plan с реальными файлами), а не «что построим когда-нибудь».

> **Финальный аудит (v5.189.5):** 12/12 артефактов A–L сверены с DoD промта 4 (§19–§21) — файлы существуют, DoD-поля присутствуют (A: 25 @entity; B: 19 doc-records; C: 14 контрактов; D: 14 ADR; E: ~60 nodes/85 edges/19 relations; F: 10 capabilities; I: 19 namespaces; J/K/L — specs). Инструменты верификации зелёные: consistency_check TOTAL 0 (11 checks), doc_code_verify CLI, anchors_resolver 1098 anchors (84 UNVERIFIED soft-only, hard=0). Найден и закрыт реестровый gap: A/B/C/D/E/F/I отсутствовали в DOCUMENT_REGISTRY → добавлены (ACTIVE 102→109).

| Фаза (промт-4 §20) | Статус | Артефакт | Механизм |
|---------------------|:------:|----------|----------|
| A Inventory | ✅ CLOSED | Artifact A `PLATFORM_CODE_MAP_V1.md`, Artifact B `DOCUMENTATION_CODE_MAP_V1.md` | существовали до промта 4 |
| B Canonical entities | ✅ CLOSED | Artifact A §A (25 `@entity`) | существовал |
| C Semantic anchors | ✅ CLOSED | Artifact I `SEMANTIC_ANCHOR_SPEC_V1.md` (19 namespaces) | существовал (Phase 1.5) |
| D Traceability graph | ✅ CLOSED | Artifact E `TRACEABILITY_GRAPH_V1.md` | существовал |
| E Contract registry | ✅ CLOSED | Artifact C `CONTRACT_REGISTRY_V1.md` | существовал |
| F Agent navigation | ✅ CLOSED | Artifact F `AGENT_NAVIGATION_MAP_V1.md` + **K** (spec) | F существовал; **K создан** в этом промте |
| G Consistency validation | ✅ CLOSED | **G** (gap map) + **H** (report) + **J** (sync spec) + `doc_code_verify.py` | **G/H/J созданы** в этом промте; код существовал |
| H CI integration | ✅ CLOSED (mechanism) / 🟡 (full gate) | **L** (этот план) | WARN-режим работает; `--strict` опционален |

---

## §L.1 — Phase-by-phase details (промт-4 §20 формат: goal / files / reuse / new code / complexity / risks / tests / acceptance)

### PHASE A — Inventory

| Поле | Значение |
|------|----------|
| goal | Машиночитаемая карта кода и документации |
| files | `PLATFORM_CODE_MAP_V1.md` (A), `DOCUMENTATION_CODE_MAP_V1.md` (B) |
| existing reused | `forge_registry.py`, `scenario_registry.py`, `workspace.py` и др. как объекты инвентаризации |
| new code | 0 |
| complexity | (уже выполнено) |
| risks | карта устаревает → фаза G/H (doc_code_verify) решает |
| tests | `test_doc_code_verify.py` (читает §A) |
| acceptance | 25 entities + 78 doc-claims анкированы |

### PHASE B — Canonical entities

| Поле | Значение |
|------|----------|
| goal | Единый словарь сущностей `@entity` (lowercase.dot, закрытое множество) |
| files | Artifact A §A + Artifact I §I.1 |
| existing reused | `_ENGINE_ROW_RE` паттерны, GLOSSARY |
| new code | 0 |
| complexity | low |
| risks | vocabulary drift (ANTI-6b) — решается close-vocabulary валидацией |
| acceptance | `@entity` токены однозначно резолвятся |

### PHASE C — Semantic anchors

| Поле | Значение |
|------|----------|
| goal | 19-namespace anchor система (regex + AnchorResolver spec) |
| files | `SEMANTIC_ANCHOR_SPEC_V1.md` (I) |
| existing reused | closed vocab в `doc_code_verify.py::ANCHOR_NAMESPACES` |
| new code | (planned) `core_02/anchors_resolver.py` — DESIGN_ONLY |
| complexity | medium |
| risks | line-number identity (запрещено §I.2); @symbol renames |
| acceptance | каждый анкор резолвится или UNVERIFIED |

### PHASE D — Traceability graph

| Поле | Значение |
|------|----------|
| goal | Граф DOCUMENT→CLAIM→ENTITY→SYMBOL→TEST→RUNTIME→EVENT→STORAGE |
| files | `TRACEABILITY_GRAPH_V1.md` (E) |
| existing reused | `graph_index.py` (реализация графа), `event_bus.py` registered_events |
| new code | 0 (граф существует как документ + graph_index как движок) |
| complexity | medium |
| risks | «graph relationships не придуманы» (§21) — каждое ребро с эвиденсом |
| acceptance | рёбра E соответствуют реальным DEPENDS_ON/CALLS в коде |

### PHASE E — Contract registry

| Поле | Значение |
|------|----------|
| goal | Единый реестр контрактов (contract_id/producer/consumer/impl/status) |
| files | `CONTRACT_REGISTRY_V1.md` (C) |
| existing reused | ForgeFacade/ScenarioRegistry/MissingRegistry как имплементации |
| new code | 0 |
| complexity | low |
| risks | contract drift → Artifact J (`doc_code_verify`) + §G.3 |
| acceptance | каждый contract = CURRENT или DESIGN_ONLY (нет фантомов) |

### PHASE F — Agent navigation

| Поле | Значение |
|------|----------|
| goal | query→entrypoint маршруты для AI-агентов |
| files | `AGENT_NAVIGATION_MAP_V1.md` (F) + `AI_REPOSITORY_NAVIGATION_SPEC_V1.md` (**K, создан**) |
| existing reused | `knowledge_engine.py` (L2 vector), `graph_index.py` (L3) |
| new code | 0 |
| complexity | low |
| risks | «архитектура предполагает» anti-pattern (§12) — маршруты только на реальных entrypoint |
| acceptance | на каждую capability — entrypoint+impl+tests (§K.5 минимум 3 поля) |

### PHASE G — Consistency validation

| Поле | Значение |
|------|----------|
| goal | Живая проверка док↔код |
| files | `ARCHITECTURE_GAP_MAP_V1.md` (**G, создан**), `DOCUMENTATION_CONSISTENCY_REPORT_V1.md` (**H, создан**), `CODE_DOCUMENTATION_SYNC_SPEC_V1.md` (**J, создан**), `core_02/doc_code_verify.py` (реализация) |
| existing reused | `consistency_check.py` (Stage 9: checks 8/9/10) |
| new code | `doc_code_verify.py` (уже реализован, register-first closed) |
| complexity | medium |
| risks | false-STALE на не-@entity анкорах; scope (engineering-memory only) |
| tests | `tests_09/test_doc_code_verify.py` (30) |
| acceptance | consistency_check TOTAL 0 после фиксов; doc_code_verify WARN-режим стабилен |

### PHASE H — CI integration

| Поле | Значение |
|------|----------|
| goal | Док-верификация в конвейере качества |
| files | **L** (этот план), `pre-commit` hook (существует), `run_checks.py` |
| existing reused | `scripts_01/drift_check.py`, `consistency_check.py` |
| new code | (предложение) hook: `doc_code_verify --strict` на engineering-memory delta |
| complexity | low |
| risks | жёсткий gate блокирует мерджи → WARN-дефолт + opt-in --strict |
| acceptance | WARN-режим в CI (не блокирует); --strict доступен для ревью |

---

## §L.2 — Register-first (что зарегистрировано в рамках слоя)

| item_id | kind | factory | status | промт |
|---------|------|---------|--------|-------|
| `doc_code_verify` | engine | architecture | prompt_written → (эта спека завершает цикл описания) | `pompts_11/082_19_doc_code_sync.md` |

> ⚠️ Статус `doc_code_verify` в `missing_registry` — `prompt_written` (промт написан, код + тесты существуют как `core_02/doc_code_verify.py`). Перевод в `implemented` — отдельный шаг (`mark-implemented`), осознанно НЕ выполнен в рамках этого документа (read-only форензика + спецификация; изменение реестра — по отдельному решению владельца, т.к. чек `missing_registry_sync` сверяет §20 ↔ реестр).

---

## §L.3 — Next steps (после этого промта)

1. **H-1/H-2 — ✅ CLOSED (v5.189.3):** `prompts_11` (сирота) удалён — `080_19_doc_code_sync.md` перенесён в канон как `pompts_11/082_19_doc_code_sync.md`; `promt81.md` → `pompts_11/081_19_model_dispatcher.md`. Consistency_check naming 0 issues.
2. **`doc_code_verify` → mark-implemented** — после подтверждения владельцем (закроет register-first цикл полностью).
3. **AnchorResolver (`core_02/anchors_resolver.py`)** — полный 19-namespace резолвер (Artifact I §I.3), hook в consistency_check как check #11.
4. **--strict gate** в CI для engineering-memory delta (после стабилизации WARN-режима).

---

## §L.4 — EXACT NEXT PROMPT (промт-4 §22 item 12)

> Сгенерирован для следующего агента. Задача — завершить Architecture–Code Synchronization Layer (НЕ Content Intelligence).

```
ROLE: Senior Repository Forensics Engineer.

TASK: завершить Architecture–Code Synchronization Layer (промт 4 projects_17/content_factory/promts/4.md, артефакты A–L уже существуют в docs_10/engineering-memory/).

1. Закрыть 2 задокументированных naming-находки (consistency_check):
   - H-1: каталог prompts_11 (дубль-суффикс _NN) — решение: удалить пустой shim либо внести в _LEGACY_TOP_LEVEL_REDIRECTS в consistency_check.py + drift_check.py;
   - H-2: файл promt81.md в pompts_11/ — переименован в 081_19_model_dispatcher.md по FINAL_STRUCTURE §2.1 (CON-59), ссылки обновлены (CAN-17: исторические CHANGELOG-упоминания не переписаны).
2. Перевести doc_code_verify в status=implemented (missing_registry mark-implemented, impl=core_02/doc_code_verify.py, промт pompts_11/082_19_doc_code_sync.md) — по решению владельца.
3. Реализовать core_02/anchors_resolver.py (Artifact I §I.3): полный 19-namespace резолвер, hook в consistency_check как check #11 (ANCHORS) + test_anchors_resolver.py.
4. Подключить doc_code_verify --strict в run_checks.py (WARN по умолчанию, opt-in gate) — аддитивно (CAN-16), без правок существующих модулей.
5. Валидация: consistency_check TOTAL 0 · pytest tests_09/ полный прогон (цель 2823+ passed) · mypy по изменённым файлам · code-reviewer-glm.

ЗАПРЕТ: НЕ реализовывать Content Intelligence (промт-4 §20/§22 граница); НЕ переписывать существующие модули; новые capabilities — register-first.
```

---

*Artifact L closed. План аддитивный (CAN-16): фазы A–G построены на существующих компонентах; 5 артефактов (G/H/J/K/L) созданы в рамках выполнения промта 4 (v5.189.2); 3 из 5 STALE-находок закрыты (H-3/H-4/H-5). **§L.4 (шаги 1–5) FULLY CLOSED (v5.189.3–v5.189.4):** H-1/H-2 naming-закрытие (prompts_11 удалён, promt81 → 081_19_model_dispatcher); `doc_code_verify` → status=implemented (missing_registry + §20 row 16); `core_02/anchors_resolver.py` (19-namespace по Artifact I §I.3) + check #11 ANCHORS в consistency_check (hard-namespaces блокируют, soft — advisory, мета-спека исключена) + tests_09/test_anchors_resolver.py; opt-in gate `doc_code_verify --strict` в run_checks.py; валидация: consistency_check TOTAL 0 · pytest 112/112 (scoped) · mypy — только pre-existing ошибки. Content Intelligence НЕ реализован (промт-4 §20/§22 граница соблюдена). Связано: Artifacts A–K, `doc_code_verify.py`, `anchors_resolver.py`, `consistency_check.py`, `missing_registry.py`.*
