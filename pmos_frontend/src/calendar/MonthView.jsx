import React from "react";
import { WEEKDAYS, groupByDate, toISO } from "./useCalendar.js";
import { EVENT_LABEL, eventMeta } from "./meta.js";

/**
 * Месячный вид (5.md §6): события внутри дня компактными чипами (+N ещё).
 * Используется и в Calendar Widget, и на странице /calendar (один движок).
 */
export default function MonthView({ viewDate, items, onEventClick, onDayClick, filterTypes }) {
  const byDate = groupByDate(items);

  const y = viewDate.getFullYear();
  const m = viewDate.getMonth();
  const from = new Date(y, m, 1);
  const firstDow = (from.getDay() + 6) % 7;
  const gridStart = new Date(y, m, 1 - firstDow);
  const today = toISO(new Date());

  const cellEvents = (d) => {
    const iso = toISO(d);
    const evs = byDate[iso] || [];
    if (!filterTypes || filterTypes.length === 0) return evs;
    return evs.filter((e) => filterTypes.includes(e.type));
  };

  return (
    <div className="grid grid-cols-7 gap-px overflow-hidden rounded-lg border border-slate-200 bg-slate-200">
      {WEEKDAYS.map((wd, i) => (
        <div key={i} className="bg-slate-50 py-1 text-center text-[10px] font-bold uppercase tracking-wide text-slate-400">
          {wd}
        </div>
      ))}
      {Array.from({ length: 42 }).map((_, i) => {
        const d = new Date(gridStart);
        d.setDate(gridStart.getDate() + i);
        const iso = toISO(d);
        const inMonth = d.getMonth() === m;
        const isToday = iso === today;
        const evs = cellEvents(d);
        return (
          <div
            key={i}
            onClick={() => onDayClick && onDayClick(iso)}
            className={`group min-h-[64px] cursor-pointer bg-white p-1 align-top transition hover:bg-indigo-50/60 ${
              inMonth ? "" : "bg-slate-50/80"
            } ${isToday ? "ring-1 ring-inset ring-indigo-400" : ""}`}
          >
            <div className={`mb-0.5 text-right text-[11px] ${isToday ? "text-indigo-600 font-bold" : inMonth ? "text-slate-500" : "text-slate-300"}`}>
              {d.getDate()}
            </div>
            <div className="space-y-0.5">
              {evs.slice(0, 3).map((e) => {
                const meta = eventMeta(e.type);
                return (
                  <div
                    key={e.id}
                    onClick={(ev) => {
                      ev.stopPropagation();
                      onEventClick && onEventClick(e);
                    }}
                    title={`${EVENT_LABEL[e.type] || e.type}: ${e.title}`}
                    className="flex items-center gap-1 truncate rounded px-1 py-0.5 text-[10px] leading-tight hover:bg-slate-100"
                  >
                    <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${meta.dot}`} />
                    <span className="truncate text-slate-600">
                      {e.metadata?.project_display_id ? `${e.metadata.project_display_id} — ` : ""}
                      {e.title}
                    </span>
                  </div>
                );
              })}
              {evs.length > 3 && (
                <div className="px-1 text-[10px] font-medium text-indigo-500">+ {evs.length - 3} ещё</div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}