# API Reference

> **Актуальность:** 2026-07-28
> **Модули:** `scripts.agent_context_bridge`, `src.workers.lightpanda_worker`

---

## Agent Context Bridge

### `get_context_bridge() -> AgentContextBridge`

Возвращает модуль-синглтон моста.

### `AgentContextBridge`

#### `ensure_session(project: str = "", topic: str = "") -> str`
Восстанавливает активную сессию `termux-ai-agent` или создаёт новую.

#### `log_user(text: str) -> None`
Логирует сообщение пользователя.

#### `log_assistant(response: Dict[str, Any***REMOVED***) -> None`
Логирует компактную версию ответа ассистента.

#### `log_error(error: Exception) -> None`
Логирует ошибку как `system` сообщение.

#### `checkpoint(summary: str) -> None`
Создаёт ручной чекпоинт.

#### `auto_conspect() -> Optional[str***REMOVED***`
Завершает сессию, сохраняет конспект и возвращает путь к файлу.

---

## Lightpanda Worker

### `LightpandaWorker(binary_path: Optional[str***REMOVED*** = None, workspace_root: Optional[str***REMOVED*** = None)`

Инициализация:
- `binary_path` — явный путь к бинарю/wrapper.
- `workspace_root` — корень freebuff (для поиска `.tools/lightpanda`).

### `LightpandaResult`

```python
@dataclass
class LightpandaResult:
    success: bool
    data: str = ""
    error: Optional[str***REMOVED*** = None
    command: str = ""
    duration_ms: float = 0.0
```

### Методы

#### `execute_agent_task(task: str, provider: str = "ollama", timeout: int = 120) -> LightpandaResult`
Запускает Lightpanda Agent Mode.

#### `run_script(script_path: str, timeout: int = 60) -> LightpandaResult`
Запускает PandaScript файл.

#### `dump_url(url: str, output_format: str = "markdown", timeout: int = 60) -> LightpandaResult`
Получает содержимое URL в формате `markdown`, `html` или `text`.

#### `serve_cdp(host: str = "127.0.0.1", port: int = 9222) -> LightpandaResult`
Запускает CDP-сервер в фоновом процессе.

#### `stop_cdp() -> LightpandaResult`
Останавливает фоновый CDP-сервер.
