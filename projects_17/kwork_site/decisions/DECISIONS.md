# DECISIONS.md — Индекс ADR проекта `kwork_site`

> **Канонический формат ADR (project-local):** **Context / Options / Decision / Rationale / Consequences** — см. [`ADR-001`***REMOVED***(ADR-001_auth_tenant_isolation.md).
> **Корневой (платформенный) индекс ADR:** [`docs_10/decisions/DECISIONS.md`***REMOVED***(../../../docs_10/decisions/DECISIONS.md) — project-local ADR независимы (миграция-готовое хранение per [`docs_10/templates/PROJECT_MIGRATION_TEMPLATE.md`***REMOVED***(../../../docs_10/templates/PROJECT_MIGRATION_TEMPLATE.md)).
> **Канон ведения проектов:** [`docs_10/core/PROJECT_RULES.md`***REMOVED***(../../../docs_10/core/PROJECT_RULES.md) §3.1 / §4 + `PROJECT_MIGRATION_TEMPLATE.md` §7 (portable ADR).

---

## 0. Шкала статусов

| Статус | Значение |
|---|---|
| 🟢 **ACCEPTED** | Принятое решение, применимое в проекте. Связанные изменения в коде/SPEC/STEPS обязательны. |
| 🟡 **PENDING** | Решение ожидает входных данных (блокер клиента или architecture step). |
| 🔴 **DEPRECATED** | Решение отменено более новым ADR (см. `Superseded by` поле). |
| ⚪ **DRAFT** | Решение в черновике, ещё не принято командой. |

---

## 1. Список ADR проекта `kwork_site`

| ADR | Title | Статус | Дата | Категория |
|---|---|---|---|---|
| [ADR-001***REMOVED***(ADR-001_auth_tenant_isolation.md) | **Модель авторизации и tenant-isolation** | 🟢 **ACCEPTED** | 2026-08-17 | Архитектура / Безопасность |
| [ADR-002***REMOVED***(ADR-002_python_vs_php.md) | Стек Excel-движка (Python vs PHP) | ⚪ **DRAFT** | 2026-08-17 (черновик; ждёт Q1 в [`CLIENT_QUESTIONS_v1.md`***REMOVED***(../CLIENT_QUESTIONS_v1.md)) | Архитектура / Tech-debt |
| [ADR-003***REMOVED***(ADR-003_excel_schema_v1.md) | Excel schema v1 (структура + общий ключ + периодичность) | ⚪ **DRAFT** | 2026-08-17 (черновик; ждёт Q2 в [`CLIENT_QUESTIONS_v1.md`***REMOVED***(../CLIENT_QUESTIONS_v1.md)) | Архитектура / Data-model |
| ADR-004+ | (зарезервировано для будущих решений) | — | — | — |

> **Status legend:** 🟢 = можно применять в коде; 🟡 = ждёт external input (ADR-файл ещё не написан); ⚪ = черновик ADR написан (Decision pending client input).

---

## 2. Шаблон ADR (canonical format)

Скопировать при создании нового ADR. Сохранять структуру **Context / Options / Decision / Rationale / Consequences** для совместимости с возможной миграцией в платформенный [`docs_10/decisions/`***REMOVED***(../../../docs_10/decisions/).

```markdown
# ADR-NNN: <slug>

> **Статус:** 🟢 ACCEPTED | 🟡 PENDING | 🔴 DEPRECATED | ⚪ DRAFT
> **Дата:** YYYY-MM-DD
> **Категория:** Архитектура | Безопасность | Data-model | Tech-debt | Performance
> **Superseded by:** ADR-NNN (только для 🟡 DEPRECATED)

## 1. Контекст
<Не более 5 предложений. Что вынуждает решать? Какой business-constraint или технический?>

## 2. Рассмотренные варианты

### Вариант A: <название>
- **Плюсы:** <1-3 пункта>
- **Минусы:** <1-3 пункта>
- **Цена:** <если применимо>

### Вариант B: <название>
...

### Вариант C: <название>
...

## 3. Решение
<Один или несколько абзацев: что выбрано. Чёткое утверждение.>

## 4. Обоснование (Rationale)
<Почему именно этот вариант. Ссылка на принципы Workspace OS / `01_PLAN_BREAKDOWN.md` / `SPEC.md` / business-логику.>

## 5. Последствия (Consequences)

### Положительные
- <...>

### Отрицательные / риски
- <...>

### Требования к реализации
- <что должно появиться в коде>

### Требования к тестированию
- <что должно быть проверено автотестами>

## Cross-links

- [`../MANIFEST.md`***REMOVED***(../MANIFEST.md) — Scope Rules (аддитивность, бюджет, конфиденциальность)
- [`../SPEC.md`***REMOVED***(../SPEC.md) §[X***REMOVED*** — формальная спецификация
- [`../STEPS.md`***REMOVED***(../STEPS.md) §[X***REMOVED*** — выполнение
- [`../01_PLAN_BREAKDOWN.md`***REMOVED***(../01_PLAN_BREAKDOWN.md) §[X***REMOVED*** — context решения
- [`../../docs_10/core/PROJECT_RULES.md`***REMOVED***(../../../docs_10/core/PROJECT_RULES.md) — канон
- [`../LESSONS.md`***REMOVED***(../LESSONS.md) — уроки, извлечённые из этого решения (если применимо)
- [`../CLIENT_QUESTIONS_v1.md`***REMOVED***(../CLIENT_QUESTIONS_v1.md) — связь с блокерами клиента (если применимо)

#### Соседние ADR

- [`DECISIONS.md`***REMOVED***(DECISIONS.md) — индекс project-local ADR
- `[ADR-NNN_<slug>.md***REMOVED***(ADR-NNN_<slug>.md)` — другой ADR этого проекта (если применимо)

#### Стилевые образцы

- `docs_10/engineering-memory/decisions/ADR-NNN_*.md` — platform-wide ADR для эталона формата
- Стандарт MADR/ADR (https://adr.github.io/madr/) — соблюдён Context/Options/Decision/Rationale/Consequences
```

> 📌 **Конвенция:** ADR-документ проекта должен оставаться **portable** (миграция-готовым) — без зависимостей от платформенных модулей `core_02/` / `scripts_01/` / `freebuff_plugin*` (per [`MANIFEST.md`***REMOVED***(../MANIFEST.md) Scope Rules).

---

## 3. Соглашения и формат

### 3.1 Именование файлов

`ADR-NNN_<slug>.md`, где:
- **NNN** — 3-значный идентификатор (001, 002, …), уникален в пределах проекта.
- **<slug>** — короткое имя темы (через `_`), без пробелов. Всегда на английском (transliteration), даже если контент на русском.

Примеры (этот проект): `ADR-001_auth_tenant_isolation.md`, `ADR-002_python_vs_php.md`.

### 3.2 Cross-references

- Ссылки между ADR: `[ADR-002***REMOVED***(ADR-002_python_vs_php.md)` (relative basename).
- Ссылки на канонические источники: относительные пути от `decisions/` вверх (`../../docs_10/...`).
- ID-формат: `ADR-001` (без слова «ADR-number-NNN»).

### 3.3 Обновление статуса

При принятии нового ADR, который меняет предыдущее решение:

1. Сменить статус старого ADR на 🔴 `DEPRECATED`.
2. Добавить поле `**Superseded by:** ADR-NNN` в старом ADR.
3. Создать новый ADR, явно ссылающийся на старый (в §Context + §Related ADRs).

### 3.4 Когда НЕ создавать ADR

- Решение уже зафиксировано в [`SPEC.md`***REMOVED***(../SPEC.md) (например, NFR) — отдельный ADR избыточен; ссылка в Cross-links ADR списком достаточно.
- Решение тривиально (выбор библиотеки из 3 эквивалентных) — слишком мелко для ADR.
- Решение требует artifact-валидации (data, perf) — может стать ADR позже, после измерения.

---

## Cross-links

- [`../MANIFEST.md`***REMOVED***(../MANIFEST.md) — общий паспорт проекта
- [`../SPEC.md`***REMOVED***(../SPEC.md) §6.2 — locked architectural decisions
- [`../01_PLAN_BREAKDOWN.md`***REMOVED***(../01_PLAN_BREAKDOWN.md) §8 — 3 sharp decisions (закладывают основу ADR')
- [`../STEPS.md`***REMOVED***(../STEPS.md) §1.0 — Architectural step (принятие ADR-001/ADR-002/ADR-003 при старте Этапа 1.0)
- [`docs_10/decisions/DECISIONS.md`***REMOVED***(../../../docs_10/decisions/DECISIONS.md) — платформенный индекс ADR (для возможной миграции)
- [`docs_10/core/PROJECT_RULES.md`***REMOVED***(../../../docs_10/core/PROJECT_RULES.md) §3.1 (уроки) + §4 (порядок работы) + §7 (миграция)

---

*Индекс создан: 2026-08-17 · Канон: PROJECT_MIGRATION_TEMPLATE.md §7 + project-local convention · Парные решения: `01_PLAN_BREAKDOWN.md §8` (sharp decisions) + `CLIENT_QUESTIONS_v1.md` (блокеры клиента) · Автор: Buffy (Workspace OS / Freebuff) · Формат ADR: **Context / Options / Decision / Rationale / Consequences***
