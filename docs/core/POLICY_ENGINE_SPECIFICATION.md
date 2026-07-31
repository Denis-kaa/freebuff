# POLICY ENGINE SPECIFICATION — Пользовательские политики

> **Версия:** 1.0.0  
> **Дата:** 2026-07-29  
> **Статус:** Спецификация (к реализации)  
> **Основание:** [VISION_3.0.md***REMOVED***(../vision/VISION_3.0.md), [ARCHITECTURE_3.0.md***REMOVED***(ARCHITECTURE_3.0.md), [promt14.md***REMOVED***(../../pompts/promt14.md) (концепции #10–12)  

---

## Содержание

1. [Executive Summary***REMOVED***(#1-executive-summary)
2. [Архитектура***REMOVED***(#2-архитектура)
3. [Policy Store***REMOVED***(#3-policy-store)
4. [Policy Executor***REMOVED***(#4-policy-executor)
5. [Policy Format***REMOVED***(#5-policy-format)
6. [Policy Packs***REMOVED***(#6-policy-packs)
7. [Интеграция с архитектурой***REMOVED***(#7-интеграция-с-архитектурой)
8. [MCP инструменты***REMOVED***(#8-mcp-инструменты)
9. [CLI для пользователя***REMOVED***(#9-cli-для-пользователя)
10. [Тестирование***REMOVED***(#10-тестирование)
11. [Реализация***REMOVED***(#11-реализация)
12. [Критерии готовности***REMOVED***(#12-критерии-готовности)

---

## 1. Executive Summary

**Policy Engine** — это компонент Core, который определяет поведение Buffy
на основе пользовательских политик.

**Ключевой принцип:** Buffy лишь исполняет политики пользователя.
Все решения — какой Runtime, провайдер, модель использовать — определяются политиками.

**Что делает Policy Engine:**
- Хранит политики пользователя в Policy Store (SQLite)
- Исполняет политики при каждом запросе (Policy Executor)
- Выбирает Runtime/Provider/Model по capability
- Управляет fallback, cost limits, retry rules
- Поддерживает Policy Packs — переносимые пакеты политик
- Публикует события в Event Bus (`policy.*`)

**🟡 Future extensions (из promt14.md #11):**
- **Scheduling** — отложенные задачи, выполнение по расписанию
- **Queue** — порядок обработки (FIFO, priority queue по важности)
- **Context Strategy** — стратегия сбора контекста (full, summary, diff-based)

Эти три возможности будут добавлены после стабилизации Core Policy Engine.

```
Пользователь → Capability → Policy Engine → Runtime + Provider + Model
                                                   │
                                                   ▼
                                           Runtime Abstraction Layer
```

---

## 2. Архитектура

### 2.1 Общая схема

```
┌─────────────────────────────────────────────────────────────────┐
│                         POLICY ENGINE                            │
│                                                                  │
│  ┌──────────────────────┐      ┌────────────────────────────┐  │
│  │    Policy Store       │      │     Policy Executor        │  │
│  │                      │      │                            │  │
│  │  • SQLite хранилище  │      │  • Выбор Runtime           │  │
│  │  • YAML/JSON импорт  │      │  • Выбор Provider          │  │
│  │  • Policy Packs      │      │  • Выбор Model             │  │
│  │  • History/audit     │      │  • Capability routing      │  │
│  └──────────┬───────────┘      │  • Fallback chain          │  │
│             │                  │  • Cost limits             │  │
│             │                  │  • Retry rules             │  │
│             │                  └────────────┬───────────────┘  │
│             │                               │                  │
│             ▼                               ▼                  │
│  ┌──────────────────────┐      ┌────────────────────────────┐  │
│  │  Capability Registry │      │     Policy Validator       │  │
│  │  (см. CAPABILITY_    │      │                            │  │
│  │   SPECIFICATION.md)  │      │  • Валидация YAML          │  │
│  │                      │      │  • Проверка reference      │  │
│  │  • capability→Runtime│      │  • Sanity check            │  │
│  │  • capability→Model  │      │  • Conflict detection      │  │
│  │  • confidence scoring│      └────────────────────────────┘  │
│  └──────────────────────┘                                       │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                Policy Pack Manager                        │  │
│  │                                                           │  │
│  │  • install/remove/list packs                              │  │
│  │  • resolve conflicts между packs                          │  │
│  │  • merge policies from multiple sources                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │                        │                       │
         ▼                        ▼                       ▼
   ┌────────────┐          ┌────────────┐          ┌────────────┐
   │ Runtime    │          │ Model      │          │ Event Bus  │
   │ Abstraction│          │ Gateway    │          │ policy.*   │
   └────────────┘          └────────────┘          └────────────┘
```

### 2.2 Абстракции

```
┌──────────────────────────────┐
│    Policy                    │  ← Правило: что, когда, как делать
├──────────────────────────────┤
│    PolicyEvaluationContext   │  ← Контекст для оценки политики
├──────────────────────────────┤
│    PolicyResult              │  ← Результат: выбранный Runtime/Provider/Model
├──────────────────────────────┤
│    PolicyPack                │  ← Набор политик для конкретного сценария
├──────────────────────────────┤
│    PolicyConflict            │  ← Конфликт между политиками
└──────────────────────────────┘
```

### 2.3 Жизненный цикл политики

```
СОЗДАНА → ПРОВЕРЕНА → АКТИВНА → ИСПОЛЬЗУЕТСЯ → ОБНОВЛЕНА → ПРОВЕРЕНА → АКТИВНА
              │                                                      │
              ▼                                                      ▼
         ОШИБКА ВАЛИДАЦИИ                                        АРХИВИРОВАНА
              │
              ▼
         НЕ АКТИВНА (требует исправления)
```

### 2.4 Место в архитектуре

Policy Engine находится в Core:

```
User Request
    │
    ▼
Orchestrator / MCP Server
    │
    ▼
Policy Engine ← Capability Registry
    │
    ├──→ Runtime Abstraction Layer (выбор Runtime)
    ├──→ ModelGateway (выбор провайдера и модели)
    ├──→ Workflow Engine (выбор последовательности шагов)
    └──→ Event Bus (публикация решения)
```

---

## 3. Policy Store

### 3.1 PolicyStore

```python
class PolicyStore:
    """Хранилище пользовательских политик.

    SQLite-backed с возможностью импорта/экспорта YAML.
    """

    def __init__(self, db_path: Optional[Path***REMOVED*** = None):
        self._db_path = db_path or Path("data/policies.db")

    def get_policy(self, name: str) -> Optional[Policy***REMOVED***:
        """Получить политику по имени."""
        ...

    def set_policy(self, policy: Policy) -> None:
        """Сохранить или обновить политику."""
        ...

    def delete_policy(self, name: str) -> bool:
        """Удалить политику."""
        ...

    def list_policies(self, tag: Optional[str***REMOVED*** = None) -> List[Policy***REMOVED***:
        """Список политик, опционально фильтр по тегу."""
        ...

    def get_active_policy(self, context: PolicyEvaluationContext) -> Policy:
        """Получить активную политику для данного контекста."""
        ...

    def import_yaml(self, path: Path) -> int:
        """Импортировать политики из YAML файла."""
        ...

    def export_yaml(self, path: Path) -> None:
        """Экспортировать все политики в YAML файл."""
        ...
```

### 3.2 Schema SQLite

```sql
CREATE TABLE policies (
    name            TEXT PRIMARY KEY,
    description     TEXT DEFAULT '',
    priority        INTEGER DEFAULT 0,     -- выше = важнее
    enabled         INTEGER DEFAULT 1,
    tags            TEXT DEFAULT '',        -- comma-separated

    -- Условия применения
    project         TEXT DEFAULT '',        -- для конкретного проекта
    capability      TEXT DEFAULT '',        -- для конкретной capability
    runtime         TEXT DEFAULT '',        -- для конкретного Runtime
    context_pattern TEXT DEFAULT '',        -- regex для контекста запроса

    -- Решение
    decision_runtime    TEXT DEFAULT '',
    decision_provider   TEXT DEFAULT '',
    decision_model      TEXT DEFAULT '',
    fallback_strategy   TEXT DEFAULT 'next-available',
    max_retries         INTEGER DEFAULT 3,
    cost_limit_daily    REAL DEFAULT 0.0,
    cost_limit_per_task REAL DEFAULT 0.0,

    -- Мета
    source          TEXT DEFAULT 'user',   -- 'user', 'pack', 'system'
    pack_name       TEXT DEFAULT '',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    version         INTEGER DEFAULT 1
);

CREATE TABLE policy_audit (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    policy_name     TEXT NOT NULL,
    action          TEXT NOT NULL,          -- created, updated, deleted, applied
    context         TEXT DEFAULT '',
    result          TEXT DEFAULT '',
    timestamp       TEXT NOT NULL
);

CREATE TABLE policy_packs (
    name            TEXT PRIMARY KEY,
    display_name    TEXT DEFAULT '',
    description     TEXT DEFAULT '',
    author          TEXT DEFAULT '',
    version         TEXT DEFAULT '1.0.0',
    policies        TEXT DEFAULT '[***REMOVED***',     -- JSON array
    installed_at    TEXT NOT NULL,
    source_url      TEXT DEFAULT '',
    checksum        TEXT DEFAULT ''
);
```

### 3.3 Policy Evaluation Context

```python
@dataclass
class PolicyEvaluationContext:
    """Контекст для оценки политики."""

    # Запрос
    capability: str                     # "coding", "review", "planning"
    project: str                        # Имя проекта
    task_type: str                      # "generate", "review", "research"
    complexity: str = "medium"          # "low", "medium", "high"

    # Пользователь
    user_id: Optional[str***REMOVED*** = None       # Для team mode
    team: Optional[str***REMOVED*** = None

    # Дополнительно
    preferred_runtime: Optional[str***REMOVED*** = None  # Явный запрос пользователя
    preferred_model: Optional[str***REMOVED*** = None
    max_cost: Optional[float***REMOVED*** = None    # Бюджет на задачу
    offline_mode: bool = False
```

---

## 4. Policy Executor

### 4.1 PolicyExecutor

```python
class PolicyExecutor:
    """Исполнитель политик.

    Принимает контекст → оценивает политики → возвращает решение.
    """

    def __init__(self, store: PolicyStore, capability_registry: CapabilityRegistry):
        self._store = store
        self._capability_registry = capability_registry

    def evaluate(
        self,
        context: PolicyEvaluationContext,
    ) -> PolicyResult:
        """Оценить политики для данного контекста и вернуть решение."""
        ...

    def evaluate_with_fallback(
        self,
        context: PolicyEvaluationContext,
    ) -> PolicyResult:
        """Оценить с fallback — если Runtime недоступен, выбрать следующий."""
        ...

    def _resolve_runtime(self, context: PolicyEvaluationContext) -> str:
        """Выбрать Runtime для данной capability."""
        ...

    def _resolve_provider(self, context: PolicyEvaluationContext, runtime: str) -> str:
        """Выбрать провайдера для Runtime."""
        ...

    def _resolve_model(self, context: PolicyEvaluationContext, runtime: str, provider: str) -> str:
        """Выбрать модель для Runtime + Provider."""
        ...

    def _check_cost_limits(self, context: PolicyEvaluationContext, decision: PolicyResult) -> bool:
        """Проверить, не превышает ли решение лимиты стоимости."""
        ...
```

### 4.2 PolicyResult

```python
@dataclass
class PolicyResult:
    """Результат оценки политики."""

    # Решение
    runtime: str                        # "freebuff", "claude-code"
    provider: str                       # "deepseek", "anthropic", "openai"
    model: str                          # "deepseek-v4-flash", "claude-3.5-sonnet"

    # Мета
    policy_name: str                    # Какая политика была применена
    policy_source: str                  # "user", "pack", "system"
    confidence: float = 1.0

    # Fallback
    fallback_used: bool = False
    fallback_chain: List[str***REMOVED*** = field(default_factory=list)

    # Cost
    estimated_cost: float = 0.0
    cost_limit_daily: float = 0.0
    cost_limit_per_task: float = 0.0
    cost_exceeded: bool = False

    # Дополнительно
    resolved_capability: Optional[str***REMOVED*** = None
    capabilities_considered: List[str***REMOVED*** = field(default_factory=list)
    alternatives: List[Dict[str, str***REMOVED******REMOVED*** = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any***REMOVED***:
        return asdict(self)
```

### 4.3 Алгоритм выполнения

```
evaluate(context):
  1. Собрать все активные политики, подходящие под context
  2. Отсортировать по priority (desc)
  3. Для каждой политики:
     a. Проверить условия (project, capability, context_pattern)
     b. Если условия совпадают → применить политику
     c. Проверить cost_limits
     d. Если лимиты превышены → искать следующую политику
  4. Если ни одна политика не подошла → использовать default_policy
  5. Если default_policy не задана → system_policy (хардкод)
  6. Вернуть PolicyResult

evaluate_with_fallback(context):
  1. result = evaluate(context)
  2. Проверить доступность выбранного Runtime
     a. Если доступен → вернуть result
     b. Если недоступен → найти следующий Runtime в fallback_chain
  3. Повторять шаг 2 пока не найдётся доступный Runtime
  4. Если все Runtime недоступны → вернуть error
```

### 4.4 Priority разрешения конфликтов

Когда несколько политик подходят под контекст, применяется следующее:

| Критерий | Вес | Пример |
|----------|-----|--------|
| Явный запрос пользователя (preferred_runtime) | 100 | `--runtime claude-code` |
| Специфичная для проекта | 50 | `project: my-app` |
| Специфичная для capability | 30 | `capability: review` |
| Общая политика (global) | 10 | без project и capability |
| System default | 0 | встроенная политика |

---

## 5. Policy Format

### 5.1 YAML формат

```yaml
# ~/.config/buffy/policies.yaml

# Политика для кодинга
- name: coding-default
  description: "Default policy for coding tasks"
  priority: 10
  enabled: true
  tags: ["coding", "default"***REMOVED***

  # Условия применения
  project: "*"                     # все проекты
  capability: coding
  context_pattern: ""

  # Решение
  runtime: claude-code
  provider: auto                   # auto = из провайдера по умолчанию
  model: auto                      # auto = из capability registry

  fallback:
    strategy: next-available       # next-available, ordered, random
    order: [claude-code, freebuff, openclaw***REMOVED***
    max_retries: 3

  cost:
    daily: 5.00
    per_task: 0.50


# Политика для ревью
- name: review-default
  description: "Code review policy"
  priority: 10
  tags: ["review"***REMOVED***

  capability: review
  runtime: claude-code
  provider: anthropic
  model: claude-3.5-sonnet

  fallback:
    strategy: next-available
    order: [freebuff***REMOVED***


# Политика для research (spec для openclaw)
- name: research-default
  description: "Research and web search"
  priority: 10
  tags: ["research"***REMOVED***

  capability: research
  runtime: openclaw

  fallback:
    strategy: next-available
    order: [freebuff***REMOVED***


# Политика для планирования (spec для freebuff)
- name: planning-default
  description: "Task planning and architecture"
  priority: 10
  tags: ["planning"***REMOVED***

  capability: planning
  runtime: freebuff

  fallback:
    strategy: ordered
    order: [freebuff, claude-code***REMOVED***


# Политика для specific проекта
- name: my-app-review
  description: "Strict review policy for my-app"
  priority: 50                    # выше, чем review-default
  project: my-app
  capability: review

  runtime: claude-code
  provider: anthropic
  model: claude-opus-4.0          # spec модель для важного проекта

  fallback:
    strategy: ordered
    order: [claude-code, freebuff***REMOVED***

  cost:
    per_task: 2.00                # можно дороже для важного проекта
```

### 5.2 Default Policy (system)

```yaml
# Встроенная политика (hardcoded в PolicyEngine)
- name: system-default
  description: "System default policy"
  priority: 0

  runtime: freebuff
  provider: auto
  model: auto

  fallback:
    strategy: next-available
    max_retries: 2
```

### 5.3 Policy Validation

```python
class PolicyValidator:
    """Валидация политик перед сохранением."""

    VALID_RUNTIMES = ["freebuff", "claude-code", "openclaw", "hermes", "gpt-4o"***REMOVED***
    VALID_CAPABILITIES = ["coding", "review", "planning", "research",
                          "documentation", "testing", "refactoring", "translation"***REMOVED***
    VALID_STRATEGIES = ["next-available", "ordered", "random"***REMOVED***
    VALID_PROJECT_PATTERN = r'^[a-zA-Z0-9_-***REMOVED***+|\*$'

    def validate(self, policy: Policy) -> List[str***REMOVED***:
        """Валидация политики. Возвращает список ошибок."""
        errors = [***REMOVED***

        if not policy.name:
            errors.append("Policy name is required")

        if policy.runtime and policy.runtime not in self.VALID_RUNTIMES:
            errors.append(f"Unknown runtime: {policy.runtime***REMOVED***")

        if policy.capability and policy.capability not in self.VALID_CAPABILITIES:
            errors.append(f"Unknown capability: {policy.capability***REMOVED***")

        if policy.fallback_strategy not in self.VALID_STRATEGIES:
            errors.append(f"Invalid fallback strategy: {policy.fallback_strategy***REMOVED***")

        if policy.cost_limit_per_task < 0:
            errors.append("Cost limit per task must be >= 0")

        return errors
```

---

## 6. Policy Packs

### 6.1 Концепция

Policy Packs — переносимые наборы политик для различных сценариев.
Пользователи могут устанавливать, обмениваться и комбинировать их.

### 6.2 Pack Format

```yaml
# solo-developer.yaml
pack:
  name: solo-developer
  display_name: "Solo Developer"
  description: "Оптимизирован для одного разработчика. Кодинг → Claude Code, планирование → freebuff"
  author: "Buffy Community"
  version: "1.0.0"

policies:
  - name: solo-coding
    capability: coding
    runtime: claude-code
    provider: anthropic
    model: claude-3.5-sonnet

  - name: solo-planning
    capability: planning
    runtime: freebuff

  - name: solo-review
    capability: review
    runtime: claude-code
```

```yaml
# budget.yaml
pack:
  name: budget
  display_name: "Budget Mode"
  description: "Минимальные затраты. Использует freebuff модели где возможно"
  author: "Buffy Community"
  version: "1.0.0"

policies:
  - name: budget-coding
    capability: coding
    runtime: freebuff           # freebuff, бесплатно
    provider: deepseek
    model: deepseek-v4-flash    # дешёвая модель

  - name: budget-research
    capability: research
    runtime: freebuff           # без OpenClaw (экономия)

  cost:
    daily: 0.50
    per_task: 0.05
```

```yaml
# enterprise.yaml
pack:
  name: enterprise
  display_name: "Enterprise"
  description: "Безопасность, аудит, фиксированные провайдеры"
  author: "Buffy Enterprise"
  version: "2.0.0"

policies:
  - name: ent-coding
    capability: coding
    runtime: claude-code
    provider: anthropic        # фиксированный провайдер
    model: claude-opus-4.0

  - name: ent-review
    capability: review
    runtime: claude-code
    provider: anthropic

  fallback:
    strategy: ordered
    order: [claude-code***REMOVED***       # никакого fallback на freebuff

  audit:
    log_all: true              # логировать все решения
    notify_on_change: true     # уведомлять при изменении политики
```

### 6.3 Pack Manager

```python
class PolicyPackManager:
    """Управление Policy Packs."""

    def install(self, source: str) -> str:
        """Установить pack из файла/URL/репозитория."""
        ...

    def remove(self, name: str) -> bool:
        """Удалить pack."""
        ...

    def list_installed(self) -> List[PolicyPack***REMOVED***:
        """Список установленных pack."""
        ...

    def list_available(self) -> List[PolicyPack***REMOVED***:
        """Список доступных для установки pack."""
        ...

    def resolve_conflicts(self, packs: List[str***REMOVED***) -> List[PolicyConflict***REMOVED***:
        """Найти конфликты между packs."""
        ...

    def merge(self, pack_names: List[str***REMOVED***) -> Policy:
        """Объединить политики из нескольких packs в одну (по priority)."""
        ...
```

---

## 7. Интеграция с архитектурой

### 7.1 Связи

```
Policy Engine
  │
  ├── Capability Registry → capability → Runtime/Model mapping
  │
  ├── Runtime Abstraction Layer → выбор Runtime
  │     └── RuntimeRegistry.list() → доступные Runtime
  │
  ├── ModelGateway → выбор провайдера и модели
  │     └── ModelGateway.list_models() → доступные модели
  │
  ├── Orchestrator → выбор Workflow по политике
  │     └── PolicyEngine → определяет последовательность шагов
  │
  ├── Event Bus → публикация policy.* событий
  │     ├── policy.evaluated
  │     ├── policy.applied
  │     ├── policy.fallback
  │     ├── policy.cost_exceeded
  │     └── policy.error
  │
  ├── ContextManager → исторические данные для политик
  │     └── Анализ предыдущих сессий
  │
  └── Bootstrap Engine → установка Policy Packs
        └── profile → какие packs установлены по умолчанию
```

### 7.2 MCP регистрация

```python
# В mcp_server.py — паттерн регистрации (как у Bridge Layer)
def _get_policy_engine(self) -> PolicyEngine:
    if self._policy_engine is None:
        from freebuff_plugin.policy import PolicyEngine
        self._policy_engine = PolicyEngine(self.workspace)
    return self._policy_engine

# Регистрация инструментов
self.tool("policy_apply")(self._handle_policy_apply)
self.tool("policy_list")(self._handle_policy_list)
self.tool("policy_status")(self._handle_policy_status)
self.tool("pack_install")(self._handle_pack_install)
self.tool("capability_list")(self._handle_capability_list)
```

### 7.3 Поток данных: запрос → решение

```
buffy run "напиши тест" --capability testing
    │
    ▼
PolicyEngine.evaluate(context)
    │
    ├── 1. Context: capability="testing", project="current"
    ├── 2. Ищем active policies:
    │       ├── project=current + capability=testing → testing-default
    │       ├── capability=testing → testing-default
    │       └── global → system-default
    ├── 3. Выбираем: testing-default (priority 10, runtime=freebuff)
    ├── 4. Проверяем cost_limits: OK
    ├── 5. Проверяем доступность freebuff: OK
    └── 6. Решение: Runtime=freebuff, Provider=auto, Model=auto
    │
    ▼
RuntimeAbstractionLayer.generate("freebuff", messages)
    │
    ▼
Результат пользователю
```

---

## 8. MCP инструменты

```json
{
    "name": "policy_apply",
    "description": "Применить политику для задачи",
    "inputSchema": {
        "capability": { "type": "string" ***REMOVED***,
        "project": { "type": "string", "optional": true ***REMOVED***,
        "preferred_runtime": { "type": "string", "optional": true ***REMOVED***
    ***REMOVED***
***REMOVED***
{
    "name": "policy_list",
    "description": "Список всех политик",
    "inputSchema": {
        "tag": { "type": "string", "optional": true ***REMOVED***,
        "enabled": { "type": "boolean", "optional": true ***REMOVED***
    ***REMOVED***
***REMOVED***
{
    "name": "policy_status",
    "description": "Статус Policy Engine",
    "inputSchema": {***REMOVED***
***REMOVED***
{
    "name": "pack_install",
    "description": "Установить Policy Pack",
    "inputSchema": {
        "source": { "type": "string", "description": "file path, URL, or pack name" ***REMOVED***
    ***REMOVED***
***REMOVED***
{
    "name": "capability_list",
    "description": "Список всех capability и их Runtime",
    "inputSchema": {***REMOVED***
***REMOVED***
```

---

## 9. CLI для пользователя

```bash
# Список политик
buffy policy list
# → coding-default  [active***REMOVED***  runtime=claude-code  priority=10
# → review-default  [active***REMOVED***  runtime=claude-code
# → my-app-review   [active***REMOVED***  project=my-app  priority=50

# Применить политику
buffy run "напиши тест" --capability testing
buffy run "архитектура" --capability planning

# Управление политиками
buffy policy set coding-default --runtime freebuff
buffy policy disable review-default

# Policy Packs
buffy pack install solo-developer
buffy pack remove enterprise
buffy pack list

# Статус
buffy policy status
# → Active policies: 5
# → Packs installed: 2 (solo-developer, budget)
# → Default runtime: freebuff
# → Cost today: $0.35 / $5.00
```

---

## 10. Тестирование

### 10.1 Unit-тесты

| Тест | Что проверяет |
|------|--------------|
| `test_policy_store_crud` | PolicyStore: create/read/update/delete |
| `test_policy_evaluate` | PolicyExecutor: evaluate с matching политикой |
| `test_policy_no_match` | PolicyExecutor: evaluate без matching политики (default) |
| `test_policy_priority` | PolicyExecutor: выбор по priority |
| `test_policy_project_specific` | PolicyExecutor: project-specific имеет приоритет |
| `test_policy_fallback` | PolicyExecutor: fallback при недоступном Runtime |
| `test_policy_cost_limits` | PolicyExecutor: cost limits блокируют дорогую модель |
| `test_policy_conflict` | PolicyExecutor: разрешение конфликтов |
| `test_policy_validator` | PolicyValidator: валидация корректных/некорректных политик |
| `test_pack_install` | PolicyPackManager: установка pack из YAML |
| `test_pack_merge` | PolicyPackManager: merge политик из нескольких packs |
| `test_pack_conflict` | PolicyPackManager: обнаружение конфликтов |
| `test_capability_routing` | CapabilityRegistry: выбор Runtime по capability |
| `test_capability_confidence` | CapabilityRegistry: сортировка по confidence |
| `test_mcp_tools` | MCP инструменты policy_apply/list/status |

### 10.2 Boundary тесты

- Пустой PolicyStore (нет политик → system default)
- Политика с несуществующим Runtime
- Политика с отрицательным cost_limit
- Conflict: две политики с одинаковым priority и context
- 1000 политик в store (производительность)
- Pack с циклическими зависимостями
- Capability, которой нет ни у одного Runtime

---

## 11. Реализация

### 11.1 Файлы

```
freebuff_plugin/policy/
├── __init__.py              # PolicyEngine, Policy types
├── store.py                 # PolicyStore (SQLite)
├── executor.py              # PolicyExecutor
├── validator.py             # PolicyValidator
├── pack_manager.py          # PolicyPackManager
├── default.yaml             # Default system policy
├── packs/
│   ├── solo-developer.yaml
│   ├── budget.yaml
│   └── enterprise.yaml
└── schema.sql              # SQLite schema
```

### 11.2 Этапы реализации

| Этап | Что | Тестов | Зависимости |
|------|-----|--------|-------------|
| **1. Store** | PolicyStore CRUD, SQLite schema | 10 | Нет |
| **2. Executor** | PolicyExecutor evaluate + fallback | 12 | Store, CapabilityRegistry |
| **3. Validator** | PolicyValidator, sanity check | 6 | Executor |
| **4. CLI** | buffy policy list/apply/set | 5 | Executor |
| **5. Packs** | PolicyPackManager, YAML import/export | 10 | Store, Validator |
| **6. MCP** | policy_apply/list/status/pack_install | 6 | MCP Server |
| **7. Cost** | Cost limits tracking, daily budget | 8 | Executor |
| **ИТОГО** | | **~67 тестов** | |

### 11.3 Приоритет

| Приоритет | Компонент | Обоснование |
|-----------|-----------|-------------|
| P0 | PolicyStore + Executor | Ядро Policy Engine |
| P1 | Validator + Capability Registry | Безопасность и корректность |
| P1 | CLI для пользователя | UX |
| P2 | MCP инструменты | Интеграция с агентами |
| P3 | Policy Packs | Обмен политиками |

---

## 12. Критерии готовности

- [ ***REMOVED*** PolicyStore CRUD — create, read, update, delete политик
- [ ***REMOVED*** PolicyExecutor.evaluate() — выбор Runtime/Provider/Model по контексту
- [ ***REMOVED*** Fallback chain — next-available, ordered, random
- [ ***REMOVED*** Cost limits — daily и per_task бюджеты
- [ ***REMOVED*** PolicyValidator — валидация YAML политик
- [ ***REMOVED*** CLI: `buffy policy list`, `buffy policy apply`, `buffy policy status`
- [ ***REMOVED*** MCP: `policy_apply`, `policy_list`, `policy_status`, `pack_install`
- [ ***REMOVED*** Policy Pack Manager — install/remove/list/merge
- [ ***REMOVED*** Event Bus: policy.evaluated, policy.applied, policy.fallback
- [ ***REMOVED*** 67+ тестов, 0 failures
- [ ***REMOVED*** Интеграция с Capability Registry (см. CAPABILITY_SPECIFICATION.md)

---

*Связанные документы: [CAPABILITY_SPECIFICATION.md***REMOVED***(CAPABILITY_SPECIFICATION.md), [VISION_3.0.md***REMOVED***(../vision/VISION_3.0.md), [ARCHITECTURE_3.0.md***REMOVED***(ARCHITECTURE_3.0.md), [RUNTIME_ABSTRACTION_SPECIFICATION.md***REMOVED***(RUNTIME_ABSTRACTION_SPECIFICATION.md)*
