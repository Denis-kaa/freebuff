#!/usr/bin/env python3
"""Seed: наполняет БД демо-данными (спец. 1.md §30).

Запуск:  python seed.py
Идемпотентно: если проекты уже есть — ничего не делает.
"""
import asyncio
import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base, SessionLocal, engine
from app.models import (
    AuditLog,
    CustomField,
    CustomFieldValue,
    Dashboard,
    DashboardWidget,
    Project,
    ProjectItem,
    Task,
    User,
    Workspace,
)

DEMO_WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

PROJECTS = [
    # title, client, manager, stage, deadline_offset, risk, payment, currency, next_action
    ("Wazzup", "ООО «Вазз»", "Денис", "Производство сигнала", 2, "Высокий", "80%", "USDT / Крипта", "Согласовать сигнальный образец"),
    ("Чико", "ООО «Чико»", "Катя", "Технический макет", 5, "Средний", "50%", "RUB", "Получить ОС по сигналу"),
    ("Юнигаз", "АО «Юнигаз»", "Миша", "Производство тиража", 8, "Нет", "100%", "RUB", "Проверить статус проекта"),
    ("Добрый Лоси", "ООО «Лось»", "Денис", "Правки дизайна", 1, "Критический", "80%", "RUB", "Уточнить оплату после 3-й правки"),
    ("Fame2Flame", "ООО «Ф2Ф»", "Катя", "Дизайн", 12, "Низкий", "50%", "EUR", "Запросить отчёт дизайна"),
    ("ТНТ", "АО «ТНТ»", "Миша", "Вошёл в работу", 3, "Средний", "0%", "RUB", "Проверить получение оплаты"),
    ("AppScience", "ООО «АпСай»", "Денис", "Производство сигнала", -1, "Критический", "80%", "USDT / Крипта", "Разобраться со срывом"),
    ("PoliteChem", "ООО «ПолитХим»", "Катя", "Правки тиража", -3, "Высокий", "100%", "RUB", "Согласовать правки дизайна"),
    ("РОМАШКА", "ООО «Ромашка»", "Иванов А.", "Производство тиража", 10, "Нет", "100%", "USDT / Крипта", ""),
    ("ПЕКАРНЯ", "ООО «Пекарь»", "Кузнецова Е.", "Производство сигнала", 4, "Средний", "50%", "RUB", "Проверить статус проекта"),
]

ITEMS = [
    ("Худи оверсайз", 100, "Шелкография, 300 гр/м2, PANTONE 1505 C", "Согласован"),
    ("Футболка", 50, "Сублимация, белый, S/M 20, L/XL 30", "Согласован"),
    ("Кепка", 30, "Вышивка, чёрный", "В работе"),
    ("Носки", 200, "Сублимация, белый", "Новый"),
    ("Зип-худи", 50, "Шелкография + сублимация, 400 гр/м2", "Согласован"),
    ("Толстовка", 75, "Шелкография, 330 гр/м2", "В работе"),
    ("Футболка оверсайз", 40, "Сублимация, 300 гр/м2", "Согласован"),
    ("Шоппер", 300, "Шелкография 1+0, хлопок", "Согласован"),
    ("Блокнот А5", 500, "Тиснение, кожзам", "В работе"),
    ("Ручка", 1000, "Лазер, металл", "Новый"),
    ("Кружка", 250, "Сублимация", "Согласован"),
    ("Панама", 60, "Вышивка, хлопок", "В работе"),
    ("Бейсболка", 80, "Вышивка", "Согласован"),
    ("Эко-сумка", 150, "Шелкография", "Новый"),
    ("Значок", 400, "Металл, заливка", "Согласован"),
    ("Папка А4", 120, "Тиснение", "В работе"),
]

