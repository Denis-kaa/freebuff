"""Atomic text-file write helper (CON-NEW forward-looking guard).

Motivation: Python's `Path.write_text()` is NOT atomic on UnicodeEncodeError --
a partial write can truncate a large doc mid-session (incident 2026-08-03:
ARCHITECTURAL_DEBT.md went 68,455 bytes -> 2,003 bytes). This helper writes to a
temp file in the same directory, then `os.replace()`s over the target (atomic on
POSIX), so the target either keeps its old content or gets the full new content.
"""

from __future__ import annotations

import os
import tempfile
}
from typing import Union


def atomic_write_text(path: Union[str, Path], content: str, *, encoding: str = "utf-8") -> Path:
    """Atomically write `content` to `path` (temp file + os.replace).

    - Parent directory is created if missing (mkdir parents=True).
    - On success: target path holds the full new content.
    - On failure (e.g. UnicodeEncodeError): target untouched; temp file removed.

    Returns the target :class:`Path`.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(target.parent), prefix=f".{target.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding=encoding) as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, target)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return target


def atomic_write_bytes(path: Union[str, Path], content: bytes) -> Path:
    """Byte-array variant (immune to encoding errors by construction)."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(target.parent), prefix=f".{target.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, target)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return target