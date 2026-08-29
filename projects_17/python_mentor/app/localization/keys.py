"""Rotating credential pool for the optional external Gemini brain.

The pool holds candidate keys and serves one at a time in round-robin order.
On a reported failure it advances to the next key. Values are never logged,
printed, or written back to disk; the pool only returns them to the caller
in-memory so a provider can build a request header/URL.

The active key file (a path outside the repository, e.g. ``.keys/gemini_active.keys``)
must be git-ignored and readable only by the owner.
"""

from __future__ import annotations

import threading
***REMOVED***
from typing import Sequence


def _read_keys(path: str | Path) -> list[str***REMOVED***:
    """Read one credential per non-empty, non-comment line."""
    raw = Path(path).read_text(encoding="utf-8", errors="replace")
    keys: list[str***REMOVED*** = [***REMOVED***
    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        # Accept both one-credential-per-line and KEY_NAME=value files.
        if "=" in line:
            name, value = line.split("=", 1)
            if name.strip().replace("_", "").isalnum():
                line = value.strip()
        if line:
            keys.append(line)
    if not keys:
        raise ValueError(f"no credentials found in {path***REMOVED***")
    return keys


class GeminiKeyPool:
    """Thread-safe round-robin rotation over a sequence of candidate keys.

    ``acquire()`` returns the current key index/credential without logging it;
    ``mark_failed()`` advances rotation so the next call uses another key.
    """

    def __init__(self, keys: Sequence[str***REMOVED*** | None = None, *, active_file: str | Path | None = None) -> None:
        if keys is not None:
            self._keys: list[str***REMOVED*** = list(keys)
        elif active_file is not None:
            self._keys = _read_keys(active_file)
        else:
            raise ValueError("GeminiKeyPool requires keys or an active_file")
        if not self._keys:
            raise ValueError("GeminiKeyPool has no keys")
        self._index = 0
        self._lock = threading.Lock()
        self._state: dict[int, int***REMOVED*** = {***REMOVED***  # key_index -> consecutive failures

    @property
    def key_count(self) -> int:
        return len(self._keys)

    def acquire(self) -> tuple[int, str***REMOVED***:
        """Return (key_index, credential) for the current rotation slot."""
        with self._lock:
            return self._index, self._keys[self._index***REMOVED***

    def mark_failed(self, key_index: int) -> None:
        """Advance rotation away from a failed key (thread-safe)."""
        with self._lock:
            self._state[key_index***REMOVED*** = self._state.get(key_index, 0) + 1
            self._index = (self._index + 1) % len(self._keys)

    def mark_success(self, key_index: int) -> None:
        with self._lock:
            self._state[key_index***REMOVED*** = 0

    def failures(self, key_index: int) -> int:
        with self._lock:
            return self._state.get(key_index, 0)

    def __repr__(self) -> str:  # never leak credentials
        return f"GeminiKeyPool(count={len(self._keys)***REMOVED***)"
