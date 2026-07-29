# TROUBLESHOOTING.md — Известные проблемы Freebuff

> **Статус:** живой документ
> **Последнее обновление:** 2026-07-28

---

## Lightpanda Worker

### `Lightpanda binary not found`

**Симптом:**
```
LightpandaResult(success=False, error="Lightpanda binary not found: ...")
```

**Причина:** бинарь Lightpanda ещё не установлен, либо wrapper `.tools/lightpanda` не создан.

**Решение:**
```bash
bash scripts/install_lightpanda.sh
```

**Диагностика:**
```bash
ls -la /storage/emulated/0/PROJECTS/workstation/freebuff/.tools/lightpanda
proot-distro login ubuntu -- /usr/local/bin/lightpanda --version
```

---

### `glibc` / `cannot link executable` / `No such file or directory`

**Симптом:** wrapper падает с ошибками динамического линковщика.

**Причина:** Lightpanda скомпилирован для glibc, а Termux использует bionic libc.

**Решение:** убедитесь, что wrapper использует `proot-distro login ubuntu -- ...`:
```bash
proot-distro login ubuntu -- /usr/local/bin/lightpanda --version
```

Если версия не выводится внутри proot, перезапустите установку:
```bash
bash scripts/install_lightpanda.sh
```

---

### CLI-флаги `--provider`/`--task` и `agent -e` не работают

**Симптом:**
```
unknown flag: --provider
unknown flag: -e
```

**Причина:** флаги `--provider`, `--task` и `agent -e` взяты из документации Lightpanda, но реальный бинарь может иметь другой интерфейс.

**Решение:**
- Проверьте реальные флаги бинаря:
  ```bash
  proot-distro login ubuntu -- /usr/local/bin/lightpanda --help
  ```
- Если флаги отличаются, откройте issue или PR с обновлёнными аргументами в `src/workers/lightpanda_worker.py`.

---

### `run_script` падает: "PandaScript not found"

**Симптом:**
```
LightpandaResult(success=False, error="PandaScript not found: /path/to/script.js")
```

**Причина:** `run_script` проверяет файл на стороне Termux (`os.path.isfile`). Если скрипт находится внутри proot-окружения, путь может не существовать в Termux.

**Решение (v1):** храните PandaScript в доступном для Termux пути, например внутри `freebuff/scripts/` или `freebuff/projects/`.

---

### OOM / Android убивает процесс

**Симптом:** агент или Lightpanda неожиданно завершается без ошибки.

**Причина:** Android ограничивает RAM; Lightpanda тяжёлее, чем ожидалось.

**Решение:**
- Не запускайте несколько агентов/вкладок параллельно.
- Используйте `timeout` в worker.
- Сохраняйте промежуточные результаты на диск.

---

## Agent Context Bridge

### termux-ai-agent не запускается после интеграции

**Симптом:** `termux-ai-agent/main.py` падает на старте.

**Причина:** интеграция обёрнута в `try/except`, но при критическом сбое в импорте может сломать импорт freebuff.

**Решение:**
- Убедитесь, что `freebuff/scripts/` доступен в `sys.path`.
- Проверьте, что `scripts/context_manager.py` не падает при инициализации.

---

### Путь к freebuff зашит в коде (`_FREEBUFF_ROOT`)

**Симптом:** после перемещения директории freebuff bridge пытается писать в старый путь и падает.

**Причина:** `scripts/agent_context_bridge.py` использует константу `_FREEBUFF_ROOT`.

**Решение:**
- Задайте путь через переменную окружения:
  ```python
  import os
  _FREEBUFF_ROOT = os.environ.get("FREEBUFF_ROOT", "/storage/emulated/0/PROJECTS/workstation/freebuff")
  ```
- В v1 путь захардкожен; перенос проекта требует ручной замены константы.

---

### Сессии агента не видны в freebuff

**Симптом:** `data/context.db` не растёт, конспекты не создаются.

**Причина:** bridge является синглтоном на модуле. Если `termux-ai-agent` запущен в другом процессе или импорте, может создаваться отдельный инстанс.

**Решение:**
- Убедитесь, что `termux-ai-agent` и freebuff используют одну и ту же БД.
- Проверьте права на запись в `freebuff/data/`.

---

### Summary assistant-сообщений обрезается

**Симптом:** в `data/context.db` видно обрезанный JSON с `... [truncated***REMOVED***`.

**Причина:** `_compact_response` обрезает JSON до 1000 символов, чтобы не переполнять БД.

**Решение:**
- Это ожидаемое поведение v1.
- Для хранения полных ответов используйте файловый стриминг в `sessions/`.

---

## Общие проблемы интеграций

### pre-commit hook блокирует коммит

**Симптом:**
```
🛑 Commit blocked! Update the required docs ...
```

**Решение:**
- Обновите `CHANGELOG.md`.
- Или обойдите hook: `git commit --no-verify` / `SKIP_AUTODOC=1 git commit`.

### `buffy_autodoc.py` ругается на отсутствие `CHANGELOG.md`

**Решение:** любое изменение кода должно сопровождаться записью в `CHANGELOG.md`.
