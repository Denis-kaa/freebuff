# Freebuff Plugin — Быстрый старт

> За 5 минут настроить и запустить freebuff_plugin на Termux/Android.

---

## 1. Проверка установки

```bash
# Всё уже настроено, если ты используешь этот проект.
# Просто запусти:

freebuff

# Или через Python:
python3 freebuff_plugin/api.py        # REST API на :8410
python3 freebuff_plugin/mcp_server.py  # MCP сервер (STDIO)
```

---

## 2. Убедись, что всё работает

```bash
# Статус OOM защиты
bash scripts/oom_protect.sh --status

# Статус плагина
python3 freebuff_plugin/wrapper.py status

# Статус системы
python3 freebuff_cli.py status

# Список сценариев
python3 freebuff_plugin/scenario_engine.py list
```

**Ожидаемый вывод:**
```
[OOM***REMOVED*** MemAvailable: 868 MB | MemFree: 126 MB | Threshold: 512 MB
✅ OK: MemAvailable 868 MB >= 512 MB

Нет активных сессий

Активных сессий: 17
Здоровье: ✅ OK

Scenarios: 7
  agent_setup           | agent       | Настройка AI агента
  freelance_api         | freelancing | API сервер / Интеграция
  freelance_integration | freelancing | Интеграция API
  freelance_landing     | freelancing | Сайт-визитка / Лендинг
  freelance_parser      | freelancing | Парсер сайта
  freelance_tg_bot      | freelancing | Telegram бот
  task_framework        | templates   | Фреймворк промтов
```

---

## 3. Базовое использование

### Вариант A: Через CLI freebuff (рекомендуется)

```bash
# Просто запусти свободный разговор
freebuff

# С задачей напрямую (без интерактива)
freebuff --oneshot "напиши парсер JSON на Python"
```

При каждом запуске:
1. **Фаза 0:** OOM Protection убивает старые freebuff процессы
2. **Фаза 1:** Python стартует сессию → tmux → exit (0.5 секунды)
3. **Фаза 2:** Codebuff работает (единственный тяжёлый процесс)
4. **Фаза 3:** monitor.sh завершает сессию → конспект

### Вариант B: Через REST API

```bash
# 1. Запусти сервер
python3 freebuff_plugin/api.py &
# → http://127.0.0.1:8410

# 2. Отправь задачу
curl -X POST http://127.0.0.1:8410/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"напиши простое приложение на FastAPI"***REMOVED***'

# 3. Проверь статус
curl http://127.0.0.1:8410/status
```

### Вариант C: Через MCP

```bash
# Запусти MCP сервер
python3 freebuff_plugin/mcp_server.py

# Подключись из Claude Code или другого MCP клиента
```

---

## 4. Использование сценариев

Сценарии — это готовые промты для типовых задач.

```bash
# Список
python3 freebuff_plugin/scenario_engine.py list

# Детали сценария "парсер"
python3 freebuff_plugin/scenario_engine.py get freelance_parser

# Сгенерировать промт для парсера example.com
python3 freebuff_plugin/scenario_engine.py apply freelance_parser \
  --vars '{"URL":"https://example.com","поле1":"title","поле2":"price","формат":"JSON"***REMOVED***'

# Полученный промт можно сразу скормить freebuff:
freebuff --oneshot "$(python3 freebuff_plugin/scenario_engine.py apply freelance_parser --vars '{"URL":"..."***REMOVED***' | tail -n +5)"
```

---

## 5. Управление сессиями

```bash
# Начать сессию
python3 freebuff_plugin/bridge.py start
# → a1b2c3d4

# Завершить (создаёт конспект)
python3 freebuff_plugin/bridge.py end a1b2c3d4 --summary "тест"
# → ✔ Конспект: context/summaries/conspect_test_2026-07-29.md

# Список сессий
python3 -c "
from freebuff_plugin.bridge import session_list
for s in session_list():
    print(f\"{s['session_id'***REMOVED***[:8***REMOVED******REMOVED*** | {s['topic'***REMOVED***[:40***REMOVED******REMOVED*** | {s['status'***REMOVED******REMOVED***\")
"
```

---

## 6. OOM Protection

Защита от Signal 9 запускается **автоматически** при каждом запуске freebuff.

