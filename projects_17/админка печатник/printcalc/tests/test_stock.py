"""Тесты Этапа 5 (роадмапа v6): склад — ledger, резерв/списание, план закупок.

Правила, которые проверяются здесь:
- движение — единственный источник истины (ledger): остаток = сумма движений;
- RESERVE не меняет физический остаток, только reserved (§19: estimated ≠ physical);
- CONSUME уменьшает physical; ADJUST задаёт physical напрямую (инвентаризация);
- резерв/списание заказа идут из consumption_json позиций (без ручного ввода);
- план закупок: Need = Required - Available - Reserved, округление до упаковки.
"""

from __future__ import annotations

import sqlite3

import pytest

from printcalc_web import store


@pytest.fixture()
def conn(tmp_path):
    from printcalc_web.db import connect

    connection = connect(tmp_path / "stock.db")
    store.seed_sections(connection)
    store.seed_operations(connection)  # для тестов 5b (план заданий)
    yield connection
    connection.close()


def _material(conn: sqlite3.Connection, **overrides) -> dict:
    fields = {
        "name": "Баннер 440г",
        "consumption_mode": "ROLL_NESTING",
        "base_unit": "m2",
        "roll_width": 3200.0,
        "min_stock": 5.0,
    }
    fields.update(overrides)
    return store.create_material(conn, fields=fields)


# ---------- математика остатков ----------


def test_empty_position_is_zero(conn: sqlite3.Connection) -> None:
    material = _material(conn)
    pos = store.stock_position(conn, material["id"])
    assert pos["physical"] == 0.0
    assert pos["reserved"] == 0.0
    assert pos["estimated"] == 0.0
    assert pos["unit"] == "m2"


def test_purchase_and_consume_change_physical_only(conn: sqlite3.Connection) -> None:
    material = _material(conn)
    store.record_stock_movement(conn, material_id=material["id"], kind="PURCHASE", quantity=50.0)
    pos = store.stock_position(conn, material["id"])
    assert pos["physical"] == 50.0
    assert pos["estimated"] == 50.0

    store.record_stock_movement(conn, material_id=material["id"], kind="CONSUME", quantity=12.5)
    pos = store.stock_position(conn, material["id"])
    assert pos["physical"] == 37.5
    assert pos["reserved"] == 0.0


def test_reserve_does_not_touch_physical(conn: sqlite3.Connection) -> None:
    """§19: резерв — расчётный, не физический приход."""
    material = _material(conn)
    store.record_stock_movement(conn, material_id=material["id"], kind="PURCHASE", quantity=50.0)
    store.record_stock_movement(conn, material_id=material["id"], kind="RESERVE", quantity=10.0)
    pos = store.stock_position(conn, material["id"])
    assert pos["physical"] == 50.0
    assert pos["reserved"] == 10.0
    assert pos["estimated"] == 40.0  # доступно для новых заказов

    store.record_stock_movement(conn, material_id=material["id"], kind="RELEASE", quantity=10.0)
    pos = store.stock_position(conn, material["id"])
    assert pos["reserved"] == 0.0
    assert pos["physical"] == 50.0


def test_adjust_sets_physical_to_counted(conn: sqlite3.Connection) -> None:
    """Инвентаризация: дельта = counted - physical записывается движением."""
    material = _material(conn)
    store.record_stock_movement(conn, material_id=material["id"], kind="PURCHASE", quantity=50.0)
    result = store.adjust_stock(conn, material["id"], counted_quantity=42.0)
    assert result["adjusted"] is True
    pos = store.stock_position(conn, material["id"])
    assert pos["physical"] == 42.0
    # идемпотентность: та же инвентаризация второй раз — без движения
    again = store.adjust_stock(conn, material["id"], counted_quantity=42.0)
    assert again["adjusted"] is False


def test_unknown_movement_kind_rejected(conn: sqlite3.Connection) -> None:
    """Закрытый словарь типов движений (ANTI-6b)."""
    material = _material(conn)
    with pytest.raises(store.StoreError, match="неизвестный тип движения"):
        store.record_stock_movement(conn, material_id=material["id"], kind="STOLEN", quantity=1.0)


# ---------- резерв/списание по заказу ----------


