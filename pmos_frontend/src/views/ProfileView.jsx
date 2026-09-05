import React, { useEffect, useState } from "react";
import { RefreshCw, Save, User } from "lucide-react";
import { api } from "../api.js";
import { useAuth } from "../rbac/AuthContext.jsx";

const TIMEZONES = [
  "UTC", "Europe/Moscow", "Europe/Kyiv", "Europe/Minsk", "Europe/Berlin", "Europe/London",
  "Asia/Almaty", "Asia/Tashkent", "Asia/Dubai", "Asia/Yerevan", "Asia/Baku", "Asia/Tbilisi",
  "Asia/Kolkata", "Asia/Shanghai", "Asia/Tokyo", "America/New_York", "America/Los_Angeles",
];

export default function ProfileView() {
  const { role, refresh } = useAuth();
  const [me, setMe] = useState(null);
  const [form, setForm] = useState({ name: "", avatar_url: "", timezone: "UTC", language: "ru" });
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    const m = await api.getMe();
    setMe(m);
    setForm({ name: m.name || "", avatar_url: m.avatar_url || "", timezone: m.timezone || "UTC", language: m.language || "ru" });
  };

  useEffect(() => { load().catch(() => {}); }, []);

  const save = async (e) => {
    e.preventDefault();
    setBusy(true); setSaved(false); setError("");
    try {
      await api.updateMe(form);
      setSaved(true);
      refresh();
      load().catch(() => {});
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-[700px] px-4 py-6">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Профиль</h1>
          <p className="text-sm text-slate-500">Личные данные и часовой пояс</p>
        </div>
        <button className="btn btn-secondary" onClick={() => load().catch(() => {})}><RefreshCw className="h-4 w-4" /> Обновить</button>
      </div>

      {me && (
        <div className="mb-5 flex items-center gap-4 rounded-xl border border-slate-200 bg-white p-4">
          {me.avatar_url ? (
            <img src={me.avatar_url} alt="" className="h-14 w-14 rounded-full object-cover" />
          ) : (
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-indigo-100 text-xl font-bold text-indigo-700">
              {(me.name || me.email || "?")[0].toUpperCase()}
            </div>
          )}
          <div>
            <div className="flex items-center gap-2 font-semibold">{me.display_name || me.name}
              <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-xs text-indigo-700">{role}</span>
            </div>
            <div className="text-sm text-slate-500">{me.email}</div>
          </div>
        </div>
      )}

      {error && <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
      {saved && <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">Сохранено</div>}

      <form className="rounded-xl border border-slate-200 bg-white p-4" onSubmit={save}>
        <h2 className="mb-4 flex items-center gap-2 font-semibold"><User className="h-4 w-4 text-indigo-600" /> Личные данные</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="text-sm"><span className="mb-1 block text-slate-500">Имя</span><input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
          <label className="text-sm"><span className="mb-1 block text-slate-500">Avatar URL</span><input className="input" value={form.avatar_url} onChange={(e) => setForm({ ...form, avatar_url: e.target.value })} placeholder="https://..." /></label>
          <label className="text-sm"><span className="mb-1 block text-slate-500">Часовой пояс</span>
            <select className="input" value={form.timezone} onChange={(e) => setForm({ ...form, timezone: e.target.value })}>
              {TIMEZONES.map((tz) => <option key={tz} value={tz}>{tz}</option>)}
            </select>
          </label>
          <label className="text-sm"><span className="mb-1 block text-slate-500">Язык</span>
            <select className="input" value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value })}>
              <option value="ru">Русский</option>
              <option value="en">English</option>
            </select>
          </label>
        </div>
        <div className="mt-4 flex justify-end">
          <button className="btn btn-indigo" type="submit" disabled={busy}><Save className="h-4 w-4" /> {busy ? "..." : "Сохранить"}</button>
        </div>
      </form>
    </div>
  );
}
