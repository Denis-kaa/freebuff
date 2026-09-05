"""Точка входа FastAPI-приложения PM OS."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import (
    audit,
    automations,
    calendar,
    custom_fields,
    dashboard_data,
    dashboards,
    documents,
    events,
    exports,
    imports,
    integrations,
    project_items,
    projects,
    rbac,
    search,
    tasks,
    views,
)
from .config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Self-healing: гарантирует системные роли/permissions при старте (RBAC §6)."""
    try:
        from .database import SessionLocal
        from .seed_rbac import backfill_memberships, seed_rbac

        async with SessionLocal() as session:
            await seed_rbac(session)
            await backfill_memberships(session)
            await session.commit()
    except Exception:
        # Не блокируем старт при недоступной БД — роуты упадут сами при обращении.
        pass
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.5.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix=settings.api_prefix)
app.include_router(search.router, prefix=settings.api_prefix)
# порядок важен: вложенные роутеры (с большей специфичностью пути) до более общих
app.include_router(events.router, prefix=settings.api_prefix)
app.include_router(tasks.router, prefix=settings.api_prefix)
app.include_router(documents.router, prefix=settings.api_prefix)
app.include_router(project_items.router, prefix=settings.api_prefix)
app.include_router(custom_fields.router, prefix=settings.api_prefix)
app.include_router(views.router, prefix=settings.api_prefix)
app.include_router(dashboards.router, prefix=settings.api_prefix)
app.include_router(dashboards.widgets_router, prefix=settings.api_prefix)
app.include_router(dashboard_data.router, prefix=settings.api_prefix)
app.include_router(calendar.router, prefix=settings.api_prefix)
app.include_router(imports.router, prefix=settings.api_prefix)
app.include_router(exports.router, prefix=settings.api_prefix)
app.include_router(integrations.router, prefix=settings.api_prefix)
app.include_router(integrations.sheets_router, prefix=settings.api_prefix)
app.include_router(audit.router, prefix=settings.api_prefix)
app.include_router(automations.router, prefix=settings.api_prefix)
app.include_router(rbac.router, prefix=settings.api_prefix)


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.app_name}


# --- Frontend (Vite SPA) ---
_FRONTEND_DIST = Path("/var/www/pm_os/frontend/dist")

if _FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=_FRONTEND_DIST / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(_FRONTEND_DIST / "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        """SPA fallback (5.md §46): /calendar, /projects, /dashboard/{id} — client-роутинг."""
        return FileResponse(_FRONTEND_DIST / "index.html")
