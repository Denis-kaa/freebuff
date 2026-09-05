"""RBAC API: /me, /permissions, /workspaces, members, roles, invitations (Stage 9)."""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import (
    Permission,
    Role,
    RolePermission,
    User,
    Team,
    TeamMember,
    Workspace,
    WorkspaceInvitation,
    WorkspaceMember,
)
from ..rbac import DEMO_WORKSPACE_ID, UserContext, get_current_user, require_permission
from ..schemas import (
    InvitationAccept,
    InvitationCreate,
    InvitationRead,
    PermissionRead,
    RoleCreate,
    RoleRead,
    RoleUpdate,
    TeamCreate,
    TeamUpdate,
    TeamMemberUpdate,
    TeamRead,
    UserPermissionsResponse,
    UserRead,
    UserUpdateProfile,
    WorkspaceCreate,
    WorkspaceMemberRead,
    WorkspaceMemberUpdate,
    WorkspaceRead,
    OwnershipTransfer,
    WorkspaceUpdate,
)
from ..services import add_audit

router = APIRouter(tags=["rbac"])


# ---------------------------------------------------------------------------
# /me and /permissions
# ---------------------------------------------------------------------------
@router.get("/me", response_model=UserRead)
async def get_me(ctx: UserContext = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if ctx.user_id is None:
        # Demo user
        user = (
            await db.execute(
                select(User).where(User.workspace_id == DEMO_WORKSPACE_ID).limit(1)
            )
        ).scalars().first()
    else:
        user = await db.get(User, ctx.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserRead(
        id=user.id,
        email=user.email,
        name=user.name or user.display_name,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        timezone=user.timezone,
        language=user.language,
        role=user.role,
        created_at=user.created_at,
    )


@router.patch("/me", response_model=UserRead)
async def update_me(
    payload: UserUpdateProfile,
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if ctx.user_id is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = await db.get(User, ctx.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    changes = payload.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(user, k, v)
    await db.commit()
    await db.refresh(user)
    return UserRead(
        id=user.id,
        email=user.email,
        name=user.name or user.display_name,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        timezone=user.timezone,
        language=user.language,
        role=user.role,
        created_at=user.created_at,
    )


@router.get("/permissions", response_model=UserPermissionsResponse)
async def get_my_permissions(
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Полная карта permissions текущего пользователя (RBAC §34)."""
    all_codes = (await db.execute(select(Permission.code).order_by(Permission.code))).scalars().all()
    return UserPermissionsResponse(
        user_id=ctx.user_id,
        role=ctx.role_code,
        workspace_id=ctx.workspace_id,
        permissions={code: ctx.has(code) for code in all_codes},
    )


@router.get("/permissions/list", response_model=list[PermissionRead])
async def list_all_permissions(
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(select(Permission).order_by(Permission.code))).scalars().all()
    return [PermissionRead(code=r.code, description=r.description) for r in rows]


# ---------------------------------------------------------------------------
# Workspaces
# ---------------------------------------------------------------------------
@router.get("/workspaces", response_model=list[WorkspaceRead])
async def list_workspaces(
    ctx: UserContext = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    if ctx.user_id is None:
        # Demo fallback (полный admin): показывает все workspace
        rows = (await db.execute(select(Workspace).order_by(Workspace.created_at))).scalars().all()
    else:
        rows = (
            await db.execute(
                select(Workspace)
                .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
                .where(WorkspaceMember.user_id == ctx.user_id)
                .order_by(Workspace.created_at)
            )
        ).scalars().all()
    return [
        WorkspaceRead(
            id=w.id, name=w.name, timezone=w.timezone,
            default_currency=w.default_currency, created_at=w.created_at,
        )
        for w in rows
    ]


@router.post("/workspaces", response_model=WorkspaceRead, status_code=201)
async def create_workspace(
    payload: WorkspaceCreate,
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = Workspace(
        name=payload.name,
        timezone=payload.timezone,
        default_currency=payload.default_currency,
    )
    db.add(ws)
    await db.flush()
    # Creator becomes OWNER
    if ctx.user_id is None:
        # Demo: create a demo user as owner
        owner = User(
            workspace_id=ws.id,
            email=f"owner@{payload.name.lower().replace(' ', '.')}.local",
            display_name="Owner",
            role="ADMIN",
        )
        db.add(owner)
        await db.flush()
        user_id = owner.id
    else:
        user_id = ctx.user_id
    owner_role = (
        await db.execute(
            select(Role).where(Role.workspace_id.is_(None), Role.code == "OWNER")
        )
    ).scalars().first()
    if owner_role:
        db.add(WorkspaceMember(
            workspace_id=ws.id, user_id=user_id, role_id=owner_role.id, status="ACTIVE",
        ))
    await db.commit()
    await db.refresh(ws)
    return WorkspaceRead(
        id=ws.id, name=ws.name, timezone=ws.timezone,
        default_currency=ws.default_currency, created_at=ws.created_at,
        owner_id=str(user_id), my_role="OWNER",
    )


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceRead)
async def get_workspace(
    workspace_id: uuid.UUID,
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await db.get(Workspace, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return WorkspaceRead(
        id=ws.id, name=ws.name, timezone=ws.timezone,
        default_currency=ws.default_currency, created_at=ws.created_at,
    )


@router.patch("/workspaces/{workspace_id}", response_model=WorkspaceRead)
async def update_workspace(
    workspace_id: uuid.UUID,
    payload: WorkspaceUpdate,
    ctx: UserContext = Depends(require_permission("workspace.update")),
    db: AsyncSession = Depends(get_db),
):
    ws = await db.get(Workspace, workspace_id)
    if not ws or ws.id != ctx.workspace_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    changes = payload.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(ws, k, v)
    await db.commit()
    await db.refresh(ws)
    return WorkspaceRead(
        id=ws.id, name=ws.name, timezone=ws.timezone,
        default_currency=ws.default_currency, created_at=ws.created_at,
    )


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------
async def _member_to_read(db: AsyncSession, member: WorkspaceMember) -> WorkspaceMemberRead:
    user = await db.get(User, member.user_id)
    role = await db.get(Role, member.role_id)
    return WorkspaceMemberRead(
        id=member.id,
        workspace_id=member.workspace_id,
        user_id=member.user_id,
        role_id=member.role_id,
        role_code=role.code if role else "MEMBER",
        status=member.status,
        email=user.email if user else None,
        display_name=user.display_name if user else None,
        joined_at=member.joined_at,
    )


@router.get("/workspaces/{workspace_id}/members", response_model=list[WorkspaceMemberRead])
async def list_members(
    workspace_id: uuid.UUID,
    ctx: UserContext = Depends(require_permission("member.read")),
    db: AsyncSession = Depends(get_db),
):
    if workspace_id != ctx.workspace_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    rows = (
        await db.execute(
            select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id)
        )
    ).scalars().all()
    return [await _member_to_read(db, m) for m in rows]


@router.patch("/workspaces/{workspace_id}/members/{member_id}", response_model=WorkspaceMemberRead)
async def update_member(
    workspace_id: uuid.UUID,
    member_id: uuid.UUID,
    payload: WorkspaceMemberUpdate,
    ctx: UserContext = Depends(require_permission("member.update")),
    db: AsyncSession = Depends(get_db),
):
    if workspace_id != ctx.workspace_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    member = await db.get(WorkspaceMember, member_id)
    if not member or member.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Member not found")
    if payload.role_id is not None:
        # Prevent demoting the last OWNER
        old_role = await db.get(Role, member.role_id)
        new_role = await db.get(Role, payload.role_id)
        if old_role and old_role.code == "OWNER" and new_role and new_role.code != "OWNER":
            owners = (
                await db.execute(
                    select(WorkspaceMember)
                    .join(Role, Role.id == WorkspaceMember.role_id)
                    .where(
                        WorkspaceMember.workspace_id == workspace_id,
                        Role.code == "OWNER",
                        WorkspaceMember.status == "ACTIVE",
                    )
                )
            ).scalars().all()
            if len(owners) <= 1:
                raise HTTPException(
                    status_code=400, detail="Cannot demote the last OWNER"
                )
        member.role_id = payload.role_id
    if payload.status is not None:
        member.status = payload.status
    await db.commit()
    await db.refresh(member)
    audit_changes = payload.model_dump(exclude_unset=True)
    for k, v in audit_changes.items():
        if isinstance(v, uuid.UUID):
            audit_changes[k] = str(v)
    await add_audit(db, workspace_id, ctx.display_name, "member_update", "member", member.id,
                    new_value=audit_changes)
    await db.commit()
    return await _member_to_read(db, member)


@router.delete("/workspaces/{workspace_id}/members/{member_id}", status_code=204)
async def remove_member(
    workspace_id: uuid.UUID,
    member_id: uuid.UUID,
    ctx: UserContext = Depends(require_permission("member.remove")),
    db: AsyncSession = Depends(get_db),
):
    if workspace_id != ctx.workspace_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    member = await db.get(WorkspaceMember, member_id)
    if not member or member.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Member not found")
    role = await db.get(Role, member.role_id)
    if role and role.code == "OWNER":
        owners = (
            await db.execute(
                select(WorkspaceMember)
                .join(Role, Role.id == WorkspaceMember.role_id)
                .where(
                    WorkspaceMember.workspace_id == workspace_id,
                    Role.code == "OWNER",
                    WorkspaceMember.status == "ACTIVE",
                )
            )
        ).scalars().all()
        if len(owners) <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the last OWNER")
    await db.delete(member)
    await add_audit(db, workspace_id, ctx.display_name, "member_remove", "member", member_id)
    await db.commit()


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------
@router.get("/workspaces/{workspace_id}/roles", response_model=list[RoleRead])
async def list_roles(
    workspace_id: uuid.UUID,
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if workspace_id != ctx.workspace_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    # System roles (workspace_id IS NULL) + workspace-specific
    rows = (
        await db.execute(
            select(Role).where(
                (Role.workspace_id.is_(None)) | (Role.workspace_id == workspace_id)
            ).order_by(Role.is_system.desc(), Role.code)
        )
    ).scalars().all()
    result = []
    for r in rows:
        perms = (
            await db.execute(
                select(Permission.code)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .where(RolePermission.role_id == r.id)
            )
        ).scalars().all()
        result.append(RoleRead(
            id=r.id, workspace_id=r.workspace_id, name=r.name, code=r.code,
            description=r.description, is_system=r.is_system, permissions=list(perms),
        ))
    return result


@router.post("/workspaces/{workspace_id}/roles", response_model=RoleRead, status_code=201)
async def create_role(
    workspace_id: uuid.UUID,
    payload: RoleCreate,
    ctx: UserContext = Depends(require_permission("role.manage")),
    db: AsyncSession = Depends(get_db),
):
    if workspace_id != ctx.workspace_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    existing = (
        await db.execute(
            select(Role).where(
                Role.workspace_id == workspace_id, Role.code == payload.code
            )
        )
    ).scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="Role code already exists")
    role = Role(
        workspace_id=workspace_id,
        name=payload.name,
        code=payload.code,
        description=payload.description,
        is_system=False,
    )
    db.add(role)
    await db.flush()
    # Attach permissions
    if payload.permissions:
        perm_rows = (
            await db.execute(
                select(Permission).where(Permission.code.in_(payload.permissions))
            )
        ).scalars().all()
        for p in perm_rows:
            db.add(RolePermission(role_id=role.id, permission_id=p.id))
    await db.commit()
    await db.refresh(role)
    await add_audit(db, workspace_id, ctx.display_name, "role_create", "role", role.id,
                    new_value={"name": role.name, "code": role.code})
    await db.commit()
    return RoleRead(
        id=role.id, workspace_id=role.workspace_id, name=role.name, code=role.code,
        description=role.description, is_system=role.is_system, permissions=payload.permissions,
    )


@router.patch("/workspaces/{workspace_id}/roles/{role_id}", response_model=RoleRead)
async def update_role(
    workspace_id: uuid.UUID,
    role_id: uuid.UUID,
    payload: RoleUpdate,
    ctx: UserContext = Depends(require_permission("role.manage")),
    db: AsyncSession = Depends(get_db),
):
    if workspace_id != ctx.workspace_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    role = await db.get(Role, role_id)
    if not role or role.workspace_id not in (None, workspace_id):
        raise HTTPException(status_code=404, detail="Role not found")
    if role.is_system and payload.permissions is not None:
        raise HTTPException(status_code=400, detail="Cannot modify system role permissions")
    if payload.name is not None:
        role.name = payload.name
    if payload.description is not None:
        role.description = payload.description
    if payload.permissions is not None:
        # Replace permissions
        existing = (
            await db.execute(
                select(RolePermission).where(RolePermission.role_id == role_id)
            )
        ).scalars().all()
        for rp in existing:
            await db.delete(rp)
        perm_rows = (
            await db.execute(
                select(Permission).where(Permission.code.in_(payload.permissions))
            )
        ).scalars().all()
        for p in perm_rows:
            db.add(RolePermission(role_id=role.id, permission_id=p.id))
    await db.commit()
    await db.refresh(role)
    perms = (
        await db.execute(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role.id)
        )
    ).scalars().all()
    return RoleRead(
        id=role.id, workspace_id=role.workspace_id, name=role.name, code=role.code,
        description=role.description, is_system=role.is_system, permissions=list(perms),
    )


@router.post("/workspaces/{workspace_id}/roles/{role_id}/duplicate", response_model=RoleRead, status_code=201)
async def duplicate_role(
    workspace_id: uuid.UUID,
    role_id: uuid.UUID,
    ctx: UserContext = Depends(require_permission("role.manage")),
    db: AsyncSession = Depends(get_db),
):
    if workspace_id != ctx.workspace_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    role = await db.get(Role, role_id)
    if not role or role.workspace_id not in (None, workspace_id):
        raise HTTPException(status_code=404, detail="Role not found")
    new_code = f"{role.code}_copy"
    new_role = Role(
        workspace_id=workspace_id,
        name=f"{role.name} — копия",
        code=new_code,
        description=role.description,
        is_system=False,
    )
    db.add(new_role)
    await db.flush()
    perms = (
        await db.execute(
            select(RolePermission).where(RolePermission.role_id == role_id)
        )
    ).scalars().all()
    for rp in perms:
        db.add(RolePermission(role_id=new_role.id, permission_id=rp.permission_id))
    await db.commit()
    await db.refresh(new_role)
    perm_codes = (
        await db.execute(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == new_role.id)
        )
    ).scalars().all()
    return RoleRead(
        id=new_role.id, workspace_id=new_role.workspace_id, name=new_role.name,
        code=new_role.code, description=new_role.description, is_system=False,
        permissions=list(perm_codes),
    )


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------
async def _team_to_read(db: AsyncSession, team, workspace_id: uuid.UUID) -> TeamRead:
    member_ids = (await db.execute(
        select(WorkspaceMember.user_id)
        .join(TeamMember, TeamMember.member_id == WorkspaceMember.id)
        .where(TeamMember.team_id == team.id)
    )).scalars().all()
    return TeamRead(id=team.id, workspace_id=workspace_id, name=team.name,
                    description=team.description, member_ids=list(member_ids))


@router.get("/workspaces/{workspace_id}/teams", response_model=list[TeamRead])
async def list_teams(workspace_id: uuid.UUID, ctx: UserContext = Depends(require_permission("member.read")), db: AsyncSession = Depends(get_db)):
    if workspace_id != ctx.workspace_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    rows = (await db.execute(select(Team).where(Team.workspace_id == workspace_id).order_by(Team.name))).scalars().all()
    return [await _team_to_read(db, team, workspace_id) for team in rows]


@router.post("/workspaces/{workspace_id}/teams", response_model=TeamRead, status_code=201)
async def create_team(workspace_id: uuid.UUID, payload: TeamCreate, ctx: UserContext = Depends(require_permission("member.update")), db: AsyncSession = Depends(get_db)):
    if workspace_id != ctx.workspace_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    team = Team(workspace_id=workspace_id, name=payload.name.strip(), description=payload.description)
    db.add(team)
    try:
        await db.flush()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Team name already exists")
    await add_audit(db, workspace_id, ctx.display_name, "team_create", "team", team.id, new_value={"name": team.name})
    await db.commit()
    await db.refresh(team)
    return await _team_to_read(db, team, workspace_id)


@router.patch("/workspaces/{workspace_id}/teams/{team_id}", response_model=TeamRead)
async def update_team(workspace_id: uuid.UUID, team_id: uuid.UUID, payload: TeamUpdate, ctx: UserContext = Depends(require_permission("member.update")), db: AsyncSession = Depends(get_db)):
    if workspace_id != ctx.workspace_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    team = await db.get(Team, team_id)
    if not team or team.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Team not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(team, key, value.strip() if key == "name" else value)
    await add_audit(db, workspace_id, ctx.display_name, "team_update", "team", team.id)
    await db.commit()
    await db.refresh(team)
    return await _team_to_read(db, team, workspace_id)


@router.delete("/workspaces/{workspace_id}/teams/{team_id}", status_code=204)
async def delete_team(workspace_id: uuid.UUID, team_id: uuid.UUID, ctx: UserContext = Depends(require_permission("member.update")), db: AsyncSession = Depends(get_db)):
    if workspace_id != ctx.workspace_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    team = await db.get(Team, team_id)
    if not team or team.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Team not found")
    await db.delete(team)
    await add_audit(db, workspace_id, ctx.display_name, "team_delete", "team", team.id)
    await db.commit()


@router.post("/workspaces/{workspace_id}/teams/{team_id}/members", response_model=TeamRead)
async def add_team_member(workspace_id: uuid.UUID, team_id: uuid.UUID, payload: TeamMemberUpdate, ctx: UserContext = Depends(require_permission("member.update")), db: AsyncSession = Depends(get_db)):
    if workspace_id != ctx.workspace_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    team = await db.get(Team, team_id)
    member = await db.get(WorkspaceMember, payload.member_id)
    if not team or team.workspace_id != workspace_id or not member or member.workspace_id != workspace_id or member.status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Team and member must belong to this workspace")
    existing = await db.get(TeamMember, {"team_id": team_id, "member_id": payload.member_id})
    if not existing:
        db.add(TeamMember(team_id=team_id, member_id=payload.member_id))
    await db.commit()
    await db.refresh(team)
    return await _team_to_read(db, team, workspace_id)


@router.delete("/workspaces/{workspace_id}/teams/{team_id}/members/{member_id}", response_model=TeamRead)
async def remove_team_member(workspace_id: uuid.UUID, team_id: uuid.UUID, member_id: uuid.UUID, ctx: UserContext = Depends(require_permission("member.update")), db: AsyncSession = Depends(get_db)):
    if workspace_id != ctx.workspace_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    team = await db.get(Team, team_id)
    if not team or team.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Team not found")
    link = await db.get(TeamMember, {"team_id": team_id, "member_id": member_id})
    if link:
        await db.delete(link)
        await db.commit()
    return await _team_to_read(db, team, workspace_id)


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------
@router.post("/workspaces/{workspace_id}/members/invite", response_model=InvitationRead, status_code=201)
async def invite_member(
    workspace_id: uuid.UUID,
    payload: InvitationCreate,
    ctx: UserContext = Depends(require_permission("member.invite")),
    db: AsyncSession = Depends(get_db),
):
    if workspace_id != ctx.workspace_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    role = (
        await db.execute(
            select(Role).where(
                (Role.workspace_id.is_(None)) | (Role.workspace_id == workspace_id),
                Role.code == payload.role_code,
            )
        )
    ).scalars().first()
    if not role:
        raise HTTPException(status_code=400, detail="Role not found")
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    inv = WorkspaceInvitation(
        workspace_id=workspace_id,
        email=payload.email,
        role_id=role.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        invited_by=ctx.user_id,
    )
    db.add(inv)
    await db.commit()
    await db.refresh(inv)
    await add_audit(db, workspace_id, ctx.display_name, "member_invite", "invitation", inv.id,
                    new_value={"email": payload.email, "role": payload.role_code})
    await db.commit()
    return InvitationRead(
        id=inv.id, workspace_id=inv.workspace_id, email=inv.email,
        role_id=inv.role_id, role_code=role.code,
        expires_at=inv.expires_at, accepted_at=inv.accepted_at,
        revoked_at=inv.revoked_at, created_at=inv.created_at,
    )


@router.get("/workspaces/{workspace_id}/invitations", response_model=list[InvitationRead])
async def list_invitations(
    workspace_id: uuid.UUID,
    ctx: UserContext = Depends(require_permission("member.read")),
    db: AsyncSession = Depends(get_db),
):
    if workspace_id != ctx.workspace_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    rows = (
        await db.execute(
            select(WorkspaceInvitation)
            .where(WorkspaceInvitation.workspace_id == workspace_id)
            .order_by(WorkspaceInvitation.created_at.desc())
        )
    ).scalars().all()
    result = []
    for inv in rows:
        role = await db.get(Role, inv.role_id)
        result.append(InvitationRead(
            id=inv.id, workspace_id=inv.workspace_id, email=inv.email,
            role_id=inv.role_id, role_code=role.code if role else None,
            expires_at=inv.expires_at, accepted_at=inv.accepted_at,
            revoked_at=inv.revoked_at, created_at=inv.created_at,
        ))
    return result


@router.post("/workspaces/{workspace_id}/ownership/transfer", response_model=WorkspaceMemberRead)
async def transfer_ownership(
    workspace_id: uuid.UUID,
    payload: OwnershipTransfer,
    ctx: UserContext = Depends(require_permission("workspace.update")),
    db: AsyncSession = Depends(get_db),
):
    """Передать OWNER другому ACTIVE участнику, не оставляя workspace без владельца."""
    if workspace_id != ctx.workspace_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    current = await db.scalar(
        select(WorkspaceMember).join(Role, Role.id == WorkspaceMember.role_id).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == ctx.user_id,
            Role.code == "OWNER",
            WorkspaceMember.status == "ACTIVE",
        )
    )
    if not current:
        raise HTTPException(status_code=403, detail="Only an OWNER can transfer ownership")
    target = await db.get(WorkspaceMember, payload.new_owner_member_id)
    if not target or target.workspace_id != workspace_id or target.status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Target member must be ACTIVE in this workspace")
    owner_role = await db.scalar(select(Role).where(Role.workspace_id.is_(None), Role.code == "OWNER"))
    fallback_role = await db.scalar(select(Role).where(Role.workspace_id.is_(None), Role.code == "ADMIN"))
    if not owner_role or not fallback_role:
        raise HTTPException(status_code=500, detail="System roles are not configured")
    current.role_id = fallback_role.id
    target.role_id = owner_role.id
    await add_audit(db, workspace_id, ctx.display_name, "ownership_transfer", "workspace", workspace_id,
                    new_value={"from_user_id": str(ctx.user_id), "to_user_id": str(target.user_id)})
    await db.commit()
    await db.refresh(target)
    return await _member_to_read(db, target)


@router.post("/invitations/accept", response_model=WorkspaceMemberRead)
async def accept_invitation(
    payload: InvitationAccept,
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Принять приглашение уже идентифицированным пользователем.

    Без полноценной auth-сессии намеренно не создаём пользователя по bearer token:
    это оставляет будущий Login/Session слой единственным источником identity.
    """
    if ctx.user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required to accept invitation")
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    inv = await db.scalar(select(WorkspaceInvitation).where(WorkspaceInvitation.token_hash == token_hash))
    now = datetime.now(timezone.utc)
    if not inv or inv.revoked_at or inv.accepted_at or inv.expires_at <= now:
        raise HTTPException(status_code=400, detail="Invitation is invalid or expired")
    user = await db.get(User, ctx.user_id)
    if not user or user.email.lower() != inv.email.lower():
        raise HTTPException(status_code=403, detail="Invitation email does not match current user")
    existing = await db.scalar(select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == inv.workspace_id, WorkspaceMember.user_id == ctx.user_id
    ))
    if existing:
        raise HTTPException(status_code=409, detail="User is already a workspace member")
    member = WorkspaceMember(workspace_id=inv.workspace_id, user_id=ctx.user_id, role_id=inv.role_id, status="ACTIVE")
    db.add(member)
    inv.accepted_at = now
    await add_audit(db, inv.workspace_id, ctx.display_name, "member_accepted", "invitation", inv.id,
                    new_value={"user_id": str(ctx.user_id)})
    await db.commit()
    await db.refresh(member)
    return await _member_to_read(db, member)


@router.delete("/workspaces/{workspace_id}/invitations/{invitation_id}", status_code=204)
async def revoke_invitation(
    workspace_id: uuid.UUID,
    invitation_id: uuid.UUID,
    ctx: UserContext = Depends(require_permission("member.invite")),
    db: AsyncSession = Depends(get_db),
):
    if workspace_id != ctx.workspace_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    inv = await db.get(WorkspaceInvitation, invitation_id)
    if not inv or inv.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Invitation not found")
    inv.revoked_at = datetime.now(timezone.utc)
    await db.commit()
