# Plugin Contract Specification

> **Версия:** 1.1.0
> **Последнее обновление:** 2026-08-01
> **Статус:** ACTIVE
> **Каноническое правило:** №9 (промт 37) — «Архитектура есть. Нужен Plugin Contract Specification».
> **Валидатор:** `scripts_01/plugin_contract.py` + CLI `python -m scripts_01.plugin_api contract <name>`

---

## 1. Назначение

Единый контракт границ **плагин ↔ ядро** Workspace OS. Определяет, что плагин
**обязан** объявить, какие lifecycle-хуки **обязан** реализовать, что ему
**разрешено** и **запрещено** делать. Контракт принудительно проверяется
валидатором при загрузке плагина (warning) и по запросу (CLI).

Плагин — это самостоятельный Python-пакет в `plugins_04/`, который:

- подписывается на события `EventBus`;
- регистрирует инструменты в `ToolRegistry`;
- добавляет CLI-команды;
- имеет собственное состояние и lifecycle (`BasePlugin`).

---

## 2. Обязательные требования

### 2.1. Структура каталога

```
plugins_04/<plugin_name>/
├── __init__.py        # экземпляр BasePlugin в переменной `plugin`
└── manifest.json      # статические метаданные (ОБЯЗАТЕЛЕН)
```

### 2.2. manifest.json — обязательные поля

