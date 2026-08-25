# ADR-023: Cowork Shared Memory — MemoryStore + RemoteDB Integration

**Статус:** Accepted (Implemented)
**Дата:** 2026-08-25
**Вызвано:** промт 109 §3 (Cowork mode) + запрос пользователя — общая база данных между Termux и сервером.

---

## Контекст

У нас есть два экземпляра Buffy:
- **Termux** (Android, ARM64) — основной рабочий агент
- **Сервер WHIMCO** (185.233.184.192, Ubuntu) — фоновый агент

ADR-022 решил транспортный уровень: rqlite на сервере + RemoteDB для HTTP-доступа.
Но MemoryStore всё ещё использовал локальный SQLite. Нужен бесшовный переход между локальным и удалённым режимом.

---

## Решение

**MemoryStore принимает опциональный `remote_db: RemoteDB`.** Если передан — все операции идут через rqlite. Если нет — локальный SQLite как раньше.

```python
# Локальный режим (по умолчанию, обратная совместимость)
store = MemoryStore("data_13/context.db")

# Cowork-режим (общая БД)
remote = RemoteDB(remote_url="http://185.233.184.192:4001")
store = MemoryStore(remote_db=remote)
```

### Архитектура маршрутизации

```
MemoryStore
├── _execute(sql, params) ──┬── remote_db.execute()  [Cowork***REMOVED***
│                            └── sqlite3.execute()    [local***REMOVED***
├── _fetchall(sql, params) ─┬── remote_db.fetchall()  [Cowork***REMOVED***
│                            └── sqlite3.fetchall()   [local***REMOVED***
└── SCHEMA ────────────────┬── remote_db.executescript()  [Cowork***REMOVED***
                            └── sqlite3.executescript()   [local***REMOVED***
```

### Совместимость

| Операция | local | Cowork |
|----------|:-----:|:------:|
| `store_knowledge` | ✅ | ✅ |
| `get_knowledge` (с тегами) | ✅ | ✅ |
| `query_all` / `query_by_type` | ✅ | ✅ |
| `count_objects` | ✅ | ✅ |
| `update_knowledge` | ✅ | ✅ (оптимистичный rowcount) |
| `delete_knowledge` | ✅ | ✅ (оптимистичный rowcount) |
| `link_knowledge` | ✅ | ✅ |
| `find_related` (BFS) | ✅ | ✅ |
| `shortest_path` (BFS) | ✅ | ✅ |
| `find_patterns` | ✅ | ✅ |
| `update_feedback` | ✅ | ✅ |
| `record_analytics` / `get_analytics` | ✅ | ✅ |
| `record_learning_event` | ✅ | ✅ |

Ограничения Cowork-режима:
- `rowcount` в `update_knowledge`/`delete_knowledge` всегда `1` (оптимистично) — rqlite не возвращает affected rows для простого execute-API
- Нет транзакций (rqlite v10 execute API — auto-commit per statement)

---

## Тесты

- **20 hermetic тестов** (Mock RemoteDB): `tests_09/test_memory_store_cowork.py`
- **3 интеграционных теста** (реальный rqlite): `TestIntegrationRqlite`
- **20 оригинальных тестов** продолжают работать: `tests_09/test_memory_store.py`
- **Smoke test**: Termux → rqlite → сервер читает/пишет те же данные ✅

```bash
# Локально (Termux)
python -m pytest tests_09/ -q -k "memory_store or MemoryStore"  # 44 passed

# Сервер (с реальным rqlite)
python -m pytest tests_09/test_memory_store_cowork.py -q         # 23 passed
```

---

## Как использовать

```python
from core_02.remote_db import RemoteDB
from core_02.memory_store import MemoryStore

# Cowork: оба Buffy подключаются к одной БД
remote = RemoteDB(remote_url="http://185.233.184.192:4001")
store = MemoryStore(remote_db=remote)

# Данные доступны обоим агентам мгновенно
store.store_knowledge(kind="lesson", title="Shared Knowledge")
```

## Последствия

- ✅ **Cowork-режим готов к использованию** — два агента могут читать/писать общую память
- ✅ **Обратная совместимость** — существующий код работает без изменений
- ⚠️ **Нет транзакций** — для критичных операций использовать локальный режим
- 🔜 **Следующий шаг** — интеграция с ContextManager для общих сессий