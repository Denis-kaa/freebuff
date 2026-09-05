"""Acceptance-сценарий 4.md §48 — реальный прогон на сервере."""
import json
import urllib.request
import urllib.error
from datetime import date, timedelta

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


print("=== Шаг 1: открыть Dashboard (default) ===")
st, ds = req("GET", "/dashboards")
dash = next(d for d in ds if d["is_default"])
print("default dashboard:", dash["name"], "| widgets:", [w["widget_type"] for w in dash["widgets"]])

print("=== Шаг 2-4: добавить Календарь, Что сделать сегодня, Дедлайны (идемпотентно) ===")
cal = dl = None
for wt, title in [("calendar", "Календарь"), ("today-tasks", "Что сделать сегодня"), ("deadlines", "Ближайшие дедлайны")]:
    existing = [w for w in dash["widgets"] if w["widget_type"] == wt]
    if wt == "deadlines":
        # переиспользуем любой deadlines-виджет (старый seed или новый)
        if existing:
            dl = existing[0]
            print(" ", wt, "reuse", dl["id"])
            continue
    elif existing:
        cal = existing[0]
        print(" ", wt, "reuse", cal["id"])
        continue
    st, w = req("POST", "/dashboards/%s/widgets" % dash["id"], {"widget_type": wt, "title": title})
    print(" ", wt, st, w.get("layout"))
    if wt == "calendar":
        cal = w
    elif wt == "deadlines":
        dl = w

print("=== Шаг 5: перетащить Calendar ===")
st, w = req("PATCH", "/dashboard-widgets/%s" % cal["id"], {"layout": {"x": 0, "y": 5, "w": 6, "h": 4}})
print(" dragged:", st, w["layout"])

print("=== Шаг 6: растянуть Calendar на всю ширину (w=12) ===")
st, w = req("PATCH", "/dashboard-widgets/%s" % cal["id"], {"layout": {"x": 0, "y": 5, "w": 12, "h": 6}})
print(" resized:", st, w["layout"])

print("=== Шаг 7: удалить Дедлайны ===")
st, _ = req("DELETE", "/dashboard-widgets/%s" % dl["id"])
print(" delete deadlines:", st)

print("=== Шаг 8: добавить Производство ===")
st, prod = req("POST", "/dashboards/%s/widgets" % dash["id"], {"widget_type": "production", "title": "Производство"})
print(" production added:", st)

print("=== Шаг 9: настроить Calendar (без производства) ===")
st, w = req("PATCH", "/dashboard-widgets/%s" % cal["id"],
            {"config": {"view": "month", "show_deadlines": True, "show_tasks": True, "show_payments": True, "show_production": False}})
print(" config:", st, w["config"])

print("=== Шаг 10: обновить страницу (пере-читать из БД) ===")
st, dash2 = req("GET", "/dashboards/%s" % dash["id"])
for wt in dash2["widgets"]:
    print("  ", wt["widget_type"], "| layout:", wt.get("layout"), "| hidden:", wt.get("is_hidden"))
cal2 = next(w for w in dash2["widgets"] if w["widget_type"] == "calendar")
assert cal2["layout"]["w"] == 12, "размер не сохранился!"
assert cal2["layout"]["x"] == 0 and cal2["layout"]["y"] == 5, "позиция не сохранилась!"
assert cal2["config"]["show_production"] is False, "настройки не сохранились!"
assert dl["id"] not in [w["id"] for w in dash2["widgets"]], "Дедлайны (экземпляр) не удалён!"
assert any(w["widget_type"] == "production" for w in dash2["widgets"]), "Production не появился!"
print(" PASS: layout/size/position/settings/deletion/add persistence OK")

print("=== Шаг 11: клик по дедлайну в Calendar открывает Project Drawer ===")
frm = date.today().isoformat()
to = (date.today() + timedelta(days=30)).isoformat()
st, cal_data = req("GET", "/dashboard-data/calendar?from=%s&to=%s" % (frm, to))
day_events = [e for d in cal_data["days"] for e in d.get("events", []) if e["event_type"] == "DEADLINE"]
print(" deadline events in calendar:", len(day_events))
if day_events:
    pid = day_events[0]["project_id"]
    st, proj = req("GET", "/projects/%s" % pid)
    print(" drawer project:", proj["display_id"], proj["title"], "-> OK (project_id in calendar event)")

print("DONE")