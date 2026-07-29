MISSION: Buffy Distributed Agent Platform (DAP)

РОЛЬ

Ты являешься командой мирового уровня:

- Principal AI Architect
- Distributed Systems Engineer
- Multi-Agent Systems Researcher
- Protocol Designer
- LLM Infrastructure Engineer
- Runtime Architect

Твоя задача — спроектировать архитектуру Buffy как распределённой агентной платформы следующего поколения.

Цель проекта — отказаться от концепции "одного суперагента" и перейти к архитектуре, где множество специализированных агентов работают совместно под управлением единого ядра.

---

ГЛАВНАЯ ИДЕЯ

Не создавать самого умного агента.

Создать систему, которая объединяет лучших специализированных агентов.

Buffy должна стать операционной системой агентной экосистемы.

---

ОСНОВНЫЕ ПРИНЦИПЫ

Single Core

Существует только одно ядро.

Ядро отвечает исключительно за:

- управление жизненным циклом;
- память;
- состояние проекта;
- маршрутизацию;
- планирование;
- безопасность;
- аудит;
- журналирование;
- синхронизацию.

Ядро никогда не занимается выполнением пользовательских задач.

---

Specialized Agents

Каждый агент выполняет только одну область задач.

Например:

Code Agent

Review Agent

Planning Agent

Memory Agent

Knowledge Agent

Browser Agent

Git Agent

Filesystem Agent

Android Agent

Termux Agent

Testing Agent

Documentation Agent

Каждый агент должен иметь минимальный набор инструментов.

Запрещается создавать универсального агента, умеющего всё.

---

Reverse Agent Protocol

Спроектировать реверсивный протокол взаимодействия.

Buffy должна одинаково работать в двух режимах.

Host Mode

Buffy управляет внешними агентами.

Например:

Claude Code

Codex

OpenClaw

Hermes

Aider

Qwen

Ollama

Local Agents

---

Agent Mode

Buffy сама становится агентом внутри другой системы.

Например:

Claude Code вызывает Buffy

OpenClaw вызывает Buffy

Hermes использует Buffy как Memory Service

Codex использует Buffy как Knowledge Provider

Buffy становится полноценным сервисом.

---

INTERNAL AGENT API

Все агенты взаимодействуют исключительно через внутренний API.

Ядро не знает ничего о конкретной реализации агента.

Каждый агент реализует единый интерфейс.

Например:

Initialize()

Capabilities()

Health()

Execute(Task)

Interrupt()

Cancel()

Checkpoint()

Resume()

Shutdown()

---

EVERYTHING IS AN ADAPTER

Любая внешняя система должна подключаться адаптером.

Например:

Claude Adapter

Codex Adapter

OpenClaw Adapter

Hermes Adapter

Gemini Adapter

OpenAI Adapter

MCP Adapter

ACP Adapter

A2A Adapter

Custom Adapter

Никакой логики внешних протоколов внутри ядра.

---

CAPABILITY REGISTRY

Каждый агент регистрирует свои возможности.

Пример.

Agent

CodeAgent

Capabilities

Python

Rust

Refactoring

Testing

Git

Другой пример.

KnowledgeAgent

Capabilities

RAG

Semantic Search

Documentation

ADR Search

Memory

Оркестратор принимает решения только на основании Capability Registry.

---

TOOL ISOLATION

Каждый агент имеет только необходимые инструменты.

Например.

Git Agent

Git

Filesystem

Code Agent

Filesystem

Compiler

Testing Agent

Docker

Python

Memory Agent

SQLite

Vector Database

Knowledge Agent

RAG

Index

Graph

Запрещается выдавать каждому агенту полный доступ ко всем инструментам.

---

ORCHESTRATION

Buffy должна использовать Planner.

Planner разбивает большую задачу на подзадачи.

Каждая подзадача отправляется соответствующему агенту.

Пример.

Создать новую функцию

↓

Planning Agent

↓

Code Agent

↓

Testing Agent

↓

Review Agent

↓

Documentation Agent

↓

Memory Agent

↓

Done

---

AGENT DISCOVERY

Buffy автоматически обнаруживает новых агентов.

Каждый агент публикует:

Название

Версию

Capabilities

Поддерживаемые протоколы

Статус

Здоровье

Поддерживаемые модели

---

EVENT BUS

Вся система построена на событиях.

Примеры.

AgentConnected

AgentDisconnected

TaskAssigned

TaskCompleted

TaskFailed

CheckpointCreated

MemoryUpdated

KnowledgeIndexed

ContextChanged

PlannerStarted

PlannerFinished

---

SECURITY

Каждый агент работает в собственной песочнице.

Поддержать:

Permission Model

Capability Tokens

Tool Access Control

Audit Log

Execution Limits

Resource Limits

---

OBSERVABILITY

Спроектировать систему мониторинга.

Каждый агент должен публиковать:

Latency

CPU

RAM

Tool Usage

Model Usage

Failures

Retries

Queue Length

Task Duration

---

FAULT TOLERANCE

Если агент завершился аварийно:

Buffy должна:

обнаружить сбой;

сохранить состояние;

назначить другого исполнителя;

восстановить выполнение;

обновить журнал.

---

MEMORY SHARING

Память не принадлежит агентам.

Память принадлежит Buffy Core.

Любой агент получает только необходимые части памяти.

Memory является отдельным сервисом.

---

KNOWLEDGE SHARING

Агенты не индексируют знания самостоятельно.

Все знания предоставляет Knowledge Engine.

Любой агент делает запрос.

Knowledge Engine возвращает контекст.

---

FUTURE

Архитектура должна позволять подключать:

freebuff модели;

облачные модели;

внешних агентов;

MCP;

ACP;

A2A;

собственные плагины;

удалённых исполнителей;

кластер агентов;

распределённые вычисления.

Без изменения ядра.

---

КОНЕЧНАЯ ЦЕЛЬ

Buffy должна стать универсальной платформой, которая объединяет любые модели, любые агентные фреймворки, любые протоколы и любые инструменты в единую экосистему.

Главная философия проекта:

- одно ядро;
- единая память;
- единое состояние проекта;
- единая система знаний;
- множество независимых специализированных агентов;
- полная независимость от конкретной модели, конкретного агента и конкретного протокола.

Любое архитектурное решение должно отвечать на вопрос:

«Позволит ли это через пять лет подключить нового агента или новый протокол без изменения ядра Buffy?»

Если ответ отрицательный — решение должно быть переработано.