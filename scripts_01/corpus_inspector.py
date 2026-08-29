"""scripts_01/corpus_inspector.py — Read-only stats + safe-cleanup tool для corpus_persistence.

AGENTS.md §5 REGISTER-FIRST lifecycle (v5.189.58):
    registered → prompt_written (pompts_11/098_19_corpus_inspector.md) → implemented (this file).

Reference: pompts_11/098_19_corpus_inspector.md.
Sibling: scripts_01/corpus_persistence.py (storage layer; this module is the read-only
+ safe-cleanup surface).

Use cases:
    python -m scripts_01.corpus_inspector stats [--json***REMOVED*** [--root DIR***REMOVED***
    python -m scripts_01.corpus_inspector dedup [--json***REMOVED*** [--root DIR***REMOVED***
    python -m scripts_01.corpus_inspector evict --older-than-days N [--apply***REMOVED*** [--json***REMOVED*** [--root DIR***REMOVED***

Design invariants (per thinker v5.189.58):
- URL-variant detection: Strategy C (hybrid canonicalization) — strip fragment,
  lowercase scheme + netloc, normalize trailing-slash path, drop known tracking
  params (TRACKING_PARAMS module constant).
- Age buckets: 4 standard (active / warming / stale / archival) — `<7d`, `7-30d`,
  `30-90d`, `>90d` + `total` + `invalid_timestamp_count` (failed parses не валят).
- Evict: dry-run BY DEFAULT (--apply обязателен для мутации); atomic per-URL
  (whole-file unlink if all entries stale, else read-filter-write-rename).
- ADR-016 fail-safe everywhere (JSONL reads, file ops, URL canonicalization).
- Cross-module ``FILE_LOCK`` для evict — избегаем race с ``corpus_persistence.persist``.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
from dataclasses import dataclass, field
***REMOVED***
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlsplit, urlunsplit

# Cross-module FILE_LOCK — shared с corpus_persistence.persist.
# Mandatory для evict: гарантирует atomic-rename race-free с concurrent persist.
# DEFAULT_CORPUS_DIR also imported → autouse monkeypatch propagates через transitive
# import (CRITICAL hermetic — v5.189.58 code-reviewer fix).
from scripts_01.corpus_persistence import (
    DEFAULT_CORPUS_DIR,
    FILE_LOCK,
    CorpusEntry,
    list_all,
)

__all__ = [
    "TRACKING_PARAMS",
    "AGE_BUCKETS",
    "VariantGroup",
    "DomainStat",
    "stats",
    "dedup",
    "evict",
    "main",
***REMOVED***

# ─── constants ──────────────────────────────────────────────────────────────

# Known tracking-style query params (whitelist of variants that don't change content).
# Источник: documented UTM spec +13 reported session/click-id conventions.
# Не включаем `page=, id=`, и т.п. (semantic query params, должны сохраняться).
TRACKING_PARAMS: frozenset = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "msclkid", "mc_eid", "mc_cid",
    "_ga", "ref", "igshid", "si", "feature", "mibextid",
***REMOVED***)

# Standard age buckets для corpus_intelligence phases (active / warming / stale / archival).
AGE_BUCKETS: Tuple[str, ...***REMOVED*** = ("<7d", "7-30d", "30-90d", ">90d")
# Bucket boundaries in days (ILL == "7", "30", "90"-inclusive on lower edge).
_AGE_BOUNDARIES_DAYS: Tuple[int, ...***REMOVED*** = (7, 30, 90)

# Version string (--version flag).
__version__: str = "1.0.0 (corpus_inspector, v5.189.58)"

# Cap default-canonicalize normalization depth: keep behavior bounded for v1.
_EVICT_PARTIAL_ATOMIC_SUFFIX: str = ".tmp"


# ─── dataclasses (output shape) ────────────────────────────────────────────


@dataclass
class VariantGroup:
    """One dedup cluster — variants of same canonical URL.

    Attributes:
        canonical: normalized URL после stripping tracking-params / fragment / case.
        variants: list of original URLs that map to this canonical.
        count: number of distinct original URLs in group (== len(variants)).
        occurrences: total source-occurrences across all variants (entry count).
    """
    canonical: str
    variants: List[str***REMOVED***
    count: int
    occurrences: int


@dataclass
class DomainStat:
    """Aggregate corpus stat per domain."""
    domain: str
    count: int


# ─── helpers ────────────────────────────────────────────────────────────────


def _now_utc() -> _dt.datetime:
    """Now в UTC. Отдельный helper для testability (mock-friendly)."""
    return _dt.datetime.now(_dt.timezone.utc)


def _safe_parse_timestamp(ts: str) -> Optional[_dt.datetime***REMOVED***:
    """Parse ISO 8601 UTC формат ``YYYY-MM-DDTHH:MM:SSZ`` / ``+00:00``.

    Fail-safe: returns ``None`` если input malformed. Не raise.
    """
    if not isinstance(ts, str) or not ts:
        return None
    # Normalize: corpus_persistence гарантирует ``Z`` суффикс, но поддержим +00:00 тоже.
    ts = ts.strip()
    if ts.endswith("Z"):
        ts_norm = ts[:-1***REMOVED*** + "+00:00"
    else:
        ts_norm = ts
    try:
        # ``fromisoformat`` accepts "+00:00" но НЕ "Z" in 3.10-; norma выше решает.
        return _dt.datetime.fromisoformat(ts_norm)
    except (ValueError, TypeError):
        return None


def _age_bucket(now: _dt.datetime, ts: _dt.datetime) -> str:
    """Bucket label для age. Caller ensured ``ts`` is valid."""
    delta_days = (now - ts).days
    if delta_days < _AGE_BOUNDARIES_DAYS[0***REMOVED***:
        return AGE_BUCKETS[0***REMOVED***          # "<7d"
    if delta_days < _AGE_BOUNDARIES_DAYS[1***REMOVED***:
        return AGE_BUCKETS[1***REMOVED***          # "7-30d"
    if delta_days < _AGE_BOUNDARIES_DAYS[2***REMOVED***:
        return AGE_BUCKETS[2***REMOVED***          # "30-90d"
    return AGE_BUCKETS[3***REMOVED***              # ">90d"


def _canonicalize_url(url: str) -> str:
    """Hybrid canonicalization per Strategy C.

    Steps:
        1. urlsplit → scheme/host/path/query/fragment.
        2. strip fragment (empty).
        3. lowercase scheme + netloc (host).
        4. collapse trailing-slash для non-root path (``/foo/`` → ``/foo``), keep
           root path ``/`` as-is.
        5. drop keys from ``TRACKING_PARAMS`` while preserving other params;
           re-sort remaining keys for determinism (otherwise semantically equal URLs
           with different key order produce different canonicals — flagging false
           variants as unique).
    """
    try:
        parts = urlsplit(url)
    except ValueError:
        # Malformed URL — return as-is (fail-safe, не raise).
        return url
    # scheme + host lowercased.
    scheme = (parts.scheme or "").lower()
    netloc = (parts.netloc or "").lower()
    # path normalize: collapse trailing-slash except для root ``/``.
    path = parts.path or ""
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    # query: drop tracking params, sort remaining.
    query_pairs: List[Tuple[str, str***REMOVED******REMOVED*** = [***REMOVED***
    if parts.query:
        for kv in parts.query.split("&"):
            if "=" not in kv:
                # Edge: bare value — preserve as key=empty.
                k = kv
                v = ""
            else:
                k, v = kv.split("=", 1)
            if k in TRACKING_PARAMS:
                continue
            query_pairs.append((k, v))
    query_pairs.sort(key=lambda kv: kv[0***REMOVED***)
    query = "&".join(f"{k***REMOVED***={v***REMOVED***" if v else k for k, v in query_pairs)
    return urlunsplit((scheme, netloc, path, query, ""))  # empty fragment


def _domain_of(url: str) -> str:
    """Extract domain (lower-cased netloc) для ``top_domains``. Empty если нет."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return ""
    return (parts.netloc or "").lower()


