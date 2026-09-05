"""Query Builder (7.md §1, §8-9, §36-37, §40, §48).

Универсальный движок запросов: один движок для Projects/Tasks/Finance/
Production/Calendar. Вход — безопасная JSON-структура (никакого raw SQL):

    {
      "operator": "AND",
      "conditions": [{"field": "stage", "operator": "equals", "value": "Тираж"}],
      "groups": [
        {"operator": "OR", "conditions": [
            {"field": "risk_level", "operator": "in", "value": ["Высокий", "Критический"]}]}
      ]
    }

Backend валидирует: поля — по белому списку для entity_type, операторы —
по белому списку типов, значения — типизируются (date, number, enum).
Фильтры по custom fields — через custom_field_values (JSONB, без новых колонок,
7.md §22). Date intelligence (7.md §10):
today|tomorrow|this_week|next_7_days|next_30_days|overdue|no_deadline.
"""

from datetime import date, timedelta
from typing import Any, Optional

from sqlalchemy import Boolean as _BoolSQL, Integer as _IntSQL, and_, or_, asc, cast, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import CustomField, CustomFieldValue, Project, ProjectItem, Task
from .schemas import FilterCondition, FilterGroup

# ---------------------------------------------------------------------------
# Whitelist: поля по entity_type (7.md §37 — никогда не верим пользовательскому вводу)
# ---------------------------------------------------------------------------
ENTITY_FIELDS: dict[str, dict[str, Any]] = {
    "projects": {
        "display_id": ("text", Project.display_id),
        "title": ("text", Project.title),
        "client_legal_name": ("text", Project.client_legal_name),
        "manager_name": ("text", Project.manager_name),
        "stage": ("text", Project.stage),
        "deadline": ("date", Project.deadline),
        "risk_level": ("text", Project.risk_level),
        "risk_reason": ("text", Project.risk_reason),
        "payment_percent": ("number", Project.payment_percent),
        "currency": ("text", Project.currency),
        "advance_date": ("date", Project.advance_date),
        "final_payment_date": ("date", Project.final_payment_date),
        "delivery_address": ("text", Project.delivery_address),
        "delivery_paid": ("text", Project.delivery_paid),
        "next_action": ("text", Project.next_action),
        "next_action_date": ("date", Project.next_action_date),
        "comment": ("text", Project.comment),
        "archived_at": ("date", Project.archived_at),
    },
    "tasks": {
        "title": ("text", Task.title),
        "description": ("text", Task.description),
        "status": ("enum", Task.status),
        "priority": ("enum", Task.priority),
        "assignee_name": ("text", Task.assignee_name),
        "due_date": ("date", Task.due_date),
        "project_id": ("text", Task.project_id),
    },
    "production": {
        "name": ("text", ProjectItem.name),
        "quantity": ("number", ProjectItem.quantity),
        "mockup_status": ("enum", ProjectItem.mockup_status),
        "signal_status": ("enum", ProjectItem.signal_status),
        "batch_status": ("enum", ProjectItem.batch_status),
        "factory": ("text", ProjectItem.factory),
        "signal_shipping_date": ("date", ProjectItem.signal_shipping_date),
        "signal_required": ("bool", ProjectItem.signal_required),
        "project_id": ("text", ProjectItem.project_id),
    },
}

TEXT_OPS = {"equals", "not_equals", "contains", "not_contains", "starts_with", "ends_with", "empty", "not_empty"}
NUMBER_OPS = {"equals", "not_equals", "gt", "gte", "lt", "lte", "empty", "not_empty"}
DATE_OPS = {
    "equals", "before", "after", "before_or_equal", "after_or_equal", "between",
    "today", "tomorrow", "this_week", "next_7_days", "next_30_days", "overdue", "no_deadline",
    "empty", "not_empty",
}
DATE_INTELLIGENCE = {"today", "tomorrow", "this_week", "next_7_days", "next_30_days", "overdue", "no_deadline"}


def _parse_date(v: Any) -> Optional[date]:
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        try:
            return date.fromisoformat(v.strip()[:10])
        except ValueError:
            return None
    return None


def _text_cond(col, op: str, value: Any):
    value = str(value or "")
    if op == "equals":
        return col == value
    if op == "not_equals":
        return col != value
    if op == "contains":
        return col.ilike(f"%{value}%")
    if op == "not_contains":
        return ~col.ilike(f"%{value}%")
    if op == "starts_with":
        return col.ilike(f"{value}%")
    if op == "ends_with":
        return col.ilike(f"%{value}")
    if op == "empty":
        return col.is_(None)
    if op == "not_empty":
        return col.isnot(None)
    return None


