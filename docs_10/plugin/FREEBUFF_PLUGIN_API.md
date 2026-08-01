# Freebuff Plugin — API Reference

> **REST:** http://127.0.0.1:8410  
> **MCP:** stdio / sse :8411  
> **Swagger UI:** http://127.0.0.1:8410/docs

---

## 1. REST API (FastAPI)

### 1.1 Статус системы

```http
GET /status
```

**Ответ:**
```json
{
  "plugin": "freebuff-plugin",
  "version": "0.1.0",
  "active_tasks": 1,
  "tasks": [
    {"pid": 12345, "sid": "a1b2c3d4", "cwd": "/storage/emulated/0/PROJECTS/workstation/freebuff"***REMOVED***
  ***REMOVED***,
  "freebuff_binary_exists": true
***REMOVED***
```

**Пример:**
```bash
curl http://127.0.0.1:8410/status | python3 -m json.tool
```

---

### 1.2 Чат (авто-роутинг)

```http
POST /chat
Content-Type: application/json
```

**Тело запроса:**
```json
{
  "message": "напиши парсер JSON",
  "topic": "парсер",         // опционально
  "force_freebuff": false    // принудительно freebuff, игнорируя роутер
***REMOVED***
```

**Ответ (freebuff — задача запущена):**
```json
{
  "session_id": "a1b2c3d4",
  "routed_to": "freebuff",
  "response": "Задача запущена (session: a1b2c3d4, PID: 12345)\nСтатус: launched\nПроверить: GET /status",
  "duration": 0.5
***REMOVED***
```

**Ответ (freebuff — Qwen 0.5B):**
```json
{
  "session_id": "local",
  "routed_to": "local_qwen",
  "response": "Привет! Чем могу помочь?",
  "duration": 0.3
***REMOVED***
```

**Примеры:**
```bash
# Сложная задача → freebuff
curl -X POST http://127.0.0.1:8410/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"напиши парсер для сайта example.com"***REMOVED***'

# Простой запрос → Qwen freebuff
curl -X POST http://127.0.0.1:8410/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"привет"***REMOVED***'

# Принудительно freebuff
curl -X POST http://127.0.0.1:8410/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"как дела", "force_freebuff":true***REMOVED***'
```

---

### 1.3 Управление сессиями

```http
POST /session?action=start&topic=моя тема
```

**Параметры:**

| Параметр | Значение | Описание |
|----------|----------|----------|
| `action` | `start` / `end` | Действие |
| `topic` | строка | Тема сессии |
| `summary` | строка | Описание завершения |

**Ответ (start):**
```json
{"status": "started", "session_id": "a1b2c3d4"***REMOVED***
```

**Ответ (end):**
```json
{
  "status": "ended",
  "session_id": "a1b2c3d4",
  "conspect_path": "/storage/.../context_12/summaries/conspect_topic_2026-07-29.md"
***REMOVED***
```

**Пример:**
```bash
# Начать
curl -X POST "http://127.0.0.1:8410/session?action=start&topic=debug"

# Завершить
curl -X POST "http://127.0.0.1:8410/session?action=end&summary=debug%20OK"
```

---

### 1.4 Запуск freebuff

```http
POST /freebuff/run
Content-Type: application/json
```

**Тело запроса:**
```json
{
  "task": "рефакторинг модуля X",
  "topic": "рефакторинг",     // опционально
  "timeout": 300               // таймаут в секундах, по умолч. 300
***REMOVED***
```

**Ответ:**
```json
{
  "session_id": "a1b2c3d4",
  "success": true,
  "pid": 12345,
  "status": "launched",
  "message": "Codebuff запущен через tmux, промпт передан в monitor.sh."
***REMOVED***
```

**Пример:**
```bash
curl -X POST http://127.0.0.1:8410/freebuff/run \
  -H "Content-Type: application/json" \
  -d '{"task":"создай файл test.py с функцией hello"***REMOVED***'
```

---

