# MISSION: First Vertical Slice v0.1 — реализация §34 Candidate 3 (Forge Pipeline+Evolution)

## Контекст

`docs_10/engineering-memory/WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md` §34
уже выбрал и обосновал конкретный, узкий путь к v0.1-minimal готовности:
Candidate 3 (Forge Pipeline+Evolution через `vkusvill_demo`) выиграл 8/8
аспектов против двух альтернатив. Это НЕ новое архитектурное решение —
это исполнение уже принятого, точно посчитанного плана (~200 строк кода,
~4.5 часа, +5 quality gates из 23).

**Прежде чем начинать:** проверь, не было ли что-то из этого уже частично
закрыто предыдущей работой над `ROADMAP_FORGE_RECONCILIATION.md` (промт
про разрыв forge_pipeline.py ↔ ScenarioRegistry). Если Шаг 1-2 оттуда
уже выполнены — не дублируй, используй как основу. Если нет — этот
промт продолжает ту же линию работы, не параллельную.

---

## ЗАДАЧА — пять модулей по §34.4, строго по порядку

Не отклоняйся от порядка Phase 4.1 → 4.2 → 4.3 → 4.4 → 4.5 — каждый
следующий зависит от предыдущего (см. §34.8 "Boundary closure order
unclear... B7/B9 first").

### Phase 4.1 — Forge CLI hook (~40 LOC, ~1.0ч)
`scripts_01/forge.py` — wire CLI `run` command, передать `on_report` hook
в `ForgePipeline`.

### Phase 4.2 — Memory integration (~60 LOC, ~1.5ч, CRITICAL)
`core_02/memory_store.py` — конвертировать `PipelineRun` output
(Success/Fail) в `record_learning_event()`. Это закрывает B7 (Factory vs
Forge boundary) — прямое продолжение того разрыва, который мы находили
ранее между forge_registry.yaml и реальным состоянием прогона.

### Phase 4.3 — Registry hook (~20 LOC, ~0.5ч)
`core_02/forge_registry.py` — pipeline start/end триггерит `record_run()`.

### Phase 4.4 — Project config (~15 LOC, ~0.5ч)
`projects_17/vkusvill_demo/project.yaml` — `requirements.steps: required`
для L2 strict validation.

### Phase 4.5 — Validation (~65 LOC, ~1.0ч, DELIVERABLE)
`tests_09/test_v0_1_slice.py` — прогнать pipeline, убедиться, что SQLite
DB зафиксировала learning event. Это единственный тест, который реально
доказывает, что все пять слоёв (L0 state-of-truth → L1 Workspace → L2
Project → L3 Forge → L4 Registry → L5 Memory) физически связаны, не
просто существуют по отдельности.

---

## Risk Registry (§34.7) — учесть при реализации

- **R-1** (SQLite lockup): `journal_mode=WAL` + serialized writes в
  `record_learning_event()`.
- **R-2** (registry corruption при прерванном прогоне): atomic write
  через tmp + rename.
- **R-3** (Memory pollution от failed pipelines): добавить
  `status: passed|failed` в KO record, queryable как фильтр.
- **R-4** (false-positive в 4.5): использовать детерминированный
  `vkusvill_demo` (без случайных элементов).

## Границы объёма — НЕ делать

- НЕ закрывать B1, B2, B10 (§34.5 явно откладывает их на v0.2 — они не
  блокируют этот slice).
- НЕ реализовывать Mode D/E (multi-agent координация без человека) —
  §36 явно называет их design-only для v0.1, не входит в этот промт.
- НЕ трогать ничего из §27 PREMATURE-списка (Federated Learning, MLOps
  v2) — документ сам явно предостерегает от этого.
- Если в процессе возникнет соблазн добавить что-то "раз уж мы тут" —
  примени Rule 2 из §27.7 самого документа: "если больше 5 файлов
  создано прежде чем first user — suspect overengineering". Пять файлов
  здесь уже названы явно (4.1-4.5), шестой не добавлять без явного
  запроса.

## Формат ответа

1. Подтверждение, что проверено пересечение с ROADMAP_FORGE_RECONCILIATION.
2. Реализация Phase 4.1 → 4.5 строго по порядку, с risk-mitigations.
3. Результат Phase 4.5 — реальный прогон, не просто "тест написан":
   покажи, что SQLite реально зафиксировала learning event после
   прогона pipeline на vkusvill_demo.
4. Финальный подсчёт: сколько из 23 quality gates закрыто после этого
   (документ прогнозирует 19/23, подтверди или опровергни фактом).
5. Список изменённых/созданных файлов.