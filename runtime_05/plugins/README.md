# Runtime Plugins — система плагинов

> **Статус:** 🟡 Foundation (структура создана, плагины — по потребности)

## Назначение

`runtime_05/plugins/` содержит опциональные Python-модули для Runtime,
которым недостаточно стандартного MCP-адаптера:

- Кастомные протоколы (не-MCP)
- Сложная логика установки/обновления
- Интеграция с нестандартными API
- Трансляция между форматами

## Когда нужен плагин

| Ситуация | Решение |
|----------|---------|
| Runtime поддерживает MCP (stdio или HTTP) | ❌ Плагин НЕ нужен — используй `StdioMCPAdapter`/`HTTPMCPAdapter` |
| Runtime — subprocess с JSON-RPC | ✅ Нужен плагин — обёртка subprocess → унифицированный API |
| Runtime — HTTP API (OpenAI-compatible) | ❌ Плагин НЕ нужен — используй стандартный HTTP-адаптер |
| Runtime — нестандартный протокол | ✅ Нужен плагин — реализация `RuntimeAdapter` |
| Runtime требует сложной установки | ✅ Нужен плагин — кастомный installer |
| Runtime — bridge к другой экосистеме | ✅ Нужен плагин — через Bridge Layer |

## Структура плагина

```
runtime_05/plugins/my_runtime/
├── __init__.py          # Регистрация плагина
├── adapter.py           # RuntimeAdapter (если нестандартный протокол)
├── installer.py         # Кастомный установщик
└── manifest.yaml        # Метаданные плагина (версия, зависимости)
```

## API плагина

Плагин регистрируется в `AdapterRegistry`:

```python
# runtime_05/plugins/my_runtime/__init__.py
from freebuff_plugin.runtime.adapter import RuntimeAdapter, default_adapter_registry
from freebuff_plugin.runtime import AdapterType

class MyCustomAdapter(RuntimeAdapter):
    """Кастомный адаптер для нестандартного протокола."""
    ...

# Регистрация
default_adapter_registry.register("my_custom_type", MyCustomAdapter)
```

И в манифесте `runtime_05/providers/my_runtime.yaml`:

```yaml
adapter_type: my_custom_type    # ← ссылается на зарегистрированный тип
```

## Автообнаружение плагинов

При запуске `RuntimeRegistry` сканирует `runtime_05/plugins/` и:

1. Импортирует `__init__.py` каждого плагина
2. Плагин саморегистрируется в `default_adapter_registry`
3. Adapter type становится доступным для provider manifests

## Отличие providers от plugins

| | providers/ | plugins_04/ |
|---|-----------|---------|
| **Формат** | YAML-манифест | Python-модуль |
| **Назначение** | Описать Runtime | Расширить систему новым типом адаптера |
| **Обязательность** | Всегда (для каждого Runtime) | Опционально (только для нестандартных протоколов) |
| **Изменение ядра** | Не требуется | Не требуется |
| **Пример** | `freebuff.yaml` | (пока нет — MCP покрывает все текущие Runtime) |

## Marketplace-ready

Структура `runtime_05/plugins/` — часть Marketplace-архитектуры:

- **providers/** = каталог Runtime
- **plugins_04/** = расширения системы
- **recipes/** = человекочитаемые инструкции

См. `runtime_05/MARKETPLACE.md` для полной архитектуры.