### 1.5 Контекст

```http
GET /context
```

**Ответ:**
```json
{
  "conspect": "# Конспект сессии...",
  "has_conspect": true
***REMOVED***
```

---

### 1.6 Активные задачи

```http
GET /tasks
```

**Ответ:**
```json
[
  {"pid": 12345, "sid": "a1b2c3d4", "cwd": "/storage/emulated/0/..."***REMOVED***,
  {"pid": 12346, "sid": "e5f6g7h8", "cwd": "/storage/emulated/0/..."***REMOVED***
***REMOVED***
```

---

### 1.7 Сценарии (Scenario Engine)

#### Список сценариев

```http
GET /scenarios
GET /scenarios?category=freelancing
GET /scenarios?tag=telegram
```

**Ответ:**
```json
{
  "scenarios": [
    {
      "slug": "freelance_parser",
      "title": "Парсер сайта",
      "category": "freelancing",
      "complexity": "средняя",
      "description": "Разработка парсера для извлечения данных с веб-сайта...",
      "tags": ["parser", "scraper", "bs4"***REMOVED***,
      "has_template": true,
      "metadata": {***REMOVED***
    ***REMOVED***
  ***REMOVED***,
  "total": 1
***REMOVED***
```

#### Поиск сценариев

```http
GET /scenarios/search?q=telegram
```

**Ответ:**
```json
{
  "results": [
    {
      "slug": "freelance_tg_bot",
      "title": "Telegram бот",
      "category": "freelancing",
      "tags": ["telegram", "bot"***REMOVED***,
      "has_template": true
    ***REMOVED***
  ***REMOVED***
***REMOVED***
```

#### Детали сценария

```http
GET /scenarios/{slug***REMOVED***
```

**Ответ:**
```json
{
  "slug": "freelance_parser",
  "title": "Парсер сайта",
  "category": "freelancing",
  "complexity": "средняя",
  "description": "Разработка парсера для извлечения данных с веб-сайта...",
  "tags": ["parser", "scraper", "bs4"***REMOVED***,
  "has_template": true,
  "metadata": {***REMOVED***
***REMOVED***
```

#### Применить сценарий

```http
POST /scenarios/{slug***REMOVED***/apply
Content-Type: application/json
```

**Тело запроса:**
```json
{
  "variables": {
    "URL": "https://example.com",
    "поле1": "название",
    "поле2": "цена",
    "поле3": "описание",
    "формат": "JSON"
  ***REMOVED***
***REMOVED***
```

**Ответ:**
```json
{
  "slug": "freelance_parser",
  "title": "Парсер сайта",
  "category": "freelancing",
  "prompt": "Разработай парсер для сайта https://example.com...\n\nТребования:\n...",
  "variables": {"URL": "https://example.com", ...***REMOVED***,
  "has_template": true
***REMOVED***
```

**Пример:**
```bash
# Список всех сценариев
curl http://127.0.0.1:8410/scenarios

# Детали парсера
curl http://127.0.0.1:8410/scenarios/freelance_parser

# Применить сценарий с переменными
curl -X POST http://127.0.0.1:8410/scenarios/freelance_parser/apply \
  -H "Content-Type: application/json" \
  -d '{"variables":{"URL":"https://example.com","поле1":"title","поле2":"price","формат":"JSON"***REMOVED******REMOVED***'

# Поиск по тегу
curl "http://127.0.0.1:8410/scenarios/search?q=telegram"
```

---

## 2. MCP Протокол

### 2.1 Подключение

**STDIO (рекомендуется):**
```bash
python3 freebuff_plugin_03/mcp_server.py --transport stdio
```

**SSE (HTTP):**
```bash
python3 freebuff_plugin_03/mcp_server.py --transport sse --port 8411
```

### 2.2 Инструменты

#### Базовые (7 шт.)