| Поле | Тип | Обязательно | Правило |
|------|-----|-------------|---------|
| `name` | string | ✅ | `^[a-z0-9_***REMOVED***+$` — только нижний регистр, цифры, `_`. Без пробелов и заглавных. |
| `version` | string | ✅ | SemVer `^\\d+\\.\\d+\\.\\d+$` (например `1.0.0`). |
| `description` | string | ✅ | Непустая строка. |
| `author` | string | ❌ | Опционально. |
| `tags` | string[***REMOVED*** | ❌ | Список тегов. |
| `events_subscribed` | string[***REMOVED*** | ❌ | Шаблоны событий `domain.event` или `domain.*`. |
| `dependencies` | string[***REMOVED*** | ❌ | Внутренние зависимости. |
| `license` | string | ❌ | SPDX-идентификатор, по умолчанию `MIT`. |
| `python_version` | string | ❌ | Ограничение версии Python (по умолчанию `>=3.10`). |
| `homepage` | string | ❌ | Ссылка. |

### 2.3. __init__.py — экземпляр плагина

Плагин обязан предоставить в модуле переменную `plugin` — экземпляр
`scripts_01.plugin_api.BasePlugin`. Если переменная отсутствует, загрузчик
пытается найти первый подкласс `BasePlugin` в модуле; если и его нет — плагин
переходит в состояние `ERROR`.

---

## 3. Lifecycle-контракт

Плагин наследует `BasePlugin` и реализует хуки:

| Хук | Когда вызывается | Обязателен |
|-----|------------------|------------|
| `on_load()` | при загрузке (инициализация ресурсов) | ❌ (базовый no-op) |
| `on_enable()` | при активации (подписка на события) | ❌ |
| `on_disable()` | при деактивации (отписка) | ❌ |
| `on_unload()` | при выгрузке (освобождение ресурсов) | ❌ |
| `on_event(event)` | для каждого события, на которое подписан | ❌ |
| `get_tools()` | список `BaseTool` для регистрации | ❌ (пустой по умолчанию) |
| `get_commands()` | список CLI-команд | ❌ |
| `execute(action, params)` | выполнение действия | ✅ (базовый через `do_*`) |

Контрактная гарантия: если `on_enable()` бросает исключение — **все подписки
отзываются (rollback)**, плагин переходит в `ERROR`. Частичное состояние
недопустимо.

---

## 4. Разрешено

- ✅ Подписываться на события EventBus (`events_subscribed`).
- ✅ Регистрировать инструменты в ToolRegistry (через `get_tools()`).
- ✅ Добавлять CLI-команды (через `get_commands()`).
- ✅ Иметь собственное состояние, файлы и конфигурацию в пределах плагина.
- ✅ Выполнять действия через `execute(action, params)` → `do_*` методы.

---

## 5. Запрещено

- 🚫 **Запускать произвольные shell-команды** (`exec`, `shell=True`) — только через
  `ToolExecutor`/`ToolRegistry` ядра (безопасность: нет произвольных shell-команд).
- 🚫 **Переписывать ядро** (`core_02/`, `scripts_01/`) из плагина.
- 🚫 **Хранить секреты** в коде/манифесте — только через `.env`/конфиг ядра.
- 🚫 **Создавать глобальные сущности** за пределами плагина.
- 🚫 **Менять определения канонических сущностей** (Workspace, Project, Resource и т.д.).

---

## 6. Валидация

### 6.1. Программный валидатор

`scripts_01/plugin_contract.py` предоставляет:

- `ContractSeverity` — `WARN` / `ERROR`;
- `ContractViolation(field, message, severity)`;
- `validate_manifest(manifest) -> List[ContractViolation***REMOVED***` — проверка полей
  манифеста (name, version, description, events_subscribed, python_version);
- `validate_plugin_entry(entry) -> List[ContractViolation***REMOVED***` — манифест +
  инстанс (является ли `BasePlugin`, наличие lifecycle-методов).

Правила severity:

| Условие | Severity |
|---------|----------|
| Отсутствует/невалиден `name`, `version` или `description` | `ERROR` |
| `events_subscribed` не по шаблону `domain.event` | `WARN` |
| Инстанс не является `BasePlugin` | `ERROR` |
| Отсутствует lifecycle-метод | `WARN` |
| Несовместим `python_version` | `WARN` |

### 6.2. CLI

```bash
python -m scripts_01.plugin_api contract <plugin_name>
```

> Примечание: запуск через `python -m scripts_01.plugin_api` (из корня воркспейса),
> а не напрямую — модульный импорт `scripts_01.*` требует корень в `sys.path`.
> Если плагины не загрузились (state ERROR), команда покажет нарушения по
> ошибочной записи — это сигнал проверить логи загрузки плагина.

Выводит отчёт по контракту плагина:

```
✅ Contract OK — hello_world v1.0.0
```

или при нарушениях:

```
❌ Contract violations for demo (2):
   [ERROR***REMOVED*** manifest.name: invalid name 'Demo Plugin' (expected ^[a-z0-9_***REMOVED***+$)
   [ERROR***REMOVED*** manifest.description: description is empty
```

### 6.3. При загрузке

`PluginLoader.load()` после успешной загрузки прогоняет валидатор и печатает
warning при нарушениях (не блокирует загрузку — контракт не является
gateway-условием, но фиксируется в реестре).

---

## 7. Границы ответственности

| Сторона | Отвечает за |
|---------|-------------|
| **Ядро (PluginRegistry/Loader)** | Загрузка, lifecycle, подписки, регистрация инструментов, публикация событий `plugin.enabled/disabled`. |
| **Плагин** | Своя логика, состояние, подписки (декларативно), инструменты, CLI-команды. |
| **Контракт (plugin_contract.py)** | Формальная проверка границ: манифест + интерфейс + запреты. |

---

## 8. MCP-инструменты ядра (справочно)

MCP Server (`scripts_01/mcp_server.py`) экспонирует инструменты ядра для агентов
и MCP-клиентов через `tools/list`. Плагины не обязаны их знать, но могут
использовать их как сервисы ядра. Категория `policy` (Policy Engine):

| Инструмент | Схема | Назначение |
|------------|-------|------------|
| `policy_override` | `{"message": string***REMOVED***` | **Conversational User-Choice Override** (правило 11, ADR-009): фраза «use deepseek instead of claude for coding» / «используй freebuff для research» → `set_preference` → persist в `runtime_05/policies.json` |
| `policy_apply` *(planned)* | `{capability, project?, preferred_runtime?***REMOVED***` | Применить политику для задачи |
| `policy_list` *(planned)* | `{tag?, enabled?***REMOVED***` | Список политик |
| `policy_status` *(planned)* | `{***REMOVED***` | Статус Policy Engine |
| `pack_install` *(planned)* | `{source***REMOVED***` | Установить Policy Pack |
| `capability_list` *(planned)* | `{***REMOVED***` | Список capability и их Runtime |

> Полный перечень MCP-инструментов Policy Engine —
> `docs_10/core/POLICY_ENGINE_SPECIFICATION.md` §8.

---

## 9. Связанные документы

- `docs_10/plugin/FREEBUFF_PLUGIN_ARCHITECTURE.md` — архитектура плагина (пути, входные точки).
- `docs_10/plugin/FREEBUFF_PLUGIN_API.md` — API плагина.
- `docs_10/plugin/FREEBUFF_PLUGIN_QUICKSTART.md` — быстрый старт.
- `docs_10/core/POLICY_ENGINE_SPECIFICATION.md` — спецификация Policy Engine (MCP-инструменты §8).
- `scripts_01/plugin_api.py` — реализация Plugin API.
- `scripts_01/plugin_contract.py` — валидатор контракта.
