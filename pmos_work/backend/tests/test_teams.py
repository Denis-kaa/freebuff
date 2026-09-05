import uuid

import pytest


DEMO_WS = "00000000-0000-0000-0000-000000000001"


@pytest.mark.anyio
async def test_team_crud_and_member_assignment(client):
    workspace = await client.post("/api/workspaces", json={"name": "Teams test workspace"})
    assert workspace.status_code == 201, workspace.text
    workspace_id = workspace.json()["id"]
    headers = {"X-Workspace-Id": workspace_id}

    members_response = await client.get(
        f"/api/workspaces/{workspace_id}/members", headers=headers
    )
    assert members_response.status_code == 200, members_response.text
    members = members_response.json()
    assert len(members) == 1

    created = await client.post(
        f"/api/workspaces/{workspace_id}/teams",
        headers=headers,
        json={"name": "Production", "description": "Factory team"},
    )
    assert created.status_code == 201, created.text
    team = created.json()
    assert team["member_ids"] == []

    member_id = members[0]["id"]
    added = await client.post(
        f"/api/workspaces/{workspace_id}/teams/{team['id']}/members",
        headers=headers,
        json={"member_id": member_id},
    )
    assert added.status_code == 200, added.text
    assert members[0]["user_id"] in added.json()["member_ids"]

    listed = await client.get(f"/api/workspaces/{workspace_id}/teams", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["name"] == "Production"

    updated = await client.patch(
        f"/api/workspaces/{workspace_id}/teams/{team['id']}",
        headers=headers,
        json={"name": "Production Updated"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Production Updated"

    removed = await client.delete(
        f"/api/workspaces/{workspace_id}/teams/{team['id']}/members/{member_id}",
        headers=headers,
    )
    assert removed.status_code == 200
    assert removed.json()["member_ids"] == []

    deleted = await client.delete(
        f"/api/workspaces/{workspace_id}/teams/{team['id']}", headers=headers
    )
    assert deleted.status_code == 204


@pytest.mark.anyio
async def test_team_workspace_isolation(client):
    other_workspace = str(uuid.uuid4())

    response = await client.get(f"/api/workspaces/{other_workspace}/teams")
    assert response.status_code == 404

    response = await client.post(
        f"/api/workspaces/{other_workspace}/teams",
        json={"name": "Should not exist"},
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_duplicate_team_name_is_rejected(client):
    first = await client.post(
        f"/api/workspaces/{DEMO_WS}/teams", json={"name": "Design"}
    )
    assert first.status_code == 201, first.text

    second = await client.post(
        f"/api/workspaces/{DEMO_WS}/teams", json={"name": "Design"}
    )
    assert second.status_code == 409
