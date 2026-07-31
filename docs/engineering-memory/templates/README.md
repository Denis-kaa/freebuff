# Engineering Memory Templates

Этот каталог содержит Markdown-шаблоны для документов Engineering Memory (EM).

## Как использовать

Шаблоны можно заполнять вручную или рендерить программно через
`scripts/engineering_memory.py`.

Пример рендеринга из кода:

```python
from scripts.engineering_memory import EMEngine

em = EMEngine()
markdown = em.render_template(
    "decision_journal",
    title="Выбор SQLite для хранения состояния",
    context="Нужно durable локальное хранилище",
    options="LevelDB, SQLite, JSON-файлы",
    decision="SQLite",
    rationale="Стандартная библиотека Python, zero setup",
    consequences="Просто, но single-node"
)
```

## Доступные шаблоны

| Шаблон | Тип | Когда использовать |
|---|---|---|
| `decision_journal.md` | Decision Journal | Значимое архитектурное решение |
| `incident_report.md` | Incident Report | Критическая ошибка / инцидент |
| `task_retrospective.md` | Task Retrospective | Сложная завершённая задача |
| `lessons_learned.md` | Lessons Learned | Короткий важный вывод |
| `feature_story.md` | Feature Story | Эволюция фичи в несколько итераций |
| `milestone_chronicle.md` | Milestone Chronicle | Завершённый крупный этап |
| `architecture_evolution.md` | Architecture Evolution | Изменение доменной модели |
| `project_chronicle.md` | Project Chronicle | Скомпилированная история проекта |

## Плейсхолдеры

Все шаблоны используют простые плейсхолдеры в фигурных скобках:

```markdown
---
title: "{title***REMOVED***"
date: "{YYYY-MM-DD***REMOVED***"
---
```

Если значение для плейсхолдера не передано, он остаётся как есть —
это позволяет использовать шаблон и как руководство для ручного заполнения.

## Жизненный цикл

1. Агент или человек создаёт черновик по шаблону.
2. Человек проверяет и дополняет недостающие детали.
3. `EMEngine.finalize_draft()` сохраняет документ в `docs/engineering-memory/<type>/`.
4. Документ индексируется в `KnowledgeEngine` и становится доступен для поиска.
