#!/bin/bash
# ============================================================
# SETUP CANONICAL — Разделение документации на canonical/history
# ============================================================

set -e

PROJECT_ROOT="/storage/emulated/0/PROJECTS/workstation/freebuff"
DOCS="$PROJECT_ROOT/docs_10"
CANONICAL="$DOCS/canonical"
HISTORY="$DOCS/history"
VISION="$DOCS/vision"
CORE="$DOCS/core"

echo "🔧 Настройка структуры документации Workspace OS"
echo "   Проект: $PROJECT_ROOT"
echo ""

# ШАГ 0: Починить Git
echo "📌 Шаг 0: Настройка Git safe.directory..."
git config --global --add safe.directory "$PROJECT_ROOT" 2>/dev/null || true
echo "   ✅ Git настроен"
echo ""

# ШАГ 1: Создать структуру папок
echo "📁 Шаг 1: Создание структуры папок..."
mkdir -p "$CANONICAL"
mkdir -p "$HISTORY"
mkdir -p "$VISION"
mkdir -p "$CORE"
echo "   ✅ Созданы: canonical/, history/, vision/, core/"
echo ""

# ШАГ 2: Перенести SESSION_UNDERSTANDING в history/
echo "📄 Шаг 2: Перенос SESSION_UNDERSTANDING в history/..."
SESSION_FILE="$PROJECT_ROOT/SESSION_UNDERSTANDING_2026-08-02.md"
if [ -f "$SESSION_FILE" ***REMOVED***; then
    mv "$SESSION_FILE" "$HISTORY/SESSION_UNDERSTANDING_2026-08-02.md"
    echo "   ✅ Перенесён: SESSION_UNDERSTANDING_2026-08-02.md → history/"
else
    echo "   ⚠️  SESSION_UNDERSTANDING_2026-08-02.md не найден (возможно, уже перенесён)"
fi
echo ""

# ШАГ 3: Создать canonical/architecture.md
echo "📝 Шаг 3: Создание canonical/architecture.md..."
cat > "$CANONICAL/architecture.md" << 'ARCH_EOF'
# Архитектура Workspace OS (Канон)

**Статус:** CANONICAL  
**Обновлено:** 2026-08-02  
**Источник:** SESSION_UNDERSTANDING_2026-08-02.md

---

## 1. Иерархия сущностей

    Platform (meta-уровень, правила экосистемы)
    └── Workspace (сфера жизни: Работа, Хобби, Личное)
        └── Project (изолированный Vault: src/, .context/, .env)
            ├── Agent (роль + права)
            └── Task (конкретная работа)

## 2. JSON-контракты (каскадное наследование)

Формат файлов:
- `system.json` — платформенные принципы
- `workspace.json` — владелец, режим (single/cowork/teamwork)
- `project.json` — цель, roadmap, состояние
- `agent.json` — роль, права (может быть несколько)
- `task.json` — конкретная задача

**Правило разрешения:** самый специфичный явно заданный уровень выигрывает; не заданное — наследуется от родителя.

**Формат task.json:**

    {
      "goal": "строка цели",
      "priority": "normal",
      "assigned_role": "auto | конкретная роль",
      "assigned_model": "auto | конкретная модель",
      "routing_hint": ["capability1", "capability2"***REMOVED***
    ***REMOVED***

**Разведение осей:** `assigned_role` (кто выполняет) и `assigned_model` (какая модель внутри Runtime) — независимые поля.

**Гранулярность MVP:** только task-level. logic_block/file-level — зарезервировано, не реализуется.

## 3. AGENTS.md генерация

- AGENTS.md — основной файл в `.context/<project>/`
- CLAUDE.md — НЕ симлинк. Содержит одну строку `@AGENTS.md` вверху (import-синтаксис Claude Code)
- AGENTS.md генерируется из контрактов, не наоборот

## 4. Позиционирование

- Workspace OS — агрегатор, не конкурент Hermes/Cursor/Mem0
- Single/Cowork — необходимый минимум, не зона дифференциации
- Teamwork — основная зона развития (ролевая изоляция, DPE, Project-Centric Chat)

## 5. Интеграция с внешними агентами

- Hermes/Claude Code/Cursor — Runtime-исполнители, не конкуренты
- Они читают `.context/` проекта и записывают отчёты обратно
- Принцип: "Инструменты гостя важнее инструментов хозяина"
ARCH_EOF

echo "   ✅ Создан: canonical/architecture.md"
echo ""

# ШАГ 4: Создать history/ADR-001_positioning.md
echo "📝 Шаг 4: Создание history/ADR-001_positioning.md..."
cat > "$HISTORY/ADR-001_positioning.md" << 'ADR1_EOF'
# ADR-001: Позиционирование Workspace OS

**Дата:** 2026-08-02  
**Статус:** ACCEPTED  
**Источник:** SESSION_UNDERSTANDING_2026-08-02.md, раздел 1

---

## Контекст

Проведён внешний конкурентный анализ. Выявлено:
- Hermes Agent (Nous Research, 175K+ stars) занял нишу персональной AI-памяти
- Mem0 (48-59K stars) — managed memory layer
- Ни один конкурент не решает multi-human коллаборацию с ролевым разделением

## Решение

Workspace OS не конкурирует с персональными AI-агентами (Hermes) или IDE (Cursor). Мы выступаем как агрегатор и единый источник истины поверх них.

Аналогия: как Claude не конкурирует с подключёнными коннекторами (Google Drive, Slack), а работает поверх них как смысловой слой — так и Workspace OS агрегирует контекст поверх инструментов, которые пользователь уже выбрал.

## Режимы работы

- **Single** — вход в воронку. Не обязан быть лучше Hermes — обязан быть достаточным.
- **Cowork** — то же самое, для нескольких агентов одного пользователя.
- **Teamwork** — единственная зона, где нет прямого конкурента. Основной фокус развития.

## Следствия

- Не наращивать Single/Cowork-функционал ради конкуренции с Hermes
- Фокусировать разработку на Teamwork: DPE, Role-based Context Isolation, Project-Centric Chat
- Внешние агенты (Hermes, Claude Code) — Runtime-исполнители, которые читают наш `.context/` и записывают отчёты обратно
ADR1_EOF

echo "   ✅ Создан: history/ADR-001_positioning.md"
echo ""

# ШАГ 5: Создать history/ADR-002_contracts.md
echo "📝 Шаг 5: Создание history/ADR-002_contracts.md..."
cat > "$HISTORY/ADR-002_contracts.md" << 'ADR2_EOF'
# ADR-002: JSON-контракты вместо промптов

**Дата:** 2026-08-02  
**Статус:** ACCEPTED  
**Источник:** SESSION_UNDERSTANDING_2026-08-02.md, раздел 4

---

## Контекст

Необходимо описать кто, где, какие права, что делать — не через длинные текстовые инструкции, а через структурированные данные.

## Решение

Использовать каскадные JSON-контракты с наследованием:
- Platform → Workspace → Project → Agent → Task
- Самый специфичный уровень выигрывает
- Не заданное — наследуется от родителя

## Кто заполняет

- Верхние уровни (workspace, project) — пользователь через wizard
- agent.json (роли) — модель рекомендует, пользователь подтверждает
- task.json — может генерироваться моделью автоматически в рамках утверждённой миссии

## Разведение осей

`assigned_role` (кто выполняет: Hermes/Claude Code) и `assigned_model` (какая модель внутри Runtime: Opus/Sonnet) — независимые поля.

## Гранулярность

MVP: только task-level. logic_block/file-level — зарезервировано, не реализуется сейчас.
ADR2_EOF

echo "   ✅ Создан: history/ADR-002_contracts.md"
echo ""

# ШАГ 6: Создать INDEX.md для canonical/
echo "📝 Шаг 6: Создание canonical/INDEX.md..."
cat > "$CANONICAL/INDEX.md" << 'INDEX_EOF'
# Индекс канонических документов

**Обновлено:** 2026-08-02

---

## Структура

- [architecture.md***REMOVED***(architecture.md) — иерархия сущностей, JSON-контракты, позиционирование
- [contracts.md***REMOVED***(contracts.md) — детальные спецификации JSON-контрактов (TODO)
- [principles.md***REMOVED***(principles.md) — архитектурные принципы (TODO)

## Правила

1. Canonical — только текущее состояние системы, без истории
2. History — в `docs_10/history/` (ADR, решения, споры)
3. При изменении канона — обновить canonical/, создать ADR в history/
INDEX_EOF

echo "   ✅ Создан: canonical/INDEX.md"
echo ""

# ШАГ 7: Обновить docs_10/INDEX.md
echo "📝 Шаг 7: Обновление docs_10/INDEX.md..."
cat > "$DOCS/INDEX.md" << 'DOCS_INDEX_EOF'
# Индекс документации Workspace OS

**Обновлено:** 2026-08-02

---

## Структура документации

### canonical/ — Текущее состояние системы (канон)
- [INDEX.md***REMOVED***(canonical/INDEX.md) — индекс канонических документов
- [architecture.md***REMOVED***(canonical/architecture.md) — иерархия, контракты, позиционирование

### history/ — История решений (ADR)
- [ADR-001_positioning.md***REMOVED***(history/ADR-001_positioning.md) — почему агрегатор, не конкурент
- [ADR-002_contracts.md***REMOVED***(history/ADR-002_contracts.md) — почему JSON-контракты
- [SESSION_UNDERSTANDING_2026-08-02.md***REMOVED***(history/SESSION_UNDERSTANDING_2026-08-02.md) — полная фиксация сессии

### vision/ — Стратегическое видение
- [VISION_3.0.md***REMOVED***(vision/VISION_3.0.md) — стратегия и цели
- [ROADMAP.md***REMOVED***(vision/ROADMAP.md) — дорожная карта

### core/ — Архитектурные манифесты
- [ARCHITECTURE_MANIFEST.md***REMOVED***(core/ARCHITECTURE_MANIFEST.md) — главный архитектурный закон
- [GLOSSARY.md***REMOVED***(core/GLOSSARY.md) — единый глоссарий терминов
- [ARCHITECTURE_PRINCIPLES.md***REMOVED***(core/ARCHITECTURE_PRINCIPLES.md) — принципы

### decisions/ — Реестр решений
- [DECISIONS.md***REMOVED***(decisions/DECISIONS.md) — индекс ADR
- [IDEAS.md***REMOVED***(decisions/IDEAS.md) — реестр идей

---

## Правила ведения документации

1. **Canonical** — только факты, без истории споров
2. **History** — почему так получилось (ADR)
3. При изменении канона — обновить canonical/, создать ADR в history/
4. Не дублировать информацию между документами
DOCS_INDEX_EOF

echo "   ✅ Обновлён: docs_10/INDEX.md"
echo ""

# ИТОГ
echo "=========================================="
echo "✅ ЗАВЕРШЕНО"
echo "=========================================="
echo ""
echo "Создано:"
echo "  - $CANONICAL/architecture.md"
echo "  - $CANONICAL/INDEX.md"
echo "  - $HISTORY/ADR-001_positioning.md"
echo "  - $HISTORY/ADR-002_contracts.md"
echo "  - $DOCS/INDEX.md (обновлён)"
echo ""
echo "Перенесено:"
echo "  - SESSION_UNDERSTANDING_2026-08-02.md → history/"
echo ""
echo "Следующий шаг:"
echo "  1. Проверить структуру: ls -la $DOCS"
echo "  2. Сделать коммит: git add . && git commit -m 'docs: split into canonical/history structure'"
echo ""
