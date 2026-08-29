MANIFEST

Workspace OS

Что мы строим

Workspace OS — это интеллектуальная операционная система для создания, развития и сопровождения проектов любой сложности.

Её задача — не написать код и не ответить на вопрос.

Её задача — организовать полный жизненный цикл создания интеллектуального продукта.

Workspace OS предоставляет человеку или команде среду, внутри которой рождаются идеи, принимаются архитектурные решения, создаются документы, проектируется система, пишется код, проверяется качество, ведётся память проекта и обеспечивается его дальнейшая эволюция.

Workspace OS рассматривает проект как живую систему, а не как набор файлов.


---

Главная идея

Большинство современных AI-инструментов умеют выполнять отдельные задачи.

Например:

написать функцию;

придумать текст;

нарисовать изображение;

найти ошибку.


Но практически ни один инструмент не умеет сопровождать проект целиком.

Workspace OS создаётся именно для этого.

Её задача — превратить хаотичный процесс разработки в управляемое производство интеллектуальных продуктов.


---

Что такое Project

В понимании Workspace OS проект — это самостоятельная система знаний.

Проект состоит не только из кода.

Он включает:

идеи;

исследования;

требования;

архитектуру;

документацию;

память;

решения;

знания;

артефакты;

код;

тесты;

историю развития.


Все эти элементы рассматриваются как части одной экосистемы.


---

Основные сущности Workspace OS

Workspace

Наивысший уровень организации.

Workspace принадлежит человеку, компании или команде.

Он содержит множество проектов.


---

Project

Изолированная среда разработки конкретного продукта.

Каждый проект имеет:

собственую память;

документацию;

архитектуру;

Factory;

процессы;

историю решений;

знания.



---

Knowledge

Любой накопленный опыт проекта.

Это могут быть:

RFC;

ADR;

Lessons;

Policies;

Patterns;

документация;

исследования;

заметки.


Knowledge никогда не теряется.

Он становится частью Organizational Memory.


---

Artifact

Любой результат работы системы.

Например:

документ;

код;

схема;

изображение;

видео;

архитектурная модель;

база данных.



---

Factory

Factory — это производственная подсистема Workspace OS.

Именно Factory превращает идею в готовый продукт.

Factory ничего не знает о конкретном проекте.

Она знает только процесс производства.

Именно поэтому Factory универсальна.


---

Factory состоит из специализированных Forge

Каждый Forge отвечает только за один этап производства.

Например

Idea Forge

формирует идеи

↓

Research Forge

собирает знания

↓

Architecture Forge

строит архитектуру

↓

Prompt Forge

создаёт интеллектуальные инструкции

↓

Code Forge

генерирует программную систему

↓

Test Forge

проверяет корректность

↓

Documentation Forge

создаёт документацию

↓

Release Forge

готовит выпуск продукта

↓

Evolution Forge

сопровождает продукт после выхода

Каждый Forge является независимой производственной линией.


---

Что такое Forge

Forge — это специализированная фабрика внутри Factory.

Каждый Forge отвечает за производство одного типа интеллектуального артефакта.

Например

Architecture Forge производит архитектурные решения.

Prompt Forge производит интеллектуальные инструкции.

Code Forge производит программный код.

Video Forge производит видеоролики.

Book Forge производит книги.

Forge ничего не знает о других Forge.

Он умеет делать только своё дело.


---

Внутреннее устройство Forge

Каждый Forge состоит из одного или нескольких Engine.

Например

Architecture Forge

содержит

Architecture Review Engine

Architecture Design Engine

Architecture Governance Engine

Architecture Evolution Engine

Каждый Engine отвечает за отдельный производственный процесс.


---

Что такое Engine

Engine — это исполнитель производственной операции.

Именно Engine организует последовательность действий.

Он ничего не знает о реализации отдельных операций.

Он знает только производственный процесс.

Например

Architecture Review Engine

последовательно выполняет

Problem Validation

↓

Context Analysis

↓

Dependency Analysis

↓

Risk Analysis

↓

Alternative Search

↓

Principle Check

↓

Verdict Generation

↓

Report Generation

Engine можно представить как конвейер.


---

Что такое Module

Каждый Engine состоит из независимых модулей.

Например

Review Engine

включает

Problem Validator

Context Analyzer

Dependency Analyzer

Risk Analyzer

Alternative Generator

Principle Checker

Debt Predictor

Verdict Generator

Report Generator


Каждый модуль отвечает за одну конкретную задачу.

Модули ничего не знают друг о друге.

Их можно заменять независимо.


---

Что такое Tool

Tool — это конкретный исполнитель.

Именно Tool выполняет реальную работу.

Например

Dependency Analyzer может использовать:

Graph Search Tool

Semantic Search Tool

Knowledge Search Tool

RFC Parser

Policy Checker

Organizational Memory API

LLM Adapter


Таким образом

Module
    ↓
использует
    ↓
Tool

Tool никогда не принимает архитектурных решений.

Он только предоставляет результат своей операции.


---

Что такое Skill

Skill — это готовая технология выполнения конкретной операции.

Например

RFC Parsing Skill

Architecture Critique Skill

Requirements Extraction Skill

Knowledge Classification Skill

Skill может использоваться разными Tool.

Skill описывает, КАК выполнять задачу.


---

Что такое Prompt

Prompt — это инструкция для интеллектуальной модели.

Prompt является лишь одним из инструментов внутри Skill.

То есть

Tool
    ↓
использует
Skill
    ↓
которая может использовать
Prompt

Следовательно Prompt — это самый нижний уровень интеллектуальной системы.

Он давно перестаёт быть центром архитектуры.


---

Полная иерархия

Workspace OS
│
├── Workspace
│   ├── Project A
│   ├── Project B
│   └── Project C
│
└── Factory
    │
    ├── Architecture Forge
    │   │
    │   ├── Review Engine
    │   │   ├── Problem Validator (Module)
    │   │   │   ├── RFC Parser (Tool)
    │   │   │   ├── Knowledge Search (Tool)
    │   │   │   └── Validation Skill
    │   │   │        └── Prompt
    │   │   │
    │   │   ├── Context Analyzer (Module)
    │   │   ├── Dependency Analyzer (Module)
    │   │   ├── Risk Analyzer (Module)
    │   │   ├── Alternative Generator (Module)
    │   │   ├── Principle Checker (Module)
    │   │   ├── Debt Predictor (Module)
    │   │   ├── Verdict Generator (Module)
    │   │   └── Report Generator (Module)
    │   │
    │   ├── Governance Engine
    │   ├── Design Engine
    │   └── Evolution Engine
    │
    ├── Prompt Forge
    ├── Code Forge
    ├── Documentation Forge
    ├── Test Forge
    ├── Release Forge
    ├── Video Forge
    └── Book Forge


---

Именно такая модель, на мой взгляд, делает архитектуру очень чистой. Она отвечает на главный вопрос: где заканчивается промпт и начинается система.

