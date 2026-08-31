#!/usr/bin/env python3
"""cli.py — CLI lead_aggregator (Фаза 4 Deploy, ROADMAP-LA-001).

Запуск:
    python -m projects_17.lead_aggregator.app.cli --dry-run     # реальные источники, БЕЗ доставки
    python -m projects_17.lead_aggregator.app.cli --once        # один проход (боевой)
    python -m projects_17.lead_aggregator.app.cli --forever     # непрерывный цикл 24/7

Принципы (промт 69 + ROADMAP):
- dry-run: читает РЕАЛЬНЫЕ источники (Kwork + TG-каналы), но НЕ отправляет в TG
  и НЕ пишет боевые чекпоинты (temp db) — безопасно для smoke-проверки.
- Боевой запуск: реальная доставка (если LA_TG_BOT_TOKEN/LA_TG_CHAT_ID заданы),
  чекпоинты в data/checkpoints.db (resume после рестарта).
- settings.env автоматически загружается через Config.load_config().
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import tempfile
from pathlib import Path
from typing import Sequence

# Корень пакета lead_aggregator — чтобы импорты app.* работали при запуске
# как `python -m projects_17.lead_aggregator.app.cli` из корня платформы.
LA_ROOT = Path(__file__).resolve().parent.parent
if str(LA_ROOT) not in sys.path:
    sys.path.insert(0, str(LA_ROOT))

from app.core.config import load_config  # noqa: E402
from app.core.tls_client import TLSClient  # noqa: E402
from app.delivery.telegram import TelegramDelivery  # noqa: E402
from app.models import Lead  # noqa: E402
from app.pipeline import LeadPipeline, build_default_adapters  # noqa: E402
from app.storage.checkpoint_store import CheckpointStore  # noqa: E402

logger = logging.getLogger("lead_aggregator.cli")


# ── dry-run delivery: ловит лиды вместо отправки ─────────────────────
class _CaptureDelivery:
    """Перехватчик доставки для dry-run: ничего не отправляет, копит лиды."""

    def __init__(self) -> None:
        self.captured: list[Lead] = []

    @property
    def enabled(self) -> bool:
        return False

    async def send(self, lead: Lead) -> bool:
        self.captured.append(lead)
        logger.info("[dry) lead %s score=%.0f", lead.source_id, lead.score)
        return False

    async def aclose(self) -> None:
        pass


# ── helpers ──────────────────────────────────────────────────────────
def _parse_sources(value: str | None) -> list[str] | None:
    """Фильтр источников: 'kwork' / 'tg' / 'kwork,tg' / None = все."""
    if not value:
        return None
    wanted: list[str] = []
    for part in value.split(","):
        part = part.strip().lower()
        if part == "tg":
            part = "tg_channel"  # имя адаптера в коде
        if part:
            wanted.append(part)
    return wanted


def _select_adapters(config, client: TLSClient, wanted: list[str] | None):
    adapters = build_default_adapters(config, client)
    if wanted is None:
        return adapters
    return [a for a in adapters if a.name in wanted]


def _print_lead(idx: int, lead: Lead) -> None:
    print(f"  {idx:>2}. [{lead.source:11s}] score={lead.score:5.1f} intent={lead.intent:7s} "
          f"{lead.text[:90]}")
    if lead.url:
        print(f"      {lead.url}")


def _print_stats(stats: dict[str, int]) -> None:
    print(f"      fetched={stats['fetched']} new={stats['new']} "
          f"delivered={stats['delivered']} errors={stats['errors']}")


# ── запуск ───────────────────────────────────────────────────────────
async def _run_pipeline(config, adapters, delivery, checkpoint_db: Path) -> dict[str, int]:
    """Один проход пайплайна; чекпоинты в checkpoint_db."""
    pipeline = LeadPipeline(
        config,
        adapters,
        delivery=delivery,
        checkpoint=CheckpointStore(checkpoint_db),
    )
    try:
        return await pipeline.run_once()
    finally:
        await pipeline.aclose()


async def _cmd_once(config, args: argparse.Namespace) -> int:
    """Один проход: dry-run (temp, без доставки) или боевой (реальный)."""
    client = TLSClient(timeout=15.0)
    adapters = _select_adapters(config, client, _parse_sources(args.sources))
    if not adapters:
        print("Нет активных источников. Проверь LA_KWORK_ENABLED / LA_TG_CHANNELS "
              "или --sources.")
        await client.aclose()
        return 2

    if args.dry_run:
        delivery: TelegramDelivery | _CaptureDelivery = _CaptureDelivery()
        with tempfile.TemporaryDirectory(prefix="la_dry_") as tmp:
            db = Path(tmp) / "checkpoints.db"
            stats = await _run_pipeline(config, adapters, delivery, db)
    else:
        delivery = TelegramDelivery(config.tg_bot_token, config.tg_chat_id)
        stats = await _run_pipeline(config, adapters, delivery, config.checkpoint_db)

    await client.aclose()

    print(f"\n[lead_aggregator] {'DRY-RUN' if args.dry_run else 'RUN'} "
          f"({', '.join(a.name for a in adapters)})")
    _print_stats(stats)
    if args.dry_run:
        print(f"  → было бы доставлено лидов: {len(delivery.captured)}")
        for i, lead in enumerate(delivery.captured, 1):
            _print_lead(i, lead)
        print(f"  [dry] доставка отключена (temp-чекпоинты, без TG)")
    elif not delivery.enabled:
        print("  [warn) LA_TG_BOT_TOKEN/LA_TG_CHAT_ID не заданы — доставка не производилась")
    if args.json:
        payload = {"mode": "dry-run" if args.dry_run else "once", "stats": stats,
                   "sources": [a.name for a in adapters]}
        if args.dry_run:
            payload["leads"] = [{"id": l.source_id, "source": l.source,
                                 "score": l.score, "intent": l.intent, "text": l.text,
                                 "url": l.url} for l in delivery.captured]
        print(json.dumps(payload, ensure_ascii=False))
    return 0 if stats["errors"] == 0 else 1


async def _cmd_forever(config, args: argparse.Namespace) -> int:
    """Непрерывный цикл 24/7 (CORE DIRECTIVE промта 69)."""
    client = TLSClient(timeout=15.0)
    adapters = _select_adapters(config, client, _parse_sources(args.sources))
    if not adapters:
        print("Нет активных источников.")
        await client.aclose()
        return 2
    delivery = TelegramDelivery(config.tg_bot_token, config.tg_chat_id)
    if not delivery.enabled:
        print("[warn) LA_TG_BOT_TOKEN/LA_TG_CHAT_ID не заданы — лиды только логируются")
    pipeline = LeadPipeline(config, adapters, delivery=delivery,
                            checkpoint=CheckpointStore(config.checkpoint_db))
    interval = args.interval if args.interval else config.poll_interval_s
    print(f"[lead_aggregator] FOREVER ({', '.join(a.name for a in adapters)}), "
          f"interval={interval}s. Ctrl+C для остановки.")
    try:
        while True:
            stats = await pipeline.run_once()
            print(f"  [cycle] {stats}")
            await asyncio.sleep(interval)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nОстановлено пользователем.")
        return 0
    finally:
        await pipeline.aclose()
        await client.aclose()


# ── parser / main ────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lead_aggregator",
        description="Attract-модуль: автономный сбор заказов (Kwork + TG-каналы). Фаза 4 Deploy.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true",
                      help="реальные источники, НО без доставки и без боевых чекпоинтов (temp)")
    mode.add_argument("--once", action="store_true", help="один проход (по умолчанию)")
    mode.add_argument("--forever", action="store_true", help="непрерывный цикл 24/7")
    parser.add_argument("--interval", type=float, default=None,
                        help="период опроса для --forever (сек; default LA_POLL_INTERVAL)")
    parser.add_argument("--sources", default=None,
                        help="фильтр источников: kwork / tg / kwork,tg (default: все)")
    parser.add_argument("--json", action="store_true", help="вывести JSON-сводку")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug-логирование")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    config = load_config()
    if args.forever:
        return asyncio.run(_cmd_forever(config, args))
    return asyncio.run(_cmd_once(config, args))


if __name__ == "__main__":
    sys.exit(main())
