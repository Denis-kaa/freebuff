# LEVIATHAN Inventory — Категоризация A/B/C + Ребрендинг терминологии

| Поле | Значение |
|------|----------|
| **Документ** | LEVIATHAN Inventory v1.1 (от v1, bump 2026-08-06 — ROADMAP-FR-001 Шаг 3: forge_pipeline/forge_registry/workspace в Cat-A + cross-ref) |
| **Релиз платформы** | v5.97.0 |
| **Дата** | 2026-08-05 |
| **Источник** | promt58 (ветка 3) + `pompts_11/014_02_leviathan_arhitektura.md` |
| **Задача** | Инвентаризация 25 компонентов LEVIATHAN: категории A/B/C + ребрендинг под терминологию Buffy |
| **Контекст** | Buffy Forge v1.1 (Workspace/Project), Organizational Memory, SmartRouter, ARB/DIS/AG |

---

## Сводка

LEVIATHAN проектировался как «Companion Platform» — инфраструктурный слой для AI-агентов. После архитектурного трека promt51→58 многие концепции LEVIATHAN уже спроектированы в Buffy под другими именами. Этот документ проводит инвентаризацию: что уже есть, что совместимо, что требует ребрендинга.

---

## Категоризация A/B/C

### A — Core: уже существует в Buffy или критично для ядра

| # | Компонент LEVIATHAN | Категория | Аналог в Buffy | Статус |
|---|---------------------|-----------|----------------|--------|
| 3 | **Runtime Abstraction Layer** | A | SmartRouter + ModelCatalog (`core_02/router.py`) | ✅ Production |
| 6 | **Capability Registry** | A | SmartRouter (`route()` по capabilities) | ✅ Production |
| 7 | **Provider Pool** | A | ModelCatalog.default() — OpenAI, Anthropic, DeepSeek, Gemini, Groq, Ollama | ✅ Production |
| 9 | **Model Pool** | A | ModelCatalog — 6 моделей с capability profiles | ✅ Production |
| 14 | **Event Platform** | A | EventBus + `event_log` (events.db) + `prompt_dispatcher.py` | ✅ Production |
| 17 | **Knowledge Platform** | A | Organizational Memory (RFC v5.92.0): Memory Store + Knowledge Graph + Semantic Layer | 📋 RFC |
| 11 | **Policy Engine** | A | Policy (Evolution v5.93.0, I-3): advisory / mandatory / blocking | 📋 RFC |
| 2 | **Core Architecture** | A | Buffy Forge (RFC-BF-001 v1.1): L0-L5 + Workspace/Project контейнеры | 📋 RFC |
| 25 | **Open Architecture Manifesto** | A | 10 принципов Buffy Forge §2 + Additive Architecture | ✅ Design |

| 26 | **Forge Pipeline (L0-L5 runtime)** | A | `core_02/forge_pipeline.py`: FORGE→CHECK→BUILD→TEST→DEPLOY→REPORT stages + `scripts_01/forge.py` CLI | ✅ Production |
| 27 | **Forge Registry (state-of-truth)** | A | `core_02/forge_registry.py`: YAML-реестр статусов (UNFORGED→DEPLOYED/FAILED), история запусков (cap 20). Persists via `data_13/forge_registry.yaml` | ✅ Production |
| 28 | **Workspace/Project контейнеры (L-1/L-2)** | A | `core_02/workspace.py`: Workspace (L-1) как корневой контейнер, Project (L-2) как изолированная среда с project.yaml + requirements (README/RUNNABLE/CHECKLIST) + run_env_doctor | ✅ Production |

---

## 🔗 Предварительные условия переноса (ROADMAP-FR-001)

> **Контекст:** до того, как эти компоненты будут перенесены в LEVIATHAN как «Candidate migration», Buffy должна закрыть ROADMAP-FR-001 (Reconciliation of Wizard vs Forge).

