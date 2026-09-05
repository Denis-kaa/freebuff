import React from "react";
import { OPERATOR_LABEL } from "../columns.js";

const OPERATORS = {
  text: ["equals", "not_equals", "contains", "not_contains", "starts_with", "ends_with", "empty", "not_empty", "in", "not_in"],
  number: ["equals", "not_equals", "gt", "gte", "lt", "lte", "empty", "not_empty"],
  date: ["today", "tomorrow", "this_week", "next_7_days", "next_30_days", "overdue", "no_deadline", "equals", "before", "after", "before_or_equal", "after_or_equal", "between", "empty", "not_empty"],
  select: ["equals", "not_equals", "in", "not_in", "empty", "not_empty"],
};

const LABELS = {
  ...OPERATOR_LABEL,
  not_contains: "не содержит", starts_with: "начинается с", ends_with: "заканчивается на",
  in: "в списке", not_in: "не в списке", today: "сегодня", tomorrow: "завтра",
  this_week: "эта неделя", next_7_days: "следующие 7 дней", next_30_days: "следующие 30 дней",
  overdue: "просрочено", no_deadline: "без дедлайна", between: "между",
};

function newCondition(fields) {
  const first = fields[0];
  return { field: first?.key || "title", operator: "contains", value: "" };
}

export default function FilterBuilder({ value, onChange, fields = [], options = {} }) {
  const group = value || { operator: "AND", conditions: [], groups: [] };
  const update = (next) => onChange({ ...group, ...next });
  const addCondition = () => update({ conditions: [...(group.conditions || []), newCondition(fields)] });
  const addGroup = () => update({ groups: [...(group.groups || []), { operator: "OR", conditions: [], groups: [] }] });
  const removeCondition = (index) => update({ conditions: group.conditions.filter((_, i) => i !== index) });
  const removeGroup = (index) => update({ groups: group.groups.filter((_, i) => i !== index) });

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <div className="mb-2 flex items-center gap-2">
        <span className="text-xs font-semibold uppercase text-slate-500">Группа</span>
        <select className="input !w-auto !py-1 !text-xs" value={group.operator || "AND"} onChange={(e) => update({ operator: e.target.value })}>
          <option value="AND">И (AND)</option>
          <option value="OR">ИЛИ (OR)</option>
        </select>
      </div>
      <div className="space-y-2">
        {(group.conditions || []).map((condition, index) => (
          <ConditionRow
            key={index}
            condition={condition}
            fields={fields}
            options={options}
            onChange={(next) => update({ conditions: group.conditions.map((c, i) => i === index ? next : c) })}
            onRemove={() => removeCondition(index)}
          />
        ))}
        {(group.groups || []).map((nested, index) => (
          <div key={index} className="relative ml-3 border-l-2 border-indigo-200 pl-3">
            <FilterBuilder
              value={nested}
              onChange={(next) => update({ groups: group.groups.map((g, i) => i === index ? next : g) })}
              fields={fields}
              options={options}
            />
            <button className="absolute right-2 top-2 text-xs text-red-500" onClick={() => removeGroup(index)}>Удалить группу</button>
          </div>
        ))}
      </div>
      <div className="mt-3 flex gap-2">
        <button className="btn btn-secondary !py-1 text-xs" onClick={addCondition}>+ Добавить условие</button>
        <button className="btn btn-ghost !py-1 text-xs" onClick={addGroup}>+ OR-группа</button>
      </div>
    </div>
  );
}

function ConditionRow({ condition, fields, options, onChange, onRemove }) {
  const field = fields.find((f) => f.key === condition.field) || fields[0] || { key: "title", label: "Проект", kind: "text" };
  const operators = OPERATORS[field.kind] || OPERATORS.text;
  const op = operators.includes(condition.operator) ? condition.operator : operators[0];
  const values = options[field.key] || field.options || [];
  const needsValue = !["empty", "not_empty", "today", "tomorrow", "this_week", "next_7_days", "next_30_days", "overdue", "no_deadline"].includes(op);

  return (
    <div className="flex flex-wrap items-center gap-1.5 rounded-md bg-white p-1.5 shadow-sm">
      <select className="input !w-36 !py-1 !text-xs" value={condition.field} onChange={(e) => onChange({ field: e.target.value, operator: "equals", value: "" })}>
        {fields.map((f) => <option key={f.key} value={f.key}>{f.label}</option>)}
      </select>
      <select className="input !w-36 !py-1 !text-xs" value={op} onChange={(e) => onChange({ ...condition, operator: e.target.value, value: "" })}>
        {operators.map((o) => <option key={o} value={o}>{LABELS[o] || o}</option>)}
      </select>
      {needsValue && field.kind === "date" && op === "between" ? (
        <div className="flex gap-1">
          <input type="date" className="input !w-32 !py-1 !text-xs" value={condition.value?.[0] || ""} onChange={(e) => onChange({ ...condition, value: [e.target.value, condition.value?.[1] || ""] })} />
          <input type="date" className="input !w-32 !py-1 !text-xs" value={condition.value?.[1] || ""} onChange={(e) => onChange({ ...condition, value: [condition.value?.[0] || "", e.target.value] })} />
        </div>
      ) : needsValue && (field.kind === "select" && values.length) ? (
        <select className="input !w-40 !py-1 !text-xs" value={condition.value || ""} onChange={(e) => onChange({ ...condition, value: e.target.value })}>
          <option value="">Выберите...</option>
          {values.map((v) => <option key={v} value={v}>{v}</option>)}
        </select>
      ) : needsValue ? (
        <input className="input !w-40 !py-1 !text-xs" type={field.kind === "date" ? "date" : field.kind === "number" ? "number" : "text"} value={condition.value ?? ""} onChange={(e) => onChange({ ...condition, value: e.target.value })} placeholder="Значение" />
      ) : null}
      <button className="px-1 text-sm text-red-500" title="Удалить" onClick={onRemove}>×</button>
    </div>
  );
}
