import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { Modal, Spinner, useToast } from "../components/ui.jsx";

/* ------------------------------------------------------------------ */
/* История импортов (6.md §36-37).                                    */
/* ------------------------------------------------------------------ */

const STATUS_STYLE = {
  COMPLETED: "bg-emerald-100 text-emerald-700",
  FAILED: "bg-red-100 text-red-700",
  VALIDATING: "bg-slate-100 text-slate-600",
  IMPORTING: "bg-indigo-100 text-indigo-700",
  PENDING: "bg-slate-100 text-slate-600",
  CANCELLED: "bg-slate-100 text-slate-500",
};

const STATUS_LABEL = {
  COMPLETED: "Завершён",
  FAILED: "Ошибка",
  VALIDATING: "Проверка",
  IMPORTING: "Импорт",
  PENDING: "Ожидание",
  CANCELLED: "Отменён",
};

export default function ImportHistoryModal({ open, onClose }) {
  const toast = useToast();
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    api.importHistory(30)
      .then(setJobs)
      .catch((e) => toast(e.message, "error"))
      .finally(() => setLoading(false));
  }, [open, toast]);

  if (!open) return null;

  const fmtDate = (iso) => {
    if (!iso) return "—";
    try {
      return new Date(iso).toLocaleString("ru-RU", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
    } catch (_) { return iso; }
  };

  return (
    <Modal open onClose={onClose} title="История импортов" wide>
      {loading ? (
        <Spinner />
      ) : jobs.length === 0 ? (
        <div className="py-10 text-center text-sm text-slate-400">Импортов пока не было</div>
      ) : (
        <div className="flex flex-col gap-2">
          {jobs.map((j) => (
            <div key={j.id} className="rounded-lg border border-slate-200">
              <button
                className="flex w-full items-center gap-3 px-3 py-2.5 text-left"
                onClick={() => setExpanded(expanded === j.id ? null : j.id)}
              >
                <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${STATUS_STYLE[j.status] || "bg-slate-100"}`}>
                  {STATUS_LABEL[j.status] || j.status}
                </span>
                <span className="flex-1 truncate text-sm font-medium">{j.file_name}</span>
                <span className="text-xs text-slate-400">{fmtDate(j.created_at)}</span>
                <span className="text-xs text-slate-500">
                  +{j.created_count} / ~{j.updated_count} / ×{j.skipped_count}
                </span>
                <span className="text-slate-300">{expanded === j.id ? "▴" : "▾"}</span>
              </button>
              {expanded === j.id && (
                <div className="border-t border-slate-100 px-3 py-2 text-xs">
                  <div className="mb-1 flex flex-wrap gap-3 text-slate-500">
                    <span>Источник: {j.source_type}</span>
                    <span>Лист: {j.sheet_name || "первый"}</span>
                    {j.completed_at && <span>Завершён: {fmtDate(j.completed_at)}</span>}
                  </div>
                  {j.errors?.length > 0 && (
                    <div className="max-h-32 overflow-auto rounded bg-slate-50 p-2">
                      {j.errors.slice(0, 20).map((e, i) => (
                        <div key={i} className={e.level === "ERROR" ? "text-red-600" : "text-amber-600"}>
                          стр. {e.row}: {e.error}
                        </div>
                      ))}
                      {j.errors.length > 20 && <div className="text-slate-400">… ещё {j.errors.length - 20}</div>}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
      <div className="mt-4 flex justify-end">
        <button className="btn btn-secondary" onClick={onClose}>Закрыть</button>
      </div>
    </Modal>
  );
}
