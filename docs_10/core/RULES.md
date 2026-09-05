# RULES.md — Правила документирования Freebuff

> **Источник:** `pompts_11/001_07_pravila_dokumentirovaniya.md` — промт «Правила документирования для терминального агента»
> **Применяется:** Buffy и все AI-агенты экосистемы
> **Высший источник правил:** [`BUFFY.md`***REMOVED***(../../BUFFY.md) — правила здесь лишь операционализируют требования Buffy

---

## 📚 Типы документов

### Обязательные (всегда)

| Документ | Описание | Когда создавать/обновлять |
|----------|----------|--------------------------|
| **TASK.md** | ТЗ + промпт + TODO + Roadmap для текущей задачи | При старте новой задачи |
| **CHANGELOG.md** | Версии, изменения, багфиксы (в корне проекта) | При каждом коммите/изменении |
| **ARCHITECTURE.md** | Слои, компоненты, диаграммы, стек, паттерны | При изменении структуры |
| **README.md** | Что это, быстрый старт, установка, команды | При добавлении функциональности |
| **SESSION_DUMP.md** | Дата, задачи, ошибки, изменения, ссылки | Каждая сессия (эквивалент: `context_12/summaries/conspect_*.md` + `data_13/context.db`) |

### Рекомендуемые (при изменениях)

| Документ | Описание | Триггер |
|----------|----------|---------|
| **docs_10/decisions/DECISIONS.md** | Индекс архитектурных решений (ADR) | Ссылка на индекс; сами ADR — в `docs_10/engineering-memory/decisions/` |
| **IMPLEMENTATION.md** | Пошаговые инструкции, ключевые файлы, зависимости | Новая фича |
| **REFERENCES.md** | Ссылки на документацию, статьи, аналоги | Исследование |
| **ROADMAP.md** | Этапы, статус, планы, сроки | Планирование |
| **COMPARISON.md** | Сравнение с OpenClaw, Aider, Codebuff и др. | Сравнительный анализ |
| **TROUBLESHOOTING.md** | Частые ошибки, решения, диагностика | Обнаружение проблемы |

### Исследования и эксперименты

| Документ | Описание | Триггер |
|----------|----------|---------|
| **BRAINSTORM.md** | Идеи, оценка сложности, приоритеты | Мозговой штурм |
| **EXPERIMENTS.md** | Что тестировали, результаты, выводы | Эксперимент |
| **GLOSSARY.md** | Термины, определения, аббревиатуры | Новая терминология |

### Специализированные

| Документ | Описание | Триггер |
|----------|----------|---------|
| **API.md** | Эндпоинты, форматы, примеры | API-изменения |
| **WORKERS.md** | Паттерн воркеров, ToolRuntime-интеграция, жизненный цикл | Добавление/изменение воркера или инструмента |
| **DEPLOYMENT.md** | Требования, инструкции, env-переменные | Деплой |
| **SECURITY.md** | Уязвимости, отчёты, практики | Проблема безопасности |
| **MIGRATION.md** | Версионирование, breaking changes, обновление | Breaking change |
| **PERFORMANCE.md** | Метрики, бенчмарки, оптимизации | Оптимизация |
| **TESTING.md** | Стратегия тестирования, coverage | Изменение тестов |
| **CHANGELOG.md** | Изменения по версиям | Релиз |

### Аудит и анализ

| Документ | Описание | Триггер |
|----------|----------|---------|
| **AUDIT_*.md** | Аудит ключей, проектов, безопасности | Периодически |
| **RECOMMENDATIONS.md** (docs_10/) | Единый append-only реестр рекомендаций (REC-NNN): аудит-фиксы, архитектурные улучшения, ops-гигиена; пара с AUDIT_*.md (CON-68) | После каждого аудита/ревью/инцидента |
| **ARCHITECTURE_REVIEW.md** | Глубокий анализ экосистемы | После сканирования |

---

## 🔄 Правила авто-создания/обновления

### При старте новой задачи:
1. Создать `TASK.md` по шаблону `../ops/TASK_TEMPLATE.md`
2. Указать ТЗ, промпт, TODO, Roadmap
3. Обновлять по мере выполнения

### После каждого изменения кода:
1. Обновить `CHANGELOG.md` — добавить запись с типом (Добавлено/Изменено/Исправлено)
2. Обновить `TASK.md` — отметить выполненные пункты
3. Обновить `ARCHITECTURE.md` если изменилась структура
4. Обновить `README.md` если добавилась функциональность
5. Создать запись в `SESSION_DUMP.md`

### При завершении задачи:
1. Установить статус в TASK.md → 🟢 ГОТОВО
2. Обновить CHANGELOG.md с итоговой версией
3. Зафиксировать все изменения

### При архитектурном решении:
→ `docs_10/engineering-memory/decisions/ADR_NNN_*.md`: проблема, альтернативы, выбор, обоснование; `docs_10/decisions/DECISIONS.md` — индекс

### При исследовании:
→ `BRAINSTORM.md` + `EXPERIMENTS.md` (если был эксперимент)

### При реализации фичи:
→ `IMPLEMENTATION.md` + `API.md` (если нужно)

### При обнаружении бага:
→ `TROUBLESHOOTING.md`

### При аудите:
→ `docs_10/AUDIT_YYYY-MM-DD.md` или `ARCHITECTURE_REVIEW.md`
→ `docs_10/RECOMMENDATIONS.md` — завести REC-записи по каждой находке (пара AUDIT + RECOMMENDATIONS, урок CON-68)

---

## 📐 Формат документов

Все документы — **Markdown** со структурой:

- ✅ Заголовки (h1–h3)
- ✅ Маркированные/нумерованные списки
- ✅ Таблицы
- ✅ Код-блоки с указанием языка
- ✅ Диаграммы Mermaid
- ✅ Перекрёстные ссылки на другие документы

---

## 📂 Структура docs_10/

```
freebuff/
└── docs_10/
    ├── INDEX.md              # навигация
    ├── core/                   # спецификации, архитектурные принципы, RULES
    ├── vision/               # VISION_3.0, ROADMAP, PRODUCT_MANIFESTO
    ├── decisions/            # ADR, DECISIONS, IDEAS
    ├── audits/               # AUDIT_*.md, DRIFT_REPORT
    ├── plugin/               # FREEBUFF_PLUGIN_*
    ├── projects_meta/        # PROJECT_REGISTRY, WORKERS, FILE_REGISTRY
    └── ops/                  # TROUBLESHOOTING, SESSION_GUIDE, AGENTS, шаблоны
```

### 🆕 Session Mesh v2.0
- **Спецификация:** `docs_10/core/DISTRIBUTED_SESSION_SPECIFICATION_v2.0.md`
- **Промпт реализации:** `pompts_11/017_02_struktura_requirements_testy.md` (канон; стаб-копия в docs_10/core архивирована 2026-08-01)
- **Код:** `freebuff_plugin_03/mesh/`

---

## 📋 Чек-лист: что создать при старте проекта

> ⚠️ **Канон ведения проектов — `docs_10/core/PROJECT_RULES.md` (§8 чек-лист нового проекта).**
> Обязательные: **MANIFEST.md (паспорт) · LESSONS.md · decisions/DECISIONS.md + ADR · ROADMAP.md ·
> README.md · RUNNABLE.md · CHECKLIST.md**. Этот чек-лист ниже — базовые документ-типы, дополняет канон.

- [ ***REMOVED*** README.md
- [ ***REMOVED*** ARCHITECTURE.md
- [ ***REMOVED*** RULES.md (этот файл)
- [ ***REMOVED*** SPEC.md (ТЗ)
- [ ***REMOVED*** .gitignore
- [ ***REMOVED*** CONTRIBUTING.md
- [ ***REMOVED*** CHANGELOG.md
- [ ***REMOVED*** TASK.md (текущая задача)
- [ ***REMOVED*** ../ops/TASK_TEMPLATE.md (шаблон задачи)

---

## 🤖 Авто-триггер документирования (`scripts_01/buffy_autodoc.py`)

Чтобы не забывать обновлять документы, в проекте есть вспомогательный скрипт:

```bash
# Показать чек-лист документов, которые нужно обновить
python scripts_01/buffy_autodoc.py

# Создать недостающие заглушки документов
python scripts_01/buffy_autodoc.py --apply

# Запуск в строгом режиме (для pre-commit hook)
python scripts_01/buffy_autodoc.py --cached --strict
```

### pre-commit hook

Чтобы не забывать обновлять `CHANGELOG.md` при изменениях кода, в репозиторий добавлен pre-commit hook:

```bash
# Установить hook (копирует scripts_01/pre-commit → .git/hooks/pre-commit)
bash scripts_01/install_hooks.sh

# Обойти проверку при крайней необходимости
git commit --no-verify
# или
SKIP_AUTODOC=1 git commit ...
```

Hook запускает `scripts_01/buffy_autodoc.py --cached --strict` и **блокирует коммит**, если для изменённого кода не обновлён `CHANGELOG.md` (или другие документы со статусом `severity=block`).

> **Важно:** `.git/hooks/` не версионируется Git. Tracked копия hook лежит в `scripts_01/pre-commit`, а `scripts_01/install_hooks.sh` устанавливает её.

Скрипт анализирует `git diff --name-status`, сопоставляет изменённые файлы с правилами и выводит:
- какие документы должны быть созданы/обновлены;
- какие файлы спровоцировали триггер.

### Триггеры скрипта

| Триггер | Изменённые файлы | Требуемые документы |
|---------|------------------|---------------------|
| New task | всегда | `TASK.md` |
| Code change | `*.py`, `*.sh`, `*.js`, `*.ts`, `*.html`, `*.css` | `CHANGELOG.md`, `TASK.md` |
| Architecture change | `src_06/`, `scripts_01/`, `freebuff_cli.py` | `ARCHITECTURE.md` |
| README feature | `freebuff_cli.py`, `scripts_01/`, `src_06/` | `README.md` |
| Architectural decision | файлы с `decision`, `adr`, `architecture` | `../decisions/DECISIONS.md` (индекс) и `../engineering-memory/decisions/` (ADR) |
| Research / spike | файлы с `research`, `spike`, `experiment` | `docs_10/BRAINSTORM.md`, `docs_10/EXPERIMENTS.md` |
| Bug fix | файлы с `bug`, `fix`, `error` | `../ops/TROUBLESHOOTING.md` |
| API change | файлы с `api`, `mcp_server`, `endpoint` | `../ops/API.md` |
| Worker / tool | файлы с `workers`, `tool_runtime` | `../projects_meta/WORKERS.md` |
| Documentation change | `*.md` | `RULES.md` |

> **Важно:** скрипт — напоминание, а не генератор готового контента. Он помогает не пропустить обязательные документы, но содержание всё равно нужно проверять вручную или с помощью LLM.
