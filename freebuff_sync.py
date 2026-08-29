#!/usr/bin/env python3
"""Compatibility entry point for ``python -m freebuff_sync``."""
from __future__ import annotations

from scripts_01.freebuff_sync import main


if __name__ == "__main__":
    raise SystemExit(main())
