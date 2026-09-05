"""Сервисный слой: бизнес-логика поверх SQLAlchemy.

- генерация display_id (P001, P002, ...);
- безопасное построение фильтров/сортировки (без raw SQL);
- чтение/запись значений пользовательских полей.
"""
import uuid
from typing import Any, Optional

from sqlalchemy import Integer as _Integer, Text as _Text, asc, cast, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import CustomField, CustomFieldValue, Project, User
from .schemas import FilterCondition

# Поля проекта, по которым разрешена фильтрация/сортировка.
FILTERABLE_COLUMNS = {
    "display_id": Project.display_id,
    "title": Project.title,
    "client_legal_name": Project.client_legal_name,
    "manager_name": Project.manager_name,
    "stage": Project.stage,
    "deadline": Project.deadline,
    "risk_level": Project.risk_level,
    "payment_percent": Project.payment_percent,
    "currency": Project.currency,
    "advance_date": Project.advance_date,
    "final_payment_date": Project.final_payment_date,
    "next_action_date": Project.next_action_date,
    "archived_at": Project.archived_at,
}

# Операторы -> SQLAlchemy-выражения. Только белый список.
OPERATORS: dict[str, Any] = {
    "equals": lambda col, v: col == v,
    "not_equals": lambda col, v: col != v,
    "contains": lambda col, v: col.ilike(f"%{v}%"),
    "starts_with": lambda col, v: col.ilike(f"{v}%"),
    "empty": lambda col, _v: col.is_(None),
    "not_empty": lambda col, _v: col.isnot(None),
    "gt": lambda col, v: col > v,
    "gte": lambda col, v: col >= v,
    "lt": lambda col, v: col < v,
    "lte": lambda col, v: col <= v,
    "before": lambda col, v: col < v,
    "after": lambda col, v: col > v,
    "before_or_equal": lambda col, v: col <= v,
    "after_or_equal": lambda col, v: col >= v,
}

# Числовые строковые поля проекта: "80%" -> 80 при сравнении.
_NUMERIC_TEXT_FIELDS = {"payment_percent"}


def _numeric_text_col(col):
    """Превращает '80%' в число 80 для сравнений."""
    cleaned = func.replace(func.replace(col, "%", ""), " ", "")
    return cast(cleaned, _Integer)


async def next_display_id(session: AsyncSession, workspace_id: uuid.UUID) -> str:
    """Генерирует следующий display_id: P001, P002, ... (спец. §4)."""
    count = await session.scalar(
        select(func.count(Project.id)).where(Project.workspace_id == workspace_id)
    )
    return f"P{count + 1:03d}"


def apply_filters(stmt, filters: list[FilterCondition], custom_fields: dict[str, CustomField]):
    """Применяет валидированные фильтры к SELECT.

    Системные поля — через колонки модели; пользовательские поля — через
    custom_field_values (подзапрос). Неизвестное поле/оператор → игнорируется.
    """
    for cond in filters:
        col = FILTERABLE_COLUMNS.get(cond.field)
        if col is not None:
            op = OPERATORS.get(cond.operator)
            if op is None:
                continue
            if cond.field in _NUMERIC_TEXT_FIELDS and cond.operator not in ("empty", "not_empty"):
                col = _numeric_text_col(col)
                try:
                    cond.value = int(str(cond.value).replace("%", "").strip())
                except (TypeError, ValueError):
                    continue
            stmt = stmt.where(op(col, cond.value))
            continue

        # Пользовательское поле: фильтр по значению в custom_field_values.
        cf = custom_fields.get(cond.field)
        if cf is None:
            continue
        op = OPERATORS.get(cond.operator)
        if op is None:
            continue
        col = _custom_value_text_col()
        if cf.field_type in ("NUMBER", "PERCENT", "CURRENCY"):
            col = cast(col, _Integer)
            try:
                cond.value = int(cond.value)
            except (TypeError, ValueError):
                continue
        elif cf.field_type == "DATE":
            from sqlalchemy import Date as _Date

            col = cast(col, _Date)
        elif isinstance(cond.value, (int, float)):
            cond.value = str(cond.value)
        subq = (
            select(CustomFieldValue.entity_id)
            .where(
                CustomFieldValue.custom_field_id == cf.id,
                op(col, cond.value),
            )
            .scalar_subquery()
        )
        stmt = stmt.where(Project.id.in_(subq))
    return stmt


