"""scripts_01/corpus_persistence.py — Persistent URL corpus для research_* tools.

AGENTS.md §5 REGISTER-FIRST: registered → prompt_written → implemented.
Lifecycle: closed в v5.189.54 (этот файл).
Reference: pompts_11/096_19_corpus_persistence.md.

Семантика (Option C, design validation §A): per-(url, source) idempotent.
Хранение: ``data_13/corpus/<sha256(url.encode('utf-8'))>.jsonl``.
Concurrency: ``threading.Lock`` на module level + append mode + write-temp-rename.
Безопасность: sha256 в filename (path-traversal исключён), reject non-http(s),
hardcap ``MAX_URL_LEN = 2048`` (DoS protection).
Fail-safe: corrupt JSONL строки пропускаются с warning (lookup не падает).

Использование::

    from scripts_01.corpus_persistence import (
        CorpusEntry, PersistResult,
        persist, lookup, lookup_by_source, list_all, stats,
    )

    result = persist("https://example.com", source="research_web",
                     title="Example", metadata={"status": 200***REMOVED***)
    assert isinstance(result, PersistResult)
    assert result.is_duplicate is False

    entries = lookup("https://example.com")
    for e in entries:
        print(e.source, e.timestamp, e.title)
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as _dt
import hashlib
import json
import os
***REMOVED***
import sys
import threading
from dataclasses import asdict, dataclass, field
***REMOVED***
from typing import Any, Dict, List, Optional

__all__ = [
    "CorpusEntry",
    "PersistResult",
    "DEFAULT_CORPUS_DIR",
    "MAX_URL_LEN",
    "persist",
    "lookup",
    "lookup_by_source",
    "list_all",
    "stats",
    "main",
    "clear",  # для тестов (test-only convenience)
***REMOVED***

# ─── constants ──────────────────────────────────────────────────────────────

# Корневой каталог corpus (относительно CWD; используется ``Path()`` напрямую).
DEFAULT_CORPUS_DIR: Path = Path("data_13/corpus")

# Жёсткий лимит длины URL (design risk #3 — DoS protection).
MAX_URL_LEN: int = 2048

# Консистентный URL-предикат: только http(s), path треб. ≥1 char,
# reject schemes file://, javascript:, data: и прочие небезопасные.
_URL_RE: "re.Pattern[str***REMOVED***" = re.compile(r"^https?://\S+$")

# Домен процесса-уровневый lock — single-process model (Freebuff runtime).
# Для multi-process нужен fcntl — out of scope для v1.
FILE_LOCK: "threading.Lock" = threading.Lock()


# ─── dataclasses ─────────────────────────────────────────────────────────────


@dataclass
class CorpusEntry:
    """Одна запись corpus (одна строка JSONL).

    Required: url, source, timestamp.
    Optional: title, metadata.
    """
    url: str
    source: str
    timestamp: str  # ISO 8601 UTC, всегда 'Z' suffix
    title: Optional[str***REMOVED*** = None
    metadata: Dict[str, Any***REMOVED*** = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any***REMOVED***:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any***REMOVED***) -> "CorpusEntry":
        """Извлечь из dict, игнорируя лишние ключи.

        Устойчивость к evolving schema (forward-compat): новые поля не роняют
        парсер (паттерн ``MissingItem.from_dict``).
        """
        known = {"url", "source", "timestamp", "title", "metadata"***REMOVED***
        kwargs = {k: v for k, v in data.items() if k in known***REMOVED***
        # Гарантируем metadata — даже если отсутствует у читаемой строки.
        kwargs.setdefault("metadata", {***REMOVED***)
        return cls(**kwargs)


@dataclass
class PersistResult:
    """Result of ``persist()``: новая запись + flag duplicate-notify."""
    entry: CorpusEntry
    is_duplicate: bool  # True ↔ существующая (url, source) была перезаписана


# ─── internal helpers ────────────────────────────────────────────────────────


def _now_iso() -> str:
    """UTC ISO 8601 с суффиксом ``Z`` (UTC marker)."""
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_url(url: str) -> str:
    """URL → sha256 hex (64 chars).

    NOTE: ключ от raw URL (не normalized). Два URL, отличающихся только trailing
    slash или scheme case, дают разные ключи — намеренно (per design draft §3).
    """
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _validate_url(url: Any) -> None:
    """Reject non-http(s) URLs / empty / overlong / non-string.

    Raises:
        TypeError: если url не str.
        ValueError: если url пустой или не проходит другие проверки.
    """
    if not isinstance(url, str):
        raise TypeError(f"url must be str, got {type(url).__name__***REMOVED***")
    if not url:
        raise ValueError("url is empty")
    if len(url) > MAX_URL_LEN:
        raise ValueError(
            f"url len={len(url)***REMOVED*** > MAX_URL_LEN={MAX_URL_LEN***REMOVED*** (DoS hardcap)"
        )
    if not _URL_RE.match(url):
        raise ValueError(
            f"url must match http(s) scheme (got {url[:64***REMOVED***!r***REMOVED***…)"
        )


def _entry_path(url: str, root: Optional[Path***REMOVED*** = None) -> Path:
    """``<root>/<sha256(url)>.jsonl`` — sha256 hex гарантирует path-safety."""
    base = root if root is not None else DEFAULT_CORPUS_DIR
    return base / f"{_sha256_url(url)***REMOVED***.jsonl"


def _read_jsonl_safely(path: Path) -> List[Dict[str, Any***REMOVED******REMOVED***:
    """Прочитать JSONL с corrupt-line recovery (fail-safe).

    Empty list если файла нет. Corrupt строки скипаются + warning в stderr
    (lookup resilient к повреждённому jsonl).
    """
    if not path.is_file():
        return [***REMOVED***
    out: List[Dict[str, Any***REMOVED******REMOVED*** = [***REMOVED***
    try:
        with path.open("r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    sys.stderr.write(
                        f"corpus_persistence: corrupt JSONL at {path***REMOVED***:{line_num***REMOVED***: {exc***REMOVED***; "
                        f"line skipped\n"
                    )
    except OSError as exc:
        sys.stderr.write(f"corpus_persistence: read {path***REMOVED***: {exc***REMOVED***\n")
    return out


def _clear_locked(root: Path) -> int:
    """Test/admin hook: удалить все *.jsonl в root (внутри FILE_LOCK).

    Используется в test fixtures для hermetic setup и as admin reset.
    Возвращает количество удалённых файлов.
    """
    if not root.is_dir():
        return 0
    n = 0
    for p in root.glob("*.jsonl"):
        try:
            p.unlink()
            n += 1
        except OSError:
            pass
    return n


# ─── public API ──────────────────────────────────────────────────────────────


def persist(
    url: str,
    source: str,
    *,
    title: Optional[str***REMOVED*** = None,
    metadata: Optional[Dict[str, Any***REMOVED******REMOVED*** = None,
    root: Optional[Path***REMOVED*** = None,
) -> PersistResult:
    """Persist ``CorpusEntry`` для ``(url, source)``. Per-(url, source) idempotent.

    Returns ``PersistResult.is_duplicate=True`` если существующая запись
    для ``(url, source)`` была перезаписана (новая запись тот же source).

    Thread-safe (FILE_LOCK). Атомарность: write-tmp + fsync + rename.

    Args:
        url: http(s) URL для сохранения. Валидируется (MAX_URL_LEN, scheme).
        source: имя источника (``research_web``, ``manual``, ``research_factory``).
        title: optional human-readable title.
        metadata: optional dict с произвольными атрибутами (status, lang, etc.).
        root: опциональный override для ``DEFAULT_CORPUS_DIR`` (тесты используют
            ``tmp_path``); None = default.
    """
    _validate_url(url)
    if not source or not isinstance(source, str):
        raise ValueError(f"source must be non-empty str, got {source!r***REMOVED***")

    entry = CorpusEntry(
        url=url,
        source=source,
        timestamp=_now_iso(),
        title=title,
        metadata=dict(metadata or {***REMOVED***),
    )

    path = _entry_path(url, root=root)
    with FILE_LOCK:
        existing = _read_jsonl_safely(path)
        # Option C: дроп существующей записи для ТОГО ЖЕ source; оставляем остальные.
        kept = [r for r in existing if r.get("source") != source***REMOVED***
        is_dup = len(kept) != len(existing)
        kept.append(entry.to_dict())

        # Atomic write: write-tmp → fsync → rename. Cleanup tmp on error.
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        try:
            with tmp.open("w", encoding="utf-8") as f:
                for rec in kept:
                    f.write(json.dumps(rec, ensure_ascii=False, sort_keys=False))
                    f.write("\n")
                f.flush()
                os.fsync(f.fileno())
            tmp.replace(path)
        except Exception:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
            raise
    return PersistResult(entry=entry, is_duplicate=is_dup)


def lookup(url: str, *, root: Optional[Path***REMOVED*** = None) -> List[CorpusEntry***REMOVED***:
    """Все entries для ``url`` across sources. ``[***REMOVED***`` если URL не persist-нут."""
    _validate_url(url)
    raw = _read_jsonl_safely(_entry_path(url, root=root))
    return [CorpusEntry.from_dict(r) for r in raw***REMOVED***


def lookup_by_source(
    source: str, *, root: Optional[Path***REMOVED*** = None,
) -> List[CorpusEntry***REMOVED***:
    """Все entries с ``source == <source>`` across URLs."""
    if not source or not isinstance(source, str):
        raise ValueError(f"source must be non-empty str, got {source!r***REMOVED***")
    base = root if root is not None else DEFAULT_CORPUS_DIR
    if not base.is_dir():
        return [***REMOVED***
    out: List[CorpusEntry***REMOVED*** = [***REMOVED***
    for jsonl in sorted(base.glob("*.jsonl")):
        for raw in _read_jsonl_safely(jsonl):
            if raw.get("source") == source:
                out.append(CorpusEntry.from_dict(raw))
    return out


def list_all(*, root: Optional[Path***REMOVED*** = None) -> List[CorpusEntry***REMOVED***:
    """Все entries в corpus (порядок: sorted by file path → read order)."""
    base = root if root is not None else DEFAULT_CORPUS_DIR
    if not base.is_dir():
        return [***REMOVED***
    out: List[CorpusEntry***REMOVED*** = [***REMOVED***
    for jsonl in sorted(base.glob("*.jsonl")):
        for raw in _read_jsonl_safely(jsonl):
            out.append(CorpusEntry.from_dict(raw))
    return out


def stats(*, root: Optional[Path***REMOVED*** = None) -> Dict[str, int***REMOVED***:
    """Counts по source. ``{source_name: count***REMOVED***``."""
    base = root if root is not None else DEFAULT_CORPUS_DIR
    if not base.is_dir():
        return {***REMOVED***
    out: Dict[str, int***REMOVED*** = {***REMOVED***
    for jsonl in sorted(base.glob("*.jsonl")):
        for raw in _read_jsonl_safely(jsonl):
            src = raw.get("source", "(unknown)")
            out[src***REMOVED*** = out.get(src, 0) + 1
    return out


def clear(*, root: Optional[Path***REMOVED*** = None) -> int:
    """Удалить все ``*.jsonl`` в ``root`` (test/admin convenience).

    Returns: количество удалённых файлов.

    NOTE: не сбрасывает FILE_LOCK (lock persists across call; this is a
    destructive utility — use with care).
    """
    base = root if root is not None else DEFAULT_CORPUS_DIR
    with FILE_LOCK:
        return _clear_locked(base)


# ─── CLI ─────────────────────────────────────────────────────────────────────


def _print_json(payload: Any) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


def _parse_metadata_kv(pairs: Optional[List[str***REMOVED******REMOVED***) -> Optional[Dict[str, str***REMOVED******REMOVED***:
    """``--metadata`` CLI helper: ``key=value`` (повторяемый)."""
    if pairs is None:
        return None
    out: Dict[str, str***REMOVED*** = {***REMOVED***
    for pair in pairs:
        if "=" not in pair:
            sys.stderr.write(f"metadata must be key=value, got {pair!r***REMOVED***\n")
            raise SystemExit(2)
        k, v = pair.split("=", 1)
        out[k.strip()***REMOVED*** = v.strip()
    return out


def _cli_add(args: argparse.Namespace) -> int:
    try:
        md = _parse_metadata_kv(args.metadata)
        result = persist(
            args.url, args.source,
            title=args.title, metadata=md, root=args.corpus_root,
        )
    except (TypeError, ValueError) as exc:
        sys.stderr.write(f"error: {exc***REMOVED***\n")
        return 2
    if args.json:
        _print_json({
            "entry": result.entry.to_dict(),
            "is_duplicate": result.is_duplicate,
        ***REMOVED***)
        return 0
    flag = "(duplicate — overwritten)" if result.is_duplicate else "(new)"
    sys.stdout.write(
        f"persisted {flag***REMOVED***: {args.url***REMOVED*** source={args.source***REMOVED*** "
        f"sha256={_sha256_url(args.url)[:12***REMOVED******REMOVED***…\n"
    )
    return 0


def _cli_lookup(args: argparse.Namespace) -> int:
    try:
        entries = lookup(args.url, root=args.corpus_root)
    except (TypeError, ValueError) as exc:
        sys.stderr.write(f"error: {exc***REMOVED***\n")
        return 2
    if args.json:
        _print_json([e.to_dict() for e in entries***REMOVED***)
        return 0
    if not entries:
        sys.stdout.write(f"(no entries) {args.url***REMOVED***\n")
        return 0
    for e in entries:
        sys.stdout.write(f"- [{e.source***REMOVED******REMOVED*** {e.timestamp***REMOVED***: {e.url***REMOVED***\n")
        if e.title:
            sys.stdout.write(f"  title: {e.title***REMOVED***\n")
        if e.metadata:
            sys.stdout.write(f"  metadata: {json.dumps(e.metadata, ensure_ascii=False)***REMOVED***\n")
    return 0


def _cli_list(args: argparse.Namespace) -> int:
    if args.source:
        try:
            entries = lookup_by_source(args.source, root=args.corpus_root)
        except ValueError as exc:
            sys.stderr.write(f"error: {exc***REMOVED***\n")
            return 2
    else:
        entries = list_all(root=args.corpus_root)
    if args.json:
        _print_json([e.to_dict() for e in entries***REMOVED***)
        return 0
    if not entries:
        sys.stdout.write("(empty corpus)\n")
        return 0
    for e in entries:
        sys.stdout.write(f"- [{e.source***REMOVED******REMOVED*** {e.timestamp***REMOVED***: {e.url***REMOVED***\n")
    return 0


def _cli_stats(args: argparse.Namespace) -> int:
    s = stats(root=args.corpus_root)
    if args.json:
        _print_json(s)
        return 0
    if not s:
        sys.stdout.write("(empty corpus)\n")
        return 0
    for src, count in sorted(s.items()):
        sys.stdout.write(f"- {src***REMOVED***: {count***REMOVED***\n")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="corpus_persistence",
        description=__doc__.splitlines()[0***REMOVED*** if __doc__ else "URL corpus",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version="corpus_persistence 1.0.0 (Option C schema, ADR-016-compatible)",
    )
    parser.add_argument(
        "--root",
        dest="corpus_root",
        type=Path,  # argparse auto-converts str → Path; default None.
        default=None,
        help="override DEFAULT_CORPUS_DIR (default=data_13/corpus); use для tests или альтернативных deployment-ов (staging vs prod)",
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    # add
    p_add = sub.add_parser("add", help="persist URL в corpus")
    p_add.add_argument("url", help="http(s) URL для сохранения")
    p_add.add_argument("--source", required=True, help="имя источника")
    p_add.add_argument("--title", default=None, help="опциональный заголовок")
    p_add.add_argument(
        "--metadata", action="append", default=None,
        help="key=value (повторяемый)",
    )
    p_add.add_argument("--json", action="store_true", help="JSON-вывод")
    p_add.set_defaults(func=_cli_add)

    # lookup
    p_lookup = sub.add_parser("lookup", help="поиск entries для URL")
    p_lookup.add_argument("url", help="URL для поиска")
    p_lookup.add_argument("--json", action="store_true")
    p_lookup.set_defaults(func=_cli_lookup)

    # list
    p_list = sub.add_parser("list", help="все entries / filter by source")
    p_list.add_argument("--source", default=None, help="фильтр по source")
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(func=_cli_list)

    # stats
    p_stats = sub.add_parser("stats", help="counts по sources")
    p_stats.add_argument("--json", action="store_true")
    p_stats.set_defaults(func=_cli_stats)

    return parser


def main(argv: Optional[List[str***REMOVED******REMOVED*** = None) -> int:
    """CLI entry point.

    Usage::

        python -m scripts_01.corpus_persistence add <URL> --source <SRC> …
        python -m scripts_01.corpus_persistence lookup <URL> [--json***REMOVED***
        python -m scripts_01.corpus_persistence list [--source S***REMOVED*** [--json***REMOVED***
        python -m scripts_01.corpus_persistence stats [--json***REMOVED***
        python -m scripts_01.corpus_persistence --version
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    func = args.func
    return func(args)  # type: ignore[no-any-return***REMOVED***  # argparse set_defaults ergases func type


if __name__ == "__main__":
    sys.exit(main())
