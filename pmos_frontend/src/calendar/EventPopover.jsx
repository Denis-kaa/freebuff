import React from "react";
import { ExternalLink, Pencil, Trash2 } from "lucide-react";
import { Modal } from "../components/ui.jsx";
import { EVENT_LABEL, eventMeta, fmtEventDate, fmtEventTime } from "./meta.js";

/**
 * Детали события (5.md §17-20). Клик никуда не уводит со страницы календаря.
 * Системное событие нельзя править здесь — кнопка ведёт к источнику (§24).
 */
export default function EventPopover({ event, onClose, onProjectClick, onEditCustom, onDeleteCustom }) {
  if (!event) return null;
  const meta = eventMeta(event.type);
  const Icon = meta.icon;
  const isCustom = event.source_type === "custom";
  const md = event.metadata || {};

  const rows = [];
  if (md.project_display_id) {
    rows.push(["Проект", `${md.project_display_id} — ${md.project_title || ""}`]);
  }
  if (event.project_item_id) {
    const itemName = event.source_type === "project_item" ? event.title.replace("Отгрузка сигнала: ", "") : md.item_name;
    if (itemName) rows.push(["Позиция", itemName]);
  }
  if (event.task_id && event.type === "TASK_DEADLINE") {
    if (md.assignee_name) rows.push(["Ответственный", md.assignee_name]);
  }
  if (event.type.startsWith("PAYMENT_")) {
    if (md.payment_percent) rows.push(["Оплата", md.payment_percent]);
    if (md.currency) rows.push(["Валюта", md.currency]);
  }
  if (event.type === "DOCUMENT") {
    rows.push(["Статус", event.status || "—"]);
  }

  return (
    <Modal open={!!event} onClose={onClose} title={EVENT_LABEL[event.type] || event.type}>
      <div className="flex items-start gap-2">
        <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${meta.color.split(" ")[0]}`} />
        <div>
          <div className="text-sm font-semibold text-slate-800">{event.title}</div>
          <div className="mt-0.5 text-xs text-slate-500">
            {fmtEventDate(event.start_at, event.all_day)}
            {event.all_day ? " · весь день" : ` · ${fmtEventTime(event.start_at, event.all_day)}`}
          </div>
        </div>
      </div>

      {rows.length > 0 && (
        <div className="mt-3 space-y-1 rounded-lg bg-slate-50 p-2.5 text-xs">
          {rows.map(([k, v]) => (
            <div key={k} className="flex gap-2">
              <span className="w-24 shrink-0 text-slate-400">{k}</span>
              <span className="text-slate-700">{v}</span>
            </div>
          ))}
        </div>
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        {event.project_id && (
          <button
            onClick={() => {
              onProjectClick?.(event.project_id, md.project_display_id);
              onClose();
            }}
            className="btn btn-primary btn-sm"
          >
            <ExternalLink className="h-3.5 w-3.5" /> Открыть проект
          </button>
        )}
        {event.task_id && (
          <button
            onClick={() => {
              onProjectClick?.(event.project_id, md.project_display_id);
              onClose();
            }}
            className="btn btn-secondary btn-sm"
          >
            Открыть задачу
          </button>
        )}
        {isCustom && (
          <>
            <button onClick={() => { onEditCustom?.(event); }} className="btn btn-secondary btn-sm">
              <Pencil className="h-3.5 w-3.5" /> Изменить
            </button>
            <button onClick={() => { onDeleteCustom?.(event); }} className="btn btn-ghost btn-sm text-red-600">
              <Trash2 className="h-3.5 w-3.5" /> Удалить
            </button>
          </>
        )}
      </div>

      {!isCustom && event.project_id && (
        <div className="mt-3 rounded bg-amber-50 px-2.5 py-1.5 text-[11px] text-amber-700">
          Системное событие — изменяется через источник. Нажмите «Открыть проект», чтобы изменить дедлайн/оплату.
        </div>
      )}
    </Modal>
  );
}