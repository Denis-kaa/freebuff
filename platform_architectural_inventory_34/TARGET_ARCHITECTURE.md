# TARGET ARCHITECTURE + MIGRATION + REFACTORING ROADMAP — promt107 §22-24

> Разделено: A. CONFIRMED CURRENT / B. PROPOSED TARGET / C. MIGRATION BRIDGE.
> Ничего не реализовано — это план на утверждение (promt107 §28).

## A. CONFIRMED CURRENT (что уже работает)

- Forge-слой: Workspace→Project→ForgePipeline→ForgeRegistry→ForgeFacade (полный, тестируемый).
- Capability routing: SmartRouter/ModelCatalog (data-driven выбор модели).
- Scenario registry (role corpus discovery).
- Factory registry (декларативные passports + select_forge).
- ScenarioIntelligence (decision/coordination).
- Privacy isolation (WorkspaceRegistry.assert_path_privacy).

## B. PROPOSED TARGET (после утверждения)

1. **Единая Workspace модель** — workspace.py (YAML) и workspace_registry.py (SQLite)
   синхронизируются через один source-of-truth (рекомендация: registry = source, YAML = cache/export).
2. **Явный Factory→Forge execution контракт** — `BaseFactory.execute(opportunity) →
   FactoryRegistry.select_forge → ForgeFacade.initiate_forge` (замкнуть Path B).
3. **Agent base class** — ввести `Agent` (identity + lifecycle + scoped memory), поверх которого
   pipeline-роли и collab-роли — проекции, НЕ дубли.
4. **AGENT ROLE ≠ PROJECT ROLE** — разделить: `RoleEngine` (agent: что умеет) + новая
   `ProjectRole` (Owner/PM/Contributor/Reviewer/Observer: место в проекте).
5. **Integration/Connector/Adapter Layer** — вынести TG/MCP/phone/remote_sync за границу ядра;
   connector = adapter, НЕ subsystem (promt107 §13).
6. **Единый Tool-контракт** — ToolRegistry как единственный источник tools; MCP = транспорт.
7. **Memory/Knownledge source-of-truth** — консолидировать 4 движка под единый интерфейс.

## C. MIGRATION BRIDGE (каждый шаг: small, reversible, testable, observable)

| Текущее | Целевое | Миграционный шаг |
|---------|---------|------------------|
| workspace.py YAML + registry SQLite | единая модель | add adapter: registry = source, YAML load → sync check |
| select_forge без execution | Factory→Forge контракт | add `BaseFactory.execute → ForgeFacade` (additive, не трогая старые CLI) |
| нет Agent-класса | Agent base | add `core_02/agent.py` (additive), проекции ролей поверх |
| RoleEngine = agent+project смешано | раздельно | add `ProjectRole` module; RoleEngine.get_collab_role → migrate |
| мосты вшиты в ядро | integration layer | add `integrations/` adapter-обёртки, ядро вызывает через interface |
| ToolRegistry vs MCP tools | единый tool-контракт | MCP server читает ToolRegistry (adapter) |

## Implementation Priority

- **P0 (architectural blockers):** дублирующие Workspace/Project модели (два source-of-truth);
  отсутствие sandbox/tool-ACL для внешних мостов.
- **P1 (missing contracts):** Factory→Forge execution; Agent base; Integration adapter boundary.
- **P2 (duplicated responsibilities):** task ×2, tool ×2, memory ×4.
- **P3 (repository cleanup):** исторические каталоги, trash, eval-пакеты.
- **P4 (enhancements):** семантические теги (только после P0-P2), метрики, UX.

## Risks

1. **Big-bang refactor** — запрещён (Additive Architecture). Каждый шаг отдельно.
2. **Унификация registry** — риск потерять owner-file/namespace разграничение (B-Rule 4/5).
3. **Agent base class** — риск сломать BC pipeline-роли (ANTI-7b: shadowing методов).
4. **Integration layer** — риск разорвать работающие TG-цепочки (e2e_promt47, remote_sync).
5. **Memory consolidation** — риск потери данных (4 SQLite/файловых движка).

## MUST NOT YET IMPLEMENT (promt107 §28)

До утверждения CURRENT REALITY MAP + RESPONSIBILITY MAP + CONTRACT GRAPH + TARGET ARCHITECTURE:
код НЕ менять, НЕ рефакторить, НЕ переименовывать, НЕ создавать production-модули.