def _custom_value_text_col():
    """JSON-скаляр -> текст без кавычек: jsonb_build_object('v', value) ->> 'v'."""
    return func.jsonb_build_object("v", CustomFieldValue.value).op("->>")("v")


def apply_sorting(stmt, sort_by: Optional[str], sort_dir: str):
    col = FILTERABLE_COLUMNS.get(sort_by) if sort_by else Project.deadline
    if col is None:
        col = Project.deadline
    direction = desc if str(sort_dir).lower() == "desc" else asc
    return stmt.order_by(direction(col))


def apply_multi_sorting(stmt, sorting: list[dict]) -> None:
    """Мульти-сортировка (спец. 2.md §16): несколько уровней.

    sorting: [{"field": "deadline", "direction": "asc"}, ...]
    """
    order = []
    for item in sorting:
        field = item.get("field") or "deadline"
        direction = "desc" if str(item.get("direction", "asc")).lower() == "desc" else "asc"
        col = FILTERABLE_COLUMNS.get(field)
        if col is None:
            col = Project.deadline
        order.append(desc(col) if direction == "desc" else asc(col))
    return stmt.order_by(*order)


async def get_custom_fields_map(
    session: AsyncSession, workspace_id: uuid.UUID, entity_type: str = "PROJECT"
) -> dict[str, CustomField]:
    rows = (
        await session.execute(
            select(CustomField).where(
                CustomField.workspace_id == workspace_id,
                CustomField.entity_type == entity_type,
                CustomField.is_active.is_(True),
            )
        )
    ).scalars().all()
    return {cf.slug: cf for cf in rows}


async def load_custom_values(
    session: AsyncSession, workspace_id: uuid.UUID, entity: Any
) -> dict[str, Any]:
    """Возвращает map slug -> значение для сущности (Project или ProjectItem)."""
    entity_type = "PROJECT" if isinstance(entity, Project) else "PROJECT_ITEM"
    fields = await get_custom_fields_map(session, workspace_id, entity_type)
    if not fields:
        return {}
    rows = (
        await session.execute(
            select(CustomFieldValue).where(CustomFieldValue.entity_id == entity.id)
        )
    ).scalars().all()
    id_to_slug = {cf.id: slug for slug, cf in fields.items()}
    result: dict[str, Any] = {}
    for row in rows:
        slug = id_to_slug.get(row.custom_field_id)
        if slug:
            result[slug] = row.value
    # FORMULA-поля вычисляются безопасным DSL (7.md §24-25, §51),
    # а не через eval. Значения сохраняются только как конфигурация формулы.
    from .formula_engine import FormulaError, evaluate
    context = {
        key: getattr(entity, key, None)
        for key in (
            "deadline", "quantity", "unit_price", "cost", "amount", "price",
            "payment_percent", "advance_date", "final_payment_date",
            "next_action_date", "signal_shipping_date", "created_at", "updated_at",
        )
    }
    for slug, cf in fields.items():
        if cf.field_type == "FORMULA" and cf.formula:
            try:
                result[slug] = evaluate(cf.formula, context)
            except FormulaError:
                result[slug] = None
    return result


async def save_custom_values(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    entity_id: uuid.UUID,
    values: dict[str, Any],
    entity_type: str = "PROJECT",
) -> None:
    """Сохраняет значения пользовательских полей сущности (Project или Item)."""
    fields = await get_custom_fields_map(session, workspace_id, entity_type)
    slug_to_id = {slug: cf.id for slug, cf in fields.items()}
    for slug, value in values.items():
        cf_id = slug_to_id.get(slug)
        if cf_id is None:
            continue  # неизвестное поле — игнорируем
        existing = await session.scalar(
            select(CustomFieldValue).where(
                CustomFieldValue.custom_field_id == cf_id,
                CustomFieldValue.entity_id == entity_id,
            )
        )
        if existing is None:
            session.add(
                CustomFieldValue(
                    custom_field_id=cf_id,
                    entity_id=entity_id,
                    value=value,
                )
            )
        else:
            existing.value = value


