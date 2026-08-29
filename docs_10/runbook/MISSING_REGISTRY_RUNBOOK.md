# MISSING_REGISTRY_RUNBOOK — Operational Manual для `python -m core_02.missing_registry`

> **Версия документа:** v1.1 (2026-08-16) · **Applies to:** `core_02/missing_registry.py` CLI (register-first lifecycle)
> **Audience:** операторы runtime, агентные сессии, разработчики Factory/Scenario
> **Status:** ACTIVE (operational, source-of-truth для register-first операций)
> **Канон:** AGENTS.md §5 REGISTER-FIRST (правило) · `data_13/missing_registry.yaml` (реестр) · FACTORY_FORGE_ARCHITECTURE_V1.md §20 (карта Missing Capabilities)

---

## 0. TL;DR — За 60 секунд

```bash
# Посмотреть реестр недостающих элементов (все статусы):
python -m core_02.missing_registry list --json

# Шаг 1 register-first: зафиксировать недостающий элемент ДО реализации:
python -m core_02.missing_registry register my_tool --kind tool --factory code --description "..."

# Шаг 2: промт на реализацию написан:
python -m core_02.missing_registry mark-prompt-written my_tool --prompt pompts_11/promtNN.md

# Шаг 3: реализация завершена (закрывает lifecycle):
python -m core_02.missing_registry mark-implemented my_tool --implementation scripts_01/my_tool.py

# Шаг 3b: если у элемента была цепочка промтов (forensics/design) — сохранить след:
python -m core_02.missing_registry add-related-prompt my_tool --prompt pompts_11/0NN_19_...forensics.md

# Проверить целостность реестра (B10/R-127 инварианты):
python -m core_02.missing_registry check     # exit 0 = валиден, exit 1 = нарушения
```

**Что получает оператор:** реестр `data_13/missing_registry.yaml` — машиночитаемую копию §20 карты v1.1 (7 канонических записей после `seed`), каждая запись движется только вперёд по lifecycle: `registered → design_ready → prompt_written → implemented` (откат запрещён).

---

## 1. Назначение и архитектурный контекст

`missing_registry` — CLI точка входа для **MissingRegistry** (`core_02/missing_registry.py`): машиночитаемый реестр недостающих элементов платформы (capability / tool / engine / forge / role / модуль). Он реализует принцип **REGISTER-FIRST** (AGENTS.md §5): любой обнаруженный недостающий элемент — НЕ «несуществующий токен», а способность, которую нужно **построить** — фиксируется в реестре **до** реализации.

| Компонент | Путь | Роль |
|-----------|------|------|
| Модуль | `core_02/missing_registry.py` | `MissingItem` dataclass + `MissingRegistry` (YAML) + CLI `main()` |
| Реестр | `data_13/missing_registry.yaml` | источник истины по недостающим элементам |
| Карта | `docs_10/engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md` §20 | человекочитаемая таблица Missing Capabilities (зеркало реестра) |
| Правило | `AGENTS.md` §5 REGISTER-FIRST | канонический порядок: зафиксировать → промт → реализация |
| Сверка | `scripts_01/consistency_check.py` → `check_missing_registry_sync` | дрейф §20 ↔ YAML репортится как issue |

**Lifecycle (forward-only, не откатывается):**

```
registered ──► design_ready ──► prompt_written ──► implemented
    │              │                  │
    │              └── дизайн готов   └── промт на реализацию написан
    └── зафиксирован (register-first)
```

- `mark_prompt_written` НЕ откатывает `implemented` (guard по рангу);
- повторный `register` НЕ откатывает более продвинутый статус.

---

## 2. CLI — полный справочник

**Глобальный флаг:** `--path PATH` — путь к YAML-реестру (default `data_13/missing_registry.yaml`). Полезен для тестов/изолированных реестров.

### 2.1 `list` — показать зарегистрированные элементы

```bash
python -m core_02.missing_registry list                                    # все записи
python -m core_02.missing_registry list --status implemented               # фильтр по статусу
python -m core_02.missing_registry list --factory research                 # фильтр по Factory
python -m core_02.missing_registry list --json                             # машинный вывод (JSON)
```

