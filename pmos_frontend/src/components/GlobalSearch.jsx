import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { Modal, Spinner, useToast } from "./ui.jsx";

const GROUPS = [
  ["projects", "Проекты"], ["tasks", "Задачи"], ["items", "Позиции"],
  ["clients", "Клиенты"], ["documents", "Документы"],
];

export default function GlobalSearch({ onProjectClick }) {
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const onKey = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault(); setOpen(true);
      }
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (!open) return;
    const value = query.trim();
    if (!value) { setData(null); return; }
    const timer = setTimeout(() => {
      setLoading(true);
      api.globalSearch(value).then(setData).catch((e) => toast(e.message, "error")).finally(() => setLoading(false));
    }, 220);
    return () => clearTimeout(timer);
  }, [open, query, toast]);

  const openResult = (type, row) => {
    if (type === "projects") onProjectClick?.(row.id, row.display_id);
    else if (row.project_id) onProjectClick?.(row.project_id, row.project_display_id);
    setOpen(false);
  };

  return (
    <>
      <button className="btn btn-ghost !px-2.5 text-slate-500" onClick={() => setOpen(true)} title="Ctrl+K">
        🔎 <span className="hidden sm:inline">Поиск</span><kbd className="ml-1 hidden rounded border border-slate-300 px-1 text-[10px] sm:inline">Ctrl K</kbd>
      </button>
      <Modal open={open} onClose={() => setOpen(false)} title="Глобальный поиск" wide>
        <div className="flex flex-col gap-3">
          <input autoFocus className="input text-base" placeholder="Проекты, задачи, позиции, документы..." value={query} onChange={(e) => setQuery(e.target.value)} />
          {loading && <Spinner label="Ищем..." />}
          {!loading && query.trim() && data && (
            <div className="max-h-[55vh] overflow-auto">
              {GROUPS.map(([type, label]) => {
                const rows = data.results?.[type] || [];
                if (!rows.length) return null;
                return <section key={type} className="mb-3"><h4 className="mb-1 text-xs font-semibold uppercase text-slate-400">{label}</h4>{rows.map((row, index) => <button key={row.id || row.name || index} className="block w-full rounded px-2 py-2 text-left text-sm hover:bg-indigo-50" onClick={() => openResult(type, row)}><span className="font-medium">{row.display_id || row.title || row.name || row.document_type}</span>{row.title && row.display_id && <span className="ml-2 text-slate-500">— {row.title}</span>}{row.project_display_id && <span className="ml-2 text-xs text-slate-400">({row.project_display_id})</span>}</button>)}</section>;
              })}
              {!GROUPS.some(([type]) => (data.results?.[type] || []).length) && <div className="py-8 text-center text-sm text-slate-400">Ничего не найдено</div>}
            </div>
          )}
          {!query.trim() && <div className="py-8 text-center text-sm text-slate-400">Начните вводить запрос</div>}
        </div>
      </Modal>
    </>
  );
}
