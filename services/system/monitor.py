"""
System Monitor: мониторинг состояния устройства.
v1.0.0: RAM, CPU, батарея, температура — всё что нужно знать о железе.

API (по SPEC.md):
    get_memory() → {"available_mb": int, "total_mb": int, "percent": float***REMOVED***
    get_cpu() → {"loadavg": str, "percent": float***REMOVED***
    get_battery() → {"level": int, "charging": bool***REMOVED*** | None
    get_temperature() → float | None
    health_check() → {"memory_ok": bool, "cpu_ok": bool, "battery_ok": bool***REMOVED***

Использование:
    from services.system.monitor import health_check
    if health_check()["memory_ok"***REMOVED***:
        print("RAM в норме")
"""

from __future__ import annotations

import os
from typing import Any


def get_memory() -> dict[str, int | float***REMOVED***:
    """Читает /proc/meminfo и возвращает доступную память в MB."""
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            meminfo = f.read()

        total_kb = 0
        available_kb = 0

        for line in meminfo.split("\n"):
            if line.startswith("MemTotal:"):
                total_kb = int(line.split()[1***REMOVED***)
            elif line.startswith("MemAvailable:"):
                available_kb = int(line.split()[1***REMOVED***)

        if total_kb == 0:
            return {"available_mb": 0, "total_mb": 0, "percent": 0.0***REMOVED***

        total_mb = total_kb // 1024
        available_mb = available_kb // 1024 if available_kb else total_mb
        used_percent = round((1 - available_mb / total_mb) * 100, 1)

        return {
            "available_mb": available_mb,
            "total_mb": total_mb,
            "percent": used_percent,
        ***REMOVED***
    except (OSError, ValueError, IndexError):
        return {"available_mb": 0, "total_mb": 0, "percent": 0.0***REMOVED***


def get_cpu() -> dict[str, Any***REMOVED***:
    """Читает /proc/loadavg и возвращает загрузку CPU."""
    try:
        with open("/proc/loadavg", "r", encoding="utf-8") as f:
            loadavg = f.read().strip()
        parts = loadavg.split()
        load_1m = float(parts[0***REMOVED***) if parts else 0.0

        # Примерный процент (load / cores)
        try:
            cores = os.cpu_count() or 4
        except Exception:
            cores = 4
        percent = round(min(load_1m / cores * 100, 100), 1)

        return {"loadavg": loadavg, "percent": percent, "error": False***REMOVED***
    except (OSError, ValueError):
        return {"loadavg": "unknown", "percent": 0.0, "error": True***REMOVED***


def get_battery() -> dict[str, Any***REMOVED*** | None:
    """Читает информацию о батарее из Android sysfs."""
    battery_paths = [
        "/sys/class/power_supply/battery/capacity",
        "/sys/class/power_supply/BAT0/capacity",
    ***REMOVED***

    for path in battery_paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                level = int(f.read().strip())
        except (OSError, ValueError):
            continue

        # Проверяем статус зарядки
        charging = False
        status_path = os.path.join(os.path.dirname(path), "status")
        try:
            with open(status_path, "r", encoding="utf-8") as f:
                charging = "charging" in f.read().lower() or "full" in f.read().lower()
        except OSError:
            pass

        return {"level": level, "charging": charging***REMOVED***

    return None


def get_temperature() -> float | None:
    """Читает температуру CPU из thermal sysfs."""
    thermal_paths = [
        "/sys/class/thermal/thermal_zone0/temp",
        "/sys/class/thermal/thermal_zone1/temp",
    ***REMOVED***

    for path in thermal_paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                temp_raw = int(f.read().strip())
                return temp_raw / 1000.0  # миллиградусы → градусы
        except (OSError, ValueError):
            continue

    return None


def health_check() -> dict[str, bool***REMOVED***:
    """
    Проверка здоровья системы.
    Возвращает словарь с булевыми флагами.
    """
    mem = get_memory()
    cpu = get_cpu()
    battery = get_battery()

    return {
        "memory_ok": mem["available_mb"***REMOVED*** >= 200,  # минимум 200 MB свободно
        "cpu_ok": not cpu.get("error", False) and cpu["percent"***REMOVED*** <= 90,
        "battery_ok": battery is None or battery["level"***REMOVED*** >= 10 or battery["charging"***REMOVED***,
    ***REMOVED***
