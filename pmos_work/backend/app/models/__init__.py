"""Модели PM OS.

Три уровня (из спецификации 1.md §3):
- CORE DATA: Project, ProjectItem, Task, Payment, Document, Delivery, User
- CONFIGURATION: CustomField, CustomFieldValue, View, Dashboard, DashboardWidget
- Утилитарные: AuditLog

Пользовательские поля НЕ создают физических колонок PostgreSQL
(спецификация §7, §9) — используется динамическая модель:
custom_fields (описание) + custom_field_values (значения, JSONB в value).
"""
import uuid
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


# ---------------------------------------------------------------------------
# CORE DATA
# ---------------------------------------------------------------------------
class Workspace(Base):
    """Рабочее пространство (tenant-граница для security §24)."""

    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    timezone: Mapped[str] = mapped_column(String(80), nullable=False, server_default="UTC")
    default_currency: Mapped[str] = mapped_column(String(20), nullable=False, server_default="RUB")
    working_days: Mapped[Optional[dict]] = mapped_column(JSON)
    working_hours: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    users: Mapped[list["User"]] = relationship(back_populates="workspace")
    projects: Mapped[list["Project"]] = relationship(back_populates="workspace")
    memberships: Mapped[list["WorkspaceMember"]] = relationship(back_populates="workspace_entity")


