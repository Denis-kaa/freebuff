# Runtime Marketplace — архитектура

> **Версия:** 1.0.0  
> **Дата:** 2026-07-29  
> **Статус:** Foundation (структура создана, Marketplace — будущее)  
> **Основание:** promt16.md §2.3, CODE_QUALITY_STANDARD.md §12.4

## Философия

**Buffy — не монолит.** Любой AI Runtime должен подключаться без изменения кода ядра.

Принципы:
1. **No core change** — новый Runtime добавляется YAML-файлом + опционально Python-адаптером
2. **Auto-discovery** — RuntimeRegistry автоматически находит новые Runtime
3. **Loose coupling** — Runtime не знает о Buffy, Buffy не зависит от конкретного Runtime
4. **Capability-first** — пользователь выбирает capability, система выбирает Runtime

## Трёхслойная архитектура

```
┌──────────────────────────────────────────────────────────────────┐
│                        MARKETPLACE                                │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ LAYER 1: providers/ (YAML-манифесты)                        │  │
│  │                                                              │  │
│  │  freebuff.yaml    claude_code.yaml    openclaw.yaml   ...   │  │
│  │                                                              │  │
│  │  Каждый YAML описывает:                                      │  │
│  │  · имя, бинарник, аргументы                                  │  │
│  │  · capabilities + confidence scores                          │  │
│  │  · метод установки                                           │  │
│  │  · платформы, требования, API-ключи                          │  │
│  │                                                              │  │
│  │  ➕ Новый Runtime = новый YAML. Ядро не меняется.            │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                              │                                     │
│                              ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ LAYER 2: plugins/ (Python-расширения)                       │  │
│  │                                                              │  │
│  │  (пусто — все текущие Runtime используют MCP)               │  │
│  │                                                              │  │
│  │  Когда нужен plugin:                                         │  │
│  │  · Нестандартный протокол (не MCP)                           │  │
│  │  · Сложная установка (кастомный installer)                   │  │
│  │  · Bridge к другой экосистеме                                │  │
│  │                                                              │  │
│  │  Плагин саморегистрируется в AdapterRegistry.                │  │
│  │  Ядро не меняется.                                           │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                              │                                     │
│                              ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ LAYER 3: recipes/ (человекочитаемые инструкции)             │  │
│  │                                                              │  │
│  │  freebuff/RECIPE.md  claude_code/RECIPE.md  ...             │  │
│  │                                                              │  │
│  │  Каждый Recipe: установка, зависимости, wrapper,             │  │
│  │  patch, update, uninstall, doctor, recovery                  │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

## Текущее состояние (2026-07-29)

### Что уже реализовано ✅

| Компонент | Файлы | Статус |
|-----------|-------|--------|
| **RuntimeAdapter ABC** | `freebuff_plugin/runtime/adapter.py` | ✅ Готов |
| **StdioMCPAdapter** | `freebuff_plugin/runtime/adapter.py` | ✅ Готов (универсальный для MCP) |
| **HTTPMCPAdapter** | `freebuff_plugin/runtime/adapter.py` | ✅ Готов (универсальный для HTTP MCP) |
| **AdapterRegistry** | `freebuff_plugin/runtime/adapter.py` | ✅ Готов (register/get/create) |
| **RuntimeRegistry** | `freebuff_plugin/runtime/registry.py` | ✅ Готов (+ load из YAML) |
| **RuntimeCapabilityRegistry** | `freebuff_plugin/runtime/registry.py` | ✅ Готов (+ load из YAML) |
| **Provider manifests** | `runtime/providers/*.yaml` | ✅ 3 манифеста |
| **Plugin система** | `runtime/plugins/` | 🟡 Структура создана (плагинов пока нет — MCP покрывает всё) |
| **Recipe система** | `runtime/recipes/` | ✅ 2 рецепта + README |
| **Doctor CLI** | `scripts/doctor.py` | ✅ Готов |

### Покрытие Runtime

| Runtime | Provider YAML | Recipe | Adapter | Валидация |
|---------|:---:|:---:|:---:|:---:|
| **Freebuff CLI** | ✅ | ✅ | ✅ StdioMCPAdapter (generic) | 🟡 Уровень 1 |
| **Claude Code** | ✅ | ✅ | ✅ StdioMCPAdapter (generic) | 🟡 Уровень 1 |
| **OpenClaw** | ✅ | 🔴 | ✅ StdioMCPAdapter (generic) | 🔴 Уровень 0 |
| **Hermes** | 🔴 | 🔴 | 🔴 | 🔴 Уровень 0 |
| **Codex (GPT-4o)** | 🔴 | 🔴 | 🔴 | 🔴 Уровень 0 |
| **Ollama** | 🔴 | 🔴 | 🔴 | 🔴 Уровень 0 |

## Как добавить новый Runtime

### Шаг 1: Создать YAML-манифест

```bash
# Создай файл
nano runtime/providers/cursor.yaml
```

```yaml
name: cursor
display_name: Cursor IDE Agent
description: Cursor AI agent через CLI
adapter_type: stdio_mcp
bin_names: [cursor-agent***REMOVED***
args: [mcp***REMOVED***
capabilities:
  coding: 0.90
  review: 0.85
platforms: [linux, macos***REMOVED***
install:
  type: manual
  command: "Установите Cursor IDE и включите CLI mode"
  check: "cursor-agent --version"
```

### Шаг 2: Проверить, что RuntimeRegistry подхватит

```python
from freebuff_plugin.runtime import RuntimeRegistry

registry = RuntimeRegistry()
registry.load_providers_from_dir()     # ← автообнаружение YAML
registry.discover()                    # ← поиск бинарников
print(registry.list())                 # ← новый Runtime в списке
```

### Шаг 3: (Опционально) Создать Recipe

```bash
mkdir -p runtime/recipes/cursor
nano runtime/recipes/cursor/RECIPE.md
```

### Шаг 4: (Опционально) Создать Plugin

Только если Runtime НЕ использует MCP.

```bash
mkdir -p runtime/plugins/cursor
nano runtime/plugins/cursor/__init__.py
```

## Проверка: новый Runtime без изменения ядра

```bash
# До: трогаем ТОЛЬКО runtime/providers/
touch runtime/providers/cursor.yaml

# Импортируем реестр — без изменений в коде
python -c "
from freebuff_plugin.runtime import RuntimeRegistry
r = RuntimeRegistry()
r.load_providers_from_dir()
print('Known runtimes:', [rt['name'***REMOVED*** for rt in r.list_known()***REMOVED***)
# → ['freebuff', 'claude-code', 'openclaw', 'cursor'***REMOVED***
"
```

**Ядро (`freebuff_plugin/runtime/registry.py`, `adapter.py`) — без изменений.**

## Будущее Marketplace

Когда система стабилизируется (уровень 4 для 3+ Runtime):

```
runtime/
├── providers/          # ~20 YAML-манифестов (каталог)
├── plugins/            # ~5 плагинов для нестандартных Runtime
├── recipes/            # человекочитаемые инструкции
└── marketplace.json    # индекс всех доступных Runtime (для UI)
```

Возможности будущего Marketplace:
- `buffy runtime search coding` — поиск Runtime по capability
- `buffy runtime install cursor` — установка из каталога
- `buffy runtime compare coding` — сравнение Runtime по capability
- Community contributions через PR в `runtime/providers/`

## Связанные документы

- `docs/core/RUNTIME_ABSTRACTION_SPECIFICATION.md` — спецификация RAL
- `docs/core/COMPATIBILITY_MATRIX.md` — матрица совместимости
- `docs/core/ARCHITECTURE_PRINCIPLES.md` — принципы (Loose coupling, Marketplace-ready)
- `freebuff_plugin/INTEGRATION_CONTRACT.md` — контракт ядро↔плагин
- `runtime/README.md` — обзор системы Recipes
- `runtime/providers/README.md` — формат манифеста