TASKS = [
    ("Согласовать макет", "TODO", "Высокий", 1),
    ("Получить ОС по сигналу", "IN_PROGRESS", "Высокий", 2),
    ("Запустить тираж", "TODO", "Средний", 3),
    ("Проверить оплату", "IN_PROGRESS", "Критический", 1),
    ("Отправить УПД дизайн", "DONE", "Низкий", 2),
    ("Запросить отчёт", "TODO", "Средний", 3),
    ("Уточнить сроки доставки", "TODO", "Низкий", 4),
    ("Согласовать сигнальный образец", "IN_PROGRESS", "Высокий", 5),
    ("Проверить статус проекта", "DONE", "Низкий", 6),
    ("Разобраться со срывом", "IN_PROGRESS", "Критический", 7),
    ("Согласовать правки дизайна", "TODO", "Высокий", 8),
    ("Проверить получение оплаты", "TODO", "Критический", 9),
    ("Проверить статус проекта", "IN_PROGRESS", "Средний", 10),
    ("Подготовить закрывающие документы", "TODO", "Средний", 1),
    ("Согласовать цвет", "DONE", "Низкий", 2),
    ("Уточнить размерный ряд", "TODO", "Средний", 3),
    ("Отправить тираж", "TODO", "Высокий", 4),
    ("Получить ОС по тиражу", "TODO", "Высокий", 5),
    ("Запросить доплату", "IN_PROGRESS", "Высокий", 6),
    ("Закрыть проект", "TODO", "Низкий", 7),
]


