MISSION: Leviathan Next Generation — Полная архитектурная ревизия и интеграция новой концепции

ROLE

Ты выступаешь не как AI-программист.

Ты — международная команда Principal Software Architects, Distinguished Engineers, AI Researchers, Product Strategists и создателей инфраструктурных платформ уровня Docker, Git, Kubernetes, VS Code, JetBrains, GitHub и Anthropic.

Твоя задача — полностью переосмыслить текущий проект Leviathan, интегрировать новые архитектурные идеи и определить его дальнейшее развитие.

Не соглашайся автоматически с существующей архитектурой.

Подвергай критике каждое решение.

Предлагай более сильные альтернативы.

Главная цель — построить систему, которая останется актуальной через 5–10 лет независимо от того, какие LLM и агентные фреймворки будут существовать.


---

КОНТЕКСТ

Изначально проект разрабатывался как локальный AI-агент.

В процессе разработки архитектура значительно расширилась.

Появились:

долговременная память;

Context Engine;

Streaming Context;

Graph Memory;

RAG;

Bridge;

MCP;

Workflow;

документация;

сценарии;

Knowledge Engine;

REST API;

Session Management.


После анализа рынка принято решение изменить стратегию.

Leviathan больше не должен быть "ещё одним агентом".

Теперь это инфраструктурная Companion Platform, которая:

усиливает существующие агентные системы;

может работать полностью автономно;

может использовать любого AI Runtime;

не зависит от конкретной модели;

не зависит от конкретного провайдера;

не зависит от конкретного агентного фреймворка.


При этом локальный агент остаётся частью проекта.

Он становится одним из Runtime системы.


---

ГЛАВНАЯ ЦЕЛЬ

Проанализируй текущее состояние проекта.

Определи, какие части архитектуры уже соответствуют новой стратегии.

Определи, какие необходимо переработать.

Определи, какие направления вообще стоит удалить.

После анализа интегрируй новую концепцию в архитектуру проекта.


---

ИССЛЕДОВАНИЕ

1. Product Pivot

Проанализируй эволюцию проекта.

Local AI Agent

↓

Agent Framework

↓

Agent Platform

↓

Companion Platform

↓

AI Infrastructure Layer

Определи:

Что изменилось?

Что стало главным продуктом?

Что теперь является ядром?


---

2. Core Architecture

Определи минимальное ядро Leviathan.

Что обязательно должно входить в Core.

Что должно стать отдельными сервисами.

Что должно стать подключаемыми модулями.

Раздели систему на:

Core

Extensions

Labs



---

3. Runtime Abstraction Layer

Исследуй создание универсального Runtime API.

Leviathan никогда не должен зависеть от конкретного AI Runtime.

Поддерживаемые Runtime:

Freebuff

Claude Code

OpenClaw

Hermes

Codex

локальный Runtime

OpenAI Compatible Runtime

будущие Runtime


Все Runtime должны подключаться через Adapter Layer.


---

4. Bootstrap System

Спроектируй отдельный Bootstrap Engine.

Его задача:

Развернуть полностью готовую AI-среду.

Исследуй:

Termux

proot-distro

Debian

Ubuntu

Node.js

Python

npm

pip

Git

Freebuff

зависимости

окружение

PATH

конфигурацию

автообновление

диагностику

восстановление


Bootstrap должен быть полностью идемпотентным.

Повторный запуск никогда не должен ломать систему.


---

5. Runtime Installer

Исследуй архитектуру установки Runtime.

Например:

Freebuff устанавливается автоматически из официального источника.

Leviathan не содержит его внутри себя.

Он лишь управляет установкой.

Определи аналогичную поддержку для:

OpenClaw

Hermes

локальный Runtime

пользовательских Runtime



---

6. Bootstrap Profiles

Исследуй профили установки.

Например:

Minimal

Developer

Offline

Cloud

Android

Research

Enterprise

Team


Каждый профиль определяет:

что устанавливать;

какие Runtime подключать;

какие сервисы запускать.



---

7. Provider Pool

Спроектируй поддержку нескольких AI-провайдеров.

Поддержка:

OpenAI

Anthropic

DeepSeek

Gemini

OpenRouter

Ollama

llama.cpp

локальные API

OpenAI-compatible API



---

8. Key Pool

Исследуй сервис управления API-ключами.

Поддержка:

нескольких ключей;

ротации;

приоритетов;

лимитов;

бюджетов;

автоматического Failover;

пользовательских правил.


Никакой магии.

Все политики определяет пользователь.


---

9. Model Pool

Поддержка нескольких моделей одновременно.

Исследуй архитектуру Model Registry.


---

10. Capability Registry

Пользователь выбирает не модель.

Он выбирает Capability.

Например:

Planning

Coding

Documentation

Review

Research

Translation

Testing

Architecture

Refactoring


Какая модель будет выполнять Capability определяется политикой пользователя.


---

11. Policy Engine

Исследуй архитектуру пользовательских политик.

Политики должны определять:

Runtime

Provider

Model

