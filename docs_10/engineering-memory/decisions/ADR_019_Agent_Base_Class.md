# ADR-019: Agent base class + lifecycle — официальная сущность «Агент»

> **Статус:** Accepted (реализован в core_02/agent_base.py, v5.189.80)
> **Дата:** 2026-08-22
> **Связанные:** ARCHITECTURAL_BASELINE_V1.md §3 (AGENT — DOCUMENTED ONLY), ADR-013 (роли/executor), ADR-017 (Workspace), §7.3 (границы), CON-16 (additive),
> **Решение 108:** ARCHITECTURE_DECISION_108_V1.md §D (Agent/Role/Model/Capability) + TOP 10 #5; COMPETING_ABSTRACTIONS_MATRIX_V1.md §4 (три модели «исполнителя»).

## Context

Baseline (§3) фиксирует: **«AGENT как класс с lifecycle — DOCUMENTED ONLY»** — класса `Agent` в коде нет, роли stateless. Платформа знает:
- **роли** (Blueprint pipeline-роли 14-17, collab-роли 6 — два разных набора, оба называют себя «роли»);
- **агентоподобные мосты** — `AgentContextBridge` (scripts_01/), `AgentMesh` (distributed_agents.py), `role_executor.BaseRoleExecutor`;
- **модели** — `SmartRouter/ModelCatalog` (capability-роутинг) и `ModelGateway` (исполнение).

Отсутствует единая сущность, которая связывает: «кто я (роль/набор ролей) → какой model-capability мне нужен → какой runtime/tool у меня есть → какой у меня жизненный цикл (создан → работает → завершён)».

**Evidence-таблица «трёх исполнителей» (верифицировано кодом 2026-08-22, COMPETING_ABSTRACTIONS_MATRIX §4):**

| Представление | Файл:символ | Роль |
|---------------|-------------|------|
| `IAgent` (ABC-интерфейс) | `core_02/interfaces.py:50` (`:68 async run`) | контракт «кто исполняет» (LEVIATHAN-паттерн) |
| `AgentNode`/`AgentMesh` (mesh-слой) | `scripts_01/distributed_agents.py:111` (`:77 AgentNodeStatus`), `:249 AgentMesh` | сетевая сущность, статусы PENDING/ONLINE/BUSY/OFFLINE |
| `BaseRoleExecutor` (исполнитель роли) | `core_02/role_executor.py:49` (`:61 execute`, `:223 LlmRoleExecutor`, `:105 LisaExecutor`) | исполнение pipeline-роли в forge-контексте (ADR-016) |
| `STANDARD_ROLES` (collab-роли) | `scripts_01/roles.py:54` (6 ролей), `:395 get_collab_role` | права коллаборации (owner/editor/viewer) |

Три модели «исполнителя» (IAgent/AgentNode/BaseRoleExecutor) пересекаются по концепции «агент с capabilities» — это и есть ядро P1-пробела, которое закрывает ADR-019.

## Decision

Ввести **`Agent` base class** (аддитивно, в `core_02/agent_base.py`) — контракт-интерфейс, НЕ новая runtime-платформа (Forge не становится runtime; RFC §12 соблюдается):

```python
class Agent(ABC):
    """Единая сущность «Агент» (design-only контракт)."""

    agent_id: str                          # uuid / slug
    role_ids: tuple[str, ...***REMOVED***              # какие роли исполняет (pipeline/collab)
    capabilities: frozenset[str***REMOVED***           # закрытое подмножество KNOWN_CAPABILITIES (ANTI-6b)
    model_capability: str | None           # для SmartRouter/ModelCatalog routing
    runtime: str = "local"                 # local | distributed (AgentMesh)

    lifecycle: AgentLifecycle              # CREATED → ACTIVE → PAUSED → DONE/FAILED

    @abstractmethod
    def execute(self, project: Project, task: Any, *, event_bus=None) -> AgentResult: ...

    # наследуемые сервисы (ленивые, fail-safe):
    def route_model(self) -> str            # capability → SmartRouter.route → model_id
    def run_forge(self, project, role_ids)  # делегирует ForgeFacade.run_chain (единственный мост §7.3)
```

**Жизненный цикл** (forward-only, как opportunity_engine):
`CREATED → ACTIVE → PAUSED ↔ ACTIVE → DONE | FAILED` (FAILED → ACTIVE retry). Персистенс — аддитивный, в существующий `context.db` (таблица `agents`, по образцу `workspaces`).

**Правила:**
1. Agent — **композиция ролей**, не замена им (pipeline-роли остаются корпусом данных в blueprint_v3).
2. Agent использует **capability-роутинг** (не выбирает модель вручную) — закрытый словарь.
3. Agent НЕ вызывает ForgePipeline напрямую — только `ForgeFacade` (§7.3 grep-инвариант).
4. `AgentContextBridge`/`AgentMesh` остаются; `Agent` — официальный интерфейс, мосты со временем адаптируются (additive).
5. Fail-safe: lazy-imports, dict-результаты, никогда не крашит владельца (ADR-016 паттерн).

## Alternatives

- **(а) Считать агентов ненужными** (роли + мосты достаточно) — отвергнуто: baseline §3 зафиксировал отсутствие Agent-абстракции как P1-пробел; без единого lifecycle нельзя ответить «кто сейчас работает и в каком состоянии».
- **(б) Слить collab-роли (roles.py) и pipeline-роли (blueprint_v3) в один набор** — отвергнуто: разные слои (коллаборация vs производство); слияние ломает BC; Agent-слой поверх обоих — правильная граница.
- **(в) Agent как runtime-оркестратор (исполняет задачи автоматически)** — отвергнуто: Forge — не runtime-платформа (RFC §12); Agent — контракт/фасад, исполнение по-прежнему через явные вызовы (не молча, §7.3).
- **(г) `core_02/agent_base.py` + lifecycle + композиция ролей** — **ВЫБРАНО**: аддитивно, сохраняет layering, закрывает P1-пробел baseline §3.

## Trade-offs

- **Выигрываем:** единая сущность «кто работает» с lifecycle; явная связь роль→capability→модель; наблюдаемость (event_bus); готовый каркас для multi-agent (AgentMesh уже есть).
- **Теряем:** ещё один слой (митигировано: контракт-минимум, без дублирования сервисов); риск переусложнения (митигировано: никакого авто-исполнения, только явные вызовы).

## Consequences

- **Реализация (отдельный заход):** `core_02/agent_base.py` (контракт + lifecycle + `route_model`/`run_forge` делегаты) + таблица `agents` в `context.db` + 6-8 hermetic тестов (lifecycle graph, capability-валидация, fail-safe, run_forge-делегат). Никакого автоматического исполнения. Гарантия: `run_forge` делегирует ровно `ForgeFacade.run_chain` (grep-инвариант §7.3 — ни Scenario, ни Agent не вызывают ForgePipeline напрямую).
- **Документация:** baseline §3 «AGENT — DOCUMENTED ONLY» → «design зафиксирован (ADR-019)»; ARCHITECTURE_DECISION_108 §D/TOP #5 закрывается этим ADR.
- **Реестры:** DECISIONS.md + DOCUMENT_REGISTRY.md + CHANGELOG.
