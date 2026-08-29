"""handlers — пакет aiogram-роутеров.

Импортируем все роутеры здесь, чтобы в `bot/main.py` можно было
одной строкой собрать диспетчер.
"""

from aiogram import Router

from . import common, catalog, account, cart, admin, seller


def build_router() -> Router:
    """Собрать корневой роутер с вложенными модулями.
    Порядок важен: cart должен быть до admin (более специфичные inline).
    """
    root = Router(name="market_bot_root")
    # Общий бот-флоу
    root.include_router(common.router)
    root.include_router(catalog.router)
    root.include_router(account.router)
    root.include_router(cart.router)
    root.include_router(admin.router)
    root.include_router(seller.router)
    return root


__all__ = ["build_router"***REMOVED***