def _order_with_consumption(conn: sqlite3.Connection, material_id: int, area: float) -> int:
    order = store.create_order(
        conn, status="новый", payment_method="наличные",
        items=[{"kind": "manual", "name": "Заглушка", "price": 100, "qty": 1}],
    )
    conn.execute(
        "UPDATE order_items SET consumption_json = ? WHERE order_id = ?",
        (
            str('{"material_id": %d, "billing_unit": "m2", "production_area_m2": %f}' % (material_id, area)),
            order["id"],
        ),
    )
    conn.commit()
    return order["id"]


# ---------- Этап 5b: автосписание при завершении производства ----------


def _reserve_and_plan(conn: sqlite3.Connection, order_id: int) -> list[dict]:
    """Резерв заказа + план заданий (типовой путь: резерв кладёт оператор)."""
    store.reserve_order_materials(conn, order_id)
    return store.generate_production_plan(conn, order_id=order_id)


def test_auto_consume_when_all_tasks_done(conn: sqlite3.Connection) -> None:
    """5b: последний завершённый таск конвертирует резерв в списание."""
    material = _material(conn)
    store.record_stock_movement(conn, material_id=material["id"], kind="PURCHASE", quantity=100.0)
    order_id = _order_with_consumption(conn, material["id"], area=7.4)
    tasks = _reserve_and_plan(conn, order_id)
    assert len(tasks) >= 1

    # завершаем все задания кроме последнего — списания ещё нет
    for task in tasks[:-1]:
        store.start_task(conn, task["id"])
        required = task["operation"]["checklist"]
        store.complete_task(conn, task["id"], checklist=[True] * len(required))
    pos = store.stock_position(conn, material["id"])
    assert pos["physical"] == 100.0  # ещё держится резерв

    # последний таск — триггер автосписания
    last = tasks[-1]
    store.start_task(conn, last["id"])
    required = last["operation"]["checklist"]
    result = store.complete_task(conn, last["id"], checklist=[True] * len(required))
    auto = result["stock_auto_consume"]
    assert auto is not None
    assert len(auto["consumed"]) == 1
    assert auto["consumed"][0]["quantity"] == pytest.approx(7.4)
    pos = store.stock_position(conn, material["id"])
    assert pos["physical"] == pytest.approx(92.6)  # 100 − 7.4
    assert pos["reserved"] == 0.0


def test_no_auto_consume_until_all_done(conn: sqlite3.Connection) -> None:
    material = _material(conn)
    store.record_stock_movement(conn, material_id=material["id"], kind="PURCHASE", quantity=100.0)
    order_id = _order_with_consumption(conn, material["id"], area=5.0)
    tasks = _reserve_and_plan(conn, order_id)
    assert len(tasks) >= 2  # иначе тест не имеет смысла

    first = tasks[0]
    store.start_task(conn, first["id"])
    required = first["operation"]["checklist"]
    result = store.complete_task(conn, first["id"], checklist=[True] * len(required))
    assert result["stock_auto_consume"] is None
    pos = store.stock_position(conn, material["id"])
    assert pos["physical"] == 100.0
    assert pos["reserved"] == pytest.approx(5.0)


def test_auto_consume_without_reserve_still_consumes(conn: sqlite3.Connection) -> None:
    """Резерв забыли, но расход рассчитан сервером: при полном завершении
    производства материалы всё равно списываются (§20 MASTER)."""
    material = _material(conn)
    store.record_stock_movement(conn, material_id=material["id"], kind="PURCHASE", quantity=50.0)
    order_id = _order_with_consumption(conn, material["id"], area=3.0)
    tasks = store.generate_production_plan(conn, order_id=order_id)
    assert len(tasks) >= 1
    for task in tasks:
        store.start_task(conn, task["id"])
        required = task["operation"]["checklist"]
        result = store.complete_task(conn, task["id"], checklist=[True] * len(required))
    auto = result["stock_auto_consume"]
    assert auto is not None
    assert auto["consumed"][0]["quantity"] == pytest.approx(3.0)
    assert auto["released"] == []  # резерва не было
    pos = store.stock_position(conn, material["id"])
    assert pos["physical"] == pytest.approx(47.0)


