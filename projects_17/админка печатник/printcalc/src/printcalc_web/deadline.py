"""Deadline Engine — вычисляемая срочность заказа (РОАДМАП_v8 поток B).

Детерминированный слой БЕЗ LLM и БЕЗ второй системы: статусы/пороги —
чистые функции от (deadline - now); хранение — колонки orders +
журнал deadline_events (db.py); настройки порогов — существующая таблица
settings (ТЗ §29 «не создавать параллельную систему настроек»).

Ключевые контракты ТЗ:
- §11: DeadlineStatus — ОТДЕЛЬНОЕ измерение, не смешивается с
  OrderStatus/Production/Payment;
- §8: финальные заказы (выполнен/завершён/отменён) не тревожат;
- §18: «без дедлайна» ≠ «просрочен» — NULL deadline → None;
- §7: remaining_time НЕ хранится в БД — вычисляется динамически;
- §10: напоминание порога пишется один раз (UNIQUE order_id+type+threshold);
- §21: timezone-aware ISO-метки (UTC), как utc_now() в store.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from printcalc_web.store import FINAL_ORDER_STATUSES, StoreError, utc_now

#: Закрытый словарь статусов срочности (ANTI-6b) — ТЗ §4.
DEADLINE_STATUSES: tuple[str, ...] = (
    "normal", "warning", "urgent", "critical", "very_critical", "overdue",
)

#: Типы дедлайна (ТЗ §3): клиентский и внутренний производственный.
DEADLINE_TYPES: tuple[str, ...] = ("customer", "internal")

#: Пороги напоминаний по умолчанию, в часах до дедлайна (ТЗ §9).
#: Ключ «overdue» — событие после наступления дедлайна.
DEFAULT_THRESHOLDS_HOURS: dict[str, float] = {
    "3d": 72.0,
    "24h": 24.0,
    "12h": 12.0,
    "2h": 2.0,
    "overdue": 0.0,
}

SETTINGS_KEY = "deadline_thresholds"


# ---------- настройки порогов (существующая таблица settings) --------------


def get_thresholds(conn: Any) -> dict[str, float]:
    """Пороги из settings (часы до дедлайна); дефолт — ТЗ §4.

    Значение в settings — JSON-словарь; битая запись = дефолт (не молча:
    возвращаем дефолт, а не падаем — настройки редактирует владелец).
    """
    row = conn.execute(
        "SELECT value FROM settings WHERE key = ?", (SETTINGS_KEY,)
    ).fetchone()
    if row is None:
        return dict(DEFAULT_THRESHOLDS_HOURS)
    try:
        raw = json.loads(row["value"])
        return {str(k): float(v) for k, v in raw.items()}
    except (ValueError, TypeError):
        return dict(DEFAULT_THRESHOLDS_HOURS)


def set_thresholds(conn: Any, thresholds: dict[str, float]) -> dict[str, float]:
    """Сохраняет пороги; ключи вне DEFAULT — ошибка (ANTI-6b, closed set)."""
    unknown = set(thresholds) - set(DEFAULT_THRESHOLDS_HOURS)
    if unknown:
        raise StoreError(
            f"неизвестные пороги: {', '.join(sorted(unknown))}"
            f" (допустимо: {', '.join(DEFAULT_THRESHOLDS_HOURS)})"
        )
    merged = {**DEFAULT_THRESHOLDS_HOURS, **{k: float(v) for k, v in thresholds.items()}}
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (SETTINGS_KEY, json.dumps(merged, ensure_ascii=False)),
    )
    conn.commit()
    return merged


# ---------- разбор/хранение меток (ТЗ §21 timezone-aware) -------------------


def _parse_ts(value: str | None) -> datetime | None:
    """ISO-строка → aware-datetime (UTC). None/пустое/битое → None (не молча:
    битая метка = «без дедлайна», а не выдуманный момент)."""
    if value is None or not str(value).strip():
        return None
    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        # Наивная метка (легаси/ручной SQL) — интерпретируем как UTC явно.
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def parse_deadline(value: str | None) -> datetime | None:
    """Публичный разбор дедлайна из БД."""
    return _parse_ts(value)


def format_deadline_input(value: str) -> str:
    """Проверяет пользовательский ввод даты-времени, возвращает ISO UTC.

    Принимает ISO с офсетом или наивное локальное время (трактуется как
    UTC по конвенции проекта). Ошибка формата → StoreError (не молча).
    """
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError as exc:
        raise StoreError(f"некорректный формат даты-времени: {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds")


# ---------- вычисление срочности (ТЗ §4–6) ----------------------------------


def urgency_from_remaining(remaining: timedelta, thresholds: dict[str, float]) -> str:
    """Остаток времени → статус срочности (чистая функция, ТЗ §4).

    Пороги — часы ОСТАТКА: WARNING ≤ 72ч, URGENT ≤ 24ч, CRITICAL ≤ 12ч,
    VERY_CRITICAL ≤ 2ч, OVERDUE ≤ 0. Нормальный (>72ч) = NORMAL.
    """
    hours = remaining.total_seconds() / 3600.0
    if hours <= 0:
        return "overdue"
    if hours <= thresholds.get("2h", 2.0):
        return "very_critical"
    if hours <= thresholds.get("12h", 12.0):
        return "critical"
    if hours <= thresholds.get("24h", 24.0):
        return "urgent"
    if hours <= thresholds.get("3d", 72.0):
        return "warning"
    return "normal"


def urgency_for_order(
    status: str,
    customer_deadline: str | None,
    internal_deadline: str | None,
    thresholds: dict[str, float],
    now: datetime | None = None,
) -> dict[str, Any] | None:
    """Срочность заказа: вычисляемое измерение (ТЗ §11), не хранится.

    Возвращает None для «без дедлайна» (ТЗ §18) и финальных статусов
    (ТЗ §8: выполнен/завершён/отменён не тревожат). Приоритет срочности —
    по САМОМУ раннему активному дедлайну; remaining — по нему же.
    """
    if status in FINAL_ORDER_STATUSES:
        return None
    candidates = [
        d
        for d in (
            _parse_ts(customer_deadline),
            _parse_ts(internal_deadline),
        )
        if d is not None
    ]
    if not candidates:
        return None
    current = now if now is not None else datetime.now(timezone.utc)
    nearest = min(candidates)
    internal_parsed = _parse_ts(internal_deadline)
    customer_parsed = _parse_ts(customer_deadline)
    remaining: timedelta = nearest - current
    return {
        "status": urgency_from_remaining(remaining, thresholds),
        "remaining_seconds": int(remaining.total_seconds()),
        "nearest_deadline": nearest.isoformat(timespec="seconds"),
        "is_internal": internal_parsed is not None
        and nearest == internal_parsed
        and (customer_parsed is None or internal_parsed <= customer_parsed),
    }


def format_remaining(seconds: int) -> str:
    """Человекочитаемый остаток (ТЗ §6: формат зависит от величины).

    >2 суток — «N дн. M ч.»; >2 часов — «N ч. M мин.»; else «M мин.»;
    прошедшее — «Просрочен: …».
    """
    overdue = seconds < 0
    total_minutes = abs(seconds) // 60
    days, rem = divmod(total_minutes, 1440)
    hours, minutes = divmod(rem, 60)
    if days >= 1:
        text = f"{days} дн. {hours} ч."
    elif hours >= 1:
        text = f"{hours} ч. {minutes} мин."
    else:
        text = f"{minutes} мин."
    return f"Просрочен: {text}" if overdue else text


#: Приоритет сортировки по срочности (ТЗ §13: OVERDUE → … → NORMAL).
URGENCY_ORDER: dict[str, int] = {
    "overdue": 0,
    "very_critical": 1,
    "critical": 2,
    "urgent": 3,
    "warning": 4,
    "normal": 5,
    "none": 6,  # «без дедлайна» — в конец списка (ТЗ §18: не просрочен)
}


# ---------- напоминания (ТЗ §9–10, §31) -------------------------------------


def _reminder_threshold_keys(
    remaining: timedelta, thresholds: dict[str, float]
) -> list[str]:
    """Ключи порогов, УЖЕ пройденных этим остатком (для напоминаний).

    «Пройден» = остаток ≤ порога. overdue включается при остатке ≤ 0.
    """
    hours = remaining.total_seconds() / 3600.0
    passed: list[str] = []
    for key, limit in thresholds.items():
        if key == "overdue":
            if hours <= 0:
                passed.append(key)
        elif hours <= limit:
            passed.append(key)
    # Стабильный порядок: от дальнего порога к ближнему.
    order = list(DEFAULT_THRESHOLDS_HOURS)
    return sorted(passed, key=order.index)


def record_deadline_change(
    conn: Any,
    order_id: int,
    deadline_type: str,
    kind: str,
    *,
    old_value: str | None = None,
    new_value: str | None = None,
) -> None:
    """Аудит-событие set/changed/cleared (ТЗ §30) — всегда пишется.

    kind: set (было NULL), changed (замена), cleared (удаление).
    payload хранит старое→новое («Иванов изменил дедлайн: A → B»).
    """
    if deadline_type not in DEADLINE_TYPES:
        raise StoreError(f"недопустимый тип дедлайна: {deadline_type!r}")
    if kind not in ("set", "changed", "cleared"):
        raise StoreError(f"недопустимый вид события: {kind!r}")
    conn.execute(
        "INSERT INTO deadline_events"
        " (order_id, deadline_type, kind, threshold, payload_json, created_at)"
        " VALUES (?, ?, ?, '', ?, ?)",
        (
            order_id,
            deadline_type,
            kind,
            json.dumps(
                {"old": old_value, "new": new_value}, ensure_ascii=False
            ),
            utc_now(),
        ),
    )


def sweep_deadline_reminders(
    conn: Any,
    orders: list[dict[str, Any]],
    *,
    now: datetime | None = None,
) -> int:
    """Пишет reminder-события для пройденных порогов; идемпотентно (ТЗ §10).

    Порог считается «отправленным», если строка
    (order_id, deadline_type, threshold) уже есть в deadline_events —
    UNIQUE гарантирует отсутствие дублей даже при гонке. Смена дедлайна
    (ТЗ §31): reminder-строки старого дедлайна НЕ переиспользуются — при
    изменении дедлайна reminder-строки типа удаляются (пороги честно
    сработают заново на новом дедлайне), но set/changed-события остаются
    в истории. Возвращает число НАПИСАННЫХ (новых) напоминаний.
    """
    thresholds = get_thresholds(conn)
    current = now if now is not None else datetime.now(timezone.utc)
    written = 0
    for order in orders:
        if order.get("status") in FINAL_ORDER_STATUSES:
            continue  # ТЗ §8: финальные не тревожим
        for dtype, value in (
            ("customer", order.get("customer_deadline")),
            ("internal", order.get("internal_deadline")),
        ):
            deadline = _parse_ts(value)
            if deadline is None:
                continue
            remaining = deadline - current
            for key in _reminder_threshold_keys(remaining, thresholds):
                cursor = conn.execute(
                    "INSERT OR IGNORE INTO deadline_events"
                    " (order_id, deadline_type, kind, threshold, payload_json, created_at)"
                    " VALUES (?, ?, 'reminder', ?, ?, ?)",
                    (
                        order["id"],
                        dtype,
                        key,
                        json.dumps(
                            {
                                "remaining_seconds": int(remaining.total_seconds()),
                                "deadline": deadline.isoformat(timespec="seconds"),
                            },
                            ensure_ascii=False,
                        ),
                        utc_now(),
                    ),
                )
                if cursor.rowcount > 0:
                    written += 1
    conn.commit()
    return written


def clear_reminders_for_reschedule(
    conn: Any, order_id: int, deadline_type: str
) -> int:
    """При смене дедлайна (ТЗ §31): старые reminder-пороги сбрасываются,
    чтобы уведомления сработали заново на новом времени — без спама по
    старым. set/changed-события (аудит) не трогаются."""
    cursor = conn.execute(
        "DELETE FROM deadline_events"
        " WHERE order_id = ? AND deadline_type = ? AND kind = 'reminder'",
        (order_id, deadline_type),
    )
    return int(cursor.rowcount or 0)


def list_events(conn: Any, order_id: int | None = None, limit: int = 200) -> list[dict[str, Any]]:
    """Журнал дедлайн-событий (новые сверху) — UI-лента и аудит."""
    if order_id is not None:
        rows = conn.execute(
            "SELECT * FROM deadline_events WHERE order_id = ?"
            " ORDER BY created_at DESC, id DESC LIMIT ?",
            (order_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM deadline_events"
            " ORDER BY created_at DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    events: list[dict[str, Any]] = []
    for row in rows:
        event = dict(row)
        event["payload"] = json.loads(event.pop("payload_json") or "{}")
        events.append(event)
    return events


# ---------- фильтры списка (ТЗ §17–18) ---------------------------------------


def deadline_filter_matches(
    order: dict[str, Any], filter_key: str, now: datetime | None = None
) -> bool:
    """Фильтр дедлайнов строки списка (детерминированный, ТЗ §17/§18)."""
    if filter_key in ("", "all"):
        return True
    current = now if now is not None else datetime.now(timezone.utc)
    active = order.get("status") not in FINAL_ORDER_STATUSES
    customer = _parse_ts(order.get("customer_deadline"))
    internal = _parse_ts(order.get("internal_deadline"))
    deadlines = [d for d in (customer, internal) if d is not None]
    if filter_key == "no_deadline":
        return not deadlines
    if not deadlines:
        return False  # «без дедлайна» не попадает в датные фильтры
    if filter_key == "active":
        return active
    if not active:
        return False
    nearest = min(deadlines)
    if filter_key == "overdue":
        return nearest < current
    day = current.date()
    target = nearest.date()
    if filter_key == "today":
        return target == day
    if filter_key == "tomorrow":
        return target == day + timedelta(days=1)
    if filter_key == "week":
        return day <= target <= day + timedelta(days=7)
    raise StoreError(f"неизвестный фильтр дедлайнов: {filter_key!r}")


# ---------- запросы помощника (ТЗ §26 второй части) --------------------------


#: Закрытый словарь дедлайн-интентов (ANTI-6b, ТЗ §26): фраза-фрагмент →
#: (фильтр deadline_filter_matches, заголовок отчёта). Распознавание —
#: детерминированное substring-совпадение нормализованной фразы; LLM нет.
DEADLINE_QUERY_INTENTS: tuple[tuple[str, str, str], ...] = (
    ("просроче", "overdue", "Просроченные"),
    ("горит", "today", "Горит сегодня"),
    ("сегодня", "today", "Горит сегодня"),
    ("завтра", "tomorrow", "На завтра"),
    ("на этой неделе", "week", "На этой неделе"),
    ("неделе", "week", "На этой неделе"),
    ("без дедлайна", "no_deadline", "Без дедлайна"),
    ("активные", "active", "Активные с дедлайном"),
)


def normalize_query(text: str) -> str:
    """Нормализация фразы для сопоставления интентов: lowercase, ё→е,
    пунктуация → пробел, схлопывание пробелов."""
    lowered = text.lower().replace("ё", "е")
    cleaned = "".join(ch if ch.isalnum() else " " for ch in lowered)
    return " ".join(cleaned.split())


def match_deadline_query(text: str) -> tuple[str, str] | None:
    """Фраза оператора → (filter_key, title) или None (не дедлайн-вопрос).

    Закрытый словарь (ANTI-6b): неизвестные фразы НЕ выдумывают интент —
    помощник уходит в обычный analyze. «Что нужно закончить до 18:00»
    отдельно не распознаётся сознательно (честное отсутствие вместо
    ложного ответа: TODO-заметка в РОАДМАП_v8).
    """
    normalized = normalize_query(text)
    if not normalized:
        return None
    for fragment, filter_key, title in DEADLINE_QUERY_INTENTS:
        if fragment in normalized:
            return (filter_key, title)
    return None


def execute_deadline_query(
    conn: Any,
    text: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    """Дедлайн-вопрос оператора → отчёт из СУЩЕСТВУЮЩЕГО Deadline-слоя
    (ТЗ §26: «не создавать отдельный источник данных»; расчёты — те же
    urgency_for_order/deadline_filter_matches, что у списка /orders).

    Возвращает None, если фраза не дедлайн-вопрос (помощник уходит в
    обычный analyze); иначе словарь с интентом, счётчиками и строками.
    Строка: id, статус, urgency-статус, remaining-текст, клиент, позиции.
    """
    matched = match_deadline_query(text)
    if matched is None:
        return None
    filter_key, title = matched
    from printcalc_web import store

    current = now if now is not None else datetime.now(timezone.utc)
    thresholds = get_thresholds(conn)
    orders = store.list_orders(conn, sort="urgency", direction="asc")
    rows: list[dict[str, Any]] = []
    for order in orders:
        if not deadline_filter_matches(order, filter_key, now=current):
            continue
        info = urgency_for_order(
            order["status"],
            order["customer_deadline"],
            order["internal_deadline"],
            thresholds,
            now=current,
        )
        remaining_text = (
            format_remaining(info["remaining_seconds"]) if info is not None else "—"
        )
        rows.append(
            {
                "id": order["id"],
                "status": order["status"],
                "urgency_status": info["status"] if info is not None else None,
                "remaining": remaining_text,
                "nearest_deadline": info["nearest_deadline"] if info is not None else None,
                "client_name": order.get("client_name") or "",
                "items": [item["name"] for item in order.get("items", [])],
            }
        )
    counts = {
        "overdue": 0,
        "very_critical": 0,
        "critical": 0,
        "urgent": 0,
        "warning": 0,
        "normal": 0,
        "no_deadline": 0,
    }
    for order in orders:
        info = urgency_for_order(
            order["status"],
            order["customer_deadline"],
            order["internal_deadline"],
            thresholds,
            now=current,
        )
        key = info["status"] if info is not None else "no_deadline"
        counts[key] = counts[key] + 1
    return {
        "intent": filter_key,
        "title": title,
        "counts": counts,
        "orders": rows,
    }
