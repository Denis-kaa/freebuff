"""HTML-страницы Phase 1: главный экран Р5б, список заказов, прайс-каталог.

Шаблоны — Jinja2; вся динамика через fetch к /api. Это «рабочий минимум»
UI Phase 1: функциональность по Р5б важнее красоты (CODE_QUALITY 13.1).
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from starlette.responses import Response

from printcalc_web.db import default_db_path

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

#: starlette <0.29: TemplateResponse(name, context); >=0.29: (request, name, context).
#: Первый параметр после self — 'request' в новой сигнатуре, 'name' в старой.
_TEMPLATE_PARAMS = [
    name for name in inspect.signature(Jinja2Templates.TemplateResponse).parameters if name != "self"
]
_TEMPLATE_NEW_STYLE = bool(_TEMPLATE_PARAMS) and _TEMPLATE_PARAMS[0] == "request"


def _render(request: Request, name: str, context: dict[str, Any] | None = None) -> Response:
    """Рендер шаблона, совместимый со старой и новой сигнатурой starlette."""
    ctx = dict(context or {})
    # mypy не может выбрать ветку по runtime-флагу — приводим к Any.
    respond: Any = templates.TemplateResponse
    if _TEMPLATE_NEW_STYLE:
        return respond(request, name, ctx)
    return respond(name, {**ctx, "request": request})


@router.get("/")
def home(request: Request):
    """Главный экран приёма заказа (Р5б v3)."""
    return _render(request, "index.html", {"db_path": str(default_db_path())})


@router.get("/orders")
def orders_page(request: Request):
    """Список заказов с фильтром по статусу (Р2 + Р5б)."""
    return _render(request, "orders.html")


@router.get("/estimates")
def estimates_page(request: Request):
    """Сметы: статусы DRAFT→ACCEPTED, snapshot, заказ из сметы (Этап 2)."""
    return _render(request, "estimates.html", {"active": "estimates"})


@router.get("/price-list")
def price_list_page(request: Request):
    """Прайс-каталог: список, «+», импорт, выгрузка, непроверенные."""
    return _render(request, "price_list.html")


@router.get("/constructor")
def constructor_page(request: Request):
    """Конструктор разделов главного экрана заказа."""
    return _render(request, "constructor.html")


@router.get("/production")
def production_page(request: Request):
    """Производство: доска заданий с чек-листами (Этап 4)."""
    return _render(request, "production.html", {"active": "production"})


@router.get("/inbox")
def inbox_page(request: Request):
    """Входящие: сообщения → заявки → сметы (Этап 6)."""
    return _render(request, "inbox.html", {"active": "inbox"})


@router.get("/clients")
def clients_page(request: Request):
    """Клиенты: список/поиск, карточка с контактами (Этап 1)."""
    return _render(request, "clients.html", {"active": "clients"})


@router.get("/analytics")
def analytics_page(request: Request):
    """Аналитика: маржинальность прайса vs себестоимость (сшивка cost)."""
    return _render(request, "analytics.html", {"active": "analytics"})


@router.get("/materials")
def materials_page(request: Request):
    """Реестр материалов (Этап 1)."""
    return _render(request, "materials.html", {"active": "materials"})