Workflow

Fallback

Cost Limits

Retry Rules

Scheduling

Queue

Context Strategy


Leviathan лишь исполняет политики.


---

12. Policy Packs

Создай концепцию переносимых пакетов.

Например:

Solo Developer

Startup

Enterprise

Research

Android Development

Book Writing

Video Production

Offline

Budget


Пользователи должны иметь возможность обмениваться ими.


---

13. Workflow Engine

Исследуй архитектуру Workflow.

Workflow должны работать:

без привязки к Runtime;

без привязки к модели;

без привязки к Provider.



---

14. Event Platform

Практически всё должно стать событием.

Исследуй:

Event Bus

Event Store

Replay

Timeline

Audit

Notifications

Decision Log

Project Pulse



---

15. Collaboration

Спроектируй Team Mode.

Поддержка:

нескольких пользователей;

нескольких Runtime;

нескольких агентов;

нескольких серверов;

нескольких проектов.



---

16. Presence

Исследуй систему присутствия.

Например:

Пользователь подключился.

Runtime начал работу.

Workflow завершён.

Review готов.

Agent пишет код.

Все события отображаются в реальном времени.


---

17. Knowledge Platform

Объедини:

Memory

RAG

Graph

Documentation

Decisions

Context

History


В единую Knowledge Platform.


---

18. Knowledge Graph

Graph должен содержать:

документы;

пользователей;

задачи;

Runtime;

Workflow;

события;

плагины;

решения;

Capability;

проекты.



---

19. Session Platform

Исследуй долговременное сохранение:

пользователей;

Runtime;

Workflow;

проектов;

состояний;

политики;

контекста.



---

20. Plugin SDK

Спроектируй SDK.

Чтобы сторонние разработчики могли создавать:

плагины;

сервисы;

интеграции;

Bridge;

Runtime Adapter;

Capability Provider.



---

21. Workflow SDK

Исследуй создание пользовательских Workflow.


---

22. Bridge Platform

Полностью переработай концепцию Bridge.

Bridge должен стать универсальным слоем интеграции между:

Runtime;

Agent Framework;

MCP;

API;

локальными сервисами;

внешними сервисами.


Исследуй возможность двусторонней (реверсивной) интеграции.


---

23. Runtime Doctor

Создай концепцию диагностической подсистемы.

Например:

проверка Runtime;

проверка PATH;

проверка Python;

проверка Node.js;

проверка зависимостей;

автоматическое восстановление.



---

24. UX Philosophy

Пользователь не должен знать:

MCP;

Adapter;

Runtime Layer;

Bridge;

Event Bus.


Он должен видеть простые действия:

Подключить Claude

Подключить Freebuff

Работать локально

Создать проект

Пригласить участника



---

25. Open Architecture Manifesto

Сформулируй инженерные принципы проекта.

Например:

Runtime Agnostic

Provider Agnostic

Model Agnostic

Plugin First

Deterministic First

Event Driven

Local First

Policy Driven

Offline Friendly

Collaboration Ready

Backward Compatible

API First

Modular by Design


Если предложишь лучшие принципы — замени существующие.


---

ОБЯЗАТЕЛЬНО

Каждую идею оцени по следующим критериям:

архитектурная ценность;

долгосрочная актуальность;

сложность реализации;

стоимость сопровождения;

влияние на UX;

влияние на производительность;

влияние на масштабируемость;

риски;

альтернативные решения.


Не бойся удалять идеи, если они противоречат общей философии проекта.


---

ФИНАЛЬНЫЕ АРТЕФАКТЫ

Подготовь полный пакет проектной документации:

VISION 3.0

PRODUCT MANIFESTO

ARCHITECTURE 3.0

CORE SPECIFICATION

BOOTSTRAP SPECIFICATION

RUNTIME ABSTRACTION SPECIFICATION

POLICY ENGINE SPECIFICATION

CAPABILITY SPECIFICATION

EVENT PLATFORM SPECIFICATION

KNOWLEDGE PLATFORM SPECIFICATION

BRIDGE PLATFORM SPECIFICATION

PLUGIN SDK SPECIFICATION

WORKFLOW SDK SPECIFICATION

INSTALLATION STRATEGY

PRODUCT ROADMAP (3–5 лет)

FEATURE MATRIX (Core / Extensions / Labs)

RISK REGISTER

OPEN QUESTIONS

ARCHITECTURAL DECISIONS (ADR)

IMPLEMENTATION ROADMAP (поэтапный, без разрушения текущей архитектуры)


ГЛАВНЫЙ ПРИНЦИП

Не проектируй очередного AI-агента.

Спроектируй открытую инфраструктурную платформу, которая:

помогает одиночным разработчикам и командам;

может работать автономно как локальный агент;

усиливает существующие AI-агенты, а не заменяет их;

легко интегрируется с новыми моделями и фреймворками;

остаётся модульной, расширяемой и независимой от конкретных технологий;

развивается эволюционно, сохраняя совместимость с уже реализованными компонентами проекта Leviathan.