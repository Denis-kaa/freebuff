import React, { useMemo, useState } from "react";
import { OPERATORS_BY_KIND, OPERATOR_LABEL, FILTERABLE_SYSTEM } from "../columns.js";
import { Field, Modal, useToast } from "../components/ui.jsx";

export default function ColumnSettings({
  open, onClose,
  columns, visibleKeys, setVisibleKeys,
  customFields,
  onAddField,
  filters, setFilters,
  sortBy, setSortBy, sortDir, setSortDir,
}) {
  const toast = useToast();
  // порядок колонок сохраняем на основе visibleKeys + все остальные
  const [order, setOrder] = useState(visibleKeys);

  // системные и пользовательские отдельно для группировки
  const systemCols = useMemo(() => columns.filter((c) => !c.custom), [columns]);
  const customCols = useMemo(() => columns.filter((c) => c.custom), [columns]);

  const isVisible = (key) => visibleKeys.includes(key);

  const toggle = (key) => {
    setVisibleKeys((arr) =>
      arr.includes(key) ? arr.filter((k) => k !== key) : [...arr, key]
    );
  };

  const moveUp = (key) => {
    setVisibleKeys((arr) => {
      const i = arr.indexOf(key);
      if (i <= 0) return arr;
      const next = [...arr];
      [next[i - 1], next[i]] = [next[i], next[i - 1]];
      return next;
    });
  };

  const moveDown = (key) => {
    setVisibleKeys((arr) => {
      const i = arr.indexOf(key);
      if (i < 0 || i >= arr.length - 1) return arr;
      const next = [...arr];
      [next[i + 1], next[i]] = [next[i], next[i + 1]];
      return next;
    });
  };

  const resetToDefault = () => {
    if (confirm("Сбросить настройку колонок к стандартной?")) {
      setVisibleKeys([...visibleKeys]); // сохраняем позиции скрытых
      setSortBy("deadline"); setSortDir("asc");
    }
  };

  const removeFilter = (i) => setFilters((f) => f.filter((_, j) => j !== i));

  return (
    <Modal open={open} onClose={onClose} title="Настроить таблицу" wide>
      <div className="space-y-5">
        {/* Колонки */}
        <div>
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-semibold text-slate-700">Колонки</span>
            <button className="text-xs font-medium text-indigo-600 hover:underline" onClick={resetToDefault}>
              Сбросить к стандартной
            </button>
          </div>

          {/* Системные */}
          <div className="mb-3">
            <div className="mb-1 text-xs font-semibold uppercase text-slate-400">Системные</div>
            {systemCols.map((c) => (
              <div key={c.key} className="flex items-center justify-between rounded px-2 py-1.5 hover:bg-slate-50">
                <div className="flex items-center gap-2">
                  <button className="text-slate-300 hover:text-slate-500" title="Вверх" onClick={() => moveUp(c.key)}>☰</button>
                  <span className="text-sm">{c.label}</span>
                </div>
                <div className="flex items-center gap-1">
                  <button className="btn btn-ghost !px-1.5 !py-0.5" onClick={() => moveUp(c.key)}>↑</button>
                  <button className="btn btn-ghost !px-1.5 !py-0.5" onClick={() => moveDown(c.key)}>↓</button>
                  <button className={`btn !px-1.5 !py-0.5 ${isVisible(c.key) ? "btn-primary" : "btn-secondary"}`}
                    onClick={() => toggle(c.key)} title={isVisible(c.key) ? "Скрыть" : "Показать"}>
                    {isVisible(c.key) ? "👁" : "○"}
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Пользовательские */}
          <div>
            <div className="mb-1 flex items-center justify-between text-xs font-semibold uppercase text-slate-400">
              <span>Пользовательские</span>
              <button className="font-medium normal-case text-indigo-600 hover:underline" onClick={onAddField}>+ Добавить поле</button>
            </div>
            {customCols.length === 0 ? (
              <div className="rounded border border-dashed border-slate-200 px-3 py-4 text-center text-sm text-slate-400">
                Пользовательских полей пока нет.
              </div>
            ) : (
              customCols.map((c) => (
                <div key={c.key} className="flex items-center justify-between rounded px-2 py-1.5 hover:bg-slate-50">
                  <div className="flex items-center gap-2">
                    <span className="text-slate-300">☰</span>
                    <span className="text-sm">{c.label}</span>
                    <span className="rounded bg-amber-100 px-1 text-[10px] text-amber-700">поле</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <button className="btn btn-ghost !px-1.5 !py-0.5" onClick={() => moveUp(c.key)}>↑</button>
                    <button className="btn btn-ghost !px-1.5 !py-0.5" onClick={() => moveDown(c.key)}>↓</button>
                    <button className={`btn !px-1.5 !py-0.5 ${isVisible(c.key) ? "btn-primary" : "btn-secondary"}`}
                      onClick={() => toggle(c.key)}>
                      {isVisible(c.key) ? "👁" : "○"}
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Сортировка */}
        <div className="border-t border-slate-200 pt-3">
          <div className="mb-2 text-sm font-semibold text-slate-700">Сортировка</div>
          <div className="flex items-center gap-2">
            <select className="input !w-auto" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
              {columns.filter((c) => c.kind !== "text" || c.key === "title").map((c) => (
                <option key={c.key} value={c.field || c.slug}>{c.label}</option>
              ))}
              {!columns.some((c) => (c.field || c.slug) === sortBy) && <option>{sortBy}</option>}
            </select>
            <select className="input !w-auto" value={sortDir} onChange={(e) => setSortDir(e.target.value)}>
              <option value="asc">По возрастанию ↑</option>
              <option value="desc">По убыванию ↓</option>
            </select>
          </div>
        </div>

        {/* Фильтры */}
        <div className="border-t border-slate-200 pt-3">
          <div className="mb-2 text-sm font-semibold text-slate-700">Фильтры</div>
          {filters.length === 0 ? (
            <div className="text-sm text-slate-400">Фильтров нет</div>
          ) : (
            <div className="space-y-2">
              {filters.map((f, i) => (
                <FilterRow key={i} filter={f} index={i} allColumns={columns} onRemove={() => removeFilter(i)} onChange={(nf) => setFilters((arr) => arr.map((x, j) => j === i ? nf : x))} />
              ))}
            </div>
          )}
          <button className="btn btn-secondary mt-2" onClick={() => setFilters((f) => [...f, { field: "title", operator: "contains", value: "" }])}>
            + Условие
          </button>
        </div>

        <div className="flex justify-end gap-2 border-t border-slate-200 pt-3">
          <button className="btn btn-secondary" onClick={onClose}>Готово</button>
        </div>
      </div>
    </Modal>
  );
}

function FilterRow({ filter, index, allColumns, onChange, onRemove }) {
  const col = allColumns.find((c) => (c.field || c.slug) === filter.field);
  const kind = col ? (col.custom ? col.kind : col.kind) : "text";
  const operators = OPERATORS_BY_KIND[kind] || OPERATORS_BY_KIND.text;

  const selectable = allColumns.filter((c) => {
    if (c.custom) {
      return c.fieldType === "SELECT" ? true : true; // любые пользовательские разрешаем
    }
    return FILTERABLE_SYSTEM.includes(c.field) || c.field === "title";
  });

  return (
    <div className="flex items-center gap-2 rounded border border-slate-200 bg-slate-50 px-2 py-2">
      <span className="text-xs text-slate-400">{index + 1}</span>
      <select className="input !w-auto min-w-[160px]" value={filter.field}
        onChange={(e) => onChange({ ...filter, field: e.target.value, operator: "contains", value: "" })}>
        {selectable.map((c) => (<option key={c.key} value={c.field || c.slug}>{c.label}</option>))}
      </select>
      <select className="input !w-auto" value={filter.operator} onChange={(e) => onChange({ ...filter, operator: e.target.value })}>
        {operators.map((op) => (<option key={op} value={op}>{OPERATOR_LABEL[op] || op}</option>))}
      </select>
      {!["empty", "not_empty"].includes(filter.operator) && (
        <input
          className="input !flex-1 min-w-[100px]"
          value={filter.value ?? ""}
          onChange={(e) => onChange({ ...filter, value: e.target.value })}
          placeholder={kind === "number" ? "100" : kind === "date" ? "2026-09-01" : "значение"}
        />
      )}
      <button className="btn btn-ghost !px-1.5 text-red-500" onClick={onRemove}>×</button>
    </div>
  );
}