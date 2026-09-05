"""Widget Registry (4.md §2, §39) + шаблоны Dashboard (4.md §35-38).

Архитектурная цель: добавить новый виджет через несколько месяцев = регистрация
(Widget Definition + Widget Component + Data Provider), без переписывания
Dashboard Engine. Сервер хранит metadata (для /dashboards/widget-types) и
валидирует widget_type; данные виджеты получают через /dashboard-data/*.
"""

# type -> metadata (спец. 4.md §2)
WIDGET_REGISTRY: dict[str, dict] = {
    "calendar": {
        "type": "calendar",
        "name": "Календарь",
        "description": "Проекты, задачи и события по датам",
        "icon": "calendar",
        "category": "planning",
        "default_size": {"w": 6, "h": 4},
    },
    "today-tasks": {
        "type": "today-tasks",
        "name": "Что сделать сегодня",
        "description": "Задачи на сегодня, просроченные и Next Action",
        "icon": "check-square",
        "category": "planning",
        "default_size": {"w": 3, "h": 4},
    },
    "deadlines": {
        "type": "deadlines",
        "name": "Ближайшие дедлайны",
        "description": "Дедлайны проектов и позиций по датам",
        "icon": "clock",
        "category": "planning",
        "default_size": {"w": 6, "h": 2},
    },
    "projects": {
        "type": "projects",
        "name": "Проекты",
        "description": "Компактный список проектов",
        "icon": "folder",
        "category": "projects",
        "default_size": {"w": 3, "h": 4},
    },
    "risks": {
        "type": "risks",
        "name": "Срочные риски",
        "description": "High/Critical, просроченные, проблемы производства",
        "icon": "alert-triangle",
        "category": "projects",
        "default_size": {"w": 3, "h": 4},
    },
    "finance": {
        "type": "finance",
        "name": "Финансы",
        "description": "Неоплаченные проекты, авансы, доплаты, валюты",
        "icon": "wallet",
        "category": "finance",
        "default_size": {"w": 6, "h": 3},
    },
    "production": {
        "type": "production",
        "name": "Производство",
        "description": "Состояние Project Items: макеты, сигналы, тираж, отгрузка",
        "icon": "factory",
        "category": "production",
        "default_size": {"w": 6, "h": 2},
    },
    "activity": {
        "type": "activity",
        "name": "Последние изменения",
        "description": "Audit Activity: кто и что менял",
        "icon": "activity",
        "category": "overview",
        "default_size": {"w": 6, "h": 3},
    },
    "kpi": {
        "type": "kpi",
        "name": "KPI",
        "description": "Универсальный счётчик метрики (источник настраивается)",
        "icon": "gauge",
        "category": "overview",
        "default_size": {"w": 2, "h": 1},
    },
    # ------- AI Widget (4.md §40): обычный тип, Data Provider позже обратится к AI
    "ai_summary": {
        "type": "ai_summary",
        "name": "AI Assistant",
        "description": "Что происходит сегодня? (архитектура подготовлена)",
        "icon": "sparkles",
        "category": "overview",
        "default_size": {"w": 6, "h": 2},
    },
    # ------- legacy (этап 1, остаются валидными)
    "tasks": {"type": "tasks", "name": "Задачи", "description": "Задачи", "icon": "check-square", "category": "planning", "default_size": {"w": 2, "h": 2}},
    "payments": {"type": "payments", "name": "Оплаты", "description": "Оплаты", "icon": "wallet", "category": "finance", "default_size": {"w": 2, "h": 2}},
    "chart": {"type": "chart", "name": "График", "description": "График", "icon": "bar-chart", "category": "overview", "default_size": {"w": 2, "h": 2}},
    "table": {"type": "table", "name": "Таблица", "description": "Таблица", "icon": "table", "category": "overview", "default_size": {"w": 3, "h": 2}},
    "note": {"type": "note", "name": "Заметка", "description": "Заметка", "icon": "sticky-note", "category": "overview", "default_size": {"w": 1, "h": 1}},
}

# Служебные aliases: старый тип -> новый (для миграции legacy-данных)
WIDGET_TYPE_ALIASES = {
    "tasks": "today-tasks",
    "payments": "finance",
}

CATEGORY_ORDER = ["planning", "projects", "finance", "production", "overview"]


def resolve_widget_type(widget_type: str) -> str:
    """Нормализует legacy-тип в современный (для миграции/создания)."""
    return WIDGET_TYPE_ALIASES.get(widget_type, widget_type)


def widget_types_metadata() -> list[dict]:
    """Полная metadata для /dashboards/widget-types (4.md §2)."""
    return [dict(v, default_size=dict(v["default_size"])) for v in WIDGET_REGISTRY.values()]


