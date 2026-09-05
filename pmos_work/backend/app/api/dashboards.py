"""Dashboard Engine API (4.md §23, §43-46).

- /dashboards: CRUD + duplicate + templates
- /dashboard-widgets: CRUD + layout/config/hide (PATCH/DELETE на уровне виджета)
- /dashboards/widget-types, /dashboards/templates: metadata реестра

Right security (4.md §46): каждый запрос — workspace -> dashboard -> widget.
В MVP один workspace (DEMO), но проверка «виджет принадлежит дашборду» и
«дашборд принадлежит workspace» выполняется в каждом хендлере — подстановка
чужого ID невозможна (404).

Optimistic locking (4.md §44): dashboards.version инкрементируется при каждом
изменении; PATCH с устаревшей version → 409, без silent corruption layout.
"""
import copy
import uuid
from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models import Dashboard, DashboardWidget
from ..schemas import (
    DashboardCreate,
    DashboardRead,
    DashboardUpdate,
    DashboardWidgetBase,
    DashboardWidgetCreate,
    DashboardWidgetRead,
    DashboardWidgetUpdate,
)
from ..services import add_audit
from ..widget_registry import TEMPLATES, WIDGET_REGISTRY, resolve_widget_type, template_widgets

router = APIRouter(prefix="/dashboards", tags=["dashboards"])
widgets_router = APIRouter(prefix="/dashboard-widgets", tags=["dashboards"])

DEMO_WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def _get_dashboard(db: AsyncSession, dash_id: uuid.UUID, with_widgets: bool = False) -> Dashboard:
    """Eager-загрузка (+populate_existing): identity-map не должен вернуть
    объект без загруженной коллекции widgets (иначе lazy-load -> MissingGreenlet)."""
    stmt = select(Dashboard).where(Dashboard.id == dash_id)
    if with_widgets:
        stmt = stmt.options(selectinload(Dashboard.widgets))
    dash = (await db.execute(stmt.execution_options(populate_existing=True))).scalars().first()
    if dash is None or dash.workspace_id != DEMO_WORKSPACE_ID:
        raise HTTPException(status_code=404, detail="Дашборд не найден")
    return dash


async def _get_widget(db: AsyncSession, widget_id: uuid.UUID) -> DashboardWidget:
    w = (
        await db.execute(
            select(DashboardWidget)
            .where(DashboardWidget.id == widget_id)
            .options(selectinload(DashboardWidget.dashboard))
            .execution_options(populate_existing=True)
        )
    ).scalars().first()
    if w is None or w.dashboard.workspace_id != DEMO_WORKSPACE_ID:
        raise HTTPException(status_code=404, detail="Виджет не найден")
    return w


async def _bump_version(db: AsyncSession, dash_id: uuid.UUID) -> None:
    """Инкремент version (optimistic locking 4.md §44) + updated_at."""
    await db.execute(
        update(Dashboard)
        .where(Dashboard.id == dash_id)
        .values(version=Dashboard.version + 1)
        .execution_options(synchronize_session="evaluate")
    )


async def _ensure_single_default(db: AsyncSession, keep_id: uuid.UUID) -> None:
    """Только один is_default в workspace (4.md §20)."""
    await db.execute(
        update(Dashboard)
        .where(Dashboard.workspace_id == DEMO_WORKSPACE_ID, Dashboard.id != keep_id)
        .values(is_default=False)
    )


def _widget_to_read(w: DashboardWidget) -> DashboardWidgetRead:
    return DashboardWidgetRead(
        id=w.id,
        dashboard_id=w.dashboard_id,
        widget_type=resolve_widget_type(w.widget_type),
        title=w.title,
        config=w.config,
        layout=w.layout,
        is_hidden=w.is_hidden,
        position=w.position,
        width=w.width,
        height=w.height,
        is_visible=w.is_visible,
        created_at=w.created_at,
        updated_at=w.updated_at,
    )


def _dashboard_to_read(d: Dashboard) -> DashboardRead:
    """Ручная конвертация: без отложенной загрузки и c нормализацией widget_type."""
    return DashboardRead(
        id=d.id,
        workspace_id=d.workspace_id,
        name=d.name,
        is_default=d.is_default,
        version=d.version,
        layout=d.layout,
        created_at=d.created_at,
        updated_at=d.updated_at,
        widgets=[_widget_to_read(w) for w in (d.widgets or [])],
    )


