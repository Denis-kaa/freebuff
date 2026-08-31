"""bot/bot.py — Telegram-бот управления (aiogram 3.x).

MVP (04_ARCHITECTURE.md §Бот) :
- /start  : enregistre le chat, message de bienvenue
- /status : dernier run (heure, compteurs)
- /run    : lancement manuel d'un run complet
- /stop   : arrêt doux du run en cours
- /stats  : nombre d'objets, nouveaux / mis à jour
- /errors : dernières erreurs du run_log
"""
from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from app.core.config import Config
from app.scheduler import RunScheduler

logger = logging.getLogger(__name__)


def make_bot(config: Config, scheduler: RunScheduler, get_stats, get_last_errors) -> tuple[Bot, Dispatcher]:
    """Construit le bot et le dispatcher avec les commandes MVP.

    Args:
        config: configuration (bot_token, admin_chat_id).
        scheduler: instance RunScheduler partagée (cron + /run).
        get_stats: async () -> dict {total, created, updated, removed, last_run}.
        get_last_errors: async (limit=10) -> list[str].
    """
    bot = Bot(token=config.bot_token)
    dp = Dispatcher()

    async def _authorized(message: Message) -> bool:
        if not config.admin_chat_id:
            return True  # pas de restriction configurée
        return str(message.chat.id) == str(config.admin_chat_id)

    @dp.message(Command("start"))
    async def cmd_start(message: Message) -> None:
        await message.answer(
            "Bot de gestion du parseur immobilier.\n"
            "Commandes : /status /run /stop /stats /errors"
        )

    @dp.message(Command("status"))
    async def cmd_status(message: Message) -> None:
        if not await _authorized(message):
            return
        stats = await get_stats()
        last = stats.get("last_run")
        await message.answer(
            "Dernier run : {last}\n"
            "Récupérés : {fetched} · Créés : {created} · Mis à jour : {updated} · "
            "Supprimés : {removed} · Erreurs : {errors}".format(
                last=last or "aucun",
                fetched=stats.get("fetched", 0),
                created=stats.get("created", 0),
                updated=stats.get("updated", 0),
                removed=stats.get("removed", 0),
                errors=stats.get("errors", 0),
            )
        )

    @dp.message(Command("run"))
    async def cmd_run(message: Message) -> None:
        if not await _authorized(message):
            return
        try:
            totals = await scheduler.run_once()
        except RuntimeError as exc:
            await message.answer(f"Impossible de lancer : {exc}")
            return
        await message.answer(
            "Run terminé : {created} créés, {updated} mis à jour, "
            "{removed} supprimés, {errors} erreurs.".format(
                created=totals.get("created", 0),
                updated=totals.get("updated", 0),
                removed=totals.get("removed", 0),
                errors=totals.get("errors", 0),
            )
        )

    @dp.message(Command("stop"))
    async def cmd_stop(message: Message) -> None:
        if not await _authorized(message):
            return
        scheduler_stop = getattr(scheduler, "request_stop", None)
        if callable(scheduler_stop):
            scheduler_stop()
            await message.answer("Arrêt doux demandé : le run s'achève après la tâche en cours.")
        else:
            await message.answer("Aucun arrêt disponible (pas de run en cours).")

    @dp.message(Command("stats"))
    async def cmd_stats(message: Message) -> None:
        if not await _authorized(message):
            return
        stats = await get_stats()
        await message.answer(
            "Objets en base : {total}\n"
            "Créés (dernier run) : {created} · Mis à jour : {updated} · "
            "Supprimés : {removed}".format(
                total=stats.get("total", 0),
                created=stats.get("created", 0),
                updated=stats.get("updated", 0),
                removed=stats.get("removed", 0),
            )
        )

    @dp.message(Command("errors"))
    async def cmd_errors(message: Message) -> None:
        if not await _authorized(message):
            return
        errors = await get_last_errors(limit=10)
        if not errors:
            await message.answer("Aucune erreur récente.")
            return
        await message.answer("Dernières erreurs :\n" + "\n".join(f"• {e}" for e in errors))

    return bot, dp
