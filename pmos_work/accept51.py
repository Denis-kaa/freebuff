"""Acceptance-сценарий 5.md §51 — реальный прогон на сервере."""
import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8010/api"


def req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method,
                               headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


print("=== Создаём проект P100 Wazzup ===")
st, p = req("POST", "/projects", {
    "title": "Wazzup",
    "deadline": "2026-09-03",
    "advance_date": "2026-08-31",
    "final_payment_date": "2026-09-05",
    "payment_percent": "50%",
    "manager_name": "Денис",
    "risk_level": "Средний",
})
print(" project:", st, p.get("display_id"), p.get("title"))
pid = p["id"]

print("=== Project Item: Худи x100, signal_shipping_date=01.09 ===")
st, item = req("POST", "/project-items", {
    "project_id": pid, "name": "Худи", "quantity": 100,
    "signal_shipping_date": "2026-09-01",
})
print(" item:", st, item.get("name"), item.get("quantity"))

print("=== Task: Получить ОС по сигналу, deadline=31.08 ===")
st, task = req("POST", "/projects/%s/tasks" % pid, {
    "title": "Получить ОС по сигналу",
    "due_date": "2026-08-31",
    "status": "TODO",
    "assignee_name": "Денис",
})
print(" task:", st, task.get("title"))

print("=== 31.08: Аванс + задача ===")
st, r = req("GET", "/calendar/events?from=2026-08-31&to=2026-08-31")
items = r["items"]
for e in items:
    print("  ", e["type"], "|", e["title"], "|", e["start_at"][:10])
types31 = {e["type"] for e in items}
assert "PAYMENT_ADVANCE" in types31, "нет аванса 31.08"
assert "TASK_DEADLINE" in types31, "нет задачи 31.08"
print(" PASS 31.08: Аванс + Получить ОС по сигналу")

print("=== 01.09: Отгрузка сигнала ===")
st, r = req("GET", "/calendar/events?from=2026-09-01&to=2026-09-01")
items = r["items"]
for e in items:
    print("  ", e["type"], "|", e["title"])
types01 = {e["type"] for e in items}
assert "SIGNAL_SHIPMENT" in types01, "нет отгрузки сигнала 01.09"
ship = next(e for e in items if e["type"] == "SIGNAL_SHIPMENT")
print(" PASS 01.09: P100 — Отгрузка сигнала (item:", ship.get("project_item_id") is not None, ")")

print("=== 03.09: Дедлайн ===")
st, r = req("GET", "/calendar/events?from=2026-09-03&to=2026-09-03")
items = r["items"]
for e in items:
    print("  ", e["type"], "|", e["title"])
types03 = {e["type"] for e in items}
assert "PROJECT_DEADLINE" in types03, "нет дедлайна 03.09"
deadline = next(e for e in items if e["type"] == "PROJECT_DEADLINE")
print(" PASS 03.09: P100 — Дедлайн")

print("=== 05.09: Доплата ===")
st, r = req("GET", "/calendar/events?from=2026-09-05&to=2026-09-05")
items = r["items"]
for e in items:
    print("  ", e["type"], "|", e["title"])
types05 = {e["type"] for e in items}
assert "PAYMENT_FINAL" in types05, "нет доплаты 05.09"
print(" PASS 05.09: P100 — Доплата")

print("=== Клик на дедлайн -> Project Drawer (deep link §47) ===")
st, ev = req("GET", "/calendar/events/%s" % deadline["id"])
print(" event-by-id:", st, ev.get("type"), ev.get("title"), "project_id:", ev.get("project_id") is not None)
assert ev.get("project_id") == pid
st, proj = req("GET", "/projects/%s" % pid)
print(" drawer:", proj.get("display_id"), proj.get("title"))

print("=== Клик на событие сигнала -> P100 -> Худи ===")
st, ev2 = req("GET", "/calendar/events/%s" % ship["id"])
assert ev2.get("project_item_id") == item["id"]
st, it2 = req("GET", "/project-items/%s" % item["id"])
print(" draw:", proj.get("display_id"), "->", it2.get("name"), ev2.get("title"))

print("=== /calendar/today ===")
st, today = req("GET", "/calendar/today")
print(" date:", today.get("date"))
print(" tasks today:", [e["title"] for e in today.get("tasks", [])])
print(" production:", [e["title"] for e in today.get("production", [])])

print("ALL ACCEPTANCE 51 PASSED")