# ---------------------------------------------------------------------------
# Шаблоны (4.md §35-38): шаблон = набор Widget Instances с дефолтными настройками.
# Не отдельная архитектура — просто дефолтный состав виджетов.
# ---------------------------------------------------------------------------
TEMPLATES: dict[str, dict] = {
    "manager": {
        "name": "Менеджер",
        "widgets": [
            {"widget_type": "today-tasks", "title": "Что сделать сегодня", "config": {"max": 10, "show_overdue": True, "show_today": True, "show_next_actions": True}, "layout": {"x": 0, "y": 0, "w": 4, "h": 4}},
            {"widget_type": "deadlines", "title": "Ближайшие дедлайны", "config": {"period_days": 7}, "layout": {"x": 4, "y": 0, "w": 8, "h": 2}},
            {"widget_type": "risks", "title": "Срочные риски", "config": {"levels": ["Высокий", "Критический"], "show_overdue": True}, "layout": {"x": 4, "y": 2, "w": 8, "h": 2}},
            {"widget_type": "calendar", "title": "Календарь", "config": {"view": "month", "show_deadlines": True, "show_tasks": True, "show_payments": True, "show_production": True}, "layout": {"x": 0, "y": 4, "w": 12, "h": 4}},
            {"widget_type": "projects", "title": "Проекты", "config": {"limit": 10}, "layout": {"x": 0, "y": 8, "w": 3, "h": 4}},
            {"widget_type": "activity", "title": "Последние изменения", "config": {"limit": 10}, "layout": {"x": 3, "y": 8, "w": 9, "h": 4}},
        ],
    },
    "production": {
        "name": "Производство",
        "widgets": [
            {"widget_type": "production", "title": "Производство", "config": {}, "layout": {"x": 0, "y": 0, "w": 6, "h": 2}},
            {"widget_type": "kpi", "title": "Сигналы", "config": {"metric": "signals_in_work"}, "layout": {"x": 6, "y": 0, "w": 2, "h": 1}},
            {"widget_type": "kpi", "title": "Тираж", "config": {"metric": "batch_in_work"}, "layout": {"x": 8, "y": 0, "w": 2, "h": 1}},
            {"widget_type": "kpi", "title": "Отгрузки", "config": {"metric": "shipments_pending"}, "layout": {"x": 10, "y": 0, "w": 2, "h": 1}},
            {"widget_type": "kpi", "title": "Ожидают ОС", "config": {"metric": "awaiting_feedback"}, "layout": {"x": 0, "y": 1, "w": 3, "h": 1}},
            {"widget_type": "kpi", "title": "Правки макетов", "config": {"metric": "mockup_revision"}, "layout": {"x": 3, "y": 1, "w": 3, "h": 1}},
            {"widget_type": "deadlines", "title": "Ближайшие дедлайны", "config": {"period_days": 7}, "layout": {"x": 0, "y": 2, "w": 6, "h": 2}},
            {"widget_type": "calendar", "title": "Календарь производства", "config": {"view": "month", "show_deadlines": True, "show_tasks": False, "show_payments": False, "show_production": True}, "layout": {"x": 6, "y": 2, "w": 6, "h": 4}},
        ],
    },
    "finance": {
        "name": "Финансы",
        "widgets": [
            {"widget_type": "kpi", "title": "Не оплаченные полностью", "config": {"metric": "unpaid_projects"}, "layout": {"x": 0, "y": 0, "w": 3, "h": 1}},
            {"widget_type": "kpi", "title": "Авансы на этой неделе", "config": {"metric": "advances_7d"}, "layout": {"x": 3, "y": 0, "w": 3, "h": 1}},
            {"widget_type": "kpi", "title": "Доплаты на этой неделе", "config": {"metric": "finals_7d"}, "layout": {"x": 6, "y": 0, "w": 3, "h": 1}},
            {"widget_type": "kpi", "title": "Проекты без оплаты", "config": {"metric": "no_payment"}, "layout": {"x": 9, "y": 0, "w": 3, "h": 1}},
            {"widget_type": "finance", "title": "Финансы", "config": {}, "layout": {"x": 0, "y": 1, "w": 12, "h": 3}},
            {"widget_type": "calendar", "title": "Календарь платежей", "config": {"view": "month", "show_deadlines": False, "show_tasks": False, "show_payments": True, "show_production": False}, "layout": {"x": 0, "y": 4, "w": 12, "h": 4}},
        ],
    },
    "director": {
        "name": "Руководитель",
        "widgets": [
            {"widget_type": "kpi", "title": "Активные проекты", "config": {"metric": "active_projects"}, "layout": {"x": 0, "y": 0, "w": 3, "h": 1}},
            {"widget_type": "kpi", "title": "Открытые задачи", "config": {"metric": "open_tasks"}, "layout": {"x": 3, "y": 0, "w": 3, "h": 1}},
            {"widget_type": "kpi", "title": "Дедлайны 7 дней", "config": {"metric": "deadlines_7d"}, "layout": {"x": 6, "y": 0, "w": 3, "h": 1}},
            {"widget_type": "kpi", "title": "Просроченные", "config": {"metric": "overdue_projects"}, "layout": {"x": 9, "y": 0, "w": 3, "h": 1}},
            {"widget_type": "risks", "title": "Срочные риски", "config": {"levels": ["Высокий", "Критический"], "show_overdue": True}, "layout": {"x": 0, "y": 1, "w": 4, "h": 4}},
            {"widget_type": "production", "title": "Производство", "config": {}, "layout": {"x": 4, "y": 1, "w": 8, "h": 2}},
            {"widget_type": "activity", "title": "Последние изменения", "config": {"limit": 12}, "layout": {"x": 4, "y": 3, "w": 8, "h": 2}},
            {"widget_type": "calendar", "title": "Календарь", "config": {"view": "month", "show_deadlines": True, "show_tasks": True, "show_payments": True, "show_production": True}, "layout": {"x": 0, "y": 5, "w": 12, "h": 4}},
        ],
    },
}


def template_widgets(template_key: str) -> list[dict]:
    """Виджеты шаблона с нормализованными типами (4.md §35)."""
    tmpl = TEMPLATES.get(template_key)
    if tmpl is None:
        return []
    widgets = []
    for w in tmpl["widgets"]:
        w = dict(w)
        w["widget_type"] = resolve_widget_type(w["widget_type"])
        widgets.append(w)
    return widgets