| Условие | Статус | Источник |
|---------|--------|----------|
| **Шаг 1** (fact-check разрыва Wizard↔Forge) | ✅ CLOSED 2026-08-06 | Hypothesis C verdict + TG-shared corrigendum → [`PB-16` в `core_02/LESSONS.md`***REMOVED***(../../core_02/LESSONS.md) |
| **Шаг 2** (Case 2' doc-only — §2a ADDITIVE граница) | ✅ CLOSED 2026-08-06 | RFC_BUFFY_FORGE_V1 v1.1 → v1.2: §2a.1/§2a.2/§2a.3 (`Grep`-устойчивые номера строк 178-270) — см. [`docs_10/engineering-memory/RFC_BUFFY_FORGE_V1.md`***REMOVED***(RFC_BUFFY_FORGE_V1.md) и [`docs_10/ROADMAP_FORGE_RECONCILIATION.md`***REMOVED***(../../ROADMAP_FORGE_RECONCILIATION.md) |
| **Пре-условие Шага 3 (LEVIATHAN inventory)** | 🟢 Этот документ | forge_pipeline/forge_registry/workspace кандидаты добавлены в Cat-A с явной ссылкой на ROADMAP-FR-001 |
| **Канонический режим pytest для forge_*** | ✅ Документирован | `core_02/LESSONS.md` PB-17: `dry_run=True` для env_doctor-зависимых тестов |

### B — Extensions: важно, но не блокирует ядро

| # | Компонент LEVIATHAN | Категория | Аналог в Buffy / Комментарий | Статус |
|---|---------------------|-----------|------------------------------|--------|
| 13 | **Workflow Engine** | B | Implementation Forge (L3) — Tasks, Code Gen, Migrations | 📋 Design |
| 8 | **Key Pool** | B | **НЕТ аналога** — управление API-ключами (ротация, failover, бюджеты). Новый компонент. | ❌ Нет |
| 4 | **Bootstrap System** | B | **НЕТ аналога** — развёртывание AI-среды (Termux, proot-distro, Node.js, Python, Git). Новый компонент. | ❌ Нет |
| 19 | **Session Platform** | B | `context.db` sessions + event_log | ✅ Production (частично) |
| 20 | **Plugin SDK** | B | Forge extensions (L2+): новые Forge'ы через контракт EventBus + OM | 📋 Design |
| 22 | **Bridge Platform** | B | Scenario Registry + Adapter Layer (Blueprint v3 → Scenario ABC) | ✅ Production |
| 5 | **Runtime Installer** | B | Частично: Wizard (`scripts_01/wizard.py`) + `--selftest` | ✅ Production (частично) |
| 23 | **Runtime Doctor** | B | Drift Detection (`drift_check.py`) + AG (Architecture Governance) | ✅ Production (частично) |
| 1 | **Product Pivot** | B | Уже выполнен: Local Agent → Platform → Buffy Forge | ✅ Выполнено |

### C — Labs/Future: визионерское, не сейчас

| # | Компонент LEVIATHAN | Категория | Комментарий |
|---|---------------------|-----------|-------------|
| 15 | **Collaboration (Team Mode)** | C | Мульти-пользователь, мульти-Runtime, мульти-сервер. Не сейчас. |
| 16 | **Presence** | C | Реальное время: кто онлайн, что делает агент. Не сейчас. |
| 12 | **Policy Packs** | C | Переносимые пакеты политик (Solo, Startup, Enterprise). Визионерское. |
| 21 | **Workflow SDK** | C | Пользовательские Workflow. После Plugin SDK. |
| 10 | **Capability → Model mapping** | C | Уже частично: SmartRouter. Полный mapping — после Model Pool. |
| 18 | **Knowledge Graph** | C | Уже в OM RFC: GraphIndex + 9 rel_types. Полный Knowledge Graph — Phase 3+. |
| 24 | **UX Philosophy** | C | «Пользователь не должен знать про MCP/Adapter/Bridge». Философия, не компонент. |

---

## Ребрендинг терминологии

### Термины, которые нужно заменить (LEVIATHAN → Buffy)

| LEVIATHAN | Buffy | Причина |
|-----------|-------|---------|
| **Companion Platform** | **Workspace OS** / Buffy Platform | Manifest (документ 68): Workspace OS — операционная система для проектов. «Companion» — уменьшительное; Buffy — самостоятельная платформа. |
| **Runtime** | **Scenario** / Agent | Scenario — роль + pipeline; Agent — исполнитель. «Runtime» перегружено (Python runtime, Node runtime, AI runtime). |
| **Runtime Abstraction Layer** | **SmartRouter** + ModelCatalog | Уже реализовано. Не нужно переименовывать. |
| **Capability Registry** | **SmartRouter** | Уже реализовано. Не нужно переименовывать. |
| **Provider Pool** | **ModelCatalog** | Уже реализовано. |
| **Key Pool** | **Key Vault** / Key Manager | «Pool» перегружено (Connection Pool, Thread Pool). «Vault» точнее: безопасное хранение. |
| **Policy Engine** | **Policy** (Evolution I-3) | Уже спроектировано. |
| **Workflow Engine** | **Implementation Forge** (L3) | «Workflow» — общее; «Implementation Forge» — конкретное место в архитектуре. |
| **Knowledge Platform** | **Organizational Memory** | Уже спроектировано (RFC v5.92.0). |
| **Event Platform** | **EventBus** + event_log | Уже реализовано. |
| **Session Platform** | **Session Store** (context.db) | Уже реализовано. |
| **Plugin SDK** | **Forge Extension SDK** | «Plugin» — общее; «Forge Extension» — конкретное: новый Forge по контракту. |
| **Bridge Platform** | **Scenario Registry** + Adapter | Уже реализовано (Blueprint v3 → Scenario ABC). |
| **Bootstrap System** | **Bootstrap Engine** (новый Forge?) | Оставить «Bootstrap» — точное имя. |
| **Runtime Doctor** | **Drift Detector** / AG Diagnostics | Уже частично: `drift_check.py` + AG. |
| **Runtime Installer** | **Wizard** + `--selftest` | Уже реализовано. |

### Термины, которые СОВПАДАЮТ (оставить)

| Термин | LEVIATHAN | Buffy | Статус |
|--------|-----------|-------|--------|
| Provider | AI-провайдер (OpenAI, Anthropic, ...) | Provider enum (GEMINI, DEEPSEEK, GROQ, ...) | ✅ Совпадает |
| Model | LLM-модель | ModelEntry в ModelCatalog | ✅ Совпадает |
| Capability | Что модель умеет | capabilities: List[str***REMOVED*** | ✅ Совпадает |
| Policy | Правила пользователя | Policy: advisory / mandatory / blocking | ✅ Совпадает |
| Event | Событие в системе | event_log + EventBus | ✅ Совпадает |
| Graph | Knowledge Graph | GraphIndex (rel_types) | ✅ Совпадает |

---

## Что уже сделано (не нужно проектировать заново)

| LEVIATHAN-компонент | Где уже реализовано в Buffy |
|---------------------|---------------------------|
| Runtime Abstraction | `core_02/router.py`: SmartRouter + ModelCatalog (6 моделей, 4 провайдера) |
| Capability Registry | `SmartRouter.route(['reasoning', 'plan', 'architecture'***REMOVED***)` → `deepseek-v4-pro` |
| Provider Pool | `ModelCatalog.default()`: OpenAI, Anthropic, DeepSeek, Gemini, Groq, Ollama |
| Model Pool | 6 ModelEntry: qwen2.5:1.5b, qwen2.5:0.5b, deepseek-v4-flash, deepseek-v4-pro, gemini-2.5-flash, llama-3.3-70b |
| Event Bus | `scripts_01/prompt_dispatcher.py` + `context_12/events.db` |
| Knowledge Memory | RFC OM v1 (v5.92.0): 10 типов KO, Memory Store, Knowledge Graph, Semantic Layer |
| Policy | Evolution v5.93.0 (I-3): enforcement levels |
| Sessions | `data_13/context.db`: sessions, messages |
| Bridge/Adapter | `core_02/scenario_registry.py` + `BlueprintCorpus` → Scenario ABC |

---

## Что действительно НОВОЕ (Buffy ещё не покрывает)

| Компонент | Почему новое | Приоритет |
|-----------|-------------|-----------|
| **Key Vault** | Управление API-ключами: ротация, failover, бюджеты, лимиты. Buffy использует ключи через env, но не управляет ими. | B |
| **Bootstrap Engine** | Развёртывание AI-среды «с нуля»: Termux → proot-distro → Python/Node.js → Git → зависимости. Идемпотентный. | B |
| **Collaboration** | Team Mode: несколько пользователей, Runtime, серверов. | C |
| **Presence** | Реальное время: кто онлайн, что делает агент. | C |
| **Policy Packs** | Переносимые пакеты: Solo Developer, Startup, Enterprise. | C |

---

## Рекомендация

1. **LEVIATHAN как отдельный проект** — сохранить. Это не конфликтует с Buffy: Buffy — платформа для архитектурного проектирования, LEVIATHAN — инфраструктурный слой (Bootstrap, Key Vault, Runtime management).

2. **НЕ дублировать** — всё, что уже есть в Buffy (SmartRouter, ModelCatalog, EventBus, OM), использовать как есть. LEVIATHAN подключает Buffy как один из Runtime.

3. **Ребрендинг** — заменить «Companion Platform» → «LEVIATHAN Infrastructure Layer»; «Runtime» → «Scenario»; «Workflow Engine» → «Pipeline Engine» (не «Forge» — занято).

4. **Приоритет:** Key Vault (B) + Bootstrap Engine (B) — единственные по-настоящему новые компоненты. Остальное — либо уже есть в Buffy, либо C-категория.

---

*Конец LEVIATHAN Inventory v1.*