class User(Base):
    """Пользователь workspace (minimal — роль для permissions §25)."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(150), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="MANAGER")  # ADMIN|MANAGER|VIEWER
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    name: Mapped[Optional[str]] = mapped_column(String(150))  # RBAC §2 name (alias of display_name)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    timezone: Mapped[str] = mapped_column(String(80), nullable=False, server_default="UTC")
    language: Mapped[str] = mapped_column(String(20), nullable=False, server_default="ru")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    workspace: Mapped["Workspace"] = relationship(back_populates="users")
    memberships: Mapped[list["WorkspaceMember"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class WorkspaceMember(Base):
    """Membership: user ↔ workspace с ролью (RBAC §4)."""

    __tablename__ = "workspace_members"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")  # ACTIVE|INVITED|SUSPENDED|DEACTIVATED
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),
    )

    user: Mapped["User"] = relationship(back_populates="memberships")
    workspace_entity: Mapped["Workspace"] = relationship(back_populates="memberships")



class Project(Base):
    """Проект. display_id человекочитаемый (P001), id — UUID (спец. §4)."""

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    display_id: Mapped[str] = mapped_column(String(10), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    client_legal_name: Mapped[Optional[str]] = mapped_column(String(255))
    manager_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    manager_name: Mapped[Optional[str]] = mapped_column(String(150))  # denormalized для скорости
    stage: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    deadline: Mapped[Optional[date]] = mapped_column(Date, index=True)
    risk_level: Mapped[Optional[str]] = mapped_column(String(30), default="Нет", index=True)
    risk_reason: Mapped[Optional[str]] = mapped_column(Text)
    payment_percent: Mapped[Optional[str]] = mapped_column(String(10))  # 0%|50%|80%|100%
    currency: Mapped[Optional[str]] = mapped_column(String(20), default="RUB")
    advance_date: Mapped[Optional[date]] = mapped_column(Date)
    final_payment_date: Mapped[Optional[date]] = mapped_column(Date)
    delivery_address: Mapped[Optional[str]] = mapped_column(Text)
    delivery_paid: Mapped[Optional[str]] = mapped_column(String(10))  # есть/нет
    next_action: Mapped[Optional[str]] = mapped_column(Text)  # «Следующее действие» (промт.md)
    next_action_date: Mapped[Optional[date]] = mapped_column(Date)  # дата для УФ AH
    comment: Mapped[Optional[str]] = mapped_column(Text)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)  # optimistic locking (3.md §25)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (UniqueConstraint("workspace_id", "display_id", name="uq_project_display_id"),)

    workspace: Mapped["Workspace"] = relationship(back_populates="projects")
    items: Mapped[list["ProjectItem"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    tasks: Mapped[list["Task"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    values: Mapped[list["CustomFieldValue"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", foreign_keys="Document.project_id"
    )
    events: Mapped[list["ProjectEvent"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", foreign_keys="ProjectEvent.project_id"
    )


class ProjectItem(Base):
    """Позиция проекта (несколько изделий в одном проекте, спец. §5)."""

    __tablename__ = "project_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[Optional[int]] = mapped_column(Integer)
    tech_specs: Mapped[Optional[str]] = mapped_column(Text)
    mockup_status: Mapped[Optional[str]] = mapped_column(String(100))
    signal_required: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    signal_status: Mapped[Optional[str]] = mapped_column(String(100))
    signal_shipping_date: Mapped[Optional[date]] = mapped_column(Date)
    signal_feedback: Mapped[Optional[str]] = mapped_column(Text)
    batch_status: Mapped[Optional[str]] = mapped_column(String(100))
    batch_feedback: Mapped[Optional[str]] = mapped_column(Text)
    factory: Mapped[Optional[str]] = mapped_column(String(150))  # фабрика (для bulk-действий §29)
    version: Mapped[int] = mapped_column(Integer, default=1)  # optimistic locking
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="items")
    documents: Mapped[list["Document"]] = relationship(back_populates="project_item")
    events: Mapped[list["ProjectEvent"]] = relationship(back_populates="project_item")


class Task(Base):
    """Задача (спец. §6). Может быть связана с проектом или глобальной."""

    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    assignee_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assignee_name: Mapped[Optional[str]] = mapped_column(String(150))  # denormalized
    project_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("project_items.id", ondelete="SET NULL"), nullable=True, index=True
    )  # задача привязана к позиции (3.md §12)
    status: Mapped[str] = mapped_column(String(20), default="TODO", index=True)  # TODO|IN_PROGRESS|DONE|CANCELLED
    priority: Mapped[Optional[str]] = mapped_column(String(20))
    due_date: Mapped[Optional[date]] = mapped_column(Date, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped[Optional["Project"]] = relationship(back_populates="tasks")
    project_item: Mapped[Optional["ProjectItem"]] = relationship()


# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
class CustomField(Base):
    """Описание пользовательского поля (спец. §7). НЕ физическая колонка."""

    __tablename__ = "custom_fields"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(20), default="PROJECT", index=True)  # PROJECT|PROJECT_ITEM|TASK
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    field_type: Mapped[str] = mapped_column(String(20), nullable=False)  # TEXT|NUMBER|DATE|SELECT|...
    description: Mapped[Optional[str]] = mapped_column(Text)
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    default_value: Mapped[Optional[str]] = mapped_column(Text)
    options: Mapped[Optional[list]] = mapped_column(JSON)  # для SELECT/MULTI_SELECT
    formula: Mapped[Optional[str]] = mapped_column(Text)  # FORMULA (движок — отдельный этап)
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (UniqueConstraint("workspace_id", "entity_type", "slug", name="uq_custom_field_slug"),)


class CustomFieldValue(Base):
    """Значение пользовательского поля для конкретной сущности (спец. §9).

    value хранит значение с типизацией: str, int, float, bool, list, dict.
    """

    __tablename__ = "custom_field_values"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    custom_field_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("custom_fields.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True
    )
    value: Mapped[Any] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("custom_field_id", "entity_id", name="uq_custom_field_value_entity"),
    )

    project: Mapped[Optional["Project"]] = relationship(back_populates="values")


class View(Base):
    """Сохранённое представление (спец. §10, 2.md §12-13, 7.md §2).

    config — JSON: visible_columns, column_order, column_widths,
    filters (nested AND/OR, 7.md §8-9), sorting (multi-level §16),
    grouping (§41), view_type (TABLE|KANBAN|CALENDAR §43).
    entity_type — projects|tasks|production|finance (7.md §2).
    visibility — private|workspace (7.md §26).
    """

    __tablename__ = "views"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(30), default="projects", index=True)
    view_type: Mapped[str] = mapped_column(String(20), default="TABLE")  # TABLE|KANBAN|CALENDAR
    visibility: Mapped[str] = mapped_column(String(20), default="workspace")  # private|workspace
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(150))
    # JSON-конфигурация: visible_columns, column_order, column_widths,
    # filters, sorting, grouping, density (спец. §13)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Dashboard(Base):
    """Дашборд-конструктор (спец. 4.md §16).

    Один Dashboard в workspace может быть is_default = true (4.md §20).
    version — optimistic locking (4.md §44): два пользователя не могут
    молча перезаписать layout друг друга.
    """

    __tablename__ = "dashboards"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)  # optimistic locking (4.md §44)
    layout: Mapped[Optional[dict]] = mapped_column(JSON)  # legacy: grid-раскладка
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    widgets: Mapped[list["DashboardWidget"]] = relationship(
        back_populates="dashboard", cascade="all, delete-orphan"
    )


class DashboardWidget(Base):
    """Виджет дашборда (4.md §16).

    config — настройки виджета (JSON, например режим календаря, радиус дедлайнов,
    источник KPI-метрики). layout — grid-раскладка {"x":0,"y":0,"w":6,"h":4}.
    is_hidden — виджет скрыт, но не удалён (4.md §9): конфигурация сохраняется.
    Удаление Widget Instance НЕ удаляет данные (4.md §8).
    """

    __tablename__ = "dashboard_widgets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    dashboard_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dashboards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    widget_type: Mapped[str] = mapped_column(String(50), nullable=False)  # calendar|today-tasks|deadlines|...
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    config: Mapped[Optional[dict]] = mapped_column(
        JSON, name="config", default=dict
    )  # настройки виджета (4.md §15)
    layout: Mapped[Optional[dict]] = mapped_column(JSON)  # {"x":0,"y":0,"w":6,"h":4} (4.md §16)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    # legacy-колонки (этап 1) — не удаляем (Additive Architecture):
    configuration: Mapped[Optional[dict]] = mapped_column(JSON, name="configuration")
    position: Mapped[Optional[str]] = mapped_column(String(10))  # "x,y"
    width: Mapped[int] = mapped_column(Integer, default=1)
    height: Mapped[int] = mapped_column(Integer, default=1)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    dashboard: Mapped["Dashboard"] = relationship(back_populates="widgets")


class Document(Base):
    """Документ проекта/позиции (спец. 3.md §15-16). Файл — во внешнем хранилище."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("project_items.id", ondelete="CASCADE"), nullable=True, index=True
    )
    document_type: Mapped[str] = mapped_column(String(30), nullable=False)  # MOCKUP|SIGNAL|BATCH|UNIFIED
    status: Mapped[str] = mapped_column(String(30), default="NOT_READY")  # NOT_READY|PREPARED|SENT|SIGNED
    file_name: Mapped[Optional[str]] = mapped_column(String(300))
    storage_key: Mapped[Optional[str]] = mapped_column(String(500))
    uploaded_by: Mapped[Optional[str]] = mapped_column(String(150))
    doc_date: Mapped[Optional[date]] = mapped_column(Date)
    comment: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped["Project"] = relationship(
        back_populates="documents", foreign_keys=[project_id]
    )
    project_item: Mapped[Optional["ProjectItem"]] = relationship(
        back_populates="documents", foreign_keys=[project_item_id]
    )


