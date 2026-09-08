"""HTML-страницы Phase 1: главный экран Р5б, список заказов, прайс-каталог.

Шаблоны — Jinja2; вся динамика через fetch к /api. Это «рабочий минимум»
UI Phase 1: функциональность по Р5б важнее красоты (CODE_QUALITY 13.1).
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from printcalc_web.db import default_db_path

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@router.get("/")
def home(request: Request):
    """Главный экран приёма заказа (Р5б v3)."""
    # starlette 0.27: старая сигнатура TemplateResponse(name, context).
    return templates.TemplateResponse(
        "index.html", {"request": request, "db_path": str(default_db_path())}
    )


@router.get("/orders")
def orders_page(request: Request):
    """Список заказов с фильтром по статусу (Р2 + Р5б)."""
    return templates.TemplateResponse("orders.html", {"request": request})


@router.get("/price-list")
def price_list_page(request: Request):
    """Прайс-каталог: список, «+», импорт, выгрузка, непроверенные."""
    return templates.TemplateResponse("price_list.html", {"request": request})
