import React, { useState } from "react";
import { api } from "../api.js";
import { fieldKindForCustom } from "../columns.js";
import { Field } from "../components/ui.jsx";

const SYSTEM_FIELDS = [
  { field: "title", label: "Название проекта", kind: "text", required: true },
  { field: "client_legal_name", label: "Юр. лицо", kind: "text" },
  { field: "manager_name", label: "Менеджер", kind: "text" },
  { field: "stage", label: "Этап", kind: "text" },
  { field: "deadline", label: "Дедлайн", kind: "date" },
  { field: "risk_level", label: "Риск", kind: "select", options: ["Нет", "Низкий", "Средний", "Высокий", "Критический"] },
  { field: "next_action", label: "Следующее действие", kind: "text" },
  { field: "next_action_date", label: "Дата след. действия", kind: "date" },
  { field: "payment_percent", label: "Оплата %", kind: "select", options: ["0%", "50%", "80%", "100%"] },
  { field: "currency", label: "Валюта", kind: "text" },
  { field: "advance_date", label: "Дата аванса", kind: "date" },
  { field: "final_payment_date", label: "Дата доплаты", kind: "date" },
  { field: "delivery_address", label: "Адрес доставки", kind: "text" },
  { field: "delivery_paid", label: "Оплата доставки", kind: "text" },
];

export default function ProjectForm({ existing, customFields, onSaved, onCancel }) {
  const [form, setForm] = useState(() => {
    const base = {};
    SYSTEM_FIELDS.forEach((f) => {
      base[f.field] = existing?.[f.field] ?? "";
    });
    return base;
  });
  const [custom, setCustom] = useState(() => {
    const obj = {};
    customFields.forEach((cf) => {
      obj[cf.slug] = existing?.custom_values?.[cf.slug] ?? cf.default_value ?? "";
    });
    return obj;
  });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState(null);

  const setF = (field, v) => setForm((f) => ({ ...f, [field]: v }));
  const setC = (slug, v) => setCustom((c) => ({ ...c, [slug]: v }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.title) {
      setErr("Название проекта обязательно");
      return;
    }
    setSaving(true);
    setErr(null);
    try {
      // Формируем payload: пустые строки -> null, даты оставляем строками YYYY-MM-DD
      const payload = {};
      Object.entries(form).forEach(([k, v]) => {
        payload[k] = v === "" || v === null ? null : v;
      });
      let saved;
      if (existing) {
        saved = await api.updateProject(existing.id, payload);
      } else {
        saved = await api.createProject(payload);
      }
      // Custom values
      const cv = {};
      Object.entries(custom).forEach(([k, v]) => {
        if (v !== "" && v !== null) cv[k] = coerce(v);
      });
      if (Object.keys(cv).length) {
        // нужно отправить отдельно, но сначала нужно сохранить проект
        await api.putCustomValues(saved.id, cv);
      }
      onSaved();
    } catch (err2) {
      setErr(err2.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        {SYSTEM_FIELDS.map((f) => (
          <Field key={f.field} label={f.label} required={f.required}>
            <SysInput field={f} value={form[f.field]} onChange={(v) => setF(f.field, v)} />
          </Field>
        ))}
      </div>

      {customFields.length > 0 && (
        <div>
          <div className="mb-2 border-t border-slate-200 pt-3 text-sm font-semibold text-slate-700">
            Пользовательские поля
          </div>
          <div className="grid grid-cols-2 gap-3">
            {customFields.map((cf) => (
              <Field key={cf.id} label={cf.name} required={cf.required}>
                <CustomInput cf={cf} value={custom[cf.slug]} onChange={(v) => setC(cf.slug, v)} />
              </Field>
            ))}
          </div>
        </div>
      )}

      {err && <div className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">{err}</div>}

      <div className="flex justify-end gap-2 pt-1">
        <button type="button" className="btn btn-secondary" onClick={onCancel}>Отмена</button>
        <button type="submit" className="btn btn-primary" disabled={saving}>
          {saving ? "Сохранение..." : "Сохранить"}
        </button>
      </div>
    </form>
  );
}

function SysInput({ field, value, onChange }) {
  if (field.kind === "date") {
    // дата в формате YYYY-MM-DD для input type=date
    const val = value ? String(value).slice(0, 10) : "";
    return <input type="date" className="input" value={val} onChange={(e) => onChange(e.target.value || "")} />;
  }
  if (field.kind === "select") {
    return (
      <select className="input" value={value || ""} onChange={(e) => onChange(e.target.value)}>
        <option value="">—</option>
        {field.options.map((o) => (<option key={o} value={o}>{o}</option>))}
      </select>
    );
  }
  return <input className="input" value={value ?? ""} onChange={(e) => onChange(e.target.value)} />;
}

export function CustomInput({ cf, value, onChange }) {
  switch (cf.field_type) {
    case "NUMBER":
    case "PERCENT":
    case "CURRENCY":
      return <input type="number" className="input" value={value ?? ""} onChange={(e) => onChange(e.target.value)} />;
    case "DATE":
      return <input type="date" className="input" value={value ? String(value).slice(0, 10) : ""} onChange={(e) => onChange(e.target.value || "")} />;
    case "DATETIME":
      return <input type="datetime-local" className="input" value={value ? String(value).slice(0, 16) : ""} onChange={(e) => onChange(e.target.value || "")} />;
    case "BOOLEAN":
      return (
        <select className="input" value={value === true ? "true" : value === false ? "false" : ""} onChange={(e) => onChange(e.target.value === "true" ? true : e.target.value === "false" ? false : "")}>
          <option value="">—</option>
          <option value="true">Да</option>
          <option value="false">Нет</option>
        </select>
      );
    case "SELECT":
      return (
        <select className="input" value={value ?? ""} onChange={(e) => onChange(e.target.value)}>
          <option value="">—</option>
          {(cf.options || []).map((o) => (<option key={o} value={o}>{o}</option>))}
        </select>
      );
    case "MULTI_SELECT":
      return (
        <select multiple className="input" value={Array.isArray(value) ? value.map(String) : []}
          onChange={(e) => onChange([...e.target.selectedOptions].map((o) => o.value))}>
          {(cf.options || []).map((o) => (<option key={o} value={o}>{o}</option>))}
        </select>
      );
    case "LONG_TEXT":
      return <textarea className="input" rows={2} value={value ?? ""} onChange={(e) => onChange(e.target.value)} />;
    default:
      return <input className="input" value={value ?? ""} onChange={(e) => onChange(e.target.value)} />;
  }
}

// Приведение значения по типу для сохранения в JSON
function coerce(v) {
  // простые числовые значения
  if (typeof v === "string") {
    const n = Number(v);
    if (v.trim() !== "" && !isNaN(n) && /^-?\d+(\.\d+)?$/.test(v.trim())) return n;
  }
  return v;
}

// Сохранение значений системного + пользовательского
export function collectPayload(existing, form, custom) {
  const payload = {};
  SYSTEM_FIELDS.forEach((f) => {
    const v = form[f.field];
    payload[f.field] = v === "" || v === null ? null : v;
  });
  return payload;
}