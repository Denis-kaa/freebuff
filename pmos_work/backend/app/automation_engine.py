"""Stage 8 deterministic event and automation engine."""
import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Automation, AutomationRun, DomainEvent, Notification, Project, ProjectTag, Task
from .services import add_audit

MAX_EXECUTION_DEPTH = 8
ALLOWED_PROJECT_FIELDS = {"stage", "risk_level", "risk_reason", "payment_percent", "next_action", "next_action_date", "comment"}


def _as_date(value: Any) -> date | None:
    if isinstance(value, date): return value
    if isinstance(value, str):
        try: return date.fromisoformat(value[:10])
        except ValueError: return None
    return None


def project_risk(project: Project, today: date | None = None) -> tuple[str, str]:
    today = today or date.today(); status = (project.stage or "").lower()
    try: payment = int((project.payment_percent or "0").replace("%", "") or 0)
    except ValueError: payment = 0
    days = (project.deadline - today).days if project.deadline else None
    if days is not None and days < 0 and "заверш" not in status and "complete" not in status: return "CRITICAL", f"Дедлайн просрочен на {abs(days)} дн., проект не завершён."
    if days is not None and days <= 2 and "отгруж" not in status and "shipped" not in status: return "HIGH", f"До дедлайна {max(days, 0)} дн., тираж ещё не отгружен."
    if payment < 50 and any(word in status for word in ("производ", "production", "печать")): return "HIGH", f"Оплата {payment}%, производство уже начато."
    if days is not None and days <= 7: return "MEDIUM", f"До дедлайна {max(days, 0)} дн."
    if payment < 100: return "LOW", f"Оплата {payment}%."
    return "NONE", "Активных детерминированных рисков не обнаружено."


async def create_event(db: AsyncSession, workspace_id: uuid.UUID, event_type: str, entity_type: str, entity_id: uuid.UUID | None = None, payload: dict[str, Any] | None = None, actor_id: uuid.UUID | None = None, deduplication_key: str | None = None, chain_id: uuid.UUID | None = None, execution_depth: int = 0) -> DomainEvent:
    if deduplication_key:
        existing = await db.scalar(select(DomainEvent).where(DomainEvent.deduplication_key == deduplication_key))
        if existing: return existing
    event = DomainEvent(workspace_id=workspace_id, type=event_type, entity_type=entity_type, entity_id=entity_id, actor_id=actor_id, payload=payload or {}, chain_id=chain_id or uuid.uuid4(), execution_depth=execution_depth, deduplication_key=deduplication_key)
    db.add(event); await db.flush(); return event


def _compare(actual: Any, operator: str, expected: Any) -> bool:
    if isinstance(actual, (date, datetime)): actual = actual.isoformat()
    if operator == "equals": return str(actual) == str(expected)
    if operator == "not_equals": return str(actual) != str(expected)
    if operator == "contains": return str(expected).lower() in str(actual or "").lower()
    if operator == "empty": return actual is None or actual == ""
    if operator == "not_empty": return actual is not None and actual != ""
    if operator in {"lt", "lte", "gt", "gte"}:
        try: left, right = float(str(actual).replace("%", "")), float(str(expected).replace("%", ""))
        except (TypeError, ValueError): left, right = _as_date(actual), _as_date(expected)
        if left is None or right is None: return False
        return {"lt": left < right, "lte": left <= right, "gt": left > right, "gte": left >= right}[operator]
    return False


async def _condition_matches(project: Project | None, conditions: dict[str, Any] | list[Any]) -> bool:
    if not conditions: return True
    if project is None: return False
    if isinstance(conditions, list): group = {"operator": "AND", "conditions": conditions}
    else: group = conditions
    results = [_compare(getattr(project, c.get("field"), None), c.get("operator", "equals"), c.get("value")) for c in group.get("conditions", [])]
    results += [await _condition_matches(project, child) for child in group.get("groups", [])]
    return all(results) if str(group.get("operator", "AND")).upper() == "AND" else any(results)


async def execute_event(db: AsyncSession, event: DomainEvent) -> list[AutomationRun]:
    if event.execution_depth >= MAX_EXECUTION_DEPTH: return []
    automations = (await db.execute(select(Automation).where(Automation.workspace_id == event.workspace_id, Automation.enabled.is_(True), Automation.trigger_type == event.type))).scalars().all()
    project = await db.get(Project, event.entity_id) if event.entity_type == "project" and event.entity_id else None
    runs = []
    for automation in automations:
        if not await _condition_matches(project, automation.conditions or {}): continue
        idem = f"{automation.id}:{event.id}"
        existing = await db.scalar(select(AutomationRun).where(AutomationRun.idempotency_key == idem))
        if existing: runs.append(existing); continue
        run = AutomationRun(automation_id=automation.id, event_id=event.id, status="RUNNING", idempotency_key=idem); db.add(run); await db.flush()
        try:
            result = {"actions": 0, "notifications": 0, "tasks": 0, "updates": 0}
            for action in automation.actions or []:
                kind = action.get("type") or action.get("action")
                if kind == "create_task":
                    if project is None: raise ValueError("Project is required for create_task")
                    title = action.get("title", "Проверить проект"); duplicate = await db.scalar(select(Task).where(Task.project_id == project.id, Task.title == title, Task.status != "DONE"))
                    if duplicate is None: db.add(Task(project_id=project.id, title=title, due_date=_as_date(action.get("due_date")) or date.today(), status="TODO")); result["tasks"] += 1
                elif kind == "notification":
                    key = f"automation:{automation.id}:{event.id}:{result['notifications']}"
                    if await db.scalar(select(Notification).where(Notification.deduplication_key == key)) is None:
                        db.add(Notification(workspace_id=event.workspace_id, type=action.get("priority", "INFO"), title=action.get("title", automation.name), message=action.get("message", "Автоматизация сработала"), entity_type=event.entity_type, entity_id=event.entity_id, deduplication_key=key)); result["notifications"] += 1
                elif kind in {"update_field", "update_status", "add_tag"}:
                    if project is None: raise ValueError("Project is required for project update")
                    if kind == "add_tag":
                        tag = str(action.get("tag") or action.get("value") or "").strip()
                        if not tag or len(tag) > 80: raise ValueError("Tag must contain 1-80 characters")
                        existing_tag = await db.scalar(select(ProjectTag).where(ProjectTag.project_id == project.id, ProjectTag.tag == tag))
                        if existing_tag is None: db.add(ProjectTag(workspace_id=event.workspace_id, project_id=project.id, tag=tag)); result["updates"] += 1
                        result["actions"] += 1
                        continue
                    field = "stage" if kind == "update_status" else action.get("field")
                    if field not in ALLOWED_PROJECT_FIELDS: raise ValueError(f"Field is not automation-writable: {field}")
                    setattr(project, field, action.get("value")); result["updates"] += 1
                else: raise ValueError(f"Unsupported automation action: {kind}")
                result["actions"] += 1
            run.status, run.result = "SUCCESS", result
        except Exception as exc: run.status, run.error = "FAILED", str(exc)
        run.completed_at = datetime.now(timezone.utc)
        await add_audit(db, event.workspace_id, "Система", "automation_run", "automation", automation.id, new_value={"event_id": str(event.id), "status": run.status, "result": run.result, "error": run.error})
        runs.append(run)
    await db.flush(); return runs
