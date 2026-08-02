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
