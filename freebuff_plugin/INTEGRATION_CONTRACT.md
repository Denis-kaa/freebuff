# INTEGRATION CONTRACT — Core ↔ Plugin Boundary

> **Дата:** 2026-07-29
> **Версия:** 1.0.0
> **Основание:** [promt16.md***REMOVED***(../pompts/promt16.md) Задача 2

---

## Принцип

Buffy — Infrastructure Plugin. Ядро и плагин связаны через **два файла** и только через них.

```
CORE (scripts/)                    PLUGIN (freebuff_plugin/)
──────────────────                  ──────────────────────────
mcp_server.py                       __init__.py  ← ЕДИНСТВЕННАЯ точка входа
  └── from freebuff_plugin             для ядра. Экспортирует:
      import (BridgeLayer,             BridgeLayer
      BootstrapEngine,                  BootstrapEngine
      RuntimeRegistry,                  RuntimeRegistry
      RuntimeCapabilityRegistry)        RuntimeCapabilityRegistry
                                   bridge.py  ← ЕДИНСТВЕННАЯ точка входа
                                      для плагина в ядро.
                                      Экспортирует:
                                      get_stream_bridge()
                                      session_start/end/list()
```

---

## Правила

### Ядро → Плагин
1. Импорт **только** через `from freebuff_plugin import ...`
2. Никаких `from freebuff_plugin.submodule import ...`
3. Все импорты обёрнуты в `try/except ImportError`
4. При отсутствии плагина — функциональность Cowork/Teamwork отключается с сообщением, ядро не падает

### Плагин → Ядро
1. Импорт **только** через `from freebuff_plugin import bridge`
2. Доступ к StreamBridge — через `bridge.get_stream_bridge()`
3. Доступ к ContextManager — через bridge (уже есть)
4. **Никаких** `from scripts.xxx import ...` в других файлах плагина
5. **Никаких** жёстких путей (`["scripts/mcp_server.py"***REMOVED***`) — все пути параметризованы

---

## Graceful Degradation

```python
# В ядре (scripts/mcp_server.py):
def _get_bridge_layer(self):
    try:
        from freebuff_plugin import BridgeLayer
        ...
    except ImportError:
        print("⚠ BridgeLayer unavailable (plugin not loaded)")
        return None
```

Плагин опционален. Ядро работает без него.
Если плагин удалён — соответствующая MCP-функциональность отключается.

---

## Проверка границы

```bash# Ядро → Плагин: только через __init__.py
    grep -rn "from freebuff_plugin\." scripts/ --include="*.py" | grep -v __init__\.py

    # Плагин → Ядро: только через bridge.py
    grep -rn "from scripts\." freebuff_plugin/ --include="*.py" | grep -v bridge\.py

    # Жёсткие пути в плагине
    grep -rn "scripts/" freebuff_plugin/ --include="*.py" | grep -v bridge\.py | grep -v __init__\.py
```

Все три команды должны выдавать **пустой вывод**.

---

## Связанные документы

- [ARCHITECTURE_PRINCIPLES.md***REMOVED***(../docs/core/ARCHITECTURE_PRINCIPLES.md) — раздел «Loosely Coupled»
- [BUFFY.md***REMOVED***(../BUFFY.md) — раздел «Buffy — Infrastructure Plugin»
- [MARKETPLACE.md***REMOVED***(../runtime/MARKETPLACE.md) — Marketplace-ready архитектура (providers/ + plugins/)
- [CODE_QUALITY_STANDARD.md***REMOVED***(../docs/core/CODE_QUALITY_STANDARD.md) — стандарты качества