##### `start_session`
Начать новую стрим-сессию с памятью.

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "start_session",
    "arguments": {"topic": "debug session"***REMOVED***
  ***REMOVED***
***REMOVED***
// Response: {"session_id": "a1b2c3d4", "topic": "debug session", "status": "started"***REMOVED***
```

##### `log_message`
Записать сообщение в текущую сессию.

```json
{
  "name": "log_message",
  "arguments": {
    "role": "user",
    "content": "напиши парсер",
    "session_id": "a1b2c3d4"  // опционально
  ***REMOVED***
***REMOVED***
// Response: {"role": "user", "session_id": "a1b2c3d4", "status": "logged"***REMOVED***
```

`role`: `"user"`, `"assistant"`, `"system"`

##### `get_context`
Конспект последней завершённой сессии.

```json
{"name": "get_context"***REMOVED***
// Response: (markdown text)
```

##### `get_status`
Статус системы и активных задач.

```json
{"name": "get_status"***REMOVED***
// Response: {"session_active": true, "session_id": "a1b2c3d4", "active_tasks": 1, "tasks": [...***REMOVED******REMOVED***
```

##### `run_freebuff`
Запустить Codebuff phase-based.

```json
{
  "name": "run_freebuff",
  "arguments": {
    "task": "рефакторинг модуля X",
    "topic": "рефакторинг",
    "timeout": 300
  ***REMOVED***
***REMOVED***
// Response: {"success": true, "session_id": "a1b2c3d4", "pid": 12345, "status": "launched"***REMOVED***
```

##### `get_task_result`
Проверить результат запущенной задачи.

```json
{
  "name": "get_task_result",
  "arguments": {"session_id": "a1b2c3d4"***REMOVED***
***REMOVED***
// Если выполняется:
//   {"session_id": "a1b2c3d4", "running": true, "pid": 12345, "cwd": "..."***REMOVED***
// Если завершена:
//   {"session_id": "a1b2c3d4", "running": false, "conspect": "..."***REMOVED***
```

##### `end_session`
Завершить сессию с конспектом.

```json
{
  "name": "end_session",
  "arguments": {"summary": "Session completed"***REMOVED***
***REMOVED***
// Response: {"status": "ended", "conspect_path": "..."***REMOVED***
```

---

#### Сценарии (4 шт.)

##### `list_scenarios`
Список сценариев с фильтром по категории.

```json
{
  "name": "list_scenarios",
  "arguments": {"category": "freelancing"***REMOVED***
***REMOVED***
```

##### `get_scenario`
Детали одного сценария.

```json
{
  "name": "get_scenario",
  "arguments": {"slug": "freelance_parser"***REMOVED***
***REMOVED***
```

##### `apply_scenario`
Применить сценарий — получить готовый промт.

```json
{
  "name": "apply_scenario",
  "arguments": {
    "slug": "freelance_parser",
    "variables": {"URL": "https://example.com"***REMOVED***
  ***REMOVED***
***REMOVED***
```

##### `search_scenarios`
Поиск сценариев по тексту.

```json
{
  "name": "search_scenarios",
  "arguments": {"query": "telegram"***REMOVED***
***REMOVED***
```

---

### 2.3 Ресурсы

#### `freebuff://session/current`
Текущая активная сессия.

```json
{
  "active": true,
  "session_id": "a1b2c3d4"
***REMOVED***
```

#### `freebuff://context_12/last`
Последний конспект.

```
# Конспект: debug session
# Дата: 2026-07-29
...
```

---

### 2.4 Конфигурация для MCP клиентов

#### Claude Code (`~/.claude.json`)
```json
{
  "mcpServers": {
    "freebuff-plugin": {
      "command": "python3",
      "args": ["/storage/emulated/0/PROJECTS/workstation/freebuff/freebuff_plugin_03/mcp_server.py"***REMOVED***
    ***REMOVED***
  ***REMOVED***
***REMOVED***
```

#### OpenClaw (`.openclaw/mcp.json`)
```json
{
  "mcpServers": {
    "freebuff-plugin": {
      "command": "python3",
      "args": ["/storage/emulated/0/PROJECTS/workstation/freebuff/freebuff_plugin_03/mcp_server.py"***REMOVED***
    ***REMOVED***
  ***REMOVED***
***REMOVED***
```

#### VS Code / Cursor (`.vscode/mcp.json`)
```json
{
  "servers": {
    "freebuff-plugin": {
      "type": "stdio",
      "command": "python3",
      "args": ["/storage/emulated/0/PROJECTS/workstation/freebuff/freebuff_plugin_03/mcp_server.py"***REMOVED***
    ***REMOVED***
  ***REMOVED***
***REMOVED***
```

> **Примечание:** Замени путь на актуальный `FREEBUFF_ROOT`, если проект расположен не в `/storage/emulated/0/PROJECTS/workstation/freebuff`.

---

## 3. CLI (Command Line)

> Все команды выполняются из корня проекта (`FREEBUFF_ROOT`).
> По умолчанию: `/storage/emulated/0/PROJECTS/workstation/freebuff`
> ```bash
> cd /storage/emulated/0/PROJECTS/workstation/freebuff
> ```

### 3.1 Wrapper CLI

```bash
python3 freebuff_plugin_03/wrapper.py launch "напиши парсер" --cwd . --timeout 300
python3 freebuff_plugin_03/wrapper.py run "тест" --timeout 120       # синхронно (отладка)
python3 freebuff_plugin_03/wrapper.py status                          # активные сессии
```

### 3.2 Bridge CLI

```bash
python3 freebuff_plugin_03/bridge.py start                           # → session_id
python3 freebuff_plugin_03/bridge.py end a1b2c3d4 --summary "done"   # → конспект
```

### 3.3 Scenario Engine CLI

```bash
python3 freebuff_plugin_03/scenario_engine.py list                      # все сценарии
python3 freebuff_plugin_03/scenario_engine.py list --category freelancing
python3 freebuff_plugin_03/scenario_engine.py list --tag telegram
python3 freebuff_plugin_03/scenario_engine.py get freelance_parser      # детали
python3 freebuff_plugin_03/scenario_engine.py search telegram            # поиск
python3 freebuff_plugin_03/scenario_engine.py apply freelance_parser \  # применить
  --vars '{"URL":"https://example.com"***REMOVED***'
python3 freebuff_plugin_03/scenario_engine.py reload                     # перезагрузка
```

### 3.4 Router CLI

```bash
python3 freebuff_plugin_03/router.py "напиши парсер"                    # одиночный запрос
python3 freebuff_plugin_03/router.py -i                                  # интерактивный режим
```

### 3.5 OOM Protection

```bash
bash scripts_01/oom_protect.sh --status    # статус памяти и процессов
bash scripts_01/oom_protect.sh --force     # принудительная очистка
bash scripts_01/oom_protect.sh             # автоматическая проверка+очистка
```

### 3.6 API сервер

```bash
# FastAPI
python3 freebuff_plugin_03/api.py
# → http://127.0.0.1:8410 | /docs

# MCP STDIO
python3 freebuff_plugin_03/mcp_server.py

# MCP SSE
python3 freebuff_plugin_03/mcp_server.py --transport sse --port 8411
```

---

## 4. Быстрые примеры

```bash
# Полный цикл через REST
curl -X POST "http://127.0.0.1:8410/session?action=start&topic=test"
curl -X POST http://127.0.0.1:8410/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"напиши hello world на Python"***REMOVED***'
curl http://127.0.0.1:8410/status
curl -X POST "http://127.0.0.1:8410/session?action=end&summary=test%20done"

# Использование сценариев
curl http://127.0.0.1:8410/scenarios
curl -X POST http://127.0.0.1:8410/scenarios/freelance_parser/apply \
  -H "Content-Type: application/json" \
  -d '{"variables":{"URL":"https://example.com"***REMOVED******REMOVED***'

# Проверка системы
freebuff --status     # через bash-обёртку
```
