Ниже — цельный промпт. Я бы именно с него начинал разработку Buffy 2.0.

Передаю его как архитектурное ТЗ для ИИ-исполнителя.

MISSION: Buffy Project 2.0 — Agentic Platform & Knowledge Operating System

РОЛЬ

Ты выступаешь как команда уровня Principal AI Architect, Distributed Systems Engineer, AI Agent Researcher, LLM Infrastructure Engineer и Knowledge Systems Architect.

Твоя задача — не написать отдельные файлы, а спроектировать полноценную агентную платформу нового поколения, ориентированную на долгосрочную работу над проектами.

Главная цель — создать систему, в которой LLM является лишь одним из компонентов, а не центром архитектуры.

---

ОСНОВНАЯ ИДЕЯ

Buffy — это не coding assistant.

Buffy — это Agentic Platform и Knowledge Operating System.

Ее задача:

- помнить;
- понимать состояние проекта;
- автоматически восстанавливать рабочий процесс;
- управлять задачами;
- использовать различные модели;
- использовать собственную базу знаний;
- работать месяцами без потери контекста.

Главный принцип:

«Один мозг — много моделей.»

Модель должна быть полностью заменяемой.

---

АРХИТЕКТУРНЫЕ ПРИНЦИПЫ

Проект должен строиться вокруг следующих принципов.

1. Model Agnostic

LLM является исполнителем.

Она не должна содержать бизнес-логику.

Система должна одинаково работать с:

- DeepSeek
- Qwen
- Ollama
- llama.cpp
- vLLM
- OpenAI API
- Claude
- Gemini

Добавление новой модели должно требовать только регистрации адаптера.

Никакой зависимости ядра от конкретной модели.

---

2. Project State First

Главной сущностью является не чат и не контекст.

Главная сущность — состояние проекта.

Каждый проект содержит собственное состояние.

Пример:

Project State

- TASK.md
- ROADMAP.md
- CHANGELOG.md
- ACTIVE_CONTEXT.md
- RULES.md
- MEMORY.db
- docs/
- conversations/
- checkpoints/

При запуске Buffy система должна восстанавливать именно состояние проекта.

---

3. Context Builder

Контекст не хранится одной простыней.

Он собирается динамически.

Перед каждым запросом система автоматически объединяет:

- Working Memory
- Project Memory
- RAG
- Architecture Rules
- TASK.md
- CHANGELOG
- ADR (Architecture Decision Records)
- Последние изменения проекта
- Пользовательские предпочтения

После объединения создается Unified Context.

Именно его получает модель.

---

4. Многоуровневая память

Спроектируй отдельные уровни памяти.

Working Memory

Текущая задача.

Последние сообщения.

Активный план.

Промежуточные результаты.

---

Project Memory

История проекта.

Архитектурные решения.

Обсуждения.

Roadmap.

Документация.

Задачи.

---

Knowledge Memory

Полноценная RAG-система.

Она должна содержать:

- документацию
- книги
- архитектурные статьи
- best practices
- freebuff базу знаний разработчика
- собственную базу знаний Buffy

Это НЕ память диалога.

Это библиотека знаний.

---

Personal Memory

Правила пользователя.

Предпочтения.

Стиль кода.

Соглашения.

Любимые технологии.

---

Archive

Старые проекты.

История.

Чекпоинты.

Полные логи.

---

KNOWLEDGE ENGINE

Не использовать классический RAG как единственный механизм.

Построить полноценный Knowledge Engine.

Он должен объединять:

- Vector Search
- SQLite Full Text Search
- Keyword Search
- Metadata Search
- Tag Search
- Graph Search
- Architecture Search
- Decision Search (ADR)
- Semantic Search

Система должна самостоятельно выбирать лучший способ поиска.

---

STREAMING CONTEXT

Каждое действие пользователя автоматически сохраняется.

Использовать:

SQLite WAL

+ 

Raw JSONL

+ 

Checkpoints

+ 

Summaries

Контекст должен переживать:

- закрытие приложения
- OOM
- перезапуск устройства
- смену модели

---

TASK SYSTEM

Каждая задача является самостоятельной сущностью.

Минимальная структура:

TASK.md

Описание

ТЗ

Промпт

TODO

Roadmap

Dependencies

Progress

Changelog

Notes

Каждый агент работает только через Task System.

---

MODEL ROUTER

Создать Capability-based Router.

Не использовать правила вроде:

если код →

Qwen

Вместо этого каждая модель должна иметь Capability Profile.

Например:

DeepSeek

- planning
- reasoning
- architecture

Qwen

- code
- offline
- local

Gemini

- vision

Claude

- review
- analysis

Router принимает решение автоматически.

---

ORCHESTRATOR

Оркестратор является сердцем платформы.

Он отвечает за:

планирование

разбиение задач

контроль выполнения

повторные попытки

валидацию

ревью

передачу задач другим моделям

Использовать FSM или DAG вместо линейного сценария.

---

TOOL RUNTIME

Инструменты являются отдельной системой.

Поддержать:

Shell

Python

Filesystem

Git

SQLite

HTTP

MCP

Browser

Termux API

Android API

Никакой логики инструментов внутри модели.

---

EVENT BUS

Все компоненты взаимодействуют через события.

Например:

TaskCreated

↓

CheckpointCreated

↓

ContextUpdated

↓

SummaryGenerated

↓

IndexUpdated

↓

MemorySynced

Минимизировать прямые зависимости компонентов.

---

PLUGIN SYSTEM

Спроектировать полноценную систему плагинов.

Примеры:

Telegram

Discord

GitHub

Obsidian

Google Drive

Local Models

MCP Servers

Каждый плагин должен подключаться без изменения ядра.

---

DOCUMENTATION

Архитектура должна быть полностью документирована.

Добавить:

ADR

Sequence Diagrams

Component Diagrams

Data Flow

State Diagrams

Deployment Diagrams

ER Diagram

API Specification

Folder Structure

---

ROADMAP

Разделить разработку на этапы.

Phase 1

Project State

Context Builder

Streaming Memory

Task System

Phase 2

Knowledge Engine

RAG

Memory Layers

Phase 3

Model Router

Orchestrator

Tool Runtime

Phase 4

Plugin API

MCP

Local Models

Distributed Agents

Phase 5

Flutter UI

Android Service

Remote Sync

---

ОСНОВНАЯ ЦЕЛЬ

Buffy не должна быть очередным AI-ассистентом.

Она должна стать полноценной Agentic Platform и Knowledge Operating System, обеспечивающей непрерывную работу над проектами, долгосрочную память, интеллектуальное управление контекстом, мультимодельную архитектуру и расширяемую экосистему.

Каждое архитектурное решение должно оцениваться по следующим критериям:

- масштабируемость;
- модульность;
- отказоустойчивость;
- независимость от модели;
- расширяемость;
- возможность автономной работы;
- простота сопровождения;
- совместимость с будущими компонентами.

Результат работы должен представлять собой архитектуру, которую можно развивать в течение многих лет без необходимости переписывать ядро.Я бы назвал это уже не просто промптом, а конституцией Buffy. На его основе можно последовательно генерировать архитектуру, ТЗ, структуру каталогов, интерфейсы модулей и реализацию каждого компонента по отдельности.