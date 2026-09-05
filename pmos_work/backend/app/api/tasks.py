"""Роутер задач (3.md §10-12). Задачи привязаны к проекту, опционально — к позиции."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..automation_engine import create_event, execute_event
from ..database import get_db
from ..models import Project, ProjectItem, Task
from ..rbac import DEMO_WORKSPACE_ID, UserContext, check_workspace_access, require_permission
from ..schemas import TaskCreate, TaskRead, TaskUpdate
from ..services import add_audit, resolve_user_name

router = APIRouter(prefix="/projects", tags=["tasks"])


async def _project_or_404(
    session: AsyncSession, project_id: uuid.UUID, ctx: Optional[UserContext] = None
) -> Project:
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Проект не найден")
    if ctx is not None:
        check_workspace_access(ctx, project.workspace_id)
    return project


async def _task_or_404(
    session: AsyncSession, task_id: uuid.UUID, ctx: Optional[UserContext] = None
) -> Task:
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    if ctx is not None and task.project_id is not None:
        project = await session.get(Project, task.project_id)
        if project is not None:
            check_workspace_access(ctx, project.workspace_id)
    return task


@router.get("/{project_id}/tasks", response_model=list[TaskRead])
async def list_tasks(
    project_id: uuid.UUID,
    ctx: UserContext = Depends(require_permission("task.read")),
    db: AsyncSession = Depends(get_db),
):
    await _project_or_404(db, project_id, ctx)
    stmt = select(Task).where(Task.project_id == project_id).order_by(Task.due_date, Task.created_at)
    return (await db.execute(stmt)).scalars().all()


@router.post("/{project_id}/tasks", response_model=TaskRead, status_code=201)
async def create_task(
    project_id: uuid.UUID,
    payload: TaskCreate,
    ctx: UserContext = Depends(require_permission("task.create")),
    db: AsyncSession = Depends(get_db),
):
    await _project_or_404(db, project_id, ctx)
    if payload.project_item_id is not None:
        item = await db.get(ProjectItem, payload.project_item_id)
        if item is None or item.project_id != project_id:
            raise HTTPException(status_code=422, detail="Позиция не принадлежит проекту")
    data = payload.model_dump(exclude_unset=True)
    assignee_id = data.pop("assignee_id", None)
    if assignee_id is not None:
        # RBAC §39: assignee_name резолвится из пользователя workspace
        project_obj = await _project_or_404(db, project_id, ctx)
        resolved = await resolve_user_name(db, project_obj.workspace_id, assignee_id)
        data["assignee_name"] = resolved
    task = Task(
        project_id=project_id,
        title=data.pop("title"),
        description=data.pop("description", None),
        project_item_id=data.pop("project_item_id", None),
        status=data.pop("status", "TODO"),
        priority=data.pop("priority", None),
        due_date=data.pop("due_date", None),
        assignee_name=data.pop("assignee_name", None),
        assignee_id=assignee_id,
    )
    db.add(task)
    await add_audit(db, DEMO_WORKSPACE_ID, "Менеджер", "create", "task", task.id,
                    new_value={"title": payload.title})
    await db.commit()
    await db.refresh(task)
    event = await create_event(db, DEMO_WORKSPACE_ID, "task.created", "task", task.id, {"title": task.title, "project_id": str(project_id)})
    await execute_event(db, event)
    await db.commit()
    return task


@router.get("/tasks", include_in_schema=False)
async def list_all_tasks(
    status: Optional[str] = None,
    assignee_name: Optional[str] = None,
    ctx: UserContext = Depends(require_permission("task.read")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Task).join(Project, Project.id == Task.project_id)
    stmt = stmt.where(Project.workspace_id == ctx.workspace_id)
    if status:
        stmt = stmt.where(Task.status == status)
    if assignee_name:
        stmt = stmt.where(Task.assignee_name == assignee_name)
    return (await db.execute(stmt.order_by(Task.due_date))).scalars().all()


@router.patch("/{project_id}/tasks/{task_id}", response_model=TaskRead)
async def update_task(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    payload: TaskUpdate,
    ctx: UserContext = Depends(require_permission("task.update")),
    db: AsyncSession = Depends(get_db),
):
    await _project_or_404(db, project_id, ctx)
    task = await _task_or_404(db, task_id, ctx)
    if task.project_id != project_id:
        raise HTTPException(status_code=404, detail="Задача не принадлежит проекту")
    changes = payload.model_dump(exclude_unset=True)
    assignee_id = changes.pop("assignee_id", None)
    if assignee_id is not None:
        project_obj = await _project_or_404(db, project_id, ctx)
        resolved = await resolve_user_name(db, project_obj.workspace_id, assignee_id)
        changes["assignee_name"] = resolved
        task.assignee_id = assignee_id
    for field, value in changes.items():
        setattr(task, field, value)
    if payload.status == "DONE":
        task.completed_at = datetime.now(timezone.utc)
    elif task.completed_at and payload.status and payload.status != "DONE":
        task.completed_at = None
    await db.commit()
    await db.refresh(task)
    event_type = "task.completed" if payload.status == "DONE" else "task.updated"
    event = await create_event(db, DEMO_WORKSPACE_ID, event_type, "task", task.id, {"changes": payload.model_dump(exclude_unset=True)})
    await execute_event(db, event)
    await db.commit()
    return task


@router.delete("/{project_id}/tasks/{task_id}", status_code=204)
async def delete_task(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    ctx: UserContext = Depends(require_permission("task.delete")),
    db: AsyncSession = Depends(get_db),
):
    await _project_or_404(db, project_id, ctx)
    task = await _task_or_404(db, task_id, ctx)
    await db.delete(task)
    await db.commit()