"""CLI for offline pipeline (P8) and controlled canary runs (P10).

Modes:

- `--once --fixture <path>` -- offline fixture slice (dry-run delivery);
- `--maintenance --db <path>` -- TTL cleanup + backup (P11);
- `--canary --source trudvsem|headhunter --db <path>` -- live canary run (P10).

Secrets are read from env only: PRP_HH_APP_TOKEN, PRP_DB_PATH.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
import logging

from app.adapters.headhunter import API_BASE as HH_BASE
from app.adapters.trudvsem import API_BASE as TRUDVSEM_BASE
from app.canary import run_canary
from app.domain import (
    RetentionPolicy,
    SearchMode,
    SearchProfile,
    SourcePolicy,
    SourcePolicyStatus,
)
from app.delivery import TelegramDelivery
from app.ops import ScheduleConfig, run_schedule
from app.pipeline import format_report, run_offline_slice
from app.rss_atom import FixtureFeedAdapter
from app.storage import SqliteCheckpointStore, SqliteStorage


def _policy_for_source(source_id: str) -> SourcePolicy:
    """Return an ALLOWED, can_poll=True policy for a live source."""
    if source_id == "trudvsem":
        endpoint = TRUDVSEM_BASE
        evidence = ("https://trudvsem.ru/opendata", "https://trudvsem.ru/opendata/api")
        access = "open_data_api"
    elif source_id == "headhunter":
        endpoint = HH_BASE
        evidence = (
            "https://dev.hh.ru/admin/developer_agreement",
            "https://api.hh.ru/openapi/redoc",
        )
        access = "official_api"
    else:
        raise ValueError(f"unknown live source: {source_id}")
    return SourcePolicy(
        source_id=source_id,
        status=SourcePolicyStatus.ALLOWED,
        access_mode=access,
        endpoint=endpoint,
        checked_at=datetime.now(timezone.utc),
        evidence_urls=evidence,
        retention=RetentionPolicy(text_ttl=None, allow_full_text=False),
        attribution_required=True,
        can_poll=True,
    )


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
        mode=SearchMode(args.mode),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="public-request-parser",
        description="Public Request Parser: offline fixture slice + P10 canary live runs",
    )
    parser.add_argument("--once", action="store_true", help="single pipeline run (fixture)")
    parser.add_argument("--canary", action="store_true", help="controlled live run (P10)")
    parser.add_argument("--maintenance", action="store_true", help="TTL cleanup + backup (P11)")
    parser.add_argument("--fixture", type=Path, help="path to RSS/Atom fixture")
    parser.add_argument("--source", default="fixture", choices=["fixture","trudvsem","headhunter"], help="source id")
    parser.add_argument("--source-id", default="cli-fixture", help="source id fo fixture")
    parser.add_argument("--db", type=str, default="parser.db", help="path to SQLite")
    parser.add_argument("--owner", default="operator")
    parser.add_argument("--profile-id", default="profile-cli")
    parser.add_argument("--service", default="Python backend")
    parser.add_argument("--required", default="python")
    parser.add_argument("--optional", default="backend")
    parser.add_argument("--intent", default="need,looking")
    parser.add_argument("--mode", default="demand", choices=["demand", "supply"], help="search direction: demand (who needs service) or supply (jobseek)")
    parser.add_argument("--schedule", action="store_true", help="schedule loop (P11)")
    parser.add_argument("--interval", type=float, default=60.0, help="poll interval seconds (P11)")
    parser.add_argument("--limit", type=int, default=50)
    return parser


def run() -> int:
    args = _build_parser().parse_args()
    if not args.once and not args.canary and not args.maintenance and not args.schedule:
        print("use --once / --canary / --schedule / --maintenance", file=sys.stderr)
        return 2

    storage = SqliteStorage(args.db)
    try:
        if args.maintenance:
            expired = storage.expire_full_text(None)
            backup = storage.backup_to(f"{args.db}.bak")
            print(json.dumps({"expired_text_rows": expired, "backup": backup}))
            return 0

        if args.canary or args.schedule:
            if args.source not in ("trudvsem", "headhunter"):
                print("--canary/--schedule support only trudvsem/headhunter", file=sys.stderr)
                return 2
            profile = _profile_from_args(args)
            checkpoint = SqliteCheckpointStore(storage)
            delivery = TelegramDelivery(storage=storage, dry_run=True)
            policy = _policy_for_source(args.source)
            token = os.getenv("PRP_HH_APP_TOKEN") if args.source == "headhunter" else None

            async def canary_once() -> str:
                report = await run_canary(
                    source_id=args.source,
                    policy=policy,
                    profile=profile,
                    storage=storage,
                    checkpoint=checkpoint,
                    delivery=delivery,
                    owner_scope=args.owner,
                    limit=min(args.limit, 20),
                    token=token,
                )
                return report.summary()

            if args.canary:
                print(asyncio.run(canary_once()))
                return 0

            # --schedule: бесконечный цикл с backoff (P11)
            import logging

            logging.basicConfig(level=logging.INFO, format="%(message)s")
            logging.getLogger("httpcore").setLevel(logging.WARNING)
            logging.getLogger("httpx").setLevel(logging.WARNING)
            config = ScheduleConfig(
                source_id=args.source,
                interval_total=max(args.interval, 5.0),
            )
            asyncio.run(run_schedule(config=config, run_once=canary_once))
            return 0

        # offline fixture slice
        if not args.fixture or not args.fixture.exists():
            print(f"fixture not found: {args.fixture}", file=sys.stderr)
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
