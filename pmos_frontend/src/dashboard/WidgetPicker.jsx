import React, { useMemo, useState } from "react";
import { Modal } from "../components/ui.jsx";
import { CATEGORY_NAMES, PICKABLE_TYPES, WIDGET_REGISTRY } from "./registry.js";

export default function WidgetPicker({ open, onClose, onAdd }) {
  const [q, setQ] = useState("");

  const byCategory = useMemo(() => {
    const map = {};
    PICKABLE_TYPES.forEach((type) => {
      const def = WIDGET_REGISTRY[type];
      if (!def) return;
      const title = `${def.name} ${def.description}`.toLowerCase();
      if (q && !title.includes(q.toLowerCase())) return;
      (map[def.category] = map[def.category] || []).push(def);
    });
    return map;
  }, [q]);

  return (
    <Modal open={open} onClose={onClose} title="Добавить виджет" wide>
      <div className="mb-3">
        <input
          autoFocus
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="🔎 Поиск виджета..."
          className="input w-full"
        />
      </div>
      <div className="max-h-[55vh] space-y-4 overflow-y-auto pr-1">
        {Object.entries(byCategory).length === 0 && (
          <div className="py-8 text-center text-sm text-slate-400">Ничего не найдено</div>
        )}
        {Object.entries(byCategory).map(([cat, defs]) => (
          <div key={cat}>
            <div className="mb-1 text-[11px] font-bold uppercase tracking-wide text-slate-400">
              {CATEGORY_NAMES[cat] || cat}
            </div>
            <div className="grid grid-cols-2 gap-2">
              {defs.map((d) => {
                const Icon = d.icon;
                return (
                  <button
                    key={d.type}
                    onClick={() => onAdd(d.type)}
                    className="flex items-start gap-2 rounded-lg border border-slate-200 p-2.5 text-left transition hover:border-indigo-300 hover:bg-indigo-50"
                  >
                    <Icon className="mt-0.5 h-4 w-4 shrink-0 text-indigo-500" />
                    <span>
                      <span className="block text-sm font-medium text-slate-700">{d.name}</span>
                      <span className="block text-[11px] leading-tight text-slate-400">{d.description}</span>
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </Modal>
  );
}