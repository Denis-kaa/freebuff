# STEPS.md — План выполнения (простыми словами)

> Дата: 2026-08-19 (актуализация)
> Что делаем: генератор Excel-дашбордов, где структура / данные / стили / проверки отделены от кода.
> Стек: **Python 3 + openpyxl** (+ pytest для тестов).

## Текущее состояние (2026-08-19)

**Фаза проектирования ЗАВЕРШЕНА** — все LIGHT-роли Blueprint v3 отработали, дизайн готов и согласован:

| Артефакт | Роль | Статус |
|----------|------|--------|
| `brief.md` + `parsed_requirements.md` | explainer | ✅ |
| `lisa_report.md` (LISA-3 = COND) | lisa | ✅ |
| `risk_matrix.md` (CONDITIONAL GO) | risk | ✅ |
| `decomposition.md` + `module_list.md` + `integration_topology.md` | decomposer | ✅ |
| `architecture.md` + `contracts.yaml` + `adr/ADR-002` | architect | ✅ |
| `audit_report.md` (READY WITH FIXES) | auditor | ✅ |
| `consistency_report.md` (D1–D7 закрыты) | — | ✅ |

**Фаза кода НЕ НАЧАТА** (MANIFEST: «код ещё не начат»). Папок `config/`, `data/`, `styles/`, `generator/`, `validator/` и `main.py` ещё нет.

**Единственный источник истины для реализации = `contracts.yaml`** (формальный контракт CONFIG/DATA/STYLES/GENERATOR/VALIDATOR). Шаги ниже — это ИМПЛЕМЕНТАЦИЯ этого контракта, не новое проектирование.

**Аудит-замечания ЗАКРЫТЫ (2026-08-19), архитектура = READY:** (H1) якорение формул/ссылок → сущность `Anchor` (колонка+строка+смещение+протяжённость); (H2) привязка DATA→sheet → `Sheet.data_source` + `DataSource.source` (именованные коллекции). Дополнительно влито **G1–G5** (lifecycle артефакта, уровни L1–L4, generation_id+template_version, atomic publish temp→rename, input snapshot). Всё уже в `contracts.yaml`/`architecture.md` — при написании `schema.py` кодить по ним, ничего не доспроектировать.

---

## Какую систему использую

- **Язык:** Python 3 (уже есть, 3.14.6).
- **Библиотека Excel:** openpyxl 3.1.5 — умеет создавать XLSX, листы, колонки, формулы, стили, выпадающие списки, условное форматирование и читать результат обратно.
- **Проверка:** pytest + собственный validator (перечитывает XLSX и сверяет структуру).
- **Ограничение:** openpyxl пишет формулы, но НЕ считает их. Расчёт формул — отдельный опциональный слой (LibreOffice), на первом этапе не делаем.

## План по шагам

### Шаг 0 — Каркас проекта + дизайн (сделано)
Каркас: паспорт, уроки, решения, roadmap, README, RUNNABLE, CHECKLIST. Дизайн: архитектура + контракты + декомпозиция + аудит + отчёт согласованности (все LIGHT-роли закрыты).

### Шаг 1 — Реализовать `config/schema.py` (доменная модель)
Доменная модель уже СПРОЕКТИРОВАНА в `contracts.yaml` §1 и `architecture.md` §2.1. Осталось закодить сущности:
Workbook (name/template_id/template_version/sheets), Sheet (name/columns/data_source), Field, DataSource (source/field_map), DashboardBlock, KPI, Card, LookupTable, ValidationRule, Anchor, Formula, Reference, DisplayRule, GenerationArtifact (dataclass, строгая типизация).
Отдельной сущности `Relationship` НЕТ (поглощён `Reference.kind`, D1); `Style` живёт в `styles/theme.py`, CONFIG ссылается по ключу (D4).

### Шаг 2 — Разделить неизменяемое и изменяемое
- Неизменяемое (ядро): механика XLSX, форматирование, листы, формулы, validation, таблицы, ссылки, ошибки, проверка.
- Изменяемое (через CONFIG): названия листов, поля, порядок, блоки, KPI, стили, справочники, правила, формулы, карточки.

### Шаг 3 — Структура проекта
```
project/
├── config/        # schema.py + project_dashboard.py
├── data/          # models.py + sample_data.py
├── generator/     # workbook, sheets, dashboard, formulas, validation, references
├── styles/        # theme.py
├── validator/     # validator.py
├── output/        # готовые XLSX
└── main.py
```

### Шаг 4 — Реализовать `config/project_dashboard.py` (CONFIG первого шаблона)
Закодить декларативный CONFIG проектного дашборда по `schema.py`: листы, порядок, поля, типы, обязательные поля, справочники (LookupTable), статусы, приоритеты, дедлайны, KPI, блоки, карточку, ссылки (Reference), формулы (Formula, структурно), правила форматирования (DisplayRule).

### Шаг 5 — Контракт DATA
Данные приходят нормализованными, независимо от источника (Python / CSV / JSON / Google Sheets / API / Bitrix24). На первом этапе — только интерфейс + sample_data, без внешних интеграций.

### Шаг 6 — GENERATOR
Загружает CONFIG → принимает DATA → создаёт workbook → листы → данные → формулы → ссылки → validation → условное форматирование → Dashboard → карточки → стили → сохраняет XLSX.
В ядре НЕ должно быть `if project_dashboard: ...`.

### Шаг 7 — VALIDATOR
Проверяет: листы есть, порядок верный, колонки обязательные, CONFIG↔DATA согласованы, формулы на месте, ссылки корректны, validation и диапазоны на месте, hyperlinks, Dashboard-блоки, карточки.
Разделяем: структурная валидация (сами) vs расчётная (LibreOffice, отдельно).

### Шаг 8 — Эталонный XLSX
Через новую архитектуру собрать рабочий проектный XLSX (только то, что реально нужно первому сценарию).

### Шаг 9 — Архитектурный тест
Поменять CONFIG (название листа, порядок листов, одно поле, один Dashboard-блок, один стиль) → получить другой XLSX без правки ядра.

### Шаг 10 — Финальная проверка
Генерация → открытие файла → структура → данные → формулы → ссылки → validation → стили → Dashboard → карточка → соответствие CONFIG → нет архитектурных исключений.

## Когда считаем готовым (DoD)

1. XLSX генерируется.
2. Структура задаётся CONFIG.
3. DATA отделён от GENERATOR.
4. STYLES отделены от GENERATOR.
5. VALIDATOR работает отдельно.
6. Ядро без привязки к конкретному шаблону.
7. Смена CONFIG меняет XLSX без правки ядра.
8. Ограничения проверки явно обозначены.
9. Архитектура остаётся простой для развития.
