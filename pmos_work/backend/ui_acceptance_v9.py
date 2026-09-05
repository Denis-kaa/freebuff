"""Live acceptance for Team / Roles / Profile UI flows (Stage 9 frontend)."""
import asyncio
import uuid

import httpx
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Role, User, WorkspaceMember

BASE = "http://127.0.0.1:8010/api"
WS = "00000000-0000-0000-0000-000000000001"


async def main() -> None:
    async with httpx.AsyncClient(base_url=BASE, timeout=20) as c:
        suffix = uuid.uuid4().hex[:6]

        # 1. Create custom role (RolesView)
        r = await c.post(f"/workspaces/{WS}/roles", json={
            "name": f"Дизайн {suffix}", "code": f"DESIGN_{suffix}",
            "permissions": ["project.read", "task.read", "task.create", "production.read", "view.read"],
        })
        assert r.status_code == 201, r.text
        rid = r.json()["id"]
        print("1. create custom role:", r.json()["name"], r.json()["code"])

        # 2. Update role permissions (RolesView edit)
        r = await c.patch(f"/workspaces/{WS}/roles/{rid}", json={
            "permissions": ["project.read", "task.read", "production.read", "finance.read"],
        })
        assert r.status_code == 200, r.text
        assert "finance.read" in r.json()["permissions"], r.text
        print("2. update role permissions:", sorted(r.json()["permissions"]))

        # 3. Invite member (TeamView)
        email = f"ui_{suffix}@pm.local"
        r = await c.post(f"/workspaces/{WS}/members/invite", json={"email": email, "role_code": "MEMBER"})
        assert r.status_code == 201, r.text
        inv_id = r.json()["id"]
        print("3. invite member:", email)

        # 4. List invitations
        r = await c.get(f"/workspaces/{WS}/invitations")
        assert r.status_code == 200, r.text
        assert any(i["id"] == inv_id for i in r.json()), r.text
        print("4. list invitations: ok")

        # 5. Revoke invitation
        r = await c.delete(f"/workspaces/{WS}/invitations/{inv_id}")
        assert r.status_code == 204, r.text
        print("5. revoke invitation: ok")

        # 6. Profile update as real user
        async with SessionLocal() as db:
            u = (await db.execute(select(User).limit(1))).scalars().first()
            uid = str(u.id)
        h = {"X-User-Id": uid}
        r = await c.patch("/me", headers=h, json={"timezone": "Europe/Moscow", "language": "ru", "name": "Денис (обновлён)"})
        assert r.status_code == 200, r.text
        assert r.json()["timezone"] == "Europe/Moscow", r.text
        print("6. profile update (real user):", r.json()["name"], r.json()["timezone"])
        await c.patch("/me", headers=h, json={"name": "Денис", "timezone": "UTC"})

        # 7. Member role change (TeamView)
        async with SessionLocal() as db:
            role = (await db.execute(select(Role).where(Role.workspace_id.is_(None), Role.code == "VIEWER"))).scalars().first()
            user = User(
                workspace_id=uuid.UUID(WS), email=f"member_{suffix}@pm.local",
                display_name="Иван", role="VIEWER", is_active=True, timezone="UTC", language="ru",
            )
            db.add(user)
            await db.flush()
            db.add(WorkspaceMember(workspace_id=uuid.UUID(WS), user_id=user.id, role_id=role.id, status="ACTIVE"))
            await db.commit()
            mid = str(user.id)

        members = await c.get(f"/workspaces/{WS}/members")
        m = next(x for x in members.json() if x["user_id"] == mid)
        roles = await c.get(f"/workspaces/{WS}/roles")
        mgr = next(x for x in roles.json() if x["code"] == "MANAGER")
        r = await c.patch(f"/workspaces/{WS}/members/{m['id']}", json={"role_id": mgr["id"]})
        assert r.status_code == 200, r.text
        assert r.json()["role_code"] == "MANAGER", r.text
        print("7. change member role to MANAGER: ok")

        # 8. Viewer скрыт от менеджмента: проверяем permission map нового пользователя
        r = await c.get("/permissions", headers={"X-User-Id": mid})
        assert r.status_code == 200, r.text
        assert r.json()["permissions"].get("member.invite") is False, r.text
        assert r.json()["permissions"].get("project.read") is True, r.text
        print("8. new manager permission map (no member.invite): ok")

        print("\nUI acceptance (live): 8 checks passed")


if __name__ == "__main__":
    asyncio.run(main())