class ProjectEvent(Base):
    """Событие проекта (спец. 3.md §18). Часть дат выводится из Project/Item (§19)."""

    __tablename__ = "project_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("project_items.id", ondelete="CASCADE"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)  # DEADLINE|MOCKUP|SIGNAL_SHIPMENT|...
    event_date: Mapped[Optional[date]] = mapped_column(Date, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(300))
    description: Mapped[Optional[str]] = mapped_column(Text)
    source: Mapped[Optional[str]] = mapped_column(String(30), default="derived")  # derived|manual
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["Project"] = relationship(
        back_populates="events", foreign_keys=[project_id]
    )
    project_item: Mapped[Optional["ProjectItem"]] = relationship(
        back_populates="events", foreign_keys=[project_item_id]
    )


class CalendarEvent(Base):
    """Ручное событие календаря (5.md §22).

    Таблица предназначена ПРЕИМУЩЕСТВЕННО для CUSTOM-событий: встречи, звонки,
    напоминания. Системные события (дедлайны, оплаты, отгрузки…) НЕ дублируются
    в этой таблице — CalendarService строит их из Project/Task/Item (5.md §1, §23).

    Все даты/время — в UTC (5.md §38); UI показывает локальное время пользователя.
    recurrence_rule — архитектура для recurring events (5.md §37, MVP: nullable).
    """

    __tablename__ = "calendar_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False, default="REMINDER")  # REMINDER|MEETING|CALL|OTHER|CUSTOM
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    all_day: Mapped[bool] = mapped_column(Boolean, default=False)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True
    )
    project_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("project_items.id", ondelete="SET NULL"), nullable=True, index=True
    )
    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(150))
    recurrence_rule: Mapped[Optional[str]] = mapped_column(String(200))  # RRULE (5.md §37)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped[Optional["Project"]] = relationship()
    project_item: Mapped[Optional["ProjectItem"]] = relationship()
    task: Mapped[Optional["Task"]] = relationship()


