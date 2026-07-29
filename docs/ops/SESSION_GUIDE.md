# SESSION_GUIDE.md — Как начинать сессию и восстанавливать контекст

> **Для:** Пользователя Denis (владелец системы)
> **Цель:** Быстрый старт с Buffy с восстановлением полного контекста предыдущей работы
> **FREEBUFF_ROOT:** `/storage/emulated/0/PROJECTS/workstation/freebuff/`
> **Все команды** предполагают что вы в корне freebuff/

---

## 🚀 Быстрый старт (30 секунд)

### Если ты общаешься с Buffy (Freebuff на DeepSeek)

Скопируй этот текст в начало диалога:

```
Я начинаю новую сессию. Загрузи последний конспект из freebuff/context/summaries/,
восстанови контекст, прочитай BUFFY.md, и расскажи кратко:
- Что было в прошлой сессии?
- Какие задачи остались незавершёнными?
- Какие файлы были изменены?

Текущий проект: [название, например "termux-ai-agent"***REMOVED***
```

### Если ты общаешься с freebuff моделью (Qwen через Termux)

```bash
# 1. Восстанови контекст
python ~/storage/shared/PROJECTS/workstation/freebuff/scripts/auto_conspect.py

# 2. Найди последний конспект и скопируй его в начало диалога
cat ~/storage/shared/PROJECTS/workstation/freebuff/context/summaries/conspect_*.md | tail -20

# 3. Запусти агента
cd ~/storage/shared/PROJECTS/workstation/ai-engineering-pipeline/projects/termux-ai-agent/
python interactive_test.py
```

### Если ты работаешь через OpenClaw

```bash
# Открой OpenClaw и скажи:
"Я начинаю сессию. Прочитай freebuff/context/summaries/ — последний конспект,
и freebuff/BUFFY.md — мои инструкции. Доложи статус."
```

---

## 📥 Восстановление контекста (подробно)

### Шаг 1: Посмотри что было в прошлой сессии

```bash
cd /storage/emulated/0/PROJECTS/workstation/freebuff/

# Список всех сессий
python -c "
from scripts.context_manager import ContextManager
cm = ContextManager('.')
for s in cm.list_sessions():
    print(f'{s[\"session_id\"***REMOVED***[:8***REMOVED******REMOVED*** | {s[\"status\"***REMOVED******REMOVED*** | {s[\"project\"***REMOVED******REMOVED*** | {s[\"topic\"***REMOVED******REMOVED*** | {s[\"message_count\"***REMOVED******REMOVED*** msgs | {s[\"updated_at\"***REMOVED***[:16***REMOVED******REMOVED***')
"

# Найди последний конспект
ls -lt context/summaries/ | head -5

# Прочитай последний конспект
cat context/summaries/$(ls -t context/summaries/ | head -1)
```

### Шаг 2: Восстанови активную сессию

```bash
# Если сессия была прервана (статус ACTIVE или PAUSED)
python -c "
from scripts.context_manager import ContextManager, SessionStatus
cm = ContextManager('.')
active = cm.list_sessions(SessionStatus.ACTIVE)
if active:
    s = active[0***REMOVED***
    print(f'Восстановлена сессия: {s[\"session_id\"***REMOVED***[:8***REMOVED******REMOVED***')
    print(f'Проект: {s[\"project\"***REMOVED******REMOVED***')
    print(f'Тема: {s[\"topic\"***REMOVED******REMOVED***')
    print(f'Сообщений: {s[\"message_count\"***REMOVED******REMOVED***')
    # Покажи последние сообщения
    msgs = cm.get_messages(s['session_id'***REMOVED***, limit=5)
    for m in msgs:
        print(f'  [{m[\"role\"***REMOVED******REMOVED******REMOVED*** {m[\"content\"***REMOVED***[:100***REMOVED******REMOVED***')
"
```

### Шаг 3: Скопируй контекст в буфер обмена

```bash
# Терминальный способ — вывести и скопировать вручную
cat context/summaries/$(ls -t context/summaries/ | head -1)

# Или запиши во временный файл и открой в редакторе
cp context/summaries/$(ls -t context/summaries/ | head -1) /sdcard/context_resume.md
```

---

## 🔄 Типичный сценарий сессии

### Начало
```
Ты: "Я начинаю новую сессию по проекту termux-ai-agent. Загрузи контекст."
Buffy: "Загрузил конспект от 27.07. Прошлая сессия: реализовали v4.0 (5 слоёв), 
       38 тестов, 0 mypy errors. Незавершённое: нужно написать тесты для новых модулей.
       Что делаем?"
```

### В течение сессии
```
Каждые ~10 сообщений Buffy создаёт авточекпоинт.
Ты можешь в любой момент сказать: "Сохрани чекпоинт" — и Buffy запишет состояние.
```

### Завершение
```
Ты: "Завершаем сессию."
Buffy: [запускает auto_conspect.py, создаёт конспект, помечает сессию COMPLETED***REMOVED***
      "Сессия завершена. Конспект: context/summaries/conspect_termux-ai-agent_2026-07-27_1800.md"
```

---

## 🛠 Если что-то сломалось

### Сессия не восстанавливается
```bash
# Проверь целостность БД
sqlite3 data/context.db "PRAGMA integrity_check;"

# Посмотри все сессии вручную
sqlite3 data/context.db "SELECT session_id, status, project, topic, updated_at FROM sessions;"

# Сбрось зависшие ACTIVE сессии (старше 1 дня)
python -c "
import sqlite3
conn = sqlite3.connect('data/context.db')
conn.execute(\"UPDATE sessions SET status = 'abandoned' WHERE status = 'active' AND updated_at < datetime('now', '-1 day')\")
conn.commit()
print(f'Сброшено: {conn.total_changes***REMOVED*** сессий')
"
```

### Конспект не создаётся
```bash
# Запусти вручную
python scripts/auto_conspect.py

# Проверь наличие файлов
ls context/checkpoints/
ls context/summaries/
```

---

## 📊 Чек-лист перед началом работы

- [ ***REMOVED*** `freebuff/BUFFY.md` — прочитан/загружен ассистентом
- [ ***REMOVED*** `freebuff/context/summaries/` — последний конспект найден
- [ ***REMOVED*** Сессия создана/восстановлена в `context.db`
- [ ***REMOVED*** Ассистент доложил статус: что было, что продолжаем
- [ ***REMOVED*** Выбран проект для работы

---

_С вопросами → BUFFY. Она знает всё._
