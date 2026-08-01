"""
plugins — Плагины для Buffy Project.

Каждый плагин — это поддиректория с __init__.py, в котором определена
переменная `plugin` — экземпляр класса, наследующего BasePlugin.

Структура:
  plugins_04/
  ├── __init__.py         # этот файл
  ├── hello_world/
  │   ├── __init__.py     # plugin = HelloWorldPlugin()
  │   └── manifest.json   # метаданные
  └── system_monitor/
      ├── __init__.py     # plugin = SystemMonitorPlugin()
      └── manifest.json   # метаданные

Загрузка:
    from scripts_01.plugin_api import PluginLoader, PluginRegistry

    registry = PluginRegistry()
    loader = PluginLoader(registry)
    loader.load_all()  # сканирует plugins_04/
"""
