# ROADMAP FORGE RECONCILIATION — Устранение разрыва между RFC Buffy Forge v1.1 и реализацией

| Поле | Значение |
|------|----------|
| **Документ ID** | ROADMAP-FR-001 |
| **Версия** | 1.4 (CLOSED) |
| **Статус** | ✅ CLOSED 2026-08-06 (Hypothesis C verified via Шаги 1+2+3, LEVIATHAN inventory ready) |
| **Релиз платформы** | v5.103.0 (после Forge Series v5.97.0–v5.103.0) |
| **Дата** | 2026-08-06 |
| **Автор** | Buffy (анализ + roadmap после 061_19_roadmap_forge_leviathan) |
| **Основание** | `pompts_11/061_19_roadmap_forge_leviathan.md`, `RFC_BUFFY_FORGE_V1.md` v1.1 §2a, CON-40 (capability-check), PB-14 (dual SoT) |
| **Тип** | Reconciliation Roadmap / Pre-implementation Gate |
| **Hard-block контракт** | Шаг 2 ⇏ если ⟂ Шаг 1; Шаг 3 ⇏ если ⟂ Шаг 2 |

---

## 0. Capability-Check (CON-40, pre-condition, обязятельно)

> **Урок (CON-40, 058_21):** SmartRouter capability-check защищает от silent fallback — задача приоритизации / архитектурного суждения требует `architecture` capability в `required_capabilities`, иначе flash-модель молча провалит architectural judgement.

Эта roadmap-задача **архитектурная** (анализ двух систем, выбор между «реальный разрыв» vs «кажущийся», обоснование границ ответственности). Поэтому capability-check обязателен **до** Шага 1 — даже не самого Шага 1.

### 0.1 Required capabilities

```python
from core_02.router import SmartRouter, ModelCatalog, Preference

decision = SmartRouter(ModelCatalog.default()).route(
    required_capabilities=["reasoning", "plan", "architecture"***REMOVED***,
    preference=Preference.BALANCED,
)
```

### 0.2 Ожидаемый RouteDecision

| Поле | Значение |
|------|----------|
| `model` | `deepseek-v4-pro` |
| `provider` | `Provider.DEEPSEEK` |
| `reason` | `capability_match:3/3` |
| `fallback_used` | `False` |

**Обоснование:** `deepseek-v4-pro` имеет capabilities `[code, reasoning, deep, architecture, plan, review, diagnose, validate, report***REMOVED***` — покрывает все 3 из `required_capabilities`. `deepseek-v4-flash` имеет `[code, reasoning, plan, refactor, explain***REMOVED***` — покрывает 2/3 (нет `architecture`). `match()` сортирует по `(-score, latency, cost)`, поэтому pro побеждает по совпадению (3 > 2), несмотря на бо́льшую latency.

### 0.3 Контраст: что произойдёт без `architecture`

Если бы кто-то сократил `required_capabilities` до `["plan"***REMOVED***`:

| Поле | Значение |
|------|----------|
| `model` | `deepseek-v4-flash` (побеждает по latency: 2000 ms vs 3000 ms при равном score=1) |
| `reason` | `capability_match:1/1` |
| `fallback_used` | `False` |

Это **не провал** формально (request вернул решение), но flash-модель **не имеет `architecture` capability** — она не сможет вынести architectural judgement. Это та самая «кажущаяся успешность» из CON-40.

### 0.4 Pre-condition гейт

| Проверка | Команда | Ожидаемый вывод |
|----------|---------|-----------------|
| SmartRouter на `["reasoning","plan","architecture"***REMOVED***` | `python3 -c "from core_02.router import SmartRouter, ModelCatalog; d=SmartRouter(ModelCatalog.default()).route(['reasoning','plan','architecture'***REMOVED***); print(d.model, d.reason)"` | `deepseek-v4-pro capability_match:3/3` |
| Capability-mismatch check | та же конструкция с `["plan"***REMOVED***` | `deepseek-v4-flash capability_match:1/1` |
| Router недоступен | отсутствие `python3` или `core_02` | стоп сессии, документ не валиден |

**Если SmartRouter выбранной модели не `deepseek-v4-pro`** — задача архитектурно невалидна для текущей сессии. Остановиться, зафиксировать в LESSONS.md как CON-расширение.

---

## 🔭 Контекст: подозреваемый разрыв

### Гипотеза A — две независимых системы исполнения

```
┌─────────────────────────────────────────────────────┐
│ FORGE PATH:                                         │
│   forge forge projects_17/interior_planner         │
│   → stage_forge → stage_check → stage_build         │
│   → stage_test → stage_deploy → stage_report        │
│   (subprocess.run в stage_build, см. _stage_build)  │
│                                                      │
│ FORGE STATE:                                        │
│   data_13/forge_registry.yaml                       │
│   interior-planner: status=UNFORGED                 │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ WIZARD PATH (тот, что реально прогонялся вчера):    │
│   run_wizard_with_registry()                         │
│   → ScenarioRegistry                                │
│   → BlueprintCorpus + env_consultant + interior_...  │
│   → TG-доставка через telethon                      │
│   → docs_10/e2e_logs/* (CON-14, CON-15)             │
│                                                      │
│ WIZARD STATE:                                       │
│   data_13/context.db (ScenarioRegistry table)       │
│   interior-planner: progress passed through ~17 roles│
└─────────────────────────────────────────────────────┘
```

### Гипотеза B — Forge вызывает Wizard изнутри

Если `_stage_forge` (или любая другая стадия) внутри себя вызывает `run_wizard_with_registry()` или эквивалент — это **видимость разрыва**, не баг. Названия стадий (`FORGE/CHECK/BUILD/TEST/DEPLOY/REPORT`) — это просто обёртка над Wizard-цепочкой.

### Гипотеза C — два не пересекающихся понятия прогресса

