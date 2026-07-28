# Changelog

> Все значимые изменения в проекте Freebuff фиксируются в этом файле.
> Формат: [Keep a Changelog***REMOVED***(https://keepachangelog.com/en/1.1.0/),
> версионирование: [Semantic Versioning***REMOVED***(https://semver.org/spec/v2.0.0.html).

---

## [2.2.0***REMOVED*** — 2026-07-28

### Добавлено
- **Авто-индексация Knowledge Engine при сохранении в Memory Engine:**
  - `scripts/event_subscribers.py`: `auto_index_subscriber` получает `content` и `workspace_root` из события `memory.stored`
  - `scripts/memory_engine.py`: `MemoryEngine` автоматически подключается к дефолтному `EventBus` внутри проектного workspace; событие содержит полный `content` и `workspace_root`
  - `scripts/event_bus.py`: `get_default_event_bus()` — ленивая инициализация EventBus + подписчики
  - `scripts/bootstrap.py`: инициализация дефолтного EventBus при старте сессии
- **Наполнение Knowledge Memory:**
  - `scripts/seed_knowledge.py`: сохраняет ключевые документы проекта (`README.md`, `BUFFY.md`, `SPEC.md`, `docs/*.md` и др.) и best-practice карточки в `MemoryLevel.KNOWLEDGE`
  - Автоматический `rebuild_index()` после заполнения
- **Тесты:**
  - `tests/test_event_subscribers.py`: 4 теста на авто-индексацию и `checkpoint_logger`
  - `tests/test_seed_knowledge.py`: 3 теста на `seed_knowledge.py`

### Изменено
- `docs/ROADMAP.md`: Phase 2 отмечена как завершённая (100%)

## [2.0.0***REMOVED*** — 2026-07-28

### Добавлено
- **Система стриминга контекста v2.0:**
  - `scripts/stream_bridge.py` — мост для интеграции Buffy с stream_session
  - `scripts/context_manager.py`: CONTEXT_FULL триггер (порог 28K токенов)
  - `scripts/context_manager.py`: `_estimate_tokens()` — точная эвристика токенов
  - `scripts/context_manager.py`: `prune_abandoned()`, `auto_abandon_stale()` — GC
  - `scripts/context_manager.py`: `get_context_status()` — мониторинг контекста
  - `scripts/context_manager.py`: `SCHEMA_VERSION = 2` + система миграций
  - `scripts/stream_session.py`: `BackgroundWriter` — асинхронная запись в файлы
  - `scripts/stream_session.py`: адаптивный чекпоинт-интервал (20→50)
  - `scripts/stream_session.py`: `prune_streams()`, `prune_all()` — GC
  - `scripts/stream_session.py`: in-memory кэш счётчика сообщений
  - `scripts/bootstrap.py`: интеграция StreamBridge при старте сессии
- **Документация:**
  - `docs/TASK_TEMPLATE.md` — шаблон TASK.md для новых задач
  - `TASK.md` — файл текущей задачи (стриминг контекста v2.0)
  - `CHANGELOG.md` — этот файл

### Изменено
- `scripts/context_manager.py`: `add_message()` теперь принимает `token_count: int | None`
- `scripts/context_manager.py`: `get_messages()` сортирует ASC (старые→новые)
- `scripts/context_manager.py`: `_get_conn()` — timeout + busy_timeout
- `scripts/stream_session.py`: `log_message()` пишет в файлы асинхронно
- `docs/RULES.md`: добавлены TASK.md и CHANGELOG.md в обязательные документы

### Исправлено
- `scripts/context_manager.py`: удалены неиспользуемые импорты `re`, `time`

---

## [2.1.0***REMOVED*** — 2026-07-28

### Добавлено
- **Auto-Rollup при CONTEXT_FULL:**
  - `scripts/context_manager.py`: `_save_context_rollup()` — генерирует сжатый конспект при превышении порога токенов
  - Сохраняется в `context/context_full_rollup.md` для инжекта в новый контекст
  - Возвращается `rollup_path` в результате `add_message()` / `save_checkpoint()`
- `scripts/stream_session.py`: при CONTEXT_FULL чекпоинте выводится путь к rollup

---

## [1.0.0***REMOVED*** — 2026-07-27

### Добавлено
- **ContextManager:** SQLite-хранилище сессий, сообщений, чекпоинтов
- **StreamSession:** непрерывная запись в файлы (conversation.log + raw.jsonl)
- **AutoConspect:** автосуммаризация при завершении сессии
- **FreebuffBridge:** мост для termux-ai-agent
- **Bootstrap:** восстановление контекста при старте сессии
- **SystemMonitor:** мониторинг RAM, CPU, батареи
- **FreebuffCLI:** 7 команд для управления системой
- **Cron:** автоматическая суммаризация каждые 30 минут
- **Тесты:** 15 тестов для ContextManager
- **Документация:** BUFFY.md, SPEC.md, RULES.md, SESSION_GUIDE.md, DECISIONS.md
