"""printcalc_web — web-слой Phase 1 «Печатника» (v3).

Собирает FastAPI-приложение приёма заказа поверх движка printcalc:
прайс-каталог услуг на кассе (Р5/Р5а), главный экран по Р5б,
заказы со статусами Р2, OrderExport для ручного переноса в WF (Р1).

Запуск из корня printcalc::

    python -m uvicorn printcalc_web:create_app --factory
    # или
    python -m printcalc_web
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from starlette.responses import JSONResponse

from printcalc_web import api, views
from printcalc_web.db import connect
from printcalc_web.store import StoreError, seed_materials, seed_operations, seed_sections

__version__ = "0.1.0"

__all__ = ["__version__", "create_app"]


def create_app(db_path: Path | None = None) -> FastAPI:
    """Фабрика приложения. db_path — путь к SQLite (None → default_db_path)."""
    app = FastAPI(title="PrintCalc Pro — приём заказа (Phase 1)")
    app.state.db_path = db_path

    # Идемпотентные севы при старте: разделы экрана + канонические материалы.
    # Ошибки сева не должны ронять приложение (БД может быть read-only в миграции).
    try:
        conn = connect(db_path)
        try:
            seed_sections(conn)
            seed_materials(conn)
            seed_operations(conn)
        finally:
            conn.close()
    except Exception:  # noqa: BLE001 — сев не критичен для старта
        pass

    @app.exception_handler(StoreError)
    async def _store_error_handler(_request: Request, exc: StoreError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    app.include_router(api.router)
    app.include_router(views.router)
    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Этап 6: Telegram-поллер (daemon; без PRINTCALC_TG_TOKEN — no-op).
    from printcalc_web import telegram

    telegram.start_poller(app)

    return app
