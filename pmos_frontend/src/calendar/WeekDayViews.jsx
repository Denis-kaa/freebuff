import React from "react";
import { WEEKDAYS, groupByDate, toISO } from "./useCalendar.js";
import { EVENT_LABEL, eventMeta, fmtEventTime } from "./meta.js";

/** Недельный вид (5.md §8): Пн..Вс, события по колонкам. */
export function WeekView({ viewDate, items, onEventClick, onDayClick, filterTypes }) {
  const byDate = groupByDate(items);
  const monday = new Date(viewDate);
  const dow = (monday.getDay() + 6) % 7;
  monday.setDate(monday.getDate() - dow);
  const today = toISO(new Date());

  const dayEvents = (d) => {
    const evs = byDate[toISO(d)] || [];
    if (!filterTypes || filterTypes.length === 0) return evs;
    return evs.filter((e) => filterTypes.includes(e.type));
  };

  return (
    <div className="grid grid-cols-7 gap-px overflow-hidden rounded-lg border border-slate-200 bg-slate-200">
      {WEEKDAYS.map((wd, i) => {
        const d = new Date(monday);
        d.setDate(monday.getDate() + i);
        const isToday = toISO(d) === today;
        return (
          <div key={i} className="flex min-h-[180px] flex-col bg-white">
            <div className={`py-1 text-center text-xs font-semibold ${isToday ? "text-indigo-600" : "text-slate-500"}`}>
              {wd} {d.getDate()}
            </div>
            <div className="flex-1 space-y-0.5 overflow-y-auto p-0.5" onClick={() => onDayClick && onDayClick(toISO(d))}>
              {dayEvents(d).map((e) => {
                const meta = eventMeta(e.type);
                return (
                  <div
                    key={e.id}
                    onClick={(ev) => {
                      ev.stopPropagation();
                      onEventClick && onEventClick(e);
                    }}
                    className={`cursor-pointer rounded border px-1.5 py-1 text-[10px] leading-tight ${meta.color}`}
                  >
                    <div className="truncate font-medium">{e.title}</div>
                    {e.metadata?.project_display_id && (
                      <div className="text-[9px] opacity-70">{e.metadata.project_display_id}</div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/** Дневной вид (5.md §7): all-day сверху, остальное — по времени. */
export function DayView({ dateObj, items, onEventClick, onDayClick, filterTypes }) {
  const byDate = groupByDate(items);
  const iso = toISO(dateObj);
  let evs = byDate[iso] || [];
  if (filterTypes && filterTypes.length) evs = evs.filter((e) => filterTypes.includes(e.type));

  const allDay = evs.filter((e) => e.all_day);
  const timed = evs.filter((e) => !e.all_day).sort((a, b) => (a.start_at < b.start_at ? -1 : 1));

  return (
    <div className="rounded-lg border border-slate-200 bg-white">
      <div className="border-b border-slate-100 px-3 py-2 text-sm font-semibold text-slate-700">
        {dateObj.toLocaleDateString("ru-RU", { weekday: "long", day: "numeric", month: "long" })}
      </div>
      {allDay.length > 0 && (
        <div className="border-b border-slate-100 p-2">
          <div className="mb-1 text-[10px] font-bold uppercase tracking-wide text-slate-400">Весь день</div>
          <div className="flex flex-wrap gap-1">
            {allDay.map((e) => (
              <button
                key={e.id}
                onClick={() => onEventClick && onEventClick(e)}
                className="flex items-center gap-1 rounded border px-1.5 py-0.5 text-xs"
                style={{ borderColor: "#e2e8f0" }}
              >
                <span className={`h-1.5 w-1.5 rounded-full ${eventMeta(e.type).dot}`} />
                {e.metadata?.project_display_id ? `${e.metadata.project_display_id} — ` : ""}{e.title}
              </button>
            ))}
          </div>
        </div>
      )}
      <div className="p-2" onClick={() => onDayClick && onDayClick(iso)}>
        {timed.length === 0 && allDay.length === 0 && (
          <div className="py-6 text-center text-sm text-slate-400">На этот день событий нет. Кликните, чтобы добавить.</div>
        )}
        <div className="space-y-1">
          {timed.map((e) => (
            <div key={e.id} className="flex items-start gap-2">
              <span className="w-14 shrink-0 pt-0.5 text-right text-[11px] font-medium text-slate-500">
                {fmtEventTime(e.start_at, e.all_day)}
              </span>
              <button
                onClick={(ev) => {
                  ev.stopPropagation();
                  onEventClick && onEventClick(e);
                }}
                className="flex-1 truncate rounded border-l-2 bg-slate-50 px-2 py-1 text-left text-xs hover:bg-indigo-50"
                style={{ borderLeftColor: eventMeta(e.type).dot.replace("bg-", "") }}
              >
                <span className="font-medium text-slate-700">{e.title}</span>
                {e.metadata?.project_display_id && (
                  <span className="ml-1 font-mono text-[10px] text-slate-400">{e.metadata.project_display_id}</span>
                )}
                {EVENT_LABEL[e.type] && <span className="ml-1 text-[10px] text-slate-400">· {EVENT_LABEL[e.type]}</span>}
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}