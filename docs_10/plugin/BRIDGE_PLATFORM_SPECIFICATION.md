# BRIDGE PLATFORM SPECIFICATION — Универсальный слой интеграции

> **Версия:** 1.0.0  
> **Дата:** 2026-07-29  
> **Статус:** ✅ Production (Bridge Layer + ACP + MCP Client — 60 тестов)  
> **Основание:** [VISION_3.0.md***REMOVED***(../vision/VISION_3.0.md), [ARCHITECTURE_3.0.md***REMOVED***(../core/ARCHITECTURE_3.0.md), [014_02_leviathan_arhitektura.md***REMOVED***(../../pompts_11/014_02_leviathan_arhitektura.md) (концепция #22)  

---

## Содержание

1. [Executive Summary***REMOVED***(#1-executive-summary)
2. [Архитектура***REMOVED***(#2-архитектура)
3. [Bridge Layer***REMOVED***(#3-bridge-layer)
4. [ACP Protocol***REMOVED***(#4-acp-protocol)
5. [MCP Client***REMOVED***(#5-mcp-client)
6. [Reverse Bridge***REMOVED***(#6-reverse-bridge)
7. [Интеграция с MCP Server***REMOVED***(#7-интеграция-с-mcp-server)
8. [Потоки данных***REMOVED***(#8-потоки-данных)
9. [Безопасность***REMOVED***(#9-безопасность)
10. [Тестирование***REMOVED***(#10-тестирование)
11. [Реализация***REMOVED***(#11-реализация)
12. [Критерии готовности***REMOVED***(#12-критерии-готовности)
13. [Открытые вопросы***REMOVED***(#13-открытые-вопросы)

---

## 1. Executive Summary

**Bridge Platform** — это набор компонентов Extensions, обеспечивающих
универсальный слой интеграции между AI Runtime, протоколами (MCP, ACP),
внешними сервисами и freebuff агентами.

**Ключевой принцип:** Bridge — это единственная точка интеграции.
Любой внешний сервис, агент или Runtime подключается через Bridge.

### 1.1 Текущий статус

Bridge Platform уже реализована и работает в production:

| Компонент | Файл | Статус | Тесты |
|-----------|------|--------|-------|
| **Bridge Layer** | `freebuff_plugin_03/bridge_layer.py` | ✅ Production | 60 |
| **ACP Protocol** | `freebuff_plugin_03/acp_protocol.py` | ✅ Production | (в составе Bridge) |
| **MCP Client** | `freebuff_plugin_03/mcp_client.py` | ✅ Production | (в составе Bridge) |
| **MCP Server integration** | `scripts_01/mcp_server.py` | ✅ Production | 89 |
| **Reverse Bridge** | — | 💡 План | — |

### 1.2 Что делает Bridge Platform

```
┌─────────────────────────────────────────────────────────────┐
│                     BRIDGE PLATFORM                          │
│                                                             │
│  ┌──────────────────────┐  ┌───────────────────────────┐   │
│  │   MCP ↔ ACP          │  │   Reverse Bridge          │   │
│  │   (Bridge Layer)     │  │   (в плане)               │   │
│  │                      │  │                            │   │
│  │  • connect_mcp_stdio │  │  • ACP → MCP tunnel       │   │
│  │  • connect_mcp_http  │  │  • External → Local       │   │
│  │  • _forward_to_mcp   │  │  • Webhook → Event Bus    │   │
│  │  • _rpc_to_server    │  │  • SSE → ACP              │   │
│  │  • sync + reconnect  │  │                            │   │
│  └──────────────────────┘  └───────────────────────────┘   │
│                                                             │
│  ┌──────────────────────┐  ┌───────────────────────────┐   │
│  │   ACP Protocol       │  │   MCP Client              │   │
│  │                      │  │                            │   │
│  │  • AgentRegistry     │  │  • StdioMCPClient         │   │
│  │  • ACPHandler        │  │  • HTTPMCPClient          │   │
│  │  • discover/task     │  │  • connect/disconnect    │   │
│  │  • broadcast/heart   │  │  • list/call tools       │   │
│  │  • prune offline     │  │  • initialize/ping       │   │
│  └──────────────────────┘  └───────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Архитектура

### 2.1 Общая схема

```
  Внешний мир                        Bridge Platform                freebuff система
  ┌──────────────┐                   ┌────────────────┐            ┌──────────────────┐
  │  External    │  ←── MCP STDIO ── │                │            │  Buffy Core      │
  │  MCP Server  │                   │                │            │  • ContextManager│
  └──────────────┘                   │  Bridge Layer  │  ← ACP →  │  • Memory Engine  │
                                    │                │            │  • Knowledge Eng  │
  ┌──────────────┐                   │  (трансляция)  │            │  • Event Bus      │
  │  Codebuff    │  ←── MCP STDIO ── │                │            └──────────────────┘
  │  (freebuff)  │                   └───────┬────────┘
  └──────────────┘                           │
                                             │ ACP
  ┌──────────────┐                           ▼
  │  Внешние     │                   ┌────────────────┐
  │  ACP-агенты  │  ←── ACP via ────│  Event Bus      │
  │  (Claude,    │      Event Bus   │  (scripts_01/)     │
  │   OpenClaw)  │                   └────────────────┘
  └──────────────┘
                                             │
                    ┌────────────────────────┴──────────────┐
                    ▼                                        ▼
          ┌──────────────────┐                    ┌──────────────────┐
          │  MCP Client      │                    │  ACP Handler     │
          │  (Stdio + HTTP)  │                    │  (AgentRegistry)  │
          └──────────────────┘                    └──────────────────┘
```

### 2.2 Место в архитектуре

Bridge Platform находится в Extensions:

```
MCP Server (Ext) ← Bridge Layer (Ext) ← ACP Protocol (Ext)
     │                      │                      │
     ▼                      ▼                      ▼
External Agents     External MCP Servers     Local ACP Agents
```

### 2.3 Компоненты

| Компонент | Назначение | Транспорт |
|-----------|-----------|-----------|
| **Bridge Layer** | Трансляция MCP ↔ ACP, управление подключениями, sync loop | Event Bus + MCP Client |
| **ACP Protocol** | Протокол кооперации агентов: discover, task/result, broadcast, heartbeat | Event Bus |
| **MCP Client** | Клиент для внешних MCP-серверов: stdio + HTTP | STDIO / HTTP |
| **Reverse Bridge** | Обратная интеграция: внешние события → ACP → freebuff агенты (план) | Webhook / SSE |
| **MCP Server integration** | bridge_connect/list/disconnect/rpc инструменты | MCP Server |

---

## 3. Bridge Layer

### 3.1 Текущая реализация

Bridge Layer — главный компонент, реализованный в `freebuff_plugin_03/bridge_layer.py`.

**Архитектура:**

```
BridgeLayer
  │
  ├── ACPHandler (acp_protocol.py) — подписка на ACP события
  ├── AgentRegistry (acp_protocol.py) — реестр агентов
  │
  ├── MCP Servers (Dict[name, BridgeMCPServer***REMOVED***)
  │   ├── client: MCPClientBase
  │   ├── tools: List[MCPToolInfo***REMOVED***
  │   ├── type: "stdio" | "http"
  │   └── connection_params: Dict — для reconnect
  │
  ├── Sync Thread — ping + reconnect + prune каждые 60s
  │
  └── ACP Capabilities:
      ├── bridge.list_servers
      ├── bridge.connect_stdio
      ├── bridge.connect_http
      ├── bridge.disconnect
      ├── bridge.rpc
      └── bridge.forward
```

**Ключевые методы:**

```python
class BridgeLayer:
    # ——— Lifecycle ———
    def start(self) -> None
    def stop(self) -> None

    # ——— MCP Connection Management ———
    def connect_mcp_stdio(command, args, cwd, name) -> Dict
    def connect_mcp_http(endpoint, name) -> Dict
    def disconnect_mcp(name) -> bool
    def list_mcp_servers() -> List[Dict***REMOVED***

    # ——— MCP ↔ ACP Translation ———
    def _forward_to_mcp(server_name, tool_name, arguments) -> Dict
    def _rpc_to_server(server_name, method, params) -> Dict
    def _handle_acp_task_on_mcp(task) -> ACPResult

    # ——— Sync ———
    def _sync_loop()           # ping каждые 60s
    def _reconnect_mcp(name) -> bool  # reconnect через connection_params

    # ——— ACP Integration ———
    def register_acp_tool_handler(tool_name, handler)
    def send_acp_broadcast(message, data)
    def send_acp_task(target, tool, arguments, timeout) -> ACPResult
```

### 3.2 BridgeMCPServer

```python
@dataclass
class BridgeMCPServer:
    name: str                     # "local-mcp", "codebuff"
    client: MCPClientBase         # StdioMCPClient | HTTPMCPClient
    type: str                     # "stdio" | "http"
    tools: List[MCPToolInfo***REMOVED***      # инструменты сервера
    resources: List[Any***REMOVED***          # ресурсы сервера
    connected_at: float           # timestamp подключения
    last_ping: float              # последний успешный ping
    error: Optional[str***REMOVED***          # последняя ошибка
    connection_params: Dict       # параметры для reconnect
```

### 3.3 Sync Loop

```
_sync_loop():
  while running:
    sleep(60)
    for each MCP server:
      ping()
      if alive → update last_ping
      if dead → reconnect() через connection_params
    prune_offline ACP agents (>300s)
```

### 3.4 Reconnect Mechanism

При падении MCP сервера Bridge Layer автоматически переподключается,
используя сохранённые `connection_params`:

```python
def _reconnect_mcp(self, server_name: str) -> bool:
    # 1. Берём server.connection_params
    # 2. Создаём новый StdioMCPClient / HTTPMCPClient
    # 3. new_client.connect()
    # 4. Обновляем server.client + server.tools
    # 5. Пытаемся old_client.disconnect()
```

---

## 4. ACP Protocol

### 4.1 Agent Collaboration Protocol

ACP — собственный протокол кооперации AI-агентов, построенный на Event Bus.

**Типы событий:**

| Событие | Направление | Описание |
|---------|-------------|----------|
| `acp.discover` | broadcast | Запрос/ответ списка агентов |
| `acp.task` | directed | Отправить задачу агенту |
| `acp.result` | directed | Результат выполнения задачи |
| `acp.broadcast` | broadcast | Широковещательное сообщение |
| `acp.status` | broadcast | Обновление статуса агента |
| `acp.heartbeat` | broadcast | Heartbeat (каждые 30s) |
| `acp.error` | directed | Ошибка |

### 4.2 AgentRegistry

```python
class AgentRegistry:
    # ——— Agent Management ———
    def register(info: AgentInfo)
    def unregister(name: str) -> bool
    def get(name: str) -> Optional[AgentInfo***REMOVED***
    def list_agents(status) -> List[AgentInfo***REMOVED***
    def update_status(name, status) -> bool
    def prune_offline(max_age_seconds) -> int

    # ——— Task Management ———
    def register_pending_task(task: ACPTask)
    def complete_task(result: ACPResult)
    def wait_for_result(task_id, timeout) -> ACPResult
```

### 4.3 Agent Lifecycle

```
REGISTERED → ONLINE → BUSY → ONLINE → OFFLINE
                │                      │
                ▼                      ▼
            ERROR → ONLINE         PRUNE (>300s)
```

### 4.4 ACPHandler

```python
class ACPHandler:
    # ——— Подписка ———
    # acp.discover, acp.task, acp.result, acp.broadcast, acp.status, acp.heartbeat
    # self._bus.subscribe(event_type, self._on_acp_event)

    # ——— Обработка ———
    # _handle_discover  — отвечает своей информацией
    # _handle_task      — вызывает _tool_handlers[tool***REMOVED***
    # _handle_result    — сохраняет в registry
    # _handle_status    — регистрирует агента
    # _handle_broadcast — переопределяемый хук on_broadcast()
    # _handle_heartbeat — обновляет last_seen

    # ——— Отправка ———
    def send_task(target, tool, arguments, timeout) -> ACPResult
    def send_broadcast(message, data)
    def send_discover()

    # ——— Heartbeat ———
    # _heartbeat_loop() — publish acp.heartbeat каждые 30s
```

**Фильтрация своих сообщений:**

```python
def _on_acp_event(self, event):
    if event.source == self._agent_name:
        return  # не обрабатываем свои сообщения
```

---

## 5. MCP Client

### 5.1 MCPClientBase

```python
class MCPClientBase:
    def connect() -> bool           # initialize handshake
    def disconnect() -> None
    def initialize() -> Dict        # protocol version handshake
    def ping() -> bool              # keepalive
    def list_tools() -> List[MCPToolInfo***REMOVED***
    def call_tool(name, arguments) -> MCPCallResult
    def list_resources() -> List[MCPResourceInfo***REMOVED***
    def read_resource(uri) -> str
    def list_prompts() -> List[Dict***REMOVED***
    def get_prompt(name, args) -> str
```

### 5.2 StdioMCPClient

**Транспорт:** subprocess stdin/stdout (JSON-RPC 2.0)

```python
class StdioMCPClient(MCPClientBase):
    def __init__(self, command, args, cwd, env, name):
        # subprocess.Popen(stdin=PIPE, stdout=PIPE)
        # _reader_thread — читает stdout, кладёт в Queue
        # _active_request_ids — отслеживает req_id
```

**Reader loop:**

```
_reader_loop():
  for line in process.stdout:
    json.loads(line) → _response_queue.put(response)
```

**Request flow:**

```
_send_request(method, params):
  1. _next_id() → req_id
  2. JSON-RPC запрос → process.stdin
  3. _response_queue.get(timeout=30)
  4. Проверка id == req_id
  5. Отбрасывание ответов с незнакомыми ID
```

### 5.3 HTTPMCPClient

**Транспорт:** HTTP POST/GET/DELETE

```python
class HTTPMCPClient(MCPClientBase):
    def __init__(self, endpoint, name):
        # self._endpoint
        # self._session_id из заголовка Mcp-Session-Id
```

**Protocol:** MCP Streamable HTTP 2025-03-26

```
POST /mcp → JSON-RPC запрос → JSON-RPC ответ
DELETE /mcp → завершение сессии
Headers: Mcp-Protocol-Version, Mcp-Session-Id
```

---

## 6. Reverse Bridge

### 6.1 Концепция

**Reverse Bridge** — это обратная интеграция: внешние события, вебхуки и SSE
транслируются в ACP задачи для freebuff агентов.

```
Внешний сервис → Webhook → Reverse Bridge → ACP Task → freebuff агент
Внешний сервис → SSE     → Reverse Bridge → ACP Task → freebuff агент
```

### 6.2 Сценарии

| Сценарий | Описание |
|----------|----------|
| **Webhook → Agent** | Внешний сервис (GitHub, GitLab) отправляет webhook → Bridge создаёт ACP задачу |
| **SSE → Broadcast** | Внешний event stream → Bridge транслирует в ACP broadcast |
| **External MCP → ACP** | Внешний MCP сервер инициирует запрос → Bridge конвертирует в ACP задачу |
| **Cloud → Local** | Облачный агент отправляет задачу → Bridge доставляет freebuff агенту |

### 6.3 Архитектура

```python
class ReverseBridge:
    """Обратный мост: внешние события → ACP."""

    def __init__(self, event_bus, bridge_layer):
        self._bus = event_bus
        self._bridge = bridge_layer
        self._handlers: Dict[str, Callable***REMOVED*** = {***REMOVED***

    # ——— Webhook Server ———
    def start_webhook_server(self, port: int = 8766) -> None:
        """Запускает HTTP сервер для приёма вебхуков."""
        # POST /webhook/{name***REMOVED*** → _handle_webhook(name, data)

    def register_webhook(self, name: str, handler: Callable) -> None:
        """Регистрирует обработчик вебхука."""
        # handler(data) → ACPTask

    # ——— SSE Client ———
    def connect_sse(self, url: str, event_types: List[str***REMOVED***) -> None:
        """Подключается к внешнему SSE потоку."""
        # SSE event → ACP broadcast или ACP task

    # ——— External MCP → ACP ———
    def register_external_trigger(self, mcp_server: str, tool: str, callback: Callable) -> None:
        """Регистрирует триггер: внешний MCP вызов → ACP задача."""
        # MCP сервер вызывает tool → Bridge конвертирует в ACP задачу
```

### 6.4 Webhook → ACP Task

```python
# Пример: GitHub webhook → ACP задача
reverse_bridge.register_webhook("github-push", lambda data: {
    "capability": "review",
    "target": "claude-agent",
    "arguments": {
        "repo": data["repository"***REMOVED***["full_name"***REMOVED***,
        "commit": data["after"***REMOVED***,
    ***REMOVED***
***REMOVED***)
```

### 6.5 SSE → ACP Broadcast

```python
# Пример: Внешний SSE поток → ACP broadcast
reverse_bridge.connect_sse(
    url="https://api.example.com/events",
    event_types=["task.created", "task.completed"***REMOVED***,
)
# SSE "task.created" → ACP broadcast "Новая задача от внешнего сервиса"
```

---

## 7. Интеграция с MCP Server

### 7.1 Bridge инструменты

Bridge Layer уже интегрирован в MCP Server через 4 инструмента:

```python
# В scripts_01/mcp_server.py
def _get_bridge_layer(self) -> BridgeLayer:
    if self._bridge_layer is None:
        from freebuff_plugin.bridge_layer import BridgeLayer
        self._bridge_layer = BridgeLayer(self._bus)
        self._bridge_layer.start()
    return self._bridge_layer

def _register_tools(self):
    self.tool("bridge_connect")(self._handle_bridge_connect)
    self.tool("bridge_list")(self._handle_bridge_list)
    self.tool("bridge_disconnect")(self._handle_bridge_disconnect)
    self.tool("bridge_rpc")(self._handle_bridge_rpc)
```

**Инструменты:**

```json
{
    "bridge_connect": {
        "description": "Подключить внешний MCP сервер",
        "params": {
            "type": { "enum": ["stdio", "http"***REMOVED*** ***REMOVED***,
            "command": { "type": "string" ***REMOVED***,
            "args": { "type": "string" ***REMOVED***,
            "endpoint": { "type": "string" ***REMOVED***
        ***REMOVED***
    ***REMOVED***,
    "bridge_list": {
        "description": "Список подключённых MCP серверов"
    ***REMOVED***,
    "bridge_disconnect": {
        "description": "Отключить MCP сервер",
        "params": { "name": { "type": "string" ***REMOVED*** ***REMOVED***
    ***REMOVED***,
    "bridge_rpc": {
        "description": "JSON-RPC к подключённому серверу",
        "params": {
            "server": { "type": "string" ***REMOVED***,
            "method": { "type": "string" ***REMOVED***,
            "arguments": { "type": "string" ***REMOVED***
        ***REMOVED***
    ***REMOVED***
***REMOVED***
```

### 7.2 Event Bus публикация

Все bridge операции публикуют события в Event Bus:

| Событие | Когда |
|---------|-------|
| `bridge.connected` | MCP сервер подключён |
| `bridge.disconnected` | MCP сервер отключён |
| `bridge.rpc` | Выполнен RPC запрос |
| `bridge.error` | Ошибка bridge |

---

## 8. Потоки данных

### 8.1 ACP → MCP

```
Agent A → send_task("buffy-bridge", "mcp.server_name.tool_name", args)
    │
    ▼
ACPHandler._on_acp_event(acp.task)
    │
    ├── Проверка: target == "buffy-bridge" ?
    ├── Да → _handle_acp_task_on_mcp(task)
    │       │
    │       ├── Парсинг: "mcp.server_name.tool_name" → server + tool
    │       ├── _forward_to_mcp(server, tool, args)
    │       │       │
    │       │       ├── BridgeMCPServer.client.call_tool(tool, args)
    │       │       └── MCPCallResult → Dict response
    │       │
    │       └── ACPResult → publish(acp.result)
    │
    └── Нет → ищем freebuff tool handler
```

### 8.2 MCP → ACP

```
External MCP Server → connect_mcp_stdio()
    │
    ▼
Bridge Layer
    │
    ├── list_tools() от MCP сервера
    ├── register_capability("mcp.{server***REMOVED***.{tool***REMOVED***", desc) в ACP
    │
    ▼
Agent B может отправить задачу: send_task("mcp.{server***REMOVED***.{tool***REMOVED***", args)
    │
    ▼
Bridge Layer → _forward_to_mcp(server, tool, args)
```

### 8.3 Sync & Reconnect

```
_sync_loop: [каждые 60s***REMOVED***
    │
    ├── for each MCP server:
    │   ├── ping()
    │   ├── alive → update last_ping, clear error
    │   └── dead → _reconnect_mcp(name)
    │       │
    │       ├── Создать новый клиент из connection_params
    │       ├── new_client.connect()
    │       ├── Обновить server.client, server.tools
    │       └── old_client.disconnect() (best effort)
    │
    └── _registry.prune_offline(max_age=300s)
```

---

## 9. Безопасность

### 9.1 Ограничения доступа

| Аспект | Текущее состояние | Рекомендация |
|--------|------------------|-------------|
| **MCP STDIO** | Запуск произвольных команд | Ограничить список разрешённых команд |
| **MCP HTTP** | Подключение к любому endpoint | Валидация endpoint по белому списку |
| **ACP доступ** | Любой агент может отправлять задачи | ACP авторизация (agent → allowed tools) |
| **Webhook** | Не реализован | Требует API ключа при реализации |
| **SSE** | Не реализован | Требует аутентификации |

### 9.2 Изоляция процессов

```python
# StdioMCPClient — subprocess с ограничениями:
subprocess.Popen(
    full_cmd,
    cwd=self._cwd,          # ограничение рабочей директории
    env=self._env,           # контроль переменных окружения
)
```

### 9.3 Timeout защита

```python
MCP_REQUEST_TIMEOUT = 30.0  # таймаут запроса
# _send_request: while time.time() < deadline
# _reconnect: try/except с timeout
```

---

## 10. Тестирование

### 10.1 Текущее покрытие (60 тестов)

| Группа | Тестов | Что тестируется |
|--------|--------|-----------------|
| AgentRegistry | 15 | register, unregister, get, list, prune, pending tasks |
| ACPHandler | 12 | task dispatch, result handling, capabilities, heartbeat |
| BridgeLayer | 21 | connect_mcp_stdio, connect_mcp_http, forward, rpc, reconnect |
| MCP Client (stdio) | 8 | connect, disconnect, list_tools, call_tool, ping |
| Edge Cases | 4 | reconnect with invalid params, timeout, unknown server |

### 10.2 Планируемые тесты

| Тест | Описание |
|------|----------|
| `test_reverse_bridge_webhook` | Webhook → ACP task |
| `test_reverse_bridge_sse` | SSE → ACP broadcast |
| `test_bridge_authorization` | ACP авторизация доступа к инструментам |
| `test_bridge_concurrent` | Параллельные запросы к разным MCP серверам |
| `test_bridge_reconnect_persistence` | Reconnect после падения сервера |

---

## 11. Реализация

### 11.1 Что уже реализовано

```
freebuff_plugin_03/
├── bridge_layer.py       ✅ 500 строк — Bridge Layer (60 тестов)
├── acp_protocol.py       ✅ 500 строк — ACP Protocol
├── mcp_client.py         ✅ 500 строк — MCP Client (stdio + HTTP)

scripts_01/
├── sdk_bridge.py         ✅ SDK Bridge (SmartRouter → termux-agent)
├── mcp_server.py         ✅ bridge_connect/list/disconnect/rpc

scripts_01/
├── mcp_server.py         ✅ bridge_connect/list/disconnect/rpc

tests_09/
├── test_bridge_layer.py  ✅ 60 тестов
```

### 11.2 Что нужно реализовать

| Компонент | Приоритет | Тестов |
|-----------|-----------|--------|
| **Reverse Bridge** | P1 | 10 |
| **Webhook Server** | P2 | 8 |
| **SSE Client** | P2 | 6 |
| **ACP Authorization** | P1 | 8 |
| **Bridge metrics** | P3 | 4 |
| **ИТОГО** | | **~36 новых тестов** |

### 11.3 Этапы

| Этап | Что | Тестов | Зависимости |
|------|-----|--------|-------------|
| **0. Текущее** | Bridge Layer + ACP + MCP Client | 60 | — |
| **1. Reverse Bridge** | Webhook → ACP, SSE → ACP | 16 | Bridge Layer |
| **2. Безопасность** | ACP авторизация, валидация endpoint | 10 | Reverse Bridge |
| **3. Метрики** | Статистика bridge, мониторинг | 6 | Всё |
| **4. Reverse MCP** | External MCP → ACP (полный цикл) | 10 | Этапы 1-2 |
| **ИТОГО** | | **~96 тестов** | |

### 11.4 Приоритет

| Приоритет | Компонент | Обоснование |
|-----------|-----------|-------------|
| P0 | Текущая реализация | ✅ Уже работает |
| P1 | Reverse Bridge | Необходим для внешней интеграции |
| P1 | ACP Authorization | Безопасность |
| P2 | Webhook Server | Интеграция с GitHub/GitLab |
| P2 | SSE Client | Event streams |
| P3 | Bridge metrics | Мониторинг |

---

## 12. Критерии готовности

- [x***REMOVED*** Bridge Layer — connect_mcp_stdio, connect_mcp_http, disconnect, list
- [x***REMOVED*** ACP Protocol — AgentRegistry, ACPHandler, discover/task/result/broadcast/heartbeat
- [x***REMOVED*** MCP Client — StdioMCPClient + HTTPMCPClient, connect/list/call/ping
- [x***REMOVED*** MCP Server integration — bridge_connect/list/disconnect/rpc инструменты
- [x***REMOVED*** Event Bus — bridge.connected, bridge.disconnected, bridge.rpc
- [x***REMOVED*** Sync Loop — ping каждые 60s, reconnect через connection_params
- [x***REMOVED*** 60 тестов, 0 failures

### План

- [ ***REMOVED*** **Reverse Bridge** — webhook → ACP task, SSE → ACP broadcast
- [ ***REMOVED*** **ACP Authorization** — контроль доступа к инструментам
- [ ***REMOVED*** **Bridge metrics** — статистика bridge операций
- [ ***REMOVED*** **96+ тестов**, 0 failures

---

## 13. Открытые вопросы

| Вопрос | Статус |
|--------|--------|
| Должен ли MCP Client быть Core или Extension? | 🟡 Прагматическое исключение (см. RUNTIME_ABSTRACTION_SPEC §1.1) |
| ACP авторизация — ACL или JWT? | 🟡 ACL (проще для freebuff сети) |
| Reverse Bridge — отдельный процесс или поток? | 🟡 Поток в BridgeLayer (как sync_loop) |
| SSE reconnection policy? | 🔴 Exponential backoff (1s → 2s → 4s → 30s max) |
| Webhook signature verification? | 🔴 HMAC-SHA256 для GitHub/GitLab |

---

*Связанные документы: [VISION_3.0.md***REMOVED***(../vision/VISION_3.0.md), [ARCHITECTURE_3.0.md***REMOVED***(../core/ARCHITECTURE_3.0.md), [RUNTIME_ABSTRACTION_SPECIFICATION.md***REMOVED***(../core/RUNTIME_ABSTRACTION_SPECIFICATION.md), [POLICY_ENGINE_SPECIFICATION.md***REMOVED***(../core/POLICY_ENGINE_SPECIFICATION.md), [freebuff_plugin_03/bridge_layer.py***REMOVED***(../../freebuff_plugin_03/bridge_layer.py), [freebuff_plugin_03/acp_protocol.py***REMOVED***(../../freebuff_plugin_03/acp_protocol.py), [freebuff_plugin_03/mcp_client.py***REMOVED***(../../freebuff_plugin_03/mcp_client.py)*
