"""Platform configuration — minimal config for wrapper and other modules.

Provides FREEBUFF_BINARY (path to the freebuff CLI binary) and PROOT_DISTRO
(Termux proot distro name).
"""

from __future__ import annotations

import shutil
from pathlib import Path

# ── Freebuff binary ─────────────────────────────────────────────
# In production this resolves to the installed CLI binary.
# Tests patch this value via freebuff_plugin_03.config.FREEBUFF_BINARY.
FREEBUFF_BINARY: Path = Path(
    shutil.which("freebuff")
    or shutil.which("freebuff-cli")
    or "/usr/local/bin/freebuff"
)

# ── Termux / proot ──────────────────────────────────────────────
PROOT_DISTRO: str = "ubuntu"
