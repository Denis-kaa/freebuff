import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import GridLayout, { WidthProvider } from "react-grid-layout";
import "react-grid-layout/css/styles.css";
import "react-resizable/css/styles.css";
import {
  Check,
  Copy,
  Eye,
  EyeOff,
  GripVertical,
  Home,
  MoreHorizontal,
  Pencil,
  Plus,
  RefreshCw,
  Settings2,
  Trash2,
} from "lucide-react";
import { api } from "../api.js";
import { useToast } from "../components/ui.jsx";
import { DASHBOARD_TEMPLATES, widgetDef } from "./registry.js";
import WidgetPicker from "./WidgetPicker.jsx";
import WidgetSettingsModal from "./WidgetSettingsModal.jsx";

const DashboardGrid = WidthProvider(GridLayout);

const COLS_BY_WIDTH = [
  [1280, 12],
  [768, 8],
  [480, 4],
  [0, 1],
];

function useCols() {
  const [cols, setCols] = useState(12);
  useEffect(() => {
    const upd = () => {
      const w = window.innerWidth;
      const found = COLS_BY_WIDTH.find(([min]) => w >= min);
      setCols(found ? found[1] : 1);
    };
    upd();
    window.addEventListener("resize", upd);
    return () => window.removeEventListener("resize", upd);
  }, []);
  return cols;
}

function uuidFromPath() {
  const m = window.location.pathname.match(/\/dashboard\/([0-9a-f-]{36})/i);
  return m ? m[1] : null;
}

