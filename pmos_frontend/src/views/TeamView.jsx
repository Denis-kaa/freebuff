import React, { useCallback, useEffect, useState } from "react";
import { Mail, RefreshCw, UserPlus, Users, X } from "lucide-react";
import { api } from "../api.js";
import { useAuth } from "../rbac/AuthContext.jsx";

export default function TeamView() {
  const { can, role } = useAuth();
  const [workspaces, setWorkspaces] = useState([]);
  const [wsId, setWsId] = useState("");
  const [members, setMembers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [invitations, setInvitations] = useState([]);
  const [teams, setTeams] = useState([]);
  const [newTeamName, setNewTeamName] = useState("");
  const [busy, setBusy] = useState(false);
  const [invite, setInvite] = useState({ email: "", role_code: "MEMBER" });
  const [error, setError] = useState("");
  const [transferTarget, setTransferTarget] = useState("");

  const canInvite = can("member.invite");
  const canUpdate = can("member.update");
  const canRemove = can("member.remove");
  const canTransfer = can("workspace.update") && role === "OWNER";

  const loadWorkspaces = useCallback(async () => {
    const list = await api.listWorkspaces();
    setWorkspaces(list);
    if (list[0]) setWsId(list[0].id);
  }, []);

  const load = useCallback(async () => {
    if (!wsId) return;
    const [m, r, i, t] = await Promise.all([
      api.listMembers(wsId).catch(() => []),
      api.listRoles(wsId).catch(() => []),
      api.listInvitations(wsId).catch(() => []),
      api.listTeams(wsId).catch(() => []),
    ]);
    setMembers(m);
    setRoles(r);
    setInvitations(i);
    setTeams(t);
  }, [wsId]);

  useEffect(() => { loadWorkspaces().catch(() => {}); }, [loadWorkspaces]);
  useEffect(() => { load().catch(() => {}); }, [load]);

  const doInvite = async (e) => {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      await api.inviteMember(wsId, invite);
      setInvite({ email: "", role_code: "MEMBER" });
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const changeRole = async (memberId, roleId) => {
    setBusy(true);
    try {
      await api.updateMember(wsId, memberId, { role_id: roleId });
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const removeMember = async (memberId) => {
    if (!window.confirm("Удалить участника из workspace?")) return;
    setBusy(true);
    try {
      await api.removeMember(wsId, memberId);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const transfer = async () => {
    if (!transferTarget) return;
    if (!window.confirm("Передать владение workspace выбранному участнику? Текущая роль станет ADMIN.")) return;
    setBusy(true); setError("");
    try {
      await api.transferOwnership(wsId, transferTarget);
      setTransferTarget("");
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const revoke = async (invitationId) => {
    setBusy(true);
    try {
      await api.revokeInvitation(wsId, invitationId);
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
          <h1 className="text-xl font-bold">Команда</h1>
          <p className="text-sm text-slate-500">Пользователи workspace и приглашения</p>
        </div>
        <button className="btn btn-secondary" onClick={() => { load().catch(() => {}); }}><RefreshCw className="h-4 w-4" /> Обновить</button>
      </div>

      <div className="mb-4 flex items-center gap-2">
        <Users className="h-4 w-4 text-indigo-600" />
        <select className="input max-w-xs" value={wsId} onChange={(e) => setWsId(e.target.value)}>
          {workspaces.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
        </select>
      </div>

      {error && <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}

      {canInvite && (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="mb-3 flex items-center gap-2 font-semibold"><UserPlus className="h-4 w-4 text-indigo-600" /> Пригласить</h2>
          <form className="flex flex-wrap items-center gap-3" onSubmit={doInvite}>
            <div className="flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-1.5">
              <Mail className="h-4 w-4 text-slate-400" />
              <input className="bg-transparent outline-none w-56" type="email" required placeholder="ivan@example.com" value={invite.email} onChange={(e) => setInvite({ ...invite, email: e.target.value })} />
            </div>
            <select className="input w-40" value={invite.role_code} onChange={(e) => setInvite({ ...invite, role_code: e.target.value })}>
              {roles.filter((r) => r.is_system).map((r) => <option key={r.code} value={r.code}>{r.name}</option>)}
            </select>
            <button className="btn btn-indigo" type="submit" disabled={busy}>{busy ? "..." : "Пригласить"}</button>
          </form>
        </section>
      )}

      <section className="mt-5 rounded-xl border border-slate-200 bg-white p-4">
        <div className="mb-3 flex items-center justify-between gap-3">
          <h2 className="font-semibold">Участники</h2>
          {canTransfer && (
            <div className="flex items-center gap-2">
              <select className="input w-48" value={transferTarget} onChange={(e) => setTransferTarget(e.target.value)}>
                <option value="">Передать workspace...</option>
                {members.filter((m) => m.status === "ACTIVE" && m.role_code !== "OWNER").map((m) => <option key={m.id} value={m.id}>{m.display_name || m.email}</option>)}
              </select>
              <button className="btn btn-secondary" disabled={!transferTarget || busy} onClick={transfer}>Передать</button>
            </div>
          )}
        </div>
        {members.length === 0 ? (
          <p className="text-sm text-slate-400">Пока нет участников.</p>
        ) : (
          <div className="divide-y divide-slate-100">
            {members.map((m) => (
              <div key={m.id} className="flex flex-wrap items-center gap-3 py-2.5">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-100 font-bold text-indigo-700">
                  {(m.display_name || m.email || "?")[0].toUpperCase()}
                </div>
                <div className="min-w-[180px] flex-1">
                  <div className="text-sm font-medium">{m.display_name || "—"}</div>
                  <div className="text-xs text-slate-400">{m.email}</div>
                </div>
                <span className={`rounded-full px-2 py-0.5 text-xs ${m.status === "ACTIVE" ? "bg-emerald-100 text-emerald-700" : "bg-slate-200 text-slate-600"}`}>{m.status}</span>
                {canUpdate ? (
                  <select className="input w-40" value={m.role_id} disabled={busy} onChange={(e) => changeRole(m.id, e.target.value)}>
                    {roles.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                  </select>
                ) : (
                  <span className="text-sm text-slate-600">{m.role_code}</span>
                )}
                {canRemove && (
                  <button className="btn btn-ghost !px-2 text-slate-400 hover:text-red-600" title="Удалить" onClick={() => removeMember(m.id)}><X className="h-4 w-4" /></button>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {canUpdate && (
        <section className="mt-5 rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="mb-3 font-semibold">Команды</h2>
          <form className="mb-3 flex gap-2" onSubmit={async (e) => { e.preventDefault(); if (!newTeamName.trim()) return; setBusy(true); try { await api.createTeam(wsId, { name: newTeamName.trim() }); setNewTeamName(""); await load(); } catch (err) { setError(err.message); } finally { setBusy(false); } }}>
            <input className="input flex-1" placeholder="Название команды" value={newTeamName} onChange={(e) => setNewTeamName(e.target.value)} />
            <button className="btn btn-indigo" disabled={busy}>Создать команду</button>
          </form>
          <div className="space-y-3">
            {teams.map((team) => (
              <div key={team.id} className="rounded-lg border border-slate-100 p-3">
                <div className="flex items-center justify-between"><span className="font-medium">{team.name}</span><button className="btn btn-ghost text-red-600" onClick={async () => { await api.deleteTeam(wsId, team.id); await load(); }}>Удалить</button></div>
                <div className="mt-2 flex flex-wrap gap-2">{members.map((member) => <button key={member.id} className={`rounded-full px-2 py-1 text-xs ${team.member_ids.includes(member.user_id) ? "bg-indigo-100 text-indigo-700" : "bg-slate-100 text-slate-600"}`} onClick={async () => { if (team.member_ids.includes(member.user_id)) await api.removeTeamMember(wsId, team.id, member.id); else await api.addTeamMember(wsId, team.id, member.id); await load(); }}>{member.display_name || member.email}</button>)}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {invitations.length > 0 && (
        <section className="mt-5 rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="mb-3 font-semibold">Приглашения</h2>
          <div className="divide-y divide-slate-100">
            {invitations.map((i) => (
              <div key={i.id} className="flex items-center gap-3 py-2 text-sm">
                <span className="flex-1">{i.email}</span>
                <span className="text-slate-500">{i.role_code}</span>
                <span className="text-xs text-slate-400">до {new Date(i.expires_at).toLocaleDateString()}</span>
                {i.accepted_at ? <span className="text-emerald-600 text-xs">Принято</span> : canInvite && <button className="btn btn-ghost !px-2 text-slate-400 hover:text-red-600" onClick={() => revoke(i.id)}><X className="h-4 w-4" /></button>}
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
