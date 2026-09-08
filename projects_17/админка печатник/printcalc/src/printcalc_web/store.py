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
import json
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any, Mapping

from printcalc.engine.errors import CalcInputError, RegistryError
from printcalc.engine.registry import calculate
from printcalc_web.calculators import get_registry

#: Статусы заказа Phase 1 (Р2). Хранение — TEXT; расширение набора в Phase 2
#: меняет только эту константу (CONFLICT-1 v3: совместимость с workflow).
ORDER_STATUSES: tuple[str, ...] = ("новый", "в работе", "выполнен", "завершён")

#: Способы оплаты (решение Q2 от 2026-09-07); редактируется без кода.
DEFAULT_PAYMENT_METHODS: tuple[str, ...] = ("наличные", "карта", "перевод")

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
        }

    raise StoreError(f"неизвестный тип позиции: '{kind}'")


def create_order(
    conn: sqlite3.Connection,
    *,
    status: str,
    payment_method: str,
    items: list[Mapping[str, Any]],
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

    now = utc_now()
    resolved = [_resolve_item(conn, raw, index) for index, raw in enumerate(items)]
    total = round(sum(item["price"] * item["qty"] for item in resolved), 2)

    cursor = conn.execute(
        "INSERT INTO orders (status, payment_method, total, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (status, payment_method, total, now, now),
    )
    lastrowid = cursor.lastrowid
    order_id = int(lastrowid if lastrowid is not None else 0)
    for item in resolved:
        conn.execute(
            "INSERT INTO order_items (order_id, kind, name, price, qty, calculator_id,"
            " params_json, price_list_item_id, saved_to_catalog, position)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
            ),
        )
    increment_usage(conn, [i["price_list_item_id"] for i in resolved if i["price_list_item_id"]])
    conn.commit()
    return get_order(conn, order_id)


def _order_row_to_dict(
    row: sqlite3.Row, item_rows: list[sqlite3.Row]
) -> dict[str, Any]:
    """Собирает словарь заказа; item_rows — уже отсортированные позиции."""
    order: dict[str, Any] = {
        "id": row["id"],
        "status": row["status"],
        "payment_method": row["payment_method"],
        "total": row["total"],
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
                "saved_to_catalog": bool(item["saved_to_catalog"]),
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
        }
        for row in conn.execute(sql, params)
    ]


def get_order(conn: sqlite3.Connection, order_id: int) -> dict[str, Any]:
    """Полный заказ с позициями. Raises StoreError, если не найден."""
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if row is None:
        raise StoreError(f"заказ не найден: id={order_id}")
    item_rows = conn.execute(
        "SELECT * FROM order_items WHERE order_id = ? ORDER BY position", (order_id,)
    ).fetchall()
    return _order_row_to_dict(row, item_rows)


def update_order(
    conn: sqlite3.Connection,
    order_id: int,
    *,
    status: str | None = None,
    payment_method: str | None = None,
) -> dict[str, Any]:
    """Меняет статус и/или способ оплаты (состав заказа после «Добавить» закрыт)."""
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
    conn.execute("UPDATE orders SET updated_at = ? WHERE id = ?", (utc_now(), order_id))
    conn.commit()
    return get_order(conn, order_id)


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