def _next_layout(db_widgets: list[DashboardWidget], default_size: dict) -> dict:
    """Автораскладка нового виджета: снизу существующих (4.md §7)."""
    col_w = 12
    max_y = 0
    occupied = []
    for w in db_widgets:
        lay = w.layout or {}
        x, y = lay.get("x", 0), lay.get("y", 0)
        ww, hh = lay.get("w", w.width or 1), lay.get("h", w.height or 1)
        occupied.append((x, y, ww, hh))
        if y + hh > max_y:
            max_y = y + hh
    x, y = 0, max_y
    w_size = default_size.get("w", 4)
    h_size = default_size.get("h", 3)
    # ищем первую свободную строку/колонку слева-направо
    for yy in range(max_y, max_y + 12):
        for xx in range(0, col_w - w_size + 1):
            clash = any(
                not (xx + w_size <= ox or xx >= ox + oww or yy + h_size <= oy or yy >= oy + ohh)
                for (ox, oy, oww, ohh) in occupied
            )
            if not clash:
                y, x = yy, xx
                break
        if y != max_y:
            break
    return {"x": x, "y": y, "w": w_size, "h": h_size}


# ---------------------------------------------------------------------------
# Реестр / metadata
# ---------------------------------------------------------------------------
@router.get("/widget-types")
async def widget_types():
    """Вся metadata реестра (4.md §2) — для Widget Picker по категориям."""
    return [dict(v, default_size=dict(v["default_size"])) for v in WIDGET_REGISTRY.values()]


@router.get("/templates")
async def templates_meta():
    return [{"key": k, "name": v["name"]} for k, v in TEMPLATES.items()]


# ---------------------------------------------------------------------------
# CRUD Dashboards (4.md §23)
# ---------------------------------------------------------------------------
@router.get("", response_model=list[DashboardRead])
async def list_dashboards(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Dashboard)
        .where(Dashboard.workspace_id == DEMO_WORKSPACE_ID)
        .options(selectinload(Dashboard.widgets))
        .order_by(Dashboard.is_default.desc(), Dashboard.created_at)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [_dashboard_to_read(d) for d in rows]


@router.post("", response_model=DashboardRead, status_code=201)
async def create_dashboard(payload: DashboardCreate, db: AsyncSession = Depends(get_db)):
    """Создание Dashboard. template (4.md §35) = сразу набор виджетов."""
    draw = Dashboard(
        workspace_id=DEMO_WORKSPACE_ID,
        name=payload.name,
        is_default=payload.is_default,
    )
    db.add(draw)
    await db.flush()

    if payload.is_default:
        await _ensure_single_default(db, keep_id=draw.id)

    if payload.template and payload.template != "empty":
        for w in template_widgets(payload.template):
            db.add(
                DashboardWidget(
                    dashboard_id=draw.id,
                    widget_type=resolve_widget_type(w["widget_type"]),
                    title=w.get("title") or WIDGET_REGISTRY.get(w["widget_type"], {}).get("name", "Виджет"),
                    config=w.get("config") or {},
                    layout=w.get("layout") or {},
                )
            )
    await db.commit()

    result = await _get_dashboard(db, draw.id, with_widgets=True)
    await add_audit(db, DEMO_WORKSPACE_ID, "Система", "create", "dashboard", draw.id, new_value={"name": draw.name})
    await db.commit()
    return _dashboard_to_read(result)


