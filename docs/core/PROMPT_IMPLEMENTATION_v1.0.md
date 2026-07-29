# PROMPT: Внедрение Session Mesh v2.0 в экосистему Buffy

> **Версия:** 1.0.0  
> **Дата:** 2026-07-30  
> **Основание:** [DISTRIBUTED_SESSION_SPECIFICATION_v2.0.md***REMOVED***(DISTRIBUTED_SESSION_SPECIFICATION_v2.0.md)  
> **Архитектор:** Denis  
> **Исполнитель:** Buffy (AI-ассистент) + команда разработчиков (опционально)  

---

> **⚠️ Полный текст промпта:** см. [`pompts/promt17.md`***REMOVED***(../../pompts/promt17.md)  
> Этот файл — точка входа в документации. Реализация — в `freebuff_plugin/mesh/`.

---

## 📋 Фазы реализации

| Фаза | Дни | Задачи | Тестов | Статус |
|------|-----|--------|:------:|:------:|
| 0: Подготовка | 1 | Структура, зависимости, фикстуры | 5 | ✅ Готово |
| 1: EventStore | 2-3 | Event, интерфейс, SQLiteEventStore | 20 | 🔴 План |
| 2: Vector Clock | 1 | VectorClock | 10 | 🔴 План |
| 3: Node Mesh | 2-3 | Device, CapabilityEngine, Heartbeat | 20 | 🔴 План |
| 4: Session Mesh | 3-4 | LeaseManager, SessionMesh, Sync | 25 | 🔴 План |
| 5: Offline-first | 2 | OfflineQueue, SyncStrategy | 15 | 🔴 План |
| 6: Agent Mesh | 2-3 | Agent, Tool, LoadBalancer | 20 | 🔴 План |
| 7: Transport | 2 | WebSocket, NATS, HTTP | 15 | 🔴 План |
| 8: MCP + CLI | 2 | MCP tools, CLI | 15 | 🔴 План |
| **ИТОГО** | **17-21** | — | **~145** | |

## 🔧 Быстрый старт

```bash
# Структура уже создана
ls freebuff_plugin/mesh/{core,node,session,agent,transport,storage***REMOVED***/

# Установить зависимости
pip install ulid-py websocket-client diff-match-patch

# Запустить тесты (когда будут написаны)
pytest tests/test_mesh.py -v
```

---

_Полный текст: [pompts/promt17.md***REMOVED***(../../pompts/promt17.md)_
