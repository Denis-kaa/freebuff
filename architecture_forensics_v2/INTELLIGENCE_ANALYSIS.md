# INTELLIGENCE_ANALYSIS.md — Intelligence / Brain слой

> **Статус:** FORENSIC FACT + INFERENCE

---

## 1. Есть ли отдельное понятие Intelligence / Brain?

**FACT:** В коде **нет** класса `Intelligence`, `Brain`, `Companion`, `Advisor`. 

**INFERENCE:** "Intelligence" — это **emergent property** нескольких компонентов, не отдельный слой.

## 2. Компоненты, формирующие "Intelligence"

| Компонент | Файл | Роль в "Intelligence" |
|-----------|------|----------------------|
| Orchestrator | scripts_01/orchestrator.py | Планирование (DefaultPlanner), DAG execution, контекст-проверка |
| ScenarioIntelligence | scripts_01/scenario_intelligence.py | Decision: discovery→evaluation→ranking→selection |
| ContextManager | scripts_01/context_manager.py | Session persistence, checkpoints, auto-summarization |
| MemoryEngine | scripts_01/memory_engine.py | Multi-level memory (WORKING/EPISODIC/SEMANTIC) |
| KnowledgeEngine | scripts_01/knowledge_engine.py | FTS + TF-IDF + graph search |
| ModelGateway | scripts_01/model_gateway.py | 6 LLM providers, capability routing, fallback |
| SmartRouter | core_02/router.py | Capability→model routing |
| RAGEngine | scripts_01/rag_engine.py | Retrieval-augmented generation |
| SemanticLayer | core_02/semantic_layer.py | Semantic search |

## 3. Функции "Intelligence" и где они реализованы

| Функция | Реализовано? | Где |
|---------|--------------|-----|
| Reasoning | ⚠️ | ModelGateway (LLM) |
| Planning | ✅ | Orchestrator.DefaultPlanner |
| Decision making | ✅ | ScenarioIntelligence |
| Context | ✅ | ContextManager |
| Project understanding | ⚠️ | KnowledgeEngine + WorkspaceRegistry |
| Recommendation | ⚠️ | ScenarioIntelligence (scenario candidates) |
| Orchestration | ✅ | Orchestrator |
| Memory | ✅ | MemoryEngine + MemoryStore |
| Knowledge | ✅ | KnowledgeEngine |
| Learning | ⚠️ | LearningLoop (в _accumulate) |
| Feedback | ⚠️ | ScenarioIntelligence.feedback() |
| Agent collaboration | ❌ | Нет A2A communication |
| Multi-agent interaction | ❌ | Нет |
| Proactive discussion | ❌ | Нет |

## 4. Companion / AI Brain — есть ли?

**FACT:** Концепция "AI companion / товарищ" **частично реализована** через:
- `ScenarioIntelligence` — задаёт вопросы "which approach fits?" и предлагает кандидатов
- `Orchestrator.check_existing_context()` — проверяет Knowledge на дубли
- `ContextManager` — помнит контекст сессии, создаёт checkpoints

**INFERENCE:** ScenarioIntelligence — это **reactive decision layer**, а не **proactive companion**. Он не:
- инициирует обсуждение
- критикует решения пользователя
- предлагает альтернативы без запроса
- помнит долгосрочные предпочтения пользователя

## 5. Кто принимает решения?

**FACT:** Решения принимаются в нескольких местах:
1. **ScenarioIntelligence.select()** — выбор сценария (weighted: relevance 0.35, capability 0.25, history 0.20, feasibility 0.20)
2. **FactoryRegistry.select_forge()** — выбор (factory, forge) по capability (status-priority)
3. **SmartRouter.route()** — выбор модели по capabilities
4. **PolicyEngine.resolve()** — user-choice override (правило 11)
5. **ForgeFacade.run_chain()** — выбор ролей (PIPELINE_CHAIN)

**INFERENCE:** Нет единого "мозга", принимающего все решения. Решения распределены по слоям.

## 6. Кто хранит контекст?

**FACT:** Несколько хранилищ:
- ContextManager (sessions, checkpoints)
- MemoryEngine (WORKING/EPISODIC/SEMANTIC)
- KnowledgeEngine (FTS index)
- DecisionHistoryStore (scenario decisions)
- OpportunityStore (opportunities)
- WhimStore (whims)

**INFERENCE:** Контекст **распределён**, нет единого query для "полное состояние проекта".

## 7. Рекомендации (INFERENCE)

1. Выделить единый `Intelligence` module, объединяющий ScenarioIntelligence + Orchestrator + ContextManager
2. Добавить proactive advisor (инициирует discussion, критикует, предлагает)
3. Единый context query API (project state → context → knowledge → memory → observation → reasoning → decision)
4. Связать LearningLoop с ScenarioIntelligence для полного feedback loop
