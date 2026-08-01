# DOCTOR GUIDE — Buffy Doctor CLI

> **Версия:** 1.0.0
> **Дата:** 2026-07-29
> **Основание:** [016_02_arhitektura_reorganizaciya.md***REMOVED***(../../pompts_11/016_02_arhitektura_reorganizaciya.md) Задача 2.2

---

## Назначение

`scripts_01/doctor.py` — CLI-инструмент диагностики окружения Buffy.
Проверяет системные компоненты, Runtime, конфигурацию, и при обнаружении
проблем предлагает автоматическое исправление.

## Использование

```bash
# Базовая диагностика (OS, Python, Git, PATH, диск, RAM, workspace)
python scripts_01/doctor.py

# Полная проверка (все Runtime, .env, тесты)
python scripts_01/doctor.py --full

# Проверить конкретный Runtime
python scripts_01/doctor.py --check-runtime freebuff
python scripts_01/doctor.py --check-runtime claude-code

# Автоматическое исправление
python scripts_01/doctor.py --fix

# Вывод в JSON (для CI)
python scripts_01/doctor.py --json

# Версия
python scripts_01/doctor.py --version
```

## Что проверяется

### Всегда (базовая диагностика)

| Проверка | Что делает |
|----------|-----------|
| **Platform** | OS и архитектура (Android/Linux/macOS, ARM64/x86_64) |
| **Termux** | PREFIX, окружение (если Android) |
| **Python** | Версия (>= 3.11), pip |
| **Git** | Наличие и версия |
| **PATH** | ~/.local/bin, /usr/local/bin |
| **Disk** | Свободное место (> 1 GB) |
| **RAM** | Доступная память (> 512 MB) |
| **Workspace** | BUFFY.md, context.db |

### С --full

| Проверка | Что делает |
|----------|-----------|
| **Node.js** | Версия (>= 18), npm |
| **proot** | proot-distro (Android) |
| **FreeBuff CLI** | Бинарник, --version |
| **Claude Code** | Бинарник, --version |
| **.env** | Наличие API ключей |
| **.keys/** | KeyPool директория |
| **Tests** | Быстрый прогон pytest |

## Health Score

```
1.0  = всё в порядке
0.8+ = есть предупреждения
0.5+ = есть проблемы
<0.5 = критично
```

## Авто-исправление (--fix)

При запуске с `--fix`, Doctor пытается автоматически исправить
обнаруженные проблемы:

| Проблема | Исправление |
|----------|------------|
| Git не установлен | `pkg install git` |
| Python < 3.11 | `pkg install python` |
| FreeBuff CLI не установлен | `pip install freebuff` |
| Claude Code не установлен | `npm install -g @anthropic/claude-code` |
| proot не установлен | `pkg install proot proot-distro` |
| PATH не настроен | `export PATH="$HOME/.local/bin:$PATH"` |

## Exit Codes

```
0 = OK или только предупреждения
1 = Есть критические ошибки
```

## Интеграция с CI

```bash
python scripts_01/doctor.py --json > doctor_report.json
```

## Связанные документы

- [../core/COMPATIBILITY_MATRIX.md***REMOVED***(../core/COMPATIBILITY_MATRIX.md)
- [../../runtime_05/README.md***REMOVED***(../../runtime_05/README.md)
- [../core/ARCHITECTURE_PRINCIPLES.md***REMOVED***(../core/ARCHITECTURE_PRINCIPLES.md)
