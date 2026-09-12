"""Тесты Этапа 4 (роадмап v6): Production — операции и задания.

Правила OPERATIONS_CATALOG: каталог — данные; задания генерируются по
триггерам (калькулятор/доп-работы/флаги); монтаж — последним; операция
не завершается без полного чек-листа (§10).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from printcalc_web import create_app, store

from asgi_client import ASGITestClient


@pytest.fixture()
def conn(tmp_path: Path) -> Iterator:
    from printcalc_web.db import connect

    connection = connect(tmp_path / "prod.db")
    store.seed_sections(connection)
    store.seed_operations(connection)
    yield connection
    connection.close()


@pytest.fixture()
def client(tmp_path: Path) -> Iterator[ASGITestClient]:
    yield ASGITestClient(create_app(db_path=tmp_path / "api_prod.db"))


def _banner_order(conn, *, eyelets: bool = True, install: bool = True, laminate: bool = False) -> dict:
    return store.create_order(
        conn,
        status="новый",
        payment_method="карта",
        items=[{
            "kind": "calculator",
            "calculator_id": "wide",
            "params": {
                "width": 300, "height": 100, "qty": 2,
                "material": "Баннер 440", "print": "Обычная печать", "mount": "Без монтажа",
                "work_eyelets": eyelets, "work_laminate_mount": laminate,
                "grommet_interval": 50,
                "delivery": False, "install": install,
            },
        }],
    )


# ---------- сид каталога ----------


def test_seed_operations_idempotent(conn) -> None:
    # сид уже применён фикстурой; повторный — ничего не создаёт (S2: +OP-22 = 13)
    second = store.seed_operations(conn)
    assert second["created"] == 0 and second["skipped"] == 13


# ---------- генерация по правилам (§3) ----------


def test_plan_includes_triggers_and_excludes_absent(conn) -> None:
    order = _banner_order(conn, eyelets=True, laminate=False)
    created = store.generate_production_plan(conn, order["id"])
    codes = [t["operation"]["code"] for t in created]
    # баннер → OP-04; люверсы → OP-13; монтаж → OP-19; ламинации НЕТ → OP-08 отсутствует
    assert "OP-04" in codes and "OP-13" in codes and "OP-19" in codes
    assert "OP-08" not in codes and "OP-05" not in codes  # не ризограф
    assert "OP-01" in codes and "OP-20" in codes  # always-операции
    # монтаж — всегда последний (position 8 > остальных)
    assert codes[-1] == "OP-19"


def test_laminate_flag_adds_operation(conn) -> None:
    with_lam = _banner_order(conn, laminate=True, eyelets=False, install=False)
    codes = {t["operation"]["code"] for t in store.generate_production_plan(conn, with_lam["id"])}
    assert "OP-08" in codes
    assert "OP-13" not in codes  # люверсов нет — операции нет (§3: «OP-08 автоматически исчезает»)


def test_regenerate_is_idempotent(conn) -> None:
    order = _banner_order(conn)
    first = store.generate_production_plan(conn, order["id"])
    second = store.generate_production_plan(conn, order["id"])
    assert first and second == []


# ---------- жизненный цикл + QC-гард (§10) ----------


def test_task_lifecycle_and_qc_guard(conn) -> None:
    order = _banner_order(conn)
    tasks = store.generate_production_plan(conn, order["id"])
    task = tasks[0]
    checklist_len = len(task["operation"]["checklist"])

    # завершить до взятия в работу — нельзя
    with pytest.raises(store.StoreError):
        store.complete_task(conn, task["id"], checklist=[True] * checklist_len)
    store.start_task(conn, task["id"])
    # без чек-листа — нельзя (§10: «Готово» без галочек не активна)
    with pytest.raises(store.StoreError):
        store.complete_task(conn, task["id"], checklist=[])
    # частичный чек-лист — нельзя
    with pytest.raises(store.StoreError):
        store.complete_task(conn, task["id"], checklist=[True] * (checklist_len - 1) + [False])
    done = store.complete_task(conn, task["id"], checklist=[True] * checklist_len, notes="ок")
    assert done["status"] == "done" and done["completed_at"]
    # повторное завершение — нельзя
    with pytest.raises(store.StoreError):
        store.complete_task(conn, task["id"], checklist=[True] * checklist_len)


def test_block_task(conn) -> None:
    order = _banner_order(conn)
    task = store.generate_production_plan(conn, order["id"])[0]
    blocked = store.block_task(conn, task["id"], reason="ждём материал")
    assert blocked["status"] == "blocked" and blocked["notes"] == "ждём материал"
    # из блокировки можно взять в работу
    started = store.start_task(conn, task["id"])
    assert started["status"] == "in_progress"


def test_production_progress(conn) -> None:
    order = _banner_order(conn)
    tasks = store.generate_production_plan(conn, order["id"])
    progress = store.production_progress(conn, order["id"])
    assert progress["total"] == len(tasks) and not progress["all_done"]
    for task in tasks:
        checklist_len = len(task["operation"]["checklist"])
        store.start_task(conn, task["id"])
        store.complete_task(conn, task["id"], checklist=[True] * checklist_len)
    assert store.production_progress(conn, order["id"])["all_done"] is True
    assert store.production_progress(conn, order["id"])["progress_percent"] == 100.0


# ---------- HTTP ----------


def test_production_over_http(client: ASGITestClient) -> None:
    order = client.post(
        "/api/orders",
        json={"status": "новый", "payment_method": "карта", "items": [{
            "kind": "calculator", "calculator_id": "wide",
            "params": {"width": 300, "height": 100, "qty": 1, "material": "Баннер 440",
                       "print": "Обычная печать", "mount": "Без монтажа",
                       "work_eyelets": True, "grommet_interval": 50,
                       "delivery": False, "install": False},
        }]},
    ).json()
    gen = client.post(f"/api/orders/{order['id']}/production/generate")
    assert gen.status_code == 201
    assert gen.json()["progress"]["total"] > 0

    tasks = client.get(f"/api/orders/{order['id']}/production").json()["tasks"]
    first = tasks[0]
    assert client.post(f"/api/production/tasks/{first['id']}/start").status_code == 200
    # неполный чек-лист → 400 по HTTP
    bad = client.post(f"/api/production/tasks/{first['id']}/complete", json={"checklist": []})
    assert bad.status_code == 400
    n = len(first["operation"]["checklist"])
    ok = client.post(f"/api/production/tasks/{first['id']}/complete", json={"checklist": [True] * n})
    assert ok.status_code == 200

    board = client.get("/api/production/tasks", params={"status": "pending"})
    assert board.status_code == 200
    # блокировка
    second = client.get(f"/api/orders/{order['id']}/production").json()["tasks"][1]
    block = client.post(f"/api/production/tasks/{second['id']}/block", json={"reason": "нет краски"})
    assert block.status_code == 200 and block.json()["status"] == "blocked"
