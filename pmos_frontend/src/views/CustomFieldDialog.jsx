import React, { useState } from "react";
import { api } from "../api.js";
import { FIELD_TYPES } from "../columns.js";
import { Field, Modal, useToast } from "../components/ui.jsx";

export default function CustomFieldDialog({ open, onClose, onSaved }) {
  const toast = useToast();
  const [name, setName] = useState("");
  const [fieldType, setFieldType] = useState("TEXT");
  const [description, setDescription] = useState("");
  const [required, setRequired] = useState(false);
  const [defaultValue, setDefaultValue] = useState("");
  const [options, setOptions] = useState([]);
  const [optionInput, setOptionInput] = useState("");
  const [formula, setFormula] = useState("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState(null);

  const isSelect = fieldType === "SELECT" || fieldType === "MULTI_SELECT";

  const addOption = () => {
    if (optionInput.trim() && !options.includes(optionInput.trim())) {
      setOptions((o) => [...o, optionInput.trim()]);
      setOptionInput("");
    }
  };

  const reset = () => {
    setName(""); setFieldType("TEXT"); setDescription(""); setRequired(false);
    setDefaultValue(""); setOptions([]); setOptionInput(""); setFormula(""); setErr(null);
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!name.trim()) { setErr("Укажите название поля"); return; }
    if (isSelect && options.length === 0) { setErr("Для SELECT укажите хотя бы одно значение"); return; }
    setSaving(true);
    setErr(null);
    try {
      await api.createCustomField({
        name: name.trim(),
        field_type: fieldType,
        description: description || null,
        required,
        default_value: defaultValue || null,
        options: isSelect ? options : undefined,
        formula: fieldType === "FORMULA" ? (formula || null) : null,
      });
      toast("Поле создано");
      reset();
      onSaved();
    } catch (e2) {
      setErr(e2.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open={open} onClose={() => { reset(); onClose(); }} title="Добавить поле">
      <form onSubmit={handleCreate} className="space-y-4">
        <Field label="Название" required>
          <input autoFocus className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Например: Номер накладной" />
        </Field>

        <Field label="Тип">
          <select className="input" value={fieldType} onChange={(e) => setFieldType(e.target.value)}>
            {FIELD_TYPES.map((t) => (<option key={t.value} value={t.value}>{t.label}</option>))}
          </select>
        </Field>

        <Field label="Описание">
          <input className="input" value={description} onChange={(e) => setDescription(e.target.value)} />
        </Field>

        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input type="checkbox" className="accent-indigo-600" checked={required} onChange={(e) => setRequired(e.target.checked)} />
          Обязательное
        </label>

        {fieldType !== "BOOLEAN" && fieldType !== "FORMULA" && (
          <Field label="Значение по умолчанию">
            <input className="input" value={defaultValue} onChange={(e) => setDefaultValue(e.target.value)} />
          </Field>
        )}

        {isSelect && (
          <Field label="Значения">
            <div className="flex gap-1.5">
              <input className="input" value={optionInput} onChange={(e) => setOptionInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addOption(); } }} />
              <button type="button" className="btn btn-secondary" onClick={addOption}>+ Добавить</button>
            </div>
            {options.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {options.map((o, i) => (
                  <span key={o} className="flex items-center gap-1 rounded bg-slate-100 px-2 py-0.5 text-xs">
                    {o}
                    <button type="button" className="text-slate-400 hover:text-red-500" onClick={() => setOptions((arr) => arr.filter((_, j) => j !== i))}>×</button>
                  </span>
                ))}
              </div>
            )}
          </Field>
        )}

        {fieldType === "FORMULA" && (
          <Field label="Формула (выражение)">
            <input className="input" value={formula} onChange={(e) => setFormula(e.target.value)} placeholder="Например: payment_percent * 100" />
            <p className="mt-1 text-xs text-slate-400">Движок формул появится на отдельном этапе. Пока хранится как текст.</p>
          </Field>
        )}

        {err && <div className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">{err}</div>}

        <div className="flex justify-end gap-2 pt-1">
          <button type="button" className="btn btn-secondary" onClick={() => { reset(); onClose(); }}>Отмена</button>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Создание..." : "Создать"}
          </button>
        </div>
      </form>
    </Modal>
  );
}