def _number_cond(col, op: str, value: Any):
    if op in ("empty", "no_deadline"):
        return col.is_(None)
    if op == "not_empty":
        return col.isnot(None)
    try:
        num = int(str(value).replace("%", "").strip())
    except (TypeError, ValueError):
        return None
    if op == "equals":
        return col == num
    if op == "not_equals":
        return col != num
    if op == "gt":
        return col > num
    if op == "gte":
        return col >= num
    if op == "lt":
        return col < num
    if op == "lte":
        return col <= num
    return None


def _bool_cond(col, op: str, value: Any):
    v = str(value or "").strip().lower() in ("true", "1", "да", "yes", "on")
    if op == "equals":
        return col.is_(v)
    if op == "not_equals":
        return col.isnot(v)
    return None


def _enum_cond(col, op: str, value: Any):
    if op == "empty":
        return col.is_(None)
    if op == "not_empty":
        return col.isnot(None)
    if op == "equals":
        return col == str(value)
    if op == "not_equals":
        return col != str(value)
    if op == "in":
        vals = value if isinstance(value, (list, tuple)) else [value]
        return col.in_([str(v) for v in vals])
    if op == "not_in":
        vals = value if isinstance(value, (list, tuple)) else [value]
        return col.not_in([str(v) for v in vals])
    return None


def _date_intelligence(col, op: str):
    today = date.today()
    if op == "today":
        return col == today
    if op == "tomorrow":
        return col == today + timedelta(days=1)
    if op == "this_week":
        start = today - timedelta(days=today.weekday())
        return col.between(start, start + timedelta(days=6))
    if op == "next_7_days":
        return col.between(today, today + timedelta(days=7))
    if op == "next_30_days":
        return col.between(today, today + timedelta(days=30))
    if op == "overdue":
        return col < today
    if op == "no_deadline":
        return col.is_(None)
    return None


def _date_cond(col, op: str, value: Any):
    if op in ("today", "tomorrow", "this_week", "next_7_days", "next_30_days", "overdue"):
        return _date_intelligence(col, op)
    if op == "no_deadline" or op == "empty":
        return col.is_(None)
    if op == "not_empty":
        return col.isnot(None)
    if op == "between":
        if isinstance(value, (list, tuple)) and len(value) == 2:
            d0, d1 = _parse_date(value[0]), _parse_date(value[1])
            if d0 and d1:
                return col.between(d0, d1)
        return None
    d = _parse_date(value)
    if d is None:
        return None
    if op == "equals":
        return col == d
    if op == "before":
        return col < d
    if op == "after":
        return col > d
    if op == "before_or_equal":
        return col <= d
    if op == "after_or_equal":
        return col >= d
    if op == "gt":
        return col > d
    if op == "gte":
        return col >= d
    if op == "lt":
        return col < d
    if op == "lte":
        return col <= d
    return None


def _custom_value_text_col():
    """JSONB-значение -> текст: jsonb_build_object('v', value) ->> 'v'."""
    return func.jsonb_build_object("v", CustomFieldValue.value).op("->>" )("v")


def _custom_date_cond(vcol, op: str, value: Any):
    """Дата в JSONB-тексте ('YYYY-MM-DD') — сравнение по ISO-строкам."""
    today = date.today()
    if op in DATE_INTELLIGENCE:
        if op == "today":
            return vcol == today.isoformat()
        if op == "tomorrow":
            return vcol == (today + timedelta(days=1)).isoformat()
        start = today - timedelta(days=today.weekday()) if op == "this_week" else today
        end = (start + timedelta(days=6)) if op == "this_week" else today + timedelta(days=7 if op == "next_7_days" else 30)
        if op in ("this_week", "next_7_days", "next_30_days"):
            return vcol.between(start.isoformat(), end.isoformat())
        if op == "overdue":
            return vcol < today.isoformat()
    if op == "no_deadline" or op == "empty":
        return vcol.is_(None)
    if op == "not_empty":
        return vcol.isnot(None)
    if op == "between" and isinstance(value, (list, tuple)) and len(value) == 2:
        d0, d1 = _parse_date(value[0]), _parse_date(value[1])
        if d0 and d1 and d1 >= d0:
            return vcol.between(d0.isoformat(), d1.isoformat())
        return None
    d = _parse_date(value)
    if d is None:
        return None
    iso = d.isoformat()
    if op == "equals":
        return vcol == iso
    if op == "before":
        return vcol < iso
    if op == "after":
        return vcol > iso
    if op == "before_or_equal":
        return vcol <= iso
    if op == "after_or_equal":
        return vcol >= iso
    if op == "gt":
        return vcol > iso
    if op == "gte":
        return vcol >= iso
    if op == "lt":
        return vcol < iso
    if op == "lte":
        return vcol <= iso
    return None


