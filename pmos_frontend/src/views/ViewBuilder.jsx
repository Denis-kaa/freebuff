import React, { useEffect, useMemo, useState } from "react";
import { api } from "../api.js";
import { DEFAULT_VISIBLE, SYSTEM_COLUMNS, fieldKindForCustom } from "../columns.js";
import { Modal, Spinner, useToast } from "../components/ui.jsx";
import FilterBuilder from "./FilterBuilder.jsx";

const DEFAULT_SORT = [{ field: "deadline", direction: "asc" }];

export default function ViewBuilder({ open, onClose, view, customFields = [], filterOptions = {}, onSaved }) {
  const toast = useToast();
  const [name, setName] = useState("");
  const [viewType, setViewType] = useState("TABLE");
  const [visibility, setVisibility] = useState("workspace");
  const [favorite, setFavorite] = useState(false);
  const [isDefault, setIsDefault] = useState(false);
  const [filters, setFilters] = useState({ operator: "AND", conditions: [], groups: [] });
  const [sorting, setSorting] = useState(DEFAULT_SORT);
  const [columns, setColumns] = useState(DEFAULT_VISIBLE);
  const [widths, setWidths] = useState({});
  const [busy, setBusy] = useState(false);

  const fields = useMemo(() => [
    ...SYSTEM_COLUMNS.map((c) => ({ key: c.field, label: c.label, kind: c.kind })),
    ...customFields.map((cf) => ({ key: cf.slug, label: cf.name, kind: fieldKindForCustom(cf), options: cf.options || [] })),
  ], [customFields]);

  useEffect(() => {
    if (!open) return;
    const cfg = view?.config || {};
    setName(view?.name || "");
    setViewType(view?.view_type || "TABLE");
    setVisibility(view?.visibility || "workspace");
    setFavorite(Boolean(view?.is_favorite));
    setIsDefault(Boolean(view?.is_default));
    setFilters(normalizeGroup(cfg.filters));
    setSorting(cfg.sorting?.length ? cfg.sorting : DEFAULT_SORT);
    setColumns(cfg.column_order || cfg.visible_columns || DEFAULT_VISIBLE);
    setWidths(cfg.column_widths || {});
  }, [open, view]);

  const save = async () => {
    if (!name.trim()) { toast("Укажите название представления", "error"); return; }
    setBusy(true);
    try {
      const payload = {
        name: name.trim(), entity_type: "projects", view_type: viewType,
        visibility, is_favorite: favorite, is_default: isDefault,
        config: { filters, sorting, visible_columns: columns, column_order: columns, column_widths: widths },
      };
      let saved;
      if (view?.id) saved = await api.updateView(view.id, payload);
      else saved = await api.createView(payload);
      onSaved?.(saved);
      onClose?.();
      toast("Представление сохранено");
    } catch (e) { toast(e.message, "error"); }
    finally { setBusy(false); }
  };

  const toggleColumn = (key) => setColumns((current) => current.includes(key) ? current.filter((x) => x !== key) : [...current, key]);
  const moveColumn = (index, delta) => setColumns((current) => {
    const next = [...current]; const target = index + delta;
    if (target < 0 || target >= next.length) return current;
    [next[index], next[target]] = [next[target], next[index]]; return next;
  });
  const addSort = () => setSorting((s) => [...s, { field: "title", direction: "asc" }]);
  const removeSort = (i) => setSorting((s) => s.filter((_, index) => index !== i));

  return (
    <Modal open={open} onClose={onClose} title={view ? "Настроить представление" : "Новое представление"} wide>
      <div className="flex flex-col gap-4">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Название</label>
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Срочное производство" autoFocus />
          </div>
          <div>
            <label className="label">Тип представления</label>
            <select className="input" value={viewType} onChange={(e) => setViewType(e.target.value)}>
              <option value="TABLE">Таблица</option><option value="KANBAN">Kanban</option><option value="CALENDAR">Календарь</option>
            </select>
          </div>
        </div>

        <div>
          <label className="label">Фильтры</label>
          <FilterBuilder value={filters} onChange={setFilters} fields={fields} options={filterOptions} />
        </div>

        <div>
          <label className="label">Сортировка</label>
          <div className="space-y-1.5">
            {sorting.map((s, i) => (
              <div key={i} className="flex items-center gap-2">
                <span className="w-5 text-xs text-slate-400">{i + 1}.</span>
                <select className="input !w-48 !py-1" value={s.field} onChange={(e) => setSorting((all) => all.map((x, j) => j === i ? { ...x, field: e.target.value } : x))}>
                  {fields.map((f) => <option key={f.key} value={f.key}>{f.label}</option>)}
                </select>
                <select className="input !w-28 !py-1" value={s.direction} onChange={(e) => setSorting((all) => all.map((x, j) => j === i ? { ...x, direction: e.target.value } : x))}>
                  <option value="asc">↑ По возр.</option><option value="desc">↓ По убыв.</option>
                </select>
                <button className="text-red-500" onClick={() => removeSort(i)}>×</button>
              </div>
            ))}
          </div>
          <button className="btn btn-ghost mt-2 !py-1 text-xs" onClick={addSort}>+ уровень сортировки</button>
        </div>

        <div>
          <label className="label">Колонки (порядок и видимость)</label>
          <div className="max-h-48 space-y-1 overflow-auto rounded-lg border border-slate-200 p-2">
            {fields.map((f) => {
              const visible = columns.includes(f.key);
              const index = columns.indexOf(f.key);
              return (
                <div key={f.key} className={`flex items-center gap-2 rounded px-2 py-1 ${visible ? "bg-indigo-50" : ""}`}>
                  <input type="checkbox" className="accent-indigo-600" checked={visible} onChange={() => toggleColumn(f.key)} />
                  <span className={`flex-1 text-sm ${visible ? "text-slate-700" : "text-slate-400"}`}>{f.label}</span>
                  {visible && <>
                    <input className="input !w-20 !py-0.5 text-xs" type="number" min="80" max="500" placeholder="ширина" value={widths[f.key] || ""} onChange={(e) => setWidths((w) => ({ ...w, [f.key]: e.target.value ? Number(e.target.value) : undefined }))} />
                    <button className="text-xs text-slate-500" disabled={index === 0} onClick={() => moveColumn(index, -1)}>↑</button>
                    <button className="text-xs text-slate-500" disabled={index === columns.length - 1} onClick={() => moveColumn(index, 1)}>↓</button>
                  </>}
                </div>
              );
            })}
          </div>
        </div>

        <div className="flex flex-wrap gap-4 text-sm">
          <label className="flex items-center gap-1.5"><input type="checkbox" className="accent-indigo-600" checked={favorite} onChange={(e) => setFavorite(e.target.checked)} /> ★ Закрепить</label>
          <label className="flex items-center gap-1.5"><input type="checkbox" className="accent-indigo-600" checked={isDefault} onChange={(e) => setIsDefault(e.target.checked)} /> Открывать по умолчанию</label>
          <label className="flex items-center gap-1.5"><span>Доступ:</span><select className="input !w-auto !py-1" value={visibility} onChange={(e) => setVisibility(e.target.value)}><option value="workspace">Workspace</option><option value="private">Private</option></select></label>
        </div>

        <div className="flex justify-end gap-2">
          <button className="btn btn-secondary" onClick={onClose}>Отмена</button>
          <button className="btn btn-primary" onClick={save} disabled={busy}>{busy ? <Spinner label="Сохраняем..." /> : "Сохранить"}</button>
        </div>
      </div>
    </Modal>
  );
}

function normalizeGroup(value) {
  if (!value) return { operator: "AND", conditions: [], groups: [] };
  if (Array.isArray(value)) return { operator: "AND", conditions: value, groups: [] };
  return { operator: value.operator || "AND", conditions: value.conditions || [], groups: value.groups || [] };
}
