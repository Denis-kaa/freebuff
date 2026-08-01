# 🏗️ ARCHITECTURE REVIEW — Экосистема Denis AI
> **Статус:** LEGACY — исторический обзор экосистемы (2026-07-27); заменён на [ARCHITECTURE_CANONICAL.md***REMOVED***(ARCHITECTURE_CANONICAL.md) (см. [DOCUMENT_REGISTRY.md***REMOVED***(../DOCUMENT_REGISTRY.md))
> **Дата:** 2026-07-27
> **Методология:** Глубокий pattern-search (223 класса) + аудит Qwen IDE + трассировка Groq

---

## 🔍 QWEN CLI — Трассировка

| Вопрос | Ответ |
|--------|-------|
| Алиас `qwen` в shell-конфигах? | ❌ **НЕ НАЙДЕН** |
| `.bashrc`, `.bash_aliases`, `.profile`? | Нет упоминаний `qwen` |
| `which qwen` / `type qwen`? | `/data/data/com.termux/files/usr/bin/qwen` |

**Вердикт:** Алиас не прописан в текущих конфигах. Возможно, ты задавал его в сессии вручную (`alias qwen=...`) или он был в конфиге, который перезаписали. Qwen Code IDE при этом **активно используется** (5 usage-записей, токены за июль 2026).

**Рекомендация:** Добавь алиас явно:
```bash
echo 'alias qwen="qwen-code"' >> ~/.bashrc
```

---

## 🧠 QWEN IDE — Архитектура

```
~/.qwen/
├── config.json              # Провайдеры: ollama (qwen2.5:1.5b/0.5b), deepseek (v4-pro/flash)
├── settings.json            # API-ключи, modelProviders, env
├── output-language.md       # Язык вывода
├── installation_id
├── tip_history.json
├── usage_record.jsonl       # 5 записей
├── usage/
│   └── token-usage-2026-07.jsonl  # DeepSeek v4 Flash: ~130K токенов/запрос
├── projects_17/                # 4 изолированных проекта
│   ├── -data-data-com-termux-files-home/         # Termux home
│   ├── -data-data-com-termux-files-home-agent/   # phone-agent
│   ├── -data-data-com-termux-files-home-leviathan-os/  # leviathan-os
│   └── -storage-emulated-0-PROJECTS/             # Все проекты
├── todos/                   # 16 задач
├── file-history/            # 19 сессий с версионированием (@v1-@v8!)
├── memories/
│   ├── MEMORY.md
│   ├── user/identity.md     # "Денис, @vaalchik, AI-разработчик"
│   ├── user/relationship.md # Лена (Telegram ID: 8113236937)
│   └── feedback/            # content-localization, assumptions
├── plans/                   # Планы в Markdown
├── extensions/              # Включённые расширения
├── extension-store/         # Управление расширениями (lock, state, staging)
└── tmp/                     # 4 временные директории (логи, shell-выводы)
```

### Ключевые архитектурные решения Qwen

| Паттерн | Реализация | Оценка |
|---------|-----------|--------|
| **Изоляция проектов** | 4 отдельных проекта с собственными meta.json, чатами, subagents | ⭐⭐⭐⭐⭐ |
| **Версионирование файлов** | `file-history/{session***REMOVED***/*@v1-@v8` — трекинг изменений | ⭐⭐⭐⭐⭐ |
| **Memory-система** | Markdown-файлы: identity, relationship, feedback, reference | ⭐⭐⭐⭐ |
| **Subagent cleanup** | Фоновые файлы `.subagent-cleanup-*` — управление жизнью саб-агентов | ⭐⭐⭐⭐ |
| **Token tracking** | `token-usage-2026-07.jsonl` — per-request метрики | ⭐⭐⭐ |
| **Extension management** | lock/state/transactions — безопасное обновление | ⭐⭐⭐⭐ |

---

## 🗺️ ПОЛНАЯ КАРТА ПРОЕКТОВ

### ✅ Найдены при глубоком поиске (ранее пропущены)

| Проект | Путь | Что там | Оценка |
|--------|------|---------|--------|
| **phone-agent** | `~/phone-agent/` | Git-репо, `tools/router.py` (Router класс!) | ⭐⭐⭐⭐ |
| **leviathan engine** | `~/leviathan/root/` | aider configs, claude MCP auth, manicode, cursor | ⭐⭐⭐⭐ |
| **wingman_agent** | `~/wingman_agent/` | Python: agent.py, core_02/ (db, ai), dashboard/ | ⭐⭐⭐ |
| **mcp-server** | `~/mcp-server/` | Node.js: server.js, .env | ⭐⭐⭐ |
| **video-server** | `~/video-server/` | Node.js: server.js, .env, public/ | ⭐⭐ |

### Полный реестр (20+ проектов)

| Проект | Тип | Полезность | Состояние |
|--------|-----|-----------|-----------|
| **freebuff** 👑 | Главная среда | ⭐⭐⭐⭐⭐ | Активен |
| **LEVIATHAN** | Агентский framework | ⭐⭐⭐⭐⭐ | Активен |
| **fcc-claude** | Claude Code форк | ⭐⭐⭐⭐⭐ | Активен |
| **termux-ai-agent** | freebuff агент | ⭐⭐⭐⭐⭐ | Активен |
| **Qwen IDE** | AI-IDE | ⭐⭐⭐⭐⭐ | Активен |
| **blueprints_v3** | Kwork Arbitr v3 | ⭐⭐⭐⭐⭐ | Активен |
| **KWORK** | Freelance платформа | ⭐⭐⭐⭐ | Активен |
| **Assistant/** | 8 подпроектов | ⭐⭐⭐⭐ | Активен |
| **phone-agent** | Телефонный агент | ⭐⭐⭐⭐ | Найден! |
| **leviathan engine** | Конфиги AI-тулов | ⭐⭐⭐⭐ | Найден! |
| **mcp-server** | MCP-сервер | ⭐⭐⭐ | Найден! |
| **wingman_agent** | Python-агент | ⭐⭐⭐ | Найден! |
| **ai-engineering-pipeline** | Конвейер | ⭐⭐⭐⭐ | Активен |
| **kwork-cli** | CLI для KWORK | ⭐⭐⭐ | Активен |
| **tg_terminal_messenger** | Telegram CLI | ⭐⭐⭐ | Активен |
| **leviathan-os** | Заготовка OS | ⭐⭐ | Пустой backend |
| **video-server** | Видео-сервер | ⭐⭐ | Найден! |
| **LEVIATHAN_refactored** | Рефакторинг | ⭐⭐⭐⭐ | Дубль |
| **FREELANCE_SYSTEM** | Фриланс-агенты | ⭐⭐⭐⭐ | Дубль |
| **CLEAN_CORP_2** | Корпоративные агенты | ⭐⭐⭐ | Дубль |

---

## 🏛️ АРХИТЕКТУРНЫЕ ПАТТЕРНЫ (223 найденных класса)

### Иерархия агентов

```
BaseAgent (ABC)
├── LEVIATHAN: HunterAgent, SEOAgent, SalvageAgent
├── FREELANCE_SYSTEM: VideoAgent, WebDevAgent, TextAgent, SMMAgent,
│   TechspecAgent, SiteBuilderAgent, ResumeAgent, ResearchAgent,
│   QCAgent, PromptsAgent, PhotoAgent, MarketingAgent, CaseAgent,
│   InstructorAgent, BizdevAgent, ClassifierAgent
├── CoderUnit: CoderAgent, ArchitectAgent, ParserAgent, RevisorAgent
├── DesignerUnit: StyleAgent, QCDesignAgent, PromptBuilderAgent, BrieferAgent
├── ai_outreach: DiscoveryAgent, ProfilingAgent, EnrichmentAgent, DraftingAgent
├── aetheris: LoreKeeperAgent, CharacterGeneratorAgent, NolWriterAgent
└── wingman: WingmanAgent, FinanceAgent, HealerAgent, ContentAgent, LifeModeAgent
```

### Семейство роутеров

```
Router (базовый)
├── SmartRouter (FREELANCE_SYSTEM, aetheris, CLEAN_CORP, legal_ai)
├── ConfidenceRouter (LEVIATHAN_refactored)
├── AdaptiveRouter (LEVIATHAN_refactored)
├── LLMRouter (CLEAN_CORP_2, director)
├── ModelRouter (fcc-claude)
└── Router (termux-ai-agent)
```

### Семейство оркестраторов

```
Orchestrator
├── EventOrchestrator / EventDrivenOrchestrator
├── WritingOrchestrator (LEVIATHAN)
├── PipelineOrchestrator (survey-finder)
├── CoderUnitOrchestrator / DesignerUnitOrchestrator
├── BridgeOrchestrator (BRIDGE)
├── Orchestrator (kwork-cli)
└── BuildOrchestrator (LEVIATHAN_refactored)
```

### Семейство bridge/шлюзов

```
MCPBridge (termux-ai-agent) — Model Context Protocol
FreebuffBridge (freebuff) — freebuff ↔ agent
BridgeCore / BridgeEngine / BridgeRegistry (BRIDGE)
LISAGateway (termux-ai-agent) — сложность → freebuff/облачный
LLMGatewayImpl (termux-ai-agent)
GraphiteBridge (prometheus_client)
```

### Семейство pipeline

```
Pipeline (LEVIATHAN, KWORK)
OperationPipeline (excel_phone_processor)
ChapterPipeline (LEVIATHAN event_listener)
PipelineRunner (ai_outreach)
LeviathanPipeline (BRIDGE)
```

---

## 🔑 GROQ — ВАЖНОЕ ОТКРЫТИЕ

| Эндпоинт | Модель | Результат |
|----------|--------|-----------|
| `/v1/models` | — | ❌ 403 (требует других прав) |
| `/v1/chat/completions` | `llama-3.3-70b-versatile` | ✅ **HTTP 200!** |
| `/v1/chat/completions` | `gemma2-9b-it` | ❌ Decommissioned |

**Вывод:** Groq-ключи **НЕ протухли** для chat completions! Наш валидатор использовал неправильный эндпоинт (`/v1/models` вместо `/v1/chat/completions`). Нужно исправить валидацию в keypool.py — использовать `/v1/chat/completions` с минимальным запросом.

### Рабочие модели Groq (проверено):
- ✅ `llama-3.3-70b-versatile`

### Нерабочие:
- ❌ `gemma2-9b-it` — decommissioned

**Рекомендация:** Заменить эндпоинт валидации в keypool.py с `/v1/models` на `/v1/chat/completions` с `{"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":"hi"***REMOVED******REMOVED***,"max_tokens":1***REMOVED***`

---

## 📊 КАТЕГОРИЗАЦИЯ: ПОЛЕЗНОЕ / МУСОР / РЕФАКТОРИНГ

### 🟢 ПОЛЕЗНОЕ (сохранить и развивать)

| Компонент | Почему |
|-----------|--------|
| **LEVIATHAN core_02/** | Роутер, оркестратор, pipeline, key_pool, circuit_breaker — production-grade |
| **LEVIATHAN memory/** | storage, manifest, vector_store (ChromaDB), session, ghost_bin — мощная memory-система |
| **fcc-claude** | ModelRouter, MessagingWorkflow, trees (in-memory graph) — эталонная архитектура |
| **termux-ai-agent** | MCPBridge, LISAGateway, FSMLite, WorkerQueue — 5-слойная архитектура |
| **Qwen memories** | Файловая memory-система: identity, relationship, feedback — просто и эффективно |
| **Qwen file-history** | Версионирование изменений (@v1-@v8) — паттерн для трекинга |

### 🟡 ТРЕБУЕТ РЕФАКТОРИНГА

| Компонент | Проблема | Что делать |
|-----------|----------|------------|
| **LEVIATHAN дубли** | LEVIATHAN + LEVIATHAN_refactored + LEVIATHAN_push — 3 версии | Объединить в одну |
| **FREELANCE_SYSTEM дубли** | 2 копии (в Assistant/ и project_dev/) | Оставить одну, вторую удалить |
| **aetheris дубли** | aetheris_backend + aetheris_backend_q — две копии | Объединить |
| **Groq validator** | Проверяет `/v1/models` вместо `/v1/chat/completions` | Исправить эндпоинт |
| **phone-agent** | Только git-репо, без кода | Наполнить логикой |
| **leviathan-os** | Пустой backend/ | Либо наполнить, либо архивировать |

### 🔴 МУСОР (можно удалить)

| Компонент | Почему |
|-----------|--------|
| **tg_export/** | Пустая директория |
| **agent/** | Пустая директория |
| **video-server** | Node.js заглушка без логики |
| **venv-дубли** | `myproject/venv/`, `leviathan/root/survey-finder/venv/` — кеши |
| **node_modules** | `video-server/node_modules/`, `mcp-server/node_modules/` — можно переустановить |

---

## 🔄 ПЕРЕКРЫТИЕ ПАТТЕРНОВ (DRY-нарушения)

| Паттерн | Где дублируется (сколько раз) |
|---------|------------------------------|
| **SmartRouter** | 5 реализаций (FREELANCE_SYSTEM, aetheris, CLEAN_CORP_2, director, legal_ai) |
| **BaseAgent** | 4 версии (LEVIATHAN, FREELANCE_SYSTEM, ai_outreach, CLEAN_CORP_2) |
| **Orchestrator** | 8+ реализаций |
| **Pipeline** | 6+ реализаций |
| **AgentResult** | 3 определения |

**Рекомендация:** Вынести общие абстракции в `freebuff/core_02/` — единый SDK для всех проектов.

---

## 💡 РЕКОМЕНДАЦИИ

### Срочно (High)
1. 🔴 **Исправить Groq-валидатор** — ключи живые, эндпоинт неверный
2. 🟡 **Добавить алиас `qwen`** в `.bashrc`
3. 🟡 **Объединить LEVIATHAN-дубли** (3 копии → 1)

### Среднесрочно (Medium)
4. 🟡 **Вынести общие абстракции** в `freebuff/core_02/` (BaseAgent, Router, Orchestrator)
5. 🟡 **Наполнить phone-agent** — router.py есть, логики нет
6. 🟡 **Интегрировать Qwen memories** с ContextManager

### Стратегически
7. 🟢 **Единый SDK (`freebuff/core_02/`)** — устранить 5+ дублей SmartRouter
8. 🟢 **Гибридная валидация ключей** — быстрая (models list) + глубокая (chat completions)
9. 🟢 **Qwen file-history → ContextManager checkpoints** — миграция версионирования
