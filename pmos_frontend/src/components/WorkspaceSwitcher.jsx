import React, { useState } from "react";
import { Building2, Check, ChevronDown, Plus, X } from "lucide-react";
import { useAuth } from "../rbac/AuthContext.jsx";
import { useToast } from "./ui.jsx";

export default function WorkspaceSwitcher() {
  const { workspaces, workspaceId, workspace, switchWorkspace, createWorkspace } = useAuth();
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState({ name: "", timezone: "UTC", default_currency: "RUB" });
  const [busy, setBusy] = useState(false);

  const doCreate = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) { toast("Укажите название workspace", "error"); return; }
    setBusy(true);
    try {
      await createWorkspace(form);
      toast("Workspace создан");
      setCreateOpen(false);
      setForm({ name: "", timezone: "UTC", default_currency: "RUB" });
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="relative">
      <button
        className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-sm font-medium text-slate-700 hover:border-indigo-300"
        onClick={() => setOpen((v) => !v)}
      >
        <Building2 className="h-4 w-4 text-indigo-600" />
        <span className="max-w-[160px] truncate">{workspace?.name || "Workspace"}</span>
        <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute left-0 top-full z-50 mt-1 w-72 rounded-xl border border-slate-200 bg-white p-2 shadow-lg">
            <div className="px-2 py-1 text-xs font-semibold uppercase tracking-wide text-slate-400">Workspace</div>
            <div className="max-h-56 space-y-0.5 overflow-auto">
              {workspaces.map((w) => (
                <button
                  key={w.id}
                  className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-slate-50"
                  onClick={() => { switchWorkspace(w.id); setOpen(false); }}
                >
                  <Building2 className="h-4 w-4 text-slate-400" />
                  <span className="flex-1 truncate text-left">{w.name}</span>
                  {w.id === workspaceId && <Check className="h-4 w-4 text-indigo-600" />}
                </button>
              ))}
              {workspaces.length === 0 && (
                <div className="px-2 py-1.5 text-sm text-slate-400">Нет workspace</div>
              )}
            </div>
            <div className="mt-1 border-t border-slate-100 pt-1">
              <button
                className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-sm text-indigo-600 hover:bg-indigo-50"
                onClick={() => { setOpen(false); setCreateOpen(true); }}
              >
                <Plus className="h-4 w-4" /> Создать workspace
              </button>
            </div>
          </div>
        </>
      )}

      {createOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" onClick={() => setCreateOpen(false)}>
          <form
            className="w-full max-w-md rounded-xl bg-white p-5 shadow-xl"
            onClick={(e) => e.stopPropagation()}
            onSubmit={doCreate}
          >
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-bold">Новый workspace</h2>
              <button type="button" className="btn btn-ghost !px-2 text-slate-400" onClick={() => setCreateOpen(false)}><X className="h-4 w-4" /></button>
            </div>
            <div className="space-y-3">
              <label className="block text-sm">
                <span className="mb-1 block text-slate-500">Название</span>
                <input className="input" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Production Team" />
              </label>
              <label className="block text-sm">
                <span className="mb-1 block text-slate-500">Часовой пояс</span>
                <select className="input" value={form.timezone} onChange={(e) => setForm({ ...form, timezone: e.target.value })}>
                  {["UTC", "Europe/Moscow", "Europe/Kyiv", "Asia/Almaty", "Asia/Tashkent", "Asia/Dubai"].map((tz) => <option key={tz}>{tz}</option>)}
                </select>
              </label>
              <label className="block text-sm">
                <span className="mb-1 block text-slate-500">Валюта по умолчанию</span>
                <select className="input" value={form.default_currency} onChange={(e) => setForm({ ...form, default_currency: e.target.value })}>
                  {["RUB", "USD", "EUR", "USDT"].map((cur) => <option key={cur}>{cur}</option>)}
                </select>
              </label>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" className="btn btn-ghost" onClick={() => setCreateOpen(false)}>Отмена</button>
              <button className="btn btn-indigo" type="submit" disabled={busy}>{busy ? "..." : "Создать"}</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