def test_auto_consume_idempotent_on_retrigger(conn: sqlite3.Connection) -> None:
    """Повторный триггер (правка/повторный вызов) не дублирует списание."""
    material = _material(conn)
    store.record_stock_movement(conn, material_id=material["id"], kind="PURCHASE", quantity=100.0)
    order_id = _order_with_consumption(conn, material["id"], area=4.0)
    tasks = _reserve_and_plan(conn, order_id)
    for task in tasks[:-1]:
        store.start_task(conn, task["id"])
        required = task["operation"]["checklist"]
        store.complete_task(conn, task["id"], checklist=[True] * len(required))
    last = tasks[-1]
    store.start_task(conn, last["id"])
    required = last["operation"]["checklist"]
    first_result = store.complete_task(conn, last["id"], checklist=[True] * len(required))
    assert first_result["stock_auto_consume"] is not None

    # повторный вызов consume напрямую — StoreError; автосписание молча пропускается
    result = store._auto_consume_if_ready(conn, order_id)
    assert result is None
    pos = store.stock_position(conn, material["id"])
    assert pos["physical"] == pytest.approx(96.0)  # не списалось дважды


def test_reserve_order_from_consumption(conn: sqlite3.Connection) -> None:
    """§20: Production Consumption заказа -> RESERVE-движения."""
    material = _material(conn)
    store.record_stock_movement(conn, material_id=material["id"], kind="PURCHASE", quantity=100.0)
    order_id = _order_with_consumption(conn, material["id"], area=7.4)

    result = store.reserve_order_materials(conn, order_id)
    assert len(result["reserved"]) == 1
    pos = store.stock_position(conn, material["id"])
    assert pos["reserved"] == 7.4
    assert pos["physical"] == 100.0
    assert pos["estimated"] == 92.6

    # идемпотентность: повторный резерв запрещён
    with pytest.raises(store.StoreError, match="уже зарезервирован"):
        store.reserve_order_materials(conn, order_id)


def test_consume_converts_reserve(conn: sqlite3.Connection) -> None:
    """Списание: RESERVE конвертируется в CONSUME, physical уменьшается."""
    material = _material(conn)
    store.record_stock_movement(conn, material_id=material["id"], kind="PURCHASE", quantity=100.0)
    order_id = _order_with_consumption(conn, material["id"], area=7.4)
    store.reserve_order_materials(conn, order_id)

    result = store.consume_order_materials(conn, order_id)
    assert len(result["consumed"]) == 1
    pos = store.stock_position(conn, material["id"])
    assert pos["physical"] == 92.6
    assert pos["reserved"] == 0.0

    # повторное списание запрещено
    with pytest.raises(store.StoreError, match="уже списан"):
        store.consume_order_materials(conn, order_id)


def test_release_after_consume_blocked(conn: sqlite3.Connection) -> None:
    material = _material(conn)
    order_id = _order_with_consumption(conn, material["id"], area=7.4)
    store.reserve_order_materials(conn, order_id)
    store.consume_order_materials(conn, order_id)
    with pytest.raises(store.StoreError, match="невозможно"):
        store.release_order_materials(conn, order_id)


def test_reserve_without_consumption_rejected(conn: sqlite3.Connection) -> None:
    """Нет рассчитанного расхода — резервировать нечего (§20 без ручного ввода)."""
    order = store.create_order(
        conn, status="новый", payment_method="наличные",
        items=[{"kind": "manual", "name": "Заглушка", "price": 100, "qty": 1}],
    )
    with pytest.raises(store.StoreError, match="нечего"):
        store.reserve_order_materials(conn, order["id"])


# ---------- план закупок ----------


def test_purchase_plan_min_stock_triggers(conn: sqlite3.Connection) -> None:
    material = _material(conn, min_stock=10.0, pack_size=20.0)
    store.record_stock_movement(conn, material_id=material["id"], kind="PURCHASE", quantity=4.0)
    plan = store.purchase_plan(conn)
    assert len(plan) == 1
    row = plan[0]
    assert row["material_id"] == material["id"]
    assert row["deficit"] == pytest.approx(6.0)
    # 6 м2 -> округление вверх до упаковки 20
    assert row["recommendation"] == pytest.approx(20.0)
    assert row["rounded_to_pack"] is True


def test_purchase_plan_no_deficit_no_row(conn: sqlite3.Connection) -> None:
    material = _material(conn, min_stock=10.0)
    store.record_stock_movement(conn, material_id=material["id"], kind="PURCHASE", quantity=15.0)
    assert store.purchase_plan(conn) == []


