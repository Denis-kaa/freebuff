"""CLI: corpus ingestion, reports, and learner-content localization.

Команды:
  ingest exercism [--source DIR***REMOVED*** [--db PATH***REMOVED*** [--dry-run***REMOVED*** [--with-refs***REMOVED*** [--report***REMOVED***
  report [--db PATH***REMOVED*** {coverage|gaps|low-confidence|license***REMOVED***
  localize {scan|status|update***REMOVED*** [options***REMOVED***

Exit codes: 0 = ok, 2 = ошибка (аргументы/данные).
"""

from __future__ import annotations

import argparse
import json
import sys

from app.curriculum.map import (
    coverage_report,
    load_competency_map,
    validate_competency_map,
)
from app.ingestion.mapping import create_mapper
from app.ingestion.pipeline import ingest
from app.ingestion.reports import (
    gap_report,
    ingest_chart,
    low_confidence_report,
    license_report,
)
from app.storage import open_corpus
from app.localization.cli import add_localization_parser, run_localization

DEFAULT_SOURCE = "data/exercism_src"
DEFAULT_DB = "data/corpus/corpus_v0.1.db"
SOURCES_YAML = "configs/sources.yaml"
MAP_YAML = "configs/competency_map.yaml"
OVERRIDES_YAML = "configs/exercise_overrides.yaml"


def _cmd_ingest(args: argparse.Namespace) -> int:
    cm = load_competency_map(MAP_YAML)
    errs = validate_competency_map(cm)
    if errs:
        for e in errs:
            print("VALIDATION ERROR:", e)
        return 2
    mapper = create_mapper(cm, OVERRIDES_YAML)

    if args.dry_run:
        rep = ingest(
            args.source, args.db, SOURCES_YAML,
            dry_run=True, with_refs=args.with_refs, mapper=mapper,
            competency_map=cm,
        )
        print("=== DRY-RUN (ничего не записано) ===")
        print(json.dumps(rep.summary(), ensure_ascii=False, indent=1))
        return 0

    rep = ingest(
        args.source, args.db, SOURCES_YAML,
        dry_run=False, with_refs=args.with_refs, mapper=mapper,
        competency_map=cm,
    )
    print("=== INGEST ===")
    print(json.dumps(rep.summary(), ensure_ascii=False, indent=1))
    if rep.errors:
        print("ОШИБКИ:", *rep.errors, sep="\n  ")
        return 2
    if args.report:
        _print_reports(args.db)
    return 0


def _print_reports(db: str) -> None:
    conn = open_corpus(db)
    cm = load_competency_map(MAP_YAML)
    print()
    print("--- coverage ---")
    print(ingest_chart(conn))
    print("--- gaps ---")
    print(gap_report(conn))
    low = low_confidence_report(conn)
    print("--- low-confidence mapping ---")
    print(json.dumps(low, ensure_ascii=False, indent=1))
    print("--- sources/license ---")
    print(json.dumps(license_report(conn), ensure_ascii=False, indent=1))
    conn.close()


def _cmd_report(args: argparse.Namespace) -> int:
    conn = open_corpus(args.db)
    cm = load_competency_map(MAP_YAML)
    if args.kind == "coverage":
        print(ingest_chart(conn))
    elif args.kind == "gaps":
        print(gap_report(conn))
    elif args.kind == "low-confidence":
        print(json.dumps(low_confidence_report(conn), ensure_ascii=False, indent=1))
    elif args.kind == "license":
        print(json.dumps(license_report(conn), ensure_ascii=False, indent=1))
    conn.close()
    return 0


def main(argv: list[str***REMOVED*** | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m app", description="python_mentor B+C CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    ingest_p = sub.add_parser("ingest", help="import Exercism corpus")
    ingest_p.add_argument("exercism", choices=["exercism"***REMOVED***)
    ingest_p.add_argument("--source", default=DEFAULT_SOURCE)
    ingest_p.add_argument("--db", default=DEFAULT_DB)
    ingest_p.add_argument("--dry-run", action="store_true")
    ingest_p.add_argument("--with-refs", action="store_true")
    ingest_p.add_argument("--report", action="store_true")
    ingest_p.set_defaults(func=_cmd_ingest)

    rep_p = sub.add_parser("report", help="отчёты по corpus")
    rep_p.add_argument("kind", choices=["coverage", "gaps", "low-confidence", "license"***REMOVED***)
    rep_p.add_argument("--db", default=DEFAULT_DB)
    rep_p.set_defaults(func=_cmd_report)

    add_localization_parser(sub)

    args = p.parse_args(argv)
    if args.cmd == "localize":
        result = run_localization(args)
    else:
        result = args.func(args)
    return int(result) if result is not None else 0


if __name__ == "__main__":
    sys.exit(main())