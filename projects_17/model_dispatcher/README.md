# Model Dispatcher (Диспетчер моделей)

Автоматизация работы с **FreeBuff** через терминал (081_19_model_dispatcher): скрипт
имитирует действия человека — запускает freebuff TUI, смотрит, какая из
мощных моделей доступна на стартовом экране, выбирает **по убыванию мощности**
(GLM 5.2 → MiMo 2.5 Pro → MiniMax M3 → DeepSeek V4 Flash free), контролирует
вылеты и таймер сессии (по умолчанию 1 час), а прерванная «часовая сессия»
не исчезает — контекст сохраняется.

## Как это работает

```
pompts_11/user/ (промты) → running/ → freebuff TUI (tmux)
   → стартовый экран → выбор модели по приоритету → «Enter a coding task»
   → промпт → мониторинг (вылеты/таймер)
→ done/ (✅) | failed/ (❌) | running/ (⏸ таймер, сессия сохранена)
```

## Быстрый старт

```bash
# Проверка окружения
python -m projects_17.model_dispatcher.dispatcher --check

# Приоритет моделей
python -m projects_17.model_dispatcher.dispatcher --models

# Что обработается
python -m projects_17.model_dispatcher.dispatcher --dry-run

# Обработать один промт из pompts_11/user/
python -m projects_17.model_dispatcher.dispatcher --once

# Дамп экрана сохранённой сессии (отладка)
python -m projects_17.model_dispatcher.dispatcher --screen <task_id>

# Тесты
python -m pytest projects_17/model_dispatcher/tests/ -q
```

## Настройка (config.yaml)

| Ключ | По умолчанию | Смысл |
|------|-------------|-------|
| `session.timeout_minutes` | `60` | Таймер сессии (1 час) |
| `session.max_restarts` | `2` | Рестарты при вылете TUI |
| `models.priority` | GLM→MiMo→MiniMax→DeepSeek | Приоритет выбора по убыванию |
| `models.unavailable_markers` | `sold out, exhausted, …` | Маркеры недоступности квоты |
| `queue.*_dir` | `pompts_11/...` | Папки очереди |
| `freebuff.continue_resume` | `true` | Продолжение сессий через `--continue` |

## Структура

```
projects_17/model_dispatcher/
├── config.yaml          # конфиг
├── dispatcher.py        # CLI
├── md_models.py         # детект моделей на экране + выбор по убыванию
├── md_queue.py          # файловая очередь (формат pompts_11/)
├── md_freebuff.py       # tmux-драйвер freebuff (имитация человека)
├── decisions/           # project-local ADR
└── tests/               # unit-тесты (без реального tmux/freebuff)
```

Подробности: [`MANIFEST.md`***REMOVED***(MANIFEST.md), [`ROADMAP.md`***REMOVED***(ROADMAP.md),
[`STEPS.md`***REMOVED***(STEPS.md), [`RUNNABLE.md`***REMOVED***(RUNNABLE.md).