def test_purchase_plan_with_external_required(conn: sqlite3.Connection) -> None:
    """Внешний спрос (план производства) учитывается: Need = Required - Available."""
    material = _material(conn, min_stock=0.0)
    store.record_stock_movement(conn, material_id=material["id"], kind="PURCHASE", quantity=5.0)
    plan = store.purchase_plan(conn, required={material["id"]: 12.0})
    assert len(plan) == 1
    assert plan[0]["deficit"] == pytest.approx(7.0)
    assert plan[0]["recommendation"] == pytest.approx(7.0)


def test_purchase_plan_accounts_reserved(conn: sqlite3.Connection) -> None:
    """Reserved уменьшает доступное: 50 куплено, 40 в резерве, min 20 -> дефицит 10."""
    material = _material(conn, min_stock=20.0)
    store.record_stock_movement(conn, material_id=material["id"], kind="PURCHASE", quantity=50.0)
    order_id = _order_with_consumption(conn, material["id"], area=40.0)
    store.reserve_order_materials(conn, order_id)
    plan = store.purchase_plan(conn)
    assert len(plan) == 1
    assert plan[0]["deficit"] == pytest.approx(10.0)


# ---------- HTTP-цикл ----------


def test_stock_http_cycle(tmp_path, conn: sqlite3.Connection) -> None:
    """HTTP-цикл: приёмка -> резерв -> списание -> план закупок через API."""
    from asgi_client import ASGITestClient

    from printcalc_web import create_app

    app = create_app(db_path=tmp_path / "stock_api.db")
    client = ASGITestClient(app)

    def position_by(material_id: int) -> dict:
        positions = client.get("/api/stock").json()["positions"]
        return next(p for p in positions if p["material_id"] == material_id)

    # материал
    response = client.post(
        "/api/materials",
        json={"name": "Плёнка белая", "consumption_mode": "ROLL_NESTING",
              "base_unit": "m2", "roll_width": 1500, "min_stock": 5, "pack_size": 30},
    )
    assert response.status_code == 201, response.text
    material_id = response.json()["id"]

    # приёмка закупки
    response = client.post(f"/api/materials/{material_id}/purchase", json={"quantity": 60.0})
    assert response.status_code == 201
    assert position_by(material_id)["physical"] == 60.0

    # заказ с расходом -> резерв -> списание
    order = client.post(
        "/api/orders",
        json={"status": "новый", "payment_method": "наличные",
              "items": [{"kind": "manual", "name": "Заглушка", "price": 100, "qty": 1}]},
    ).json()
    # UPDATE через то же соединение, что и приложение (та же БД!) — эмулирует
    # расход, посчитанный движком при сохранении заказа.
    from printcalc_web.db import connect as db_connect

    app_conn = db_connect(tmp_path / "stock_api.db")
    app_conn.execute(
        "UPDATE order_items SET consumption_json = ? WHERE order_id = ?",
        (f'{{"material_id": {material_id}, "billing_unit": "m2", "production_area_m2": 10.0}}', order["id"]),
    )
    app_conn.commit()
    app_conn.close()

    response = client.post(f"/api/orders/{order['id']}/materials/reserve")
    assert response.status_code == 201
    pos = position_by(material_id)
    assert pos["reserved"] == 10.0
    assert pos["estimated"] == 50.0

    response = client.post(f"/api/orders/{order['id']}/materials/consume")
    assert response.status_code == 200
    assert position_by(material_id)["physical"] == 50.0

    # инвентаризация через API
    response = client.post("/api/stock/adjust", params={"material_id": material_id}, json={"counted": 47.5})
    assert response.status_code == 200
    assert position_by(material_id)["physical"] == 47.5

    # план закупок: min 5, available 47.5 -> дефицита нет
    response = client.post("/api/stock/purchase-plan", json={"required": {}})
    assert response.status_code == 200
    assert response.json()["plan"] == []

    # лента движений
    kinds = [m["kind"] for m in client.get("/api/stock/movements").json()["movements"]]
    assert kinds[0] == "ADJUST"
    assert "PURCHASE" in kinds and "RESERVE" in kinds and "CONSUME" in kinds
