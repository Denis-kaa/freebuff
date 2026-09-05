import React, { useEffect, useState } from "react";
import { Bell, Check } from "lucide-react";
import { api } from "../api.js";

export default function NotificationCenter() {
  const [groups, setGroups] = useState([]); const [open, setOpen] = useState(false);
  const load = () => api.groupedNotifications().then(setGroups).catch(() => {});
  useEffect(() => { load(); const timer = setInterval(load, 60000); return () => clearInterval(timer); }, []);
  const unread = groups.reduce((sum, group) => sum + (group.unread || 0), 0);
  const mark = async (id) => { await api.markNotificationRead(id).catch(() => {}); load(); };
  const markAll = async () => { await api.markAllNotificationsRead().catch(() => {}); setGroups([]); };
  return <div className="relative">
    <button onClick={() => setOpen((x) => !x)} className="btn btn-ghost relative !px-2" title="Уведомления"><Bell className="h-4 w-4" />{unread > 0 && <span className="absolute -right-0.5 -top-0.5 min-w-4 rounded-full bg-red-600 px-1 text-center text-[10px] font-bold text-white">{unread > 9 ? "9+" : unread}</span>}</button>
    {open && <><div className="fixed inset-0 z-40" onClick={() => setOpen(false)} /><div className="absolute right-0 z-50 mt-2 w-80 rounded-xl border border-slate-200 bg-white p-2 shadow-xl"><div className="flex items-center justify-between px-2 py-1"><b className="text-sm">Уведомления</b>{unread > 0 && <button onClick={markAll} className="text-xs text-indigo-600">Прочитать все</button>}</div>{groups.length === 0 ? <div className="p-5 text-center text-sm text-slate-400">Новых уведомлений нет</div> : <div className="mt-1 max-h-80 overflow-auto">{groups.map((group) => <div key={String(group.entity_id || group.title)} className="mb-1 rounded-lg border border-slate-100 p-2"><div className="flex items-center justify-between"><div className="text-sm font-medium text-slate-700">{group.title}</div>{group.unread > 1 && <span className="text-[10px] text-slate-400">{group.unread} новых</span>}</div>{group.items.slice(0, 3).map((n) => <div key={n.id} className="mt-1 flex gap-2"><div className="min-w-0 flex-1"><div className="text-xs text-slate-600">{n.message}</div><div className="text-[10px] text-slate-400">{new Date(n.created_at).toLocaleString()}</div></div>{!n.read && <button onClick={() => mark(n.id)} className="btn btn-ghost btn-icon-sm self-start" title="Прочитать"><Check className="h-3.5 w-3.5" /></button>}</div>)}</div>)}</div>}</div></>}
  </div>;
}
