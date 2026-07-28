# TASK: Система стриминга контекста v2.0

> **Версия:** 1.0.0
> **Статус:** 🟢 ГОТОВО
> **Приоритет:** 🔴 Критический
> **Начало:** 2026-07-27
> **Завершение:** 2026-07-28
> **Связано:** [BUFFY_PROJECT.md***REMOVED***(BUFFY_PROJECT.md) — теперь часть Buffy Project

---

## 📋 Техническое задание (ТЗ)

### Цель
Реализовать непрерывное сохранение контекста диалога Buffy в реальном времени:
каждое сообщение автоматически пишется в SQLite + файлы, а при превышении
лимита токенов создаётся CONTEXT_FULL чекпоинт.

### Функциональные требования (MUST)
- [x***REMOVED*** Каждое сообщение Buffy сохраняется в stream_session (файлы + SQLite)
- [x***REMOVED*** CONTEXT_FULL триггер при превышении порога 28K токенов
- [x***REMOVED*** Автоматическая очистка ABANDONED сессий старше 1 дня
- [x***REMOVED*** Асинхронная запись в файлы (не блокирует ответ)
- [x***REMOVED*** Адаптивный чекпоинт-интервал (20→30→40→50)
- [x***REMOVED*** GC стрим-директорий (хранить последние 10)
- [x***REMOVED*** Миграции схемы БД (SCHEMA_VERSION)
- [x***REMOVED*** StreamBridge — мост для интеграции Buffy

### Дополнительные требования (SHOULD/COULD)
- [x***REMOVED*** Точная эвристика токенов (len//4*1.3)
- [x***REMOVED*** Bootstrap с авто-стримингом при старте
- [x***REMOVED*** In-memory кэш счётчика сообщений
- [x***REMOVED*** Все 24 теста проходят

### Ограничения
- Termux на Android (ARM64)
- SQLite WAL-режим
- Python 3.11+
- tiktoken недоступен (segfault на Termux) → эвристика

---

## 🤖 Промпт для реализации

```text
ROLE: Архитектор / Python-разработчик
CONTEXT: Freebuff — AI Engineering Platform на Termux/Android.
Система стриминга сохраняет каждое сообщение в real-time.
Нужно улучшить: async writes, CONTEXT_FULL триггер, GC, адаптивный интервал.
INPUT:
  - scripts/context_manager.py — ядро (SQLite)
  - scripts/stream_session.py — стриминг
  - scripts/bootstrap.py — старт сессии
TASK:
  1. Добавить CONTEXT_FULL триггер в add_message()
  2. Добавить SCHEMA_VERSION + миграции
  3. Добавить prune_abandoned(), auto_abandon_stale()
  4. Добавить BackgroundWriter с Queue для async writes
  5. Добавить _get_adaptive_interval()
  6. Добавить prune_streams(), prune_all()
  7. Создать StreamBridge — мост для Buffy
  8. Обновить bootstrap с интеграцией StreamBridge
  9. Обновить тесты
CONSTRAINTS:
  - Python 3.11+ (без match/case, без 3.12 фич)
  - SQLite в WAL-режиме
  - Thread-safe через threading.Lock
  - Без tiktoken (segfault на Termux)
OUTPUT: 4 изменённых файла + 1 новый (stream_bridge.py)
DoD:
  - Тесты проходят (pytest tests/ -v)
  - Нет segfault'ов на Termux
  - StreamBridge можно импортировать и использовать
```

---

## 📊 План (TODO)

### Этап 1: ContextManager (core)
- [x***REMOVED*** SCHEMA_VERSION = 2 + миграции через PRAGMA user_version
- [x***REMOVED*** _estimate_tokens() — эвристика без tiktoken
- [x***REMOVED*** add_message() — CONTEXT_FULL триггер при token_estimate > threshold
- [x***REMOVED*** prune_abandoned(days) — удаление ABANDONED сессий
- [x***REMOVED*** auto_abandon_stale() — перевод пустых ACTIVE → ABANDONED
- [x***REMOVED*** get_context_status() — мониторинг контекста
- [x***REMOVED*** get_total_token_estimate() / get_message_count() / update_session_status()
- [x***REMOVED*** _get_conn() с timeout + busy_timeout

### Этап 2: StreamSession (IO)
- [x***REMOVED*** BackgroundWriter — фоновый поток с Queue
- [x***REMOVED*** _handle_log / _handle_checkpoint — handlers для BG записи
- [x***REMOVED*** _get_adaptive_interval() — интервал 20→30→40→50
- [x***REMOVED*** _counter_cache — in-memory кэш счётчика
- [x***REMOVED*** prune_streams(keep=10) — GC стрим-директорий
- [x***REMOVED*** prune_all() — полная очистка (abandoned + streams)
- [x***REMOVED*** log_message использует BG writer для файлов, синхронно SQLite

### Этап 3: StreamBridge (bridge)
- [x***REMOVED*** StreamBridge — мост: log_user/log_assistant/log_system
- [x***REMOVED*** start_session / end_session / get_context_resume
- [x***REMOVED*** _auto_bootstrap — восстановление последней сессии
- [x***REMOVED*** Lazy import auto_conspect (избегаем циклических импортов)

### Этап 4: Bootstrap + интеграция
- [x***REMOVED*** Bootstrap использует StreamBridge при старте
- [x***REMOVED*** Стартовый промпт включает Stream ID

### Этап 5: Тестирование
- [x***REMOVED*** test_context_full_trigger — порог срабатывает
- [x***REMOVED*** test_estimate_tokens — эвристика работает
- [x***REMOVED*** test_prune_abandoned — GC ABANDONED
- [x***REMOVED*** test_auto_abandon_stale — перевод ACTIVE→ABANDONED
- [x***REMOVED*** test_get_context_status — статус контекста
- [x***REMOVED*** test_get_total_token_estimate — сумма токенов
- [x***REMOVED*** test_update_session_status — смена статуса
- [x***REMOVED*** test_add_message_auto_token — авто-оценка токенов
- [x***REMOVED*** Все 24 теста проходят (0 errors)

---

## 🗺 Roadmap

| Дата | Веха | Статус |
|------|------|--------|
| 2026-07-27 | Анализ узких мест стриминга | 🟢 |
| 2026-07-28 | Реализация ContextManager улучшений | 🟢 |
| 2026-07-28 | Реализация StreamSession улучшений | 🟢 |
| 2026-07-28 | StreamBridge + bootstrap интеграция | 🟢 |
| 2026-07-28 | Тестирование (24 теста, 0 errors) | 🟢 |
| 2026-07-28 | Code review | 🟢 |

---

## 📝 Changelog задачи

### [2.0.0***REMOVED*** — 2026-07-28
- **Добавлено:** StreamBridge — мост Buffy ↔ stream_session
- **Добавлено:** CONTEXT_FULL триггер (порог 28K токенов)
- **Добавлено:** BACKGROUND_WRITER — асинхронная запись (Queue + thread)
- **Добавлено:** Адаптивный чекпоинт-интервал (20→30→40→50)
- **Добавлено:** GC: prune_abandoned, auto_abandon_stale, prune_streams
- **Добавлено:** SCHEMA_VERSION + миграции БД
- **Добавлено:** In-memory кэш счётчика (_counter_cache)
- **Добавлено:** get_context_status() для мониторинга
- **Изменено:** bootstrap.py — интеграция StreamBridge
- **Изменено:** add_message() — token_count: int | None (авто-оценка)
- **Исправлено:** Удалены неиспользуемые импорты (re, time)

---

_Связанные файлы: [CHANGELOG.md***REMOVED***(CHANGELOG.md), [docs/TASK_TEMPLATE.md***REMOVED***(docs/TASK_TEMPLATE.md), [docs/DECISIONS.md***REMOVED***(docs/DECISIONS.md), [docs/RULES.md***REMOVED***(docs/RULES.md)_
