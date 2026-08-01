# Buffy Vision 3.0 — AI Infrastructure Layer

> **Версия:** 3.0.0  
> **Дата:** 2026-07-29  
> **Статус:** Черновик  
> **Авторы:** Buffy (DeepSeek v4 Flash)  
> **Основание:** [012_01_evolution_cowork_platform.md***REMOVED***(../../pompts_11/012_01_evolution_cowork_platform.md), [013_01_vision_2_0_universal_companion.md***REMOVED***(../../pompts_11/013_01_vision_2_0_universal_companion.md), [014_02_leviathan_arhitektura.md***REMOVED***(../../pompts_11/014_02_leviathan_arhitektura.md), [IDEAS.md***REMOVED***(../decisions/IDEAS.md)

---

## 1. Executive Summary

**Buffy — это AI Infrastructure Layer.**

Не агент. Не фреймворк. Не IDE. Инфраструктурный слой, который работает под, над и между любыми AI-инструментами.

```
Эволюция продукта:
  Local AI Agent → Agent Framework → Agent Platform → Companion Platform → AI Infrastructure Layer
       v1.x            v2.x              v3.x              v4.x                  v5.0+
```

В мире, где существуют десятки AI-агентов (Claude Code, Cursor, OpenClaw, Codex, GPT-5, Codebuff),
создание ещё одного — тупик. Buffy становится **открытой инфраструктурной платформой**, которая:

- **Усиливает** существующие AI-агенты, а не заменяет их
- **Работает полностью автономно** как freebuff агент
- **Поддерживает любой AI Runtime** через Runtime Abstraction Layer
- **Не зависит** от конкретной модели, провайдера или агентного фреймворка
- **Остаётся актуальной** через 5-10 лет независимо от эволюции LLM

Ключевой принцип: **Buffy — инфраструктура, которую подключают к Claude/Cursor/Codebuff, чтобы они стали умнее, памятливее и команднее.**

---

## 2. Три режима работы

Buffy — не монолитный продукт. Это платформа с тремя явными режимами использования,
каждый из которых надстраивается над предыдущим, не ломая его.

### Режим 1 — Single

**Один пользователь, один воркспейс.**

Buffy — персистентный контекст и мост к одному или нескольким Runtime
(Claude Code, OpenClaw, Codex, FreeBuff CLI). Даёт им функции, которых нет
из коробки: сохранение контекста между сессиями, документация, знания проекта.

**Это то, что уже существует и работает** — Core + текущий freebuff_plugin.

**Обслуживающие компоненты:**
| Компонент | Статус | Роль в Single |
|-----------|--------|---------------|
| ContextManager | ✅ Production | Сохранение сессий |
| Memory Engine | ✅ Production | 5 уровней памяти |
| Knowledge Engine | ✅ Production | FTS5 + TF-IDF поиск |
| Graph Index | ✅ Production | Граф связей |
| Model Gateway | ✅ Production | 6 провайдеров |
| Runtime Abstraction | ✅ Реализован (v4.9.0) | Адаптеры FreeBuff/Claude |
| MCP Server | ✅ Production | STDIO + HTTP |
| Scenario Engine | ✅ Production | 11 сценариев |
| OOM Protection | ✅ Production | Signal 9 защита |

### Режим 2 — Cowork (Companion)

**Один пользователь, несколько агентов/провайдеров одновременно.**

Buffy выступает мостом между агентными системами (OpenClaw, Claude Code, Codex) —
даёт им общий контекст и возможности, которых нет по отдельности у каждого.

**Ключевой механизм: агентная карусель (round-robin) между провайдерами/Runtime'ами.**
Если у одного закончился лимит/токены или пользователь экономит — задача передаётся
следующему в очереди без потери контекста.

**Обслуживающие компоненты:**
| Компонент | Статус | Роль в Cowork | GAP |
|-----------|--------|---------------|-----|
| Key Pool | 🟡 Частично | Ротация API-ключей провайдеров | Только ключи, не агенты |
| Runtime Abstraction | ✅ Реализован | Переключение между Runtime | Нет round-robin логики |
| Bridge Layer | ✅ Production | MCP↔ACP трансляция | Только прямая адресация, нет карусели |
| ACP Protocol | ✅ Production | Agent-to-agent коммуникация | Нет логики выбора агента по нагрузке |
| Model Gateway | ✅ Production | Fallback между провайдерами | Fallback только при ошибке, не по лимитам |

**Честный статус:** инфраструктура связи (connectivity) готова.
Инфраструктура оркестрации (orchestration) — **нет**:
- ❌ Нет round-robin между агентами (только прямая адресация `send_task(target, ...)`)
- ❌ Нет agent carousel (переключение при исчерпании лимита)
- ❌ Нет load-based routing
- ❌ Нет общей очереди задач между Runtime

### Режим 3 — Teamwork

**Несколько пользователей, несколько агентов, один проект.**

Каждый участник использует свой инструмент (один — Claude Code по подписке,
другой — OpenClaw, третий — Codex с собственными API-ключами).
Buffy синхронизирует контекст между ними через MCP + ACP.

**Ключевая функция:** разделение и переназначение задач. Пользователь настраивает
воркфлоу, кто за какую часть отвечает (backend/frontend), с переходом от «я один»
к «нас трое, каждый со своим воркспейсом».

**Обслуживающие компоненты:**
| Компонент | Статус | Роль в Teamwork | GAP |
|-----------|--------|-----------------|-----|
| ACP Protocol | ✅ Production | Agent-to-agent коммуникация | Нет task assignment/reassignment |
| Bridge Layer | ✅ Production | MCP↔ACP трансляция | Только point-to-point |
| MCP Server | ✅ Production | STDIO + HTTP интерфейс | Нет мульти-клиентских сессий |
| Event Bus | ✅ Production | Publish/subscribe | Нет distributed mode |
| Policy Engine | 💡 План | Роли и назначения | Весь компонент — план |

**Честный статус:** ACP + Bridge обеспечивают связь между агентами,
но **нет** логики верхнего уровня:
- ❌ Нет распределения ролей (кто за backend, кто за frontend)
- ❌ Нет переназначения задач между участниками
- ❌ Нет общей сессии для нескольких пользователей
- ❌ Нет Presence System
- ❌ Нет Policy Engine для ролей

---

## 3. Масштабирование

Модель масштабирования продукта:

```
Single
  ↓
Cowork
  ↓
Teamwork
  ↓
Organization
  ↓
Community
```

Каждый уровень надстраивается над предыдущим без разрушения.
Архитектурные решения на уровне Single не препятствуют переходу к Teamwork.

| Уровень | Пользователей | Агентов | Ключевые компоненты | Статус |
|---------|--------------|---------|-------------------|--------|
| **Single** | 1 | 1-2 | Core + Runtime Adapters + Bridge | ✅ Готово |
| **Cowork** | 1 | 2-5 | + KeyPool + Agent Carousel + Runtime Switching | 🟡 Connectivity готов, orchestration — нет |
| **Teamwork** | 2-10 | 3-10 | + ACP + Policy Engine + Presence + Task Assignment | 🟡 ACP/Bridge готовы, остальное — план |
| **Organization** | 10-100 | 5-20 | + Distributed Event Bus + SSO + Audit | 🔵 Концепт |
| **Community** | 100+ | 20+ | + Marketplace + Plugin Ecosystem + Federation | 🔵 Концепт |

---

## 4. Product Manifesto

### 4.1 Open Architecture Manifesto

```
🧱 Runtime Agnostic   — не привязан к конкретному AI Runtime
🏢 Provider Agnostic  — работает с любым API-провайдером
🧠 Model Agnostic     — не зависит от конкретной модели
🔌 Plugin First       — всё расширяется через плагины
⚙️ Deterministic First — LLM только там, где нужен интеллект
📡 Event Driven       — вся система построена на событиях
📱 Local First        — работает offline, синхронизация опциональна
📋 Policy Driven      — все решения определяются политиками пользователя
🌍 Offline Friendly   — без интернета — полная функциональность
👥 Collaboration Ready — multiple users, runtimes, agents
🔄 Backward Compatible — эволюция без разрушения
🔗 API First          — всё доступно через API
🧩 Modular by Design  — каждый компонент заменяем
```

### 4.2 Что Buffy НЕ является

| Заблуждение | Реальность |
|-------------|------------|
| ❌ Ещё один AI-агент | Инфраструктура, усиливающая существующих агентов |
| ❌ ChatGPT/DeepSeek с файловой системой | Детерминированная платформа с LLM Sparingly |
| ❌ Agent framework (LangChain, CrewAI) | Платформа, не привязанная к конкретному runtime |
| ❌ RAG-система / vector database | Knowledge Platform — единая система памяти |
| ❌ MCP-сервер | MCP — лишь один из протоколов коммуникации |
| ❌ Очередной coding assistant | Универсальная среда для любых проектов |

### 4.3 Целевая аудитория

| Аудитория | Проблема | Как Buffy помогает |
|-----------|----------|-------------------|
| **Solopreneur** | Контекст теряется между сессиями | Project State + Knowledge Platform |
| **Dev-команда** | Нет единой памяти и политик | Policy Engine + Event Platform + Collaboration |
| **AI-агенты** | Нет доступа к истории проекта | Runtime Abstraction + MCP + Bridge |
| **Фрилансер** | Нужны готовые шаблоны задач | Scenario Engine + Policy Packs |
| **Исследователь** | Много источников, нет связей | Knowledge Graph + RAG 2.0 |
| **DevOps** | Развёртывание AI-сред | Bootstrap Engine + Runtime Installer |
| **Enterprise** | Безопасность и аудит | Policy Engine + Event Store + Audit |

---

## 5. Архитектура 3.0

### 5.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BUFFY AI INFRASTRUCTURE LAYER                        │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │   CORE — Минимальное ядро, обязательно для любого режима работы      │  │
│  │                                                                      │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │  │
│  │  │ Project  │ │ Session  │ │ Memory   │ │ Event    │ │ Policy   │  │  │
│  │  │ State    │ │ Platform │ │ Engine   │ │ Platform │ │ Engine   │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │  │
│  │                                                                      │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────────────┐ │  │
│  │  │ Knowledge│ │ Graph    │ │ Workflow │ │ Bootstrap              │ │  │
│  │  │ Platform │ │ Index    │ │ Engine   │ │ Engine                 │ │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │   EXTENSIONS — Опциональные сервисы, подключаемые по профилю         │  │
│  │                                                                      │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │  │
│  │  │ MCP      │ │ Bridge   │ │ Runtime  │ │ Capability│ │ Key      │  │  │
│  │  │ Server   │ │ Platform │ │ Installer│ │ Registry │ │ Pool     │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │  │
│  │                                                                      │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │  │
│  │  │ Model    │ │ Provider │ │ Scenario │ │ ACP      │ │ OOM      │  │  │
│  │  │ Pool     │ │ Pool     │ │ Engine   │ │ Protocol │ │ Protect  │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │   LABS — Экспериментальные компоненты (могут измениться)             │  │
│  │                                                                      │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │  │
│  │  │ Presence │ │ RAG 2.0  │ │ Live     │ │ Team     │ │ Runtime  │  │  │
│  │  │ System   │ │          │ │ Collab   │ │ Mode     │ │ Doctor   │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │  │
│  │                                                                      │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────────────┐ │  │
│  │  │ Plugin   │ │ Workflow │ │ Policy   │ │ Distributed            │  │  │
│  │  │ SDK      │ │ SDK      │ │ Packs    │ │ Event Bus              │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Runtime Abstraction Layer

**Принцип:** Buffy никогда не зависит от конкретного AI Runtime.

```
┌────────────────────────────────────────────────────────────────┐
│                    RUNTIME ABSTRACTION LAYER                     │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Runtime API                            │  │
│  │  (generate, generate_stream, list_models, capabilities)   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                    │
│      ┌────────────────────┼────────────────────┐              │
│      ▼                    ▼                    ▼                │
│  ┌────────┐         ┌──────────┐         ┌──────────┐         │
│  │ freebuff│         │ Claude   │         │ OpenClaw │         │
│  │ Adapter│         │ Code     │         │ Adapter  │         │
│  └────────┘         └──────────┘         └──────────┘         │
│                                                                  │
│  ┌────────┐         ┌──────────┐         ┌──────────┐         │
│  │ Hermes │         │  Codex   │         │ Future   │         │
│  │ Adapter│         │ Adapter  │         │ Runtime  │         │
│  └────────┘         └──────────┘         └──────────┘         │
└────────────────────────────────────────────────────────────────┘
```

**Все Runtime подключаются через Adapter Layer.**
Buffy управляет установкой, но не содержит Runtime внутри себя.

### 5.3 Policy Engine

**Принцип:** Buffy лишь исполняет политики пользователя. Все решения определяются политиками.

```
Пользовательские политики определяют:
  • Runtime       — какой AI Runtime использовать
  • Provider      — через какого провайдера (OpenAI, Anthropic, DeepSeek)
  • Model         — какую модель
  • Workflow      — последовательность шагов
  • Fallback      — что делать при ошибке
  • Cost Limits   — максимальная стоимость
  • Retry Rules   — правила повторных попыток
  • Scheduling    — когда выполнять
  • Queue         — порядок обработки
  • Context Strategy — как собирать контекст
```

**Policy Packs** — переносимые пакеты политик для обмена между пользователями:
`Solo Developer`, `Startup`, `Enterprise`, `Research`, `Android Development`, `Offline`, `Budget`

### 5.4 Bootstrap Profiles

**Принцип:** Профиль установки определяет, какие компоненты Core/Extensions/Labs активировать.
Каждый профиль соответствует одному из режимов работы (см. раздел 2).

| Профиль | Режим | Runtime | Сервисы | Сценарий использования |
|---------|-------|---------|---------|----------------------|
| **Minimal** | Single | freebuff агент | Core только | Быстрый старт на телефоне |
| **Developer** | Single → Cowork | freebuff + Claude Code | Core + Scenario Engine + Bridge | Повседневная разработка |
| **Offline** | Single | freebuff (Qwen/Ollama) | Core + Knowledge | Работа без интернета |
| **Cloud** | Single → Cowork | Любой через API | Core + Provider Pool + Policy Engine | Мощные модели по запросу |
| **Android** | Single | Termux + freebuff | Core + OOM Protection + Monitor | Нативное использование |
| **Research** | Cowork | Все доступные | Core + RAG + Graph + Workflow | Исследования и анализ |
| **Team** | Teamwork | freebuff + Claude + др. | Core + Presence + ACP + Bridge + Collaboration | Совместная разработка |
| **Enterprise** | Teamwork → Organization | По политикам | Всё + Audit + Policy Engine | Командная работа, безопасность |

### 5.5 Capability Registry

**Принцип:** Пользователь выбирает не модель, а capability.

```
Planning │ Coding │ Documentation │ Review │ Research
Translation │ Testing │ Architecture │ Refactoring
```

Какая модель выполняет capability — определяется Policy Engine.

---

## 6. Current State vs Vision 3.0

| Компонент | Статус | Примечание |
|-----------|--------|------------|
| **CORE** | | |
| ContextManager (Session Platform) | ✅ Production | Расширить до мульти-пользователей |
| Memory Engine | ✅ Production | 5 уровней |
| Knowledge Engine | ✅ Production | FTS5 + TF-IDF + SVD |
| Graph Index | ✅ Production | BFS, subgraph |
| Event Bus | ✅ Production | publish/subscribe |
| Orchestrator (Workflow Engine) | 🟡 MVP | DAG, parallel execution |
| Policy Engine | 💡 План | Новый компонент |
| Bootstrap Engine | ✅ Production | Реализован и протестирован (61 тест) |
| **EXTENSIONS** | | |
| MCP Server | ✅ Production | STDIO + HTTP |
| MCP Client | 🆕 Реализован | stdio + HTTP transport |
| Bridge Layer | 🆕 Реализован | MCP↔ACP трансляция |
| ACP Protocol | 🆕 Реализован | Agent Collaboration Protocol |
| Runtime Abstraction | ✅ Production | Adapter Layer + Registry (v4.9.0, 60 тестов) |
| Runtime Installer | 💡 План | Auto-install runtimes |
| Scenario Engine | ✅ Production | 11 сценариев |
| Provider Pool | 🟡 Частично | ModelGateway поддерживает 6 провайдеров |
| Key Pool | 🟡 Частично | KeyPool с ротацией ключей (НЕ агентов) |
| Model Pool | 💡 План | Model Registry |
| Capability Registry | 💡 План | Пользователь выбирает capability |
| OOM Protection | ✅ Production | Signal 9 защита |
| **LABS** | | |
| Presence System | 💡 План | |
| RAG 2.0 | 💡 План | |
| Live Collaboration | 💡 План | |
| Team Mode | 💡 План | ACP/Bridge есть, но нет task assignment |
| Agent Carousel | 🔴 GAP | Round-robin между агентами НЕ реализован |
| Task Assignment | 🔴 GAP | Переназначение задач НЕ реализовано |
| Runtime Doctor | 💡 План | |
| Plugin SDK | 💡 План | |
| Workflow SDK | 💡 План | |
| Policy Packs | 💡 План | |
| Distributed Event Bus | 💡 План | |

---

## 7. Что уже реализовано (из 25 концепций 014_02_leviathan_arhitektura.md)

| # | Концепция | Статус | Компонент |
|---|-----------|--------|-----------|
| 1 | Product Pivot | ✅ Документация | VISION_3.0.md |
| 2 | Core Architecture | ✅ Документация | Раздел 5.1 |
| 3 | Runtime Abstraction | 💡 План | Adapter Layer |
| 4 | Bootstrap System | 💡 План | Bootstrap Engine |
| 5 | Runtime Installer | 💡 План | Runtime Installer |
| 6 | Bootstrap Profiles | 💡 План | |
| 7 | Provider Pool | 🟡 Частично | ModelGateway |
| 8 | Key Pool | 🟡 Частично | KeyPool |
| 9 | Model Pool | 💡 План | |
| 10 | Capability Registry | 💡 План | |
| 11 | Policy Engine | 💡 План | |
| 12 | Policy Packs | 💡 План | |
| 13 | Workflow Engine | 🟡 MVP | Orchestrator |
| 14 | Event Platform | ✅ Production | Event Bus + SQLite лог |
| 15 | Collaboration | 💡 План | |
| 16 | Presence | 💡 План | |
| 17 | Knowledge Platform | ✅ Production | Memory + Knowledge + Graph |
| 18 | Knowledge Graph | ✅ Production | Graph Index |
| 19 | Session Platform | ✅ Production | ContextManager |
| 20 | Plugin SDK | 🟡 MVP | Plugin API |
| 21 | Workflow SDK | 💡 План | |
| 22 | Bridge Platform | 🆕 Реализован | Bridge Layer + ACP + MCP Client |
| 23 | Runtime Doctor | 💡 План | |
| 24 | UX Philosophy | ✅ Документация | Раздел 8 |
| 25 | Open Architecture Manifesto | ✅ Документация | Раздел 4.1 |

---

## 8. UX Philosophy

Пользователь не должен знать сложность системы:

| Скрываем | Показываем |
|----------|------------|
| MCP протокол | «Подключить Claude Code» |
| Runtime Adapter | «Работать freebuff / в облаке» |
| Runtime Layer | «Выбрать исполнителя» |
| Bridge Layer | «Подключить агента» |
| Event Bus | «История изменений» |
| Policy Engine | «Настроить правила» |
| ACP Protocol | «Пригласить участника» |

---

## 9. Стратегия развития

### Этап 0: База (текущий — v4.x)
**Статус:** ✅ Завершено

- ContextManager + Memory + Knowledge + Graph Engines
- Event Bus + MCP Server + REST API
- Bridge Layer + ACP + MCP Client
- Scenario Engine + Telegram Bot
- OOM Protection
- 836 тестов → 1143 тестов (v4.9.0)

### Этап 1: Infrastructure Core (v5.0)
**Фокус:** Bootstrap, Policy Engine, Runtime Abstraction

- [ ***REMOVED*** **Bootstrap Engine** — идемпотентное развёртывание среды
- [ ***REMOVED*** **Runtime Abstraction Layer** — универсальный Runtime API
- [ ***REMOVED*** **Runtime Installer** — авто-установка freebuff/Claude/OpenClaw
- [ ***REMOVED*** **Policy Engine** — пользовательские политики
- [ ***REMOVED*** **Capability Registry** — выбор capability вместо модели

### Этап 2: Ecosystem (v6.0)
**Фокус:** Интеграция, Provider Pool, Policy Packs

- [ ***REMOVED*** **Provider Pool v2** — полная поддержка всех провайдеров
- [ ***REMOVED*** **Key Pool v2** — ротация, лимиты, бюджеты, failover
- [ ***REMOVED*** **Model Pool** — Model Registry
- [ ***REMOVED*** **Policy Packs** — переносимые пакеты политик
- [ ***REMOVED*** **Plugin SDK** — SDK для сторонних разработчиков
- [ ***REMOVED*** **Workflow SDK** — пользовательские Workflow

### Этап 3: Collaboration (v7.0)
**Фокус:** Множество участников, присутствие

- [ ***REMOVED*** **Presence System** — статусы участников
- [ ***REMOVED*** **Team Mode** — несколько пользователей + Runtime
- [ ***REMOVED*** **Project Pulse** — лента событий проекта
- [ ***REMOVED*** **Session Platform v2** — мульти-пользовательские сессии
- [ ***REMOVED*** **Runtime Doctor** — диагностика и восстановление

### Этап 4: Intelligence (v8.0)
**Фокус:** RAG 2.0, распределённость

- [ ***REMOVED*** **RAG 2.0** — agentic RAG, re-ranking, HyDE
- [ ***REMOVED*** **Distributed Event Bus** — события между устройствами
- [ ***REMOVED*** **Live Collaboration** — real-time редактирование
- [ ***REMOVED*** **Deterministic First** — минимизация LLM

---

## 10. Feature Matrix

| Компонент | Core | Extensions | Labs |
|-----------|------|------------|------|
| ContextManager | ✅ | | |
| Memory Engine | ✅ | | |
| Knowledge Engine | ✅ | | |
| Graph Index | ✅ | | |
| Event Bus | ✅ | | |
| Policy Engine | 💡 | | |
| Bootstrap Engine | ✅ | | |
| MCP Server | | ✅ | |
| MCP Client | | ✅ | |
| Bridge Layer | | ✅ | |
| ACP Protocol | | ✅ | |
| Scenario Engine | | ✅ | |
| Provider Pool | | ✅ | |
| Key Pool | | ✅ | |
| Model Pool | | 💡 | |
| Capability Registry | | 💡 | |
| Runtime Abstraction | | ✅ | |
| Runtime Installer | | 💡 | |
| Plugin SDK | | | 💡 |
| Workflow SDK | | | 💡 |
| Policy Packs | | | 💡 |
| Presence | | | 💡 |
| RAG 2.0 | | | 💡 |
| Team Mode | | | 💡 |
| Live Collab | | | 💡 |
| Runtime Doctor | | | 💡 |

---

## 11. Риски

| Риск | Вероятность | Влияние | Митигация |
|------|------------|---------|-----------|
| Feature creep — слишком много компонентов | Высокая | Критическое | Core/Extensions/Labs жёсткое разделение |
| Сложность интеграции Runtime | Высокая | Высокое | Начать с одного (freebuff), добавлять по одному |
| Потеря фокуса на Termux | Средняя | Среднее | Local First — базовый принцип |
| Зависимость от API-провайдеров | Средняя | Высокое | Provider Pool с graceful fallback |
| Невостребованность платформы | Низкая | Критическое | Focus на solopreneur — самая большая аудитория |
| Усложнение кодовой базы | Средняя | Среднее | Модульность, Boundary Testing, ADR |

---

## 12. Заключение

**Buffy 3.0 — это AI Infrastructure Layer.**

Не очередной агент. Не фреймворк. Инфраструктура, которая:
- Остаётся актуальной через 5-10 лет
- Не зависит от конкретных LLM, провайдеров и Runtime
- Усиливает существующие агенты, а не конкурирует с ними
- Работает от Android-телефона до серверного кластера
- Определяется политиками пользователя, а не кодом

Главная победа Vision 3.0: разработчик скажет:
> *«Я установил Buffy, подключил свой Claude Code, настроил политики и забыл про инфраструктуру. Он просто работает.»*

---

## 13. Следующие документы

Из 17 требуемых артефактов 014_02_leviathan_arhitektura.md готовы:

| # | Артефакт | Статус | Файл |
|---|----------|--------|------|
| 1 | **VISION 3.0** | ✅ Готов | `VISION_3.0.md` |
| 2 | **PRODUCT MANIFESTO** | ✅ Включён | Раздел 4 |
| 3 | **ARCHITECTURE 3.0** | 🟡 Частично | `../core/ARCHITECTURE.md` (нужно расширить) |
| 4 | **PRODUCT ROADMAP** | ✅ Готов | `ROADMAP.md` |
| 5 | **FEATURE MATRIX** | ✅ Включён | Раздел 10 |
| 6 | **RISK REGISTER** | ✅ Включён | Раздел 11 |
| 7 | **ARCHITECTURAL DECISIONS** | 🟡 Частично | `../decisions/DECISIONS.md` (нужен ADR для Vision 3.0) |
| 8 | **IMPLEMENTATION ROADMAP** | ✅ Включён | Раздел 9 |
| 9 | **OPEN QUESTIONS** | 💡 TODO | `docs_10/OPEN_QUESTIONS.md` |
| 10 | **BOOTSTRAP SPECIFICATION** | 💡 TODO | — |
| 11 | **RUNTIME ABSTRACTION SPEC** | 💡 TODO | — |
| 12 | **POLICY ENGINE SPECIFICATION** | 💡 TODO | — |
| 13 | **CAPABILITY SPECIFICATION** | 💡 TODO | — |
| 14 | **EVENT PLATFORM SPECIFICATION** | 💡 TODO | — |
| 15 | **KNOWLEDGE PLATFORM SPEC** | 💡 TODO | — |
| 16 | **BRIDGE PLATFORM SPECIFICATION** | 💡 TODO | — |
| 17 | **PLUGIN SDK SPECIFICATION** | 💡 TODO | — |
| 18 | **WORKFLOW SDK SPECIFICATION** | 💡 TODO | — |
| 19 | **INSTALLATION STRATEGY** | 💡 TODO | — |

---

*Связанные документы: [IDEAS.md***REMOVED***(../decisions/IDEAS.md), [ROADMAP.md***REMOVED***(ROADMAP.md), [ARCHITECTURE.md***REMOVED***(../engineering-memory/ARCHITECTURE.md), [BUFFY.md***REMOVED***(../../BUFFY.md)*