# ---------------------------------------------------------------------------
# 3.md §14: NextActionService — оперативный слой «следующее действие».
# Позже сюда подключится rule engine / AI. Сейчас — детерминированные правила.
# ---------------------------------------------------------------------------
class NextActionService:
    """Предлагает следующее действие проекта на основе состояния позиций.

    Правила (пример из спец.):
    - signal_status = SENT и signal_feedback пусто → «Получить ОС по сигналу»
    - batch_status = IN_PRODUCTION и feedback пусто → «Получить ОС по тиражу»
    - mockup_status = REVISION → «Согласовать правки макета»
    """

    SENT_VALUES = {"Sent", "Отгружен", "SENT", "В производстве"}

    @classmethod
    def suggest(cls, items, next_action: Optional[str] = None) -> Optional[str]:
        # 1) сигнал отправлен, ОС не получено
        for it in items:
            st = (it.signal_status or "").strip().lower()
            fb = (it.signal_feedback or "").strip().lower()
            if st and any(k in st for k in ("отгружен", "производств", "согласован")) and (
                "ожидается" in fb or not fb
            ) and "согласовано" not in fb:
                return "Получить ОС по сигналу"
        # 2) макет на правках
        for it in items:
            ms = (it.mockup_status or "").strip().lower()
            if "правк" in ms:
                return "Согласовать правки макета"
        # 3) тираж в производстве — ждём ОС
        for it in items:
            bs = (it.batch_status or "").strip().lower()
            fb = (it.batch_feedback or "").strip().lower()
            if bs and "производств" in bs and not fb:
                return "Получить ОС по тиражу"
        return next_action or None


# ---------------------------------------------------------------------------
# 3.md §22: Project Health — детерминированный rule engine (расширяемый).
# ---------------------------------------------------------------------------
# Порядок приоритета: critical > at_risk > attention > healthy.
HEALTH_RULES: list[tuple[str, str]] = [
    ("critical", "risk_level == Критический"),
    ("at_risk", "deadline просрочен"),
    ("at_risk", "есть сигнал без ОС"),
    ("attention", "оплата < 100%"),
]


async def compute_project_health(
    session: AsyncSession,
    project: Project,
    items: list[Any],
    open_tasks_count: int = 0,
) -> tuple[str, list[str]]:
    """Возвращает (health, reasons). Источник истины — данные Project/Items."""
    from datetime import date

    reasons: list[str] = []
    health = "healthy"

    risk = (project.risk_level or "").lower()
    if "критич" in risk:
        return "critical", ["Риск: критический"]
    if "высок" in risk:
        health = "at_risk"
        reasons.append("Риск: высокий")

    today = date.today()
    if project.deadline and project.deadline < today:
        if health != "at_risk":
            health = "at_risk"
        reasons.append("Дедлайн просрочен")
    elif project.deadline and project.deadline <= today:
        reasons.append("Дедлайн сегодня")

    # сигнал без ОС
    for it in items:
        if it.signal_status and (it.signal_feedback or "").strip() == "":
            if health != "at_risk":
                health = "at_risk"
            reasons.append(f"Ожидается ОС по сигналу: {it.name}")
            break

    if open_tasks_count > 3:
        if health == "healthy":
            health = "attention"
        reasons.append(f"Открытых задач: {open_tasks_count}")

    pay = (project.payment_percent or "").replace("%", "").strip()
    if pay and pay != "100":
        if health == "healthy":
            health = "attention"
        reasons.append(f"Оплата {pay}%")

    return health, reasons


