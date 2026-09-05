"""Идемпотентный seed RBAC (Stage 9): системные роли + permissions + backfill memberships.

Вызывается из conftest (тесты) и при старте приложения (self-healing после
drop_all в тестовой БД). Повторный запуск безопасен.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Permission, Role, RolePermission, User, WorkspaceMember

DEMO_WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

SYSTEM_ROLES: dict[str, dict] = {
    "OWNER": {"name": "Owner", "description": "Full workspace access", "permissions": "*"},
    "ADMIN": {
        "name": "Admin",
        "description": "Workspace administration",
        "permissions": [
            "project.read", "project.create", "project.update", "project.delete",
            "project.import", "project.bulk_update",
            "task.read", "task.create", "task.update", "task.delete", "task.bulk_update",
            "production.read", "production.update",
            "finance.read", "finance.update",
            "document.read", "document.create", "document.update", "document.delete",
            "automation.read", "automation.create", "automation.update", "automation.delete",
            "view.read", "view.create", "view.update", "view.delete",
            "workspace.read", "workspace.update",
            "member.read", "member.invite", "member.update", "member.remove",
            "role.manage",
        ],
    },
    "MANAGER": {
        "name": "Manager",
        "description": "Operational management",
        "permissions": [
            "project.read", "project.create", "project.update",
            "task.read", "task.create", "task.update",
            "production.read", "production.update",
            "finance.read", "finance.update",
            "document.read", "document.create", "document.update",
            "view.read", "view.create", "view.update",
            "automation.read",
        ],
    },
    "MEMBER": {
        "name": "Member",
        "description": "Standard member access",
        "permissions": [
            "project.read",
            "task.read", "task.create", "task.update",
            "production.read",
            "document.read",
            "view.read",
        ],
    },
    "VIEWER": {
        "name": "Viewer",
        "description": "Read-only access",
        "permissions": [
            "project.read", "task.read", "production.read", "document.read", "view.read",
        ],
    },
}

ALL_PERMISSIONS = [
    "project.read", "project.create", "project.update", "project.delete",
    "project.import", "project.bulk_update",
    "task.read", "task.create", "task.update", "task.delete", "task.bulk_update",
    "production.read", "production.update",
    "finance.read", "finance.update",
    "document.read", "document.create", "document.update", "document.delete",
    "automation.read", "automation.create", "automation.update", "automation.delete",
    "view.read", "view.create", "view.update", "view.delete",
    "workspace.read", "workspace.update",
    "member.read", "member.invite", "member.update", "member.remove",
    "role.manage",
]


async def seed_rbac(session: AsyncSession) -> None:
    """Создаёт permissions, системные роли и их связи (идемпотентно)."""
    # Permissions
    perm_by_code: dict[str, Permission] = {}
    existing_perms = (await session.execute(select(Permission))).scalars().all()
    for p in existing_perms:
        perm_by_code[p.code] = p
    for code in ALL_PERMISSIONS:
        if code not in perm_by_code:
            p = Permission(code=code, description=code)
            session.add(p)
            perm_by_code[code] = p
    await session.flush()

    # System roles (workspace_id IS NULL)
    role_by_code: dict[str, Role] = {}
    existing_roles = (
        await session.execute(select(Role).where(Role.workspace_id.is_(None)))
    ).scalars().all()
    for r in existing_roles:
        role_by_code[r.code] = r
    for code, spec in SYSTEM_ROLES.items():
        if code not in role_by_code:
            role = Role(
                workspace_id=None,
                name=spec["name"],
                code=code,
                description=spec["description"],
                is_system=True,
            )
            session.add(role)
            await session.flush()
            role_by_code[code] = role

    # role_permissions
    for code, spec in SYSTEM_ROLES.items():
        role = role_by_code[code]
        wanted = ALL_PERMISSIONS if spec["permissions"] == "*" else spec["permissions"]
        existing_rp = (
            await session.execute(
                select(RolePermission).where(RolePermission.role_id == role.id)
            )
        ).scalars().all()
        have = {rp.permission_id for rp in existing_rp}
        for pcode in wanted:
            p = perm_by_code.get(pcode)
            if p is None or p.id in have:
                continue
            session.add(RolePermission(role_id=role.id, permission_id=p.id))

    await session.flush()


async def backfill_memberships(session: AsyncSession) -> None:
    """Backfill: существующие users (single-workspace) -> workspace_members."""
    users = (await session.execute(select(User))).scalars().all()
    role_by_code: dict[str, Role] = {}
    existing_roles = (
        await session.execute(select(Role).where(Role.workspace_id.is_(None)))
    ).scalars().all()
    for r in existing_roles:
        role_by_code[r.code] = r

    existing_members = (
        await session.execute(select(WorkspaceMember))
    ).scalars().all()
    member_keys = {(m.workspace_id, m.user_id) for m in existing_members}

    for user in users:
        if (user.workspace_id, user.id) in member_keys:
            continue
        role_code = user.role if user.role in role_by_code else "MEMBER"
        role = role_by_code.get(role_code) or role_by_code.get("MEMBER")
        if role is None:
            continue
        session.add(
            WorkspaceMember(
                workspace_id=user.workspace_id,
                user_id=user.id,
                role_id=role.id,
                status="ACTIVE" if user.is_active else "DEACTIVATED",
            )
        )
    await session.flush()