`--status` choices: `registered` \| `design_ready` \| `prompt_written` \| `implemented`.

### 2.2 `seed` — канонические записи §20 (идемпотентно)

```bash
python -m core_02.missing_registry seed
```

Добавляет 7 канонических записей Missing Capabilities из §20 карты v1.1 (если их ещё нет). Идемпотентно: повторный запуск не дублирует. Актуальный статус seed: #1/#2 `design_ready` (дизайн готов), #6 `research_web` ✅ implemented, #7 `lisa_estimator` ✅ implemented, #3–#5 `registered`.

### 2.3 `register` — шаг 1: зафиксировать недостающий элемент

```bash
python -m core_02.missing_registry register <item_id> --kind <kind> \
    [--factory <factory>***REMOVED*** [--description <text>***REMOVED*** [--prompt <path>***REMOVED*** \
    [--implementation <path>***REMOVED*** [--status <status>***REMOVED*** [--backfill***REMOVED***
```

`--kind` choices: `capability` \| `tool` \| `engine` \| `forge` \| `role` \| `factory` \| `module` \| `registry` \| `system`.

`--backfill` — флаг для retroactive-регистрации (элемент существовал ДО фиксации в реестре); требует парного `--status implemented`. Подробнее — §6.1.

Пример: `python -m core_02.missing_registry register my_tool --kind tool --factory research --description "Research-утилита"`.

### 2.4 `mark-prompt-written` — шаг 2: промт на реализацию написан

```bash
python -m core_02.missing_registry mark-prompt-written <item_id> --prompt pompts_11/promtNN.md
```

### 2.5 `mark-implemented` — шаг 3: реализация завершена (закрывает lifecycle)

```bash
python -m core_02.missing_registry mark-implemented <item_id> --implementation scripts_01/x.py [--prompt pompts_11/promtNN.md***REMOVED***
```

После этого обновить закрытый словарь (`KNOWN_CAPABILITIES` + `ModelCatalog`) и §20 карты v1.1 (см. §4).

### 2.6 `check` — B10/R-127 валидация реестра

```bash
python -m core_02.missing_registry check
```

Проверяет инварианты: обязательные поля, kind/status enums, `implemented ⇒ implementation непустой`, `prompt_written ⇒ prompt_path непустой`, `related_prompts` (если есть) — список непустых строк. **Exit 0** = валиден, **exit 1** = нарушения (список в stdout), **exit 2** = не удалось открыть реестр.

### 2.7 `add-related-prompt` + конвенция `prompt_path` (multi-prompt, promt 088)

```bash
python -m core_02.missing_registry add-related-prompt <item_id> --prompt <path> [--prompt <path> ...***REMOVED***
python -m core_02.missing_registry mark-implemented <item_id> --implementation <path> --related-prompt <path> [--related-prompt ...***REMOVED***
```

**Конвенция полей (source of truth, promt 088 / v5.189.19):**

- `prompt_path` — **primary/implementation-промт** (ровно один): промт, по которому реализован элемент. При `mark-implemented --prompt` заменяется на актуальный implementation-промт.
- `related_prompts` — **forensics/design/supporting промты** (список): предшествующие промты, чей machine-readable след НЕ должен теряться при замене `prompt_path`.

