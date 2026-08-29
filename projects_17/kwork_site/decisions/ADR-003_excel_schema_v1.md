# ADR-003: Excel schema v1 (структура + общий ключ + периодичность) для `kwork_site`

> **Статус:** ⚪ **DRAFT** — ждёт ответа клиента по **Q2** в [`CLIENT_QUESTIONS_v1.md`***REMOVED***(../CLIENT_QUESTIONS_v1.md) (TBD).
> **Дата черновика:** 2026-08-17
> **Дата принятия:** TBD (после ответа клиента → перевод ⚪ → 🟢 ACCEPTED или 🔴 DEPRECATED, если Q2 выявит что схема не сводима с архитектурой).
> **Категория:** Архитектура / Data-model
> **Блокер:** 🔴 **Q2** в [`CLIENT_QUESTIONS_v1.md`***REMOVED***(../CLIENT_QUESTIONS_v1.md) (2 эталонных Excel-файла: структура колонок + общий ключ + периодичность обновления).
> **Зависимости:** [`01_PLAN_BREAKDOWN.md`***REMOVED***(../01_PLAN_BREAKDOWN.md) §3 (структура данных) + §6 #3 (БЛОКЕР «2 эталонных Excel») + §8 Decision 1 (заморозка схемы БД до получения файлов). **Влияет на:** [`SPEC.md`***REMOVED***(../SPEC.md) §4 (SQL DDL — финальные колонки Container / Dislocation определяются Q2), [ADR-002***REMOVED***(ADR-002_python_vs_php.md) (выбор парсера: pandas/openpyxl при Python, PhpSpreadsheet при PHP).
> **Канон-формат:** **Context / Options / Decision / Rationale / Consequences** ([шаблон в `DECISIONS.md`***REMOVED***(DECISIONS.md#2-шаблон-adr-canonical-format)).

---

## 1. Контекст

Бриф + [`промт.md`***REMOVED***(../промт.md) требуют **«обработки 2 Excel-файлов»** дислокации контейнеров и сведения их в единую БД. Без **2 эталонных файлов** (текущий + предыдущий период) от клиента невозможно:

1. Зафиксировать **структуру колонок** в файлах (= структура полей в `Container` / `Dislocation` таблицах).
2. Определить **общий ключ сведения** (например, `container_no` — наиболее вероятно).
3. Определить **периодичность обновления** (дневной / событийный / ручной) → как часто вызывается парсер.

[`01_PLAN_BREAKDOWN.md`***REMOVED***(../01_PLAN_BREAKDOWN.md) §8 Decision 1 фиксирует: **«заморозить схему БД и парсер до получения эталонных файлов»** — структура БД строится *вокруг* реальных полей файлов, а не наоборот.

**Ключевые ограничения:**

- **Бюджет** 30 000 ₽ (Этап 1 = 15 000 ₽, Этап 2 = 15 000 ₽) — слепой парсинг «из головы» = хрупкий код + переделка.
- **Hard stop:** без Q2 парсер не пишется; Этап 1.3 (Excel pipeline) блокирован.
- **Workaround:** возможен фикстур-fallback (исполнитель генерирует 2 sample Excel на основе прогноза по [`01_PLAN_BREAKDOWN.md`***REMOVED***(../01_PLAN_BREAKDOWN.md) §3), но это не отменяет необходимости реального подтверждения от клиента.

---

## 2. Рассмотренные варианты

### Вариант A: `container_no` как общий ключ + ручная загрузка админом через `/admin/upload` — **рекомендуется**

`container_no` (номер контейнера) — наиболее вероятный общий ключ из двух файлов (текущий + предыдущий период). Парсер сводит: новый файл приходит → строки с тем же `container_no` обновляются (status, lat, lon, timestamp_event); строки без соответствия в предыдущем файле — это новые контейнеры; строки, исчезнувшие из нового файла — это «доставленные».

- **Плюсы:**
  - ✅ Самый типовой pattern для транспортной дислокации (1 контейнер = 1 строка в файле текущего периода).
  - ✅ Простота: PRIMARY KEY в БД = `container_no` (внутри `company_id` scope per [ADR-001***REMOVED***(ADR-001_auth_tenant_isolation.md)).
  - ✅ Тестируемость: фикстуры легко генерировать (10 контейнеров × 2 периода).
- **Минусы:**
  - 🟡 Если у клиента **другой** ключ (например, `container_no + vessel_no` или `container_id` UUID) — потребуется переписать парсер.
  - 🟡 Ручная загрузка — риск забыть (админ КТК ТРАСТ должен помнить обновлять). Альтернатива: cron-job (но out-of-scope per [`01_PLAN_BREAKDOWN.md`***REMOVED***(../01_PLAN_BREAKDOWN.md) §5.2).
- **Цена:** низкая (1 уникальный ключ, 1 `PRIMARY KEY (company_id, container_no)`).

### Вариант B: Composite key (`container_no` + период)

Общий ключ сведения — это пара `(container_no, period)`. Контейнер может менять статус между периодами, поэтому в БД он сохраняется несколько раз (одна строка на период).

- **Плюсы:**
  - ✅ Полная history дислокации: видно, где контейнер был 2 месяца назад и где сейчас.
  - ✅ Audit-trail: можно откатиться к предыдущему «состоянию мира».
- **Минусы:**
  - ❌ Увеличивает объём БД в `N_периодов` раз (для 2 файлов — не страшно, для 12 ежемесячных файлов за год — ×12 SELECT-ов).
  - ❌ Сложнее логика сведения (нужно решить: «текущий статус» = последняя запись или агрегат?).
  - ❌ На дашборде нужно показать «текущее» состояние, а не все записи → дополнительные VIEW/запросы.
- **Цена:** средняя (дополнительные ~3–5 ч к Этапу 1 + сложные запросы).

### Вариант C: Auto-detect common key (если клиент не указал)

Исполнитель применяет heuristic: парсит заголовки файлов, пытается найти общий ключ по `Jaccard similarity` названий колонок (например, ищет «container*» в обоих файлах). Если нашёл — использует; если нет — запрашивает помощь клиента.

- **Плюсы:**
  - ✅ Если клиент не хочет вникать в детали ключа — может положиться на эвристику.
- **Минусы:**
  - ❌ Эвристика может ошибиться (выбрать `container_id` UUID вместо `container_no`, или `id` вместо `container_no`).
  - ❌ Нужны unit-тесты на эвристику — дополнительная сложность (15+ тестов для всех edge cases).
  - ❌ Не снимает hard-stop (если клиент не указал ключ, исполнитель всё равно тратит время).
- **Цена:** ❌ **избыточен** в условиях явного ответа клиента по Q2.

### Вариант D: Auto-CSV-detect (через headers + types)

Парсер пытается auto-detect по `pandas.read_excel(header=0, dtype={'id': str***REMOVED***)` + типы колонок. Если 2 файла имеют совместимую структуру — сведение успешно автоматически.

- **Плюсы:**
  - ✅ Минимум кода от исполнителя.
- **Минусы:**
  - ❌ Типы колонок могут различаться между файлами (например, `container_no` в одном файле — int, в другом — string с ведущими нулями).
  - ❌ Не учитывает fuzzy-именования колонок («Номер контейнера» vs «container_no» vs «CONTAINER_NUMBER»).
- **Цена:** средняя (нужен dedup-logic по названиям ~5 ч).

---

## 3. Решение

⚠️ **DRAFT-плейсхолдер — будет заполнен после Q2.**

После ответа клиента Q2 в [`CLIENT_QUESTIONS_v1.md`***REMOVED***(../CLIENT_QUESTIONS_v1.md) один из вариантов станет финальным Decision:

- **Если клиент прислал 2 эталонных файла с явным общим ключом** → принять соответствующий вариант (A: `container_no`, B: composite, или кастомный).
- **Если клиент прислал файлы, но без явного указания ключа** → **Вариант A** по умолчанию (наиболее вероятно — `container_no`); исполнитель верифицирует по структуре файлов.
- **Если клиент не прислал файлы в течение 5 дней** → **фикстур-fallback**: исполнитель генерирует 2 sample Excel на основе [`01_PLAN_BREAKDOWN.md`***REMOVED***(../01_PLAN_BREAKDOWN.md) §3, ADR помечается как ⚪ DRAFT с пометкой «awaiting files».

**Текущее намерение** (будет вычеркнуто при принятии ADR): принять **Вариант A** (`container_no` как PRIMARY KEY + ручная загрузка через `/admin/upload`).

> 📌 **Действия после ответа:** обновить этот раздел ⚠️ → ✅ Решение; обновить [`SPEC.md`***REMOVED***(../SPEC.md) §4 SQL DDL (добавить финальные колонки Container / Dislocation на основе реальных полей); вычеркнуть плейсхолдер; обновить [`STEPS.md`***REMOVED***(../STEPS.md) §1.3 чекбокс «Получить 2 эталонных файла»; обновить [`DECISIONS.md`***REMOVED***(DECISIONS.md) статус ⚪ → 🟢/🔴.

---

## 4. Обоснование (Rationale)

### 4.1 Соответствие [`01_PLAN_BREAKDOWN.md`***REMOVED***(../01_PLAN_BREAKDOWN.md) §3 (entity model + §8 Decision 1)

`Container` (per [`01_PLAN_BREAKDOWN.md`***REMOVED***(../01_PLAN_BREAKDOWN.md) §3): id, **company_id** (FK), **`container_no` (уникальный)**, type/size, current_status, current_lat, current_lon, updated_at — указывает `container_no` как ключевое поле. ADR-003 фиксирует это явно.

`Dislocation (log)` (per [`01_PLAN_BREAKDOWN.md`***REMOVED***(../01_PLAN_BREAKDOWN.md) §3): id, container_id (FK), status, lat, lon, timestamp_event, source_file — лог перемещений контейнера.

§ 8 Decision 1 (заморозка схемы БД): «без 2 эталонных Excel-файлов парсер невозможно написать осмысленно — слепой парсинг = хрупкий код».

### 4.2 Tenant isolation (per [ADR-001***REMOVED***(ADR-001_auth_tenant_isolation.md))

**Composite UNIQUE constraint** `UNIQUE (company_id, container_no)` на таблице — гарантирует tenant-isolation на уровне DDL: контейнер с `container_no='MSCU1234567'` из компании A **не** конфликтует с таким же номером у компании B. PK остаётся за `id INTEGER` rowid (стандарт для SQLite-breadcrumbs: history все равно доступима через PK), а UNIQUE-constraint дополнительно предотвращает конфликт между tenants. NFR-007 (every table has `company_id`) — соблюдается.

> **Примечание:** тут речь **не** о composite PRIMARY KEY (т.к. `id INTEGER PRIMARY KEY AUTOINCREMENT` остаётся как rowid-alias SQLite) — а о composite **UNIQUE constraint** для anti-conflict между tenants. На уровне репозитория (per ADR-001 §5.3) фильтрация идёт через `WHERE company_id = ?` независимо от PK/UNIQUE-конструкции.

### 4.3 Тестируемость

После принятия ADR-003 легко зафикстурить 2 sample Excel (`tests/data/dislocations_aug.xlsx` + `dislocations_sep.xlsx`) и проверить:
- Парсинг: `parse_workbook(file) → DataFrame` корректно читает колонки.
- Сведение: `reconcile(dfs) → DataFrame` правильно добавляет/обновляет/помечает как доставленные.
- Tenant isolation: 2 компании с одинаковыми `container_no` не конфликтуют (PRIMARY KEY составной).

### 4.4 Соответствие бюджету

Вариант A = 1 PRIMARY KEY + 1 парсер-слой + 1 `/admin/upload` страница = **минимум кода**. Вариант B = дополнительные 3–5 ч (history VIEW, агрегатные query). Варианты C/D = дополнительная сложность без явной выгоды.

---

## 5. Последствия (Consequences)

### 5.1 Положительные *(при принятии Варианта A)*

- ✅ **Минимальная сложность:** 1 ключ, 1 парсер, простая валидация.
- ✅ **Tenant isolation через PRIMARY KEY:** нет риска коллизии между компаниями.
- ✅ **Тестируемость:** фикстуры `tests/data/dislocations_*.xlsx` легко генерировать.
- ✅ **Ручная загрузка через `/admin/upload`** = per [`01_PLAN_BREAKDOWN.md`***REMOVED***(../01_PLAN_BREAKDOWN.md) §8 Decision 1 (in scope) + §5.1 (UI §1.3 в SPEC).
- ✅ **Совместимо с ADR-001** (Cookie-session + middleware для admin-эндпоинта).

### 5.2 Отрицательные / риски *(при принятии Варианта B/D)*

- ❌ **Вариант B (composite key):** дополнительные VIEW/запросы для «текущего состояния»; рост БД в `N_периодов` раз.
- ❌ **Вариант C (auto-detect):** heuristic может ошибиться; нужны 15+ тестов на edge cases; не снимает hard-stop.
- ❌ **Вариант D (auto-CSV-detect):** типы колонок могут различаться; fuzzy-имена не dedup-нутся.

### 5.3 Требования к реализации (при принятии Варианта A)

> ⚠️ Пункты ниже — **под Вариант A**. При принятии другого варианта — переписать.

1. **SQL DDL** ([`SPEC.md`***REMOVED***(../SPEC.md) §4 — обновить после Q2):

   ```sql
   CREATE TABLE container (
     id INTEGER PRIMARY KEY AUTOINCREMENT,
     company_id INTEGER NOT NULL REFERENCES company(id),
     container_no TEXT NOT NULL,
     type TEXT, size TEXT,
     current_status TEXT,
     current_lat REAL, current_lon REAL,
     updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
     UNIQUE (company_id, container_no)  -- anti-conflict между tenants (UNIQUE constraint, не PK; PK остаётся за id rowid)
   );
   CREATE INDEX idx_container_company ON container(company_id);
   ```

2. **Парсер:** [`app/excel_pipeline/parser.py`***REMOVED***(../app/excel_pipeline/parser.py) — модули (при Python per [ADR-002***REMOVED***(ADR-002_python_vs_php.md) Вариант A):
   - `parse_workbook(path: str) → pd.DataFrame` — читает `.xlsx` через `openpyxl`, нормализует заголовки (`strip().lower().replace(' ', '_')`), валидирует наличие обязательных колонок.
   - `reconcile(dfs: List[pd.DataFrame***REMOVED***, new_period: datetime) → pd.DataFrame` — сводит 2 файла по `container_no`, выдаёт операции: `INSERT` / `UPDATE` / `MARK_AS_DELIVERED` (отсутствует в новом периоде).

3. **`/admin/upload`** ([`SPEC.md`***REMOVED***(../SPEC.md) §7 UI): страница для admin КТК ТРАСТ с формой загрузки `.xlsx/.xls` файла. После загрузки:
   - Парсер читает; ошибки выводятся в preview (какая строка, какая колонка).
   - На success → `INSERT/UPDATE` в `container` + `dislocation` лог + `UploadLog` (file_name, uploaded_by, parsed_rows, errors).

4. **Периодичность (per Q2):**
   - Если Q2 = «дневной» → указать в [`SPEC.md`***REMOVED***(../SPEC.md) §5.5 (SLA), что данные обновляются **1 раз в сутки ручной загрузкой** (не auto cron).
   - Если Q2 = «по событию» → добавить note в SPEC о том, что админ загружает файл при отправке/прибытии партии контейнеров.
   - Если Q2 = «ручной ad-hoc» → требование отсутствует (админ загружает по запросу).

5. **`UploadLog`** ([`SPEC.md`***REMOVED***(../SPEC.md) §4.7): таблица для отладки; `id, file_name, uploaded_by (FK user), parsed_rows_count, errors_json, uploaded_at`.

### 5.4 Требования к тестированию

- **≥ 3 парсер-теста:** happy path (10 контейнеров, 2 периода), частично сломанные данные (битые колонки), пустой файл.
- **≥ 1 reconcile-тест:** сводка INSERT/UPDATE/MARK_AS_DELIVERED на 3-операционном примере.
- **≥ 5 tenant-isolation тестов** для `/admin/upload` — обязательно (admin может загрузить файл только в рамках своей `company_id`; нельзя загрузить файл «от имени другой компании»).
- Coverage target: **≥ 80 %** строк в `app/excel_pipeline/`.

### 5.5 ADR supersedes / related

| ADR | Relationship |
|---|---|
| [ADR-003***REMOVED***(ADR-003_excel_schema_v1.md) | **этот ADR** *(⚪ DRAFT — ждёт Q2)* |
| [ADR-001***REMOVED***(ADR-001_auth_tenant_isolation.md) | 🟢 ACCEPTED — **tenant isolation применяется** через `UNIQUE (company_id, container_no)` в `container` PK. |
| [ADR-002***REMOVED***(ADR-002_python_vs_php.md) | ⚪ DRAFT (зависит от Q1). При выборе **Вариант A** (Python) — парсер на `pandas+openpyxl`; при **Вариант B** (PHP) — на PhpSpreadsheet. В обоих случаях структура `parse_workbook`/`reconcile` остаётся. |

**Downstream impact:** после принятия ADR-003 — обновить [`SPEC.md`***REMOVED***(../SPEC.md) §4 (финальные колонки Container + Dislocation на основе реальных данных из эталонных файлов) + §5 (Excel-pipeline) + §6 (DB-init скрипт) + §8 (AC §AC-001..018 — добавить специфические AC для сведения).

---

## Cross-links

### Проектные документы

- [`../MANIFEST.md`***REMOVED***(../MANIFEST.md) — Scope Rules
- [`../SPEC.md`***REMOVED***(../SPEC.md) §4 (SQL DDL — после Q2 обновить финальные колонки Container + Dislocation), §5.1 (стек), §11 Q2 (open question)
- [`../STEPS.md`***REMOVED***(../STEPS.md) §0 #2 (блокер «2 эталонных Excel»), §1.3 (Excel pipeline — чек-лист по реализации после ADR-003)
- [`../01_PLAN_BREAKDOWN.md`***REMOVED***(../01_PLAN_BREAKDOWN.md) §3 (entity model: Container/Dislocation), §6 #3 (БЛОКЕР), §8 Decision 1 (заморозка схемы)
- [`../CLIENT_QUESTIONS_v1.md`***REMOVED***(../CLIENT_QUESTIONS_v1.md) **Q2** — структура колонок + общий ключ + периодичность; действие после ответа

### Канонические источники платформы

- [`docs_10/core/PROJECT_RULES.md`***REMOVED***(../../../docs_10/core/PROJECT_RULES.md) §3.1 (уроки в проекте) + §7 (миграция ADR)
- [`docs_10/core/CODE_QUALITY_STANDARD.md`***REMOVED***(../../../docs_10/core/CODE_QUALITY_STANDARD.md) — обязательный регламент качества кода (особенно для парсинга external files)

### Соседние ADR

- [`DECISIONS.md`***REMOVED***(DECISIONS.md) — индекс project-local ADR
- [`ADR-001_auth_tenant_isolation.md`***REMOVED***(ADR-001_auth_tenant_isolation.md) — 🟢 ACCEPTED
- [`ADR-002_python_vs_php.md`***REMOVED***(ADR-002_python_vs_php.md) — ⚪ DRAFT (зависит от Q1)

### Стилевые образцы

- [`ADR-001_auth_tenant_isolation.md`***REMOVED***(ADR-001_auth_tenant_isolation.md) — структурный образец (5 канонических разделов)

---

*ADR создан: 2026-08-17 (черновик) · Статус: ⚪ DRAFT до ответа клиента Q2 · Канон: Context/Options/Decision/Rationale/Consequences · Опоры: PLAN_BREAKDOWN §3/§6/§8 + CLIENT_QUESTIONS Q2 (структура/ключ/периодичность) · Автор: Buffy (Workspace OS / Freebuff)*
