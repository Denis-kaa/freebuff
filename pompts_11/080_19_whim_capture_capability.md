# ПРОМТ 79: РЕАЛИЗАЦИЯ Whim Capture (`whim_capture`, Phase 1.2 Content Intelligence)

> **Статус:** 🏗 ПРОМТ НА РЕАЛИЗАЦИЮ (Missing Capability #9, зарегистрирован в §20 карты v1.1 + data_13/missing_registry.yaml, G3 по FORENSICS_CI_REPORT_V1.md)
> **Дата:** 2026-08-12
> **Нумерация:** файл 080_19 → «ПРОМТ 79» (конвенция `pompts_11/`)
> **Источник:** FORENSICS_CI_REPORT_V1.md (§D primitives, §I G3 module), FACTORY_FORGE_ARCHITECTURE_V1.md (§17.1 triple-stage pipeline: Whim → Opportunity → Forge → Artifact), INTELLIGENCE_FACTORY_CONTRACT_V1.md (§E persistence decision), ARB_REVIEW_VERTICAL_SLICE_V1.md (§8 Whim requirements + §9 Gate permission step 2).
> **Принцип (register-first, RA2):** `whim_capture` уже зарегистрирован (kind=module, factory=content, R18 RECONCILIATION backlog item) — этот промт переводит его в `prompt_written`, а реализация — в `implemented`.
> **Phase relation:** Phase 1.1 (`opportunity_engine`) уже mark-implemented (CHANGELOG v5.187.7). Этот Phase 1.2 закроет ГAIT-loop Whim → Opportunity → ... обратной связи.

## 1. Задача

Реализовать **`whim_capture`** — модуль **Whim-слоя CI**: minimal intake для неструктурированных идей пользователя, которые накапливаются и могут впоследствии стать Opportunity.

**Execution Path (§J FORENSICS_CI_REPORT):**

```
Whim-capture entry (CLI / hand / project_pulse)
    ↓
WHIM  (новая запись с body + project_id + source)
    ↓
TRIAGE  (классификация: KEEP | DISCARD | PROMOTE_CANDIDATE)
    ↓
PROMOTE → Opportunity Engine DISCOVER  (data_13/opportunities.yaml)
    ↓
Existing execution tail (opportunity_engine.run → ForgeFacade)
```

**Результат:** запись в `data_13/whims.yaml` с lifecycle; promoted Whim в итоге генерирует Opportunity через `opportunity_engine.discover_candidates(project_id)` (lazy hooks per additive CAN-16). Полный цикл Whim → Opportunity будет работать без второго реестра.

**Что НЕ делаем:** не реализуем Content Factory целиком, не пишем FactoрyRegistry, не делаем Whim KPI dashboard, не дублируем Opportunity структуру в Whim-store, не создаём Knowledge Ontology — только minimal capture + classification + promote-flow.

## 2. Контекст и место в архитектуре

```
Content Factory (Future) → Intelligence-слой CI
└── Whim Capture (module, G3)         ← ЭТА РЕАЛИЗАЦИЯ
        ├── Captures timestamped body+context  →  persistent yaml (NEW)
        ├── Classifies heuristically           →  TRIAGED (KEEP|DISCARD|PROMOTE_CANDIDATE)
        ├── Promotes via opportunity_engine    →  Opportunity Record (CONNECTS BACK)
        └── Disregarded/Archived               →  DISCARDED (terminal, audit-trail-preserved)
```

**Маппинг на существующий код:**

| Что | Где | Статус |
|-----|-----|--------|
| Persistence | `data_13/whims.yaml` (atomic `.tmp`+`replace` per v5.39.0 Lesson) | СОЗДАЁТСЯ |
| Integration target | `scripts_01/opportunity_engine.py::discover_candidates(project_id)` | G0 (CONFIRMED — Phase 1.1 done) |
| Module import | `scripts_01/whim_capture.py` (~400 LOC) | СОЗДАЁТСЯ |
| Register-first | `core_02/missing_registry.py` — `whim_capture` (kind=module, factory=content) + `whims_yaml` (kind=registry, factory=opportunity_engine) | **registered** → этот промт → `prompt_written` → → → → `implemented` |
| Vocabulary (ANTI-6b) | `whim_capture` — kind=module, NOT in `KNOWN_CAPABILITIES` (real ModelCatalog token), тест reference: `tests_09/test_wizard.py::test_known_capabilities_subset_of_actual_catalog` | enforced by design |

## 3. Требования к реализации

### 3.1 Функциональные

1. **Capturе (NEW-состояние):** текст тела + project_id + source (whim | cli | hand | project_pulse) + timestamp;
2. **Triage (NEW → TRIAGED):** deterministic classification (`"статья"|"книга"|"guide"|"план" → KEEP+PROMOTE_CANDIDATE`; `"спам"|"повтор"|"тест" → DISCARD`; default `KEEP`); явное override через `--classification X`;
3. **Promote (TRIAGED → PROMOTED_TO_OPPORTUNITY):** вызов `opportunity_engine.discover_candidates(project_id)` (lazy integration) → новая Opportunity запись в `data_13/opportunities.yaml` + Whim запись получает `related_opportunity_id`;
4. **Discard (TRIAGED → DISCARDED):** terminal state; record НЕ стирается (audit trail);
5. **Defer (NEW → DEFERRED):** если не хочется triage сразу — отложить с reason; **DEFERRED ≠ DELETED** (can resume via re-triage).

### 3.2 Режимы CLI

- `whim_capture capture <body> [--project-id X***REMOVED*** [--source X***REMOVED*** [--json***REMOVED***` — создать Whim (NEW);
- `whim_capture list [--status NEW|TRIAGED|PROMOTED_TO_OPPORTUNITY|DISCARDED|DEFERRED|FAILED***REMOVED*** [--project-id X***REMOVED*** [--json***REMOVED***` — фильтр list;
- `whim_capture status <whim_id> [--json***REMOVED***` — показать lifecycle;
- `whim_capture triage <whim_id> [--classification KEEP|DISCARD|PROMOTE_CANDIDATE***REMOVED*** [--reason X***REMOVED*** [--json***REMOVED***` — TRIAGED state;
- `whim_capture promote <whim_id> [--json***REMOVED***` — продвинуть в Opportunity (calls opportunity_engine);
- `whim_capture defer <whim_id> [--reason X***REMOVED*** [--json***REMOVED***` — отложить Whim;
- `whim_capture get <whim_id> [--json***REMOVED***` — fetch by id.

### 3.3 Архитектурные (обязательные)

1. **ADDITIVE (CAN-16):** новый `scripts_01/whim_capture.py`; НЕ модифицируются: `opportunity_engine.py`, `forge_facade.py`, `scenario_registry.py`, `memory_store.py`, `learning_loop.py`, `missing_registry.py`;
2. **Lazy integration:** `promote` использует `from scripts_01.opportunity_engine import discover_candidates` — внутри try/except; при недоступности → graceful fail (Whim остаётся в TRIAGED, не FAILED), с сообщением в результате;
3. **Безопасность:** никаких `exec`/`eval`/`shell=True`/`os.system`; YAML через безопасный dumper (`yaml.safe_dump`); failures gracefully exit 0 или 1;
4. **Fail-safe:** пустой вход / нет yaml / нет project_id → exit 0 (degraded) + пустой list; critical path errors → exit 1;
5. **Determinism:** triage classification heuristic deterministic (keyword whitelist), tests unit-friendly;
6. **Observability:** lifecycle transitions логируются в stderr (при `--json` mode ошибки → stderr, stdout = JSON);
7. **Закрытый словарь:** `whim_capture` НЕ добавляется в `KNOWN_CAPABILITIES` (это Engine/Module name, а не model token);
8. **Lifecycle forward-only:** status_rank enforced; DISCARDED = terminal; PROMOTED_TO_OPPORTUNITY = terminal (audit-trail via `related_opportunity_id`).

### 3.4 Файловая карта

**CREATE:**
| Path | Responsibility |
|------|----------------|
| `pompts_11/080_19_whim_capture_capability.md` | (этот файл) |
| `data_13/whims.yaml` | Schema skeleton (header + empty {***REMOVED***); created automatically on first capture |
| `scripts_01/whim_capture.py` | CLI + dataclass Whim + WhimStore (YAML persistence) + FSM |
| `tests_09/test_whim_capture.py` | Unit tests: capture/list/triage/promote/goto-lifecycle + DEFERRED preservation + atomic write + JSON discipline + integration with opportunity_engine |

**MODIFY:** none.

**DO NOT TOUCH:**
`scripts_01/opportunity_engine.py`, `core_02/forge_facade.py`, `core_02/scenario_registry.py`, `core_02/memory_store.py`, `core_02/learning_loop.py`, `core_02/missing_registry.py`, `runtime_05/scenarios/*`.

### 3.5 Качество

- docstrings, обработка ошибок, валидация входных данных, детерминизм;
- тесты: `pytest tests_09/test_whim_capture.py -q` — все зелёные;
- mypy clean (или только lazy-stubs);
- `python -m whim_capture --help` success.

## 4. Definition of Done

1. `python scripts_01/whim_capture.py capture "Идея для статьи" --project-id proj-x` → Whim id в stdout (или JSON);
2. `capture "Опять спам"` → KEEP default; `--classification DISCARD` → TRIAGED + DISCARDED;
3. `triage <id> --classification PROMOTE_CANDIDATE` → TRIAGED;
4. `promote <id>` → создаёт Opportunity через opportunity_engine; Whim record получает `related_opportunity_id` + status `PROMOTED_TO_OPPORTUNITY`;
5. `list --project-id proj-x --json` → JSON parseable;
6. `defer <id> --reason "later"` → DEFERRED, record preserved through re-triage;
7. `pytest tests_09/test_whim_capture.py` зелёные;
8. `missing_registry` cli: `whim_capture` + `whims_yaml` — переведены в `implemented`;
9. Lifecycle forward-only enforced (NEW→skip→PROMOTE = InvalidTransition).

## 5. Связанные документы

- `pompts_11/079_19_opportunity_engine_capability.md` — Phase 1.1 (peer module, mirror style)
- `scripts_01/opportunity_engine.py` — peer FSM (lifecycle + persistence pattern)
- `docs_10/engineering-memory/ARB_REVIEW_VERTICAL_SLICE_V1.md` — §8 Whim requirements + §9 gate permission
- `docs_10/engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md` — §17.1 triple-stage pipeline
- `docs_10/engineering-memory/INTELLIGENCE_FACTORY_CONTRACT_V1.md` — §E persistence split
- `core_02/missing_registry.py` — register-first machinery
- `data_13/missing_registry.yaml` — Registry state machine

## 6. Scope Guard — НЕ строить сейчас

- ❌ Knowledge Ontology / Whim classification AI
- ❌ UI / dashboard для Whim list
- ❌ Whim dedup / Whim clustering
- ❌ Whim export / backup cron
- ❌ Whim sharing / cross-project
- ❌ Whim dead-letter queue
- ❌ autonomous Whim → Opportunity promotion (always manual promote)

*Промт на реализацию Missing Capability #9 (Whim Capture, Phase 1.2 CI). Статус: register-first цикл. После реализации — mark-implemented + bump DOCUMENT_REGISTRY + CHANGELOG [5.187.8***REMOVED***.*