**Правило про forensics-след (CAN-17 / traceability):** если элемент реализован по цепочке промтов (напр. forensics 084 → implementation 085), то при `mark-implemented --prompt <implementation>` forensics-промт добавляется в `related_prompts` (`add-related-prompt` или `mark-implemented --related-prompt`). Иначе forensics-след остаётся только в free-text `description` + §20-сноске — без структурированного поля (это был GAP 09_FUTURE_GAPS row #8, закрыт v5.189.19).

**Пример (intelligence_integration, v5.189.19):**

```bash
python -m core_02.missing_registry add-related-prompt intelligence_integration \
    --prompt pompts_11/084_19_intelligence_integration_forensics.md
# prompt_path=085_19_close_intelligence_loop.md (implementation) + related_prompts=[084_...forensics.md***REMOVED***
```

---

## 3. Exit Codes

| Сценарий | Exit | Примечание |
|----------|-----:|------------|
| Любая успешная операция (list/seed/register/mark-*) | 0 | |
| `check` с нарушениями B10/R-127 | 1 | список нарушений в stdout |
| Ошибка открытия/чтения реестра | 2 | битый YAML / нет файла |
| `register` без `--kind` | 2 | argparse error (required) |
| `mark-prompt-written`/`mark-implemented` несуществующего item | 1 | KeyError → сообщение |

---

## 4. Регистрация нового элемента — пошаговый гайд

```bash
# 1. Зафиксировать (register-first — ДО любой реализации!):
python -m core_02.missing_registry register my_cap --kind tool --factory research \
    --description "что за способность и где нужна"

# 2. Написать промт на реализацию (pompts_11/promtNN.md), затем:
python -m core_02.missing_registry mark-prompt-written my_cap --prompt pompts_11/075_04_research_web_capability.md

# 3. Реализовать по промту (additive, CAN-16), затем:
python -m core_02.missing_registry mark-implemented my_cap --implementation scripts_01/my_cap.py
#    Если у элемента была цепочка промтов (forensics/design) — сохранить их machine-readable след:
python -m core_02.missing_registry add-related-prompt my_cap --prompt pompts_11/0NN_19_...forensics.md

# 4. Пополнить закрытый словарь (если это genuine capability-токен):
#    - KNOWN_CAPABILITIES (core_02/blueprint_v3.py) += токен
#    - ModelCatalog (core_02/router.py) += токен  (синхронно! drift-тест падает иначе)

# 5. Обновить §20 карты v1.1: «промт написан» → «✅ реализовано»
#    (реестр и карта должны быть зеркальны — consistency_check ловит расхождение)

# 6. Финальная проверка:
python -m core_02.missing_registry check
python -m pytest tests_09/test_missing_registry.py tests_09/test_consistency_check.py -q
```

---

## 5. Troubleshooting Matrix

| Симптом | Root cause | Fix |
|---------|-----------|-----|
| `check` → exit 1 «implemented ⇒ implementation непустой» | `mark-implemented` вызван без `--implementation` | Перевызвать с `--implementation scripts_01/x.py` |
| `check` → exit 1 «prompt_written ⇒ prompt_path непустой» | `mark_prompt_written` без `--prompt` (CLI требует) / ручная правка YAML | Вызвать CLI с `--prompt`; не править YAML руками |
| `register` → exit 2 missing `--kind` | argparse required | Указать `--kind {capability,tool,engine,forge,role,factory,module,registry,system***REMOVED***` |
| Статус «застрял» на registered, хотя дизайн готов | lifecycle требует явного перехода | `register item --status design_ready` (или seed для канонических #1/#2) |
| §20 карты и YAML-реестр расходятся | ручная правка одной стороны | `python -m scripts_01.consistency_check` → `missing_registry_sync` issues; привести обе стороны к одному |
| `seed` не добавляет запись | запись уже есть (идемпотентность) | Это ожидаемо; `list --json` для проверки |

---

## 7. Кросс-ссылки

- **Канон:** [`AGENTS.md`***REMOVED***(../../AGENTS.md) §5 REGISTER-FIRST
- **Модуль:** [`core_02/missing_registry.py`***REMOVED***(../../core_02/missing_registry.py) (MissingItem, MissingRegistry, `main()`)
- **Реестр:** `data_13/missing_registry.yaml`
- **Карта:** [`docs_10/engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md`***REMOVED***(../engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md) §20 (Missing Capabilities)
- **Сверка:** [`scripts_01/consistency_check.py`***REMOVED***(../../scripts_01/consistency_check.py) → `check_missing_registry_sync` (10-я проверка)
- **Тесты:** [`tests_09/test_missing_registry.py`***REMOVED***(../../tests_09/test_missing_registry.py) (27: lifecycle, schema, CLI, seed) + [`tests_09/test_consistency_check.py`***REMOVED***(../../tests_09/test_consistency_check.py) (TestCheckMissingRegistrySync)
- **Примеры реализаций:** `research_web` (Missing Capability #6, `pompts_11/075_04_research_web_capability.md`), `lisa_estimator` (Missing Capability #7, `pompts_11/076_13_lisa_estimator_capability.md`) — обе ✅ implemented, lifecycle закрыт через CLI.

---

## 6. `backfill: bool` — retroactive-registration discipline (v5.189.49 + v5.189.51)

**Контекст:** lifecycle `registered → design_ready → prompt_written → implemented` (AGENTS.md §5 REGISTER-FIRST) предполагает GREENFIELD элементы — такие, которые проходят все три транзишена. **Но некоторые элементы существовали ДО создания реестра** (factory_base, lisa_calibration_store, role_executor) или были мигрированы без полного lifecycle (например, модуль вне canon §20, добавленный обходным путём). Такие entries — **retroactive-registrations**.

Проблема (по v5.189.46 audit): до v5.189.49 эти entries помечались только free-text `⚠️ BACKFILL (…)` в `description` — без machine-readable flag'а. Downstream queries, фильтрующие по `backfill=true`, SILENTLY их skip'али. Discipline была непрозрачна.

Решение (v5.189.49 + CON-63/CON-64): backfill стал типизированным `bool` полем в `MissingItem`, проверяемым реестром по B10/R-127 инвариантам. **Поддерживается в v5.189.51** `check_backfill_signatures()` heuristic в `consistency_check.py` — soft WARNING для retro-omit cases.

### 7.1 Как регистрировать задним числом (`register --backfill --status implemented`)

```bash
python -m core_02.missing_registry register <item_id> --kind <kind> \
    --factory <factory> --status implemented --backfill \
    --implementation <path/to/script.py> \
    --description "retroactive registration: <existed before registry / migrated>"
```

**Семантика `--backfill`:**

- Означает: элемент реально существовал/работал ДО его фиксации в реестре; lifecycle пропущен по объективной причине, и **это явно зафиксировано** как `backfill: true` в YAML.
- Требует парный `--status implemented` (B10-инвариант: `backfill=true ⇔ status==implemented` — элемент, который не implemented, не имеет смысла как retroactive).
- Требует `--implementation <path>` (по правилу B10 R-127: `status=implemented ⇒ implementation непустой`).
- CLI бросает `ValueError` при нарушении → сообщение: ``error: backfill=True requires status=='implemented'; got ...`` + exit 1 (не traceback).

**Идемпотентность:** повторный `register --backfill --status implemented` для существующего `item_id` НЕ откатывает существующий `backfill: true` (lifecycle + backfill — facts, не откатываются). Lifecycle `mark_implemented` тоже **не** трогает `backfill` (когда нет --backfill, backfill остаётся как был).

### 7.2 B10-инварианты (R-127 schema validation)

`MissingRegistry.validate_schema()` проверяет:

| Инвариант | Условие | Где проверяется |
|----------|--------|---------|
| **B10-a: тип поля** | `backfill` обязан быть `bool` (НЕ строка `'true'`/`'false'`, NOT int `0/1`, НЕ `None`-эквивалент). | `validate_schema()` — строковое значение ловится как violation. |
| **B10-b: семантический** | `backfill=true` ⇒ `status == 'implemented'`. Обратное: `status != 'implemented'` при `backfill=true` — violation. | `validate_schema()` — `(backfill is True) and (status != IMPLEMENTED)` → violation. |
| **B10-c: ранний guard** | `register_missing(backfill=True, status != IMPLEMENTED)` → `ValueError` при сохранении. | В `register_missing()` ДО записи. |
| **B10-d: existing-state preservation** | При update существующего item: `backfill` не откатывается к `False`, если он был `True` (`bool(backfill or existing.get("backfill", False))`). | В `register_missing()` update-ветка. |

**Тесты:** `tests_09/test_missing_registry.py::test_validate_schema_*` + `test_register_backfill_true_requires_implemented` (6 тестов добавлено в v5.189.49 + связанные проверки).

**Также:** все ранее существовавшие инварианты (см. §2.6 `check`) продолжают работать. `backfill: bool` — **дополнительный** уровень discipline, а не замена существующего.

### 7.3 Backfill-аудит через `registered_at == updated_at`

`scripts_01/consistency_check.py::check_backfill_signatures()` (v5.189.51) — heuristic для surfaces retro-omit:

```bash
# 1. Быстрый spot-check (raw JSON):
python3 scripts_01/consistency_check.py --json | jq '.backfill_signature'

# 2. Полный consistency run (включая soft warnings):
python3 scripts_01/consistency_check.py
#   Ищите в stdout ['backfill_signature'***REMOVED*** список warnings (если есть).
```

**Heuristic:** entries, удовлетворяющие **ВСЕМ** условиям, FLAGGED как WARNING (severity='warning'):

1. `status == implemented` — уже реализованные entries.
2. `registered_at == updated_at` ISO strings (ВНИМАНИЕ: second-precision collision — легитимные single-shot updates тоже match).
3. `backfill` НЕ равно `True` (либо отсутствует, либо =False).
4. **НЕ** in `_SEED` (canonical entries pre-date backfill:bool discipline — exempt).

**Пример вывода** (для гипотетического non-SEED модуля `forge_chain_metrics`, который был мигрирован БЕЗ полного lifecycle):

```python
[
    {
        "check": "backfill_signature",
        "severity": "warning",
        "doc": "data_13/missing_registry.yaml",
        "item_id": "forge_chain_metrics",
        "reason": "status=implemented + registered_at==updated_at without backfill:true — looks retroactive. Re-register with `--backfill` (or bump updated_at to differ from registered_at)."
    ***REMOVED***
***REMOVED***
```

> **⚠️ SEED-entries exempt:** `research_web`, `lisa_estimator` и другие из `_SEED` в `core_02/missing_registry.py` (`seed_defaults()`) — CANONICAL pre-backfill-discipline entries; они НЕ flagged heuristic, так как `backfill` для них default=`False` не означает «forgot» — сознательно оставлено для трассировки исторического присутствия. Если вы хотите поверхность retro-omit в _SEED — fix в `is_canonical_seed_item()` (deferred).

**Severity:** WARNING (NOT violation). Soft-signal semantic per user intent 'предупреждение':
- **Не** counted в `report["total_issues"***REMOVED***` → `consistent=True` сохраняется даже при warnings (CI-friendly).
- **Виден** в `report["backfill_signature"***REMOVED***` для review.
- **Audit-friendly:** developer получает чёткий signal для fix — никакой tool не теряет retro-entries silently.

**Если retroactive registration legitimate** (элемент существовал до реестра), UPDATE-семантика (НЕ INSERT):

```bash
# Re-register существующего item с флагом --backfill (обновляет поле backfill=true без overwriting status/implementation):
python -m core_02.missing_registry register forge_chain_metrics --kind tool --factory code \
    --status implemented --backfill --implementation scripts_01/forge_chain_metrics.py
# (status_rank guard: --status implemented сохраняется; backfill: true добавляется в YAML;
#  consistency_check --json теперь покажет backfill_signature=[***REMOVED*** для этого slug)
```

> **UPDATE не INSERT:** CLI `register` для существующего `item_id` (например, `mark-implemented` уже вызван ранее) — просто добавляет `backfill: true` в data-поля, lifecycle остаётся там где был. `KeyError` НЕ броcается (MarkFirst register_first принцип: re-register idempotent on existing).

**Если collision легитимна** (запись действительно прошла single-shot): бампните `updated_at` в YAML или просто оставьте warning — CI не сломается.

**Подробнее:**
- Имплементация: [`scripts_01/consistency_check.py`***REMOVED***(../../scripts_01/consistency_check.py) → `check_backfill_signatures(workspace)`.
- Тесты: [`tests_09/test_consistency_check.py`***REMOVED***(../../tests_09/test_consistency_check.py) → `TestBackfillSignature` (5 contract tests).
- GLOSSARY term: [`docs_10/core/GLOSSARY.md` §13***REMOVED***(../../docs_10/core/GLOSSARY.md) → `backfill (MissingRegistry)` (v1.4.0).
- LESSONS: [`core_02/LESSONS.md`***REMOVED***(../../core_02/LESSONS.md) → CON-63 (register-first discipline), CON-64 (same-pass-glossary).

---

*Compiled 2026-08-11 by Buffy. Maintenance: при добавлении канонической записи в §20 карты — обновить `seed_defaults()` в `core_02/missing_registry.py` и этот runbook (таблица §2.2).*
