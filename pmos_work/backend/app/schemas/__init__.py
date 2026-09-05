"""Pydantic-схемы: типизированные контракты API (спец. §26)."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------
class ProjectBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    client_legal_name: Optional[str] = None
    manager_name: Optional[str] = None
    stage: Optional[str] = None
    deadline: Optional[date] = None
    risk_level: Optional[str] = None
    risk_reason: Optional[str] = None
    payment_percent: Optional[str] = None
    currency: Optional[str] = "RUB"
    advance_date: Optional[date] = None
    final_payment_date: Optional[date] = None
    delivery_address: Optional[str] = None
    delivery_paid: Optional[str] = None
    next_action: Optional[str] = None
    next_action_date: Optional[date] = None
    comment: Optional[str] = None


class ProjectCreate(ProjectBase):
    """Создание проекта. display_id генерирует сервер (спец. §4)."""

    manager_id: Optional[uuid.UUID] = None  # RBAC §39: менеджер — пользователь workspace


class ProjectUpdate(BaseModel):
    """Частичное обновление. Поля без значения не меняются."""

    manager_id: Optional[uuid.UUID] = None  # RBAC §39
    title: Optional[str] = None
    client_legal_name: Optional[str] = None
    manager_name: Optional[str] = None
    stage: Optional[str] = None
    deadline: Optional[date] = None
    risk_level: Optional[str] = None
    risk_reason: Optional[str] = None
    payment_percent: Optional[str] = None
    currency: Optional[str] = None
    advance_date: Optional[date] = None
    final_payment_date: Optional[date] = None
    delivery_address: Optional[str] = None
    delivery_paid: Optional[str] = None
    next_action: Optional[str] = None
    next_action_date: Optional[date] = None
    comment: Optional[str] = None
    # optimistic locking (3.md §25): клиент передаёт ожидаемую версию
    version: Optional[int] = None


class ProjectRead(ProjectBase):
    id: uuid.UUID
    display_id: str
    manager_id: Optional[uuid.UUID] = None  # RBAC §39
    archived_at: Optional[datetime] = None
    version: int = 1
    created_at: datetime
    updated_at: datetime
    custom_values: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class ProjectListResponse(BaseModel):
    items: list[ProjectRead]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Project Items
# ---------------------------------------------------------------------------
class ProjectItemBase(BaseModel):
    name: str
    quantity: Optional[int] = None
    tech_specs: Optional[str] = None
    mockup_status: Optional[str] = None
    signal_required: Optional[bool] = False
    signal_status: Optional[str] = None
    signal_shipping_date: Optional[date] = None
    signal_feedback: Optional[str] = None
    batch_status: Optional[str] = None
    batch_feedback: Optional[str] = None
    factory: Optional[str] = None


class ProjectItemRead(ProjectItemBase):
    id: uuid.UUID
    project_id: uuid.UUID
    version: int = 1
    created_at: datetime
    updated_at: datetime
    custom_values: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class ProjectItemCreate(ProjectItemBase):
    project_id: uuid.UUID


class ProjectItemUpdate(BaseModel):
    name: Optional[str] = None
    quantity: Optional[int] = None
    tech_specs: Optional[str] = None
    mockup_status: Optional[str] = None
    signal_required: Optional[bool] = None
    signal_status: Optional[str] = None
    signal_shipping_date: Optional[date] = None
    signal_feedback: Optional[str] = None
    batch_status: Optional[str] = None
    batch_feedback: Optional[str] = None
    factory: Optional[str] = None
    version: Optional[int] = None  # optimistic locking


class ProjectItemProductionUpdate(BaseModel):
    """Обновление производственных статусов позиции (3.md §23)."""

    mockup_status: Optional[str] = None
    signal_status: Optional[str] = None
    signal_shipping_date: Optional[date] = None
    signal_feedback: Optional[str] = None
    batch_status: Optional[str] = None
    batch_feedback: Optional[str] = None
    factory: Optional[str] = None
    version: Optional[int] = None


# ---------------------------------------------------------------------------
# Custom Fields
# ---------------------------------------------------------------------------
class CustomFieldBase(BaseModel):
    entity_type: str = "PROJECT"
    name: str = Field(min_length=1, max_length=200)
    field_type: str  # TEXT|LONG_TEXT|NUMBER|DATE|DATETIME|BOOLEAN|SELECT|MULTI_SELECT|PERCENT|CURRENCY|URL|FORMULA
    description: Optional[str] = None
    required: bool = False
    default_value: Optional[str] = None
    options: Optional[list[str]] = None
    formula: Optional[str] = None
    position: int = 0
    is_active: bool = True


class CustomFieldCreate(CustomFieldBase):
    pass


class CustomFieldUpdate(BaseModel):
    name: Optional[str] = None
    field_type: Optional[str] = None
    description: Optional[str] = None
    required: Optional[bool] = None
    default_value: Optional[str] = None
    options: Optional[list[str]] = None
    formula: Optional[str] = None
    position: Optional[int] = None
    is_active: Optional[bool] = None


class CustomFieldRead(CustomFieldBase):
    id: uuid.UUID
    workspace_id: uuid.UUID
    slug: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomFieldValueUpdate(BaseModel):
    """Значения пользовательских полей сущности (map slug -> value)."""

    values: dict[str, Any]


# ---------------------------------------------------------------------------
# Filters / Bulk / Misc
# ---------------------------------------------------------------------------
class FilterCondition(BaseModel):
    """Структурированный фильтр (7.md §7-9, §36). Не raw SQL."""

    field: str
    operator: str
    value: Any = None


# ---------------------------------------------------------------------------
# Views (7.md §2, §47)
# ---------------------------------------------------------------------------
class ViewBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    entity_type: str = "projects"  # projects|tasks|production|finance
    view_type: str = "TABLE"  # TABLE|KANBAN|CALENDAR
    visibility: str = "workspace"  # private|workspace
    is_default: bool = False
    is_favorite: bool = False
    created_by: Optional[str] = None
    config: dict[str, Any] = Field(default_factory=dict)


class ViewCreate(ViewBase):
    pass


class ViewUpdate(BaseModel):
    name: Optional[str] = None
    entity_type: Optional[str] = None
    view_type: Optional[str] = None
    visibility: Optional[str] = None
    is_default: Optional[bool] = None
    is_favorite: Optional[bool] = None
    config: Optional[dict[str, Any]] = None


class ViewRead(ViewBase):
    id: uuid.UUID
    workspace_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FilterGroup(BaseModel):
    """Вложенная группа фильтров: AND/OR (7.md §8-9).

    conditions — листовые условия; groups — вложенные группы.
    """

    operator: str = "AND"  # AND|OR
    conditions: Optional[list[FilterCondition]] = None
    groups: Optional[list["FilterGroup"]] = None

    def __iter__(self):
        return iter((self.conditions or []) + (self.groups or []))


FilterGroup.model_rebuild()


class ViewQueryRequest(BaseModel):
    """Запрос к Query Builder (7.md §36, §48).

    Поля структуры валидируются на сервере (без raw SQL).
    """

    filters: Optional[FilterGroup] = None  # дерево AND/OR
    sorting: Optional[list[dict[str, Any]]] = None  # [{"field":.., "direction":..}]
    columns: Optional[list[str]] = None
    group_by: Optional[str] = None
    search: Optional[str] = None
    page: int = 1
    page_size: int = 50
    include_archived: bool = False


# ---------------------------------------------------------------------------
# Dashboards (4.md §16, §23)
# ---------------------------------------------------------------------------
class DashboardWidgetBase(BaseModel):
    widget_type: str
    title: str
    config: Optional[dict[str, Any]] = None  # настройки виджета (4.md §15)
    layout: Optional[dict[str, Any]] = None  # {"x":0,"y":0,"w":6,"h":4} (4.md §16)
    is_hidden: bool = False
    # legacy (этап 1): configuration/position/width/height/is_visible — читаем только
    configuration: Optional[dict[str, Any]] = None
    position: Optional[str] = None
    width: int = 1
    height: int = 1
    is_visible: bool = True


class DashboardWidgetCreate(BaseModel):
    widget_type: str
    title: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    layout: Optional[dict[str, Any]] = None


class DashboardWidgetUpdate(BaseModel):
    title: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    layout: Optional[dict[str, Any]] = None
    is_hidden: Optional[bool] = None


class DashboardWidgetRead(BaseModel):
    id: uuid.UUID
    dashboard_id: uuid.UUID
    widget_type: str
    title: str
    config: Optional[dict[str, Any]] = None
    layout: Optional[dict[str, Any]] = None
    is_hidden: bool = False
    position: Optional[str] = None
    width: int = 1
    height: int = 1
    is_visible: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DashboardCreate(BaseModel):
    name: str
    is_default: bool = False
    template: Optional[str] = None  # empty|manager|production|finance|director (4.md §35-38)


class DashboardUpdate(BaseModel):
    """Обновление дашборда. version — optimistic locking (4.md §44)."""

    name: Optional[str] = None
    is_default: Optional[bool] = None
    version: Optional[int] = None


class DashboardRead(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    is_default: bool = False
    version: int = 1
    layout: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    widgets: list[DashboardWidgetRead] = []

    model_config = ConfigDict(from_attributes=True)


class DashboardDuplicateRead(BaseModel):
    id: uuid.UUID
    name: str


# ---------------------------------------------------------------------------
# Widget Registry (4.md §2, §39)
# ---------------------------------------------------------------------------
class WidgetTypeInfo(BaseModel):
    type: str
    name: str
    description: str
    icon: str
    category: str  # planning|projects|finance|production|overview
    default_size: dict[str, int]  # {"w": 6, "h": 4}


class DashboardTemplateInfo(BaseModel):
    key: str
    name: str
    widgets: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Widget Data API (4.md §22, §24) — каждый виджет получает ровно свои данные
# ---------------------------------------------------------------------------
class CalendarEventItem(BaseModel):
    event_date: date
    event_type: str  # DEADLINE|TASK|SIGNAL_SHIPMENT|PAYMENT_ADVANCE|PAYMENT_FINAL|DELIVERY|NEXT_ACTION
    title: str
    project_id: Optional[uuid.UUID] = None
    project_display_id: Optional[str] = None
    project_title: Optional[str] = None
    project_item_id: Optional[uuid.UUID] = None
    source: str = "derived"


class CalendarDay(BaseModel):
    date: date
    events: list[CalendarEventItem] = []


class CalendarData(BaseModel):
    from_: Optional[date] = None
    to: Optional[date] = None
    days: list[CalendarDay]


class TodayTaskItem(BaseModel):
    id: Optional[uuid.UUID] = None
    title: str
    project_id: Optional[uuid.UUID] = None
    project_display_id: Optional[str] = None
    project_title: Optional[str] = None
    due_date: Optional[date] = None
    assignee_name: Optional[str] = None
    priority: Optional[str] = None
    status: str = "TODO"


class TodayTasksData(BaseModel):
    overdue: list[TodayTaskItem]
    today: list[TodayTaskItem]
    next_actions: list[TodayTaskItem]


class DeadlineItem(BaseModel):
    id: uuid.UUID
    display_id: str
    title: str
    kind: str = "project"  # project|item
    # поле называется due_date, но в JSON сериализуется как "date" (alias) —
    # имя поля не должно совпадать с именем типа (PEP 649 / deferred annotations)
    due_date: Optional[date] = Field(None, alias="date")
    days_left: Optional[int] = None
    project_id: Optional[uuid.UUID] = None
    risk_level: Optional[str] = None


class DeadlinesData(BaseModel):
    period_days: int
    items: list[DeadlineItem]


class RiskItem(BaseModel):
    id: uuid.UUID
    display_id: str
    title: str
    risk_level: Optional[str] = None
    risk_reason: Optional[str] = None
    deadline: Optional[date] = None
    kind: str = "risk"  # risk|overdue|production
    reason: Optional[str] = None


class RisksData(BaseModel):
    items: list[RiskItem]


class ProductionCountItem(BaseModel):
    key: str
    label: str
    count: int
    status: str  # done|active|pending


class ProductionData(BaseModel):
    items: list[ProductionCountItem]
    total_items: int = 0


class FinanceItem(BaseModel):
    id: uuid.UUID
    display_id: str
    title: str
    payment_percent: Optional[str] = None
    currency: Optional[str] = None
    advance_date: Optional[date] = None
    final_payment_date: Optional[date] = None
    kind: str = "unpaid"  # unpaid|advance_due|final_due


class FinanceData(BaseModel):
    unpaid: list[FinanceItem]
    unpaid_count: int = 0
    advances_due: list[FinanceItem]
    finals_due: list[FinanceItem]
    currencies: dict[str, int] = {}


class ActivityData(BaseModel):
    # plain dicts из activity_data (сервис уже возвращает готовый JSON)
    items: list[dict]


class KpiData(BaseModel):
    metric: str
    label: str
    value: int



# ---------------------------------------------------------------------------
# Calendar & Events (5.md §2, §45)
# ---------------------------------------------------------------------------
class CalendarEventRead(BaseModel):
    """Unified Calendar Event (5.md §2). id детерминирован для системных событий."""

    id: str
    type: str  # PROJECT_DEADLINE|TASK_DEADLINE|PAYMENT_ADVANCE|...
    title: str
    description: Optional[str] = None
    start_at: datetime
    end_at: Optional[datetime] = None
    all_day: bool = True
    project_id: Optional[uuid.UUID] = None
    project_item_id: Optional[uuid.UUID] = None
    task_id: Optional[uuid.UUID] = None
    document_id: Optional[uuid.UUID] = None
    source_type: str  # project|payment|task|project_item|document|custom
    source_id: str
    status: Optional[str] = None
    priority: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CustomEventCreate(BaseModel):
    """Ручное событие (5.md §21-22). start_at — UTC ISO (5.md §38)."""

    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    event_type: str = "REMINDER"  # REMINDER|MEETING|CALL|OTHER|CUSTOM
    start_at: datetime
    end_at: Optional[datetime] = None
    all_day: bool = False
    project_id: Optional[uuid.UUID] = None
    project_item_id: Optional[uuid.UUID] = None
    task_id: Optional[uuid.UUID] = None
    recurrence_rule: Optional[str] = None  # RRULE (5.md §37, MVP: nullable)


class CustomEventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    event_type: Optional[str] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    all_day: Optional[bool] = None
    project_id: Optional[uuid.UUID] = None
    project_item_id: Optional[uuid.UUID] = None
    task_id: Optional[uuid.UUID] = None


class CalendarEventsResponse(BaseModel):
    items: list[CalendarEventRead]
    total: int
    from_: Optional[str] = None
    to: Optional[str] = None


class CalendarTodayRead(BaseModel):
    date: str
    overdue: list[CalendarEventRead] = []
    events: list[CalendarEventRead] = []
    tasks: list[CalendarEventRead] = []
    deadlines: list[CalendarEventRead] = []
    payments: list[CalendarEventRead] = []
    production: list[CalendarEventRead] = []
    documents: list[CalendarEventRead] = []
    custom: list[CalendarEventRead] = []
    next_actions: list[dict] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Filters / Bulk / Misc
# ---------------------------------------------------------------------------
class ProjectListQuery(BaseModel):
    search: Optional[str] = None
    filters: list[FilterCondition] = Field(default_factory=list)
    sort_by: Optional[str] = "deadline"
    sort_dir: str = "asc"
    page: int = 1
    page_size: int = 20
    include_archived: bool = False


class BulkUpdateRequest(BaseModel):
    ids: list[uuid.UUID]
    stage: Optional[str] = None
    manager_name: Optional[str] = None
    risk_level: Optional[str] = None


# ---------------------------------------------------------------------------
# Tasks (3.md §10-12)
# ---------------------------------------------------------------------------
class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    assignee_name: Optional[str] = None
    assignee_id: Optional[uuid.UUID] = None  # RBAC §39: исполнитель — пользователь workspace
    project_item_id: Optional[uuid.UUID] = None
    status: str = "TODO"  # TODO|IN_PROGRESS|DONE|CANCELLED
    priority: Optional[str] = None  # LOW|MEDIUM|HIGH|URGENT
    due_date: Optional[date] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_name: Optional[str] = None
    assignee_id: Optional[uuid.UUID] = None
    project_item_id: Optional[uuid.UUID] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[date] = None


class TaskRead(TaskBase):
    id: uuid.UUID
    project_id: uuid.UUID
    assignee_id: Optional[uuid.UUID] = None  # RBAC §39
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Documents (3.md §15-16)
# ---------------------------------------------------------------------------
class DocumentBase(BaseModel):
    project_item_id: Optional[uuid.UUID] = None
    document_type: str = "UNIFIED"  # MOCKUP|SIGNAL|BATCH|UNIFIED
    status: str = "NOT_READY"  # NOT_READY|PREPARED|SENT|SIGNED
    file_name: Optional[str] = None
    storage_key: Optional[str] = None
    uploaded_by: Optional[str] = None
    doc_date: Optional[date] = None
    comment: Optional[str] = None


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    document_type: Optional[str] = None
    status: Optional[str] = None
    file_name: Optional[str] = None
    storage_key: Optional[str] = None
    uploaded_by: Optional[str] = None
    doc_date: Optional[date] = None
    comment: Optional[str] = None
    project_item_id: Optional[uuid.UUID] = None


class DocumentRead(DocumentBase):
    id: uuid.UUID
    project_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Events (3.md §18) / Activity (3.md §20) / Summary (3.md §21-22)
# ---------------------------------------------------------------------------
class ProjectEventRead(BaseModel):
    id: Optional[uuid.UUID] = None  # None для производных событий (§19)
    project_item_id: Optional[uuid.UUID] = None
    event_type: str
    event_date: Optional[date] = None
    title: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ActivityItemRead(BaseModel):
    created_at: datetime
    user_name: Optional[str]
    action: str
    entity_type: str
    old_value: Optional[dict]
    new_value: Optional[dict]

    model_config = ConfigDict(from_attributes=True)


class ProductionTimelineStage(BaseModel):
    code: str
    label: str
    status: str  # done|active|pending|na


class ProductionTimelineRead(BaseModel):
    stages: list[ProductionTimelineStage]


class ProjectSummaryRead(BaseModel):
    """Краткое резюме проекта для Drawer (3.md §21-22)."""

    project_id: uuid.UUID
    display_id: str
    title: str
    risk_level: Optional[str] = None
    deadline: Optional[date] = None
    payment_percent: Optional[str] = None
    currency: Optional[str] = None
    next_action: Optional[str] = None
    suggested_next_action: Optional[str] = None
    items_count: int = 0
    open_tasks_count: int = 0
    health: str  # healthy|attention|at_risk|critical
    health_reasons: list[str] = Field(default_factory=list)


class ProjectActivityResponse(BaseModel):
    items: list[ActivityItemRead]



class AutomationBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    enabled: bool = True
    trigger_type: str
    trigger_config: dict[str, Any] = Field(default_factory=dict)
    conditions: dict[str, Any] = Field(default_factory=dict)
    actions: list[dict[str, Any]] = Field(default_factory=list)


class AutomationCreate(AutomationBase):
    pass


class AutomationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    trigger_type: Optional[str] = None
    trigger_config: Optional[dict[str, Any]] = None
    conditions: Optional[dict[str, Any]] = None
    actions: Optional[list[dict[str, Any]]] = None


class AutomationRead(AutomationBase):
    id: uuid.UUID
    workspace_id: uuid.UUID
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class EventRead(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    type: str
    entity_type: str
    entity_id: Optional[uuid.UUID] = None
    actor_id: Optional[uuid.UUID] = None
    payload: dict[str, Any] = Field(default_factory=dict)
    chain_id: uuid.UUID
    execution_depth: int = 0
    deduplication_key: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AutomationRunRead(BaseModel):
    id: uuid.UUID
    automation_id: uuid.UUID
    event_id: uuid.UUID
    status: str
    attempt: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    idempotency_key: str
    model_config = ConfigDict(from_attributes=True)


class NotificationRead(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    type: str
    title: str
    message: str
    entity_type: Optional[str] = None
    entity_id: Optional[uuid.UUID] = None
    read: bool = False
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class NotificationPreferenceUpdate(BaseModel):
    category: str = "all"
    in_app: bool = True
    email: bool = False
    telegram: bool = False
    quiet_start: str = "22:00"
    quiet_end: str = "08:00"


class AuditLogRead(BaseModel):
    id: uuid.UUID
    user_name: Optional[str]
    action: str
    entity_type: str
    entity_id: Optional[uuid.UUID]
    old_value: Optional[dict]
    new_value: Optional[dict]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BulkItemsUpdateRequest(BaseModel):
    """Массовое изменение позиций (3.md §29)."""

    ids: list[uuid.UUID]
    mockup_status: Optional[str] = None
    signal_status: Optional[str] = None
    factory: Optional[str] = None


# ---------------------------------------------------------------------------
# Stage 9: RBAC schemas (Users / Roles / Permissions / Memberships / Teams / Invitations)
# ---------------------------------------------------------------------------
class UserRead(BaseModel):
    id: uuid.UUID
    email: str
    name: Optional[str] = None
    display_name: str
    avatar_url: Optional[str] = None
    is_active: bool = True
    timezone: str = "UTC"
    language: str = "ru"
    role: str = "MANAGER"
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class UserUpdateProfile(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None


class RoleRead(BaseModel):
    id: uuid.UUID
    workspace_id: Optional[uuid.UUID] = None
    name: str
    code: str
    description: Optional[str] = None
    is_system: bool = False
    permissions: list[str] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    code: str = Field(min_length=1, max_length=40)
    description: Optional[str] = None
    permissions: list[str] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[list[str]] = None


class WorkspaceMemberRead(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    role_id: uuid.UUID
    role_code: str = "MEMBER"
    status: str = "ACTIVE"
    email: Optional[str] = None
    display_name: Optional[str] = None
    joined_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class WorkspaceMemberUpdate(BaseModel):
    role_id: Optional[uuid.UUID] = None
    status: Optional[str] = None


class TeamRead(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: Optional[str] = None
    member_ids: list[uuid.UUID] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class TeamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = None


class TeamUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = None


class TeamMemberUpdate(BaseModel):
    member_id: uuid.UUID


class InvitationCreate(BaseModel):
    email: str
    role_code: str = "MEMBER"


class InvitationRead(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    email: str
    role_id: uuid.UUID
    role_code: Optional[str] = None
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class InvitationAccept(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class OwnershipTransfer(BaseModel):
    new_owner_member_id: uuid.UUID


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    timezone: str = "UTC"
    default_currency: str = "RUB"


class WorkspaceRead(BaseModel):
    id: uuid.UUID
    name: str
    timezone: str = "UTC"
    default_currency: str = "RUB"
    created_at: Optional[datetime] = None
    # Полезно при создании workspace (RBAC §29): создатель автоматически OWNER
    owner_id: Optional[str] = None
    my_role: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    timezone: Optional[str] = None
    default_currency: Optional[str] = None
    working_days: Optional[dict] = None
    working_hours: Optional[dict] = None


class PermissionRead(BaseModel):
    code: str
    description: Optional[str] = None


class UserPermissionsResponse(BaseModel):
    user_id: Optional[uuid.UUID] = None
    role: str
    workspace_id: uuid.UUID
    permissions: dict[str, bool]