class ImportMapping(Base):
    """Сохранённое сопоставление колонок (6.md §9)."""

    __tablename__ = "import_mappings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), default="excel")  # excel|csv|google_sheets
    mapping_config: Mapped[Optional[dict]] = mapped_column(JSON)  # {excel_col: db_field}
    created_by: Mapped[Optional[str]] = mapped_column(String(150))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ImportJob(Base):
    """История импорта (6.md §36-38). Status: PENDING|PROCESSING|VALIDATING|
    IMPORTING|COMPLETED|FAILED|CANCELLED (§47)."""

    __tablename__ = "import_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)  # excel|csv|google_sheets
    file_name: Mapped[Optional[str]] = mapped_column(String(300))
    sheet_name: Mapped[Optional[str]] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    duplicate_mode: Mapped[str] = mapped_column(String(10), default="update")  # update|skip|copy
    partial: Mapped[bool] = mapped_column(Boolean, default=False)  # импорт только корректных
    created_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, default=0)
    preview: Mapped[Optional[dict]] = mapped_column(JSON)  # summary предпросмотра
    errors: Mapped[Optional[list]] = mapped_column(JSON)  # [{row, field, value, error, level}]
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[Optional[str]] = mapped_column(String(150))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExportPreset(Base):
    """Сохранённые настройки экспорта (6.md §40)."""

    __tablename__ = "export_presets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict)  # {scope, columns, filters, sort, format}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ProjectTag(Base):
    __tablename__ = "project_tags"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    tag: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("project_id", "tag", name="uq_project_tag"),)


class DomainEvent(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    chain_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=_uuid, index=True)
    execution_depth: Mapped[int] = mapped_column(Integer, default=0)
    deduplication_key: Mapped[Optional[str]] = mapped_column(String(300), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class Automation(Base):
    __tablename__ = "automations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    trigger_type: Mapped[str] = mapped_column(String(100), nullable=False)
    trigger_config: Mapped[dict] = mapped_column(JSON, default=dict)
    conditions: Mapped[dict] = mapped_column(JSON, default=dict)
    actions: Mapped[list] = mapped_column(JSON, default=list)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AutomationRun(Base):
    __tablename__ = "automation_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    automation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("automations.id", ondelete="CASCADE"), nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    result: Mapped[Optional[dict]] = mapped_column(JSON)
    error: Mapped[Optional[str]] = mapped_column(Text)
    idempotency_key: Mapped[str] = mapped_column(String(400), unique=True, nullable=False)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    type: Mapped[str] = mapped_column(String(30), default="INFO")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(50))
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    deduplication_key: Mapped[Optional[str]] = mapped_column(String(400), unique=True)
    read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    in_app: Mapped[bool] = mapped_column(Boolean, default=True)
    email: Mapped[bool] = mapped_column(Boolean, default=False)
    telegram: Mapped[bool] = mapped_column(Boolean, default=False)
    quiet_start: Mapped[str] = mapped_column(String(5), default="22:00")
    quiet_end: Mapped[str] = mapped_column(String(5), default="08:00")


class Permission(Base):
    """Глобальный каталог permission-кодов (RBAC §7)."""

    __tablename__ = "permissions"
    __table_args__ = {"extend_existing": True}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)


class Role(Base):
    """Роль в workspace (RBAC §5). Системные роли (is_system=True) — OWNER/ADMIN/MANAGER/MEMBER/VIEWER."""

    __tablename__ = "roles"
    __table_args__ = {"extend_existing": True}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, index=True
    )  # NULL = системный шаблон роли
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("workspace_id", "code", name="uq_role_workspace_code"),
        {"extend_existing": True},
    )


class RolePermission(Base):
    """Связь роль↔permission (RBAC §7)."""

    __tablename__ = "role_permissions"
    __table_args__ = {"extend_existing": True}
    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )


class Team(Base):
    """Команда/отдел в workspace (RBAC §12)."""

    __tablename__ = "teams"
    __table_args__ = {"extend_existing": True}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("workspace_id", "name", name="uq_team_workspace_name"),)


class TeamMember(Base):
    """Член команды (RBAC §12)."""

    __tablename__ = "team_members"
    __table_args__ = {"extend_existing": True}
    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspace_members.id", ondelete="CASCADE"), primary_key=True
    )


class FieldPermission(Base):
    """Field-level permissions (RBAC §14). MVP: финансовый блок."""

    __tablename__ = "field_permissions"
    __table_args__ = {"extend_existing": True}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    field_code: Mapped[str] = mapped_column(String(160), nullable=False)
    can_read: Mapped[bool] = mapped_column(Boolean, default=False)
    can_update: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (UniqueConstraint("role_id", "field_code", name="uq_field_permission"),)


class WorkspaceInvitation(Base):
    """Приглашение в workspace (RBAC §17). Token хранится как hash."""

    __tablename__ = "workspace_invitations"
    __table_args__ = {"extend_existing": True}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    invited_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    """Аудит действий (спец. §28)."""

    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_name: Mapped[Optional[str]] = mapped_column(String(150))
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    old_value: Mapped[Optional[dict]] = mapped_column(JSON)
    new_value: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