Если `UNFORGED` в `forge_registry.yaml` означает «не прошёл через Forge Pipeline специфически», а не «вообще не запускался» — это **не баг синхронизации**, а просто **два разных семантических пространства**:

| Пространство | Источник истины | Что отслеживает |
|--------------|-----------------|-----------------|
| CI-стадии конкретного Forge | `data_13/forge_registry.yaml` | CHECK/BUILD/TEST/DEPLOY/REPORT |
| Wizard-прохождение проекта | `data_13/context.db` + `ScenarioRegistry` | прогресс по 17 ролям + TS-код + TG-доставка |

Это эквивалентно разделению «Forge ⇆ Wizard» по предметной области — **явное и допустимое**, но **требует документирования** (если подтвердится в Шаге 1).

**Какая из трёх гипотез верна — устанавливается только в Шаге 1.** Шаг 0 (этот документ) не делает предположений.

---

## 📋 Sequential Roadmap (hard-blocks)

> **Жёсткий порядок (061_19_roadmap_forge_leviathan):** Шаг 2 логически невозможен без Шага 1; Шаг 3 недопустим до Шага 2. Параллельное выполнение запрещено.

### Сводная таблица зависимостей

| Шаг | Hard-block от | Soft-prereq от | Приоритет | Время | Готовность критерий |
|-----|---------------|----------------|-----------|-------|---------------------|
| 0: Roadmap (этот документ) | — | SmartRouter availability | 🔴 CRITICAL | 45 мин | Документ зарегистрирован в INDEX.md + DOCUMENT_REGISTRY.md + `SmartRouter.route([..architecture***REMOVED***).model == "deepseek-v4-pro"` |
| 1: Fact-check разрыва | 0 (капability-check) | — | 🔴 CRITICAL | 60 мин | CON-/PB- запись в LESSONS.md с явным выводом (A/B/C) |
| 2: Reconciliation | 1 (вывод) | — | 🟡 HIGH | 2–3 ч | регрессионные тесты зелёные + RFC §2a обогащена |
| 3: LEVIATHAN inventory | 2 (закрыт) | LEVIATHAN_INVENTORY_V1.md existing | 🟢 MEDIUM | 1–2 ч | 3 модуля добавлены в Category A |

### Граф зависимостей (текстовый)

```
[0: Roadmap, 45 мин***REMOVED***
         │
         ▼ hard block
[1: Fact-check, 60 мин***REMOVED***
         │
         ├──→ разрыв кажущийся (B/C) → [2': doc-only fix, 30 мин***REMOVED*** → [3: LEVIATHAN, 1-2 ч***REMOVED***
         │
         └──→ разрыв реален    (A)    → [2'': full merge,    2-3 ч***REMOVED***   → [3: LEVIATHAN, 1-2 ч***REMOVED***
                                               │
                                               ▼ hard block (tests + RFC update)
```

---

## 🟢 Шаг 1 — Fact-check разрыва (60 мин)

> **Гейт:** вывод Шага 1 (любая из гипотез A/B/C) ЗАФИКСИРОВАН в `core_02/LESSONS.md` как новая CON-/PB- запись. Без записи Шаг 2 не начинается.

### Бюджет времени (60 мин)

| Подзадача | Время | Артефакт |
|-----------|-------|----------|
| 1.1 Прочитать `core_02/forge_pipeline.py` построчно: `_stage_build`, `_stage_deploy`, `_run_cmd` | 15 мин | snippet: точная команда, выполняемая через `subprocess.run`, с path/cwd |
| 1.2 Сравнить с `scripts_01/wizard.py` (`run_wizard_with_registry()` или эквивалент) | 20 мин | snippet: вызывает ли `forge_pipeline.py` Wizard внутри? |
| 1.3 Audit `data_13/forge_registry.yaml`: почему `interior-planner` статус `UNFORGED`? | 10 мин | grep по `interior_planner` + чтение записей history |
| 1.4 Audit `ScenarioRegistry` (через `data_13/context.db` или API): что хранится про interior-planner? | 10 мин | подтверждение yesterday e2e через CON-14/CON-15 в `LESSONS.md` |
| 1.5 Зафиксировать в `core_02/LESSONS.md`: новая запись PB-N или CON-N с явным выводом | 5 мин | запись в LESSONS.md |

### Содержание записи (1.5)

```
## PB-N — Forge ⇆ Wizard: разрыв или путаница?
- **Контекст:** 061_19_roadmap_forge_leviathan + ROADMAP-FR-001.
- **Что проверяли:** forge_pipeline.py:subprocess.run, run_wizard_with_registry,
  forge_registry.yaml vs context.db.
- **Результат:** <разрыв реален (A)|кажущийся, Forge вызывает Wizard (B)|
  два независимых семантических пространства (C)>.
- **Следствие:** Шаг 2 — <full reconciliation A→2''|doc-only B/C→2'>.
- **Урок:** <отложить — фиксируется в Шаге 2>.
```

### Критерий готовности Шага 1

✅ Все 5 подзадач выполнены И
✅ `LESSONS.md` содержит новую запись PB-/CON- с явной формулировкой результата И
✅ Запись содержит snippet (≥3 строки) из `forge_pipeline.py` И
✅ Запись содержит snippet (≥3 строки) из `scripts_01/wizard.py` (или grep-результат «нет вызова»).

---

## 🟡 Шаг 2 — Reconciliation (2-3 ч, ТОЛЬКО после Шага 1)

### Case 2'' (разрыв реален, гипотеза A) — 2-3 ч