```bash
# Проверить текущее состояние
bash scripts/oom_protect.sh --status

# Принудительно очистить (если память кончается)
bash scripts/oom_protect.sh --force
```

**Что делает:**
- Проверяет `MemAvailable` из `/proc/meminfo`
- Если < 512 MB → убивает старые freebuff процессы
- Чистит зависшие tmux сессии
- Чистит PID-файлы мёртвых процессов

---

## 7. Примеры для фриланса

### Telegram бот
```bash
# Сценарий
python3 freebuff_plugin/scenario_engine.py apply freelance_tg_bot \
  --vars '{"описание":"бот для заказа пиццы","текст":"Добро пожаловать!","команда1":"/menu","описание1":"меню","команда2":"/order","описание2":"заказ"***REMOVED***'

# Запустить разработку через freebuff
freebuff --oneshot "$(python3 freebuff_plugin/scenario_engine.py apply freelance_tg_bot ...)"
```

### Парсер сайта
```bash
python3 freebuff_plugin/scenario_engine.py apply freelance_parser \
  --vars '{"URL":"https://books.toscrape.com","поле1":"название","поле2":"цена","поле3":"наличие","формат":"CSV"***REMOVED***'
```

### Лендинг
```bash
python3 freebuff_plugin/scenario_engine.py apply freelance_landing \
  --vars '{"тип_сайта":"портфолио фотографа","доп_секция":"Галерея работ","цвета":"тёмная тема, акцент золотой"***REMOVED***'
```

---

## 8. Интеграция с другими AI-агентами

### Claude Code
Добавь в `~/.claude.json`:
```json
{
  "mcpServers": {
    "freebuff-plugin": {
      "command": "python3",
      "args": ["/storage/emulated/0/PROJECTS/workstation/freebuff/freebuff_plugin/mcp_server.py"***REMOVED***
    ***REMOVED***
  ***REMOVED***
***REMOVED***
```

### OpenClaw
Добавь в `.openclaw/mcp.json` или настрой REST:
```json
{
  "mcpServers": {
    "freebuff-plugin": {
      "command": "python3",
      "args": ["/storage/emulated/0/PROJECTS/workstation/freebuff/freebuff_plugin/mcp_server.py"***REMOVED***
    ***REMOVED***
  ***REMOVED***
***REMOVED***
```

### Любой HTTP-клиент
```bash
curl -X POST http://127.0.0.1:8410/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"твоя задача"***REMOVED***'
```

---

## 9. Частые вопросы

**Q: Codebuff запускается слишком долго?**  
A: Фаза 1 (Python) занимает < 1 секунды. Долго только сам Codebuff.

**Q: Памяти мало, процесс убивается?**  
A: OOM Protection убивает старые freebuff перед запуском. Если всё равно не хватает — запусти `bash scripts/oom_protect.sh --force` вручную.

**Q: Как посмотреть результат задачи?**  
A: `python3 freebuff_plugin/wrapper.py status` покажет активные сессии. После завершения — `Get /context` или `GET /status`.

**Q: Сценарий не подходит?**  
A: Сценарии — это шаблоны. Их можно редактировать в `freebuff_plugin/scenarios/*.md` или добавить свой.

---

## 10. Диагностика

```bash
# Все проверки одной командой
echo "=== OOM ==="
bash scripts/oom_protect.sh --status | head -5
echo "=== API ==="
curl -s http://127.0.0.1:8410/status 2>/dev/null | python3 -m json.tool || echo "API not running"
echo "=== MCP ==="
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"***REMOVED***' | python3 freebuff_plugin/mcp_server.py 2>/dev/null | head -c 200 || echo "MCP not running"
echo "=== SCENARIOS ==="
python3 freebuff_plugin/scenario_engine.py list 2>/dev/null || echo "Engine error"
echo "=== SYNTAX ==="
bash -n scripts/oom_protect.sh && echo "oom_protect.sh: OK"
python3 -c "import freebuff_plugin.api; print('api.py: OK')"
python3 -c "import freebuff_plugin.wrapper; print('wrapper.py: OK')"
python3 -c "import freebuff_plugin.mcp_server; print('mcp_server.py: OK')"
```