@router.get("/{dash_id}", response_model=DashboardRead)
async def get_dashboard(dash_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    dash = await _get_dashboard(db, dash_id, with_widgets=True)
    return _dashboard_to_read(dash)


@router.patch("/{dash_id}", response_model=DashboardRead)
async def update_dashboard(
    dash_id: uuid.UUID, payload: DashboardUpdate, db: AsyncSession = Depends(get_db)
):
    dash = await _get_dashboard(db, dash_id, with_widgets=True)
    # optimistic locking (4.md §44) — только если клиент передал ожидаемую версию
    if payload.version is not None and payload.version != dash.version:
        raise HTTPException(status_code=409, detail=f"Дашборд изменён (версия {dash.version}), обновите страницу")
    changed = False
    if payload.name is not None and payload.name != dash.name:
        dash.name = payload.name
        changed = True
    if payload.is_default is not None and payload.is_default != dash.is_default:
        dash.is_default = payload.is_default
        if payload.is_default:
            await _ensure_single_default(db, keep_id=dash.id)
        changed = True
    if changed:
        dash.version += 1
        await db.commit()
    result = await _get_dashboard(db, dash_id, with_widgets=True)
    return _dashboard_to_read(result)


@router.delete("/{dash_id}", status_code=204)
async def delete_dashboard(dash_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    dash = await _get_dashboard(db, dash_id)
    was_default = dash.is_default
    await db.delete(dash)  # widgets каскадом (relationship delete-orphan)
    await db.commit()
    if was_default:
        # назначаем новый default — старейший из оставшихся (4.md §20)
        remaining = (await db.execute(
            select(Dashboard).where(Dashboard.workspace_id == DEMO_WORKSPACE_ID)
            .order_by(Dashboard.created_at)
        )).scalars().all()
        if remaining:
            remaining[0].is_default = True
            await db.commit()


@router.post("/{dash_id}/duplicate", response_model=DashboardRead, status_code=201)
async def duplicate_dashboard(dash_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Копия дашборда: widgets, layout, settings. Данные НЕ копируются (4.md §19)."""
    src = await _get_dashboard(db, dash_id, with_widgets=True)
    new_name = f"{src.name} — копия"
    copy_dash = Dashboard(
        workspace_id=DEMO_WORKSPACE_ID,
        name=new_name,
        is_default=False,
    )
    db.add(copy_dash)
    await db.flush()
    for w in src.widgets:
        db.add(
            DashboardWidget(
                dashboard_id=copy_dash.id,
                widget_type=resolve_widget_type(w.widget_type),
                title=w.title,
                config=copy.deepcopy(w.config) if w.config else {},
                layout=copy.deepcopy(w.layout) if w.layout else {"x": 0, "y": 0, "w": w.width or 1, "h": w.height or 1},
                is_hidden=w.is_hidden,
            )
        )
    await db.commit()
    result = await _get_dashboard(db, copy_dash.id, with_widgets=True)
    await add_audit(db, DEMO_WORKSPACE_ID, "Система", "duplicate", "dashboard", copy_dash.id, new_value={"name": new_name})
    await db.commit()
    return _dashboard_to_read(result)


# ---------------------------------------------------------------------------
# Widgets (4.md §23)
# ---------------------------------------------------------------------------
@router.get("/{dash_id}/widgets", response_model=list[DashboardWidgetRead])
async def list_widgets(dash_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await _get_dashboard(db, dash_id)
    stmt = (
        select(DashboardWidget)
        .where(DashboardWidget.dashboard_id == dash_id)
        .order_by(DashboardWidget.created_at)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [_widget_to_read(w) for w in rows]


@router.post("/{dash_id}/widgets", response_model=DashboardWidgetRead, status_code=201)
async def add_widget(
    dash_id: uuid.UUID, payload: DashboardWidgetCreate, db: AsyncSession = Depends(get_db)
):
    dash = await _get_dashboard(db, dash_id, with_widgets=True)
    wtype = resolve_widget_type(payload.widget_type)
    meta = WIDGET_REGISTRY.get(wtype)
    if meta is None:
        raise HTTPException(status_code=422, detail=f"Неизвестный виджет: {payload.widget_type}")
    layout = payload.layout or _next_layout(
        list(dash.widgets), meta.get("default_size", {"w": 4, "h": 3})
    )
    title = payload.title or meta["name"]
    w = DashboardWidget(
        dashboard_id=dash_id,
        widget_type=wtype,
        title=title,
        config=payload.config or {},
        layout=layout,
        is_hidden=False,
    )
    db.add(w)
    await _bump_version(db, dash_id)
    await db.commit()
    await db.refresh(w)
    return _widget_to_read(w)


@widgets_router.get("/{widget_id}", response_model=DashboardWidgetRead)
async def get_widget(widget_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Один виджет (permission-проверка: чужой/удалённый -> 404)."""
    w = await _get_widget(db, widget_id)
    return _widget_to_read(w)


@widgets_router.patch("/{widget_id}", response_model=DashboardWidgetRead)
async def update_widget(
    widget_id: uuid.UUID, payload: DashboardWidgetUpdate, db: AsyncSession = Depends(get_db)
):
    """layout/config/hide/restore. Автосохранение drag&drop — без кнопки Save (4.md §5)."""
    w = await _get_widget(db, widget_id)
    changed = False
    for field in ("title", "config", "layout", "is_hidden"):
        val = getattr(payload, field)
        if val is not None:
            setattr(w, field, val)
            changed = True
    if changed:
        await _bump_version(db, w.dashboard_id)
        await db.commit()
    await db.refresh(w)
    return _widget_to_read(w)


@widgets_router.delete("/{widget_id}", status_code=204)
async def delete_widget(widget_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Удаление Widget Instance НЕ удаляет данные (4.md §8)."""
    w = await _get_widget(db, widget_id)
    await _bump_version(db, w.dashboard_id)
    await db.delete(w)
    await db.commit()


# legacy-маршруты (этап 1) — сохраняем для обратной совместимости (Additive)
@router.patch("/widgets/{widget_id}", response_model=DashboardWidgetRead)
async def update_widget_legacy(
    widget_id: uuid.UUID, payload: DashboardWidgetBase, db: AsyncSession = Depends(get_db)
):
    w = await _get_widget(db, widget_id)
    upd = DashboardWidgetUpdate()
    if payload.title is not None:
        upd.title = payload.title
    if payload.configuration is not None:
        upd.config = payload.configuration
    if payload.layout is not None:
        upd.layout = payload.layout
    if not payload.is_visible:
        upd.is_hidden = True
    return await update_widget(widget_id, upd, db)


@router.delete("/widgets/{widget_id}", status_code=204)
async def delete_widget_legacy(widget_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await delete_widget(widget_id, db)