"""Репозитории Phase 1: прайс-каталог, заказы, настройки, отчёт.

Правила v3, зашитые здесь:
- счётчик использования растёт при СОХРАНЕНИИ заказа (идея №3 раздела 5а);
- позиция, добавленная «на лету», создаётся с unverified=1 (идея №4);
- ручная позиция без «сохранить в прайс» остаётся kind='manual',
  saved_to_catalog=0 и попадает в отчёт «мимо каталога» (идея №10);
- цены расчётных позиций пересчитываются сервером через движок —
  клиентская цена доверия не имеет (движок — единственный источник);
- fuzzy-подсказка «похожее уже есть» создание не блокирует (идея №8).
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from types import EllipsisType
from typing import Any, Mapping

import printcalc
from printcalc.engine.errors import CalcInputError, RegistryError
from printcalc.engine.registry import calculate
from printcalc_web import parser
from printcalc_web.calculators import get_registry

#: Статусы заказа Phase 1 (Р2). Хранение — TEXT; расширение набора в Phase 2
#: меняет только эту константу (CONFLICT-1 v3: совместимость с workflow).
ORDER_STATUSES: tuple[str, ...] = ("новый", "в работе", "выполнен", "завершён")

#: Способы оплаты (решение Q2 от 2026-09-07); редактируется без кода.
DEFAULT_PAYMENT_METHODS: tuple[str, ...] = ("наличные", "карта", "перевод")

#: Конструктор разделов (2026-09-08): закрытый словарь типов раздела (ANTI-6b).
SECTION_KINDS: tuple[str, ...] = ("text", "select", "checkbox", "number", "date")

#: Разделы по умолчанию (сид при первом запуске; пользователь меняет их свободно).
DEFAULT_SECTIONS: tuple[dict[str, Any], ...] = (
    {"title": "Пожелания заказчика", "kind": "textarea", "required": False, "options": []},
    {"title": "Срочность", "kind": "select", "required": False, "options": ["обычная", "к завтрашнему дню", "срочно"]},
    {"title": "Доставка", "kind": "select", "required": False, "options": ["самовывоз", "доставка", "доставка + монтаж"]},
)

_IMPORT_SEPARATOR = re.compile(r"\s+[-—–]\s+|\t")


class StoreError(Exception):
    """Ожидаемая ошибка бизнес-правил (маппится в HTTP 400)."""


def utc_now() -> str:
    """ISO-метка времени (UTC, секундная точность)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _price_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "price": row["price"],
        "unit": row["unit"],
        "category": row["category"],
        "synonyms": json.loads(row["synonyms"]),
        "usage_count": row["usage_count"],
        "unverified": bool(row["unverified"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


# ---------- настройки ----------


def get_payment_methods(conn: sqlite3.Connection) -> list[str]:
    """Способы оплаты: значение из settings или дефолт Q2."""
    row = conn.execute(
        "SELECT value FROM settings WHERE key = 'payment_methods'"
    ).fetchone()
    if row is None:
        return list(DEFAULT_PAYMENT_METHODS)
    return list(json.loads(row["value"]))


def set_payment_methods(conn: sqlite3.Connection, methods: list[str]) -> list[str]:
    """Сохраняет список способов оплаты. Raises StoreError при пустом списке."""
    cleaned = [method.strip() for method in methods if method.strip()]
    if not cleaned:
        raise StoreError("список способов оплаты пуст")
    conn.execute(
        "INSERT INTO settings (key, value) VALUES ('payment_methods', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (json.dumps(cleaned, ensure_ascii=False),),
    )
    conn.commit()
    return cleaned


# ---------- прайс-каталог ----------


def add_price_item(
    conn: sqlite3.Connection,
    *,
    name: str,
    price: float,
    unit: str | None = None,
    category: str | None = None,
) -> dict[str, Any]:
    """Создаёт позицию каталога (unverified=1 — идея №4). Дубликаты не блокируются (идея №8)."""
    clean_name = name.strip()
    if not clean_name:
        raise StoreError("название позиции не может быть пустым")
    if price < 0:
        raise StoreError("цена не может быть отрицательной")
    now = utc_now()
    cursor = conn.execute(
        "INSERT INTO price_list_items (name, price, unit, category, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (clean_name, float(price), unit, category, now, now),
    )
    conn.commit()
    lastrowid = cursor.lastrowid
    return get_price_item(conn, int(lastrowid if lastrowid is not None else 0))


def get_price_item(conn: sqlite3.Connection, item_id: int) -> dict[str, Any]:
    """Возвращает позицию каталога. Raises StoreError, если не найдена/архив."""
    row = conn.execute(
        "SELECT * FROM price_list_items WHERE id = ? AND archived = 0", (item_id,)
    ).fetchone()
    if row is None:
        raise StoreError(f"позиция прайса не найдена: id={item_id}")
    return _price_row_to_dict(row)


def list_price_items(
    conn: sqlite3.Connection,
    *,
    query: str | None = None,
    unverified: bool | None = None,
) -> list[dict[str, Any]]:
    """Список позиций: поиск по названию/категории, фильтр непроверенных."""
    sql = "SELECT * FROM price_list_items WHERE archived = 0"
    params: list[Any] = []
    if unverified is not None:
        sql += " AND unverified = ?"
        params.append(1 if unverified else 0)
    if query:
        like = f"%{query.lower()}%"
        sql += " AND (lower(name) LIKE ? OR lower(coalesce(category, '')) LIKE ?)"
        params += [like, like]
    sql += " ORDER BY usage_count DESC, name COLLATE NOCASE"
    return [_price_row_to_dict(row) for row in conn.execute(sql, params)]


_UPDATABLE_FIELDS = ("name", "price", "unit", "category", "unverified")


def update_price_item(
    conn: sqlite3.Connection, item_id: int, fields: Mapping[str, Any]
) -> dict[str, Any]:
    """Частично обновляет позицию. Synonyms передаётся списком строк."""
    updates: dict[str, Any] = {}
    for key in _UPDATABLE_FIELDS:
        if key in fields and fields[key] is not None:
            updates[key] = fields[key]
    if "unverified" in updates:
        updates["unverified"] = 1 if updates["unverified"] else 0
    if "price" in updates:
        if float(updates["price"]) < 0:
            raise StoreError("цена не может быть отрицательной")
        updates["price"] = float(updates["price"])
    if "name" in updates and not str(updates["name"]).strip():
        raise StoreError("название позиции не может быть пустым")
    if "synonyms" in fields and fields["synonyms"] is not None:
        updates["synonyms"] = json.dumps(
            [str(word).strip() for word in fields["synonyms"] if str(word).strip()],
            ensure_ascii=False,
        )
    if not updates:
        return get_price_item(conn, item_id)
    set_clause = ", ".join(f"{key} = ?" for key in updates)
    params = list(updates.values()) + [utc_now(), item_id]
    cursor = conn.execute(
        f"UPDATE price_list_items SET {set_clause}, updated_at = ? WHERE id = ?",
        params,
    )
    if cursor.rowcount == 0:
        raise StoreError(f"позиция прайса не найдена: id={item_id}")
    conn.commit()
    return get_price_item(conn, item_id)


def add_synonym(conn: sqlite3.Connection, item_id: int, word: str) -> dict[str, Any]:
    """Добавляет синоним позиции (идея №5). Идемпотентно, без дублей."""
    item = get_price_item(conn, item_id)
    clean = word.strip()
    known = {existing.lower() for existing in item["synonyms"]}
    known.add(item["name"].lower())
    if clean and clean.lower() not in known:
        synonyms = item["synonyms"] + [clean]
        conn.execute(
            "UPDATE price_list_items SET synonyms = ?, updated_at = ? WHERE id = ?",
            (json.dumps(synonyms, ensure_ascii=False), utc_now(), item_id),
        )
        conn.commit()
    return get_price_item(conn, item_id)


def find_similar(
    conn: sqlite3.Connection, name: str, *, limit: int = 5
) -> list[dict[str, Any]]:
    """Fuzzy-подсказка «похожее уже есть» (идея №8): подстрока + difflib."""
    target = name.strip().lower()
    if not target:
        return []
    scored: list[tuple[float, sqlite3.Row]] = []
    for row in conn.execute("SELECT * FROM price_list_items WHERE archived = 0"):
        known_name = row["name"].lower()
        ratio = difflib.SequenceMatcher(None, target, known_name).ratio()
        if target in known_name or known_name in target:
            ratio = max(ratio, 0.75)
        if ratio >= 0.6:
            synonyms = json.loads(row["synonyms"])
            for synonym in synonyms:
                if target == synonym.lower():
                    ratio = 1.0
                    break
        scored.append((ratio, row))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [_price_row_to_dict(row) for _, row in scored[:limit]]


def _parse_import_line(line: str) -> tuple[str, float] | None:
    parts = _IMPORT_SEPARATOR.split(line, maxsplit=1)
    if len(parts) != 2:
        return None
    name = parts[0].strip()
    raw_price = parts[1].strip().replace("₽", "").replace(",", ".").strip()
    try:
        price = float(raw_price)
    except ValueError:
        return None
    if not name or price < 0:
        return None
    return name, price


def import_price_items(conn: sqlite3.Connection, text: str) -> dict[str, Any]:
    """Массовый импорт «Название - Цена» построчно (идея №6).

    Разделители: « - », «—», «–», таб. Возвращает created + skipped с причинами.
    """
    created = 0
    skipped: list[dict[str, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parsed = _parse_import_line(line)
        if parsed is None:
            skipped.append(
                {
                    "line": line,
                    "reason": "не удалось разобрать (нужен формат «Название - Цена»)",
                }
            )
            continue
        name, price = parsed
        add_price_item(conn, name=name, price=price)
        created += 1
    return {"created": created, "skipped": skipped}


def export_price_items(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Строки для CSV-выгрузки каталога (идея №9), сортировка по названию."""
    rows = conn.execute(
        "SELECT * FROM price_list_items WHERE archived = 0 ORDER BY name COLLATE NOCASE"
    ).fetchall()
    return [_price_row_to_dict(row) for row in rows]


def increment_usage(conn: sqlite3.Connection, item_ids: list[int]) -> None:
    """Увеличивает счётчик использования (идея №3) — при сохранении заказа."""
    for item_id in set(item_ids):
        conn.execute(
            "UPDATE price_list_items SET usage_count = usage_count + 1 WHERE id = ?",
            (item_id,),
        )


# ---------- заказы ----------

#: Калькуляторы, для которых расход считается движком при сохранении (Этап 3).
#: Геометрия берётся из params (см → мм на границе движка).
CONSUMPTION_CALCULATORS: dict[str, dict[str, str]] = {
    # calculator_id → {ширина, высота, тираж} имена полей в params
    "wide": {"width": "width", "height": "height", "qty": "qty"},
    "tablichki": {"width": "width", "height": "height", "qty": "qty"},
}


def _row_to_engine_material(row: sqlite3.Row) -> Any:
    """Строка реестра материалов → доменная Material движка расхода."""
    from printcalc.engine.consumption.models import Material

    return Material(
        id=str(row["id"]),
        name=row["name"],
        category=row["category"],
        consumption_mode=row["consumption_mode"],
        base_unit=row["base_unit"],
        purchase_unit=row["purchase_unit"],
        roll_width=row["roll_width"],
        roll_length=row["roll_length"],
        sheet_width=row["sheet_width"],
        sheet_height=row["sheet_height"],
        purchase_price=row["purchase_cost"],
        price_unit=row["price_unit"],
        active=bool(row["active"]),
    )


def calculate_material_consumption(
    conn: sqlite3.Connection,
    *,
    material_id: int,
    width_cm: float,
    height_cm: float,
    quantity: float,
    policy_overrides: Mapping[str, Any] | None = None,
    roll_width_mm: float | None = None,
) -> dict[str, Any]:
    """Расход материала для изделия (Этап 3, ТЗ промт_4 §48).

    Материал и его режим — из реестра; политика — дефолты движка +
    overrides вызывающего (bleed/gap/margins). Вход в см (интерфейс
    оператора), движок получает мм. Результат — to_dict() движка
    (мм²→м² уже на границе, трассировка включена).

    roll_width_mm (правило владельца 2026-09-09): ручная ширина загруженного
    рулона (1 м / 1.5 м / 3 м плоттер…) — перекрывает значение реестра,
    потому что фактическая ширина известна оператору «на месте».
    """
    from printcalc.engine.consumption.engine import ConsumptionEngine
    from printcalc.engine.consumption.errors import ConsumptionError
    from printcalc.engine.consumption.models import Material, MaterialConsumptionPolicy

    row = conn.execute("SELECT * FROM materials WHERE id = ?", (material_id,)).fetchone()
    if row is None:
        raise StoreError(f"материал {material_id} не найден")
    material = _row_to_engine_material(row)
    if roll_width_mm is not None:
        if isinstance(roll_width_mm, bool) or not isinstance(roll_width_mm, (int, float)) or roll_width_mm <= 0:
            raise StoreError("roll_width_mm должен быть положительным числом")
        material = Material(
            id=material.id,
            name=material.name,
            category=material.category,
            consumption_mode=material.consumption_mode,
            base_unit=material.base_unit,
            purchase_unit=material.purchase_unit,
            roll_width=float(roll_width_mm),  # ручной рулон вместо реестра
            roll_length=material.roll_length,
            sheet_width=material.sheet_width,
            sheet_height=material.sheet_height,
            purchase_price=material.purchase_price,
            price_unit=material.price_unit,
            active=material.active,
        )

    for name, value in (("width_cm", width_cm), ("height_cm", height_cm), ("quantity", quantity)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            raise StoreError(f"{name} должен быть положительным числом")

    engine = ConsumptionEngine()
    policy = MaterialConsumptionPolicy(
        material_id=material.id,
        mode=material.consumption_mode,
        **dict(policy_overrides or {}),
    )
    try:
        result = engine.calculate(
            material,
            {
                "width": width_cm * 10.0,  # см → мм
                "height": height_cm * 10.0,
                "quantity": float(quantity),
            },
            policy,
        )
    except ConsumptionError as exc:
        # Стабильный машинный код наружу (§38): ROLL_WIDTH_TOO_SMALL, PRODUCT_DOES_NOT_FIT…
        raise StoreError(f"[{exc.code}] {exc.message}") from None
    except ValueError as exc:
        raise StoreError(str(exc)) from None
    return result.to_dict()


def _consumption_for_calculator_item(
    conn: sqlite3.Connection, calculator_id: str, params: Mapping[str, Any]
) -> dict[str, Any] | None:
    """Расход для расчётной позиции (Этап 3) или None, если не применим.

    Материал выбирается по имени из params (legacy-поле material),
    резолвится через реестр материалов (алиасы, BR-W1). Материал не найден
    или у калькулятора нет геометрии — расход просто не записывается
    (цена заказа от этого не зависит).
    """
    geometry = CONSUMPTION_CALCULATORS.get(calculator_id)
    if geometry is None:
        return None
    material_name = params.get("material")
    if not isinstance(material_name, str) or not material_name.strip():
        return None
    width = params.get(geometry["width"])
    height = params.get(geometry["height"])
    qty = params.get(geometry["qty"], 1)
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 for v in (width, height, qty)):
        return None
    material = find_material_by_name(conn, material_name)
    if material is None:
        return None
    assert width is not None and height is not None and qty is not None  # проверено выше
    # Ручной рулон из params (поле спеки wide); Таблички его не имеют — None.
    roll_width_mm = params.get("roll_width_mm")
    if not isinstance(roll_width_mm, (int, float)) or isinstance(roll_width_mm, bool) or roll_width_mm <= 0:
        roll_width_mm = None
    try:
        return calculate_material_consumption(
            conn,
            material_id=material["id"],
            width_cm=float(width),
            height_cm=float(height),
            quantity=float(qty),
            roll_width_mm=roll_width_mm,
        )
    except StoreError:
        # Не блокируем приём заказа из-за расхода (например, материал без
        # roll_width) — цена уже посчитана калькулятором; расход можно
        # досчитать вручную через /api/consumption/calculate.
        return None



def _segment_of(raw: Mapping[str, Any]) -> int | None:
    """Сегмент мультизаказа (парсер v2) из черновика; вне [0..999] → None."""
    value = raw.get("segment_id")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    ivalue = int(value)
    return ivalue if 0 <= ivalue <= 999 else None

def _resolve_item(
    conn: sqlite3.Connection, raw: Mapping[str, Any], position: int
) -> dict[str, Any]:
    """Приводит позицию черновика к хранимой: цены — только с сервера."""
    kind = raw.get("kind")
    qty = raw.get("qty", 1)
    if not isinstance(qty, (int, float)) or isinstance(qty, bool) or qty <= 0:
        raise StoreError("количество должно быть положительным числом")

    if kind == "price_list":
        item_id = raw.get("price_list_item_id")
        if not isinstance(item_id, int):
            raise StoreError("для позиции из каталога нужен price_list_item_id")
        item = get_price_item(conn, item_id)
        return {
            "kind": "price_list",
            "name": item["name"],
            "price": round(float(item["price"]), 2),
            "qty": float(qty),
            "calculator_id": None,
            "params_json": None,
            "price_list_item_id": item["id"],
            "saved_to_catalog": 1,
            "position": position,
            "segment_id": _segment_of(raw),
            "consumption": None,
        }

    if kind == "calculator":
        calculator_id = raw.get("calculator_id")
        if not calculator_id:
            raise StoreError("для расчётной позиции нужен calculator_id")
        params = raw.get("params") or {}
        try:
            result = calculate(get_registry(), str(calculator_id), params)
        except CalcInputError as exc:
            raise StoreError(f"{exc.field}: {exc.message}") from None
        except RegistryError:
            raise StoreError(f"неизвестный калькулятор: '{calculator_id}'") from None
        title = get_registry().get(str(calculator_id)).spec.title
        consumption = _consumption_for_calculator_item(conn, str(calculator_id), params)
        return {
            "kind": "calculator",
            "name": title,
            "price": round(result.price, 2),
            "qty": 1.0,
            "calculator_id": str(calculator_id),
            "params_json": json.dumps(params, ensure_ascii=False),
            "price_list_item_id": None,
            "saved_to_catalog": 1,
            "position": position,
            "segment_id": _segment_of(raw),
            "consumption": consumption,
        }

    if kind == "manual":
        name = str(raw.get("name") or "").strip()
        price = raw.get("price")
        if not name or price is None:
            raise StoreError("для ручной позиции нужны название и цена")
        if float(price) < 0:
            raise StoreError("цена не может быть отрицательной")
        if bool(raw.get("save_to_catalog", True)):
            created = add_price_item(conn, name=name, price=float(price))
            return {
                "kind": "price_list",
                "name": name,
                "price": round(float(price), 2),
                "qty": float(qty),
                "calculator_id": None,
                "params_json": None,
                "price_list_item_id": created["id"],
                "saved_to_catalog": 1,
                "position": position,
                "segment_id": _segment_of(raw),
            }
        return {
            "kind": "manual",
            "name": name,
            "price": round(float(price), 2),
            "qty": float(qty),
            "calculator_id": None,
            "params_json": None,
            "price_list_item_id": None,
            "saved_to_catalog": 0,
            "position": position,
            "segment_id": _segment_of(raw),
            "consumption": None,
        }

    raise StoreError(f"неизвестный тип позиции: '{kind}'")


def create_order(
    conn: sqlite3.Connection,
    *,
    status: str,
    payment_method: str,
    items: list[Mapping[str, Any]],
    wishes: str = "",
    section_values: Mapping[str, str | None] | None = None,
    client_id: int | None = None,
) -> dict[str, Any]:
    """Создаёт заказ: резолв позиций, сумма, счётчики использования."""
    if status not in ORDER_STATUSES:
        raise StoreError(
            f"недопустимый статус: '{status}' (допустимо: {', '.join(ORDER_STATUSES)})"
        )
    if payment_method not in get_payment_methods(conn):
        raise StoreError(f"недопустимый способ оплаты: '{payment_method}'")
    if not items:
        raise StoreError("заказ без позиций сохранить нельзя")
    if client_id is not None and get_client(conn, client_id) is None:
        raise StoreError(f"клиент {client_id} не найден")

    now = utc_now()
    resolved = [_resolve_item(conn, raw, index) for index, raw in enumerate(items)]
    total = round(sum(item["price"] * item["qty"] for item in resolved), 2)

    cursor = conn.execute(
        "INSERT INTO orders (status, payment_method, total, client_id, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (status, payment_method, total, client_id, now, now),
    )
    lastrowid = cursor.lastrowid
    order_id = int(lastrowid if lastrowid is not None else 0)
    for item in resolved:
        conn.execute(
        "INSERT INTO order_items (order_id, kind, name, price, qty, calculator_id,"
        " params_json, price_list_item_id, saved_to_catalog, position, consumption_json,"
        " segment_id)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            order_id,
            item["kind"],
            item["name"],
            item["price"],
            item["qty"],
            item["calculator_id"],
            item["params_json"],
            item["price_list_item_id"],
            item["saved_to_catalog"],
            item["position"],
            json.dumps(item["consumption"], ensure_ascii=False) if item.get("consumption") else None,
            # Сегмент мультизаказа (парсер v2): int из черновика либо NULL.
            int(item["segment_id"]) if item.get("segment_id") is not None else None,
        ),
        )
    increment_usage(conn, [i["price_list_item_id"] for i in resolved if i["price_list_item_id"]])
    conn.execute("UPDATE orders SET wishes = ? WHERE id = ?", (wishes.strip(), order_id))
    if section_values:
        set_order_sections(conn, order_id, section_values)
    conn.commit()
    return get_order(conn, order_id)


def _order_row_to_dict(
    conn: sqlite3.Connection, row: sqlite3.Row, item_rows: list[sqlite3.Row]
) -> dict[str, Any]:
    """Собирает словарь заказа; item_rows — уже отсортированные позиции."""
    order: dict[str, Any] = {
        "id": row["id"],
        "status": row["status"],
        "payment_method": row["payment_method"],
        "total": row["total"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "wishes": row["wishes"] if "wishes" in row.keys() else "",
        "client_id": row["client_id"] if "client_id" in row.keys() else None,
        "estimate_id": row["estimate_id"] if "estimate_id" in row.keys() else None,
        "client_name": _client_name_for_order(conn, row),
        "items": [
            {
                "kind": item["kind"],
                "name": item["name"],
                "price": item["price"],
                "qty": item["qty"],
                "calculator_id": item["calculator_id"],
                "params": json.loads(item["params_json"]) if item["params_json"] else None,
                "price_list_item_id": item["price_list_item_id"],
                "saved_to_catalog": bool(item["saved_to_catalog"]),
                "segment_id": (
                    item["segment_id"] if "segment_id" in item.keys() else None
                ),
                "consumption": (
                    json.loads(item["consumption_json"]) if item["consumption_json"] else None
                ),
            }
            for item in item_rows
        ],
    }
    return order


def list_orders(
    conn: sqlite3.Connection, *, status: str | None = None
) -> list[dict[str, Any]]:
    """Список заказов (краткий), фильтр по статусу (Р5б: история заказов)."""
    if status is not None and status not in ORDER_STATUSES:
        raise StoreError(f"недопустимый статус: '{status}'")
    sql = (
        "SELECT o.*, COUNT(i.id) AS items_count FROM orders o"
        " LEFT JOIN order_items i ON i.order_id = o.id"
    )
    params: list[Any] = []
    if status is not None:
        sql += " WHERE o.status = ?"
        params.append(status)
    sql += " GROUP BY o.id ORDER BY o.id DESC"
    return [
        {
            "id": row["id"],
            "status": row["status"],
            "payment_method": row["payment_method"],
            "total": row["total"],
            "created_at": row["created_at"],
            "items_count": row["items_count"],
            "client_id": row["client_id"] if "client_id" in row.keys() else None,
            "estimate_id": row["estimate_id"] if "estimate_id" in row.keys() else None,
            "client_name": _client_name_for_order(conn, row),
        }
        for row in conn.execute(sql, params)
    ]


def _client_name_for_order(conn: sqlite3.Connection, row: sqlite3.Row) -> str | None:
    """Имя клиента заказа (для списков без JOIN на стороне вызывающего кода)."""
    if "client_id" not in row.keys() or row["client_id"] is None:
        return None
    client = get_client(conn, int(row["client_id"]))
    return client["name"] if client else None


def get_order(conn: sqlite3.Connection, order_id: int) -> dict[str, Any]:
    """Полный заказ с позициями. Raises StoreError, если не найден."""
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if row is None:
        raise StoreError(f"заказ не найден: id={order_id}")
    item_rows = conn.execute(
        "SELECT * FROM order_items WHERE order_id = ? ORDER BY position", (order_id,)
    ).fetchall()
    return _order_row_to_dict(conn, row, item_rows)


def update_order(
    conn: sqlite3.Connection,
    order_id: int,
    *,
    status: str | None = None,
    payment_method: str | None = None,
    wishes: str | None = None,
) -> dict[str, Any]:
    """Меняет статус/оплату/пожелания (состав заказа после «Добавить» закрыт)."""
    get_order(conn, order_id)
    if status is not None:
        if status not in ORDER_STATUSES:
            raise StoreError(
                f"недопустимый статус: '{status}' (допустимо: {', '.join(ORDER_STATUSES)})"
            )
        conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    if payment_method is not None:
        if payment_method not in get_payment_methods(conn):
            raise StoreError(f"недопустимый способ оплаты: '{payment_method}'")
        conn.execute(
            "UPDATE orders SET payment_method = ? WHERE id = ?", (payment_method, order_id)
        )
    if wishes is not None:
        conn.execute("UPDATE orders SET wishes = ? WHERE id = ?", (wishes.strip(), order_id))
    conn.execute("UPDATE orders SET updated_at = ? WHERE id = ?", (utc_now(), order_id))
    conn.commit()
    return get_order(conn, order_id)


# ---------- конструктор разделов заказа ----------


def _section_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "kind": row["kind"],
        "required": bool(row["required"]),
        "options": json.loads(row["options_json"]),
        "position": row["position"],
        "archived": bool(row["archived"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def seed_sections(conn: sqlite3.Connection) -> None:
    """Сид разделов по умолчанию (идемпотентно): только если таблица пуста."""
    count = conn.execute("SELECT COUNT(*) FROM ui_sections").fetchone()[0]
    if count:
        return
    now = utc_now()
    for position, section in enumerate(DEFAULT_SECTIONS):
        conn.execute(
            "INSERT INTO ui_sections (title, kind, required, options_json, position, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                section["title"],
                section["kind"],
                int(section["required"]),
                json.dumps(section["options"], ensure_ascii=False),
                position,
                now,
                now,
            ),
        )
    conn.commit()


def list_sections(
    conn: sqlite3.Connection, *, include_archived: bool = False
) -> list[dict[str, Any]]:
    """Разделы главного экрана по позиции (архив — по флагу)."""
    sql = "SELECT * FROM ui_sections"
    if not include_archived:
        sql += " WHERE archived = 0"
    sql += " ORDER BY position, id"
    return [_section_row_to_dict(row) for row in conn.execute(sql)]


def add_section(
    conn: sqlite3.Connection,
    *,
    title: str,
    kind: str,
    required: bool = False,
    options: list[str] | None = None,
) -> dict[str, Any]:
    """Новый раздел конструктора. kind — закрытый словарь SECTION_KINDS."""
    clean_title = title.strip()
    if not clean_title:
        raise StoreError("название раздела не может быть пустым")
    if kind not in SECTION_KINDS:
        raise StoreError(
            f"недопустимый тип раздела: '{kind}' (допустимо: {', '.join(SECTION_KINDS)})"
        )
    clean_options = [option.strip() for option in (options or []) if option.strip()]
    if kind == "select" and not clean_options:
        raise StoreError("для типа select нужен список вариантов")
    max_pos = conn.execute(
        "SELECT COALESCE(MAX(position), -1) FROM ui_sections"
    ).fetchone()[0]
    now = utc_now()
    cursor = conn.execute(
        "INSERT INTO ui_sections (title, kind, required, options_json, position, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (clean_title, kind, int(required), json.dumps(clean_options, ensure_ascii=False), int(max_pos) + 1, now, now),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM ui_sections WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _section_row_to_dict(row)


def update_section(
    conn: sqlite3.Connection,
    section_id: int,
    *,
    title: str | None = None,
    kind: str | None = None,
    required: bool | None = None,
    options: list[str] | None = None,
    archived: bool | None = None,
) -> dict[str, Any]:
    """Правка/архивирование раздела (Additive: ничего не удаляем физически)."""
    row = conn.execute("SELECT * FROM ui_sections WHERE id = ?", (section_id,)).fetchone()
    if row is None:
        raise StoreError(f"раздел не найден: id={section_id}")
    new_title = title.strip() if title is not None else row["title"]
    if not new_title:
        raise StoreError("название раздела не может быть пустым")
    new_kind = kind if kind is not None else row["kind"]
    if new_kind not in SECTION_KINDS:
        raise StoreError(
            f"недопустимый тип раздела: '{new_kind}' (допустимо: {', '.join(SECTION_KINDS)})"
        )
    new_options = (
        [option.strip() for option in options if option.strip()] if options is not None else json.loads(row["options_json"])
    )
    if new_kind == "select" and not new_options:
        raise StoreError("для типа select нужен список вариантов")
    new_required = int(required) if required is not None else row["required"]
    new_archived = int(archived) if archived is not None else row["archived"]
    conn.execute(
        "UPDATE ui_sections SET title = ?, kind = ?, required = ?, options_json = ?,"
        " archived = ?, updated_at = ? WHERE id = ?",
        (new_title, new_kind, new_required, json.dumps(new_options, ensure_ascii=False), new_archived, utc_now(), section_id),
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM ui_sections WHERE id = ?", (section_id,)).fetchone()
    return _section_row_to_dict(updated)


def reorder_sections(conn: sqlite3.Connection, ordered_ids: list[int]) -> list[dict[str, Any]]:
    """Пересортировка разделов: полный порядок идентификаторов обязателен."""
    existing = {row["id"] for row in conn.execute("SELECT id FROM ui_sections WHERE archived = 0")}
    if set(ordered_ids) != existing or len(ordered_ids) != len(existing):
        raise StoreError("список reorder должен содержать все активные разделы ровно один раз")
    for position, section_id in enumerate(ordered_ids):
        conn.execute(
            "UPDATE ui_sections SET position = ?, updated_at = ? WHERE id = ?",
            (position, utc_now(), section_id),
        )
    conn.commit()
    return list_sections(conn)


def set_order_sections(
    conn: sqlite3.Connection,
    order_id: int,
    values: Mapping[str, str | None],
) -> None:
    """Сохраняет значения разделов заказа. Ключ — id раздела (строкой).

    Значение None/'' для необязательного раздела = пусто; для required-раздела
    пустое значение — StoreError (правило: обязательное — значит обязательное).
    """
    get_order(conn, order_id)
    sections = {str(section["id"]): section for section in list_sections(conn)}
    for section_id, raw in values.items():
        if section_id not in sections:
            raise StoreError(f"неизвестный раздел: id={section_id}")
        section = sections[section_id]
        value = "" if raw is None else str(raw).strip()
        if section["required"] and not value:
            raise StoreError(f"раздел «{section['title']}» обязателен")
        if section["kind"] == "select" and value and value not in section["options"]:
            raise StoreError(
                f"значение «{value}» не входит в варианты раздела «{section['title']}»"
            )
        conn.execute(
            "INSERT INTO order_section_values (order_id, section_id, value) VALUES (?, ?, ?)"
            " ON CONFLICT(order_id, section_id) DO UPDATE SET value = excluded.value",
            (order_id, int(section_id), value),
        )
    conn.commit()


def get_order_sections(conn: sqlite3.Connection, order_id: int) -> list[dict[str, Any]]:
    """Значения разделов заказа вместе с метаданными раздела (для UI/экспорта)."""
    rows = conn.execute(
        "SELECT s.id, s.title, s.kind, s.required, s.position, v.value"
        " FROM ui_sections s"
        " LEFT JOIN order_section_values v ON v.section_id = s.id AND v.order_id = ?"
        " WHERE s.archived = 0 ORDER BY s.position, s.id",
        (order_id,),
    ).fetchall()
    return [
        {
            "section_id": row["id"],
            "title": row["title"],
            "kind": row["kind"],
            "required": bool(row["required"]),
            "value": row["value"] if row["value"] is not None else "",
        }
        for row in rows
    ]


def off_catalog_report(
    conn: sqlite3.Connection,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict[str, Any]]:
    """Отчёт «мимо каталога» (идея №10): ручные позиции без сохранения в прайс.

    date_from/date_to — даты YYYY-MM-DD (включительно), сравнение по
    первым 10 символам ISO-метки created_at.
    """
    sql = (
        "SELECT o.id AS order_id, o.created_at, o.status, i.name, i.price, i.qty"
        " FROM order_items i JOIN orders o ON o.id = i.order_id"
        " WHERE i.saved_to_catalog = 0"
    )
    params: list[Any] = []
    if date_from:
        sql += " AND substr(o.created_at, 1, 10) >= ?"
        params.append(date_from)
    if date_to:
        sql += " AND substr(o.created_at, 1, 10) <= ?"
        params.append(date_to)
    sql += " ORDER BY o.id DESC"
    return [
        {
            "order_id": row["order_id"],
            "created_at": row["created_at"],
            "status": row["status"],
            "name": row["name"],
            "price": row["price"],
            "qty": row["qty"],
        }
        for row in conn.execute(sql, params)
    ]


# ---------- клиенты и контакты (Этап 1, §6 промт_4) ----------

#: Закрытый словарь каналов контактов (ANTI-6b); расширение — новой редакцией.
CONTACT_CHANNELS: tuple[str, ...] = (
    "phone",
    "telegram",
    "vk",
    "max",
    "email",
    "web",
)

#: Закрытый словарь типов клиента.
CLIENT_KINDS: tuple[str, ...] = ("физлицо", "компания")


def _client_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "kind": row["kind"],
        "note": row["note"],
        "archived": bool(row["archived"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _contact_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "client_id": row["client_id"],
        "channel": row["channel"],
        "value": row["value"],
        "created_at": row["created_at"],
    }


def create_client(
    conn: sqlite3.Connection,
    *,
    name: str,
    kind: str = "физлицо",
    note: str = "",
) -> dict[str, Any]:
    """Создаёт клиента. Raises StoreError при пустом имени/неизвестном типе."""
    if not name.strip():
        raise StoreError("имя клиента не может быть пустым")
    if kind not in CLIENT_KINDS:
        raise StoreError(f"неизвестный тип клиента: {kind} (допустимо: {CLIENT_KINDS})")
    now = utc_now()
    cursor = conn.execute(
        "INSERT INTO clients (name, kind, note, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (name.strip(), kind, note, now, now),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM clients WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _client_row_to_dict(row)


def get_client(conn: sqlite3.Connection, client_id: int) -> dict[str, Any] | None:
    """Клиент по id (включая архив) или None."""
    row = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
    return _client_row_to_dict(row) if row else None


def list_clients(
    conn: sqlite3.Connection, *, query: str | None = None, include_archived: bool = False
) -> list[dict[str, Any]]:
    """Список клиентов; query ищет по имени и значению контактов (глобальный поиск)."""
    if query:
        like = f"%{query.strip()}%"
        rows = conn.execute(
            """
            SELECT DISTINCT c.* FROM clients c
            LEFT JOIN contacts ct ON ct.client_id = c.id
            WHERE (c.name LIKE ? OR ct.value LIKE ?) AND (? OR c.archived = 0)
            ORDER BY c.name
            """,
            (like, like, include_archived),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM clients WHERE (? OR archived = 0) ORDER BY name",
            (include_archived,),
        ).fetchall()
    return [_client_row_to_dict(row) for row in rows]


def update_client(
    conn: sqlite3.Connection,
    client_id: int,
    *,
    name: str | None = None,
    kind: str | None = None,
    note: str | None = None,
    archived: bool | None = None,
) -> dict[str, Any]:
    """Частичная правка клиента. Raises StoreError если не найден."""
    current = get_client(conn, client_id)
    if current is None:
        raise StoreError(f"клиент {client_id} не найден")
    if name is not None and not name.strip():
        raise StoreError("имя клиента не может быть пустым")
    if kind is not None and kind not in CLIENT_KINDS:
        raise StoreError(f"неизвестный тип клиента: {kind}")
    fields: list[str] = []
    params: list[Any] = []
    for column, value in (
        ("name", name.strip() if name is not None else None),
        ("kind", kind),
        ("note", note),
        ("archived", int(archived) if archived is not None else None),
    ):
        if value is not None:
            fields.append(f"{column} = ?")
            params.append(value)
    if fields:
        fields.append("updated_at = ?")
        params.append(utc_now())
        params.append(client_id)
        conn.execute(f"UPDATE clients SET {', '.join(fields)} WHERE id = ?", params)
        conn.commit()
    result = get_client(conn, client_id)
    assert result is not None  # проверено выше
    return result


def add_contact(
    conn: sqlite3.Connection, client_id: int, *, channel: str, value: str
) -> dict[str, Any]:
    """Добавляет контакт клиенту. Raises StoreError: клиент/канал/дубль."""
    if get_client(conn, client_id) is None:
        raise StoreError(f"клиент {client_id} не найден")
    if channel not in CONTACT_CHANNELS:
        raise StoreError(f"неизвестный канал: {channel} (допустимо: {CONTACT_CHANNELS})")
    if not value.strip():
        raise StoreError("значение контакта не может быть пустым")
    now = utc_now()
    try:
        cursor = conn.execute(
            "INSERT INTO contacts (client_id, channel, value, created_at) VALUES (?, ?, ?, ?)",
            (client_id, channel, value.strip(), now),
        )
    except sqlite3.IntegrityError as exc:
        raise StoreError(f"контакт {channel}:{value} уже существует") from exc
    conn.commit()
    row = conn.execute("SELECT * FROM contacts WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _contact_row_to_dict(row)


def list_contacts(conn: sqlite3.Connection, client_id: int) -> list[dict[str, Any]]:
    """Контакты клиента (все каналы)."""
    rows = conn.execute(
        "SELECT * FROM contacts WHERE client_id = ? ORDER BY channel, value", (client_id,)
    ).fetchall()
    return [_contact_row_to_dict(row) for row in rows]


def delete_contact(conn: sqlite3.Connection, contact_id: int) -> None:
    """Удаляет контакт (сам контакт, не клиента). Raises StoreError если нет."""
    cursor = conn.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
    if cursor.rowcount == 0:
        raise StoreError(f"контакт {contact_id} не найден")
    conn.commit()


def find_client_by_contact(
    conn: sqlite3.Connection, *, channel: str, value: str
) -> dict[str, Any] | None:
    """Поиск клиента по контакту — основа client matching (§45 промт_4)."""
    row = conn.execute(
        "SELECT c.* FROM clients c JOIN contacts ct ON ct.client_id = c.id "
        "WHERE ct.channel = ? AND ct.value = ?",
        (channel, value.strip()),
    ).fetchone()
    return _client_row_to_dict(row) if row else None


def assign_order_client(
    conn: sqlite3.Connection, order_id: int, client_id: int | None
) -> dict[str, Any]:
    """Привязывает клиента к заказу (None — отвязать). Raises StoreError."""
    if client_id is not None and get_client(conn, client_id) is None:
        raise StoreError(f"клиент {client_id} не найден")
    row = conn.execute("SELECT id FROM orders WHERE id = ?", (order_id,)).fetchone()
    if row is None:
        raise StoreError(f"заказ {order_id} не найден")
    conn.execute(
        "UPDATE orders SET client_id = ?, updated_at = ? WHERE id = ?",
        (client_id, utc_now(), order_id),
    )
    conn.commit()
    return get_order(conn, order_id)  # type: ignore[return-value]


# ---------- реестр материалов (Этап 1, §18 промт_4) ----------

#: Закрытые словари material registry (ANTI-6b; совместимы с consumption engine).
MATERIAL_MODES: tuple[str, ...] = (
    "AREA",
    "LINEAR",
    "SHEET",
    "PIECE",
    "ROLL_NESTING",
    "SHEET_NESTING",
    "COUNT",
    "CUSTOM",
)
MATERIAL_UNITS: tuple[str, ...] = ("m2", "lm", "mm", "шт", "лист")


def _material_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "aliases": json.loads(row["aliases_json"]),
        "category": row["category"],
        "consumption_mode": row["consumption_mode"],
        "base_unit": row["base_unit"],
        "purchase_unit": row["purchase_unit"],
        "purchase_cost": row["purchase_cost"],
        "price_unit": row["price_unit"],
        "roll_width": row["roll_width"],
        "roll_length": row["roll_length"],
        "sheet_width": row["sheet_width"],
        "sheet_height": row["sheet_height"],
        "min_stock": row["min_stock"],
        "supplier": row["supplier"],
        "pack_size": row["pack_size"],
        "active": bool(row["active"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def create_material(conn: sqlite3.Connection, *, fields: dict[str, Any]) -> dict[str, Any]:
    """Создаёт материал. Raises StoreError: пустое имя/дубль/неизвестные словари."""
    name = str(fields.get("name", "")).strip()
    if not name:
        raise StoreError("название материала не может быть пустым")
    mode = fields.get("consumption_mode", "AREA")
    if mode not in MATERIAL_MODES:
        raise StoreError(f"неизвестный режим расхода: {mode}")
    base_unit = fields.get("base_unit", "m2")
    if base_unit not in MATERIAL_UNITS:
        raise StoreError(f"неизвестная единица: {base_unit}")
    purchase_cost = float(fields.get("purchase_cost", 0.0))
    if purchase_cost < 0:
        raise StoreError("закупочная цена не может быть отрицательной")
    aliases = list(fields.get("aliases", []))
    if name in aliases or len(set(aliases)) != len(aliases):
        raise StoreError("алиасы не должны содержать имя или дублироваться")
    roll_width = fields.get("roll_width")
    if mode == "ROLL_NESTING" and (roll_width is None or float(roll_width) <= 0):
        raise StoreError("рулонный материал требует положительную ширину рулона")
    now = utc_now()
    try:
        cursor = conn.execute(
            """
            INSERT INTO materials (name, aliases_json, category, consumption_mode,
                base_unit, purchase_unit, purchase_cost, price_unit, roll_width,
                roll_length, sheet_width, sheet_height, min_stock, supplier,
                pack_size, active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                json.dumps(aliases, ensure_ascii=False),
                fields.get("category", "general"),
                mode,
                base_unit,
                fields.get("purchase_unit", base_unit),
                purchase_cost,
                fields.get("price_unit", base_unit),
                roll_width,
                fields.get("roll_length"),
                fields.get("sheet_width"),
                fields.get("sheet_height"),
                float(fields.get("min_stock", 0.0)),
                fields.get("supplier"),
                fields.get("pack_size"),
                int(fields.get("active", True)),
                now,
                now,
            ),
        )
    except sqlite3.IntegrityError as exc:
        raise StoreError(f"материал «{name}» уже существует") from exc
    conn.commit()
    row = conn.execute("SELECT * FROM materials WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _material_row_to_dict(row)


def get_material(conn: sqlite3.Connection, material_id: int) -> dict[str, Any] | None:
    """Материал по id или None."""
    row = conn.execute("SELECT * FROM materials WHERE id = ?", (material_id,)).fetchone()
    return _material_row_to_dict(row) if row else None


def list_materials(
    conn: sqlite3.Connection, *, active_only: bool = False, category: str | None = None
) -> list[dict[str, Any]]:
    """Список материалов (опционально только активные / по категории)."""
    sql = "SELECT * FROM materials WHERE (? OR active = 1)"
    params: list[Any] = [not active_only]
    if category:
        sql += " AND category = ?"
        params.append(category)
    sql += " ORDER BY name"
    return [_material_row_to_dict(row) for row in conn.execute(sql, params)]


def find_material_by_name(
    conn: sqlite3.Connection, name: str
) -> dict[str, Any] | None:
    """Поиск по имени ИЛИ алиасу — защита от дрейфа словаря (BR-W1)."""
    row = conn.execute("SELECT * FROM materials WHERE name = ?", (name,)).fetchone()
    if row:
        return _material_row_to_dict(row)
    rows = conn.execute(
        "SELECT * FROM materials WHERE active = 1", ()
    ).fetchall()
    for candidate in rows:
        if name in json.loads(candidate["aliases_json"]):
            return _material_row_to_dict(candidate)
    return None


def update_material(
    conn: sqlite3.Connection, material_id: int, *, fields: dict[str, Any]
) -> dict[str, Any]:
    """Частичная правка материала. Raises StoreError: не найден/недопустимые значения."""
    current = get_material(conn, material_id)
    if current is None:
        raise StoreError(f"материал {material_id} не найден")
    allowed = {
        "name", "aliases", "category", "consumption_mode", "base_unit",
        "purchase_unit", "purchase_cost", "price_unit", "roll_width",
        "roll_length", "sheet_width", "sheet_height", "min_stock",
        "supplier", "pack_size", "active",
    }
    unknown = set(fields) - allowed
    if unknown:
        raise StoreError(f"неизвестные поля материала: {sorted(unknown)}")
    if "consumption_mode" in fields and fields["consumption_mode"] not in MATERIAL_MODES:
        raise StoreError(f"неизвестный режим расхода: {fields['consumption_mode']}")
    if "base_unit" in fields and fields["base_unit"] not in MATERIAL_UNITS:
        raise StoreError(f"неизвестная единица: {fields['base_unit']}")
    if "purchase_cost" in fields and float(fields["purchase_cost"]) < 0:
        raise StoreError("закупочная цена не может быть отрицательной")
    if "pack_size" in fields and fields["pack_size"] is not None and float(fields["pack_size"]) <= 0:
        raise StoreError("размер упаковки должен быть положительным")
    if "name" in fields and not str(fields["name"]).strip():
        raise StoreError("название материала не может быть пустым")
    new_mode = fields.get("consumption_mode", current["consumption_mode"])
    new_roll = fields.get("roll_width", current["roll_width"])
    if new_mode == "ROLL_NESTING" and (new_roll is None or float(new_roll) <= 0):
        raise StoreError("рулонный материал требует положительную ширину рулона")

    assignments: list[str] = []
    params: list[Any] = []
    column_values: dict[str, Any] = dict(fields)
    if "aliases" in column_values:
        column_values["aliases_json"] = json.dumps(
            list(column_values.pop("aliases")), ensure_ascii=False
        )
    if "active" in column_values:
        column_values["active"] = int(column_values["active"])
    for column, value in column_values.items():
        assignments.append(f"{column} = ?")
        params.append(value)
    assignments.append("updated_at = ?")
    params.append(utc_now())
    params.append(material_id)
    try:
        conn.execute(f"UPDATE materials SET {', '.join(assignments)} WHERE id = ?", params)
        conn.commit()
    except sqlite3.IntegrityError as exc:
        raise StoreError(f"материал «{fields.get('name')}» уже существует") from exc
    result = get_material(conn, material_id)
    assert result is not None
    return result


# ---------- сид канонических материалов (Этап 1+: деплой) ----------

#: Канонические материалы Wide из frozen-конфига (calculators/wide/config.py):
#: только закупочные цены НЕ известны из legacy (там sell-пары) — цена закупки
#: UNKNOWN, поэтому 0 и помечается владельцем при первом заполнении реестра.
CANONICAL_WIDE_MATERIALS: tuple[dict[str, Any], ...] = (
    {
        "name": "Баннер 440г",
        "aliases": ["Баннер 440", "Баннер (обычный)"],
        "category": "wide",
        "consumption_mode": "ROLL_NESTING",
        "base_unit": "m2",
        "purchase_unit": "m2",
        "price_unit": "m2",
        "roll_width": 1000.0,
    },
    {
        "name": "Баннер 510г",
        "aliases": ["Баннер 510"],
        "category": "wide",
        "consumption_mode": "ROLL_NESTING",
        "base_unit": "m2",
        "purchase_unit": "m2",
        "price_unit": "m2",
        "roll_width": 1000.0,
    },
    {
        "name": "Плёнка самоклеящаяся",
        "aliases": ["Самоклеящаяся", "Самоклейка", "Плёнка"],
        "category": "wide",
        "consumption_mode": "ROLL_NESTING",
        "base_unit": "m2",
        "purchase_unit": "m2",
        "price_unit": "m2",
        "roll_width": 1520.0,
    },
    {
        "name": "Холст",
        "aliases": ["Холст печатный"],
        "category": "wide",
        "consumption_mode": "ROLL_NESTING",
        "base_unit": "m2",
        "purchase_unit": "m2",
        "price_unit": "m2",
        "roll_width": 1100.0,
    },
    # S1 (решение Дениса 2026-09-12, PHASE_RULES_R0_REPORT §6.3): бэклит —
    # реальный материал производства (universal_calc.py: «Бэклит» 260 ₽/м²
    # cost_unit на Roland VP540/SJ645; TERMS_GLOSSARY S-01; прайсы района:
    # «баннер/пленка/сетка/бэклит/бумага/флаги» — research/03_price_lists.csv).
    # Рулонная, как остальные wide-материалы; ширина рулона 1520 мм —
    # ВНИМАНИЕ: в документации проекта ширина НЕ зафиксирована, значение
    # помечено для подтверждения владельцем при первом заполнении реестра
    # (как закупочные цены сидов Этапа 1).
    {
        "name": "Бэклит",
        "aliases": ["беклит", "Backlit"],
        "category": "wide",
        "consumption_mode": "ROLL_NESTING",
        "base_unit": "m2",
        "purchase_unit": "m2",
        "price_unit": "m2",
        "roll_width": 1520.0,
    },
)

#: Канонические материалы Табличек (листовые заготовки — SHEET-режим).
CANONICAL_TABLICHKI_MATERIALS: tuple[dict[str, Any], ...] = (
    # Листовые заготовки: стандартный лист 3000×2000 мм (Этап 3b — SHEET_NESTING).
    {"name": "ПВХ 3 мм", "aliases": ["ПВХ"], "category": "tablichki", "consumption_mode": "SHEET", "base_unit": "m2", "sheet_width": 3000.0, "sheet_height": 2000.0},
    {"name": "ПВХ 5 мм", "aliases": [], "category": "tablichki", "consumption_mode": "SHEET", "base_unit": "m2", "sheet_width": 3000.0, "sheet_height": 2000.0},
    {"name": "Акрил 3 мм", "aliases": ["Оргстекло 3 мм"], "category": "tablichki", "consumption_mode": "SHEET", "base_unit": "m2", "sheet_width": 3000.0, "sheet_height": 2000.0},
    {"name": "Акрил 5 мм", "aliases": [], "category": "tablichki", "consumption_mode": "SHEET", "base_unit": "m2", "sheet_width": 3000.0, "sheet_height": 2000.0},
    {"name": "Композит 3 мм", "aliases": [], "category": "tablichki", "consumption_mode": "SHEET", "base_unit": "m2", "sheet_width": 3000.0, "sheet_height": 2000.0},
    {"name": "Композит 5 мм", "aliases": [], "category": "tablichki", "consumption_mode": "SHEET", "base_unit": "m2", "sheet_width": 3000.0, "sheet_height": 2000.0},
)


# ---------- кассовые услуги P0 (RESEARCH_ADOPTION_PLAN §5-Б, блок B) ----------


def seed_p0_services(conn: sqlite3.Connection) -> dict[str, int]:
    """Идемпотентный сид кассовых услуг P0 из исследования (p0_services.py).

    Ключ идемпотентности — точное имя. Существующие позиции НЕ изменяются:
    цены — собственность владельца, сид только дополняет каталог.
    Синонимы добавляются идемпотентно (add_synonym). unverified=0 — это
    канонические значения исследования, но владелец может править цену.
    """
    from printcalc_web.p0_services import P0_SERVICES

    created = 0
    skipped = 0
    for spec in P0_SERVICES:
        row = conn.execute(
            "SELECT id FROM price_list_items WHERE lower(name) = lower(?) AND archived = 0",
            (spec["name"],),
        ).fetchone()
        if row is None:
            item = add_price_item(
                conn,
                name=spec["name"],
                price=spec["price"],
                unit=spec["unit"],
                category=spec["category"],
            )
            conn.execute(
                "UPDATE price_list_items SET unverified = 0 WHERE id = ?", (item["id"],)
            )
            for word in spec["synonyms"]:
                add_synonym(conn, item["id"], word)
            created += 1
        else:
            # Синонимы досыпаем даже существующим (словарь растёт аддитивно).
            item = _price_row_to_dict(
                conn.execute(
                    "SELECT * FROM price_list_items WHERE id = ?", (row["id"],)
                ).fetchone()
            )
            known = {s.lower() for s in item["synonyms"]}
            for word in spec["synonyms"]:
                if word.lower() not in known and word.lower() != item["name"].lower():
                    add_synonym(conn, item["id"], word)
            skipped += 1
    conn.commit()
    return {"created": created, "skipped": skipped}


def price_template_csv(conn: sqlite3.Connection) -> str:
    """Прайс-шаблон с разделами (вертикальная иерархия) для round-trip.

    Формат Excel-RU: разделитель «;», UTF-8 BOM (добавляет caller).
    Строки разделов: «# РАЗДЕЛ» (пропускаются импортом, служат визуальной
    иерархией в Excel). Строки позиций:
    «Название;Цена;Ед;Синонимы (через |)» — импорт обновляет цену
    существующей позиции по имени, добавляет новую, если имени нет.
    """
    items = export_price_items(conn)
    by_category: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        category = item["category"] or "9. БЕЗ РАЗДЕЛА"
        by_category.setdefault(category, []).append(item)

    lines: list[str] = [
        "# Прайс-лист Печатникъ — правьте ЦЕНУ и добавляйте позиции;",
        "# разделы (строки #) не редактировать; синонимы — через |;",
        "# сохранить CSV (UTF-8) и загрузить через «Импортировать».",
        "Название;Цена;Ед;Синонимы",
    ]
    for category in sorted(by_category):
        lines.append(f"# {category}")
        for item in by_category[category]:
            price = f"{item['price']:.2f}".rstrip("0").rstrip(".")
            lines.append(
                f"{item['name']};{price};{item['unit'] or ''};"
                + " | ".join(item["synonyms"])
            )
    return "\n".join(lines) + "\n"


def _parse_template_line(line: str) -> tuple[str, float, str, list[str]] | None:
    """«Название;Цена;Ед;Синонимы» → кортеж; None для разделов/мусора."""
    if line.startswith("#") or line.lower().startswith("название;"):
        return None
    parts = [p.strip() for p in line.split(";")]
    if len(parts) < 2 or not parts[0]:
        return None
    try:
        price = float(parts[1].replace("₽", "").replace(",", "."))
    except ValueError:
        return None
    if price < 0:
        return None
    synonyms = [s for s in (parts[3].split("|") if len(parts) > 3 else []) if s.strip()]
    return parts[0], price, (parts[2] if len(parts) > 2 else ""), synonyms


def import_price_template(conn: sqlite3.Connection, text: str) -> dict[str, Any]:
    """Импорт прайс-шаблона round-trip: обновить цены, добавить новое.

    Отличие от import_price_items (формат «Название - Цена»): здесь
    «;»-формат с синонимами, существующие позиции находятся по имени
    (case-insensitive) и получают новую ЦЕНУ (и единицу/синонимы, если
    заданы), новые — создаются. Возвращает счётчики.
    """
    updated = 0
    created = 0
    skipped: list[dict[str, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parsed = _parse_template_line(line)
        if parsed is None:
            continue
        name, price, unit, synonyms = parsed
        row = conn.execute(
            "SELECT id FROM price_list_items WHERE lower(name) = lower(?) AND archived = 0",
            (name,),
        ).fetchone()
        if row is not None:
            update_price_item(
                conn, int(row["id"]), {"price": price, **({"unit": unit} if unit else {})}
            )
            item_id = int(row["id"])
            updated += 1
        else:
            item = add_price_item(conn, name=name, price=price, unit=unit or None)
            item_id = item["id"]
            created += 1
        for word in synonyms:
            add_synonym(conn, item_id, word)
    return {"created": created, "updated": updated, "skipped": skipped}


def seed_materials(conn: sqlite3.Connection) -> dict[str, int]:
    """Идемпотентный сид канонических материалов (дух seed_sections).

    Ключ идемпотентности — точное имя материала. Существующие не изменяются
    (владелец мог поправить закупочную цену). Возвращает счётчики.
    """
    created = 0
    skipped = 0
    for fields in CANONICAL_WIDE_MATERIALS + CANONICAL_TABLICHKI_MATERIALS:
        if find_material_by_name(conn, fields["name"]) is not None:
            skipped += 1
            continue
        create_material(conn, fields=fields)
        created += 1
    conn.commit()
    return {"created": created, "skipped": skipped}


# ---------- сметы (Этап 2 роадмапа v6, §22/§24/§49 промт_4) ----------

#: Статусы сметы (§24): закрытый словарь (ANTI-6b). Терминальные —
#: accepted / rejected / expired; из draft разрешён переход в sent.
ESTIMATE_STATUSES: tuple[str, ...] = (
    "draft",
    "sent",
    "viewed",
    "accepted",
    "rejected",
    "expired",
)

#: Разрешённые переходы статусов сметы (§24). Всё, что не указано — запрещено.
ESTIMATE_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "draft": ("sent", "accepted", "rejected", "expired"),
    "sent": ("viewed", "accepted", "rejected", "expired"),
    "viewed": ("accepted", "rejected", "expired"),
    "accepted": (),
    "rejected": (),
    "expired": (),
}


def _estimate_row_to_dict(
    conn: sqlite3.Connection, row: sqlite3.Row, item_rows: list[sqlite3.Row]
) -> dict[str, Any]:
    estimate: dict[str, Any] = {
        "id": row["id"],
        "status": row["status"],
        "total": row["total"],
        "client_id": row["client_id"],
        "client_name": _client_name_for_order(conn, row),
        "note": row["note"],
        "valid_until": row["valid_until"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "items": [
            {
                "kind": item["kind"],
                "name": item["name"],
                "price": item["price"],
                "qty": item["qty"],
                "calculator_id": item["calculator_id"],
                "params": json.loads(item["params_json"]) if item["params_json"] else None,
                "price_list_item_id": item["price_list_item_id"],
            }
            for item in item_rows
        ],
    }
    snapshot = conn.execute(
        "SELECT * FROM calc_snapshots WHERE estimate_id = ?", (row["id"],)
    ).fetchone()
    estimate["snapshot"] = _snapshot_row_to_dict(snapshot) if snapshot else None
    return estimate


def _snapshot_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "engine_version": row["engine_version"],
        "registry_checksum": row["registry_checksum"],
        "catalog_checksum": row["catalog_checksum"],
        "policy_version": row["policy_version"],
        "details": json.loads(row["details_json"]),
        "created_at": row["created_at"],
    }


def _catalog_checksum(conn: sqlite3.Connection) -> str:
    """Стабильная подпись прайс-каталога (id, цена, количество активных позиций)."""
    rows = conn.execute(
        "SELECT id, price, unit FROM price_list_items WHERE archived = 0 ORDER BY id"
    ).fetchall()
    payload = json.dumps(
        [[row["id"], row["price"], row["unit"]] for row in rows],
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _registry_checksum() -> str:
    """Подпись реестра калькуляторов: id + версия спеки + поля (детерминированно)."""
    registry = get_registry()
    payload = json.dumps(
        {
            calculator_id: {
                "version": reg.spec.version,
                "fields": [
                    [f.name, f.kind.value, f.required] for f in reg.spec.fields
                ],
            }
            for calculator_id, reg in ((cid, registry.get(cid)) for cid in registry.ids())
        },
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def create_estimate(
    conn: sqlite3.Connection,
    *,
    items: list[Mapping[str, Any]],
    client_id: int | None = None,
    note: str = "",
    valid_until: str | None = None,
) -> dict[str, Any]:
    """Создаёт смету из позиций (§22): Client, Items, Note, Validity.

    Позиции резолвятся тем же _resolve_item, что и заказы: цены — только
    с сервера (каталог/движок); клиентская цена доверия не имеет.
    """
    if not items:
        raise StoreError("смета без позиций не имеет смысла")
    if client_id is not None and get_client(conn, client_id) is None:
        raise StoreError(f"клиент {client_id} не найден")
    if valid_until is not None:
        try:
            datetime.fromisoformat(valid_until)
        except ValueError:
            raise StoreError(f"некорректная дата valid_until: '{valid_until}'") from None

    now = utc_now()
    resolved = [_resolve_item(conn, raw, index) for index, raw in enumerate(items)]
    total = round(sum(item["price"] * item["qty"] for item in resolved), 2)

    cursor = conn.execute(
        "INSERT INTO estimates (status, total, client_id, note, valid_until, created_at, updated_at)"
        " VALUES ('draft', ?, ?, ?, ?, ?, ?)",
        (total, client_id, note.strip(), valid_until, now, now),
    )
    estimate_id = int(cursor.lastrowid if cursor.lastrowid is not None else 0)
    for item in resolved:
        conn.execute(
            "INSERT INTO estimate_items (estimate_id, kind, name, price, qty, calculator_id,"
            " params_json, price_list_item_id, position)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                estimate_id,
                item["kind"],
                item["name"],
                item["price"],
                item["qty"],
                item["calculator_id"],
                item["params_json"],
                item["price_list_item_id"],
                item["position"],
            ),
        )
    conn.commit()
    return get_estimate(conn, estimate_id)


def get_estimate(conn: sqlite3.Connection, estimate_id: int) -> dict[str, Any]:
    """Смета целиком (позиции + snapshot, если есть)."""
    row = conn.execute("SELECT * FROM estimates WHERE id = ?", (estimate_id,)).fetchone()
    if row is None:
        raise StoreError(f"смета не найдена: id={estimate_id}")
    item_rows = conn.execute(
        "SELECT * FROM estimate_items WHERE estimate_id = ? ORDER BY position, id",
        (estimate_id,),
    ).fetchall()
    return _estimate_row_to_dict(conn, row, list(item_rows))


def list_estimates(
    conn: sqlite3.Connection, *, status: str | None = None, client_id: int | None = None
) -> list[dict[str, Any]]:
    """Список смет (краткий), фильтры по статусу и клиенту."""
    if status is not None and status not in ESTIMATE_STATUSES:
        raise StoreError(f"недопустимый статус сметы: '{status}'")
    sql = (
        "SELECT e.*, COUNT(i.id) AS items_count FROM estimates e"
        " LEFT JOIN estimate_items i ON i.estimate_id = e.id"
    )
    params: list[Any] = []
    where: list[str] = []
    if status is not None:
        where.append("e.status = ?")
        params.append(status)
    if client_id is not None:
        where.append("e.client_id = ?")
        params.append(client_id)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " GROUP BY e.id ORDER BY e.id DESC"
    return [
        {
            "id": row["id"],
            "status": row["status"],
            "total": row["total"],
            "client_id": row["client_id"],
            "client_name": _client_name_for_order(conn, row),
            "valid_until": row["valid_until"],
            "created_at": row["created_at"],
            "items_count": row["items_count"],
        }
        for row in conn.execute(sql, params)
    ]


def update_estimate(
    conn: sqlite3.Connection,
    estimate_id: int,
    *,
    note: str | None = None,
    valid_until: str | None = None,
    client_id: int | None = ...,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Правка meta-полей сметы (только пока не ACCEPTED — §49)."""
    estimate = get_estimate(conn, estimate_id)
    if estimate["status"] == "accepted":
        raise StoreError("принятая смета неизменяема (§49: snapshot запрещает правку задним числом)")
    sets: list[str] = []
    params: list[Any] = []
    if client_id is not ...:
        if client_id is not None and get_client(conn, client_id) is None:
            raise StoreError(f"клиент {client_id} не найден")
        sets.append("client_id = ?")
        params.append(client_id)
    if note is not None:
        sets.append("note = ?")
        params.append(note.strip())
    if valid_until is not None:
        try:
            datetime.fromisoformat(valid_until)
        except ValueError:
            raise StoreError(f"некорректная дата valid_until: '{valid_until}'") from None
        sets.append("valid_until = ?")
        params.append(valid_until)
    if sets:
        params.append(utc_now())
        params.append(estimate_id)
        conn.execute(
            f"UPDATE estimates SET {', '.join(sets)}, updated_at = ? WHERE id = ?", params
        )
        conn.commit()
    return get_estimate(conn, estimate_id)


def transition_estimate(
    conn: sqlite3.Connection, estimate_id: int, new_status: str
) -> dict[str, Any]:
    """Перевод сметы по статусам (§24). В accepted фиксирует snapshot (§49).

    Переход в rejected/expired разрешён из любого активного статуса —
    клиент может отказать или «передумать» на любом шаге.
    """
    if new_status not in ESTIMATE_STATUSES:
        raise StoreError(f"недопустимый статус сметы: '{new_status}'")
    row = conn.execute("SELECT status FROM estimates WHERE id = ?", (estimate_id,)).fetchone()
    if row is None:
        raise StoreError(f"смета не найдена: id={estimate_id}")
    current = row["status"]
    if current == new_status:
        return get_estimate(conn, estimate_id)
    if new_status not in ESTIMATE_TRANSITIONS[current]:
        raise StoreError(f"переход '{current}' → '{new_status}' запрещён")
    if new_status == "accepted":
        return accept_estimate(conn, estimate_id)
    conn.execute(
        "UPDATE estimates SET status = ?, updated_at = ? WHERE id = ?",
        (new_status, utc_now(), estimate_id),
    )
    conn.commit()
    return get_estimate(conn, estimate_id)


def accept_estimate(conn: sqlite3.Connection, estimate_id: int) -> dict[str, Any]:
    """Принимает смету: статус accepted + snapshot версий (§49)."""
    estimate = get_estimate(conn, estimate_id)
    if estimate["status"] == "accepted":
        return estimate  # идемпотентно: повторный accept ничего не меняет
    if estimate["status"] not in ("draft", "sent", "viewed"):
        raise StoreError(f"смета в статусе '{estimate['status']}' не может быть принята")
    now = utc_now()
    conn.execute(
        "INSERT INTO calc_snapshots (estimate_id, engine_version, registry_checksum,"
        " catalog_checksum, policy_version, details_json, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            estimate_id,
            printcalc.__version__,
            _registry_checksum(),
            _catalog_checksum(conn),
            "v1",
            json.dumps(
                {
                    "total": estimate["total"],
                    "items": [
                        {"name": i["name"], "price": i["price"], "qty": i["qty"]}
                        for i in estimate["items"]
                    ],
                },
                ensure_ascii=False,
            ),
            now,
        ),
    )
    conn.execute(
        "UPDATE estimates SET status = 'accepted', updated_at = ? WHERE id = ?",
        (now, estimate_id),
    )
    conn.commit()
    return get_estimate(conn, estimate_id)


def create_order_from_estimate(
    conn: sqlite3.Connection,
    estimate_id: int,
    *,
    payment_method: str,
    status: str = "новый",
) -> dict[str, Any]:
    """Заказ из сметы (§9 промт_4): все поля переносятся, ручного ввода нет.

    Цены берутся из сохранённых позиций сметы БЕЗ пересчёта — смета уже
    согласована с клиентом; изменение цен в каталоге задним числом
    не влияет на принятую смету (§49). Повторный вызов запрещён:
    одна смета — один заказ (идемпотентность по estimate_id).
    """
    estimate = get_estimate(conn, estimate_id)
    if estimate["status"] != "accepted":
        raise StoreError(
            f"заказ можно создать только из принятой сметы (сейчас: '{estimate['status']}')"
        )
    existing = conn.execute(
        "SELECT id FROM orders WHERE estimate_id = ?", (estimate_id,)
    ).fetchone()
    if existing is not None:
        raise StoreError(f"заказ из сметы {estimate_id} уже создан (заказ {existing['id']})")

    now = utc_now()
    cursor = conn.execute(
        "INSERT INTO orders (status, payment_method, total, client_id, estimate_id,"
        " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            status,
            payment_method,
            estimate["total"],
            estimate["client_id"],
            estimate_id,
            now,
            now,
        ),
    )
    order_id = int(cursor.lastrowid if cursor.lastrowid is not None else 0)
    for position, item in enumerate(estimate["items"]):
        conn.execute(
            "INSERT INTO order_items (order_id, kind, name, price, qty, calculator_id,"
            " params_json, price_list_item_id, saved_to_catalog, position, consumption_json)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                order_id,
                item["kind"],
                item["name"],
                item["price"],
                item["qty"],
                item["calculator_id"],
                json.dumps(item["params"], ensure_ascii=False) if item["params"] else None,
                item["price_list_item_id"],
                0 if item["kind"] == "manual" else 1,
                position,
                None,  # расход сметы не копируется: пересчитается при заказе, если применим
            ),
        )
    conn.commit()
    return get_order(conn, order_id)


# ---------- производство (Этап 4 роадмапа v6, OPERATIONS_CATALOG) ----------

#: Статусы производственного задания (закрытый словарь, ANTI-6b).
TASK_STATUSES: tuple[str, ...] = ("pending", "in_progress", "done", "blocked")

#: Стартовый каталог операций (OPERATIONS_CATALOG §2, стартовый скелет).
#: trigger: 'always' | 'wide' | 'tablichki' | 'riso' | flag-имя доп. работы.
DEFAULT_OPERATIONS: tuple[dict[str, Any], ...] = (
    {"code": "OP-01", "name": "Проверить макет", "description": "Размер, вылеты, разрешение, цвет",
     "steps": ["Открыть макет", "Сверить размер с заказом", "Проверить разрешение и цвет"],
     "checklist": ["размер соответствует заказу", "разрешение достаточное", "цвет CMYK"],
     "equipment": "графический редактор", "minutes": 10, "trigger": "always", "position": 1},
    {"code": "OP-02", "name": "Подготовить файл к печати", "description": "Масштаб 1:1, CMYK, текст в кривые",
     "steps": ["Масштабировать 1:1", "Перевести в CMYK", "Текст в кривые"],
     "checklist": ["размер = заказ", "текст в кривых", "файл открывается после экспорта"],
     "equipment": "CorelDRAW/PS/AI", "minutes": 15, "trigger": "always", "position": 2},
    {"code": "OP-04", "name": "Напечатать (широкоформат)", "description": "Печать баннеров/плёнки/холста",
     "steps": ["Заложить материал", "Отправить файл на печать", "Контроль качества печати"],
     "checklist": ["цвет совпадает с макетом", "нет полос и артефактов"],
     "equipment": "Roland VP540/SJ645", "minutes": 40, "trigger": "wide", "position": 3},
    {"code": "OP-07", "name": "УФ-печать на жёстком", "description": "Печать на ПВХ/акриле/композите",
     "steps": ["Закрепить лист", "Отправить задание", "Контроль печати"],
     "checklist": ["изображение ровное", "краска закреплена"],
     "equipment": "УФ-принтер", "minutes": 35, "trigger": "tablichki", "position": 3},
    {"code": "OP-05", "name": "Напечатать (ризограф)", "description": "Мастера, краска, приладка",
     "steps": ["Установить мастер", "Приладка", "Печать тиража"],
     "checklist": ["приладка по контрольному листу", "тираж полный"],
     "equipment": "RISO RZ300EP", "minutes": 30, "trigger": "riso", "position": 3},
    {"code": "OP-09", "name": "Резать/подрезать", "description": "Гильотина/резак",
     "steps": ["Разметить", "Резать", "Проверить размеры"],
     "checklist": ["размеры по заказу", "края ровные"],
     "equipment": "гильотина/резак", "minutes": 15, "trigger": "always", "position": 4},
    {"code": "OP-08", "name": "Ламинировать", "description": "Ламинация отпечатка",
     "steps": ["Прогреть ламинатор", "Пропустить отпечаток", "Контроль пузырей"],
     "checklist": ["без пузырей", "края запечатаны"],
     "equipment": "Bulros FM650A", "minutes": 15, "trigger": "work_laminate_mount", "position": 5},
    {"code": "OP-13", "name": "Установить люверсы", "description": "Пробивка и фиксация колец по краю",
     "steps": ["Разметить шаг", "Пробить отверстия", "Установить кольца"],
     "checklist": ["шаг равномерный", "кольца не прокручиваются", "край не порван"],
     "equipment": "пуансон/пресс", "minutes": 20, "trigger": "work_eyelets", "position": 5},
    {"code": "OP-14", "name": "Загибка / карман", "description": "Загибка краёв, карман под трубку",
     "steps": ["Разметить линию загиба", "Прошить/проклеить"],
     "checklist": ["загиб ровный", "карман нужной ширины"],
     "equipment": "швейная машина/лента", "minutes": 20, "trigger": "work_hemming", "position": 5},
    {"code": "OP-19", "name": "Монтаж на объекте", "description": "Установка на месте (высотные работы)",
     "steps": ["Подготовить крепёж", "Смонтировать", "Убрать за собой"],
     "checklist": ["установлено по уровню", "надёжно закреплено"],
     "equipment": "лестница/вышка, дюбели", "minutes": 60, "trigger": "install", "position": 8},
    {"code": "OP-20", "name": "Контроль качества", "description": "Проверка изделия по чек-листу заказа",
     "steps": ["Сверить с заказом", "Осмотреть изделие"],
     "checklist": ["комплектность по заказу", "нет дефектов", "размеры сходятся"],
     "equipment": "", "minutes": 10, "trigger": "always", "position": 6},
    {"code": "OP-21", "name": "Упаковать и выдать", "description": "Упаковка и передача клиенту",
     "steps": ["Упаковать", "Оформить выдачу"],
     "checklist": ["упаковка целая", "клиент предупреждён о правилах хранения"],
     "equipment": "", "minutes": 5, "trigger": "always", "position": 7},
)


def seed_operations(conn: sqlite3.Connection) -> dict[str, int]:
    """Идемпотентный сид каталога операций (ключ — code)."""
    created = 0
    skipped = 0
    now = utc_now()
    for op in DEFAULT_OPERATIONS:
        exists = conn.execute(
            "SELECT 1 FROM operations WHERE code = ?", (op["code"],)
        ).fetchone()
        if exists:
            skipped += 1
            continue
        conn.execute(
            "INSERT INTO operations (code, name, description, steps_json, checklist_json,"
            " equipment, minutes, role, trigger, position, enabled, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
            (
                op["code"],
                op["name"],
                op.get("description", ""),
                json.dumps(op.get("steps", []), ensure_ascii=False),
                json.dumps(op.get("checklist", []), ensure_ascii=False),
                op.get("equipment", ""),
                int(op.get("minutes", 0)),
                op.get("role", "производство"),
                op["trigger"],
                int(op.get("position", 0)),
                now,
                now,
            ),
        )
        created += 1
    conn.commit()
    return {"created": created, "skipped": skipped}


def _operation_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "code": row["code"],
        "name": row["name"],
        "description": row["description"],
        "steps": json.loads(row["steps_json"]),
        "checklist": json.loads(row["checklist_json"]),
        "equipment": row["equipment"],
        "minutes": row["minutes"],
        "role": row["role"],
        "trigger": row["trigger"],
        "position": row["position"],
        "enabled": bool(row["enabled"]),
    }


def list_operations(
    conn: sqlite3.Connection, *, enabled_only: bool = False
) -> list[dict[str, Any]]:
    """Каталог операций (§1 OPERATIONS_CATALOG) — источник правил и UI."""
    sql = "SELECT * FROM operations"
    if enabled_only:
        sql += " WHERE enabled = 1"
    sql += " ORDER BY position, code"
    return [_operation_row_to_dict(row) for row in conn.execute(sql)]


def _triggers_for_order(
    conn: sqlite3.Connection, items: list[dict[str, Any]]
) -> set[str]:
    """Набор триггеров заказа (§3 каталога): калькуляторы + доп-работы + флаги."""
    triggers: set[str] = set()
    for item in items:
        calculator_id = item.get("calculator_id")
        if calculator_id:
            triggers.add(str(calculator_id))
        params = item.get("params") or {}
        for key, value in params.items():
            if value is True and key.startswith("work_"):
                triggers.add(key)
            if value is True and key in ("install", "delivery"):
                triggers.add(key)
    return triggers


def generate_production_plan(
    conn: sqlite3.Connection, order_id: int
) -> list[dict[str, Any]]:
    """Генерирует задания заказа по правилам (OPERATIONS_CATALOG §3).

    Правила — данные: операция попадает в план, если её trigger есть в
    наборе триггеров заказа (калькуляторы, доп-работы, флаги) либо
    trigger='always'. Монтаж (install) — всегда в конце; если он не в
    заказе, последними идут QC и упаковка (по position). Повторная
    генерация идемпотентна: существующие (не-done) задания не дублируются.
    """
    order = get_order(conn, order_id)
    triggers = _triggers_for_order(conn, order["items"])
    operations = [
        op for op in list_operations(conn, enabled_only=True) if op["trigger"] in triggers or op["trigger"] == "always"
    ]
    operations.sort(key=lambda op: (op["position"], op["code"]))

    existing = {
        row["operation_id"]: row
        for row in conn.execute(
            "SELECT * FROM production_tasks WHERE order_id = ?", (order_id,)
        )
    }
    now = utc_now()
    created: list[dict[str, Any]] = []
    for sequence, op in enumerate(operations, start=1):
        if op["id"] in existing:
            continue
        cursor = conn.execute(
            "INSERT INTO production_tasks (order_id, operation_id, status, sequence, created_at)"
            " VALUES (?, ?, 'pending', ?, ?)",
            (order_id, op["id"], sequence, now),
        )
        task_id = int(cursor.lastrowid if cursor.lastrowid is not None else 0)
        created.append(get_task(conn, task_id))
    conn.commit()
    return created


def _task_row_to_dict(
    conn: sqlite3.Connection, row: sqlite3.Row
) -> dict[str, Any]:
    op_row = conn.execute(
        "SELECT * FROM operations WHERE id = ?", (row["operation_id"],)
    ).fetchone()
    return {
        "id": row["id"],
        "order_id": row["order_id"],
        "operation": _operation_row_to_dict(op_row) if op_row else None,
        "status": row["status"],
        "sequence": row["sequence"],
        "checklist": json.loads(row["checklist_result"]) if row["checklist_result"] else [],
        "notes": row["notes"],
        "started_at": row["started_at"],
        "completed_at": row["completed_at"],
        "created_at": row["created_at"],
    }


def get_task(conn: sqlite3.Connection, task_id: int) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM production_tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        raise StoreError(f"задание не найдено: id={task_id}")
    return _task_row_to_dict(conn, row)


def list_production_tasks(
    conn: sqlite3.Connection,
    *,
    order_id: int | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """Задания (для раздела «Производство»), фильтры по заказу и статусу."""
    if status is not None and status not in TASK_STATUSES:
        raise StoreError(f"недопустимый статус задания: '{status}'")
    sql = "SELECT * FROM production_tasks WHERE 1=1"
    params: list[Any] = []
    if order_id is not None:
        sql += " AND order_id = ?"
        params.append(order_id)
    if status is not None:
        sql += " AND status = ?"
        params.append(status)
    sql += " ORDER BY order_id, sequence, id"
    return [_task_row_to_dict(conn, row) for row in conn.execute(sql, params)]


def start_task(conn: sqlite3.Connection, task_id: int) -> dict[str, Any]:
    """Взять задание в работу (pending → in_progress)."""
    task = get_task(conn, task_id)
    if task["status"] not in ("pending", "blocked"):
        raise StoreError(f"задание в статусе '{task['status']}' нельзя взять в работу")
    conn.execute(
        "UPDATE production_tasks SET status = 'in_progress', started_at = ? WHERE id = ?",
        (utc_now(), task_id),
    )
    conn.commit()
    return get_task(conn, task_id)


def complete_task(
    conn: sqlite3.Connection,
    task_id: int,
    *,
    checklist: list[bool] | None = None,
    notes: str = "",
) -> dict[str, Any]:
    """Завершить задание. QC-правило (§10 каталога): все пункты чек-листа
    операции должны быть отмечены — «Готово» без галочек запрещено."""
    task = get_task(conn, task_id)
    if task["status"] != "in_progress":
        raise StoreError(f"завершить можно только задание в работе (сейчас: '{task['status']}')")
    operation = task["operation"] or {}
    required = operation.get("checklist") or []
    checked = checklist if checklist is not None else []
    if len(checked) < len(required):
        raise StoreError(
            f"чек-лист не пройден: отмечено {len(checked)} из {len(required)} (§10: "
            "операция не завершается без выполненных пунктов)"
        )
    if not all(checked):
        raise StoreError("не все пункты чек-листа отмечены выполненными")
    conn.execute(
        "UPDATE production_tasks SET status = 'done', checklist_result = ?, notes = ?,"
        " completed_at = ? WHERE id = ?",
        (json.dumps(checked, ensure_ascii=False), notes.strip(), utc_now(), task_id),
    )
    conn.commit()
    task = get_task(conn, task_id)
    task["stock_auto_consume"] = _auto_consume_if_ready(conn, task["order_id"])
    return task


def _auto_consume_if_ready(conn: sqlite3.Connection, order_id: int) -> dict[str, Any] | None:
    """Этап 5b (связка Склад×Производство): когда ВСЕ задания заказа выполнены,
    резерв заказа автоматически конвертируется в списание (RESERVE→CONSUME).

    Никогда не ломает завершение задания: любая ошибка склада (нет расхода,
    уже списан, нет материалов в реестре) гасится и возвращает None.
    Идемпотентно: consume_order_materials сам запрещает повторное списание.
    """
    progress = production_progress(conn, order_id)
    if not progress["all_done"]:
        return None
    try:
        return consume_order_materials(conn, order_id)
    except StoreError:
        return None


def block_task(conn: sqlite3.Connection, task_id: int, *, reason: str) -> dict[str, Any]:
    """Заблокировать задание (нет материала, ждём клиента…)."""
    task = get_task(conn, task_id)
    if task["status"] in ("done",):
        raise StoreError("выполненное задание нельзя заблокировать")
    conn.execute(
        "UPDATE production_tasks SET status = 'blocked', notes = ? WHERE id = ?",
        (reason.strip(), task_id),
    )
    conn.commit()
    return get_task(conn, task_id)


def production_progress(conn: sqlite3.Connection, order_id: int) -> dict[str, Any]:
    """Прогресс заказа в производстве: счётчики по статусам + готовность."""
    tasks = list_production_tasks(conn, order_id=order_id)
    counts = {status: 0 for status in TASK_STATUSES}
    for task in tasks:
        counts[task["status"]] += 1
    total = len(tasks)
    done = counts["done"]
    return {
        "order_id": order_id,
        "total": total,
        "counts": counts,
        "all_done": total > 0 and done == total,
        "progress_percent": round(done / total * 100.0, 1) if total else 0.0,
    }


# ---------- склад (Этап 5 роадмапа v6, промт_4 §19-21) ----------

#: Типы движений склада (§7.1 промт_5). Закрытый словарь (ANTI-6b).
STOCK_MOVEMENT_KINDS: tuple[str, ...] = (
    "PURCHASE",   # закупка (приход, физически подтверждён)
    "RESERVE",    # резерв под заказ (расчётный, не физический приход)
    "RELEASE",    # снятие резерва (отказ/правка заказа)
    "CONSUME",    # фактическое списание в производство
    "ADJUST",     # инвентаризация: коррекция к физическому остатку
)

#: Знак влияния движения на остаток: +1 приход, −1 расход, 0 — только память.
_MOVEMENT_SIGN: dict[str, int] = {
    "PURCHASE": 1,
    "RESERVE": 0,   # резерв не меняет физический остаток (§19: estimated ≠ physical)
    "RELEASE": 0,
    "CONSUME": -1,
    "ADJUST": 0,    # ADJUST задаёт остаток напрямую (set), а не складывается
}

#: Единицы склада — единица РАСХОДА материала (base_unit реестра, BR-W3).


def record_stock_movement(
    conn: sqlite3.Connection,
    *,
    material_id: int,
    kind: str,
    quantity: float,
    order_id: int | None = None,
    note: str = "",
) -> dict[str, Any]:
    """Записывает движение склада (ledger). Raises StoreError на неизвестный тип."""
    if kind not in STOCK_MOVEMENT_KINDS:
        raise StoreError(f"неизвестный тип движения: '{kind}'")
    if isinstance(quantity, bool) or not isinstance(quantity, (int, float)) or quantity == 0:
        raise StoreError("количество должно быть ненулевым числом")
    if get_material(conn, material_id) is None:
        raise StoreError(f"материал {material_id} не найден")
    conn.execute(
        "INSERT INTO stock_movements (material_id, order_id, kind, quantity, note, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (material_id, order_id, kind, float(quantity), note.strip(), utc_now()),
    )
    conn.commit()
    return {"material_id": material_id, "order_id": order_id, "kind": kind, "quantity": float(quantity)}


def stock_position(conn: sqlite3.Connection, material_id: int) -> dict[str, Any]:
    """Позиция склада материала (§19-20 промт_4).

    physical  — PURCHASE − CONSUME (только подтверждённые движения);
    reserved  — RESERVE − RELEASE (под заказы);
    estimated — physical − reserved (доступно для новых заказов);
    Признак «~» (расчётный) — estimated всегда расчётный, physical
    подтверждается только инвентаризацией (ADJUST).
    """
    rows = conn.execute(
        "SELECT kind, quantity FROM stock_movements WHERE material_id = ?", (material_id,)
    ).fetchall()
    physical = 0.0
    reserved = 0.0
    for row in rows:
        kind, qty = row["kind"], float(row["quantity"])
        if kind == "PURCHASE":
            physical += qty
        elif kind == "CONSUME":
            physical -= qty
        elif kind == "ADJUST":
            physical += qty  # дельта может быть любой: set-семантика инвентаризации
        elif kind == "RESERVE":
            reserved += qty
        elif kind == "RELEASE":
            reserved -= qty
    material = get_material(conn, material_id)
    unit = material["base_unit"] if material else "m2"
    return {
        "material_id": material_id,
        "material_name": material["name"] if material else None,
        "unit": unit,
        "physical": round(physical, 4),
        "reserved": round(reserved, 4),
        "estimated": round(physical - reserved, 4),  # «~» — расчётный остаток
        "min_stock": material["min_stock"] if material else 0,
    }


def list_stock_movements(
    conn: sqlite3.Connection,
    *,
    material_id: int | None = None,
    order_id: int | None = None,
    kind: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Лента движений склада (ledger) с фильтрами, новые первыми."""
    sql = "SELECT * FROM stock_movements"
    conditions: list[str] = []
    params: list[Any] = []
    if material_id is not None:
        conditions.append("material_id = ?")
        params.append(material_id)
    if order_id is not None:
        conditions.append("order_id = ?")
        params.append(order_id)
    if kind is not None:
        if kind not in STOCK_MOVEMENT_KINDS:
            raise StoreError(f"неизвестный тип движения: '{kind}'")
        conditions.append("kind = ?")
        params.append(kind)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(int(limit))
    rows = conn.execute(sql, params).fetchall()
    material_names = {m["id"]: m["name"] for m in list_materials(conn, active_only=False)}
    return [
        {
            "id": row["id"],
            "material_id": row["material_id"],
            "material_name": material_names.get(row["material_id"]),
            "order_id": row["order_id"],
            "kind": row["kind"],
            "quantity": float(row["quantity"]),
            "note": row["note"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def list_stock(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Склад целиком: позиции всех активных материалов."""
    materials = list_materials(conn, active_only=True)
    return [stock_position(conn, m["id"]) for m in materials]


def adjust_stock(
    conn: sqlite3.Connection, material_id: int, *, counted_quantity: float, note: str = ""
) -> dict[str, Any]:
    """Инвентаризация (§19): коррекция к физически посчитанному остатку.

    ADJUST — единственное движение, задающее остаток напрямую (set):
    дельта = counted − current_physical записывается как ADJUST-движение.
    """
    current = stock_position(conn, material_id)
    delta = float(counted_quantity) - current["physical"]
    if abs(delta) < 1e-9:
        return {"adjusted": False, "movement": None, "position": current}
    movement = record_stock_movement(
        conn,
        material_id=material_id,
        kind="ADJUST",
        quantity=delta,
        note=note or f"инвентаризация: посчитано {counted_quantity}",
    )
    return {"adjusted": True, "movement": movement, "position": stock_position(conn, material_id)}


def _order_consumption_by_material(
    conn: sqlite3.Connection, items: list[dict[str, Any]]
) -> dict[int, float]:
    """Суммирует production-расход заказа по материалам (из consumption_json).

    Ключ агрегации — billing/production в ЕДИНИЦЕ РАСХОДА материала:
    ROLL_NESTING → пог.м (production_length_m), иначе м² (production_area_m2).
    """
    totals: dict[int, float] = {}
    for item in items:
        consumption = item.get("consumption")
        if not consumption:
            continue
        try:
            material_id = int(consumption["material_id"])
        except (KeyError, TypeError, ValueError):
            continue
        unit = consumption.get("billing_unit", "")
        if unit == "lm":
            qty = float(consumption.get("production_length_m") or 0.0)
        elif unit == "лист":
            qty = float(consumption.get("billing_quantity") or 0.0)
        else:
            qty = float(consumption.get("production_area_m2") or 0.0)
        if qty > 0:
            totals[material_id] = totals.get(material_id, 0.0) + qty
    return totals


def reserve_order_materials(
    conn: sqlite3.Connection, order_id: int
) -> dict[str, Any]:
    """Резерв материалов заказа (§20): Production Consumption → RESERVE.

    Расход берётся из consumption_json позиций заказа (уже посчитан движком
    при сохранении). Повторный вызов идемпотентен: заказ с активным резервом
    не резервируется второй раз. Один материал — одно RESERVE-движение.
    """
    order = get_order(conn, order_id)
    existing = conn.execute(
        "SELECT COUNT(*) FROM stock_movements WHERE order_id = ? AND kind = 'RESERVE'",
        (order_id,),
    ).fetchone()[0]
    if existing:
        raise StoreError(f"заказ {order_id} уже зарезервирован на складе")
    totals = _order_consumption_by_material(conn, order["items"])
    if not totals:
        raise StoreError("у заказа нет рассчитанного расхода — резервировать нечего")
    created: list[dict[str, Any]] = []
    for material_id, qty in sorted(totals.items()):
        created.append(
            record_stock_movement(
                conn, material_id=material_id, kind="RESERVE", quantity=qty,
                order_id=order_id, note=f"резерв под заказ {order_id}",
            )
        )
    return {"order_id": order_id, "reserved": created}


def release_order_materials(conn: sqlite3.Connection, order_id: int) -> dict[str, Any]:
    """Снятие резерва заказа (отказ, правка состава). Идемпотентно: снимает
    только существующие RESERVE; CONSUME после списания блокирует снятие."""
    consumed = conn.execute(
        "SELECT COUNT(*) FROM stock_movements WHERE order_id = ? AND kind = 'CONSUME'",
        (order_id,),
    ).fetchone()[0]
    if consumed:
        raise StoreError("заказ уже списан со склада — снятие резерва невозможно")
    reserves = conn.execute(
        "SELECT * FROM stock_movements WHERE order_id = ? AND kind = 'RESERVE'",
        (order_id,),
    ).fetchall()
    if not reserves:
        raise StoreError(f"у заказа {order_id} нет активного резерва")
    released: list[dict[str, Any]] = []
    for row in reserves:
        released.append(
            record_stock_movement(
                conn, material_id=row["material_id"], kind="RELEASE",
                quantity=float(row["quantity"]), order_id=order_id,
                note=f"снятие резерва заказа {order_id}",
            )
        )
    return {"order_id": order_id, "released": released}


def consume_order_materials(conn: sqlite3.Connection, order_id: int) -> dict[str, Any]:
    """Фактическое списание по выдаче (§20 MASTER: «материалы списываются»).

    Резерв конвертируется: RESERVE-движения заказа заменяются CONSUME
    (физический остаток уменьшается, резерв обнуляется RELEASE'ом).
    """
    reserves = conn.execute(
        "SELECT * FROM stock_movements WHERE order_id = ? AND kind = 'RESERVE'",
        (order_id,),
    ).fetchall()
    consumed_before = conn.execute(
        "SELECT COUNT(*) FROM stock_movements WHERE order_id = ? AND kind = 'CONSUME'",
        (order_id,),
    ).fetchone()[0]
    if consumed_before:
        raise StoreError(f"заказ {order_id} уже списан")
    order = get_order(conn, order_id)
    totals = _order_consumption_by_material(conn, order["items"])
    if not totals and not reserves:
        raise StoreError("у заказа нет рассчитанного расхода — списывать нечего")
    released: list[dict[str, Any]] = []
    for row in reserves:
        released.append(
            record_stock_movement(
                conn, material_id=row["material_id"], kind="RELEASE",
                quantity=float(row["quantity"]), order_id=order_id,
                note=f"конвертация резерва в списание (заказ {order_id})",
            )
        )
    consumed: list[dict[str, Any]] = []
    for material_id, qty in sorted(totals.items()):
        consumed.append(
            record_stock_movement(
                conn, material_id=material_id, kind="CONSUME", quantity=qty,
                order_id=order_id, note=f"списание по заказу {order_id}",
            )
        )
    return {"order_id": order_id, "consumed": consumed, "released": released}


def _round_up_pack(quantity: float, pack_size: float | None) -> tuple[float, bool]:
    """Округление закупки до упаковки/рулона (§21). Возвращает (кол-во, округлено)."""
    if pack_size is not None and pack_size > 0:
        import math

        packed = math.ceil(quantity / pack_size) * pack_size
        return packed, packed > quantity
    return quantity, False


def purchase_plan(
    conn: sqlite3.Connection, *, required: dict[int, float] | None = None
) -> list[dict[str, Any]]:
    """Планировщик закупок (§21): Need = Required − Available − Reserved.

    required — внешний дополнительный спрос (material_id → количество),
    например сумма планов производства. По умолчанию — только min_stock.
    Рекомендация округляется вверх до pack_size (упаковка/рулон).
    Порог срабатывания: below min_stock ИЛИ внешний required превышает
    estimated. Нулевые рекомендации не возвращаются.
    """
    plan: list[dict[str, Any]] = []
    for material in list_materials(conn, active_only=True):
        position = stock_position(conn, material["id"])
        extra = float((required or {}).get(material["id"], 0.0))
        min_stock = float(material["min_stock"] or 0.0)
        deficit = (min_stock + extra) - position["estimated"]
        if deficit <= 1e-9:
            continue
        recommendation, rounded = _round_up_pack(deficit, material.get("pack_size"))
        plan.append({
            "material_id": material["id"],
            "material_name": material["name"],
            "unit": position["unit"],
            "estimated": position["estimated"],
            "reserved": position["reserved"],
            "min_stock": min_stock,
            "extra_required": extra if extra > 0 else None,
            "deficit": round(deficit, 4),
            "recommendation": round(recommendation, 4),
            "rounded_to_pack": rounded,
            "pack_size": material.get("pack_size"),
        })
    plan.sort(key=lambda row: -row["deficit"])
    return plan


# ---------- коммуникации: входящие и заявки (Этап 6, §44/§45/§55 промт_4) ----------

#: Закрытые словари коммуникаций (ANTI-6b).
INBOX_CHANNELS: tuple[str, ...] = ("telegram", "manual", "email")
INBOX_STATUSES: tuple[str, ...] = ("new", "inquiry", "archived")
INQUIRY_STATUSES: tuple[str, ...] = ("new", "estimated", "archived")
CLIENT_MATCH_KINDS: tuple[str, ...] = ("none", "auto", "manual")


def _message_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "channel": row["channel"],
        "external_id": row["external_id"],
        "chat_id": row["chat_id"],
        "sender_name": row["sender_name"],
        "sender_handle": row["sender_handle"],
        "text": row["text"],
        "status": row["status"],
        "parsed": json.loads(row["parsed_json"] or "{}"),
        "inquiry_id": row["inquiry_id"],
        "received_at": row["received_at"],
    }


def _inquiry_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "message_id": row["message_id"],
        "client_id": row["client_id"],
        "client_match": row["client_match"],
        "summary": row["summary"],
        "status": row["status"],
        "estimate_id": row["estimate_id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def record_incoming_message(
    conn: sqlite3.Connection,
    *,
    channel: str,
    external_id: str,
    chat_id: str = "",
    sender_name: str = "",
    sender_handle: str = "",
    text: str = "",
    received_at: str | None = None,
) -> tuple[dict[str, Any], bool]:
    """Принимает сообщение (§55): дубликат по (channel, external_id) не создаёт
    строку, а возвращает существующую (created=False). Парсер запускается
    детерминированный (printcalc_web.parser.parse)."""
    if channel not in INBOX_CHANNELS:
        raise StoreError(f"неизвестный канал: {channel} (допустимо: {INBOX_CHANNELS})")
    if not external_id.strip():
        raise StoreError("external_id обязателен (идемпотентность §55)")
    existing = conn.execute(
        "SELECT * FROM inbox_messages WHERE channel = ? AND external_id = ?",
        (channel, external_id),
    ).fetchone()
    if existing is not None:
        return _message_row_to_dict(existing), False

    parsed = parser.parse(conn, text or "")
    now = received_at or utc_now()
    cursor = conn.execute(
        "INSERT INTO inbox_messages (channel, external_id, chat_id, sender_name,"
        " sender_handle, text, status, parsed_json, received_at)"
        " VALUES (?, ?, ?, ?, ?, ?, 'new', ?, ?)",
        (channel, external_id.strip(), chat_id, sender_name, sender_handle,
         text or "", json.dumps(parsed, ensure_ascii=False), now),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM inbox_messages WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return _message_row_to_dict(row), True


def list_inbox(
    conn: sqlite3.Connection, *, status: str | None = None, limit: int = 100
) -> list[dict[str, Any]]:
    """Входящие, новые сверху (по убыванию received_at)."""
    if status is not None and status not in INBOX_STATUSES:
        raise StoreError(f"неизвестный статус входящих: {status}")
    query = "SELECT * FROM inbox_messages"
    params: list[Any] = []
    if status is not None:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY received_at DESC, id DESC LIMIT ?"
    params.append(limit)
    return [_message_row_to_dict(row) for row in conn.execute(query, params).fetchall()]


def get_inbox_message(conn: sqlite3.Connection, message_id: int) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM inbox_messages WHERE id = ?", (message_id,)).fetchone()
    return _message_row_to_dict(row) if row else None


def archive_inbox_message(conn: sqlite3.Connection, message_id: int) -> dict[str, Any]:
    """Спрятать сообщение без заявки (спам/дубль-сообщение)."""
    row = conn.execute("SELECT * FROM inbox_messages WHERE id = ?", (message_id,)).fetchone()
    if row is None:
        raise StoreError(f"сообщение {message_id} не найдено")
    conn.execute(
        "UPDATE inbox_messages SET status = 'archived' WHERE id = ?", (message_id,)
    )
    conn.commit()
    return get_inbox_message(conn, message_id)  # type: ignore[return-value]


def _normalize_telegram_handle(value: str) -> str:
    v = value.strip().lstrip("@")
    return v.lower()


def match_client_for_message(
    conn: sqlite3.Connection, message: dict[str, Any]
) -> dict[str, Any] | None:
    """Client matching (§45): точное совпадение по telegram-контакту."""
    handle = _normalize_telegram_handle(message.get("sender_handle") or "")
    if handle:
        client = find_client_by_contact(conn, channel="telegram", value=handle)
        if client is not None:
            return client
    return None


def create_inquiry_from_message(
    conn: sqlite3.Connection, message_id: int, *, client_id: int | None = None
) -> dict[str, Any]:
    """Сообщение → заявка. client_id=None — авто-matching (§45); найденный
    клиент привязывается (client_match='auto'), иначе 'none'. Повторный вызов
    для одного сообщения возвращает существующую заявку (идемпотентно)."""
    message = get_inbox_message(conn, message_id)
    if message is None:
        raise StoreError(f"сообщение {message_id} не найдено")
    existing = conn.execute(
        "SELECT * FROM inquiries WHERE message_id = ?", (message_id,)
    ).fetchone()
    if existing is not None:
        return _inquiry_row_to_dict(existing)
    if client_id is not None and get_client(conn, client_id) is None:
        raise StoreError(f"клиент {client_id} не найден")

    match_kind = "manual" if client_id is not None else "none"
    if client_id is None:
        auto = match_client_for_message(conn, message)
        if auto is not None:
            client_id = auto["id"]
            match_kind = "auto"

    summary_items = message.get("parsed", {}).get("items") or []
    summary = "; ".join(
        str(item.get("name", "?")) for item in summary_items
    ) or (message["text"] or "")[:120]

    now = utc_now()
    cursor = conn.execute(
        "INSERT INTO inquiries (message_id, client_id, client_match, summary, status,"
        " created_at, updated_at) VALUES (?, ?, ?, ?, 'new', ?, ?)",
        (message_id, client_id, match_kind, summary, now, now),
    )
    inquiry_id = int(cursor.lastrowid if cursor.lastrowid is not None else 0)
    conn.execute(
        "UPDATE inbox_messages SET status = 'inquiry', inquiry_id = ? WHERE id = ?",
        (inquiry_id, message_id),
    )
    conn.commit()
    return get_inquiry(conn, inquiry_id)


def get_inquiry(conn: sqlite3.Connection, inquiry_id: int) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM inquiries WHERE id = ?", (inquiry_id,)).fetchone()
    if row is None:
        raise StoreError(f"заявка не найдена: id={inquiry_id}")
    return _inquiry_row_to_dict(row)


def list_inquiries(
    conn: sqlite3.Connection, *, status: str | None = None
) -> list[dict[str, Any]]:
    if status is not None and status not in INQUIRY_STATUSES:
        raise StoreError(f"неизвестный статус заявки: {status}")
    query = "SELECT * FROM inquiries"
    params: list[Any] = []
    if status is not None:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY updated_at DESC, id DESC"
    return [_inquiry_row_to_dict(row) for row in conn.execute(query, params).fetchall()]


def update_inquiry(
    conn: sqlite3.Connection,
    inquiry_id: int,
    *,
    client_id: int | None | EllipsisType = ...,
    summary: str | None = None,
) -> dict[str, Any]:
    """Правка заявки оператором: перепривязка клиента (manual) и описание."""
    current = get_inquiry(conn, inquiry_id)
    fields: list[str] = []
    params: list[Any] = []
    if client_id is not ...:
        if client_id is not None and get_client(conn, client_id) is None:
            raise StoreError(f"клиент {client_id} не найден")
        fields.append("client_id = ?")
        params.append(client_id)
        fields.append("client_match = ?")
        params.append("manual" if client_id is not None else "none")
    if summary is not None:
        fields.append("summary = ?")
        params.append(summary.strip())
    if fields:
        fields.append("updated_at = ?")
        params.append(utc_now())
        params.append(inquiry_id)
        conn.execute(f"UPDATE inquiries SET {', '.join(fields)} WHERE id = ?", params)
        conn.commit()
    return get_inquiry(conn, inquiry_id)


def attach_estimate_to_inquiry(
    conn: sqlite3.Connection, inquiry_id: int, estimate_id: int
) -> dict[str, Any]:
    """Смета → заявка (жизненный цикл new → estimated). Идемпотентно:
    повторная привязка той же сметы возвращается без ошибки."""
    inquiry = get_inquiry(conn, inquiry_id)
    if inquiry["estimate_id"] == estimate_id and inquiry["status"] == "estimated":
        return inquiry
    row = conn.execute("SELECT id FROM estimates WHERE id = ?", (estimate_id,)).fetchone()
    if row is None:
        raise StoreError(f"смета {estimate_id} не найдена")
    conn.execute(
        "UPDATE inquiries SET estimate_id = ?, status = 'estimated', updated_at = ?"
        " WHERE id = ?",
        (estimate_id, utc_now(), inquiry_id),
    )
    conn.commit()
    return get_inquiry(conn, inquiry_id)