def _group_variants(entries: List[CorpusEntry***REMOVED***) -> List[VariantGroup***REMOVED***:
    """Group entries by canonical URL → VariantGroup list.

    Notes:
        - variant list = unique original URLs in group (preserve first-seen order).
        - occurrences = total source-occurrences across all variants (counts in
          CorpusEntry occurrences, not dedup-by-source).
    """
    canon_to_variants: Dict[str, List[str***REMOVED******REMOVED*** = {***REMOVED***  # canonical → ordered uniques
    canon_to_occurrences: Dict[str, int***REMOVED*** = {***REMOVED***
    for e in entries:
        canon = _canonicalize_url(e.url)
        if canon not in canon_to_variants:
            canon_to_variants[canon***REMOVED*** = [***REMOVED***
            canon_to_occurrences[canon***REMOVED*** = 0
        if e.url not in canon_to_variants[canon***REMOVED***:
            canon_to_variants[canon***REMOVED***.append(e.url)
        canon_to_occurrences[canon***REMOVED*** += 1
    groups: List[VariantGroup***REMOVED*** = [***REMOVED***
    # Stable order: by canonical URL (deterministic on repeated runs).
    for canon in sorted(canon_to_variants):
        variants = canon_to_variants[canon***REMOVED***
        if len(variants) <= 1:
            # Skip singletons — variant report requires multi-variant clusters
            # (otherwise dedup report bloats with `count=1` trivial entries).
            continue
        groups.append(VariantGroup(
            canonical=canon,
            variants=variants,
            count=len(variants),
            occurrences=canon_to_occurrences[canon***REMOVED***,
        ))
    return groups


def _group_by_domain(entries: List[CorpusEntry***REMOVED***) -> List[DomainStat***REMOVED***:
    """Top domains sorted by URL count desc. Tie-breaker: domain name asc."""
    counts: Dict[str, int***REMOVED*** = {***REMOVED***
    for e in entries:
        d = _domain_of(e.url)
        if not d:
            continue
        counts[d***REMOVED*** = counts.get(d, 0) + 1
    return sorted(
        [DomainStat(domain=d, count=c) for d, c in counts.items()***REMOVED***,
        key=lambda ds: (-ds.count, ds.domain),
    )


# ─── public functions ──────────────────────────────────────────────────────


def stats(
    *, root: Optional[Path***REMOVED*** = None, top_domains_limit: int = 10,
) -> Dict[str, Any***REMOVED***:
    """Aggregate corpus stats.

    Returns dict:
        ``by_source``: ``{source: count***REMOVED***``
        ``total``: int (sum)
        ``by_age_bucket``: ``{<7d: N, 7-30d: N, 30-90d: N, >90d: N***REMOVED***``
        ``top_domains``: ``[{domain, count***REMOVED***, ...***REMOVED***`` (top-10 by URL count)
        ``invalid_timestamp_count``: int (entries с malformed timestamps)
    """
    entries = list_all(root=root)
    by_source: Dict[str, int***REMOVED*** = {***REMOVED***
    by_age: Dict[str, int***REMOVED*** = {bucket: 0 for bucket in AGE_BUCKETS***REMOVED***
    invalid_count = 0
    now = _now_utc()
    for e in entries:
        by_source[e.source***REMOVED*** = by_source.get(e.source, 0) + 1
        parsed = _safe_parse_timestamp(e.timestamp)
        if parsed is None:
            invalid_count += 1
            continue
        # Convert to UTC if naive (defensive — corpus гарантирует UTC ISO).
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=_dt.timezone.utc)
        try:
            bucket = _age_bucket(now, parsed)
        except Exception:
            invalid_count += 1
            continue
        by_age[bucket***REMOVED*** += 1
    return {
        "by_source": dict(sorted(by_source.items())),
        "total": sum(by_source.values()),
        "by_age_bucket": by_age,
        "top_domains": [
            {"domain": d.domain, "count": d.count***REMOVED***
            for d in _group_by_domain(entries)[:top_domains_limit***REMOVED***
        ***REMOVED***,
        "invalid_timestamp_count": invalid_count,
    ***REMOVED***


def dedup(*, root: Optional[Path***REMOVED*** = None) -> List[VariantGroup***REMOVED***:
    """Find URL-variant clusters (multi-variant groups only).

    Returns list of ``VariantGroup`` (length 1+ clusters; singletons excluded).
    """
    return _group_variants(list_all(root=root))


def evict(
    older_than_days: int, *, apply: bool = False, root: Optional[Path***REMOVED*** = None,
) -> Dict[str, Any***REMOVED***:
    """TTL eviction. Returns report dict (для --json output и dry-run preview).

    Dry-run semantics (default):
        - ``apply=False`` → NO mutation; returns ``{"mode": "dry-run", ...***REMOVED***``.
        - ``apply=True`` → EVICT applied atomically (per-file).

    Strategy (per-file, in sorted order):
        - Whole-file ``unlink()`` if ALL entries within file are older than TTL.
        - Else atomic read-filter-write-rename (entries with timestamp → TTL dropped).
        - Partial-evict failures (read or write exception) → leave file untouched +
          ``warning`` + continue to next file (ADR-016 fail-safe).

    Returns:
        ``{"mode": "dry-run"|"apply", "removed_files": N, "removed_entries": M,
          "kept_entries": K, "considered_files": N, "warnings": [...***REMOVED******REMOVED***``.
    """
    if older_than_days < 0:
        raise ValueError(
            f"older_than_days must be non-negative, got {older_than_days***REMOVED***"
        )

    base = root if root is not None else DEFAULT_CORPUS_DIR
    if not base.is_dir():
        return {
            "mode": "apply" if apply else "dry-run",
            "removed_files": 0,
            "removed_entries": 0,
            "kept_entries": 0,
            "considered_files": 0,
            "warnings": [***REMOVED***,
        ***REMOVED***

    cutoff = _now_utc() - _dt.timedelta(days=older_than_days)
    considered = 0
    removed_files = 0
    removed_entries = 0
    kept_entries = 0
    warnings: List[str***REMOVED*** = [***REMOVED***

    # Lock globally to avoid race with concurrent persist calls (competing writes
    # to the same .jsonl files). FILE_LOCK shared с corpus_persistence module.
    with FILE_LOCK:
        for jsonl in sorted(base.glob("*.jsonl")):
            considered += 1
            raw_records = _read_jsonl_safely(jsonl)  # never raises
            if not raw_records:
                # Empty file (degenerate / all corrupt-readable) → unlink в dry-run preview.
                if apply:
                    try:
                        jsonl.unlink()
                        removed_files += 1
                    except OSError as exc:
                        warnings.append(
                            f"evict: unlink {jsonl***REMOVED*** failed: {exc***REMOVED***"
                        )
                else:
                    removed_files += 1  # dry-run preview count
                continue

            # Stratify records by age.
            kept: List[Dict[str, Any***REMOVED******REMOVED*** = [***REMOVED***
            to_drop: List[Dict[str, Any***REMOVED******REMOVED*** = [***REMOVED***
            for r in raw_records:
                ts = r.get("timestamp", "")
                parsed = _safe_parse_timestamp(ts)
                if parsed is None:
                    # Invalid timestamp: keep (не evict по malformed data).
                    kept.append(r)
                    continue
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=_dt.timezone.utc)
                if parsed < cutoff:
                    to_drop.append(r)
                else:
                    kept.append(r)

            if not kept:
                # All stale → unlink whole file (Strategy B fast-path).
                if apply:
                    try:
                        jsonl.unlink()
                        removed_files += 1
                        removed_entries += len(to_drop)
                    except OSError as exc:
                        warnings.append(
                            f"evict: unlink {jsonl***REMOVED*** failed: {exc***REMOVED***"
                        )
                else:
                    removed_files += 1
                    removed_entries += len(to_drop)
                continue

            if not to_drop:
                # No eviction needed for this file.
                kept_entries += len(kept)
                continue

            # Partial-evict path: atomic read-filter-write-rename.
            if not apply:
                # Dry-run preview: estimate eviction count, leave file untouched.
                removed_entries += len(to_drop)
                kept_entries += len(kept)
                continue
            try:
                _atomic_write_jsonl(jsonl, kept)
                removed_entries += len(to_drop)
                kept_entries += len(kept)
            except Exception as exc:
                warnings.append(
                    f"evict: partial-evict {jsonl***REMOVED*** failed: {exc***REMOVED***; file left untouched"
                )

    return {
        "mode": "apply" if apply else "dry-run",
        "removed_files": removed_files,
        "removed_entries": removed_entries,
        "kept_entries": kept_entries,
        "considered_files": considered,
        "warnings": warnings,
    ***REMOVED***


# ─── low-level helpers (depend on corpus_persistence internals through
#     safe rewrite-strategy mirror) ──────────────────────────────────────────


def _read_jsonl_safely(path: Path) -> List[Dict[str, Any***REMOVED******REMOVED***:
    """Прочитать JSONL с corrupt-line recovery. Same pattern as corpus_persistence."""
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
                        f"corpus_inspector: corrupt JSONL at {path***REMOVED***:{line_num***REMOVED***: "
                        f"{exc***REMOVED***; line skipped\n"
                    )
    except OSError as exc:
        sys.stderr.write(f"corpus_inspector: read {path***REMOVED***: {exc***REMOVED***\n")
    return out


def _atomic_write_jsonl(path: Path, records: List[Dict[str, Any***REMOVED******REMOVED***) -> None:
    """Atomic write-tmp + fsync + rename. Mirror of corpus_persistence.persist pattern.

    Cleanup ``.tmp`` on exception (no leakage).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + _EVICT_PARTIAL_ATOMIC_SUFFIX)
    try:
        with tmp.open("w", encoding="utf-8") as f:
            for rec in records:
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


# ─── CLI ─────────────────────────────────────────────────────────────────────


def _print_json(payload: Any) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


def _cli_stats(args: argparse.Namespace) -> int:
    payload = stats(root=args.root)
    if args.json:
        _print_json(payload)
        return 0
    if payload["total"***REMOVED*** == 0:
        sys.stdout.write("(empty corpus)\n")
        return 0
    sys.stdout.write("### corpus stats\n")
    sys.stdout.write(f"by source:\n")
    for src, count in payload["by_source"***REMOVED***.items():
        sys.stdout.write(f"  - {src***REMOVED***: {count***REMOVED***\n")
    sys.stdout.write(f"total: {payload['total'***REMOVED******REMOVED***\n")
    sys.stdout.write("by age bucket:\n")
    for bucket, count in payload["by_age_bucket"***REMOVED***.items():
        sys.stdout.write(f"  - {bucket***REMOVED***: {count***REMOVED***\n")
    sys.stdout.write("top domains:\n")
    for d in payload["top_domains"***REMOVED***:
        sys.stdout.write(f"  - {d['domain'***REMOVED******REMOVED***: {d['count'***REMOVED******REMOVED***\n")
    if payload["invalid_timestamp_count"***REMOVED*** > 0:
        sys.stdout.write(
            f"WARNING: {payload['invalid_timestamp_count'***REMOVED******REMOVED*** entries with "
            f"invalid timestamps (excluded from age buckets)\n"
        )
    return 0


def _cli_dedup(args: argparse.Namespace) -> int:
    groups = dedup(root=args.root)
    if args.json:
        _print_json([
            {
                "canonical": g.canonical,
                "variants": g.variants,
                "count": g.count,
                "occurrences": g.occurrences,
            ***REMOVED***
            for g in groups
        ***REMOVED***)
        return 0
    if not groups:
        sys.stdout.write("(no variant clusters found)\n")
        return 0
    sys.stdout.write(
        f"### URL-variant clusters ({len(groups)***REMOVED*** groups)\n"
    )
    sys.stdout.write(
        "Each canonical has 2+ variants. This usually indicates tracking-param\n"
        "duplication across fetches. Consider merging or evicting duplicates.\n\n"
    )
    for g in groups:
        sys.stdout.write(f"Canonical: {g.canonical***REMOVED***\n")
        sys.stdout.write(f"  variants ({g.count***REMOVED***):\n")
        for v in g.variants:
            sys.stdout.write(f"    - {v***REMOVED***\n")
        sys.stdout.write(f"  total occurrences: {g.occurrences***REMOVED***\n\n")
    return 0


def _positive_int(value: str) -> int:
    """argparse type для --older-than-days: positive int."""
    try:
        n = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"older-than-days must be int, got {value!r***REMOVED***"
        )
    if n < 0:
        raise argparse.ArgumentTypeError(
            f"older-than-days must be non-negative, got {n***REMOVED***"
        )
    return n


def _cli_evict(args: argparse.Namespace) -> int:
    try:
        report = evict(
            older_than_days=args.older_than_days,
            apply=args.apply,
            root=args.root,
        )
    except ValueError as exc:
        sys.stderr.write(f"error: {exc***REMOVED***\n")
        return 2
    if args.json:
        _print_json(report)
        return 0
    sys.stdout.write(
        f"### evict [{report['mode'***REMOVED******REMOVED******REMOVED*** "
        f"(older-than-days={args.older_than_days***REMOVED***)\n"
    )
    sys.stdout.write(
        f"considered files: {report['considered_files'***REMOVED******REMOVED***\n"
    )
    sys.stdout.write(
        f"removed files: {report['removed_files'***REMOVED******REMOVED***\n"
    )
    sys.stdout.write(
        f"removed entries: {report['removed_entries'***REMOVED******REMOVED***\n"
    )
    sys.stdout.write(
        f"kept entries: {report['kept_entries'***REMOVED******REMOVED***\n"
    )
    if report["warnings"***REMOVED***:
        sys.stdout.write(
            f"WARNINGS ({len(report['warnings'***REMOVED***)***REMOVED***):\n"
        )
        for w in report["warnings"***REMOVED***:
            sys.stdout.write(f"  - {w***REMOVED***\n")
    if report["mode"***REMOVED*** == "dry-run":
        sys.stdout.write(
            "\n(dry-run: no files removed; pass --apply to evict)\n"
        )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="corpus_inspector",
        description=(
            "Read-only stats + safe-cleanup for corpus_persistence. "
            "Use 'stats' for overview, 'dedup' to find URL variants, "
            "'evict' for TTL cleanup (dry-run by default)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=__version__,
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="corpus root override (default=data_13/corpus); use для tests "
             "или staging vs prod deployments",
    )
    # NOTE: --json — per-subcommand (НЕ top-level), mirroring corpus_persistence's
    # pattern. Top-level --json работает только когда ANTEDES subcommand, что
    # не-fluent для users.

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_stats = sub.add_parser(
        "stats", help="URL count per source, age distribution, top domains",
    )
    p_stats.add_argument(
        "--json", action="store_true",
        help="JSON output (machine-readable)",
    )
    p_stats.set_defaults(func=_cli_stats)

    p_dedup = sub.add_parser(
        "dedup", help="find URL variants (multi-cluster groups)",
    )
    p_dedup.add_argument(
        "--json", action="store_true",
        help="JSON output (machine-readable)",
    )
    p_dedup.set_defaults(func=_cli_dedup)

    p_evict = sub.add_parser(
        "evict", help="evict entries older than TTL (dry-run by default)",
    )
    p_evict.add_argument(
        "--older-than-days", type=_positive_int, required=True,
        help="TTL window in days (non-negative int)",
    )
    p_evict.add_argument(
        "--apply", action="store_true",
        help="REQUIRED для actual eviction (default = dry-run preview)",
    )
    p_evict.add_argument(
        "--json", action="store_true",
        help="JSON output (machine-readable)",
    )
    p_evict.set_defaults(func=_cli_evict)

    return parser


def main(argv: Optional[List[str***REMOVED******REMOVED*** = None) -> int:
    """CLI entry point.

    Usage::

        python -m scripts_01.corpus_inspector stats [--json***REMOVED*** [--root DIR***REMOVED***
        python -m scripts_01.corpus_inspector dedup [--json***REMOVED*** [--root DIR***REMOVED***
        python -m scripts_01.corpus_inspector evict --older-than-days N [--apply***REMOVED*** [--json***REMOVED*** [--root DIR***REMOVED***
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    func = args.func
    return func(args)  # type: ignore[no-any-return***REMOVED***


if __name__ == "__main__":
    sys.exit(main())