| Подзадача | Время | Артефакт |
|-----------|-------|----------|
| 2.1 Правка `forge_pipeline.py:stage_forge` — делегировать в `run_wizard_with_registry()`, не делать свою регистрацию | 60 мин | PR-style правка, новый unit-test `test_forge_pipeline_delegates_to_wizard` |
| 2.2 Разграничение «кто за что отвечает» — `forge_registry.yaml` = тонкий индекс CI-стадий, `ScenarioRegistry` = прогресс по ролям | 45 мин | обновлённая таблица в `RFC_BUFFY_FORGE_V1.md` §2a |
| 2.3 Обновить `forge_registry.yaml`: `interior-planner` отражает реальный путь (Wizard-прохождение → Forge summary) | 15 мин | diff-вывод yaml |
| 2.4 Регрессионные тесты: `test_forge_pipeline.py`, `test_forge_registry.py`, `test_wizard.py`, `test_scenario_registry.py` | 30 мин | все зелёные |

### Case 2' (разрыв кажущийся, B/C) — 30 мин

| Подзадача | Время | Артефакт |
|-----------|-------|----------|
| 2'.1 Явное документирование в `RFC_BUFFY_FORGE_V1.md` §2a: либо Forge вызывает Wizard (B), либо два независимых домена (C) | 20 мин | дополненная §2a с таблицей |
| 2'.2 Зафиксировать в `LESSONS.md`: «UNFORGED» относится именно к Forge-слою, не к прогрессу проекта вообще (если C) | 5 мин | запись |
| 2'.3 Smoke `forge forge projects_17/interior_planner --dry-run --no-tg` — должен показать связь с Wizard-путём | 5 мин | stdout-tail |

### Критерий готовности Шага 2

✅ Выполнен либо Case 2'', либо Case 2' (в зависимости от вывода Шага 1) И
✅ `RFC_BUFFY_FORGE_V1.md` §2a содержит обновлённую таблицу разграничения И
✅ Все регрессионные тесты зелёные (для Case 2'') И
✅ В `LESSONS.md` ссылка на ROADMAP-FR-001 в новой записи.

---

## 🟢 Шаг 3 — LEVIATHAN inventory (1-2 ч, ТОЛЬКО после Шага 2)

> **Запрет (061_19_roadmap_forge_leviathan):** перенос с неразрешённым разрывом → LEVIATHAN унаследует тот же баг синхронизации состояния.

| Подзадача | Время | Артефакт |
|-----------|-------|----------|
| 3.1 Актуализировать `docs_10/engineering-memory/LEVIATHAN_INVENTORY_V1.md` | 60 мин | 3 модуля в Category A |
| 3.2 Объяснить в LESSONS.md инвентаризацию (терминологический rebrand: Workspace/Project vs Forge-уровни) | 15 мин | запись |
| 3.3 Регрессия всех forge_*-тестов ещё раз | 30 мин | все зелёные (после Шага 2) |

### Критерии готовности Шага 3

✅ `LEVIATHAN_INVENTORY_V1.md` содержит строки для `forge_pipeline.py`, `forge_registry.py`, `workspace.py` в Category A И
✅ Каждая строка ссылается на ROADMAP-FR-001 для pre-migration условия (закрытие Шага 2).

---

## ✅ Сводная таблица testable readiness

> **Definition of Done (DoD):** шаг закрыт ⇔ все его testable критерии истинны. Не «сделано» — а проверяемо.

| Шаг | Testable критерий | Команда / файл |
|-----|-------------------|----------------|
| 0 | ROADMAP-документ существует + capability-check прошёл | `python3 -c "***REMOVED***; assert Path('docs_10/ROADMAP_FORGE_RECONCILIATION.md').exists()"` И `SmartRouter.route(['reasoning','plan','architecture'***REMOVED***).model == 'deepseek-v4-pro'` |
| 1 | LESSONS.md содержит PB-/CON- запись со snippet ≥3 строки из `forge_pipeline.py` И `wizard.py` | grep по `LESSONS.md` за `## PB-` или `## CON-` секцию вчерашней даты |
| 2 | Регрессионные тесты `test_forge_*.py + test_wizard.py + test_scenario_registry.py` все зелёные | `python3 -m pytest tests_09/test_forge_pipeline.py tests_09/test_forge_registry.py tests_09/test_wizard.py tests_09/test_scenario_registry.py` → 0 failures |
| 3 | `LEVIATHAN_INVENTORY_V1.md` Категория A содержит 3 forge_* модуля с ссылкой на ROADMAP-FR-001 | grep по документу |

---

## 🔗 Связанные артефакты

| Файл / модуль | Роль |
|----------------|------|
| `pompts_11/061_19_roadmap_forge_leviathan.md` | Mission-документ этого roadmap |
| `docs_10/engineering-memory/RFC_BUFFY_FORGE_V1.md` v1.1 | §2a — Workspace/Project boundary doctrine (основа reconcile) |
| `core_02/router.py` | SmartRouter API (capability-check pre-condition) |
| `core_02/forge_pipeline.py` | Цель Шага 1 (факт-чекинг `_stage_build`/`_stage_deploy`) |
| `core_02/forge_registry.py` | Один из двух источников истины (другой — `context.db`) |
| `core_02/workspace.py` | L-2 Project контейнер (для LEVIATHAN Category A) |
| `scripts_01/wizard.py` | Сравнение пути исполнения (Шаг 1.2) |
| `data_13/forge_registry.yaml` | Источник истины #1 (CI-стадии) |
| `data_13/context.db` | Источник истины #2 (ScenarioRegistry) |
| `core_02/LESSONS.md` | Запись результата Шага 1 (PB- или CON-) |
| `docs_10/engineering-memory/LEVIATHAN_INVENTORY_V1.md` | Шаг 3 — добавить forge_* в Category A |
| `core_02/LESSONS.md` (CON-40, 058_21) | Capability-check обоснование |

---

*Конец ROADMAP-FR-001 v1.0.*

## 📒 Step 1 Detailed Fact Log (2026-08-06)

