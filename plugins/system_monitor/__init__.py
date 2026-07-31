"""
system_monitor — System Monitor Plugin для Buffy.

Функции:
  - cpu / memory / battery / temperature: текущие метрики системы
  - health: полный health check
  - start_watch / stop_watch: фоновый периодический мониторинг
  - status: сводка всех метрик
  - Публикация system.metrics событий при watch-цикле

Fallback-реализации через /proc/* для Termux-совместимости.
"""

import threading
import time
***REMOVED***

from scripts.plugin_api import BasePlugin, PluginMeta, PluginResult

try:
    from scripts.system_monitor import (  # type: ignore
        get_battery,
        get_cpu,
        get_memory,
        get_temperature,
        health_check,
    )

    _has_monitor = True
except ImportError:
    _has_monitor = False


class SystemMonitorPlugin(BasePlugin):
    """Мониторинг CPU, памяти, батареи, температуры и health check."""

    def __init__(self):
        super().__init__(
            name="system_monitor",
            version="1.0.0",
            description="System Monitor — CPU, память, батарея, температура, health check",
        )
        self._watching: bool = False
        self._watch_thread: threading.Thread | None = None
        self._watch_interval: int = 5
        self._last_readings: dict = {***REMOVED***

    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name=self._name,
            version=self._version,
            description=self._description,
            events_subscribed=self.events_subscribed,
        )

    @property
    def events_subscribed(self):
        return ["system.*"***REMOVED***

    # ── Lifecycle ───────────────────────────────────────────

    def on_load(self):
        if _has_monitor:
            print("💻 system_monitor: loaded (monitor module: ✅)")
        else:
            print("💻 system_monitor: loaded (monitor module: ❌ — using fallbacks)")

    def on_unload(self):
        self._watching = False
        self._watch_thread = None

    def on_event(self, event):
        return

    # ── Действия ───────────────────────────────────────────

    def do_cpu(self) -> dict:
        """Загрузка CPU."""
        try:
            if _has_monitor:
                cpu_info = get_cpu()
                self._last_readings["cpu"***REMOVED*** = cpu_info
                return {"success": True, "data": cpu_info***REMOVED***
            return self._read_cpu_fallback()
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def do_memory(self) -> dict:
        """Использование памяти."""
        try:
            if _has_monitor:
                mem_info = get_memory()
                self._last_readings["memory"***REMOVED*** = mem_info
                return {"success": True, "data": mem_info***REMOVED***
            return self._read_memory_fallback()
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def do_battery(self) -> dict:
        """Статус батареи."""
        try:
            if _has_monitor:
                batt_info = get_battery()
                self._last_readings["battery"***REMOVED*** = batt_info
                return {"success": True, "data": batt_info***REMOVED***
            return self._read_battery_fallback()
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def do_temperature(self) -> dict:
        """Температура."""
        try:
            if _has_monitor:
                temp_info = get_temperature()
                self._last_readings["temperature"***REMOVED*** = temp_info
                return {"success": True, "data": temp_info***REMOVED***
            return self._read_temp_fallback()
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def do_health(self) -> dict:
        """Полный health check."""
        try:
            if _has_monitor:
                hc = health_check()
                self._last_readings["health"***REMOVED*** = hc
                return {"success": True, "data": hc***REMOVED***
            cpu = self._read_cpu_fallback().get("data", {***REMOVED***)
            mem = self._read_memory_fallback().get("data", {***REMOVED***)
            return {
                "success": True,
                "data": {
                    "status": "degraded",
                    "cpu": cpu,
                    "memory": mem,
                    "note": "Using fallback implementation (services.system.monitor not available)",
                ***REMOVED***,
            ***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def do_start_watch(self, interval: int = 5) -> dict:
        """Запускает периодический мониторинг в фоне.

        Args:
            interval: интервал между замерами (секунд)
        """
        if self._watching:
            return {"success": True, "data": "Already watching"***REMOVED***
        self._watch_interval = max(1, int(interval))
        self._watching = True
        self._watch_thread = threading.Thread(
            target=self._watch_loop, daemon=True, name="system-monitor-watch"
        )
        self._watch_thread.start()
        return {
            "success": True,
            "data": f"Watching every {self._watch_interval***REMOVED***s",
        ***REMOVED***

    def do_stop_watch(self) -> dict:
        """Останавливает периодический мониторинг."""
        self._watching = False
        self._watch_thread = None
        return {"success": True, "data": "Watch stopped"***REMOVED***

    def do_status(self) -> dict:
        """Сводка всех метрик системы."""
        cpu = self.do_cpu().get("data", {***REMOVED***)
        mem = self.do_memory().get("data", {***REMOVED***)
        batt = self.do_battery().get("data", {***REMOVED***)
        temp = self.do_temperature().get("data", {***REMOVED***)
        return {
            "success": True,
            "data": {
                "cpu": cpu,
                "memory": mem,
                "battery": batt,
                "temperature": temp,
                "watching": self._watching,
                "watch_interval": self._watch_interval,
            ***REMOVED***,
        ***REMOVED***

    # ── Fallback-реализации (Termux /proc) ────────────────

    def _read_cpu_fallback(self) -> dict:
        """Читает CPU загрузку из /proc/stat."""
        try:
            with open("/proc/stat") as f:
                lines = f.readlines()
            total = 0
            idle = 0
            for line in lines:
                if line.startswith("cpu "):
                    parts = line.split()
                    idle = int(parts[4***REMOVED***)
                    total = sum(int(v) for v in parts[1:***REMOVED***)
                    break
            usage_pct = 0.0
            if total > 0:
                usage_pct = round((1.0 - idle / total) * 100, 1)
            cores = max(
                1,
                len([l for l in lines if l.startswith("cpu") and not l.startswith("cpu ")***REMOVED***),
            )
            return {
                "success": True,
                "data": {
                    "usage_percent": usage_pct,
                    "cores": cores,
                    "idle_percent": round(idle / total * 100, 1) if total > 0 else 0.0,
                    "source": "/proc/stat",
                ***REMOVED***,
            ***REMOVED***
        except Exception:
            return {"success": False, "error": "Cannot read CPU info"***REMOVED***

    def _read_memory_fallback(self) -> dict:
        """Читает использование памяти из /proc/meminfo."""
        try:
            mem_info = {***REMOVED***
            with open("/proc/meminfo") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        key = parts[0***REMOVED***.strip()
                        val_str = parts[1***REMOVED***.strip().split()[0***REMOVED***
                        mem_info[key***REMOVED*** = int(val_str) // 1024  # kB → MB
            total = mem_info.get("MemTotal")
            available = mem_info.get("MemAvailable")
            if total is None or available is None:
                return {"success": False, "error": "Cannot read memory info"***REMOVED***
            used = total - available
            usage_pct = round(used / total * 100, 1) if total > 0 else 0.0
            return {
                "success": True,
                "data": {
                    "total_mb": total,
                    "used_mb": used,
                    "available_mb": available,
                    "usage_percent": usage_pct,
                    "source": "/proc/meminfo",
                ***REMOVED***,
            ***REMOVED***
        except (ValueError, IndexError):
            return {"success": False, "error": "Cannot read memory info"***REMOVED***
        except Exception:
            return {"success": False, "error": "Cannot read memory info"***REMOVED***

    def _read_battery_fallback(self) -> dict:
        """Читает статус батареи из /sys/class/power_supply."""
        try:
            base = "/sys/class/power_supply"
            ***REMOVED***

            batt_dirs = [p for p in Path(base).iterdir() if p.is_dir()***REMOVED***
            for d in batt_dirs:
                cap_file = d / "capacity"
                if cap_file.exists():
                    capacity = int(cap_file.read_text().strip())
                    return {
                        "success": True,
                        "data": {
                            "capacity": capacity,
                            "charging": "Unknown",
                            "source": str(d),
                        ***REMOVED***,
                    ***REMOVED***
            return {"success": False, "error": "No battery found"***REMOVED***
        except Exception:
            return {"success": False, "error": "No battery found"***REMOVED***

    def _read_temp_fallback(self) -> dict:
        """Читает температуру из /sys/class/thermal."""
        try:
            ***REMOVED***

            thermal = Path("/sys/class/thermal")
            temps = [***REMOVED***
            for zone in sorted(thermal.glob("thermal_zone*")):
                temp_file = zone / "temp"
                if temp_file.exists():
                    raw = int(temp_file.read_text().strip())
                    temps.append(round(raw / 1000.0, 1))
            if temps:
                return {
                    "success": True,
                    "data": {
                        "temperature_c": max(temps),
                        "zones": len(temps),
                        "source": "/sys/class/thermal",
                    ***REMOVED***,
                ***REMOVED***
            return {"success": False, "error": "No thermal zones found"***REMOVED***
        except Exception:
            return {"success": False, "error": "No thermal zones found"***REMOVED***

    # ── Фоновый watch-цикл ────────────────────────────────

    def _watch_loop(self):
        """Фоновый цикл: замеряет метрики и публикует system.metrics."""
        while self._watching:
            try:
                reading = {
                    "cpu": self.do_cpu().get("data", {***REMOVED***),
                    "memory": self.do_memory().get("data", {***REMOVED***),
                ***REMOVED***
                self._last_readings["watch"***REMOVED*** = reading
            except Exception:
                pass
            time.sleep(self._watch_interval)


# Экземпляр плагина (обнаруживается PluginLoader по переменной `plugin`)
plugin = SystemMonitorPlugin()
