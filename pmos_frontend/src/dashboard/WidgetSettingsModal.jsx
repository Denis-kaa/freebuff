import React, { useEffect, useState } from "react";
import { Modal } from "../components/ui.jsx";
import { widgetDef } from "./registry.js";

function FieldControl({ field, value, onChange }) {
  switch (field.type) {
    case "check":
      return (
        <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
          <input type="checkbox" checked={!!value} onChange={(e) => onChange(e.target.checked)} className="h-4 w-4 rounded border-slate-300 text-indigo-600" />
          {field.label}
        </label>
      );
    case "radio":
      return (
        <div className="space-y-1">
          {field.options.map((o) => (
            <label key={String(o.value)} className="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
              <input
                type="radio"
                name={`radio-${field.key}`}
                checked={String(value) === String(o.value)}
                onChange={() => onChange(o.value)}
                className="h-4 w-4 text-indigo-600"
              />
              {o.label}
            </label>
          ))}
        </div>
      );
    case "select":
      return (
        <select value={value ?? ""} onChange={(e) => onChange(field.options?.find((o) => String(o.value) === e.target.value)?.value ?? e.target.value)} className="input w-full">
          {field.options.map((o) => (
            <option key={String(o.value)} value={String(o.value)}>
              {o.label}
            </option>
          ))}
        </select>
      );
    case "multi":
      return (
        <div className="space-y-1">
          {field.options.map((o) => {
            const arr = Array.isArray(value) ? value : field.default || [];
            const checked = arr.includes(o.value);
            return (
              <label key={o.value} className="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={(e) => {
                    const next = e.target.checked ? [...arr, o.value] : arr.filter((v) => v !== o.value);
                    onChange(next.length ? next : null);
                  }}
                  className="h-4 w-4 rounded border-slate-300 text-indigo-600"
                />
                {o.label}
              </label>
            );
          })}
        </div>
      );
    case "number":
      return (
        <input
          type="number"
          min={field.min}
          max={field.max}
          value={value ?? field.default ?? ""}
          onChange={(e) => onChange(Number(e.target.value))}
          className="input w-full"
        />
      );
    default: // text
      return (
        <input value={value ?? ""} onChange={(e) => onChange(e.target.value)} className="input w-full" />
      );
  }
}

export default function WidgetSettingsModal({ widget, open, onClose, onSave }) {
  const def = widget ? widgetDef(widget.widget_type) : null;
  const [form, setForm] = useState({});

  useEffect(() => {
    if (!def || !open) return;
    const init = {};
    def.settings.forEach((group) =>
      group.fields.forEach((f) => (init[f.key] = widget.config?.[f.key] ?? f.default))
    );
    setForm(init);
  }, [open, widget?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!open || !def) return null;

  const change = (key, val) => setForm((f) => ({ ...f, [key]: val }));

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`Настройки: ${def.name}`}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          // сохраняем только заданные поля (+существующий config)
          onSave({ ...(widget.config || {}), ...form });
        }}
        className="space-y-4"
      >
        {def.settings.map((group) => (
          <div key={group.section}>
            <div className="mb-1 text-[11px] font-bold uppercase tracking-wide text-slate-400">
              {group.section}
            </div>
            <div className="space-y-2">
              {group.fields.map((f) => (
                <FieldControl key={f.key} field={f} value={form[f.key]} onChange={(v) => change(f.key, v)} />
              ))}
            </div>
          </div>
        ))}
        {def.settings.length === 0 && (
          <div className="text-sm text-slate-400">У этого виджета нет настроек.</div>
        )}
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="btn btn-ghost">Отмена</button>
          <button type="submit" className="btn btn-primary">Сохранить</button>
        </div>
      </form>
    </Modal>
  );
}