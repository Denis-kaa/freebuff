# Паспорт проекта Model Dispatcher (Диспетчер моделей)

| Поле | Значение |
|---|---|
| **Название** | Model Dispatcher (081_19_model_dispatcher) |
| **Версия** | 0.1.0 |
| **Назначение** | Автоматизация работы с установленным инструментом FreeBuff через терминал: запуск freebuff TUI, выбор мощной модели по убыванию (GLM → MiMo → MiniMax → DeepSeek), контроль вылетов и таймера сессии (по умолчанию 1 час), очередь промтов `pompts_11/user → done` |
| **Владелец** | Владелец устройства (оператор Freebuff) |
| **Среда** | Termux на Android (ARM64), Python 3.10+, tmux, freebuff v0.0.128 |
| **Статус** | 🟡 MVP v0.1.0: каркас + config + CLI + тесты (модели-детект, очередь, драйвер, CLI) |
| **Источник задачи** | [`pompts_11/081_19_model_dispatcher.md`***REMOVED***(../../pompts_11/081_19_model_dispatcher.md) |

## Цели

1. Запускать FreeBuff (имитация действий человека: tmux + freebuff TUI).
2. Смотреть на стартовом экране, какая из мощных моделей доступна, и выбирать **по убыванию мощности** (GLM 5.2 → MiMo 2.5 Pro → MiniMax M3 → DeepSeek V4 Flash free).
3. Контролировать вылеты (рестарт) и время (таймер сессии, по умолчанию 1 час).
4. «Сессия, ориентированная на час, не исчезает» — при таймауте сессия сохраняется, продолжение через `--continue`.
5. Брать промты из `pompts_11/user/`, после выполнения переносить в `done/` (✅) / `failed/` (❌).

## Архитектура

- **Reuse First (promt 48/81):** структура очереди `pompts_11/{user,running,done,failed***REMOVED***` уже заложена — используется как есть; формат файлов совместим с `scripts_01/prompt_queue.py`.
- **Additive:** 0 изменений в `core_02/`, `scripts_01/`, `freebuff_plugin_03/` — весь проект живёт в `projects_17/model_dispatcher/`.
- **Инъекция tmux:** драйвер (`md_freebuff.py`) получает tmux-операции функциями-параметрами → unit-тесты без реального tmux/freebuff.
- **Самодостаточность:** `md_queue.py` и `md_models.py` не импортируют платформенные скрипты (портируемость по PROJECT_RULES §7).

## Документация проекта

| Документ | Роль |
|---|---|
| `MANIFEST.md` | Настоящий паспорт |
| `ROADMAP.md` | Этапы и прогресс |
| `STEPS.md` | Живой журнал шагов («почему» приняты решения) |
| `LESSONS.md` | Уроки проекта (CON/ANTI) |
| `decisions/DECISIONS.md` | Индекс project-local ADR |
| `config.yaml` | Таймер (1ч по умолчанию), приоритет моделей, пути очереди |
| `dispatcher.py` | CLI: `--check` / `--models` / `--dry-run` / `--once` / `--all` / `--screen` |
| Тесты | `tests/test_md_models.py` + `test_md_queue.py` + `test_md_freebuff.py` + `test_dispatcher.py` |

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

# Тесты
python -m pytest projects_17/model_dispatcher/tests/ -q
```

## Правила проекта (scope)

- **Аддитивность:** только `projects_17/model_dispatcher/`.
- **Изоляция:** работаем только внутри `/storage/emulated/0/PROJECTS/workstation/freebuff/`.
- **Таймер:** по умолчанию 60 мин на сессию (настраивается в `config.yaml` → `session.timeout_minutes`).
- **Модели:** приоритет по убыванию мощности в `config.yaml` → `models.priority`; free-fallback — последняя.
- **Живой инстанс:** свободен только один инстанс freebuff (CON-33) — при занятости задача откладывается, не фейлится.
