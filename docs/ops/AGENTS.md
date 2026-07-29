# AGENTS.md — Руководство для AI-агентов и чат-ботов

> **Для кого:** ChatGPT, Claude, DeepSeek, OpenClaw agents, freebuff LLM
> **Цель:** Стандартизировать взаимодействие с системой Freebuff на Termux/Android
> **FREEBUFF_ROOT:** `/storage/emulated/0/PROJECTS/workstation/freebuff/`

> **Note:** This is the detailed version. For Freebuff/Codebuff CLI, the canonical
> entry point is the root `AGENTS.md` and `.freebuff/AGENTS.md`.

---

## 🤖 Как работать с Freebuff

### Ты — агент в чужой среде

Freebuff — это рабочая среда на Android (Termux). Ты можешь:
- Читать и редактировать файлы в `/storage/emulated/0/PROJECTS/workstation/freebuff/`
- Запускать Python-скрипты из `scripts/`
- Работать с SQLite-базой `data/context.db`
- Читать документацию из `docs/`

Ты **НЕ** можешь (без ручного подтверждения пользователя):
- Менять системные файлы Android
- Устанавливать пакеты
- Пушить в Git

---

## 📋 Протокол взаимодействия

### 1. Начало работы
Когда пользователь просит тебя что-то сделать, первым делом:
```
1. Прочитай BUFFY.md
2. Запроси у пользователя ID сессии или создай новую:
   python scripts/context_manager.py
3. Найди последний конспект:
   ls freebuff/context/summaries/ | tail -1
```

### 2. Работа с файлами
- Всегда указывай **полный путь** от корня
- Не создавай файлы за пределами `freebuff/` без разрешения
- Используй `write_file` / `str_replace` для редактирования
- После изменений — запусти тесты

### 3. Сохранение контекста
В конце каждого значимого шага:
```python
from scripts.context_manager import ContextManager, CheckpointType
cm = ContextManager("freebuff/")
cm.save_checkpoint(session_id, "Краткое описание что сделано", CheckpointType.POST_STEP)
```

### 4. Коммуникация с Buffy
Buffy — главный ассистент. Если ты freebuff модель (Qwen) и задача слишком сложная:
- Передай управление Buffy (облачный DeepSeek) через MCP Bridge
- Или скажи пользователю: «Это сложная задача, рекомендую переключиться на Buffy»

---

## 🧩 Интеграция с внешними системами

### OpenClaw
```
- SOUL.md → ~/.openclaw/SOUL.md
- Логи → ~/.openclaw/logs/
- Агенты → ~/.openclaw/agents/
```

### Aider
```
- История → leviathan/root/.aider.chat.history.md
- Конфигурация → leviathan/root/.aider.conf.yml (если есть)
```

### Ollama
```
- API: http://localhost:11434
- Модели: qwen2.5:0.5b, qwen2.5:1.5b
```

### Termux AI Agent
```
- Путь: ai-engineering-pipeline/projects/termux-ai-agent/
- Запуск: python main.py
- Инструменты: search_web, reminder, file_reader, code_gen
```

---

## ⚡ Быстрые команды

```bash
# Контекст
cd /storage/emulated/0/PROJECTS/workstation/freebuff/
python scripts/auto_conspect.py                          # суммаризация всех активных сессий
python -c "
from scripts.context_manager import ContextManager
cm = ContextManager('.')
for s in cm.list_sessions():
    print(f'{s[\"session_id\"***REMOVED***[:8***REMOVED******REMOVED*** | {s[\"status\"***REMOVED******REMOVED*** | {s[\"project\"***REMOVED******REMOVED*** | {s[\"topic\"***REMOVED******REMOVED***')
"

# Проект termux-ai-agent
cd /storage/emulated/0/PROJECTS/workstation/ai-engineering-pipeline/projects/termux-ai-agent
python -m pytest tests/ -v                          # тесты (38 шт)
python -m mypy . --ignore-missing-imports           # статический анализ

# Git
cd freebuff && git status
cd ai-engineering-pipeline && git status
```

---

## 📚 Структура документации

| Документ | Для кого | Содержание |
|----------|---------|------------|
| **BUFFY.md** | Buffy (главный ассистент) | Роль, окружение, правила, сессии |
| **AGENTS.md** | Все AI-агенты | Протокол, интеграции, команды |
| **SESSION_GUIDE.md** | Пользователь | Как начинать сессию, восстанавливать контекст |
| **SPEC.md** | Разработчики | Полное ТЗ на freebuff по blueprints_v3 |
| **README.md** | Все | Обзор воркспейса |

---

_Вопросы? Читай BUFFY.md. Там всё._
