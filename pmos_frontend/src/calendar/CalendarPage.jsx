import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, Filter, Plus, Search } from "lucide-react";
import { api } from "../api.js";
import { useToast } from "../components/ui.jsx";
import MonthView from "./MonthView.jsx";
import { DayView, WeekView } from "./WeekDayViews.jsx";
import EventPopover from "./EventPopover.jsx";
import CustomEventForm from "./CustomEventForm.jsx";
import { FILTER_GROUPS, fmtEventTime } from "./meta.js";
import { toISO, useCalendar } from "./useCalendar.js";

const MONTHS = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
  "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"];

function readQuery() {
  const qs = new URLSearchParams(window.location.search);
  return {
    date: qs.get("date") || toISO(new Date()),
    view: ["month", "week", "day"].includes(qs.get("view")) ? qs.get("view") : "month",
  };
}

export default function CalendarPage({ onProjectClick, onOpenProjects }) {
  const toast = useToast();
  const initial = useRef(readQuery());
  const [view, setView] = useState(initial.current.view);
  const [cursor, setCursor] = useState(new Date(`${initial.current.date}T12:00:00`));

  const [types, setTypes] = useState([]); // [] = все
  const [projectId, setProjectId] = useState("");
  const [manager, setManager] = useState("");
  const [riskOnly, setRiskOnly] = useState(false);
  const [q, setQ] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [projects, setProjects] = useState([]);

  const [selectedEvent, setSelectedEvent] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editEvent, setEditEvent] = useState(null);
  const [quickDate, setQuickDate] = useState(null);

  // диапазон по view (5.md §48: запрашиваем только видимый диапазон)
  const range = useMemo(() => {
    const y = cursor.getFullYear();
    const m = cursor.getMonth();
    if (view === "month") {
      const from = new Date(y, m, 1);
      const nxt = new Date(y, m + 1, 1);
      return { from: toISO(from), to: toISO(new Date(nxt.getTime() - 86400000)) };
    }
    if (view === "week") {
      const mon = new Date(cursor);
      const dow = (mon.getDay() + 6) % 7;
      mon.setDate(mon.getDate() - dow);
      const sun = new Date(mon);
      sun.setDate(mon.getDate() + 6);
      return { from: toISO(mon), to: toISO(sun) };
    }
    return { from: toISO(cursor), to: toISO(cursor) };
  }, [cursor, view]);

  const filters = useMemo(
    () => ({
      types: types.length ? types.join(",") : undefined,
      project_id: projectId || undefined,
      manager: manager || undefined,
      risk_only: riskOnly || undefined,
      q: q || undefined,
    }),
    [types, projectId, manager, riskOnly, q]
  );

  const { items, loading, error, refresh } = useCalendar(range.from, range.to, filters, [range, filters]);

  // URL query state (5.md §46): /calendar?date=2026-08-31&view=month
  useEffect(() => {
    window.history.replaceState({}, "", `/calendar?date=${toISO(cursor)}&view=${view}`);
  }, [cursor, view]);

  useEffect(() => {
    api.widgetData.projects(50).then(setProjects).catch(() => {});
  }, []);

  const managers = useMemo(
    () => [...new Set(projects.map((p) => p.manager_name).filter(Boolean))].sort(),
    [projects]
  );

  const move = useCallback(
    (delta) => {
      setCursor((c) => {
        const n = new Date(c);
        if (view === "month") n.setMonth(n.getMonth() + delta);
        else if (view === "week") n.setDate(n.getDate() + 7 * delta);
        else n.setDate(n.getDate() + delta);
        return n;
      });
    },
    [view]
  );

  const title =
    view === "month"
      ? `${MONTHS[cursor.getMonth()]} ${cursor.getFullYear()}`
      : view === "week"
        ? `${range.from.slice(8, 10)}.${range.from.slice(5, 7)} — ${range.to.slice(8, 10)}.${range.to.slice(5, 7)}`
        : cursor.toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" });

  const toggleType = (key) =>
    setTypes((t) => (t.includes(key) ? t.filter((x) => x !== key) : [...t, key]));

  const openCreate = (dateStr, ev = null) => {
    setQuickDate(dateStr || null);
    setEditEvent(ev || null);
    setFormOpen(true);
  };

  const handleDelete = async () => {
    try {
      await api.deleteCalendarEvent(selectedEvent.id);
      toast("Событие удалено");
      setSelectedEvent(null);
      refresh();
    } catch (e) {
      toast(e.message, "error");
    }
  };

  return (
    <div className="mx-auto max-w-[1400px] px-4 py-4">
      {/* Toolbar (5.md §5, §10, §46) */}
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-1">
          <button onClick={() => move(-1)} className="btn btn-secondary btn-icon" title="Назад">
            <ChevronLeft className="h-4 w-4" />
          </button>
          <button onClick={() => setCursor(new Date())} className="btn btn-secondary btn-sm">
            Сегодня
          </button>
          <button onClick={() => move(1)} className="btn btn-secondary btn-icon" title="Вперёд">
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
        <div className="text-base font-semibold text-slate-700">{title}</div>

        <div className="ml-auto flex items-center gap-1.5">
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Поиск событий..."
              className="input !w-44 !py-1.5 !pl-8 text-sm"
            />
          </div>
          <button
            onClick={() => setFiltersOpen(!filtersOpen)}
            className={`btn btn-sm ${filtersOpen || types.length > 0 || projectId || manager || riskOnly ? "btn-indigo" : "btn-secondary"}`}
          >
            <Filter className="h-3.5 w-3.5" /> Фильтры
          </button>
          <div className="flex overflow-hidden rounded-md border border-slate-300">
            {["month", "week", "day"].map((v) => (
              <button
                key={v}
                onClick={() => setView(v)}
                className={`px-2.5 py-1.5 text-xs font-medium ${view === v ? "bg-indigo-600 text-white" : "bg-white text-slate-600 hover:bg-slate-50"}`}
              >
                {v === "month" ? "Месяц" : v === "week" ? "Неделя" : "День"}
              </button>
            ))}
          </div>
          <button onClick={() => openCreate(toISO(cursor))} className="btn btn-primary">
            <Plus className="h-4 w-4" /> Событие
          </button>
        </div>
      </div>

      {/* Filters panel (5.md §11-15) */}
      {filtersOpen && (
        <div className="mb-3 rounded-lg border border-slate-200 bg-white p-3">
          <div className="mb-2 text-[11px] font-bold uppercase tracking-wide text-slate-400">Показывать</div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 sm:grid-cols-4">
            {FILTER_GROUPS.map((g) => (
              <label key={g.key} className="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={types.includes(g.key)}
                  onChange={() => toggleType(g.key)}
                  className="h-4 w-4 rounded border-slate-300 text-indigo-600"
                />
                {g.label}
              </label>
            ))}
          </div>
          <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-4">
            <div>
              <label className="label">Проект</label>
              <select value={projectId} onChange={(e) => setProjectId(e.target.value)} className="input w-full">
                <option value="">Все проекты</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>{p.display_id} — {p.title}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Менеджер</label>
              <select value={manager} onChange={(e) => setManager(e.target.value)} className="input w-full">
                <option value="">Все</option>
                {managers.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>
            <div className="flex items-end">
              <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={riskOnly}
                  onChange={(e) => setRiskOnly(e.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-indigo-600"
                />
                Только проекты с риском
              </label>
            </div>
            {(types.length > 0 || projectId || manager || riskOnly) && (
              <div className="flex items-end justify-end">
                <button
                  onClick={() => { setTypes([]); setProjectId(""); setManager(""); setRiskOnly(false); }}
                  className="btn btn-ghost btn-sm text-slate-500"
                >
                  Сбросить
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {loading && <div className="py-16 text-center text-slate-400">Загрузка календаря…</div>}
      {error && (
        <div className="flex flex-col items-center gap-2 py-16 text-sm text-slate-500">
          ⚠️ {error}
          <button onClick={refresh} className="btn btn-secondary btn-sm">Повторить</button>
        </div>
      )}

      {!loading && !error && (
        <>
          {view === "month" && (
            <MonthView viewDate={cursor} items={items} onEventClick={setSelectedEvent} onDayClick={(d) => openCreate(d)} />
          )}
          {view === "week" && (
            <WeekView viewDate={cursor} items={items} onEventClick={setSelectedEvent} onDayClick={(d) => openCreate(d)} />
          )}
          {view === "day" && (
            <DayView dateObj={cursor} items={items} onEventClick={setSelectedEvent} onDayClick={(d) => openCreate(d)} />
          )}
        </>
      )}

      <EventPopover
        event={selectedEvent}
        onClose={() => setSelectedEvent(null)}
        onProjectClick={onProjectClick}
        onEditCustom={(ev) => { setSelectedEvent(null); openCreate(null, ev); }}
        onDeleteCustom={handleDelete}
      />
      <CustomEventForm
        open={formOpen}
        onClose={() => { setFormOpen(false); setEditEvent(null); }}
        onSaved={() => { refresh(); }}
        prefillDate={quickDate}
        event={editEvent}
        projects={projects}
      />
    </div>
  );
}