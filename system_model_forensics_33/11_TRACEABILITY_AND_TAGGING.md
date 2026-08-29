# 11_TRACEABILITY_AND_TAGGING.md — Traceability + оценка semantic-тегов

> **Задача (§11 + §12):** предложить traceability; исследовать гипотезу semantic-тегов.

---

## Существующие механизмы traceability (по коду)

| Механизм | Где | Что связывает |
|----------|-----|---------------|
| `doc_id` / component mapping | `docs_10/DOCUMENT_REGISTRY.md` | документация → статус |
| `traceability.json` | `phase6_code_contract_forensics_27/traceability.json` | компоненты → код → тесты |
| `architecture_graph.json` | `phase6_code_contract_forensics_27/architecture_graph.json` | граф отношений |
| `missing_registry.py` + YAML | `core_02/missing_registry.py`, `data_13/missing_registry.yaml` | недостающие элементы → lifecycle |
| `KNOWN_CAPABILITIES` | `core_02/blueprint_v3.py` | закрытый словарь capability-токенов |
| ADR-файлы | `docs_10/engineering-memory/decisions/ADR_*.md` | решения → rationale |
| `CON-*` / `ANTI-*` | `core_02/LESSONS.md` | уроки → правила |
| promt-контракты | `pompts_11/NNN_TT_name.md` | задача → спецификация |
| `consistency_check.py` | `scripts_01/consistency_check.py` | машино-проверяемые инварианты |

**Вывод:** механизмы traceability **разрознены** — нет единого `component_id → code_path → test_path → contract_id`. Существует частично (traceability.json, DOCUMENT_REGISTRY, missing_registry), но не как сквозной слой.

---

## Предлагаемый механизм traceability

Единый лёгкий реестр (YAML), НЕ новая БД:

```yaml
# data_13/traceability.yaml
components:
  - component_id: forge_facade
    code_path: core_02/forge_facade.py
    test_path: tests_09/test_forge_facade.py
    contract_id: promt_068_forge_facade
    doc_id: docs_10/engineering-memory/RFC_BUFFY_FORGE_V1.md
    scenario_id: blueprint_v3
    factory_id: null        # ForgeFacade — execution boundary, не фабрика
    status: CONFIRMED
  - component_id: opportunity_engine
    code_path: scripts_01/opportunity_engine.py
    test_path: tests_09/test_opportunity_engine.py
    contract_id: promt_079_opportunity_engine
    factory_id: null
    status: CONFIRMED
```

Связь DOCUMENT ↔ CONTRACT ↔ CODE ↔ TEST ↔ RUNTIME BEHAVIOR:
- `document_id` → `docs_10/*`
- `contract_id` → `pompts_11/*`
- `code_path` → `core_02/` / `scripts_01/`
- `test_path` → `tests_09/`
- `scenario_id` / `factory_id` / `forge_id` — семантические родители.

---

## Оценка гипотезы semantic-тегов (§12)

### Есть ли уже подобная система?
**Частично.** Теги-маркеры встречаются в документах (`[CONCEPT:FACTORY***REMOVED***`-стиль НЕ внедрён;
но `CON-*`/`ANTI-*`/`R-*`/`ADR-*`/`EV-*` — уже де-факто теги). Машиночитаемых тегов нет.

### Где теги полезны
1. **Decision/ADR** — `[DECISION:ADR-015***REMOVED***` (связь решение↔реализация).
2. **Component-level** в шапках архитектурных доков — `[COMPONENT:FORGE_FACADE***REMOVED***`.
3. **Status** — `[STATUS:CONFIRMED***REMOVED***` в forensic-пакетах.
4. **Contract** — `[CONTRACT:EXECUTION***REMOVED***` в промтах.

### Где теги создадут шум
- На **каждый абзац** документации — перегрузка, без semantic value.
- В **runtime-коде** — теги в комментариях Python дадут мусор при grep.
- В **промтах-контрактах** — конвенция `NNN_TT` уже несёт структуру; дублировать не нужно.

### Какие сущности стоит тегировать
`DECISION`, `COMPONENT`, `CONTRACT`, `CONCEPT`, `STATUS`, `EVIDENCE` — в **шапках** доков
и **ADR**, НЕ в каждом параграфе.

### Связи — в graph/db, а не в тексте
Родительские связи (factory_id/forge_id/scenario_id) — в `traceability.yaml` и
`architecture_graph.json`, НЕ в markdown. Текст — для чтения, graph — для query.

### Автогенерация тегов
**Да** — из repository metadata (имя файла → component_id; grep `from core_02.*` →
dependency; тесты → test_path). `consistency_check` уже частично это делает (counter,
naming). Расширить аддитивно.

---

## Рекомендация (§12 «не внедрять автоматически»)

1. **Сначала** — `data_13/traceability.yaml` (единый реестр) + соглашение о 6 тегах в шапках.
2. **Потом** — автогенерация тегов из metadata (расширение consistency_check).
3. **Не делать** — теги на каждом абзаце, теги в runtime-коде.
