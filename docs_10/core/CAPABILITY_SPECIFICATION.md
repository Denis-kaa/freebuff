# CAPABILITY SPECIFICATION — Capability Registry & Routing

> **Версия:** 1.0.0  
> **Дата:** 2026-07-29  
> **Статус:** Спецификация (к реализации)  
> **Основание:** [VISION_3.0.md***REMOVED***(../vision/VISION_3.0.md), [ARCHITECTURE_3.0.md***REMOVED***(ARCHITECTURE_3.0.md), [014_02_leviathan_arhitektura.md***REMOVED***(../../pompts_11/014_02_leviathan_arhitektura.md) (концепция #10)  

---

## Содержание

1. [Executive Summary***REMOVED***(#1-executive-summary)
2. [Архитектура***REMOVED***(#2-архитектура)
3. [Capability Registry***REMOVED***(#3-capability-registry)
4. [Capability Scoring***REMOVED***(#4-capability-scoring)
5. [Capability Routing***REMOVED***(#5-capability-routing)
6. [Стандартные Capability***REMOVED***(#6-стандартные-capability)
7. [Capability Discovery***REMOVED***(#7-capability-discovery)
8. [Интеграция с Policy Engine***REMOVED***(#8-интеграция-с-policy-engine)
9. [MCP инструменты***REMOVED***(#9-mcp-инструменты)
10. [CLI для пользователя***REMOVED***(#10-cli-для-пользователя)
11. [Тестирование***REMOVED***(#11-тестирование)
12. [Реализация***REMOVED***(#12-реализация)
13. [Критерии готовности***REMOVED***(#13-критерии-готовности)

---

## 1. Executive Summary

**Capability Registry** — это компонент, который маппит **возможности (capability)**
на **AI Runtime** и **модели**, которые могут их выполнять.

**Ключевой принцип:** Пользователь выбирает не модель, а capability.
Какая модель выполняет capability — определяется политиками пользователя.

```
Пользователь: "напиши код"  →  capability: "coding"
Engine:       "coding"      →  Runtime: "claude-code"  →  Model: "claude-3.5-sonnet"
```

**Что делает Capability Registry:**
- Хранит маппинг capability → Runtime
- Хранит маппинг capability → Model (через провайдера)
- Оценивает confidence (насколько Runtime хорош в capability)
- Поддерживает авто-обнаружение capability через Runtime Registry
- Предоставляет API для Policy Engine

---

## 2. Архитектура

### 2.1 Общая схема

```
┌──────────────────────────────────────────────────────────────┐
│                     CAPABILITY REGISTRY                       │
│                                                               │
│  ┌────────────────────┐  ┌───────────────────────────────┐   │
│  │  Capability Store   │  │   Capability Router          │   │
│  │                     │  │                               │   │
│  │  • capability defs  │  │  • capability → Runtime      │   │
│  │  • Runtime mapping  │  │  • capability → Model        │   │
│  │  • Model mapping    │  │  • scoring & ranking         │   │
│  │  • confidence scores│  │  • multi-capability routing  │   │
│  └────────────────────┘  └───────────────────────────────┘   │
│                                                               │
│  ┌────────────────────┐  ┌───────────────────────────────┐   │
│  │  Capability        │  │   Capability Discovery        │   │
│  │  Validator         │  │                               │   │
│  │                    │  │  • auto-detect from Runtime   │   │
│  │  • проверка name   │  │  • import from YAML          │   │
│  │  • проверка mapping│  │  • plugin registration       │   │
│  │  • conflict detect │  │  • sync with Runtime Registry │   │
│  └────────────────────┘  └───────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
         │                        │
         ▼                        ▼
   ┌────────────┐          ┌────────────┐
   │ Policy     │          │ Runtime    │
   │ Engine     │          │ Abstraction│
   └────────────┘          └────────────┘
```

### 2.2 Абстракции

```
┌──────────────────────────────┐
│    CapabilityDefinition      │  ← Определение capability (имя, описание)
├──────────────────────────────┤
│    CapabilityMapping         │  ← Маппинг capability → Runtime/Model
├──────────────────────────────┤
│    CapabilityScore           │  ← Оценка Runtime для capability (0.0-1.0)
├──────────────────────────────┤
│    CapabilityRoute           │  ← Результат роутинга: какой Runtime использовать
├──────────────────────────────┤
│    CapabilitySource          │  ← Откуда capability (builtin, runtime, plugin, user)
└──────────────────────────────┘
```

### 2.3 Место в архитектуре

Capability Registry находится в Extensions, между Policy Engine и Runtime Abstraction Layer:

```
Запрос пользователя
    │
    ▼
Policy Engine
    │
    ▼
Capability Registry ← Runtime Registry (discover)
    │
    ├──→ Определяем: capability → Runtime
    ├──→ Определяем: capability → Model (через Provider)
    └──→ Возвращаем: PolicyResult
         │
         ▼
    Runtime Abstraction Layer → выполнение
```

---

## 3. Capability Registry

### 3.1 CapabilityRegistry

```python
class CapabilityRegistry:
    """Реестр capability и их маппинг на Runtime и модели."""

    def __init__(self, storage: Optional[Path***REMOVED*** = None):
        self._storage = storage or Path("data_13/capabilities.json")

    # ── Определения ───────────────────────────────────────────

    def register_capability(self, capability: CapabilityDefinition) -> None:
        """Зарегистрировать новую capability."""
        ...

    def unregister_capability(self, name: str) -> bool:
        """Удалить capability."""
        ...

    def get_capability(self, name: str) -> Optional[CapabilityDefinition***REMOVED***:
        """Получить определение capability."""
        ...

    def list_capabilities(self) -> List[CapabilityDefinition***REMOVED***:
        """Список всех зарегистрированных capability."""
        ...

    # ── Маппинг ──────────────────────────────────────────────

    def map_runtime(self, capability: str, runtime: str, score: float) -> None:
        """Установить маппинг capability → Runtime с оценкой."""
        ...

    def map_model(self, capability: str, provider: str, model: str, score: float) -> None:
        """Установить маппинг capability → Model с оценкой."""
        ...

    def get_runtimes_for_capability(self, capability: str) -> List[CapabilityMapping***REMOVED***:
        """Получить все Runtime для capability, отсортированные по score."""
        ...

    def get_models_for_capability(self, capability: str) -> List[CapabilityMapping***REMOVED***:
        """Получить все модели для capability, отсортированные по score."""
        ...

    # ── Роутинг ──────────────────────────────────────────────

    def route(
        self,
        capability: str,
        preferred_runtime: Optional[str***REMOVED*** = None,
    ) -> CapabilityRoute:
        """Выбрать лучший Runtime для capability."""
        ...

    def route_multi(
        self,
        capabilities: List[str***REMOVED***,
    ) -> Dict[str, CapabilityRoute***REMOVED***:
        """Выбрать Runtime для нескольких capability."""
        ...

    # ── Персистентность ──────────────────────────────────────

    def save(self) -> None:
        """Сохранить registry в storage."""
        ...

    def load(self) -> None:
        """Загрузить registry из storage."""
        ...

    def discover_from_runtimes(self, runtime_registry: RuntimeRegistry) -> int:
        """Авто-обнаружение capability из зарегистрированных Runtime.

        Вызывает RuntimeCapabilityRegistry (из RAL) для каждого Runtime
        и добавляет новые capability/mapping в свой реестр.
        """
        ...
```

### 3.2 Типы данных

```python
@dataclass
class CapabilityDefinition:
    """Определение capability."""

    name: str                           # "coding", "review", "planning"
    display_name: str                   # "Code Generation", "Code Review"
    description: str
    category: str                       # "development", "research", "management"
    tags: List[str***REMOVED*** = field(default_factory=list)

    # Мета
    source: str = "builtin"             # "builtin", "runtime", "plugin", "user"
    source_name: str = ""               # имя Runtime/плагина, предоставившего capability
    version: str = "1.0.0"
    deprecated: bool = False

    # Параметры
    requires_network: bool = False      # требуется интернет?
    requires_api_key: bool = False      # требуется API ключ?
    estimated_cost_per_task: float = 0.0  # примерная стоимость


@dataclass
class CapabilityMapping:
    """Маппинг capability → Runtime или Model."""

    capability: str
    target_type: str                    # "runtime", "provider", "model"
    target_name: str                    # имя Runtime/Provider/Model
    score: float = 1.0                  # 0.0 (плохо) — 1.0 (идеально)

    # Дополнительно
    provider: Optional[str***REMOVED*** = None      # для model: какой провайдер
    context_window: Optional[int***REMOVED*** = None  # контекст модели
    max_tokens: Optional[int***REMOVED*** = None


@dataclass
class CapabilityScore:
    """Оценка Runtime для capability."""

    runtime: str
    capability: str
    overall_score: float                # итоговая оценка (0.0-1.0)

    # Компоненты оценки
    benchmark_score: float = 0.0        # на основе бенчмарков
    user_score: float = 0.0            # пользовательская оценка
    community_score: float = 0.0       # от сообщества
    auto_score: float = 0.0            # автоматическая (Runtime Doctor)


@dataclass
class CapabilityRoute:
    """Результат роутинга — что использовать для capability."""

    capability: str
    runtime: Optional[str***REMOVED*** = None
    provider: Optional[str***REMOVED*** = None
    model: Optional[str***REMOVED*** = None
    score: float = 0.0
    alternatives: List[Dict[str, Any***REMOVED******REMOVED*** = field(default_factory=list)
    error: Optional[str***REMOVED*** = None
```

### 3.3 Storage (JSON)

```json
{
  "version": "1.0.0",
  "capabilities": {
    "coding": {
      "display_name": "Code Generation",
      "description": "Generation of new code and refactoring",
      "category": "development",
      "tags": ["code", "development"***REMOVED***,
      "source": "builtin"
    ***REMOVED***,
    "review": {
      "display_name": "Code Review",
      "description": "Analysis and review of existing code",
      "category": "development",
      "source": "builtin"
    ***REMOVED***
  ***REMOVED***,
  "mappings": {
    "coding": {
      "runtimes": [
        {"name": "claude-code", "score": 0.95, "provider": "anthropic", "model": "claude-3.5-sonnet"***REMOVED***,
        {"name": "freebuff", "score": 0.85, "provider": "deepseek", "model": "deepseek-v4-flash"***REMOVED***,
        {"name": "gpt-4o", "score": 0.80, "provider": "openai", "model": "gpt-4o"***REMOVED***
      ***REMOVED***
    ***REMOVED***,
    "review": {
      "runtimes": [
        {"name": "claude-code", "score": 0.95, "provider": "anthropic", "model": "claude-3.5-sonnet"***REMOVED***,
        {"name": "freebuff", "score": 0.70, "provider": "deepseek", "model": "deepseek-v4-flash"***REMOVED***
      ***REMOVED***
    ***REMOVED***
  ***REMOVED***,
  "scores": {
    "claude-code": {
      "coding": {"overall": 0.95, "benchmark": 0.94, "auto": 0.96***REMOVED***,
      "review": {"overall": 0.95, "benchmark": 0.93, "auto": 0.97***REMOVED***,
      "planning": {"overall": 0.80, "benchmark": 0.78, "auto": 0.82***REMOVED***
    ***REMOVED***,
    "freebuff": {
      "coding": {"overall": 0.85, "benchmark": 0.82, "auto": 0.88***REMOVED***
    ***REMOVED***
  ***REMOVED***
***REMOVED***
```

---

## 4. Capability Scoring

### 4.1 Система оценки

Capability оценивается по нескольким измерениям:

| Компонент | Вес | Источник |
|-----------|-----|----------|
| **benchmark_score** | 40% | Бенчмарки (HumanEval, SWE-bench) |
| **auto_score** | 30% | Runtime Doctor: тестовый промпт → оценка результата |
| **user_score** | 20% | Пользователь: thumbs up/down после каждой задачи |
| **community_score** | 10% | Сообщество: агрегированные оценки |

```python
def calculate_overall_score(scores: CapabilityScore) -> float:
    """Рассчитать итоговую оценку."""
    return (
        scores.benchmark_score * 0.4 +
        scores.auto_score * 0.3 +
        scores.user_score * 0.2 +
        scores.community_score * 0.1
    )
```

### 4.2 Runtime Doctor (интеграция)

Runtime Doctor (Labs) запускает тестовый промпт для каждого Runtime
и оценивает качество результата. Результат → `auto_score`.

```python
class CapabilityAutoScorer:
    """Автоматическая оценка capability через Runtime Doctor."""

    def score_runtime(
        self,
        runtime: str,
        capability: str,
    ) -> float:
        """Запустить тестовый промпт для capability и оценить результат."""
        test_prompts = {
            "coding": "Напиши функцию сортировки слиянием на Python",
            "review": "Найди ошибки в этом коде: [code***REMOVED***",
            "planning": "Спланируй архитектуру микросервиса",
        ***REMOVED***
        prompt = test_prompts.get(capability)
        if not prompt:
            return 0.5  # нейтральная оценка для неизвестных capability

        result = runtime_adapter.generate(prompt)
        score = self._evaluate_result(result, capability)
        return score
```

### 4.3 User Feedback

Пользователь может влиять на scores:

```bash
# После выполнения задачи
buffy rate 5                     # оценить последний результат (1-5)
buffy rate good                  # thumbs up
buffy rate bad                   # thumbs down

# Изменить score для пары capability+Runtime
buffy capability score coding --runtime claude-code --set 0.9
```

---

## 5. Capability Routing

### 5.1 Алгоритм выбора

```
route(capability, preferred_runtime=None):
  1. Найти все маппинги для capability
  2. Если preferred_runtime задан:
     a. Проверить, есть ли маппинг для preferred_runtime
     b. Если есть → вернуть его
     c. Если нет → Warning: preferred Runtime не поддерживает capability
  3. Отсортировать маппинги по score (desc)
  4. Вернуть маппинг с наивысшим score
  5. Включить альтернативы в результат
```

### 5.2 Multi-capability routing

Для задач, требующих нескольких capability:

```python
def route_multi(self, capabilities: List[str***REMOVED***) -> Dict[str, CapabilityRoute***REMOVED***:
    """Выбрать Runtime для нескольких capability.

    Пытается найти один Runtime, который хорошо справляется
    со всеми capability. Если такого нет — выбирает лучший
    для каждой capability отдельно.
    """
    # 1. Найти Runtime, которые покрывают все capability
    common_runtimes = self._find_common_runtimes(capabilities)
    
    if common_runtimes:
        # 2. Есть Runtime, покрывающий всё → используем его
        best = common_runtimes[0***REMOVED***
        return {cap: self.route(cap, preferred_runtime=best.runtime)
                for cap in capabilities***REMOVED***
    
    # 3. Нет единого Runtime → выбираем лучший для каждой capability
    return {cap: self.route(cap) for cap in capabilities***REMOVED***
```

### 5.3 Примеры роутинга

| Задача | capability | Runtime выбран | Почему |
|--------|-----------|---------------|--------|
| «Напиши тест» | testing | freebuff | freebuff лучший для testing (0.80) |
| «Сделай ревью» | review | claude-code | claude-code лучший для review (0.95) |
| «Найди в интернете» | research | openclaw | openclaw spec для research (0.85) |
| «Спланируй архитектуру» | planning | freebuff | planning не требует внешних моделей |
| «Переведи на английский» | translation | gpt-4o | gpt-4o лучший для translation (0.90) |

---

## 6. Стандартные Capability

### 6.1 Built-in capability (Core)

| Capability | Описание | Категория | Требует сети | Лучший Runtime |
|------------|----------|-----------|-------------|---------------|
| **coding** | Написание и рефакторинг кода | development | опционально | claude-code |
| **review** | Ревью кода, поиск ошибок | development | опционально | claude-code |
| **planning** | Планирование задач | development | нет | freebuff |
| **architecture** | Проектирование архитектуры | development | опционально | claude-code |
| **research** | Поиск информации, исследования | research | да | openclaw |
| **documentation** | Генерация документации | development | опционально | claude-code |
| **testing** | Написание тестов | development | нет | freebuff |
| **refactoring** | Рефакторинг кода | development | нет | freebuff |
| **translation** | Перевод кода/текста | management | да | ModelGateway (gpt-4o) |

### 6.2 Категории

```
development:  coding, review, planning, documentation, testing, refactoring
research:     research
management:   translation, architecture
```

### 6.3 Capability Discovery

Capability Registry может авто-обнаруживать новые capability:

1. **Из Runtime** — каждый Runtime может предоставить свои capability
2. **Из плагинов** — плагины могут регистрировать новые capability
3. **Из Policy Packs** — pack может определять новые capability
4. **Пользовательские** — пользователь может добавить свою capability

```python
@dataclass
class CapabilityProvider:
    """Провайдер capability — Runtime, плагин или пользователь."""

    source_type: str                    # "runtime", "plugin", "user"
    source_name: str                    # "claude-code", "my-plugin"
    capabilities: List[CapabilityDefinition***REMOVED***
    mappings: List[CapabilityMapping***REMOVED***
```

---

## 7. Integration с Policy Engine

### 7.1 Совместная работа

```
Policy Engine + Capability Registry:

1. Пользователь: "напиши тест"
2. Intent Router: → capability="testing"
3. Policy Engine:
   a. Создаёт PolicyEvaluationContext(capability="testing")
   b. Вызывает CapabilityRegistry.route("testing")
   c. Получает CapabilityRoute(runtime="freebuff", score=0.80)
   d. Проверяет cost_limits → OK
   e. Применяет пользовательские политики (override?)
   f. Возвращает PolicyResult(runtime="freebuff")
4. Runtime Abstraction Layer: generate() через freebuff
```

### 7.2 Override через политики

Capability Registry определяет **рекомендованный** Runtime.
Policy Engine может **override** это решение на основе политик пользователя.

```yaml
# Пользовательская политика — override
- name: my-coding-override
  capability: coding
  runtime: freebuff                 # вместо claude-code (рекомендованного)
  reason: "Экономлю ключи Anthropic"
```

### 7.3 Пример: полный цикл

```python
# 1. Пользовательский запрос
user_input = "сделай ревью этого пулл-реквеста"

# 2. Intent Router определяет capability
capability = "review"

# 3. Policy Engine собирает контекст
context = PolicyEvaluationContext(
    capability=capability,
    project="my-app",
    preferred_runtime=None,  # пользователь не указал
)

# 4. Policy Engine вызывает Capability Registry
capability_route = capability_registry.route(capability)
# → CapabilityRoute(
#     capability="review",
#     runtime="claude-code",
#     score=0.95,
#     alternatives=[{"runtime": "freebuff", "score": 0.70***REMOVED******REMOVED***
#   )

# 5. Policy Engine применяет политики
policy_result = policy_executor.evaluate(context)
# → PolicyResult(
#     runtime="claude-code",
#     provider="anthropic",
#     model="claude-3.5-sonnet",
#     policy_name="review-default",
#     fallback_used=False,
#   )

# 6. Runtime Abstraction Layer выполняет
result = runtime_layer.generate("claude-code", messages)
```

---

## 8. Интеграция с MCP Server

MCP tools для Capability Registry регистрируются в `scripts_01/mcp_server.py`
по тому же паттерну, что Bridge Layer, Bootstrap Engine и Policy Engine:

```python
def _get_capability_registry(self) -> CapabilityRegistry:
    if self._capability_registry is None:
        from freebuff_plugin.capability import CapabilityRegistry
        self._capability_registry = CapabilityRegistry()
        self._capability_registry.load()
    return self._capability_registry

def _register_tools(self) -> None:
    # ... существующие инструменты ...
    self.tool("capability_list")(self._handle_capability_list)
    self.tool("capability_route")(self._handle_capability_route)
    self.tool("capability_score")(self._handle_capability_score)
```

### 8.1 MCP инструменты

```json
{
    "name": "capability_list",
    "description": "Список всех capability",
    "inputSchema": {
        "category": { "type": "string", "optional": true ***REMOVED***
    ***REMOVED***
***REMOVED***
{
    "name": "capability_route",
    "description": "Выбрать Runtime для capability",
    "inputSchema": {
        "capability": { "type": "string" ***REMOVED***,
        "preferred_runtime": { "type": "string", "optional": true ***REMOVED***
    ***REMOVED***
***REMOVED***
{
    "name": "capability_score",
    "description": "Получить score Runtime для capability",
    "inputSchema": {
        "runtime": { "type": "string" ***REMOVED***,
        "capability": { "type": "string" ***REMOVED***
    ***REMOVED***
***REMOVED***
```

---

## 9. CLI для пользователя

```bash
# Список всех capability
buffy capability list
# → coding        [development***REMOVED***  best: claude-code (0.95)
# → review        [development***REMOVED***  best: claude-code (0.95)
# → planning      [development***REMOVED***  best: freebuff (0.85)
# → research      [research***REMOVED***     best: openclaw (0.85)

# Узнать какой Runtime использовать для capability
buffy capability route planning
# → freebuff (0.85)  alternatives: claude-code (0.80)

# Оценить Runtime для capability
buffy capability score claude-code review
# → 0.95  (benchmark: 0.93, auto: 0.97)

# Изменить score
buffy capability score coding --runtime freebuff --set 0.9

# Зарегистрировать новую capability
buffy capability register my-capability --category development --description "..."
```

---

## 10. Тестирование

### 10.1 Unit-тесты

| Тест | Что проверяет |
|------|--------------|
| `test_capability_crud` | CapabilityRegistry: register/get/list/unregister |
| `test_capability_map` | CapabilityRegistry: map_runtime, get_runtimes_for_capability |
| `test_capability_route` | CapabilityRegistry: route — выбор лучшего Runtime |
| `test_capability_route_preferred` | CapabilityRegistry: route с preferred_runtime |
| `test_capability_route_no_match` | CapabilityRegistry: route без matching Runtime |
| `test_capability_multi_route` | CapabilityRegistry: route_multi |
| `test_capability_scoring` | CapabilityScore: calculate_overall_score |
| `test_capability_discovery` | CapabilityDiscovery: auto-detect from Runtime |
| `test_capability_persist` | CapabilityRegistry: save/load JSON |
| `test_capability_validator` | CapabilityValidator: проверка дубликатов, конфликтов |
| `test_capability_user_override` | CapabilityRegistry: пользовательский score override |
| `test_integration_with_policy` | CapabilityRegistry + PolicyEngine: полный цикл |

### 10.2 Boundary тесты

- CapabilityRegistry пустой (нет capability)
- Все Runtime имеют score 0.0 для capability
- 100 capability в registry (производительность)
- Capability с несуществующим Runtime в маппинге
- Multi-route с 10 capability

---

## 11. Реализация

### 11.1 Файлы

```
freebuff_plugin_03/capability/
├── __init__.py              # CapabilityRegistry, типы данных
├── registry.py              # CapabilityRegistry
├── router.py                # CapabilityRouter
├── scorer.py                # CapabilityScorer
├── discovery.py             # CapabilityDiscovery
├── validator.py             # CapabilityValidator
└── builtin.yaml             # Стандартные capability
```

### 11.2 Этапы реализации

| Этап | Что | Тестов | Зависимости |
|------|-----|--------|-------------|
| **1. Core API** | CapabilityDefinition, CapabilityMapping, базовые типы | 6 | Нет |
| **2. Registry** | CapabilityRegistry CRUD + JSON storage | 10 | Core API |
| **3. Router** | CapabilityRouter: route + route_multi | 8 | Registry |
| **4. Scorer** | CapabilityScorer: overall_score, user override | 8 | Router |
| **5. Discovery** | CapabilityDiscovery: auto-detect from Runtime | 6 | Registry, RuntimeRegistry (RAL) |
| **6. CLI** | buffy capability list/route/score/register | 5 | Router |
| **7. MCP** | capability_list/route/score | 4 | MCP Server |
| **8. Policy integration** | Полный цикл: CapabilityRegistry + PolicyExecutor | 8 | Policy Engine |
| **ИТОГО** | | **~55 тестов** | |

### 11.3 Приоритет

| Приоритет | Компонент | Обоснование |
|-----------|-----------|-------------|
| P0 | Core API + Registry | База для всей capability системы |
| P1 | Router | Немедленно нужен для Policy Engine |
| P1 | CLI для пользователя | UX |
| P2 | Scorer + Discovery | Улучшение качества |
| P3 | Policy integration | После Policy Engine |

---

## 12. Критерии готовности

- [ ***REMOVED*** CapabilityRegistry — register/get/list/unregister capability
- [ ***REMOVED*** CapabilityRouter — route(capability) → лучший Runtime
- [ ***REMOVED*** CapabilityRouter — route_multi(capabilities) → несколько capability
- [ ***REMOVED*** CapabilityScorer — overall_score с benchmark/auto/user/community
- [ ***REMOVED*** JSON persistence — save/load registry
- [ ***REMOVED*** CapabilityDiscovery — auto-detect из RuntimeRegistry
- [ ***REMOVED*** CLI: `buffy capability list`, `buffy capability route`, `buffy capability score`
- [ ***REMOVED*** MCP: `capability_list`, `capability_route`, `capability_score`
- [ ***REMOVED*** Интеграция с Policy Engine — полный цикл
- [ ***REMOVED*** 55+ тестов, 0 failures
- [ ***REMOVED*** 8 built-in capability (coding, review, planning, research, documentation, testing, refactoring, translation)

---

*Связанные документы: [POLICY_ENGINE_SPECIFICATION.md***REMOVED***(POLICY_ENGINE_SPECIFICATION.md), [VISION_3.0.md***REMOVED***(../vision/VISION_3.0.md), [ARCHITECTURE_3.0.md***REMOVED***(ARCHITECTURE_3.0.md), [RUNTIME_ABSTRACTION_SPECIFICATION.md***REMOVED***(RUNTIME_ABSTRACTION_SPECIFICATION.md)*
