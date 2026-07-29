"""
System Monitor: backward-compatible shim.

The implementation has been moved to ``services/system/monitor.py``
as part of the v5 restructure.  This module re-exports the same API
so that existing imports continue to work.
"""

from __future__ import annotations

from services.system.monitor import (  # noqa: F401
    get_battery,
    get_cpu,
    get_memory,
    get_temperature,
    health_check,
)