export default function DashboardView({ onProjectClick, onOpenProjects, onOpenCalendar }) {
  const toast = useToast();
  const cols = useCols();

  const [dashboards, setDashboards] = useState([]);
  const [dashId, setDashId] = useState(null);
  const [dash, setDash] = useState(null); // {id,name,is_default,version,widgets}
  const [loading, setLoading] = useState(true);
  const [editMode, setEditMode] = useState(false);

  const [pickerOpen, setPickerOpen] = useState(false);
  const [settingsFor, setSettingsFor] = useState(null);
  const [hiddenOpen, setHiddenOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [renameOpen, setRenameOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const [confirmDel, setConfirmDel] = useState(null); // {kind:'dashboard'|'widget', id, name}

  const saveTimer = useRef(null);
  const initialLoad = useRef(true);

  // ------------------------------------------------------------------ load
  const loadDashboards = useCallback(async (preferredId) => {
    try {
      const list = await api.listDashboards();
      setDashboards(list);
      let next = preferredId || uuidFromPath();
      if (next && !list.some((d) => d.id === next)) next = null;
      if (!next) {
        const def = list.find((d) => d.is_default);
        next = def ? def.id : list[0]?.id || null;
      }
      setDashId(next);
      if (next) {
        const full = await api.getDashboard(next);
        setDash(full);
      } else {
        setDash(null);
      }
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    loadDashboards();
  }, [loadDashboards]);

  // URL state (4.md §42): /dashboard/{id} — но источник истины — БД
  useEffect(() => {
    if (!dashId) return;
    if (uuidFromPath() !== dashId) {
      window.history.pushState({}, "", `/dashboard/${dashId}`);
    }
  }, [dashId]);

  useEffect(() => {
    const onPop = () => loadDashboards();
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, [loadDashboards]);

  const switchDashboard = useCallback(async (id, skipFirst = false) => {
    setDashId(id);
    setLoading(true);
    try {
      const full = await api.getDashboard(id);
      setDash(full);
      initialLoad.current = true;
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  // ------------------------------------------------------------------ CRUD
  const createDashboard = async (name, template) => {
    try {
      const d = await api.createDashboard({ name, template: template || "empty" });
      setDashboards((l) => [...l, d]);
      await switchDashboard(d.id);
      toast(`Дашборд «${name}» создан`);
      setCreateOpen(false);
    } catch (e) {
      toast(e.message, "error");
    }
  };

  const renameDashboard = async (name) => {
    if (!dash || !name || name === dash.name) {
      setRenameOpen(false);
      return;
    }
    try {
      const d = await api.updateDashboard(dash.id, { name, version: dash.version });
      setDash((x) => ({ ...x, name: d.name, version: d.version }));
      setDashboards((l) => l.map((x) => (x.id === d.id ? { ...x, name: d.name } : x)));
      toast("Переименовано");
      setRenameOpen(false);
    } catch (e) {
      toast(e.message, "error");
    }
  };

  const setDefault = async () => {
    if (!dash || dash.is_default) return;
    try {
      const d = await api.updateDashboard(dash.id, { is_default: true, version: dash.version });
      setDash((x) => ({ ...x, is_default: true, version: d.version }));
      setDashboards((l) => l.map((x) => ({ ...x, is_default: x.id === d.id })));
      toast("Теперь это основной Dashboard");
    } catch (e) {
      toast(e.message, "error");
    }
  };

  const duplicateDashboard = async () => {
    try {
      const d = await api.duplicateDashboard(dash.id);
      setDashboards((l) => [...l, d]);
      toast(`Дубликат: ${d.name}`);
    } catch (e) {
      toast(e.message, "error");
    }
  };

  const deleteDashboard = async () => {
    try {
      await api.deleteDashboard(dash.id);
      setDashboards((l) => l.filter((x) => x.id !== dash.id));
      setDash(null);
      const rest = dashboards.filter((x) => x.id !== dash.id);
      if (rest.length) {
        await switchDashboard(rest[0].id);
      }
      toast("Дашборд удалён (данные проектов не тронуты)");
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setConfirmDel(null);
    }
  };

  // ------------------------------------------------------------------ widgets
  const addWidget = async (type) => {
    try {
      const w = await api.addWidget(dashId, { widget_type: type });
      setDash((d) => ({ ...d, widgets: [...d.widgets, w] }));
      toast(`${widgetDef(type)?.name || type} добавлен`);
      setPickerOpen(false);
    } catch (e) {
      toast(e.message, "error");
    }
  };

  const removeWidget = async (w) => {
    try {
      await api.deleteWidget(w.id);
      setDash((d) => ({ ...d, widgets: d.widgets.filter((x) => x.id !== w.id) }));
      toast("Виджет удалён с Dashboard. Данные не удалены.");
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setConfirmDel(null);
    }
  };

  const hideWidget = async (w) => {
    try {
      await api.updateWidget(w.id, { is_hidden: true });
      setDash((d) => ({ ...d, widgets: d.widgets.map((x) => (x.id === w.id ? { ...x, is_hidden: true } : x)) }));
      toast("Виджет скрыт. Его можно вернуть в настройках.");
    } catch (e) {
      toast(e.message, "error");
    }
  };

  const restoreWidget = async (w) => {
    try {
      await api.updateWidget(w.id, { is_hidden: false });
      setDash((d) => ({ ...d, widgets: d.widgets.map((x) => (x.id === w.id ? { ...x, is_hidden: false } : x)) }));
    } catch (e) {
      toast(e.message, "error");
    }
  };

  const saveWidgetConfig = async (config) => {
    if (!settingsFor) return;
    try {
      const w = await api.updateWidget(settingsFor.id, { config });
      setDash((d) => ({ ...d, widgets: d.widgets.map((x) => (x.id === w.id ? { ...x, config: w.config } : x)) }));
      toast("Настройки сохранены");
      setSettingsFor(null);
    } catch (e) {
      toast(e.message, "error");
    }
  };

  // Автосохранение drag/resize (4.md §5, §43) — без кнопки Save, debounce 600ms
  const handleLayoutChange = useCallback(
    (layout) => {
      if (initialLoad.current || !dash || !editMode) {
        initialLoad.current = false;
        return;
      }
      const changed = layout
        .filter((item) => {
          const w = dash.widgets.find((x) => x.id === item.i);
          if (!w) return false;
          const cur = w.layout || {};
          return !(cur.x === item.x && cur.y === item.y && cur.w === item.w && cur.h === item.h);
        })
        .map((item) => {
          const { x, y, w, h } = item;
          return { id: item.i, layout: { x, y, w, h } };
        });
      if (!changed.length) return;
      // локально мгновенно
      setDash((d) => ({
        ...d,
        widgets: d.widgets.map((x) => {
          const c = changed.find((k) => k.id === x.id);
          return c ? { ...x, layout: c.layout } : x;
        }),
      }));
      clearTimeout(saveTimer.current);
      saveTimer.current = setTimeout(() => {
        changed.forEach((c) => api.updateWidget(c.id, { layout: c.layout }).catch(() => {}));
      }, 600);
    },
    [dash, editMode]
  );

  // Глобальный refresh (4.md §30): событие слушают все виджеты через useWidgetData
  const refreshAll = useCallback(() => {
    window.dispatchEvent(new CustomEvent("pmos-widget-refresh"));
  }, []);

  // ------------------------------------------------------------------ render
  const visibleWidgets = useMemo(
    () => (dash?.widgets || []).filter((w) => !w.is_hidden),
    [dash]
  );
  const hiddenWidgets = useMemo(
    () => (dash?.widgets || []).filter((w) => w.is_hidden),
    [dash]
  );

  const gridItems = useMemo(
    () =>
      visibleWidgets.map((w) => {
        const def = widgetDef(w.widget_type);
        const lay = w.layout || { x: 0, y: 0 };
        return {
          i: w.id,
          x: lay.x ?? 0,
          y: lay.y ?? 0,
          w: Math.min(lay.w ?? def?.defaultSize?.w ?? 3, 12),
          h: lay.h ?? def?.defaultSize?.h ?? 2,
          minW: 1,
          minH: 1,
        };
      }),
    [visibleWidgets]
  );

  if (loading) {
    return (
      <div className="p-10 text-center text-slate-400">
        <span className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-slate-200 border-t-indigo-600" />
      </div>
    );
  }

  if (!dash && dashboards.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 py-20">
        <Home className="h-8 w-8 text-slate-300" />
        <div className="text-lg font-semibold text-slate-700">Dashboard пуст</div>
        <div className="text-sm text-slate-500">Добавьте первый виджет</div>
        <button onClick={() => setCreateOpen(true)} className="btn btn-primary mt-2">
          <Plus className="h-4 w-4" /> Создать Dashboard
        </button>
        <NewDashboardModal
          open={createOpen}
          onClose={() => setCreateOpen(false)}
          onCreate={createDashboard}
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1400px] px-4 py-4">
      {/* Header (4.md §34) */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div className="relative">
          <select
            value={dashId || ""}
            onChange={(e) => switchDashboard(e.target.value)}
            className="input w-auto cursor-pointer pr-8 font-semibold"
          >
            {dashboards.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}{d.is_default ? " ✓" : ""}
              </option>
            ))}
          </select>
        </div>
        {dash?.is_default && (
          <span className="rounded bg-emerald-50 px-1.5 py-0.5 text-[11px] font-medium text-emerald-700">
            Основной
          </span>
        )}
        <div className="ml-auto flex items-center gap-1.5">
          <button onClick={() => setPickerOpen(true)} className="btn btn-primary">
            <Plus className="h-4 w-4" /> Добавить
          </button>
          <button onClick={refreshAll} className="btn btn-secondary btn-icon" title="Обновить">
            <RefreshCw className="h-4 w-4" />
          </button>
          <div className="relative">
            <button
              onClick={() => setMoreOpen(!moreOpen)}
              className="btn btn-secondary btn-icon"
              title="Меню"
            >
              <MoreHorizontal className="h-4 w-4" />
            </button>
            {moreOpen && (
              <div onClick={() => setMoreOpen(false)} className="fixed inset-0 z-40" />
            )}
            {moreOpen && (
              <div className="absolute right-0 z-50 mt-1 w-56 rounded-lg border border-slate-200 bg-white py-1 shadow-lg">
                <MenuItem icon={Pencil} label="Переименовать" onClick={() => { setMoreOpen(false); setRenameOpen(true); }} />
                <MenuItem icon={Copy} label="Дублировать" onClick={() => { setMoreOpen(false); duplicateDashboard(); }} />
                <MenuItem icon={Settings2} label="Настроить Dashboard" onClick={() => { setMoreOpen(false); setHiddenOpen(true); }} />
                <MenuItem
                  icon={dash?.is_default ? Check : Star}
                  label={dash?.is_default ? "Основной ✓" : "Сделать основным"}
                  onClick={() => { setMoreOpen(false); setDefault(); }}
                />
                <div className="my-1 border-t border-slate-100" />
                <MenuItem icon={Trash2} label="Удалить" danger onClick={() => { setMoreOpen(false); setConfirmDel({ kind: "dashboard", id: dash.id, name: dash.name }); }} />
              </div>
            )}
          </div>
          <button
            onClick={() => setEditMode(!editMode)}
            className={editMode ? "btn btn-indigo" : "btn btn-secondary"}
          >
            {editMode ? "Готово" : "Редактировать"}
          </button>
        </div>
      </div>

      <div className="mb-3 text-xs text-slate-400">
        {new Date().toLocaleDateString("ru-RU", { weekday: "long", day: "numeric", month: "long" })}
      </div>

      {editMode && (
        <div className="mb-3 rounded-lg border border-indigo-100 bg-indigo-50 px-3 py-2 text-xs text-indigo-700">
          Режим редактирования: перетаскивайте виджеты, меняйте их размер. Изменения сохраняются автоматически.
        </div>
      )}

      {/* Grid (4.md §4-6) */}
      {visibleWidgets.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-slate-200 py-16">
          <div className="text-lg font-semibold text-slate-600">Dashboard пуст</div>
          <div className="text-sm text-slate-400">Добавьте первый виджет</div>
          <button onClick={() => setPickerOpen(true)} className="btn btn-primary mt-1">
            <Plus className="h-4 w-4" /> Добавить виджет
          </button>
        </div>
      ) : (
        <DashboardGrid
          layout={gridItems}
          cols={cols}
          rowHeight={64}
          margin={[10, 10]}
          isDraggable={editMode}
          isResizable={editMode}
          draggableHandle=".widget-drag-handle"
          compactType="vertical"
          onLayoutChange={handleLayoutChange}
        >
          {visibleWidgets.map((w) => {
            const defW = widgetDef(w.widget_type);
            if (!defW) return <div key={w.id} className="rounded-lg border border-slate-200 bg-white p-3 text-xs text-slate-400">Неизвестный виджет: {w.widget_type}</div>;
            const Cmp = defW.component;
            return (
              <div key={w.id} className="flex flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
                <div className="flex items-center gap-1 border-b border-slate-100 px-2 py-1">
                  {editMode && (
                    <span className="widget-drag-handle cursor-move text-slate-300 hover:text-slate-500">
                      <GripVertical className="h-3.5 w-3.5" />
                    </span>
                  )}
                  <span className="truncate text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                    {w.title || defW.name}
                  </span>
                  <div className="ml-auto flex items-center gap-0.5">
                    <button onClick={refreshAll} className="btn btn-ghost btn-icon-sm" title="Обновить">
                      <RefreshCw className="h-3 w-3" />
                    </button>
                    {editMode && (
                      <>
                        <button onClick={() => setSettingsFor(w)} className="btn btn-ghost btn-icon-sm" title="Настроить">
                          <Settings2 className="h-3 w-3" />
                        </button>
                        <button onClick={() => hideWidget(w)} className="btn btn-ghost btn-icon-sm" title="Скрыть">
                          <EyeOff className="h-3 w-3" />
                        </button>
                        <button onClick={() => setConfirmDel({ kind: "widget", id: w.id, name: w.title || defW.name })} className="btn btn-ghost btn-icon-sm text-red-500" title="Удалить">
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </>
                    )}
                  </div>
                </div>
                <div className="flex-1 overflow-hidden">
                  <Cmp key={w.id} config={w.config || {}} onProjectClick={onProjectClick} onOpenCalendar={onOpenCalendar} />
                </div>
              </div>
            );
          })}
        </DashboardGrid>
      )}

      {/* Скрытые виджеты (4.md §10) */}
      {hiddenOpen && (
        <div className="mt-4 rounded-lg border border-slate-200 bg-white p-4">
          <div className="mb-2 text-sm font-semibold text-slate-700">Скрытые виджеты</div>
          {hiddenWidgets.length === 0 && (
            <div className="text-sm text-slate-400">Скрытых виджетов нет.</div>
          )}
          <div className="space-y-1">
            {hiddenWidgets.map((w) => (
              <div key={w.id} className="flex items-center justify-between rounded px-2 py-1.5 hover:bg-slate-50">
                <span className="text-sm text-slate-600">{w.title || widgetDef(w.widget_type)?.name}</span>
                <button onClick={() => restoreWidget(w)} className="btn btn-secondary btn-sm">
                  <Eye className="h-3.5 w-3.5" /> Вернуть
                </button>
              </div>
            ))}
          </div>
          <button onClick={() => setHiddenOpen(false)} className="btn btn-ghost btn-sm mt-3">
            Закрыть
          </button>
        </div>
      )}

      {/* Modals */}
      <WidgetPicker open={pickerOpen} onClose={() => setPickerOpen(false)} onAdd={addWidget} />
      <WidgetSettingsModal
        widget={settingsFor}
        open={!!settingsFor}
        onClose={() => setSettingsFor(null)}
        onSave={saveWidgetConfig}
      />
      <NewDashboardModal open={createOpen} onClose={() => setCreateOpen(false)} onCreate={createDashboard} />

      {renameOpen && (
        <RenameModal
          current={dash?.name || ""}
          onClose={() => setRenameOpen(false)}
          onSave={renameDashboard}
        />
      )}

      {confirmDel && (
        <ConfirmModal
          title={confirmDel.kind === "dashboard" ? "Удалить Dashboard?" : "Удалить виджет?"}
          body={
            confirmDel.kind === "dashboard"
              ? `«${confirmDel.name}» будет удалён. Это удалит только виджеты с Dashboard — данные проектов не будут удалены.`
              : `«${confirmDel.name}» будет удалён с Dashboard. Данные проектов не будут удалены.`
          }
          onCancel={() => setConfirmDel(null)}
          onConfirm={() => (confirmDel.kind === "dashboard" ? deleteDashboard() : removeWidget(confirmDel))}
        />
      )}
    </div>
  );
}

function MenuItem({ icon: Icon, label, onClick, danger }) {
  return (
    <button
      onClick={onClick}
      className={`flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm hover:bg-slate-50 ${danger ? "text-red-600" : "text-slate-700"}`}
    >
      <Icon className="h-3.5 w-3.5" /> {label}
    </button>
  );
}

function Star() {
  return <span className="text-sm">⭐</span>;
}

function NewDashboardModal({ open, onClose, onCreate }) {
  const [name, setName] = useState("");
  const [template, setTemplate] = useState("empty");
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-slate-900/50" onClick={onClose} />
      <div className="relative z-10 w-[420px] max-w-[95vw] rounded-xl bg-white p-5 shadow-2xl">
        <h3 className="mb-3 text-base font-semibold">Новый Dashboard</h3>
        <label className="label">Название</label>
        <input autoFocus value={name} onChange={(e) => setName(e.target.value)} className="input w-full" placeholder="Например, Производство" />
        <div className="mt-3">
          <div className="label">Шаблон (4.md §35)</div>
          <div className="grid grid-cols-2 gap-1.5">
            {DASHBOARD_TEMPLATES.map((t) => (
              <button
                key={t.key}
                onClick={() => setTemplate(t.key)}
                className={`rounded-lg border px-2 py-1.5 text-sm transition ${
                  template === t.key ? "border-indigo-400 bg-indigo-50 text-indigo-700" : "border-slate-200 text-slate-600 hover:border-slate-300"
                }`}
              >
                {t.name}
              </button>
            ))}
          </div>
        </div>
        <div className="mt-4 flex justify-end gap-2">
          <button onClick={onClose} className="btn btn-ghost">Отмена</button>
          <button
            disabled={!name.trim()}
            onClick={() => onCreate(name.trim(), template)}
            className="btn btn-primary"
          >
            Создать
          </button>
        </div>
      </div>
    </div>
  );
}

function RenameModal({ current, onClose, onSave }) {
  const [name, setName] = useState(current);
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-slate-900/50" onClick={onClose} />
      <div className="relative z-10 w-[380px] max-w-[95vw] rounded-xl bg-white p-5 shadow-2xl">
        <h3 className="mb-3 text-base font-semibold">Переименовать Dashboard</h3>
        <input autoFocus value={name} onChange={(e) => setName(e.target.value)} className="input w-full" />
        <div className="mt-4 flex justify-end gap-2">
          <button onClick={onClose} className="btn btn-ghost">Отмена</button>
          <button disabled={!name.trim()} onClick={() => onSave(name.trim())} className="btn btn-primary">
            Сохранить
          </button>
        </div>
      </div>
    </div>
  );
}

function ConfirmModal({ title, body, onCancel, onConfirm }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-slate-900/50" onClick={onCancel} />
      <div className="relative z-10 w-[420px] max-w-[95vw] rounded-xl bg-white p-5 shadow-2xl">
        <h3 className="mb-2 text-base font-semibold">{title}</h3>
        <p className="text-sm leading-relaxed text-slate-600">{body}</p>
        <div className="mt-4 flex justify-end gap-2">
          <button onClick={onCancel} className="btn btn-ghost">Отмена</button>
          <button onClick={onConfirm} className="btn btn-danger">Удалить</button>
        </div>
      </div>
    </div>
  );
}