async def seed() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        # Проверка идемпотентности
        exists = await session.scalar(select(Project.id).limit(1))
        if exists is not None:
            print("База уже наполнена — пропускаем seed.")
            return

        ws = Workspace(id=DEMO_WORKSPACE_ID, name="Демо-воркспейс")
        session.add(ws)
        await session.flush()

        # Пользователи
        users = [
            User(workspace_id=DEMO_WORKSPACE_ID, email="denis@pm.local", display_name="Денис", role="ADMIN"),
            User(workspace_id=DEMO_WORKSPACE_ID, email="katya@pm.local", display_name="Катя", role="MANAGER"),
            User(workspace_id=DEMO_WORKSPACE_ID, email="misha@pm.local", display_name="Миша", role="MANAGER"),
            User(workspace_id=DEMO_WORKSPACE_ID, email="ivanov@pm.local", display_name="Иванов А.", role="MANAGER"),
        ]
        session.add_all(users)

        # Custom Fields (спец. §7)
        custom_fields = [
            CustomField(
                workspace_id=DEMO_WORKSPACE_ID, entity_type="PROJECT", name="Номер накладной",
                slug="invoice_number", field_type="TEXT", position=0,
            ),
            CustomField(
                workspace_id=DEMO_WORKSPACE_ID, entity_type="PROJECT", name="Количество упаковок",
                slug="packages", field_type="NUMBER", position=1,
            ),
            CustomField(
                workspace_id=DEMO_WORKSPACE_ID, entity_type="PROJECT", name="Дата доставки",
                slug="delivery_date", field_type="DATE", position=2,
            ),
            CustomField(
                workspace_id=DEMO_WORKSPACE_ID, entity_type="PROJECT", name="Приоритет",
                slug="priority", field_type="SELECT", options=["Низкий", "Средний", "Высокий"], position=3,
            ),
            CustomField(
                workspace_id=DEMO_WORKSPACE_ID, entity_type="PROJECT", name="Внутренний комментарий",
                slug="internal_note", field_type="LONG_TEXT", position=4,
            ),
            CustomField(
                workspace_id=DEMO_WORKSPACE_ID, entity_type="PROJECT", name="Маржа",
                slug="margin", field_type="FORMULA", formula="packages * 150", position=5,
            ),
        ]
        session.add_all(custom_fields)
        await session.flush()

        # Проекты + позиции + задачи + значения полей
        today = date.today()
        projects_by_title: dict[str, Project] = {}
        cf_by_slug = {cf.slug: cf for cf in custom_fields}

        for i, (title, client, manager, stage, days, risk, pay, cur, action) in enumerate(PROJECTS, start=1):
            p = Project(
                workspace_id=DEMO_WORKSPACE_ID,
                display_id=f"P{i:03d}",
                title=title,
                client_legal_name=client,
                manager_name=manager,
                stage=stage,
                deadline=today + timedelta(days=days),
                risk_level=risk,
                payment_percent=pay,
                currency=cur,
                advance_date=today + timedelta(days=max(days - 10, -5)),
                final_payment_date=today + timedelta(days=days + 7),
                delivery_address=f"г. Москва, ул. {title}, д. {i}",
                delivery_paid="есть" if i % 2 else "нет",
                next_action=action,
                next_action_date=today + timedelta(days=max(days - 1, 0)),
            )
            session.add(p)
            projects_by_title[title] = p
            await session.flush()

            # 1-2 позиции на проект
            for j in range(2):
                it = ITEMS[(i + j) % len(ITEMS)]
                session.add(
                    ProjectItem(
                        project_id=p.id,
                        name=f"{it[0]} ({p.title})",
                        quantity=it[1],
                        tech_specs=it[2],
                        mockup_status=it[3],
                        signal_required=(i + j) % 3 == 0,
                        signal_status="Согласован" if (i + j) % 2 else "В работе",
                        signal_shipping_date=today + timedelta(days=max(days - 2, 0)),
                        batch_status="Производство" if (i + j) % 2 else "Ожидание",
                    )
                )

            # Значения custom fields
            session.add(
                CustomFieldValue(
                    custom_field_id=cf_by_slug["invoice_number"].id,
                    entity_id=p.id, project_id=p.id, value=f"НН-{1000 + i}",
                )
            )
            session.add(
                CustomFieldValue(
                    custom_field_id=cf_by_slug["packages"].id,
                    entity_id=p.id, project_id=p.id, value=i * 3,
                )
            )
            session.add(
                CustomFieldValue(
                    custom_field_id=cf_by_slug["delivery_date"].id,
                    entity_id=p.id, project_id=p.id,
                    value=(today + timedelta(days=days + 3)).isoformat(),
                )
            )
            session.add(
                CustomFieldValue(
                    custom_field_id=cf_by_slug["priority"].id,
                    entity_id=p.id, project_id=p.id,
                    value="Высокий" if risk in ("Высокий", "Критический") else "Средний",
                )
            )

        # Задачи
        proj_list = list(projects_by_title.values())
        for k, (title, status, priority, proj_idx) in enumerate(TASKS, start=1):
            session.add(
                Task(
                    project_id=proj_list[proj_idx % len(proj_list)].id,
                    title=title,
                    status=status,
                    priority=priority,
                    due_date=today + timedelta(days=k % 7),
                )
            )

        # Дашборды (спец. §11, §15)
        dash1 = Dashboard(workspace_id=DEMO_WORKSPACE_ID, name="Главный")
        dash2 = Dashboard(workspace_id=DEMO_WORKSPACE_ID, name="Производство")
        dash3 = Dashboard(workspace_id=DEMO_WORKSPACE_ID, name="Финансы")
        session.add_all([dash1, dash2, dash3])
        await session.flush()

        widgets = [
            DashboardWidget(dashboard_id=dash1.id, widget_type="kpi", title="KPI", position="0,0", width=2, height=1),
            DashboardWidget(dashboard_id=dash1.id, widget_type="deadlines", title="Дедлайны", position="2,0", width=2, height=2),
            DashboardWidget(dashboard_id=dash1.id, widget_type="risks", title="Риски", position="4,0", width=2, height=2),
            DashboardWidget(dashboard_id=dash1.id, widget_type="tasks", title="Задачи", position="0,2", width=2, height=2),
            DashboardWidget(dashboard_id=dash2.id, widget_type="projects", title="Проекты в производстве", position="0,0", width=4, height=2),
            DashboardWidget(dashboard_id=dash3.id, widget_type="payments", title="Оплаты", position="0,0", width=2, height=2),
        ]
        session.add_all(widgets)

        # Аудит (спец. §28)
        session.add(
            AuditLog(
                workspace_id=DEMO_WORKSPACE_ID, user_name="Денис",
                action="seed", entity_type="workspace", entity_id=DEMO_WORKSPACE_ID,
                new_value={"count": len(PROJECTS)},
            )
        )

        await session.commit()
        print(f"✅ Seed завершён: {len(PROJECTS)} проектов, {len(ITEMS) * 2} позиций, "
              f"{len(TASKS)} задач, 3 дашборда, {len(custom_fields)} custom fields")


if __name__ == "__main__":
    asyncio.run(seed())
