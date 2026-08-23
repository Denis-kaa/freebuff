"""CLI для офлайн-прогона pipeline (P8).

`python -m app.cli --once --fixture fixtures/rss/sample_rss.xml ...`

Режимы:

- `--once` — один отформатированный прогон (dry-run delivery);
- `--maintenance --db parser.db` — TTL cleanup + vacuum (P11).

Секреты: переменные окружения (PRP_DB_PATH, PRP_PROFILE) — не в аргументах.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
***REMOVED***

from app.domain import SearchProfile
from app.delivery import TelegramDelivery
from app.pipeline import format_report, run_offline_slice
from app.rss_atom import FixtureFeedAdapter
from app.storage import SqliteCheckpointStore, SqliteStorage


def _profile_from_args(args: argparse.Namespace) -> SearchProfile:
    required = tuple(t.strip() for t in args.required.split(",") if t.strip())
    optional = tuple(t.strip() for t in args.optional.split(",") if t.strip())
    intent = tuple(t.strip() for t in args.intent.split(",") if t.strip())
    return SearchProfile(
        profile_id=args.profile_id,
        owner_scope=args.owner,
        version=1,
        service_name=args.service,
        required_terms=required,
        optional_terms=optional,
        intent_terms=intent,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="public-request-parser",
        description="Офлайн-срез P8: fixture-feed → matcher → SQLite → dry-run delivery",
    )
    parser.add_argument("--once", action="store_true", help="один прогон pipeline")
    parser.add_argument("--maintenance", action="store_true", help="TTL cleanup + фон (P11)")
    parser.add_argument("--fixture", type=Path, help="путь к RSS/Atom fixture")
    parser.add_argument("--source-id", default="cli-fixture", help="source id адаптера")
    parser.add_argument("--db", type=str, default="parser.db", help="путь к SQLite")
    parser.add_argument("--owner", default="operator")
    parser.add_argument("--profile-id", default="profile-cli")
    parser.add_argument("--service", default="Python разработка")
    parser.add_argument("--required", default="python")
    parser.add_argument("--optional", default="backend")
    parser.add_argument("--intent", default="нужен,ищу")
    parser.add_argument("--limit", type=int, default=50)
    return parser


def run() -> int:
    args = _build_parser().parse_args()
    if not args.once and not args.maintenance:
        print("укажите --once или --maintenance", file=sys.stderr)
        return 2

    storage = SqliteStorage(args.db)
    try:
        if args.maintenance:
            now = None
            expired = storage.expire_full_text(now)
            backup = storage.backup_to(f"{args.db***REMOVED***.bak")
            print(json.dumps({"expired_text_rows": expired, "backup": backup***REMOVED***))
            return 0

        if not args.fixture or not args.fixture.exists():
            print(f"fixture не найден: {args.fixture***REMOVED***", file=sys.stderr)
            return 2

        profile = _profile_from_args(args)
        adapter = FixtureFeedAdapter(args.source_id, args.fixture.read_bytes())
        checkpoint = SqliteCheckpointStore(storage)
        delivery = TelegramDelivery(storage=storage, dry_run=True)
        result = asyncio.run(
            run_offline_slice(
                adapter=adapter,
                profile=profile,
                storage=storage,
                checkpoint=checkpoint,
                delivery=delivery,
                owner_scope=args.owner,
                limit=args.limit,
            )
        )
        print(format_report(result))
        return 0
    finally:
        storage.close()


if __name__ == "__main__":
    raise SystemExit(run())