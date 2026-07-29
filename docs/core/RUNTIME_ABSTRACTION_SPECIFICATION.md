# RUNTIME ABSTRACTION SPECIFICATION — Universal Runtime API

> **Версия:** 1.0.0  
> **Дата:** 2026-07-29  
> **Статус:** Спецификация (к реализации)  
> **Основание:** [VISION_3.0.md***REMOVED***(VISION_3.0.md), [ARCHITECTURE_3.0.md***REMOVED***(ARCHITECTURE_3.0.md), [promt14.md***REMOVED***(../pompts/promt14.md) (концепция #3)  

---

## Содержание

1. [Executive Summary***REMOVED***(#1-executive-summary)
2. [Архитектура***REMOVED***(#2-архитектура)
3. [Runtime API***REMOVED***(#3-runtime-api)
4. [Adapter Layer***REMOVED***(#4-adapter-layer)
5. [Поддерживаемые Runtime***REMOVED***(#5-поддерживаемые-runtime)
6. [Runtime Registry***REMOVED***(#6-runtime-registry)
7. [Интеграция с существующей архитектурой***REMOVED***(#7-интеграция-с-существующей-архитектурой)
8. [Профили Runtime***REMOVED***(#8-профили-runtime)
9. [Потоки данных***REMOVED***(#9-потоки-данных)
10. [Тестирование***REMOVED***(#10-тестирование)
11. [Реализация***REMOVED***(#11-реализация)
12. [Критерии готовности***REMOVED***(#12-критерии-готовности)
13. [Открытые вопросы***REMOVED***(#13-открытые-вопросы)

---

## 1. Executive Summary

**Runtime Abstraction Layer (RAL)** — это компонент Extensions, который предоставляет
универсальный API для взаимодействия Buffy с любым AI Runtime.

**Ключевой принцип:** Buffy никогда не зависит от конкретного AI Runtime.
Все Runtime подключаются через Adapter Layer.

**Что делает RAL:**
- Предоставляет единый Runtime API: `generate`, `generate_stream`, `list_models`, `capabilities`
- Содержит Adapter Layer для каждого Runtime (freebuff, Claude Code, OpenClaw, Hermes, Codex)
- Управляет Runtime Registry — установка, версионирование, переключение
- Публикует события в Event Bus (`runtime.*`)
- Интегрируется с Policy Engine для выбора Runtime по capability

**RAL — не замена ModelGateway.**
ModelGateway работает с API-провайдерами (OpenAI, Anthropic, DeepSeek).
RAL работает с AI Runtime (Claude Code, OpenClaw, Codebuff).

```
ModelGateway: API Provider → LLM
RAL:          AI Runtime   → Agent (который может использовать LLM)
```

### 1.1 Архитектурное замечание: зависимость RAL → Bridge Platform

По ARCHITECTURE_3.0.md §1.2 (принцип 2), Extensions не должны зависеть друг от друга.
Однако RAL использует `StdioMCPClient` и `HTTPMCPClient` из Bridge Platform для транспорта.

**Решение — прагматическое исключение:** MCP Client является настолько фундаментальным
транспортным слоем, что его можно считать **Core-компонентом** (вынести при рефакторинге),
либо RAL и Bridge Platform должны быть объединены под общей `freebuff_plugin/`.

На этапе реализации это решается дублированием интерфейса MCP Client внутри RAL
(абстракция транспорта) без прямой зависимости от bridge_layer.

---

## 2. Архитектура

### 2.1 Общая схема

```
┌─────────────────────────────────────────────────────────────────────┐
│                     RUNTIME ABSTRACTION LAYER                        │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                     Runtime API                               │    │
│  │  (generate, generate_stream, list_models, capabilities,       │    │
│  │   ping, health, context_build, shutdown)                      │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                       │
│        ┌─────────────────────┼─────────────────────┐                │
│        ▼                     ▼                     ▼                  │
│  ┌──────────┐          ┌──────────┐          ┌──────────┐           │
│  │ Freebuff │          │  Claude  │          │ OpenClaw │           │
│  │ Adapter  │          │  Code    │          │ Adapter  │           │
│  │          │          │  Adapter │          │          │           │
│  │ MCP.stdio│          │ MCP.stdio│          │ MCP.stdio│           │
│  └──────────┘          └──────────┘          └──────────┘           │
│                                                                      │
│  ┌──────────┐          ┌──────────┐          ┌──────────┐           │
│  │  Hermes  │          │  Codex   │          │  Future  │           │
│  │ Adapter  │          │ Adapter  │          │ Runtime  │           │
│  │          │          │          │          │ Adapter  │           │
│  │ MCP.stdio│          │ MCP.stdio│          │ pluggable│           │
│  └──────────┘          └──────────┘          └──────────┘           │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                   Runtime Registry                           │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │    │
│  │  │ Discover    │  │ Version     │  │ Config              │  │    │
│  │  │ Runtime     │  │ Management  │  │ Management          │  │    │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
         │                        │                       │
         ▼                        ▼                       ▼
   ┌────────────┐          ┌────────────┐          ┌────────────┐
   │  MCP via   │          │ Model       │          │ Event Bus  │
   │  Bridge    │          │ Gateway     │          │ runtime.*  │
   └────────────┘          └────────────┘          └────────────┘
```

### 2.2 Абстракции

```
┌────────────────────────────┐
│    RuntimeDefinition       │  ← Метаданные Runtime (имя, версия, адаптер)
├────────────────────────────┤
│    RuntimeAdapter          │  ← Базовый класс адаптера для Runtime
├────────────────────────────┤
│    RuntimeSession          │  ← Сессия с конкретным Runtime (контекст, история)
├────────────────────────────┤
│    RuntimeRegistry         │  ← Реестр доступных и установленных Runtime
├────────────────────────────┤
│    RuntimeConfig           │  ← Конфигурация Runtime (политики, лимиты)
├────────────────────────────┤
│    RuntimeCapability       │  ← Capability Runtime (coding, planning, ...)
└────────────────────────────┘
```

### 2.3 Жизненный цикл Runtime

```
INSTALLED → DISCOVERED → CONNECTED → ACTIVE → DISCONNECTED
                │                        │
                ▼                        ▼
           UPDATE_AVAILABLE          ERROR
                │                        │
                ▼                        ▼
            UPDATING                 RECOVERING → ACTIVE
                │
                ▼
          INSTALLED (updated)
```

### 2.4 Место в архитектуре

RAL находится в Extensions, между Core (Policy Engine, Event Bus) и внешними AI Runtime:

```
Policy Engine → выбирает Runtime по capability
     │
     ▼
Runtime Abstraction Layer → Runtime API
     │
     ├──→ RuntimeAdapter → Runtime Process (stdio MCP)
     ├──→ RuntimeAdapter → HTTP API (OpenAI-compatible)
     └──→ RuntimeAdapter → freebuff subprocess
          │
          ▼
     Event Bus → runtime.connected, runtime.disconnected, runtime.error
```

---

## 3. Runtime API

### 3.1 Базовый протокол

```python
class RuntimeAPI(ABC):
    """Единый API для взаимодействия с AI Runtime."""

    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, str***REMOVED******REMOVED***,
        system: Optional[str***REMOVED*** = None,
        temperature: float = 0.7,
        max_tokens: Optional[int***REMOVED*** = None,
        stream: bool = False,
    ) -> RuntimeResult:
        """Генерация ответа от Runtime."""
        ...

    @abstractmethod
    def generate_stream(
        self,
        messages: List[Dict[str, str***REMOVED******REMOVED***,
        system: Optional[str***REMOVED*** = None,
        temperature: float = 0.7,
        max_tokens: Optional[int***REMOVED*** = None,
    ) -> Iterator[RuntimeChunk***REMOVED***:
        """Стриминг ответа от Runtime."""
        ...

    @abstractmethod
    def ping(self) -> bool:
        """Проверка доступности Runtime."""
        ...

    @abstractmethod
    def health(self) -> RuntimeHealth:
        """Полный health check Runtime."""
        ...

    @abstractmethod
    def shutdown(self) -> None:
        """Корректное завершение Runtime."""
        ...
```

### 3.2 Типы данных

```python
@dataclass
class RuntimeDefinition:
    """Метаданные AI Runtime."""
    name: str                           # "freebuff", "claude-code", "openclaw"
    display_name: str                   # "Freebuff CLI", "Claude Code"
    version: str                        # "1.0.0"
    adapter_type: str                   # "stdio_mcp", "http", "subprocess"
    capabilities: List[str***REMOVED***             # ["coding", "planning", "research"***REMOVED***
    status: RuntimeStatus               # INSTALLED, CONNECTED, ACTIVE, ERROR
    config: Optional[RuntimeConfig***REMOVED***


@dataclass
class RuntimeResult:
    """Результат генерации Runtime."""
    content: str
    runtime: str
    finish_reason: str = "stop"
    usage: Dict[str, int***REMOVED*** = field(default_factory=dict)
    latency_ms: int = 0

    # Метаданные Runtime
    model_used: Optional[str***REMOVED*** = None    # Какая модель внутри Runtime была использована
    provider_used: Optional[str***REMOVED*** = None # Какой провайдер
    cached: bool = False
    fallback_used: bool = False


@dataclass
class RuntimeCapability:
    """Возможность Runtime."""
    name: str                           # "coding", "planning", "documentation"
    description: str
    confidence: float = 1.0             # Насколько Runtime хорош в этом (0.0 - 1.0)
    models: List[str***REMOVED*** = field(default_factory=list)  # Какие модели поддерживает


@dataclass
class RuntimeConfig:
    """Конфигурация Runtime."""
    max_concurrent: int = 1
    timeout_seconds: int = 300
    max_retries: int = 3
    env_vars: Dict[str, str***REMOVED*** = field(default_factory=dict)
    args: List[str***REMOVED*** = field(default_factory=list)
    work_dir: Optional[str***REMOVED*** = None
```

### 3.3 Capability-based routing

```python
class RuntimeCapabilityRegistry:
    """Реестр capability для всех Runtime."""

    def list_capabilities(self) -> Dict[str, List[RuntimeCapability***REMOVED******REMOVED***:
        """Все доступные capability: capability_name → [Runtime, ...***REMOVED***"""
        ...

    def get_runtime_for_capability(
        self,
        capability: str,
        preferred_runtime: Optional[str***REMOVED*** = None,
    ) -> Optional[RuntimeDefinition***REMOVED***:
        """Какой Runtime лучше всего подходит для capability."""
        ...

    def score_runtime(
        self,
        runtime: RuntimeDefinition,
        capability: str,
    ) -> float:
        """Оценка Runtime для capability (0.0 - 1.0)."""
        ...
```

### 3.4 Runtime Session

```python
@dataclass
class RuntimeSession:
    """Сессия с конкретным Runtime."""
    runtime: str
    session_id: str
    created_at: datetime
    context: Dict[str, Any***REMOVED***             # Текущий контекст Runtime

    # История взаимодействия
    message_count: int = 0
    token_estimate: int = 0
    last_activity: Optional[datetime***REMOVED*** = None

    # Состояние
    status: SessionStatus = SessionStatus.ACTIVE
    error: Optional[str***REMOVED*** = None
```

---

## 4. Adapter Layer

### 4.1 Базовый класс Adapter

```python
class RuntimeAdapter(ABC):
    """Базовый класс для адаптера конкретного Runtime."""

    def __init__(self, config: RuntimeConfig):
        self.config = config
        self._process: Optional[subprocess.Popen***REMOVED*** = None
        self._session: Optional[RuntimeSession***REMOVED*** = None

    @abstractmethod
    def connect(self) -> bool:
        """Подключиться к Runtime."""
        ...

    @abstractmethod
    def disconnect(self) -> bool:
        """Отключиться от Runtime."""
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        """Проверить подключение."""
        ...

    # Runtime API implementation
    @abstractmethod
    def generate(self, messages, **kwargs) -> RuntimeResult:
        ...

    @abstractmethod
    def generate_stream(self, messages, **kwargs) -> Iterator[RuntimeChunk***REMOVED***:
        ...
```

### 4.2 Типы адаптеров

| Тип адаптера | Транспорт | Пример Runtime |
|-------------|-----------|---------------|
| **stdio_mcp** | STDIO (MCP протокол) | freebuff CLI, Claude Code CLI |
| **mcp_client** | Через MCP Client | Внешний MCP-сервер |
| **subprocess** | Прямой subprocess | freebuff скрипт, Hermes |
| **http_api** | HTTP API (OpenAI-compatible) | Codex API, OpenAI API |
| **bridge** | Через Bridge Layer | ACP-совместимый Runtime |

### 4.3 StdioMCPAdapter

```python
class StdioMCPAdapter(RuntimeAdapter):
    """Адаптер для Runtime, работающих через STDIO MCP протокол.

    Использует существующий StdioMCPClient из bridge_layer.
    """

    def __init__(self, config: RuntimeConfig, command: str, args: List[str***REMOVED***):
        super().__init__(config)
        self._client = StdioMCPClient(
            command=command,
            args=args,
            env=config.env_vars,
        )

    def connect(self) -> bool:
        try:
            result = self._client.initialize()
            return result is not None
        except Exception:
            return False

    def generate(self, messages, **kwargs) -> RuntimeResult:
        # Используем tools/call для генерации
        response = self._client.call_tool(
            "generate",
            {"messages": messages, **kwargs***REMOVED***,
        )
        return RuntimeResult(
            content=response.content,
            runtime="claude-code",
            latency_ms=response.metadata.get("latency_ms", 0),
        )

    def disconnect(self) -> bool:
        self._client.close()
        return True
```

### 4.4 HTTPAdapter

```python
class HTTPAdapter(RuntimeAdapter):
    """Адаптер для Runtime с HTTP API.

    Использует существующий HTTPMCPClient из bridge_layer.
    Поддерживает OpenAI-compatible API.
    """

    def __init__(self, config: RuntimeConfig, endpoint: str, api_key: Optional[str***REMOVED*** = None):
        super().__init__(config)
        self._client = HTTPMCPClient(
            endpoint=endpoint,
            api_key=api_key,
        )

    def connect(self) -> bool:
        # Проверяем доступность эндпоинта
        try:
            self._client.ping()
            return True
        except Exception:
            return False

    def generate(self, messages, **kwargs) -> RuntimeResult:
        start = time.time()
        response = self._client.call_tool("generate", {
            "messages": messages,
            **kwargs,
        ***REMOVED***)
        return RuntimeResult(
            content=response.content,
            runtime="codex",
            latency_ms=int((time.time() - start) * 1000),
        )
```

### 4.5 Adapter Registry

```python
class AdapterRegistry:
    """Реестр адаптеров Runtime."""

    _adapters: Dict[str, Type[RuntimeAdapter***REMOVED******REMOVED*** = {
        "stdio_mcp": StdioMCPAdapter,
        "http": HTTPAdapter,
        "bridge": BridgeAdapter,    # через Bridge Layer
    ***REMOVED***

    def get_adapter(self, adapter_type: str) -> Type[RuntimeAdapter***REMOVED***:
        if adapter_type not in self._adapters:
            raise ValueError(f"Unknown adapter type: {adapter_type***REMOVED***")
        return self._adapters[adapter_type***REMOVED***

    def register_adapter(self, name: str, adapter_cls: Type[RuntimeAdapter***REMOVED***) -> None:
        """Позволяет плагинам регистрировать свои адаптеры."""
        self._adapters[name***REMOVED*** = adapter_cls
```

---

## 5. Поддерживаемые Runtime

### 5.1 Сводная таблица

| Runtime | Тип адаптера | Capabilities | Статус | Установка |
|---------|-------------|-------------|--------|-----------|
| **freebuff (Codebuff)** | stdio_mcp | coding, planning, architecture | 🟡 План | npm / pip |
| **Claude Code** | stdio_mcp | coding, review, architecture, documentation | 🟡 План | npm (`@anthropic/claude-code`) |
| **OpenClaw** | stdio_mcp | coding, research | 🟡 План | git clone + setup |
| **Hermes** | subprocess | coding, planning | 🔴 План | git clone |
| **GPT-4o (OpenAI)** | http | coding, planning, translation | 🟡 План | API ключ |
| **freebuff (Qwen/Ollama)** | http | coding (базовое) | 🟡 План | `ollama pull qwen2.5` |
| **OpenAI Compatible** | http | зависит от модели | 🟡 План | API ключ |
| **Пользовательский Runtime** | bridge / plugins | пользовательские | 💡 Концепция | Plugin SDK |

### 5.2 Freebuff Adapter

```python
class FreebuffAdapter(StdioMCPAdapter):
    """Адаптер для freebuff (Codebuff) CLI.

    RuntimeName: "freebuff"
    Транспорт: MCP STDIO
    Установка: npm install -g @freebuff/cli  или  pip install freebuff
    """

    def __init__(self, config: RuntimeConfig):
        command = self._find_freebuff()
        super().__init__(
            config=config,
            command=command,
            args=["mcp"***REMOVED***,  # Режим MCP сервера
        )

    def _find_freebuff(self) -> str:
        """Ищет freebuff в PATH или npm global."""
        # 1. which freebuff
        # 2. ~/.local/bin/freebuff (wrapper)
        # 3. npm root -g
        # 4. pip show freebuff
        ...

    @property
    def capabilities(self) -> List[RuntimeCapability***REMOVED***:
        return [
            RuntimeCapability("coding", "Code generation and refactoring", 0.95),
            RuntimeCapability("planning", "Task planning and architecture", 0.85),
            RuntimeCapability("research", "Codebase research", 0.80),
        ***REMOVED***
```

### 5.3 Claude Code Adapter

```python
class ClaudeCodeAdapter(StdioMCPAdapter):
    """Адаптер для Claude Code CLI.

    RuntimeName: "claude-code"
    Транспорт: MCP STDIO
    Установка: npm install -g @anthropic/claude-code
    """

    def __init__(self, config: RuntimeConfig):
        super().__init__(
            config=config,
            command="claude",
            args=["mcp"***REMOVED***,  # Режим MCP сервера Claude
        )

    @property
    def capabilities(self) -> List[RuntimeCapability***REMOVED***:
        return [
            RuntimeCapability("coding", "Code generation and review", 0.90),
            RuntimeCapability("review", "Code review and analysis", 0.95),
            RuntimeCapability("architecture", "Architecture and design", 0.85),
            RuntimeCapability("documentation", "Documentation generation", 0.90),
        ***REMOVED***
```

### 5.4 OpenClaw Adapter

```python
class OpenClawAdapter(StdioMCPAdapter):
    """Адаптер для OpenClaw.

    RuntimeName: "openclaw"
    Транспорт: MCP STDIO
    Установка: git clone + pip install
    """

    def __init__(self, config: RuntimeConfig):
        openclaw_path = config.work_dir or os.path.expanduser("~/OpenClaw")
        super().__init__(
            config=config,
            command=sys.executable,
            args=[os.path.join(openclaw_path, "main.py"), "--mcp"***REMOVED***,
        )

    @property
    def capabilities(self) -> List[RuntimeCapability***REMOVED***:
        return [
            RuntimeCapability("coding", "Code generation", 0.70),
            RuntimeCapability("research", "Internet research", 0.85),
        ***REMOVED***
```

### 5.5 Hermes Adapter

```python
class HermesAdapter(RuntimeAdapter):
    """Адаптер для Hermes.

    RuntimeName: "hermes"
    Транспорт: subprocess (прямой запуск)
    Установка: git clone + cargo build

    Hermes — это агент для планирования и исполнения.
    """

    def __init__(self, config: RuntimeConfig):
        super().__init__(config)
        self._hermes_path = config.work_dir or os.path.expanduser("~/Hermes")
        self._binary = os.path.join(self._hermes_path, "target/release/hermes")

    def connect(self) -> bool:
        return os.path.exists(self._binary)

    def generate(self, messages, **kwargs) -> RuntimeResult:
        # Hermes запускается как subprocess с JSON-RPC
        cmd = [self._binary, "run", json.dumps({"messages": messages***REMOVED***)***REMOVED***
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.config.timeout_seconds)
        return RuntimeResult(
            content=result.stdout,
            runtime="hermes",
        )

    @property
    def capabilities(self) -> List[RuntimeCapability***REMOVED***:
        return [
            RuntimeCapability("planning", "Task planning and execution", 0.80),
            RuntimeCapability("coding", "Basic code generation", 0.60),
        ***REMOVED***
```

### 5.6 GPT-4o (OpenAI) Adapter

```python
class GPT4oAdapter(HTTPAdapter):
    """Адаптер для GPT-4o (OpenAI API).

    RuntimeName: "gpt-4o"
    Транспорт: HTTP (OpenAI Assistants / Chat Completions API)
    Установка: только API ключ
    Примечание: Заменяет устаревший Codex API (shut down March 2024).
    Использует GPT-4o / GPT-4o-mini через Chat Completions API.
    """

    def __init__(self, config: RuntimeConfig):
        super().__init__(
            config=config,
            endpoint="https://api.openai.com/v1",
            api_key=config.env_vars.get("OPENAI_API_KEY"),
        )

    @property
    def capabilities(self) -> List[RuntimeCapability***REMOVED***:
        return [
            RuntimeCapability("coding", "Code generation", 0.85),
            RuntimeCapability("translation", "Code translation between languages", 0.90),
            RuntimeCapability("planning", "Task planning", 0.80),
        ***REMOVED***
```

---

## 6. Runtime Registry

### 6.1 RuntimeRegistry

```python
class RuntimeRegistry:
    """Реестр всех Runtime — установленных, доступных, активных."""

    def __init__(self, storage: Optional[Path***REMOVED*** = None):
        self._runtimes: Dict[str, RuntimeDefinition***REMOVED*** = {***REMOVED***
        self._storage = storage or Path("data/runtime_registry.json")

    def register(self, runtime: RuntimeDefinition) -> None:
        """Зарегистрировать Runtime (вручную или авто-обнаружение)."""
        ...

    def unregister(self, name: str) -> None:
        """Удалить Runtime из реестра."""
        ...

    def get(self, name: str) -> Optional[RuntimeDefinition***REMOVED***:
        """Получить Runtime по имени."""
        ...

    def list(self, status: Optional[RuntimeStatus***REMOVED*** = None) -> List[RuntimeDefinition***REMOVED***:
        """Список Runtime, опционально фильтр по статусу."""
        ...

    def discover(self) -> List[RuntimeDefinition***REMOVED***:
        """Авто-обнаружение установленных Runtime.

        Проверяет:
        - which freebuff, which claude, which openclaw
        - npm root -g (@anthropic/claude-code, @freebuff/cli)
        - pip list (freebuff)
        - ~/Hermes/ (бинарник)
        """
        ...

    def set_active(self, name: str) -> None:
        """Установить Runtime как активный по умолчанию."""
        ...

    def get_active(self) -> Optional[RuntimeDefinition***REMOVED***:
        """Получить активный Runtime."""
        ...
```

### 6.2 CLI для пользователя

```bash
# Список всех Runtime (установленных и доступных)
buffy runtime list
# → freebuff  v1.0.0  ✅ active
# → claude-code  v0.1.0  ✅ connected
# → openclaw  —  ❌ not installed

# Подключиться к Runtime
buffy runtime connect claude-code
# → ✅ Connected to claude-code (v0.1.0)

# Отключиться
buffy runtime disconnect claude-code

# Выбрать активный Runtime по умолчанию
buffy runtime use claude-code

# Статус Runtime
buffy runtime status
# → Active: claude-code (connected, 5 messages)
# → Available: freebuff (idle), openclaw (not installed)

# Генерация через выбранный Runtime
buffy run "напиши тест" --runtime claude-code
# или через capability
buffy run "напиши тест" --capability testing
```

### 6.3 Runtime Installer (интеграция с Bootstrap Engine)

```python
class RuntimeInstaller:
    """Управление установкой Runtime.

    Интегрируется с Bootstrap Engine (см. BOOTSTRAP_SPECIFICATION.md).
    """

    def install(self, name: str, version: str = "latest") -> bool:
        """Установить Runtime."""
        ...

    def uninstall(self, name: str) -> bool:
        """Удалить Runtime."""
        ...

    def update(self, name: str) -> bool:
        """Обновить Runtime до последней версии."""
        ...

    def list_available(self) -> List[RuntimeDefinition***REMOVED***:
        """Список Runtime, доступных для установки."""
        ...

    @property
    def install_methods(self) -> Dict[str, Dict[str, Any***REMOVED******REMOVED***:
        return {
            "freebuff": {
                "type": "npm",
                "command": "npm install -g @freebuff/cli",
                "check": "freebuff --version",
            ***REMOVED***,
            "claude-code": {
                "type": "npm",
                "command": "npm install -g @anthropic/claude-code",
                "check": "claude --version",
            ***REMOVED***,
            "openclaw": {
                "type": "git",
                "repo": "https://github.com/openclaw/openclaw.git",
                "command": "git clone && pip install -r requirements.txt",
                "check": "python openclaw/main.py --version",
            ***REMOVED***,
            "hermes": {
                "type": "git",
                "repo": "https://github.com/hermes-ai/hermes.git",
                "command": "git clone && cargo build --release",
                "check": "ls target/release/hermes",
            ***REMOVED***,
        ***REMOVED***
```

### 6.3 Runtime Config (YAML)

```yaml
# ~/.config/buffy/runtimes.yaml
runtimes:
  freebuff:
    enabled: true
    path: auto                     # auto = найти в PATH
    adapter: stdio_mcp
    max_concurrent: 1
    timeout: 300

  claude-code:
    enabled: false
    path: auto
    adapter: stdio_mcp
    max_concurrent: 1
    timeout: 600

  openclaw:
    enabled: true
    path: ~/OpenClaw
    adapter: stdio_mcp
    max_concurrent: 1
    timeout: 120

  codex:
    enabled: false
    adapter: http
    endpoint: https://api.openai.com/v1
    api_key: $OPENAI_API_KEY       # из .env
    model: code-davinci-002

default_runtime: freebuff
```

---

## 7. Интеграция с существующей архитектурой

### 7.1 Связи

```
Runtime Abstraction Layer
  │
  ├── Event Bus ← публикует runtime.* события
  │     ├── runtime.registered
  │     ├── runtime.connected
  │     ├── runtime.disconnected
  │     ├── runtime.error
  │     ├── runtime.generated
  │     └── runtime.health
  │
  ├── Policy Engine → выбирает Runtime по capability
  │     ├── Policy Store → runtime preferences
  │     └── Capability Registry → capability → Runtime mapping
  │
  ├── ModelGateway ← делегирует generate() если Runtime не поддерживает
  │     └── Использует ModelGateway для Runtime без собственной LLM
  │
  ├── Bridge Layer → использует MCP Client для stdio/http Runtime
  │     ├── StdioMCPClient → freebuff, Claude Code, OpenClaw
  │     └── HTTPMCPClient → Codex, OpenAI Compatible
  │
  ├── Bootstrap Engine → Runtime Installer
  │     └── Устанавливает Runtime по профилю
  │
  ├── MCP Server → runtime инструменты
  │     ├── runtime_list → список Runtime
  │     ├── runtime_connect → подключить Runtime
  │     ├── runtime_select → выбрать активный Runtime
  │     └── runtime_generate → генерация через Runtime
  │
  └── ContextManager → Runtime Session
        └── Сохраняет сессии Runtime в context.db
```

### 7.2 Интеграция с Policy Engine

Policy Engine решает: **какой Runtime использовать для задачи**.

```yaml
# Пример политики
runtime:
  default: freebuff
  capability_mapping:
    coding: claude-code
    review: claude-code
    planning: freebuff
    research: openclaw
    documentation: claude-code
    translation: codex
  fallback:
    strategy: next-available
    order: [claude-code, freebuff, openclaw, codex***REMOVED***
```

### 7.3 Регистрация в MCP Server

MCP tools для Runtime Abstraction Layer регистрируются в `scripts/mcp_server.py`
по тому же паттерну, что Bridge Layer и Bootstrap Engine:

```python
def _get_runtime_layer(self) -> RuntimeAbstractionLayer:
    if self._runtime_layer is None:
        from freebuff_plugin.runtime import RuntimeAbstractionLayer
        self._runtime_layer = RuntimeAbstractionLayer(self.workspace)
        self._runtime_layer.start()
    return self._runtime_layer

def _register_tools(self) -> None:
    # ... существующие инструменты ...
    self.tool("runtime_list")(self._handle_runtime_list)
    self.tool("runtime_connect")(self._handle_runtime_connect)
    self.tool("runtime_disconnect")(self._handle_runtime_disconnect)
    self.tool("runtime_select")(self._handle_runtime_select)
    self.tool("runtime_generate")(self._handle_runtime_generate)
```

Каждый инструмент публикует событие в Event Bus (`runtime.*`), консистентно
с `bridge.connected` и `knowledge.searched`.

### 7.4 MCP инструменты

```json
{
    "name": "runtime_list",
    "description": "Список зарегистрированных и активных Runtime",
    "inputSchema": { "status": { "type": "string", "optional": true ***REMOVED*** ***REMOVED***
***REMOVED***
{
    "name": "runtime_connect",
    "description": "Подключиться к Runtime",
    "inputSchema": {
        "name": { "type": "string", "enum": ["freebuff", "claude-code", "openclaw"***REMOVED*** ***REMOVED***
    ***REMOVED***
***REMOVED***
{
    "name": "runtime_disconnect",
    "description": "Отключиться от Runtime",
    "inputSchema": {
        "name": { "type": "string" ***REMOVED***
    ***REMOVED***
***REMOVED***
{
    "name": "runtime_select",
    "description": "Выбрать активный Runtime для генерации",
    "inputSchema": {
        "name": { "type": "string" ***REMOVED***
    ***REMOVED***
***REMOVED***
{
    "name": "runtime_generate",
    "description": "Сгенерировать ответ через выбранный Runtime",
    "inputSchema": {
        "messages": { "type": "array" ***REMOVED***,
        "runtime": { "type": "string", "optional": true ***REMOVED***,
        "capability": { "type": "string", "optional": true ***REMOVED***
    ***REMOVED***
***REMOVED***
```

---

## 8. Профили Runtime

### 8.1 Bootstrap Profiles (из BOOTSTRAP_SPECIFICATION.md)

| Профиль | Какие Runtime подключает |
|---------|------------------------|
| **minimal** | Только текущий (freebuff) |
| **developer** | freebuff + Claude Code |
| **offline** | freebuff (Qwen/Ollama) |
| **cloud** | Любой через API (Codex, Claude API) |
| **android** | freebuff (freebuff) |
| **research** | Все доступные (freebuff + Claude + OpenClaw + Codex) |
| **enterprise** | По политикам |
| **team** | freebuff + Claude |

### 8.2 Runtime API Mapping

Каждый Runtime имеет свои MCP инструменты. RAL маппит их на универсальный Runtime API:

| Runtime | MCP инструменты | Маппинг на Runtime API |
|---------|----------------|------------------------|
| **freebuff** | `generate`, `generate_stream`, `list_models` | Прямой — freebuff поддерживает generate из коробки |
| **Claude Code** | `ClaudeCodeTask.create`, `ClaudeCodeTask.read` | Адаптер создаёт task, ждёт завершения, возвращает результат как `generate()` |
| **OpenClaw** | `research`, `codegen`, `plan` | Адаптер выбирает tool по capability и custom rules |
| **Hermes** | (нет MCP) | MCP-wrapper: обёртка subprocess → stdio JSON-RPC → единый MCP интерфейс |
| **Codex** | (нет MCP) | HTTP API wrapper: OpenAI Assistants API → единый Runtime API |

**Принцип маппинга:**
- Если Runtime поддерживает MCP — используем его MCP инструменты напрямую
- Если Runtime не поддерживает MCP — создаём MCP-wrapper (subprocess → stdio JSON-RPC)
- Адаптер скрывает детали маппинга от RAL

### 8.3 Capability → Runtime Mapping (рекомендованный)

Confidence (`RuntimeCapability.confidence`, 0.0–1.0) определяется комбинацией:
- **Hardcoded baseline** — субъективная оценка автора адаптера (0.5–1.0)
- **Auto-measured** — через Runtime Doctor (запуск тестового промпта, оценка результата)
- **User override** — пользователь может изменить confidence в политиках

| Capability | Лучший Runtime | Confidence | Альтернативы |
|------------|---------------|------------|--------------|
| coding | claude-code | 0.95 | freebuff (0.85), codex (0.80) |
| review | claude-code | 0.95 | freebuff (0.70) |
| planning | freebuff | 0.85 | claude-code (0.80), hermes (0.70) |
| architecture | claude-code | 0.85 | freebuff (0.80) |
| research | openclaw | 0.85 | freebuff (0.70) |
| documentation | claude-code | 0.90 | freebuff (0.75) |
| testing | freebuff | 0.80 | claude-code (0.75) |
| refactoring | freebuff | 0.85 | claude-code (0.80) |
| translation | GPT-4o | 0.90 | claude-code (0.80) |

---

## 9. Потоки данных

### 9.1 Пользователь → Runtime

```
Пользователь
    │
    ▼
freebuff_cli.py "напиши тест для модуля X"
    │
    ▼
Policy Engine → capability("testing") → Runtime("freebuff")
    │
    ▼
Runtime Abstraction Layer → get_runtime("freebuff")
    │
    ▼
FreebuffAdapter → StdioMCPClient("freebuff", ["mcp"***REMOVED***)
    │
    ▼
freebuff process (MCP STDIO)
    │
    ▼
RuntimeResult → пользователь
```

### 9.2 Policy-driven Runtime selection

```
Задача: "проведи code review этого файла"
    │
    ▼
Policy Engine
    │
    ├── 1. Определяем capability: "review"
    ├── 2. Смотрим policy: review → claude-code
    ├── 3. Проверяем доступность claude-code
    │       ├── Connected → используем
    │       └── Not connected → пытаемся connect()
    │           ├── Success → используем
    │           └── Failed → fallback: freebuff
    └── 4. Возвращаем RuntimeDefinition + RuntimeAdapter
    │
    ▼
Runtime Abstraction Layer → generate() через выбранный Runtime
```

### 9.3 Multi-Runtime workflow

```
Workflow: "спланируй архитектуру, напиши код, сделай ревью"

  Шаг 1: planning → freebuff
  Шаг 2: coding  → claude-code
  Шаг 3: review  → claude-code
       │
       ▼
  Все шаги логируются в RuntimeSession
  Результаты сохраняются в Memory → Knowledge Engine
```

---

## 10. Тестирование

### 10.1 Unit-тесты

| Тест | Что проверяет |
|------|--------------|
| `test_adapter_base` | RuntimeAdapter ABC — все методы корректно абстрактны |
| `test_freebuff_adapter` | FreebuffAdapter — поиск бинарника, connect, list_models |
| `test_claude_adapter` | ClaudeCodeAdapter — capabilities, connect |
| `test_openclaw_adapter` | OpenClawAdapter — установка, generate |
| `test_hermes_adapter` | HermesAdapter — subprocess, connect |
| `test_codex_adapter` | CodexAdapter — HTTP, API key validation |
| `test_registry_register` | RuntimeRegistry — register/get/list/unregister |
| `test_registry_discover` | RuntimeRegistry — авто-обнаружение установленных Runtime |
| `test_registry_status` | RuntimeRegistry — жизненный цикл INSTALLED→CONNECTED→ACTIVE |
| `test_capability_routing` | RuntimeCapabilityRegistry — выбор Runtime по capability |
| `test_policy_integration` | Policy Engine + RAL — выбор Runtime по политике |
| `test_mcp_tools` | MCP инструменты runtime_list/connect/select/generate |
| `test_error_fallback` | Graceful fallback при недоступности Runtime |

### 10.2 Boundary тесты

- Runtime не установлен (Registry.discover возвращает пустой список)
- Runtime установлен, но бинарник не найден
- Runtime подключен, но не отвечает (timeout)
- Runtime отвечает, но с ошибкой (MCP error code)
- Два Runtime с одинаковым capability (выбор по confidence)
- Все Runtime отключены (fallback → error)
- RuntimeRegistry с повреждённым JSON storage

### 10.3 Integration тесты

- actual freebuff CLI (если установлен) — end-to-end generate
- actual Claude Code CLI (если установлен) — end-to-end generate
- Runtime Registry + Bootstrap Engine интеграция

---

## 11. Реализация

### 11.1 Файлы

```
freebuff_plugin/runtime/
├── __init__.py              # RuntimeAPI, RuntimeAdapter базовые классы
├── api.py                   # Runtime API протокол
├── adapter.py               # AdapterRegistry + базовый RuntimeAdapter
├── adapters/
│   ├── __init__.py
│   ├── freebuff.py          # FreebuffAdapter
│   ├── claude.py            # ClaudeCodeAdapter
│   ├── openclaw.py          # OpenClawAdapter
│   ├── hermes.py            # HermesAdapter
│   └── codex.py             # CodexAdapter
├── registry.py              # RuntimeRegistry
├── installer.py             # RuntimeInstaller
├── capability.py            # RuntimeCapabilityRegistry
├── session.py               # RuntimeSession
└── config.py                # RuntimeConfig (YAML)
```

### 11.2 Этапы реализации

| Этап | Что | Тестов | Зависимости |
|------|-----|--------|-------------|
| **1. Core API** | RuntimeAPI ABC, RuntimeAdapter ABC, типы данных | 10 | Нет |
| **2. Registry** | RuntimeRegistry, сохранение/загрузка, discover | 12 | Core API |
| **3. Freebuff Adapter** | FreebuffAdapter через StdioMCPClient | 8 | Registry, Bridge Layer (StdioMCPClient) |
| **4. Claude Adapter** | ClaudeCodeAdapter | 8 | Registry, Bridge Layer |
| **5. Capability** | RuntimeCapabilityRegistry, scoring | 10 | Registry |
| **6. MCP tools** | runtime_list/connect/select/generate | 6 | MCP Server |
| **7. Policy integration** | Policy Engine + RAL | 10 | Policy Engine |
| **8. Installer** | RuntimeInstaller + Bootstrap Engine | 8 | Bootstrap Engine |
| **ИТОГО** | | **~72 теста** | |

### 11.3 Приоритет

| Приоритет | Компонент | Обоснование |
|-----------|-----------|-------------|
| P0 | Core API + Freebuff Adapter | База для всей RAL |
| P0 | RuntimeRegistry | discover установленных Runtime |
| P1 | Capability Registry | Нужен для Policy Engine |
| P1 | MCP tools | Нужен для пользователей |
| P2 | Claude/OpenClaw Adapters | Второй приоритет |
| P3 | Policy integration | После Policy Engine |
| P3 | Hermes/Codex Adapters | После основного функционала |

---

## 12. Критерии готовности

- [ ***REMOVED*** `RuntimeAPI` ABC с полным протоколом (generate, generate_stream, list_models, capabilities, ping, health)
- [ ***REMOVED*** `RuntimeAdapter` ABC с connect/disconnect/is_connected
- [ ***REMOVED*** `FreebuffAdapter` — подключается к freebuff freebuff через StdioMCPClient
- [ ***REMOVED*** `ClaudeCodeAdapter` — подключается к freebuff Claude Code
- [ ***REMOVED*** `RuntimeRegistry` — register/get/list/discover/unregister
- [ ***REMOVED*** `RuntimeCapabilityRegistry` — mapping capability → Runtime
- [ ***REMOVED*** MCP tools runtime_list/connect/select/generate
- [ ***REMOVED*** Event Bus события: runtime.registered, runtime.connected, runtime.disconnected, runtime.error
- [ ***REMOVED*** Интеграция с Policy Engine: выбор Runtime по capability
- [ ***REMOVED*** 72+ теста, 0 failures
- [ ***REMOVED*** Документация в README.md

---

## 13. Открытые вопросы

| Вопрос | Статус |
|--------|--------|
| Как быть с Runtime, которые не поддерживают MCP? (например, прямой subprocess) | Использовать subprocess адаптер или оборачивать в MCP-wrapper |
| Claude Code —真的有 MCP режим? | ✅ Да, `claude mcp` запускает MCP сервер |
| OpenClaw — есть MCP режим? | 🟡 Нужно проверить, возможно через Bridge Layer |
| Hermes — какой транспорт? | 🟡 subprocess с JSON-RPC stdio |
| Codex — через OpenAI API? Требует ключ. | ✅ Да, через HTTPAdapter с API key |
| Как быть с Rate Limiting для HTTP Runtime? | RuntimeConfig может содержать rate_limit параметры |
| Должен ли RAL сам выбирать модель внутри Runtime? | Нет, это задача Policy Engine. RAL только передаёт запрос |
| RuntimeSession — в memory или в ContextManager? | 🟡 И то и другое: active session в memory, история в ContextManager |
| Как тестировать адаптеры без установленного Runtime? | Mock-адаптеры, которые симулируют MCP STDIO |

---

*Связанные документы: [VISION_3.0.md***REMOVED***(VISION_3.0.md), [ARCHITECTURE_3.0.md***REMOVED***(ARCHITECTURE_3.0.md), [BOOTSTRAP_SPECIFICATION.md***REMOVED***(BOOTSTRAP_SPECIFICATION.md), [BRIDGE_PLATFORM_SPECIFICATION.md***REMOVED***(BRIDGE_PLATFORM_SPECIFICATION.md) (план), [POLICY_ENGINE_SPECIFICATION.md***REMOVED***(POLICY_ENGINE_SPECIFICATION.md) (план), [scripts/model_gateway.py***REMOVED***(../scripts/model_gateway.py)*
