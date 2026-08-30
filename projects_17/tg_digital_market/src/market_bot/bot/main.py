"""bot/main.py — точка входа Telegram-маркетплейса.

Запуск: `python -m market_bot.bot.main` (или `python src/market_bot/bot/main.py`).
"""

from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from ..config import load_config
from ..models import NotificationKind
from .aiogram_channel import AiogramNotificationChannel
from .handlers import build_router
from .services_container import ServiceFactory, Services

logger = logging.getLogger(__name__)


class WorkflowMiddleware(BaseMiddleware):
    """Инжектирует `services` в хэндлеры через kwargs."""

    def __init__(self, services: Services) -> None:
        self.services = services

    async def __call__(self, handler, event, data: dict):
        data["services"] = self.services
        return await handler(event, data)


def _recover_one_order(services: Services, order_id: int) -> None:
    """Восстановить один PAID-заказ без доставки.

    Сценарий: процесс упал между `mark_paid` и `publish`.
    """
    try:
        services.delivery.publish(order_id)
        code = services.delivery.code_for_order(order_id)
        order = services.repo.get_order(order_id)
        if order is None:
            logger.warning("Recovery: заказ #%s исчез на этапе recovery.", order_id)
            return
        user_id = order.user_id
        asyncio.create_task(
            services.notifications.notify_user(
                user_id=user_id,
                kind=NotificationKind.ORDER_DELIVERED,
                text=f"✅ Заказ #{order_id} доставлен (recovery).\n\nКод:\n<code>{code or '?'}</code>",
            )
        )
        logger.info("Recovery: заказ #%s доставлен.", order_id)
    except Exception:
        logger.exception("Recovery для заказа #%s провалилось.", order_id)


def _maybe_recover_paid_orphans(services: Services) -> None:
    """Sync recovery при старте: каждый вызов в отдельном потоке.

    Startup выполняется ДО polling — асинхронные хэндлеры ещё не стартовали,
    но всё равно оборачиваем в to_thread для консистентности: если recovery
    будет перенесён в background, уже не нужно переписывать.
    """
    orphans = services.orders.find_paid_orphans()
    if not orphans:
        return
    logger.warning("Найдено %d PAID-заказов без доставки — восстанавливаем.", len(orphans))
    for order_id in orphans:
        asyncio.to_thread(_recover_one_order, services, order_id)


async def _ttl_watcher(services: Services, interval_seconds: int = 60) -> None:
    """Фоновая задача: отмена просроченных pending-заказов.

    Без неё PENDING-заказы накапливаются бесконечно (особенно в Mock-режиме,
    где пользователь может не закончить оплату). Вызывается
    `OrderService.expire_overdue(ttl_seconds)` — он делает заказы CANCELLED,
    освобождает ключи, фейлит связанные payment.
    """
    ttl = services.config.payment_ttl_seconds
    logger.info("TTL watcher запущен (ttl=%s sec, interval=%s).", ttl, interval_seconds)
    while True:
        try:
            cancelled = await asyncio.to_thread(services.orders.expire_overdue, ttl)
            if cancelled:
                logger.info("TTL watcher: отменено %s заказов: %s", len(cancelled), cancelled)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("TTL watcher: исключение, продолжим.")
        await asyncio.sleep(interval_seconds)


async def main_async() -> None:
    cfg = load_config(".env")
    logging.basicConfig(
        level=cfg.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("Запуск tg_digital_market (provider=%s)", cfg.payment_provider)

    bot = Bot(
        token=cfg.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    factory = ServiceFactory(cfg)
    services = factory.build(notification_channel=AiogramNotificationChannel(bot))

    _maybe_recover_paid_orphans(services)

    dp = Dispatcher()
    dp.message.middleware(WorkflowMiddleware(services))
    dp.callback_query.middleware(WorkflowMiddleware(services))
    dp.pre_checkout_query.middleware(WorkflowMiddleware(services))
    dp.include_router(build_router())

    # Фоновая задача: TTL-сборка просроченных pending-заказов.
    ttl_task = asyncio.create_task(_ttl_watcher(services, interval_seconds=60))

    try:
        logger.info("Начинаем polling...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        ttl_task.cancel()
        try:
            await ttl_task
        except (asyncio.CancelledError, Exception):
            pass
        await bot.session.close()
        logger.info("Бот остановлен.")


def main() -> None:
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Остановлено пользователем.")
        sys.exit(0)


if __name__ == "__main__":
    main()
