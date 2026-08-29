# CURRENT_ARCHITECTURE.md — Фактическая архитектура Freebuff / Workspace OS

> **Версия:** v5.189.67
> **Статус:** FORENSIC FACT (только код, без интерпретации)

---

## 1. Слои системы

```
┌─────────────────────────────────────────────────┐
│ USER LAYER                                       │
│ CLI · Telegram Bot · MCP Server · REST API      │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│ ORCHESTRATION LAYER                              │
│ Orchestrator (FSM/DAG) · ContextManager · EventBus│
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│ DECISION LAYER                                   │
│ ScenarioIntelligence (discovery→eval→select)     │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│ FACTORY LAYER                                    │
│ FactoryRegistry → BaseFactory → ForgeFacade      │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│ FORGE LAYER                                      │
│ ForgePipeline (FORGE→CHECK→BUILD→TEST→DEPLOY→REPORT)│
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│ PERSISTENCE LAYER                                │
│ MemoryStore · KnowledgeEngine · ForgeRegistry    │
│ WorkspaceRegistry · DecisionHistoryStore         │
└─────────────────────────────────────────────────┘
```

## 2. Параллельные подсистемы

| Подсистема | Компоненты | Интеграция |
|------------|------------|------------|
| CoWork | PresenceEngine, CollaborationEngine, RoleEngine | SQLite (context.db), EventBus |
| Knowledge | KnowledgeEngine, GraphIndex, SemanticLayer, RAGEngine | SQLite (knowledge/index.db) |
| Plugin | PluginRegistry, BasePlugin, 3 plugins | EventBus, ToolRegistry |
| Policy | PolicyEngine, rules.py, conversational.py | RuntimeRegistry |
| Runtime | RuntimeRegistry, RuntimeCapabilityRegistry, AdapterRegistry | JSON storage |
| Observability | MetricsEngine, NotificationManager | EventBus |
| Bootstrap | BootstrapEngine, checker.py, doctor.py, installer.py | — |

## 3. Ключевые инварианты

| Инвариант | Где enforced | Описание |
|-----------|-------------|----------|
| §7.3: Scenario ≠ Forge direct call | forge_facade.py: `can_initiate()` gate | Pipeline-роли не вызывают ForgePipeline напрямую |
| B10/R-127: UNFORGED ≠ UNTESTED | forge_registry.py: `validate_schema()` | UNFORGED ⇒ last_run_at is None |
| B15: Workspace-Profile check | forge_registry.py: `_check_workspace_profile()` | Registry write проверяет workspace profile |
| Privacy: path ∈ ONE workspace | workspace_registry.py: PRIMARY KEY | PrivacyViolationError при нарушении |
| ANTI-6b: Closed vocabulary | blueprint_v3.py: `validate_override_vocabulary()` | Capability tokens ⊆ KNOWN_CAPABILITIES |
| CAN-16: Additive only | AGENTS.md §1 | Новый код не переписывает существующий |
