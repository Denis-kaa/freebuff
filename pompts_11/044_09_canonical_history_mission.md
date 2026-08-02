# MISSION: Фиксация изменений документации в структуре canonical/history

## КОНТЕКСТ

В сессии 2026-08-02 была проведена архитектурная сессия, результаты которой зафиксированы в документе `SESSION_UNDERSTANDING_2026-08-02.md` (если он существует в корне проекта — проверь). 

Принято решение разделить документацию на две категории:
- **canonical/** — только текущее состояние системы (факты, без истории споров)
- **history/** — почему так получилось (ADR, решения, споры)

Запущен скрипт `setup_canonical.sh`, который создал базовую структуру. Твоя задача — **проверить, что всё создано корректно, дополнить недостающее и зафиксировать в git**.

## ПРАВИЛА РАБОТЫ

1. **Точные пути:** 
   - Проект: `/storage/emulated/0/PROJECTS/workstation/freebuff`
   - Документация: `docs_10/`
   - Canonical: `docs_10/canonical/`
   - History: `docs_10/history/`
   - Vision: `docs_10/vision/`
   - Core: `docs_10/core/`

2. **Git:** Уже настроен через `safe.directory`. Коммиты обязательны.

3. **AFC (Architectural Fit Check):** Перед каждым изменением документа в сообщении коммита укажи:
   - Какие файлы затронуты
   - Почему это служит цели разделения canonical/history
   - Не дублирует ли это существующие документы

4. **Не добавляй новый код.** Только документация и структура.

5. **Не трогай существующие файлы** в `docs_10/core/`, `docs_10/vision/`, `docs_10/decisions/` — они уже работают. Только добавляешь новую структуру `canonical/` и `history/`.

---

## ФАЗА A: Проверка структуры

1. Проверь, что существуют папки:
   - `docs_10/canonical/`
   - `docs_10/history/`
   
2. Если их нет — создай:
```bash
   mkdir -p docs_10/canonical
   mkdir -p docs_10/history
```

3. Проверь, что существует `docs_10/canonical/architecture.md`. Если нет — создай его с минимальным содержанием (см. Фазу B).

4. Проверь, что существует `docs_10/canonical/INDEX.md`. Если нет — создай.

---

## ФАЗА B: Создание canonical/architecture.md

Если файл не существует или пуст — создай его со следующим содержанием (строго факты, без истории):

```markdown
# Архитектура Workspace OS (Канон)

**Статус:** CANONICAL  
**Обновлено:** 2026-08-02  

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
```

---

## ФАЗА C: Создание ADR в history/

### ADR-001: Позиционирование

Создай `docs_10/history/ADR-001_positioning.md`:

```markdown
# ADR-001: Позиционирование Workspace OS

**Дата:** 2026-08-02  
**Статус:** ACCEPTED  

---

## Контекст

Проведён внешний конкурентный анализ. Выявлено:
- Hermes Agent (Nous Research, 175K+ stars) занял нишу персональной AI-памяти
- Mem0 (48-59K stars) — managed memory layer
- Ни один конкурент не решает multi-human коллаборацию с ролевым разделением

## Решение

Workspace OS не конкурирует с персональными AI-агентами (Hermes) или IDE (Cursor). Мы выступаем как агрегатор и единый источник истины поверх них.

## Режимы работы

- **Single** — вход в воронку. Не обязан быть лучше Hermes — обязан быть достаточным.
- **Cowork** — то же самое, для нескольких агентов одного пользователя.
- **Teamwork** — единственная зона, где нет прямого конкурента. Основной фокус развития.

## Следствия

- Не наращивать Single/Cowork-функционал ради конкуренции с Hermes
- Фокусировать разработку на Teamwork: DPE, Role-based Context Isolation, Project-Centric Chat
- Внешние агенты (Hermes, Claude Code) — Runtime-исполнители, которые читают наш `.context/` и записывают отчёты обратно
```

### ADR-002: JSON-контракты

Создай `docs_10/history/ADR-002_contracts.md`:

```markdown
# ADR-002: JSON-контракты вместо промптов

**Дата:** 2026-08-02  
**Статус:** ACCEPTED  

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
```

---

## ФАЗА D: Обновление INDEX.md

Обнови `docs_10/INDEX.md`, добавив ссылки на новые папки:

```markdown
## Структура документации

### canonical/ — Текущее состояние системы (канон)
- [INDEX.md***REMOVED***(canonical/INDEX.md) — индекс канонических документов
- [architecture.md***REMOVED***(canonical/architecture.md) — иерархия, контракты, позиционирование

### history/ — История решений (ADR)
- [ADR-001_positioning.md***REMOVED***(history/ADR-001_positioning.md) — почему агрегатор, не конкурент
- [ADR-002_contracts.md***REMOVED***(history/ADR-002_contracts.md) — почему JSON-контракты
- [SESSION_UNDERSTANDING_2026-08-02.md***REMOVED***(history/SESSION_UNDERSTANDING_2026-08-02.md) — полная фиксация сессии (если существует)
```

Если `SESSION_UNDERSTANDING_2026-08-02.md` существует в корне проекта — перенеси его в `docs_10/history/`.

---

## ФАЗА E: Коммиты

Сделай **один коммит** со всеми изменениями:

```bash
git add docs_10/canonical/ docs_10/history/ docs_10/INDEX.md
git commit -m "docs: split documentation into canonical/history structure

AFC:
- Затронуты: docs_10/canonical/, docs_10/history/, docs_10/INDEX.md
- Цель: разделение фактов (canonical) и истории решений (history)
- Не дублирует: существующие docs_10/core/, docs_10/vision/, docs_10/decisions/ не изменены

Создано:
- canonical/architecture.md — факты архитектуры (без истории)
- canonical/INDEX.md — индекс канонических документов
- history/ADR-001_positioning.md — почему агрегатор, не конкурент
- history/ADR-002_contracts.md — почему JSON-контракты
- Обновлён docs_10/INDEX.md с ссылками на новые папки"
```

---

## КРИТЕРИЙ ЗАВЕРШЕНИЯ

1. ✅ Папки `docs_10/canonical/` и `docs_10/history/` существуют
2. ✅ `canonical/architecture.md` содержит только факты (без истории споров)
3. ✅ `history/ADR-001_positioning.md` и `ADR-002_contracts.md` созданы
4. ✅ `docs_10/INDEX.md` обновлён с ссылками на новые папки
5. ✅ Коммит создан с AFC в сообщении
6. ✅ Существующие файлы в `docs_10/core/`, `docs_10/vision/`, `docs_10/decisions/` НЕ изменены

## ОТЧЁТ

После завершения предоставь:
1. Список созданных/изменённых файлов
2. Подтверждение, что коммит создан
3. Вывод `git log --oneline -1` (последний коммит)
4. Если что-то пошло не так — опиши проблему, не пытайся чинить наугад

Приступай к Фазе A.