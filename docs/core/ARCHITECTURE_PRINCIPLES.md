# ARCHITECTURE PRINCIPLES — Buffy AI Infrastructure Layer

> **Версия:** 1.0.0
> **Дата:** 2026-07-29
> **Статус:** Утверждён
> **Основание:** [promt16.md***REMOVED***(../../pompts/promt16.md), [VISION_3.0.md***REMOVED***(../VISION_3.0.md)

---

## 1. Главный архитектурный принцип

**Buffy — Infrastructure Plugin. Не AI Agent.**

Buffy расширяет существующие Runtime, не заменяя их.
Любой Runtime должен продолжать работать после удаления Buffy.
Buffy не должен становиться точкой отказа.
Архитектура должна оставаться loosely coupled.

---

## 2. Инженерные принципы

### 2.1 Infrastructure Plugin

```
Buffy — НЕ новый AI Agent.
Buffy — Infrastructure Plugin.

Он расширяет существующие Runtime:
  - Claude Code
  - OpenClaw
  - Hermes
  - Codex
  - Cursor
  - FreeBuff CLI

Buffy предоставляет дополнительные возможности:
  - долговременный контекст
  - документацию проекта
  - знания проекта
  - синхронизацию
  - совместную работу
  - передачу задач
  - маршрутизацию
  - Bridge между Runtime
  - Collaboration Layer
```

**Следствия:**
- Никакой бизнес-логики генерации кода внутри Buffy
- Runtime'ы подключаются, а не встраиваются
- Удаление плагина не ломает ядро
- Ядро не знает о внутренностях плагина (только через `__init__.py`)

### 2.2 Android First

**Основная целевая платформа:** Android + Termux.

Все новые функции необходимо оценивать с точки зрения возможности реализации на Android.
Если решение невозможно реализовать на Android — предложить альтернативу.

Поддержка Linux/macOS/Windows является расширением, а не основной целью.

### 2.3 Loosely Coupled

```
ЯДРО (scripts/)                    ПЛАГИН (freebuff_plugin/)
────────────────────                ──────────────────────────
Не импортирует плагин               Импортирует ядро только
напрямую (кроме __init__.py)        через bridge.py
                                   
mcp_server.py                       bridge.py
  └── freebuff_plugin.__init__        └── scripts.context_manager
  └── try/except graceful degradation └── scripts.stream_session
```

**Граница:**
- Ядро → Плагин: только через `freebuff_plugin/__init__.py`, с `try/except`
- Плагин → Ядро: только через `freebuff_plugin/bridge.py`
- Никаких жёстких путей (типа `["scripts/mcp_server.py"***REMOVED***`)
- Контракт зафиксирован в `freebuff_plugin/INTEGRATION_CONTRACT.md`

### 2.4 Runtime Agnostic

Buffy не привязан к конкретному AI Runtime.
Все Runtime подключаются через Adapter Layer.
Добавление нового Runtime не требует изменения ядра.

**Marketplace-ready:** структура `runtime/providers/` позволяет добавлять
новые Runtime через YAML-манифесты без изменения кода.

См. [MARKETPLACE.md***REMOVED***(../../runtime/MARKETPLACE.md) и [Runtime Providers README***REMOVED***(../../runtime/providers/README.md).

### 2.5 Deterministic First

LLM используется только там, где нужен интеллект.
Всё остальное — детерминированные алгоритмы:
- Поиск по FTS5
- Хранение в SQLite
- Индексация через TF-IDF
- Графовые запросы через BFS

### 2.6 Event Driven

Вся система построена на событиях.
Компоненты общаются через Event Bus (publish/subscribe).
Никаких прямых вызовов между модулями разных слоёв.

### 2.7 Marketplace-Ready

Архитектура должна позволять в будущем создать Marketplace.

Трёхслойная структура:
- `runtime/providers/` — YAML-манифесты (добавление Runtime без изменения кода)
- `runtime/plugins/` — Python-расширения (нестандартные протоколы)
- `runtime/recipes/` — человекочитаемые инструкции

Принципы:
- **No core change** — новый Runtime добавляется YAML-файлом + опционально адаптером
- **Auto-discovery** — RuntimeRegistry автоматически сканирует providers/
- **Capability-first** — пользователь выбирает capability, система выбирает Runtime

См. [MARKETPLACE.md***REMOVED***(../../runtime/MARKETPLACE.md).

---

## 3. Принципы лицензирования

**Buffy не должен нарушать лицензии сторонних проектов.**

Запрещается:
- обход лицензий
- модификация закрытого кода
- использование недокументированных внутренних API

Интеграция — только через:
- CLI
- MCP (Model Context Protocol)
- ACP (Agent Collaboration Protocol)
- публичные API
- официальные механизмы расширения

---

## 4. Принципы документирования Runtime

**Нельзя считать Runtime поддерживаемым до прохождения практической проверки.**

Уровни утверждений (в порядке убывания достоверности):
1. «поддерживается после успешной практической валидации» — Level 4+
2. «совместимость подтверждена» — Level 3+
3. «экспериментальная поддержка» — Level 2
4. «исследуется» — Level 1
5. «не проверено» — Level 0

**Никогда не обещать поддержку без реального тестирования.**

См. [RUNTIME_VALIDATION_FRAMEWORK.md***REMOVED***(RUNTIME_VALIDATION_FRAMEWORK.md) и [COMPATIBILITY_MATRIX.md***REMOVED***(COMPATIBILITY_MATRIX.md).

---

## 5. Принципы масштабирования

Система развивается по модели:

```
Single → Cowork → Teamwork → Organization → Community
```

Каждый следующий уровень надстраивается над предыдущим, не ломая его.
Архитектурные решения на уровне Single не должны препятствовать переходу к Teamwork.

См. [VISION_3.0.md***REMOVED***(../VISION_3.0.md), раздел «Три режима работы».

---

## 6. Принципы тестирования

- Каждый компонент имеет тесты
- Boundary Testing для всех интерфейсов
- Регрессионные тесты перед каждым релизом
- Code review для каждого изменения
- Никаких merge без прохождения тестов
- Все требования из [CODE_QUALITY_STANDARD.md***REMOVED***(CODE_QUALITY_STANDARD.md) обязательны

---

## 7. Принципы эволюции

- Evolution over Revolution — никаких rewrite
- Миграции данных — автоматические, обратно совместимые
- Deprecation — минимум за один мажорный релиз
- IDEAS.md хранит все идеи вечно (статус меняется, идея не удаляется)

---

*Связанные документы: [VISION_3.0.md***REMOVED***(../vision/VISION_3.0.md), [CODE_QUALITY_STANDARD.md***REMOVED***(CODE_QUALITY_STANDARD.md), [RUNTIME_VALIDATION_FRAMEWORK.md***REMOVED***(RUNTIME_VALIDATION_FRAMEWORK.md), [COMPATIBILITY_MATRIX.md***REMOVED***(COMPATIBILITY_MATRIX.md), [INTEGRATION_CONTRACT.md***REMOVED***(../../freebuff_plugin/INTEGRATION_CONTRACT.md), [MARKETPLACE.md***REMOVED***(../../runtime/MARKETPLACE.md)*
