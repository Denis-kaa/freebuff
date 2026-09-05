"""RBAC: permission engine, current_user dependency, workspace isolation (Stage 9).

Design:
- current_user resolves the active user from the X-User-Id header (MVP).
  In production this would be replaced by a JWT/session dependency.
- UserContext carries user_id, workspace_id, role code, and permission set.
- require_permission("project.update") returns a dependency that checks.
- Finance fields are masked when the user lacks finance.read.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .models import Permission, Role, RolePermission, User, WorkspaceMember

# Demo workspace (single-tenant MVP). Real multi-workspace switching later.
DEMO_WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

# Fields considered sensitive financial data (RBAC §15).
FINANCE_FIELDS = {
    "payment_percent",
    "currency",
    "advance_date",
    "final_payment_date",
}


@dataclass
class UserContext:
    """Resolved user context for the current request."""

    user_id: Optional[uuid.UUID]
    workspace_id: uuid.UUID
    role_code: str
    permissions: set[str] = field(default_factory=set)
    display_name: str = "Менеджер"
    is_demo: bool = True

    def has(self, perm: str) -> bool:
        """Check if the user has a permission. OWNER always returns True."""
        if self.role_code == "OWNER":
            return True
        return perm in self.permissions

    def can_read_finance(self) -> bool:
        return self.has("finance.read")


async def _load_permissions(
    session: AsyncSession, role_id: uuid.UUID
) -> set[str]:
    rows = (
        await session.execute(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role_id)
        )
    ).scalars().all()
    return set(rows)


async def resolve_user(
    session: AsyncSession,
    user_id: Optional[uuid.UUID],
    workspace_id: uuid.UUID = DEMO_WORKSPACE_ID,
) -> UserContext:
    """Resolve a UserContext from user_id or fall back to demo admin."""
    if user_id is not None:
        member = (
            await session.execute(
                select(WorkspaceMember)
                .where(
                    WorkspaceMember.user_id == user_id,
                    WorkspaceMember.workspace_id == workspace_id,
                )
            )
        ).scalars().first()

        if member and member.status == "ACTIVE":
            role = await session.get(Role, member.role_id)
            perms = await _load_permissions(session, member.role_id)
            user = await session.get(User, user_id)
            return UserContext(
                user_id=user_id,
                workspace_id=workspace_id,
                role_code=role.code if role else "MEMBER",
                permissions=perms,
                display_name=user.display_name if user else "User",
                is_demo=False,
            )

        # Реальный пользователь без ACTIVE membership в этом workspace:
        # НЕ fallback на demo-admin — это дыра IDOR (RBAC §28, §52).
        # Отдаём контекст без единого permission: все проверки дадут 403.
        return UserContext(
            user_id=user_id,
            workspace_id=workspace_id,
            role_code="NONE",
            permissions=set(),
            display_name="",
            is_demo=False,
        )

    # Demo fallback: full admin (backward compat with stages 1-8)
    admin_role = (
        await session.execute(
            select(Role).where(Role.workspace_id.is_(None), Role.code == "ADMIN")
        )
    ).scalars().first()
    perms: set[str] = set()
    if admin_role:
        perms = await _load_permissions(session, admin_role.id)
    return UserContext(
        user_id=None,
        workspace_id=workspace_id,
        role_code="ADMIN",
        permissions=perms,
        display_name="Менеджер",
        is_demo=True,
    )


async def get_current_user(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-Id"),
    db: AsyncSession = Depends(get_db),
) -> UserContext:
    """FastAPI dependency: resolve current user + workspace (RBAC §29).

    X-User-Id — идентификатор пользователя; X-Workspace-Id — активный workspace
    (переключение workspace в UI, RBAC §29). Если workspace не передан —
    используется DEMO_WORKSPACE_ID (обратная совместимость).
    """
    uid: Optional[uuid.UUID] = None
    if x_user_id:
        try:
            uid = uuid.UUID(x_user_id)
        except (ValueError, AttributeError):
            raise HTTPException(status_code=401, detail="Invalid X-User-Id")

    ws_id: uuid.UUID = DEMO_WORKSPACE_ID
    if x_workspace_id:
        try:
            ws_id = uuid.UUID(x_workspace_id)
        except (ValueError, AttributeError):
            raise HTTPException(status_code=400, detail="Invalid X-Workspace-Id")
    return await resolve_user(db, uid, workspace_id=ws_id)


def require_permission(perm: str):
    """Dependency factory: require a specific permission."""

    async def _checker(ctx: UserContext = Depends(get_current_user)) -> UserContext:
        if not ctx.has(perm):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {perm}",
            )
        return ctx

    return _checker


def mask_finance_fields(
    ctx: UserContext, data: dict[str, Any]
) -> dict[str, Any]:
    """Mask financial fields (set to None) if the user lacks finance.read.

    Удалять ключи нельзя: Pydantic-модель ProjectRead подставит default
    (например currency="RUB") — данные всё равно утекут. Поэтому значения
    принудительно обнуляются (RBAC §15: backend исключает данные).
    """
    if ctx.can_read_finance():
        return data
    out = dict(data)
    for f in FINANCE_FIELDS:
        out[f] = None
    return out


def mask_finance_fields_bulk(
    ctx: UserContext, items: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if ctx.can_read_finance():
        return items
    return [mask_finance_fields(ctx, item) for item in items]


def check_workspace_access(ctx: UserContext, resource_workspace_id: Any) -> None:
    """IDOR protection: resource must belong to the user's workspace."""
    if resource_workspace_id != ctx.workspace_id:
        raise HTTPException(status_code=404, detail="Resource not found")
