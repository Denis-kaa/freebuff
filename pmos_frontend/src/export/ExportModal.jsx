import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { Modal, Spinner, useToast } from "../components/ui.jsx";

/* ------------------------------------------------------------------ */
/* Export (6.md §23-29): формирование файла и скачивание.             */
/* ------------------------------------------------------------------ */

const SCOPES = [
  { key: "all_projects", label: "Все проекты" },
  { key: "projects_items", label: "Проекты + позиции" },
  { key: "tasks", label: "Задачи" },
  { key: "calendar", label: "Календарь (события)" },
  { key: "legacy", label: "Legacy (старая структура)" },
  { key: "current_view", label: "Текущее представление" },
];

export default function ExportModal({ open, onClose, filters = {}, managers = [] }) {
  const toast = useToast();
  const [scope, setScope] = useState("all_projects");
  const [format, setFormat] = useState("xlsx");
  const [manager, setManager] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [busy, setBusy] = useState(false);
  const [meta, setMeta] = useState(null);

  useEffect(() => {
    if (open) { setScope("all_projects"); setFormat("xlsx"); setManager(""); setFrom(""); setTo(""); setMeta(null); }
  }, [open]);

  if (!open) return null;

  const doExport = async () => {
    setBusy(true);
    try {
      const f = { ...filters };
      if (manager) f.manager = manager;
      if (from) f.from = from;
      if (to) f.to = to;
      const payload = { scope, filters: f, include_archived: false };
      const res = format === "csv" ? await api.exportCsv(payload) : await api.exportExcel(payload);
      setMeta(res);
      toast("Файл сформирован");
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal open onClose={onClose} title="Экспорт в Excel / CSV" wide>
      <div className="flex flex-col gap-4">
        {/* Область */}
        <div>
          <label className="label">Что экспортировать</label>
          <div className="grid grid-cols-2 gap-1.5">
            {SCOPES.map((s) => (
              <button
                key={s.key}
                className={`rounded-lg border px-3 py-2 text-left text-sm ${
                  scope === s.key ? "border-indigo-500 bg-indigo-50 text-indigo-700" : "border-slate-200 hover:bg-slate-50"
                }`}
                onClick={() => setScope(s.key)}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>

        {/* Формат */}
        <div className="flex items-center gap-4">
          <label className="label !mb-0">Формат:</label>
          <div className="flex gap-1.5">
            {["xlsx", "csv"].map((f) => (
              <button
                key={f}
                className={`btn ${format === f ? "btn-primary" : "btn-secondary"}`}
                onClick={() => setFormat(f)}
              >
                {f.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        {/* Фильтры */}
        <div className="grid grid-cols-3 gap-2">
          <div>
            <label className="label">Менеджер</label>
            <select className="input" value={manager} onChange={(e) => setManager(e.target.value)}>
              <option value="">Все</option>
              {managers.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
          <div>
            <label className="label">С</label>
            <input type="date" className="input" value={from} onChange={(e) => setFrom(e.target.value)} />
          </div>
          <div>
            <label className="label">По</label>
            <input type="date" className="input" value={to} onChange={(e) => setTo(e.target.value)} />
          </div>
        </div>

        {busy && <Spinner label="Формирование файла..." />}

        {/* Результат */}
        {meta && (
          <div className="flex items-center justify-between rounded-lg bg-emerald-50 px-4 py-3">
            <div className="text-sm text-emerald-700">
              ✅ {meta.filename} ({meta.rows} строк)
            </div>
            <a className="btn btn-primary" href={meta.download_url}>
              Скачать
            </a>
          </div>
        )}

        <div className="flex justify-end gap-2">
          <button className="btn btn-secondary" onClick={onClose}>Закрыть</button>
          <button className="btn btn-primary" onClick={doExport} disabled={busy}>
            Сформировать
          </button>
        </div>
      </div>
    </Modal>
  );
}
