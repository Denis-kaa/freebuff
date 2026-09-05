import React, { useCallback, useEffect, useState } from "react";
import { Copy, Plus, RefreshCw, Shield, X } from "lucide-react";
import { api } from "../api.js";
import { useAuth } from "../rbac/AuthContext.jsx";

const PERM_GROUPS = [
  { key: "project", label: "Проекты", perms: ["project.read", "project.create", "project.update", "project.delete", "project.import", "project.bulk_update"] },
  { key: "task", label: "Задачи", perms: ["task.read", "task.create", "task.update", "task.delete", "task.bulk_update"] },
  { key: "production", label: "Производство", perms: ["production.read", "production.update"] },
  { key: "finance", label: "Финансы", perms: ["finance.read", "finance.update"] },
  { key: "document", label: "Документы", perms: ["document.read", "document.create", "document.update", "document.delete"] },
  { key: "automation", label: "Автоматизации", perms: ["automation.read", "automation.create", "automation.update", "automation.delete"] },
  { key: "view", label: "Представления", perms: ["view.read", "view.create", "view.update", "view.delete"] },
  { key: "workspace", label: "Workspace", perms: ["workspace.read", "workspace.update"] },
  { key: "member", label: "Команда", perms: ["member.read", "member.invite", "member.update", "member.remove"] },
  { key: "role", label: "Роли", perms: ["role.manage"] },
];

const SHORT_LABEL = (p) => p.split(".")[1].replace(/_/g, " ");

export default function RolesView() {
  const { can } = useAuth();
  const [wsId, setWsId] = useState("");
  const [workspaces, setWorkspaces] = useState([]);
  const [roles, setRoles] = useState([]);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(null); // null | {isNew, code, name, description, permissions}
  const [error, setError] = useState("");

  const canManage = can("role.manage");

  const load = useCallback(async () => {
    if (!wsId) return;
    setRoles(await api.listRoles(wsId).catch(() => []));
  }, [wsId]);

  useEffect(() => {
    api.listWorkspaces().then((list) => {
      setWorkspaces(list);
      if (list[0]) setWsId(list[0].id);
    }).catch(() => {});
  }, []);
  useEffect(() => { load().catch(() => {}); }, [load]);

  const startNew = () => setEditing({ isNew: true, code: "", name: "", description: "", permissions: [] });
  const startEdit = (role) => {
    if (role.is_system) return; // системные роли не редактируются (правки — копией)
    setEditing({ isNew: false, id: role.id, code: role.code, name: role.name, description: role.description, permissions: role.permissions });
  };

  const togglePerm = (p) => {
    setEditing((e) => ({ ...e, permissions: e.permissions.includes(p) ? e.permissions.filter((x) => x !== p) : [...e.permissions, p] }));
  };

  const save = async (e) => {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      if (editing.isNew) {
        await api.createRole(wsId, { code: editing.code.toUpperCase(), name: editing.name, description: editing.description, permissions: editing.permissions });
      } else {
        await api.updateRole(wsId, editing.id, { name: editing.name, description: editing.description, permissions: editing.permissions });
      }
      setEditing(null);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const duplicate = async (role) => {
    setBusy(true);
    try {
      await api.duplicateRole(wsId, role.id);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-[1000px] px-4 py-6">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Роли</h1>
          <p className="text-sm text-slate-500">Права доступа ролей в workspace</p>
        </div>
        <div className="flex items-center gap-2">
          <button className="btn btn-secondary" onClick={() => load().catch(() => {})}><RefreshCw className="h-4 w-4" /> Обновить</button>
          {canManage && <button className="btn btn-indigo" onClick={startNew}><Plus className="h-4 w-4" /> Создать роль</button>}
        </div>
      </div>

      <div className="mb-4 flex items-center gap-2">
        <Shield className="h-4 w-4 text-indigo-600" />
        <select className="input max-w-xs" value={wsId} onChange={(e) => setWsId(e.target.value)}>
          {workspaces.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
        </select>
      </div>

      {error && <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}

      {editing ? (
        <form className="rounded-xl border border-slate-200 bg-white p-4" onSubmit={save}>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold">{editing.isNew ? "Новая роль" : `Роль: ${editing.name}`}</h2>
            <button type="button" className="btn btn-ghost !px-2 text-slate-400" onClick={() => setEditing(null)}><X className="h-4 w-4" /></button>
          </div>
          <div className="mb-4 grid gap-3 sm:grid-cols-3">
            <label className="text-sm"><span className="mb-1 block text-slate-500">Название</span><input className="input" required value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })} placeholder="Производственник" /></label>
            <label className="text-sm"><span className="mb-1 block text-slate-500">Код</span><input className="input" required disabled={!editing.isNew} value={editing.code} onChange={(e) => setEditing({ ...editing, code: e.target.value })} placeholder="PROD" /></label>
            <label className="text-sm"><span className="mb-1 block text-slate-500">Описание</span><input className="input" value={editing.description || ""} onChange={(e) => setEditing({ ...editing, description: e.target.value })} /></label>
          </div>
          <div className="space-y-3">
            {PERM_GROUPS.map((g) => (
              <div key={g.key} className="rounded-lg bg-slate-50 p-3">
                <div className="mb-1.5 text-sm font-medium text-slate-700">{g.label}</div>
                <div className="flex flex-wrap gap-3">
                  {g.perms.map((p) => (
                    <label key={p} className="flex items-center gap-1 text-xs text-slate-600">
                      <input type="checkbox" checked={editing.permissions.includes(p)} onChange={() => togglePerm(p)} /> {SHORT_LABEL(p)}
                    </label>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 flex justify-end gap-2">
            <button type="button" className="btn btn-ghost" onClick={() => setEditing(null)}>Отмена</button>
            <button className="btn btn-indigo" type="submit" disabled={busy}>{busy ? "..." : "Сохранить"}</button>
          </div>
        </form>
      ) : (
        <div className="space-y-3">
          {roles.map((r) => (
            <div key={r.id} className="rounded-xl border border-slate-200 bg-white p-4">
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 font-semibold">
                    {r.name}
                    {r.is_system && <span className="rounded-full bg-slate-200 px-2 py-0.5 text-[10px] uppercase text-slate-500">Системная</span>}
                  </div>
                  {r.description && <div className="text-xs text-slate-400">{r.description}</div>}
                </div>
                {canManage && !r.is_system && (
                  <button className="btn btn-ghost !px-2 text-slate-500" onClick={() => startEdit(r)}>Изменить</button>
                )}
                {canManage && (
                  <button className="btn btn-ghost !px-2 text-slate-500" title="Дублировать" onClick={() => duplicate(r)}><Copy className="h-4 w-4" /></button>
                )}
              </div>
              <div className="mt-2 flex flex-wrap gap-1">
                {r.permissions.length === 0 ? <span className="text-xs text-slate-300">нет прав</span> :
                  r.permissions.slice(0, 12).map((p) => <span key={p} className="rounded bg-indigo-50 px-1.5 py-0.5 text-[10px] text-indigo-600">{p}</span>)}
                {r.permissions.length > 12 && <span className="text-[10px] text-slate-400">+{r.permissions.length - 12}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
