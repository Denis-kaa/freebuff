# Runtime Providers — формат манифеста

> **Версия формата:** 1.0.0  
> **Marketplace-ready:** добавление нового Runtime — один YAML-файл

## Назначение

`runtime_05/providers/` содержит YAML-манифесты для каждого AI Runtime.
Каждый манифест полностью описывает Runtime: как его найти, установить, какие у него capabilities.

**Принцип:** новый Runtime добавляется **без изменения кода ядра** — достаточно создать YAML-файл
в этой директории. `RuntimeRegistry` автоматически обнаружит его при следующем `discover()`.

## Как добавить новый Runtime

```bash
# 1. Создай YAML-файл
cp runtime_05/providers/_template.yaml runtime_05/providers/my_runtime.yaml

# 2. Заполни поля
nano runtime_05/providers/my_runtime.yaml

# 3. (Опционально) создай адаптер, если MCP не подходит
# freebuff_plugin_03/runtime/adapters/my_runtime.py

# 4. Всё. RuntimeRegistry.discover() подхватит новый Runtime.
```

## Формат манифеста

```yaml
# Версия формата
name: my-runtime                    # Каноническое имя (a-z, -)
display_name: My Runtime            # Человеческое имя
description: >                      # Описание (многострочное)
  Что делает Runtime, для каких задач подходит.

# ── Adapter ─────────────────────
adapter_type: stdio_mcp             # stdio_mcp | http_mcp | subprocess | http_api | bridge
bin_names:                          # Как найти бинарник (which)
  - myrt
  - my-runtime-cli
args:                               # Аргументы для запуска в MCP-режиме
  - mcp

# ── Capabilities ────────────────
capabilities:
  coding: 0.80                      # confidence 0.0–1.0
  planning: 0.75
  # ... любые capability

# ── Platforms ────────────────────
platforms:
  - linux
  - macos
  - android

# ── Installation ────────────────
install:
  type: npm                         # npm | pip | git | manual
  command: "npm install -g @org/my-runtime"
  fallback: "pip install my-runtime"  # опционально
  check: "myrt --version"           # команда проверки установки
  repo: "https://github.com/org/repo"  # для git-типа
  android_note: >                   # примечание для Android/Termux
    Особые инструкции для Android.

# ── API Key ──────────────────────
requires_api_key: true
api_key_env: MY_RUNTIME_API_KEY

# ── Requirements ─────────────────
requirements:
  python: ">=3.11"
  node: ">=18"
  memory_mb: 256

# ── Metadata ─────────────────────
version: auto                       # auto = определять при запуске
maintainer: Community
docs_url: https://example.com/docs
recipe: recipes/my_runtime/RECIPE.md  # путь к Recipe
```

## Автообнаружение

`RuntimeRegistry.discover()` сканирует `runtime_05/providers/*.yaml` и:

1. Читает YAML-манифест
2. Проверяет `bin_names` через `which` и `~/.local/bin/`
3. Если бинарник найден — создаёт `RuntimeDefinition`
4. Загружает `capabilities` в `RuntimeCapabilityRegistry`
5. Сохраняет состояние в `data_13/runtime_registry.json`

## Связь с Adapter системой

| adapter_type | Класс адаптера | Когда использовать |
|-------------|---------------|-------------------|
| `stdio_mcp` | `StdioMCPAdapter` | Runtime с MCP STDIO (freebuff, Claude Code) |
| `http_mcp` | `HTTPMCPAdapter` | Runtime с MCP HTTP транспортом |
| `subprocess` | (пользовательский) | Runtime без MCP — прямой subprocess |
| `http_api` | (пользовательский) | OpenAI-compatible API |
| `bridge` | (через Bridge Layer) | ACP-совместимый Runtime |

Если `adapter_type: stdio_mcp` или `adapter_type: http_mcp` — используется встроенный адаптер.
Для других типов нужен Python-адаптер в `freebuff_plugin_03/runtime/adapters/`.

## Marketplace-ready

Эта структура закладывает фундамент для будущего Marketplace:

- **runtime_05/providers/** — каталог провайдеров (YAML)
- **runtime_05/plugins/** — опциональные Python-плагины для сложных адаптеров
- **runtime_05/recipes/** — человекочитаемые инструкции по установке

См. `runtime_05/MARKETPLACE.md` для полной архитектуры.