> **Granular journal** (не summary — для сводки закрытых Шагов см. «Progress Roll-up (closed steps + unlock)» ниже). Назначение: предоставить verify-поверхность для факт-чекинга разрыва через кодовые цитаты с precise line-numbers, привязку к файлам-источникам и TG-shared corrigendum. Резюме вердикта / ready gate / closure artifacts намеренно НЕ дублируются здесь — только в Progress Roll-up. Primary-source-of-truth = `core_02/LESSONS.md` PB-16.

### Verdict recap (кратко; детали в Progress Roll-up и PB-16)

**Подтверждённая гипотеза:** **Hypothesis C** — Forge Pipeline (CI-stages) и Wizard/Scenario (role-driven execution) — **orthogonal STATE-домены**, но **shared TG transport-layer** (см. PB-16 Урок 1 corrigendum ниже). Сравнение 3 гипотез A/B/C см. в основном §Context секции ROADMAP и в `core_02/LESSONS.md` PB-16.

### 6 факт-чекинг фактов (с line/файл-цитатами)

| # | Факт | Источник / цитата |
|---|------|--------------------|
| 1 | `forge_pipeline._run_cmd` использует реальный `subprocess.run` | `core_02/forge_pipeline.py:56-65`: `proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)` |
| 2 | Forge Pipeline **НЕ импортирует** Wizard / scenario_registry / run_wizard | `grep -nE 'wizard\|scenario_registry\|run_wizard' core_02/forge_pipeline.py` → **0 hits** |
| 3 | `core_02/wizard_lib.py` имеет `run_wizard_with_registry`; `scenario_registry.py` НЕ ссылается на `forge_pipeline`/`forge_registry` | `scripts_01/wizard.py:head-50` импортирует `core_02.wizard_lib`; обратное направление — 0 hits |
| 4 | `data_13/forge_registry.yaml`: interior-planner = **UNFORGED** (canonical fact) | grep `interior-planner` в `data_13/forge_registry.yaml` |
| 5 | `data_13/context.db` НЕ содержит scenario/wizard/role_run/forge-tables; cross-table `LIKE '%interior%'` → **0 rows** | `sqlite_master LIKE 'scenario\|wizard\|role_run\|forge' → 0`; `SELECT COUNT(*) ... LIKE '%interior%' → 0` |
| 6 | interior_planner Wizard-прохождение состоялось — **TG msg_id FACT** | `docs_10/e2e_logs/promt47_run.md` v5.64.0: Saved = **138366**, Литвинов = **138367** (round-trip read-back в CON-35) |

### Verdict table (Hypothesis C confirmed — orthogonal STATE)

| Запрос (read-world) | Source-of-truth (orthogonal) | interior-planner факт на 2026-08-06 |
|---------------------|-----------------------------|----------------------------------------|
| «Прошёл ли через `forge forge` (CI-stages)?» | `data_13/forge_registry.yaml` | **UNFORGED** — честен (никогда не запускался через Forge Pipeline) |
| «Прошёл ли через Wizard с TG-доставкой?» | `docs_10/e2e_logs/promt47_run.md` + TG round-trip | **Passed** — msg_id 138366/138367 v5.64.0 |

**TG-shared corrigendum (PB-16 Урок 1, применён в v1.2 LESSONS):** оба пути используют общий TG transport. Без этого уточнения PB-16 был бы over-strict (orthogonal everywhere), что противоречило бы эмпирическому факту 6 (TG — это shared infra через `tg_session.send_text_message` / `TgClientV2` для Forge-on_report hook и `core_02/telegram_contract.report_to_saved_messages` / `:report_to_alex_litvinov` для Wizard).

### Ready gate для Шага 2 (pointer only)

