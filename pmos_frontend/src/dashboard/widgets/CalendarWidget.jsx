import React, { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, ExternalLink } from "lucide-react";
import MonthView from "../../calendar/MonthView.jsx";
import EventPopover from "../../calendar/EventPopover.jsx";
import CustomEventForm from "../../calendar/CustomEventForm.jsx";
import { useCalendar, toISO } from "../../calendar/useCalendar.js";
import { WidgetError } from "../shell.jsx";

const MONTHS = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
  "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"];

/**
 * Компактный Calendar Widget (5.md §28-29, §44): тот же Calendar Engine,
 * что и страница /calendar. Кнопка «Открыть календарь» ведёт на /calendar.
 */
export default function CalendarWidget({ config = {}, onProjectClick, onOpenCalendar }) {
  const now = new Date();
  const [viewDate, setViewDate] = useState(new Date(now.getFullYear(), now.getMonth(), 1));
  const [selected, setSelected] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const [quickDate, setQuickDate] = useState(null);

  const y = viewDate.getFullYear();
  const m = viewDate.getMonth();
  const from = toISO(new Date(y, m, 1));
  const nxt = new Date(y, m + 1, 1);
  const to = toISO(new Date(nxt.getTime() - 86400000));

  // настройки виджета -> типы событий (серверная фильтрация, §11)
  const show = {
    deadlines: config.show_deadlines !== false,
    tasks: config.show_tasks !== false,
    payments: config.show_payments !== false,
    production: config.show_production !== false,
  };
  const typeFilter = useMemo(() => {
    const types = [];
    if (show.deadlines) types.push("PROJECT_DEADLINE");
    if (show.tasks) types.push("TASK_DEADLINE");
    if (show.payments) types.push("PAYMENT_ADVANCE", "PAYMENT_FINAL");
    if (show.production) types.push("SIGNAL_SHIPMENT", "PRODUCTION", "BATCH_READY", "BATCH_SHIPMENT", "SIGNAL_FEEDBACK");
    return types;
  }, [show.deadlines, show.tasks, show.payments, show.production]);

  const { items, loading, error, refresh } = useCalendar(from, to, { types: typeFilter.join(",") }, [from, to, typeFilter]);

  const handleQuickCreate = (d) => {
    setQuickDate(d);
    setFormOpen(true);
  };

  return (
    <div className="flex h-full flex-col p-2">
      <div className="mb-1 flex items-center justify-between">
        <div className="flex items-center gap-1 text-sm font-semibold text-slate-700">
          <button onClick={() => setViewDate(new Date(y, m - 1, 1))} className="btn btn-ghost btn-xs">‹</button>
          <span>{MONTHS[m]} {y}</span>
          <button onClick={() => setViewDate(new Date(y, m + 1, 1))} className="btn btn-ghost btn-xs">›</button>
        </div>
        <button
          onClick={() => onOpenCalendar?.(toISO(viewDate), "month")}
          className="btn btn-ghost btn-xs text-indigo-600 hover:bg-indigo-50"
        >
          <ExternalLink className="h-3 w-3" /> Открыть календарь
        </button>
      </div>

      {loading && <div className="py-8 text-center text-xs text-slate-400">Загрузка…</div>}
      {error && <WidgetError message={error} onRetry={refresh} />}
      {!loading && !error && (
        <div className="min-h-0 flex-1 overflow-y-auto">
          <MonthView
            viewDate={viewDate}
            items={items}
            onEventClick={setSelected}
            onDayClick={handleQuickCreate}
          />
        </div>
      )}

      <EventPopover
        event={selected}
        onClose={() => setSelected(null)}
        onProjectClick={onProjectClick}
      />
      <CustomEventForm
        open={formOpen}
        onClose={() => setFormOpen(false)}
        onSaved={refresh}
        prefillDate={quickDate}
      />
    </div>
  );
}