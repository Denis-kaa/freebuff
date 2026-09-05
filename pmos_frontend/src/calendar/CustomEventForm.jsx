import React, { useEffect, useState } from "react";
import { Modal, useToast } from "../components/ui.jsx";
import { api } from "../api.js";
import { CUSTOM_EVENT_TYPES } from "./meta.js";

export default function CustomEventForm({ open, onClose, onSaved, prefillDate, event, projects }) {
  const toast = useToast();
  const [options, setOptions] = useState(projects || null);
  useEffect(() => {
    if (projects) {
      setOptions(projects);
    } else if (options === null) {
      api.widgetData.projects(50).then(setOptions).catch(() => setOptions([]));
    }
  }, [projects]); // eslint-disable-line react-hooks/exhaustive-deps
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [type, setType] = useState("REMINDER");
  const [date, setDate] = useState("");
  const [time, setTime] = useState("09:00");
  const [allDay, setAllDay] = useState(false);
  const [projectId, setProjectId] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    if (event) {
      setTitle(event.title || "");
      setDescription(event.description || "");
      setType((event.type in { REMINDER: 1, MEETING: 1, CALL: 1, OTHER: 1, CUSTOM: 1 }) ? event.type : "OTHER");
      const d = new Date(event.start_at);
      setDate(d.toISOString().slice(0, 10));
      setTime(d.toISOString().slice(11, 16));
      setAllDay(!!event.all_day);
      setProjectId(event.project_id || "");
    } else {
      setTitle("");
      setDescription("");
      setType("REMINDER");
      setAllDay(false);
      setProjectId("");
      const d = prefillDate ? new Date(`${prefillDate}T12:00:00`) : new Date();
      setDate(d.toISOString().slice(0, 10));
      setTime("09:00");
    }
  }, [open, event, prefillDate]);

  const submit = async () => {
    if (!title.trim() || !date) return;
    setSaving(true);
    try {
      const startAt = allDay
        ? `${date}T00:00:00Z`
        : new Date(`${date}T${time}:00`).toISOString();
      const payload = {
        title: title.trim(),
        description: description.trim() || null,
        event_type: type,
        start_at: startAt,
        all_day: allDay,
        project_id: projectId || null,
      };
      if (event) {
        await api.updateCalendarEvent(event.id, payload);
        toast("Событие обновлено");
      } else {
        await api.createCalendarEvent(payload);
        toast("Событие создано");
      }
      onSaved?.();
      onClose();
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title={event ? "Изменить событие" : "Новое событие"}>
      <div className="space-y-3">
        <div>
          <label className="label">Название</label>
          <input autoFocus value={title} onChange={(e) => setTitle(e.target.value)} className="input w-full" placeholder="Например, Встреча с фабрикой" />
        </div>
        <div>
          <label className="label">Тип</label>
          <div className="grid grid-cols-2 gap-1.5">
            {CUSTOM_EVENT_TYPES.map((t) => (
              <button
                key={t.value}
                type="button"
                onClick={() => setType(t.value)}
                className={`rounded-lg border px-2 py-1.5 text-sm ${type === t.value ? "border-indigo-400 bg-indigo-50 text-indigo-700" : "border-slate-200 text-slate-600 hover:border-slate-300"}`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="label">Дата</label>
            <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="input w-full" />
          </div>
          <div>
            <label className="label">{allDay ? "Весь день" : "Время"}</label>
            {allDay ? (
              <div className="input flex items-center text-slate-400">Весь день</div>
            ) : (
              <input type="time" value={time} onChange={(e) => setTime(e.target.value)} className="input w-full" />
            )}
          </div>
        </div>
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input type="checkbox" checked={allDay} onChange={(e) => setAllDay(e.target.checked)} className="h-4 w-4 rounded border-slate-300 text-indigo-600" />
          Весь день (без времени)
        </label>
        <div>
          <label className="label">Проект (необязательно)</label>            <select value={projectId} onChange={(e) => setProjectId(e.target.value)} className="input w-full">
              <option value="">— Без проекта —</option>
              {(options || []).map((p) => (
                <option key={p.id} value={p.id}>{p.display_id} — {p.title}</option>
              ))}
            </select>
        </div>
        <div>
          <label className="label">Описание</label>
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} className="input w-full" rows={2} />
        </div>
        <div className="flex justify-end gap-2 pt-1">
          <button onClick={onClose} className="btn btn-ghost">Отмена</button>
          <button onClick={submit} disabled={saving || !title.trim() || !date} className="btn btn-primary">
            {saving ? "Сохраняем..." : event ? "Сохранить" : "Создать"}
          </button>
        </div>
      </div>
    </Modal>
  );
}