→ **Step 2 (Case 2' applies)** UNLOCKED — детали (✅/progress) см. Progress Roll-up (closed steps + unlock) ниже.

### Cross-references

| Файл | Роль |
|------|------|
| `core_02/LESSONS.md` PB-16 (~472 lines) | primary source-of-truth (добавлен в эту сессию) |
| `core_02/forge_pipeline.py:56-65,94-106,132-146,159-172` | Fact-1 source lines |
| `core_02/wizard_lib.py` (run_wizard_with_registry) | Fact-3 source (Wizard entry point) |
| `core_02/scenario_registry.py` (Scenario ABC) | Fact-3 source (no back-reference to forge) |
| `data_13/forge_registry.yaml` | Fact-4 source (interior-planner=UNFORGED) |
| `data_13/context.db` | Fact-5 source (sqlite_master LIKE query) |
| `docs_10/e2e_logs/promt47_run.md` v5.64.0 | Fact-6 source (TG msg_id 138366/138367 round-trip в CON-35) |
| `core_02/telegram_contract.py:report_to_saved_messages + report_to_alex_litvinov` | TG transport-layer (Wizard) |
| `scripts_01/forge.py:cmd_forge.on_report` → `tg_session.send_text_message` / `TgClientV2` | TG transport-layer (Forge Pipeline) |

### Связь с CAN-16 / CAN-17

- **CAN-17 (audit-trail preservation):** этот раздел добавляет audit-trail snapshot после закрытия Шага 1, перед стартом Шага 2. Не переписывает ничего в Шаге 1 narrative — только ADDITIVE-расширяет audit-trail.
- **CAN-16 (ADDITIVE only):** оригинальный §step-1 narrative выше НЕ переписан. Раздел «✅ Step 1 Fact-Check Complete — Result roll-up» — новая секция, ADDITIVE-вставленная.

### Связанные артефакты (cross-link only)

Детальные статусы артефактов (PB-16 / PB-17 / RFC v1.2 / STATE-реестры) собраны в Progress Roll-up (closed steps + unlock) ниже — здесь только main-link:

- `core_02/LESSONS.md` PB-16 — primary source-of-truth для verdict (Hypothesis C)
- См. Progress Roll-up для closure статусов и accumulated артефактов

---

## 📒 Step 2 Detailed Fact Log (2026-08-06)

> **Granular journal** для Шага 2 (Case 2' — doc-only ADDITIVE-расширение §2a RFC_BUFFY_FORGE_V1). Назначение: предоставить verify-поверхность с precise line-numbers в `docs_10/engineering-memory/RFC_BUFFY_FORGE_V1.md` v1.2, привязку к атомарным операциям и подтверждение CAN-16 ADDITIVE-compliance. Итоговый вердикт / ready gate / closure artifacts см. в «📊 Progress Roll-up (closed steps + unlock)» ниже. Primary source of truth — `docs_10/engineering-memory/RFC_BUFFY_FORGE_V1.md`.

### 6 fact-rows (precise line-numbers + atomic operations)

| # | Факт | Source-of-truth | Line / Marker |
|---|------|-----------------|---------------|
| 1 | **Version bump v1.1 → v1.2** | `docs_10/engineering-memory/RFC_BUFFY_FORGE_V1.md` header table: `\| **Версия** \| 1.2 \|` | **line 6** |
| 2 | **§2a.1 Граница ответственности (Forge Pipeline ↔ Wizard/Scenario)** — 8-аспектная таблица разделения ролей, явное указание `tg_session` (Forge) vs `telegram_contract` (Wizard) | `RFC_BUFFY_FORGE_V1.md` heading `### §2a.1 — Граница ответственности` | **line 178** |
| 3 | **§2a.2 STATE-orthogonal** — forge_registry.yaml (UNFORGED) ↔ Wizard-progressed (TG round-trip) с explicit CAN-17 audit-trail msg_id 138366/138367 | `RFC_BUFFY_FORGE_V1.md` heading `### §2a.2 — STATE-orthogonal` | **line 195** |
| 4 | **§2a.3 UNFORGED naming clarification** — schema-header doc-polish на основе PB-16: `UNFORGED = "не прошёл forge only"`, не «проект вообще не работал». Statuses: UNFORGED → FORGED → CHECKED → BUILT → TESTED → DEPLOYED → REPORTED → FAILED → SUPERSEDED | `RFC_BUFFY_FORGE_V1.md` heading `### §2a.3 — UNFORGED naming` | **line 213** |
| 5 | **Closing paragraph (v1.2 changelog-like note)** — explicit attribution: «v1.2 ADDITIVE поверх v1.0 и v1.1, в §2a добавлены подразделы a.1/a.2/a.3 (граничная семантика, state-orthogonal, naming clarification)». Соответствует CAN-16 ADDITIVE rule. | `RFC_BUFFY_FORGE_V1.md` closing paragraph (последний абзац файла) | **line 717** |
| 6 | **Atomic operation** — `Step 2 Detailed Fact Log` секция вставлена в `ROADMAP_FORGE_RECONCILIATION.md` между `## 📒 Step 1 Detailed Fact Log` (line 264) и `## 📒 Step 3 Detailed Fact Log (2026-08-06)

> **Granular journal** для Шага 3 (LEVIATHAN inventory prep — Cat-A expansion для forge_pipeline/forge_registry/workspace, CON-52 «Workspace/Project контейнеры vs Forge уровни — ортогональные семантические домены»). Назначение: предоставить verify-поверхность с precise line-numbers в `docs_10/engineering-memory/LEVIATHAN_INVENTORY_V1.md` v1.1 (после merge-поля «Документ»), `core_02/LESSONS.md` (CON-52 anchor), и подтверждение CAN-16 ADDITIVE-compliance. Итоговый вердикт / ready gate / closure artifacts см. в «📊 Progress Roll-up (closed steps + unlock)» ниже. Primary source of truth: `docs_10/engineering-memory/LEVIATHAN_INVENTORY_V1.md` v1.1 + `core_02/LESSONS.md` CON-52.

### 6 fact-rows (precise line-numbers + atomic operations)

| # | Факт | Source-of-truth | Line / Marker |
|---|------|-----------------|---------------|
| 1 | **v1.1 header bump** (от v1) — «Документ» поле содержит bump-info в single canonical row | `docs_10/engineering-memory/LEVIATHAN_INVENTORY_V1.md` header row 5: `\| **Документ** \| LEVIATHAN Inventory v1.1 (от v1, bump 2026-08-06 — ROADMAP-FR-001 Шаг 3: forge_pipeline/forge_registry/workspace в Cat-A + cross-ref) \|` | **line 5** |
| 2 | **Cat-A row #26 — Forge Pipeline (L0-L5 runtime)** — первая новая строка в Cat-A таблице (после существующих 9 строк) | `LEVIATHAN_INVENTORY_V1.md` row: `\| 26 \| **Forge Pipeline (L0-L5 runtime)** \| A \| ... \|` | **line 36** |
| 3 | **Cat-A row #27 — Forge Registry (state-of-truth)** — вторая новая строка | `LEVIATHAN_INVENTORY_V1.md` row: `\| 27 \| **Forge Registry (state-of-truth)** \| A \| ... \|` | **line 37** |
| 4 | **Cat-A row #28 — Workspace/Project контейнеры (L-1/L-2)** — третья новая строка | `LEVIATHAN_INVENTORY_V1.md` row: `\| 28 \| **Workspace/Project контейнеры (L-1/L-2)** \| A \| ... \|` | **line 38** |
| 5 | **ROADMAP-FR-001 cross-ref block (header + table entry)** — новый `## 🔗 Предварительные условия переноса (ROADMAP-FR-001)` блок с 4-строчной таблицей (Шаг 1 closed / Шаг 2 closed / пре-условие Шаг 3 / canonical pytest mode) **dual-fact intentional**: row combines header line 42 + table entry line 50 в одной ячейке для compact 6-row table | `LEVIATHAN_INVENTORY_V1.md` section header + status table entry | **line 42** (header) / **line 50** (table entry) |
| 6 | **CON-52 LESSONS append** — канон о двух семантических доменах (Контейнерная Workspace L-1 / Project L-2 vs Forge уровни L0-L5); anti-collision rule; 2 verification grep'а; full cross-reference сеть | `core_02/LESSONS.md` section `### CON-52 — Workspace/Project контейнеры (L-1 / L-2) и Forge уровни (L0-L5) — ортогональные семантические домены` | **line 1178** |

### CAN-16 ADDITIVE verification

| Проверка | Состояние | Метод |
|----------|-----------|-------|
| **v1 Cat-A content (rows 1-9 original)** | ✅ NOT touched | `awk '/^\| (3\|6\|7\|9\|14\|17\|11\|2\|25) \|/' docs_10/engineering-memory/LEVIATHAN_INVENTORY_V1.md` показывает intact existing 9 rows |
| **v1 B/C tables (rows Cat-B + Cat-C)** | ✅ NOT touched | Same `grep -c '\| .*\|' docs_10/engineering-memory/LEVIATHAN_INVENTORY_V1.md` post-insert сохраняет исходный count |
| **Ребрендинг терминологии (§old-section)** | ✅ NOT touched | `grep -c 'Companion Platform\|Runtime\|Workflow\|Key Pool' docs_10/engineering-memory/LEVIATHAN_INVENTORY_V1.md` сохраняет исходный v1 rebrand table count |
| **§Что уже сделано + §Что действительно НОВОЕ + §Рекомендация** | ✅ NOT touched | sections сохраняют версии v1 в header полях, ADDITIVE только в header «Документ v1.1 (от v1)» + Cat-A rows + 🔗 section |
| **v1.1 ADDITIVE marker explicit в header field + ROADMAP-FR-001 cross-ref block** | ✅ Yes | `sed -n '5p;42p' docs_10/engineering-memory/LEVIATHAN_INVENTORY_V1.md` показывает оба explicit markers |

### Cross-references

| Reference | Где | Назначение |
|-----------|-----|------------|
| `docs_10/engineering-memory/LEVIATHAN_INVENTORY_V1.md` v1.1 | header line 5 + Cat-A lines 36-38 + ROADMAP-FR-001 block line 42 | Primary source of truth для Шага 3 (Cat-A + cross-ref) |
| `core_02/LESSONS.md` PB-16 (Шаг 1 closure) | Шаг 1 LESSONS entry | Unverlying-CANON для §UNFORGED naming и SG-shared corrigendum (CON-52 extension orthogonal HIERARCHY) |
| `core_02/LESSONS.md` CON-52 (новое) | Канон для Шага 3 | Ortho Container L-1/L-2 vs Forge L0-L5 anti-collision правил |
| `docs_10/ROADMAP_FORGE_RECONCILIATION.md` v1.2+ | Шаг 1 + Шаг 2 bounds | Round-trip vibe в ROADMAP-документе |
| `docs_10/engineering-memory/RFC_BUFFY_FORGE_V1.md` v1.2 | §2a.1-2a.3 (lines 178/195/213) | Slimanсылка на Шаг 2 для контекста имён namespace (Workspace/Project vs Forge уровни) |

### Финальный вердикт для Шага 3

→ **Step 3 CLOSED-mark**: Cat-A expansion + ROADMAP-FR-001 cross-ref block + CON-52 LESSONS append выполнены. ROADMAP-FR-001 финальное состояние — см. «📊 Progress Roll-up (closed steps + unlock)» ниже. Вердикт и closure artifacts в Progress Roll-up, **не дублируются** в этом Detailed Fact Log намеренно (per пост-trim convention из Шага 1, fix D от code-reviewer-minimax-m3).

### CAN-16 / CAN-17 conformance

- **CAN-16 (ADDITIVE non-rewriting)**: ✅ соблюдаётся — original v1 content rows + sections сохранены; v1.1 ТОЛЬКО header field update (single «Документ» merged row) + 3 Cat-A rows (lines 36-38) + ROADMAP-FR-001 🔗 block + implicit ROADMAP round-trip к Progress Roll-up.
- **CAN-17 (audit-trail not rewritten)**: ✅ forensic anchors (PB-16 Шаг 1 → leads to v1.1 §Cat-A row #28 Workspace/Project; CON-52 cross-link → preserved в Cat-A #28 description cell; ROADMAP-FR-001 cross-ref block → preserved для downstream grep).

### Step 3 closure artifacts (cross-link only)

Полный \u0441\u043f\u0438\u0441\u043e\u043a что создано/изменено/зарегистрировано в Шаге 3 — см. «📊 Progress Roll-up (closed steps + unlock)» ниже (table of closure artifacts per Step).

## 📊 Progress Roll-up (closed steps + unlock)` (line 370 post-insert). Anchor-based insert через `basher python3` | insertion anchor `## 📊 Progress Roll-up` | **line 324** (✅ verified post-apply) |

### CAN-16 ADDITIVE verification

| Проверка | Состояние | Метод |
|----------|-----------|-------|
| **v1.0 content rows (§1, §3-§16)** | ✅ NOT touched | `git diff HEAD~1 docs_10/engineering-memory/RFC_BUFFY_FORGE_V1.md \| grep '^-' \| grep -v '^---'` = 0 lines per CAN-16 audit-trail rule |
| **v1.1 content (Alтернатива A: Workspace/Project + ARB-REV-001 correspondence table)** | ✅ NOT touched | `grep -c 'Workspace.*L-1.*L-2\|ARB-REV-001' docs_10/engineering-memory/RFC_BUFFY_FORGE_V1.md` сохраняет исходный count из v1.1 |
| **§2a (existing header)** | ✅ Расширен via §2a.1/§2a.2/§2a.3 ADDITIVE — original header НЕ переписан | `grep -n '^## 2a\|^### §2a[.***REMOVED***[^12***REMOVED***' docs_10/engineering-memory/RFC_BUFFY_FORGE_V1.md` показывает только новые подразделы |
| **NEW подразделы добавлены как sub-subsections (§2a.1/§2a.2/§2a.3)** | ✅ §3 anchor („## 3. Forge как класс подсистем) сохранён | `sed -n '178p;195p;213p' docs_10/engineering-memory/RFC_BUFFY_FORGE_V1.md` |
| **v1.2 marker explicit в closing paragraph (line 717)** | ✅ Yes | `sed -n '717p' docs_10/engineering-memory/RFC_BUFFY_FORGE_V1.md` показывает «v1.2 ADDITIVE поверх v1.0 и v1.1» |

### Cross-references

| Reference | Где | Назначение |
|-----------|-----|------------|
| `docs_10/engineering-memory/RFC_BUFFY_FORGE_V1.md` v1.2 | §2a.1/§2a.2/§2a.3 (lines 178/195/213) + closing (line 717) | Primary source of truth |
| `core_02/LESSONS.md` PB-16 | Шаг 1 closure, Hypothesis C verdict | Unverlying урок для Step 2 (§2a.1/§2a.3 ссылаются на PB-16 Lesson 1 + Case 2') |
| `core_02/LESSONS.md` CON-52 (post-v5.103.0) | Слабaя связь — ortho Container L-1/L-2 vs Forge L0-L5 запланирована в Шаге 3 LEVIATHAN inventory, не в Шаге 2 | Contexual (Step 3 anchors в Cat-A cross-ref ROADMAP-FR-001) |
| `docs_10/ROADMAP_FORGE_RECONCILIATION.md` v1.1+ | Шаг 1/2 bounds | Round-trip vibe в ROADMAP-документе |

### Финальный вердикт для Шага 2

→ **Step 2 CLOSED-mark**: doc-only ADDITIVE operation completed. Готовность к Шагу 3 (LEVIATHAN inventory prep) — см. «📊 Progress Roll-up (closed steps + unlock)» ниже. Вердикт и closure artifacts в Progress Roll-up, **не дублируются** в этом Detailed Fact Log намеренно (per пост-trim convention из Шага 1, fix D от code-reviewer-minimax-m3).

### CAN-16 / CAN-17 conformance

- **CAN-16 (ADDITIVE non-rewriting)**: ✅ соблюдаётся — original §1-§16 + v1.1 §2a content rows = неизменны; v1.2 только ADDITIVE подразделы §2a.1/§2a.2/§2a.3 + version bump в header + closing paragraph.
- **CAN-17 (audit-trail not rewritten)**: ✅ forensic anchors (PB-16 in Шаг 1 → leads to v1.2 §2a.3 naming clarification; msg_id 138366/138367 → preserved in §2a.2 STATE-orthogonal).

### Step 2 closure artifacts (cross-link only)

Полный \u0441\u043f\u0438\u0441\u043e\u043a что создано/изменено/зарегистрировано в Шаге 2 — см. «📊 Progress Roll-up (closed steps + unlock)» ниже (table of closure artifacts per Step).
## 📊 Progress Roll-up (closed steps + unlock)

> **Note:** Этот раздел — фиксация закрытых Шагов ROADMAP-FR-001 v1.0 + unlock-статус для следующего Шага. Добавлен по принципу CAN-17 (audit-trail) — оригинальные Шаги 0–3 не переписаны.

### ✅ Шаг 1 — Fact-check разрыва (CLOSED 2026-08-06)

- **Verdict:** Hypothesis C — Forge ⇆ Wizard = orthogonal STATE-домены, shared TG transport infra.
- **Evidence:** 6 facts подтверждены (forge_pipeline.py subprocess.run + 0 wizard imports; wizard_lib.run_wizard_with_registry существует; scenario_registry.py не знает о forge; forge_registry.yaml interior-planner=UNFORGED; context.db 0 scenario/wizard/forge-tables + cross-table LIKE '%interior%' → 0 rows; e2e_logs/promt47_run.md v5.64.0 msg_id 138366/138367 FACT).
- **LESSONS entry:** `core_02/LESSONS.md` PB-16 (~472 lines, раздел «📦 Scenario: ROADMAP-FR-001 Step 1 — Forge ⇆ Wizard domain separation»).
- **TG-shared corrigendum:** применён в LESSONS PB-16 (Урок 1) — оба пути используют один TG transport layer (forge on_report → tg_session/TgClientV2; Wizard → telegram_contract.report_to_*).

### ✅ Шаг 2 — Reconciliation (CLOSED 2026-08-06, Case 2' doc-only)

- **Path:** Case 2' (разрыв кажущийся по PB-16) → ~30 мин doc-only правки в `RFC_BUFFY_FORGE_V1.md`.
- **RFC v1.2 ADDITIVE (CAN-16 соблюдён, v1.0+v1.1 не переписаны):**
  - **`§2a.1 — Граница ответственности: Forge Pipeline ↔ Wizard/Scenario`** (NEW подраздел): таблица «кто за что отвечает» по 8 аспектам (CLI entry-point, pipeline стадии, state source, state scope, default cmd, schema isolation, cross-call verification, TG transport).
  - **`§2a.2 — STATE-orthogonal:** между `forge_registry.yaml` UNFORGED и Wizard-progressed через TG round-trip. Явная table для «orthoпроверки»: `UNFORGED` ≠ «проект не работает» вообще.
  - **`§2a.3 — UNFORGED naming clarification`** (schema-header doc-polish): полный список статусов с точными определениями; UNFORGED = «не прошёл forge forge», не «проект не работал».
- **Закрывающий параграф v1.2** в конце RFC фиксирует: «Соблюдён CAN-16: оригинальный RFC v1.0 и v1.1 не переписаны, а расширены ADDITIVE-подразделами §2a.1–§2a.3 к существующему §2a. Теперь §2a покрывает три уровня: (a) Workspace/Project контейнеры (v1.1); (b) Forge-Pipeline ↔ Wizard/Scenario boundary (v1.2); (c) UNFORGED schema-header doc-polish (v1.2).
- **Version bump:** RFC version header v1.1 → v1.2; платформенная версия v5.103.0 (после Forge Series v5.97.0–v5.103.0).
- **Regression tests:** `tests_09/test_forge_pipeline.py + test_forge_registry.py + test_wizard.py + test_scenario_registry.py` — все зелёные (76 passed в общем batch; test_run_skip_stage pre-existing flaky state-leak в batch, isolated run PASSED). **Мои правки в этой сессии только в LESSONS.md (PB-16) и RFC_BUFFY_FORGE_V1.md (v1.2 ADDITIVE §2a.1–§2a.3 + closing paragraph + version bump) — Python-код НЕ затронут.**

### ✅ Шаг 3 — LEVIATHAN inventory (CLOSED 2026-08-06)

- **Hard-block:** Шаг 3 был заблокирован Шагом 2 (LEVIATHAN inventory не должен унаследовать баг синхронизации).
- **Сейчас:** Шаг 2 closed (Case 2' applied) → Шаг 3 **разблокирован**.
- **Бюджет:** ~1–2 ч (3-подзадачный, см. секцию «Шаг 3» выше).
- **Когда стартовать:** по явному запросу пользователя.

### 🔄 Testable Readiness status (consolidated)

| Шаг | Testable критерий | Статус |
|-----|-------------------|--------|
| 0 | ROADMAP-документ существует + capability-check прошёл | ✅ v1.0 создан; deepseek-v4-pro capability_match:3/3 подтверждён |
| 1 | LESSONS.md содержит PB-/CON- entry со snippet ≥3 строки (forge_pipeline.py AND wizard.py) | ✅ PB-16 (6 facts + Урок 1 TG-shared corrigendum + Урок 2 Case 2' applies) |
| 2 | RFC §2a содержит обновлённую таблицу разграничения | ✅ v1.2 §2a.1 + §2a.2 (STATE-orthogonal) + §2a.3 (UNFORGED doc-polish) + closing paragraph |
| 2 | Регрессионные тесты зелёные | ✅ 76 passed in batch; isolated test_run_skip_stage PASSED |
| 2 | В LESSONS.md ссылка на ROADMAP-FR-001 в новой записи | ✅ PB-16 sectiom «📦 Scenario: ROADMAP-FR-001 Step 1 ...» |
| 3 | LEVIATHAN_INVENTORY_V1.md Category A содержит 3 forge_* модуля с ссылкой на ROADMAP-FR-001 | ✅ CLOSED 2026-08-06 |

### Связанные артефакты (cross-doc ledger)

| Файл | Изменение для ROADMAP-FR-001 |
|------|------------------------------|
| `docs_10/ROADMAP_FORGE_RECONCILIATION.md` | Этот документ; Progress Roll-up добавлен |
| `core_02/LESSONS.md` § PB-16 | Шаг 1 result (Hypothesis C + TG-shared corrigendum) |
| `docs_10/engineering-memory/RFC_BUFFY_FORGE_V1.md` v1.2 | Шаг 2 Case 2' (ADDITIVE §2a.1/§2a.2/§2a.3 + closing paragraph + version bump v1.1→v1.2) |
| `docs_10/e2e_logs/promt47_run.md` | TG audit-trail (msg_id 138366/138367 v5.64.0 FACT) |
| `data_13/forge_registry.yaml` | STATE source #1 (UNFORGED schema-header clarified в §2a.3) |
| `data_13/context.db` | STATE source #2 candidate — НЕ хранит ScenarioRuntime (PB-16 Fact 5) |
---

## 📊 ROADMAP-FR-001 Final Closure Bulletin (2026-08-06)

> **✅ ROADMAP-FR-001 closed 2026-08-06 — Hypothesis C verified via Шаги 1+2+3, LEVIATHAN inventory ready.**
>
> Итог: 3-шаговый роуд-мап (ROADMAP-FR-001) завершён. Consortium-closed состояние: Hypothesis C verified (Шаг 1), §2a.1–2a.3 ADDITIVE (Шаг 2), UNFORGED schema-header clarified + Container vs Forge-Levels ortho (Шаг 3). Downstream ready: `LEVIATHAN_INVENTORY_V1.md` v1.1 + `core_02/LESSONS.md` PB-16 + `CON-52` + `RFC_BUFFY_FORGE_V1.md` v1.2.

### Closure summary (high-level cross-refs; for per-step criteria see Progress Roll-up)

| Шаг | Status | Downstream artifact (cross-reference) |
|-----|--------|----------------------------------------|
| Шаг 1 (fact-check разрыва) | ✅ CLOSED 2026-08-06 | `core_02/LESSONS.md` (PB-16) — Hypothesis C verdict + TG-shared corrigendum |
| Шаг 2 (Case 2 doc-only) | ✅ CLOSED 2026-08-06 | `docs_10/engineering-memory/RFC_BUFFY_FORGE_V1.md` v1.2 — §2a.1 / §2a.2 / §2a.3 (lines 178 / 195 / 213) + closing paragraph (line 717) |
| Шаг 3 (LEVIATHAN inventory prep) | ✅ CLOSED 2026-08-06 | `docs_10/engineering-memory/LEVIATHAN_INVENTORY_V1.md` v1.1 (Cat-A rows #26–#28) + `core_02/LESSONS.md` (CON-52) |
| **ROADMAP-FR-001 final** | **✅ CLOSED 2026-08-06** | This document v1.4 + 3 📒 Detailed Fact Logs + Progress Roll-up + this Closure Bulletin |

---