def _custom_field_condition(entity_id_col, cf: CustomField, op: str, value: Any):
    """Условие по пользовательскому полю: подзапрос по custom_field_values."""
    vcol = _custom_value_text_col()
    if cf.field_type in ("NUMBER", "PERCENT", "CURRENCY"):
        cond = _number_cond(cast(vcol, _IntSQL), op, value)
    elif cf.field_type == "DATE":
        cond = _custom_date_cond(vcol, op, value)
    elif cf.field_type == "BOOLEAN":
        cond = _bool_cond(cast(vcol, _BoolSQL), op, value)
    else:  # TEXT, SELECT, MULTI_SELECT, URL, LONG_TEXT
        cond = _enum_cond(vcol, op, value) if cf.field_type in ("SELECT", "MULTI_SELECT") else _text_cond(vcol, op, value)
    if cond is None:
        return None
    inner = select(CustomFieldValue.entity_id).where(
        CustomFieldValue.custom_field_id == cf.id,
        cond,
    )
    return entity_id_col.in_(inner)


def build_condition(
    cond: FilterCondition,
    fields: dict[str, Any],
    custom_fields: dict[str, CustomField],
    entity_id_col,
) -> Optional[Any]:
    """SQL-условие для одного FilterCondition. None — если невалидно (пропускаем)."""
    fdef = fields.get(cond.field)
    if fdef is not None:
        ftype, col = fdef
        if ftype == "text":
            if cond.operator in ("in", "not_in"):
                return _enum_cond(col, cond.operator, cond.value)
            return _text_cond(col, cond.operator, cond.value)
        if ftype == "enum":
            return _enum_cond(col, cond.operator, cond.value)
        if ftype == "number":
            if cond.field == "payment_percent":
                cleaned = func.replace(func.replace(col, "%", ""), " ", "")
                col = cast(cleaned, _IntSQL)
            return _number_cond(col, cond.operator, cond.value)
        if ftype == "bool":
            return _bool_cond(col, cond.operator, cond.value)
        if ftype == "date":
            return _date_cond(col, cond.operator, cond.value)
        return None
    cf = custom_fields.get(cond.field)
    if cf is None:
        return None
    return _custom_field_condition(entity_id_col, cf, cond.operator, cond.value)


def build_filter_tree(
    group: Optional[FilterGroup],
    fields: dict[str, Any],
    custom_fields: dict[str, CustomField],
    entity_id_col,
) -> Optional[Any]:
    """Рекурсивно строит SQL-выражение для дерева AND/OR (7.md §9)."""
    if group is None:
        return None
    clauses: list[Any] = []
    for cond in group.conditions or []:
        c = build_condition(cond, fields, custom_fields, entity_id_col)
        if c is not None:
            clauses.append(c)
    for sub in group.groups or []:
        c = build_filter_tree(sub, fields, custom_fields, entity_id_col)
        if c is not None:
            clauses.append(c)
    if not clauses:
        return None
    if group.operator.upper() == "OR":
        return or_(*clauses)
    return clauses[0] if len(clauses) == 1 else and_(*clauses)


def build_sorting(sorting: Optional[list[dict]], fields: dict[str, Any]) -> list:
    """Мульти-сортировка (7.md §16) с whitelist полей."""
    if not sorting:
        return []
    order = []
    for item in sorting:
        fdef = fields.get(item.get("field"))
        if fdef is None:
            continue
        col = fdef[1]
        direction = "desc" if str(item.get("direction", "asc")).lower() == "desc" else "asc"
        order.append(desc(col) if direction == "desc" else asc(col))
    return order


def apply_grouping(stmt, group_by: Optional[str], fields: dict[str, Any]):
    """Группировка (7.md §41): GROUP BY по выбранной колонке."""
    if not group_by:
        return stmt
    fdef = fields.get(group_by)
    if fdef is None:
        return stmt
    return stmt.group_by(fdef[1])


ENUM_OPS = TEXT_OPS | NUMBER_OPS | {"in", "not_in"}