# ---------------------------------------------------------------------------
# 3.md §9: Production Timeline — вычисляется по данным позиции, не хранится.
# ---------------------------------------------------------------------------
def production_timeline(item) -> list[dict]:
    """Возвращает стадии: [{code, label, status}] (done|active|pending|na)."""
    mockup = (item.mockup_status or "").strip().lower()
    signal = (item.signal_status or "").strip().lower()
    batch = (item.batch_status or "").strip().lower()
    s_fb = (item.signal_feedback or "").strip().lower()
    b_fb = (item.batch_feedback or "").strip().lower()

    def stage_status(done_words, active_words, na_condition=False):
        if na_condition:
            return "na"
        if any(w in done_words for w in ("сдан", "готов", "утвержд", "согласован", "отгружен", "принято")):
            return "done"
        if any(w in active_words for w in ("в работе", "правк", "производств", "согласован", "отправлен")):
            return "active"
        return "pending"

    stages = [
        {"code": "mockup", "label": "Тех. макет", "status": stage_status(mockup, mockup)},
        {"code": "signal", "label": "Сигнал", "status": stage_status(signal, signal)},
        {"code": "signal_fb", "label": "ОС по сигналу", "status": stage_status(s_fb, s_fb, na_condition="не нужен" in signal or not (item.signal_required and signal))},
        {"code": "batch", "label": "Тираж", "status": stage_status(batch, batch, na_condition=not item.signal_required and not signal)},
        {"code": "batch_fb", "label": "ОС по тиражу", "status": stage_status(b_fb, b_fb, na_condition=not batch)},
        {"code": "shipment", "label": "Отгрузка", "status": stage_status(batch, batch, na_condition=not batch)},
    ]
    return stages


# ---------------------------------------------------------------------------
# 3.md §19: Event generation — производные события из дат Project/Item.
# ---------------------------------------------------------------------------
EVENT_TYPE_LABELS = {
    "DEADLINE": "Дедлайн проекта",
    "MOCKUP": "Макет",
    "SIGNAL_SHIPMENT": "Отгрузка сигнала",
    "SIGNAL_FEEDBACK": "ОС по сигналу",
    "BATCH_READY": "Тираж готов",
    "BATCH_SHIPMENT": "Отгрузка тиража",
    "PAYMENT_ADVANCE": "Аванс",
    "PAYMENT_FINAL": "Доплата",
    "DELIVERY": "Доставка",
    "CUSTOM": "Событие",
}


def derive_events(project: Project, items: list[Any]) -> list[dict]:
    """Строит события из дат без дублирования (§19): источник — Project/Item."""
    events: list[dict] = []
    if project.deadline:
        events.append({"event_type": "DEADLINE", "event_date": project.deadline, "title": "Дедлайн проекта"})
    if project.advance_date:
        events.append({"event_type": "PAYMENT_ADVANCE", "event_date": project.advance_date, "title": "Аванс"})
    if project.final_payment_date:
        events.append({"event_type": "PAYMENT_FINAL", "event_date": project.final_payment_date, "title": "Доплата"})
    for it in items:
        if it.signal_shipping_date:
            events.append({"event_type": "SIGNAL_SHIPMENT", "event_date": it.signal_shipping_date, "project_item_id": it.id, "title": f"Отгрузка сигнала: {it.name}"})
    return events


from .models import Permission, Role, RolePermission, User, Workspace, WorkspaceMember, Team, TeamMember


class WorkspaceError(Exception):
    pass


def workspace_access_effective(workspace_id, user):
    """Placeholder stub to keep old imports working."""
    pass

async def resolve_user_name(
    session: AsyncSession, workspace_id: uuid.UUID, user_id: Optional[uuid.UUID]
) -> Optional[str]:
    """RBAC §39: display_name пользователя workspace по user_id (для manager_name/assignee_name)."""
    if user_id is None:
        return None
    user = await session.get(User, user_id)
    if user is None or user.workspace_id != workspace_id:
        return None
    return user.display_name or user.name or user.email


async def add_audit(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    user_name: str,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID,
    old_value: Optional[dict] = None,
    new_value: Optional[dict] = None,
) -> None:
    """Запись в единый Audit Log (3.md §20 — НЕ плодить вторую систему)."""
    from .models import AuditLog

    session.add(
        AuditLog(
            workspace_id=workspace_id,
            user_name=user_name or "Система",
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value,
        )
    )
