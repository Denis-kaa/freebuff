import React, { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import { Button, Drawer, Field, Spinner, useToast } from "../components/ui.jsx";
import { CustomInput } from "./ProjectForm.jsx";
import { useAuth } from "../rbac/AuthContext.jsx";
import { memberOptions, useMembers } from "../rbac/useMembers.js";

const TABS = [
  { key: "overview", label: "Основное" },
  { key: "production", label: "Производство" },
  { key: "tasks", label: "Задачи" },
  { key: "documents", label: "Документы" },
  { key: "activity", label: "История" },
];

const HEALTH_META = {
  healthy: { label: "ОК", cls: "bg-emerald-100 text-emerald-700" },
  attention: { label: "Внимание", cls: "bg-amber-100 text-amber-700" },
  at_risk: { label: "Риск", cls: "bg-orange-100 text-orange-700" },
  critical: { label: "Критично", cls: "bg-red-100 text-red-700" },
};

const SYS_FIELDS = [
  { field: "title", label: "Название", kind: "text" },
  { field: "client_legal_name", label: "Юр. лицо", kind: "text" },
  { field: "manager_id", label: "Менеджер", kind: "user" },
  { field: "stage", label: "Этап", kind: "text" },
  { field: "deadline", label: "Дедлайн", kind: "date" },
  { field: "risk_level", label: "Риск", kind: "select", options: ["Нет", "Низкий", "Средний", "Высокий", "Критический"] },
  { field: "risk_reason", label: "Причина риска", kind: "text" },
  { field: "payment_percent", label: "Оплата %", kind: "text" },
  { field: "currency", label: "Валюта", kind: "text" },
  { field: "advance_date", label: "Дата аванса", kind: "date" },
  { field: "final_payment_date", label: "Дата доплаты", kind: "date" },
  { field: "delivery_address", label: "Адрес доставки", kind: "text" },
  { field: "delivery_paid", label: "Оплата доставки", kind: "text" },
  { field: "next_action", label: "Следующее действие", kind: "text" },
  { field: "next_action_date", label: "Дата след. действия", kind: "date" },
  { field: "comment", label: "Комментарий", kind: "text" },
];

export default function ProjectDetail({ project, customFields = [], itemCustomFields = [], onClose, onSaved, onArchived }) {
  const toast = useToast();
  if (!project) return null;
  const { can } = useAuth();
  const [tab, setTab] = useState("overview");
  const [summary, setSummary] = useState(null);
  const [items, setItems] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [docs, setDocs] = useState([]);
  const [activity, setActivity] = useState([]);
  const [events, setEvents] = useState([]);
  const [loadingTab, setLoadingTab] = useState(false);
  const [tags, setTags] = useState([]);

  useEffect(() => { api.projectTags(project.id).then((data) => setTags(data.tags || [])).catch(() => {}); }, [project.id]);

  // lazy: грузим данные таба при открытии
  useEffect(() => {
    api.projectSummary(project.id).then(setSummary).catch(() => {});
  }, [project.id]);

  const loadTab = useCallback(
    async (key) => {
      setLoadingTab(true);
      try {
        if (key === "production") {
          const [its, evs] = await Promise.all([
            api.listItems(project.id),
            api.projectEvents(project.id),
          ]);
          setItems(its);
          setEvents(evs);
        } else if (key === "tasks") {
          setTasks(await api.listTasks(project.id));
        } else if (key === "documents") {
          setDocs(await api.listDocuments(project.id));
        } else if (key === "activity") {
          const a = await api.projectActivity(project.id);
          setActivity(a.items || []);
        }
      } catch (e) {
        toast(e.message, "error");
      } finally {
        setLoadingTab(false);
      }
    },
    [project.id, toast]
  );

  const changeTab = (key) => {
    setTab(key);
    loadTab(key);
  };

  const refreshTab = (key) => {
    loadTab(key);
    api.projectSummary(project.id).then(setSummary).catch(() => {});
  };

  return (
    <Drawer open onClose={onClose} title={project.display_id} full>
      {/* Header проекта */}
      <div className="mb-3 border-b border-slate-200 pb-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <div className="text-xl font-bold">{project.title || "Без названия"}</div>
            <div className="text-sm text-slate-400">{project.display_id}</div>
          </div>
          <div className="flex flex-col items-end gap-1">
            {summary && (
              <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${(HEALTH_META[summary.health] || HEALTH_META.healthy).cls}`}>
                {(HEALTH_META[summary.health] || HEALTH_META.healthy).label}
              </span>
            )}
            {project.archived_at && (
              <span className="rounded bg-slate-200 px-2 py-0.5 text-xs font-semibold text-slate-600">Архив</span>
            )}
          </div>
        </div>

        {summary && (
          <div className="mt-2 grid grid-cols-4 gap-2 text-center">
            <MiniStat label="Дедлайн" value={fmtDate(summary.deadline)} />
            <MiniStat label="Оплата" value={`${summary.payment_percent || "—"} ${summary.currency || ""}`} />
            <MiniStat label="Позиций" value={summary.items_count} />
            <MiniStat label="Откр. задач" value={summary.open_tasks_count} />
          </div>
        )}
        {summary?.suggested_next_action && (
          <div className="mt-2 rounded bg-indigo-50 px-2 py-1.5 text-xs text-indigo-700">
            💡 {summary.suggested_next_action}
          </div>
        )}
        {tags.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {tags.map((tag) => <span key={tag} className="rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] text-indigo-700">#{tag}</span>)}
          </div>
        )}
        {summary?.health_reasons?.length > 0 && (
          <div className="mt-1 flex flex-wrap gap-1">
            {summary.health_reasons.map((r, i) => (
              <span key={i} className="rounded bg-red-50 px-1.5 py-0.5 text-[11px] text-red-600">{r}</span>
            ))}
          </div>
        )}
      </div>

      {/* Табы */}
      <div className="mb-4 flex flex-wrap gap-1 border-b border-slate-200 pb-0">
        {TABS.map((t) => (
          <button
            key={t.key}
            className={`rounded-t-lg px-3 py-1.5 text-sm font-medium ${
              tab === t.key ? "border border-slate-200 border-b-white bg-white text-indigo-600" : "text-slate-500 hover:bg-slate-100"
            }`}
            onClick={() => changeTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loadingTab ? <Spinner /> : (
        <div className="space-y-4">
          {tab === "overview" && (
            <OverviewTab project={project} customFields={customFields} canUpdate={can("project.update")} onSaved={(u) => onSaved(u)} toast={toast} />
          )}            {tab === "production" && (
            <ProductionTab
              project={project}
              items={items}
              events={events}
              itemCustomFields={itemCustomFields}
              canUpdate={can("production.update")}
              onChanged={() => refreshTab("production")}
              toast={toast}
            />
          )}
          {tab === "tasks" && (
            <TasksTab project={project} tasks={tasks} items={items} canCreate={can("task.create")} onChanged={() => refreshTab("tasks")} toast={toast} />
          )}
          {tab === "documents" && (
            <DocumentsTab project={project} docs={docs} items={items} canCreate={can("document.create")} onChanged={() => refreshTab("documents")} toast={toast} />
          )}
          {tab === "activity" && <ActivityTab activity={activity} />}
        </div>
      )}

      {can("project.update") && (
        <div className="mt-4 flex items-center gap-2 border-t border-slate-200 pt-3">
          <Button secondary onClick={handleArchive}>{project.archived_at ? "Разархировать" : "Архивировать"}</Button>
        </div>
      )}
    </Drawer>
  );

  async function handleArchive() {
    try {
      if (project.archived_at) await api.unarchiveProject(project.id);
      else await api.archiveProject(project.id);
      toast(project.archived_at ? "Разархивировано" : "Заархивировано");
      onArchived();
    } catch (e) {
      toast(e.message, "error");
    }
  }
}

function MiniStat({ label, value }) {
  return (
    <div className="rounded bg-slate-50 px-1 py-1.5">
      <div className="text-xs font-semibold text-slate-700">{value ?? "—"}</div>
      <div className="text-[10px] text-slate-400">{label}</div>
    </div>
  );
}

function fmtDate(d) {
  return d ? String(d).slice(0, 10) : "—";
}

// ---------------------------------------------------------------------------
// Обзор: inline-редактирование системных + custom полей
// ---------------------------------------------------------------------------
function OverviewTab({ project, customFields, canUpdate = true, onSaved, toast }) {
  const { members } = useMembers();
  const users = memberOptions(members);
  const [form, setForm] = useState(() => {
    const base = {};
    SYS_FIELDS.forEach((f) => { base[f.field] = project[f.field] ?? ""; });
    return base;
  });
  const [custom, setCustom] = useState(() => {
    const obj = {};
    customFields.forEach((cf) => { obj[cf.slug] = project.custom_values?.[cf.slug] ?? ""; });
    return obj;
  });
  const [saving, setSaving] = useState(false);

  const setF = (field, v) => setForm((f) => ({ ...f, [field]: v }));
  const setC = (slug, v) => setCustom((c) => ({ ...c, [slug]: v }));

  const save = async () => {
    setSaving(true);
    try {
      const payload = {};
      SYS_FIELDS.forEach((f) => {
        let v = form[f.field];
        if (f.kind === "user") {
          // manager: шлём и manager_id, и manager_name (имя для отображения)
          payload.manager_id = v === "" || v === null ? null : v;
          payload.manager_name = v ? (users.find((u) => u.id === v)?.label || null) : null;
          return;
        }
        payload[f.field] = v === "" || v === null ? null : v;
      });
      payload.version = project.version;
      const updated = await api.updateProject(project.id, payload);
      const cv = {};
      Object.entries(custom).forEach(([k, v]) => {
        if (v !== "" && v !== null && v !== undefined) cv[k] = coerce(v);
      });
      await api.putCustomValues(project.id, cv);
      toast("Сохранено");
      onSaved(updated);
    } catch (e) {
      toast(e.response?.message || e.message, "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3">
        {SYS_FIELDS.map((f) => (
          <Field key={f.field} label={f.label}>
            <DetailInput field={f} value={form[f.field]} onChange={(v) => setF(f.field, v)} users={users} />
          </Field>
        ))}
      </div>

      {customFields.length > 0 && (
        <div>
          <div className="mb-2 border-t border-slate-200 pt-3 text-sm font-semibold text-slate-700">
            Пользовательские поля
          </div>
          <div className="grid grid-cols-1 gap-3">
            {customFields.map((cf) => (
              <Field key={cf.id} label={cf.name} required={cf.required}>
                <CustomInput cf={cf} value={custom[cf.slug]} onChange={(v) => setC(cf.slug, v)} />
              </Field>
            ))}
          </div>
        </div>
      )}

      {canUpdate && (
        <div className="flex gap-2">
          <Button primary onClick={save} disabled={saving}>{saving ? "Сохранение..." : "Сохранить"}</Button>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Производство: карточки позиций + таймлайн + редактор
// ---------------------------------------------------------------------------
const MOCKUP_STATUSES = ["Не начат", "В работе", "Сдан", "Правки", "Утверждён"];
const SIGNAL_STATUSES = ["Не начат", "В производстве", "Отгружен", "На согласовании", "Согласован", "Правки"];
const SIGNAL_FEEDBACKS = ["", "Ожидается", "Согласовано", "Правки"];
const BATCH_STATUSES = ["Не начат", "В производстве", "Готов", "Отгружен"];
const BATCH_FEEDBACKS = ["", "Ожидается", "Принято", "Правки"];

function ProductionTab({ project, items, events, itemCustomFields = [], canUpdate = true, onChanged, toast }) {
  const [createOpen, setCreateOpen] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [newName, setNewName] = useState("");
  const [newQty, setNewQty] = useState("");
  const [newSpecs, setNewSpecs] = useState("");
  const [newSignal, setNewSignal] = useState(false);

  const addItem = async () => {
    if (!newName.trim()) { toast("Укажите название позиции", "error"); return; }
    try {
      await api.createItem(project.id, {
        name: newName.trim(),
        quantity: newQty ? Number(newQty) : null,
        tech_specs: newSpecs || null,
        signal_required: newSignal,
      });
      toast("Позиция добавлена");
      setCreateOpen(false); setNewName(""); setNewQty(""); setNewSpecs(""); setNewSignal(false);
      onChanged();
    } catch (e) { toast(e.message, "error"); }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold text-slate-700">
          Состав заказа
          {items.length > 0 && <span className="ml-1 text-slate-400">· {items.length}</span>}
        </div>
        {canUpdate && <Button secondary onClick={() => setCreateOpen((v) => !v)}>+ Добавить позицию</Button>}
      </div>

      {createOpen && (
        <div className="space-y-2 rounded border border-indigo-200 bg-indigo-50 p-3">
          <Field label="Название" required><input className="input" value={newName} onChange={(e) => setNewName(e.target.value)} /></Field>
          <Field label="Количество"><input type="number" className="input" value={newQty} onChange={(e) => setNewQty(e.target.value)} /></Field>
          <Field label="Тех. характеристики"><textarea className="input" rows={2} value={newSpecs} onChange={(e) => setNewSpecs(e.target.value)} /></Field>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" className="accent-indigo-600" checked={newSignal} onChange={(e) => setNewSignal(e.target.checked)} />
            Нужен сигнал
          </label>
          <div className="flex gap-2">
            <Button primary onClick={addItem}>Создать</Button>
            <Button secondary onClick={() => setCreateOpen(false)}>Отмена</Button>
          </div>
        </div>
      )}

      {items.length === 0 ? (
        <div className="rounded border border-dashed border-slate-200 p-6 text-center text-sm text-slate-400">
          Позиций пока нет. Добавьте первую позицию заказа.
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((it) => (
            <ItemCard key={it.id} item={it} onEdit={() => setEditItem(it)} />
          ))}
        </div>
      )}

      {editItem && (
        <ItemEditor
          project={project}
          item={editItem}
          itemCustomFields={itemCustomFields}
          onClose={() => setEditItem(null)}
          onSaved={() => { setEditItem(null); onChanged(); toast("Сохранено"); }}
          toast={toast}
        />
      )}

      {events.length > 0 && (
        <div>
          <div className="mb-1 text-sm font-semibold text-slate-700">События проекта</div>
          <div className="space-y-1">
            {events.map((e, i) => (
              <div key={i} className="flex items-center gap-2 text-xs text-slate-500">
                <span className="rounded bg-slate-100 px-1.5 py-0.5">{e.event_type}</span>
                <span>{e.event_date}</span>
                <span>{e.title}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ItemCard({ item, onEdit }) {
  return (
    <div className="cursor-pointer rounded-lg border border-slate-200 p-3 hover:border-indigo-300 hover:bg-slate-50" onClick={onEdit}>
      <div className="mb-1 flex items-center justify-between">
        <div className="font-semibold">{item.name}</div>
        <div className="text-sm text-slate-500">{item.quantity ?? "—"} шт</div>
      </div>
      <div className="grid grid-cols-3 gap-1 text-xs">
        <StatusLine label="Макет" value={item.mockup_status} />
        <StatusLine label="Сигнал" value={item.signal_status} />
        <StatusLine label="Тираж" value={item.batch_status} />
      </div>
      {(item.signal_feedback || item.batch_feedback) && (
        <div className="mt-1 text-xs text-slate-400">
          {item.signal_feedback && <span>ОС сигнал: {item.signal_feedback}. </span>}
          {item.batch_feedback && <span>ОС тираж: {item.batch_feedback}.</span>}
        </div>
      )}
    </div>
  );
}

function StatusLine({ label, value }) {
  if (!value) return <div className="text-slate-400">{label}: —</div>;
  const active = /в работе|правк|производств/i.test(value);
  const done = /сдан|готов|утвержд|согласован|отгружен|принято/i.test(value);
  const cls = done ? "text-emerald-600" : active ? "text-blue-600" : "text-slate-500";
  return <div className={cls}>{label}: {done ? "✓" : active ? "●" : "•"} {value}</div>;
}

function ItemEditor({ project, item, itemCustomFields, onClose, onSaved, toast }) {
  const [form, setForm] = useState({
    name: item.name, quantity: item.quantity ?? "", tech_specs: item.tech_specs ?? "",
    mockup_status: item.mockup_status ?? "", signal_status: item.signal_status ?? "",
    signal_feedback: item.signal_feedback ?? "", batch_status: item.batch_status ?? "",
    batch_feedback: item.batch_feedback ?? "", signal_required: !!item.signal_required,
  });
  const [custom, setCustom] = useState(() => {
    const obj = {};
    itemCustomFields.forEach((cf) => {
      obj[cf.slug] = item.custom_values?.[cf.slug] ?? cf.default_value ?? "";
    });
    return obj;
  });
  const [saving, setSaving] = useState(false);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const save = async () => {
    setSaving(true);
    try {
      await api.updateItem(item.id, {
        name: form.name, quantity: form.quantity ? Number(form.quantity) : null,
        tech_specs: form.tech_specs || null,
      });
      await api.updateItemProduction(item.id, {
        mockup_status: form.mockup_status || null,
        signal_status: form.signal_status || null,
        signal_feedback: form.signal_feedback || null,
        batch_status: form.batch_status || null,
        batch_feedback: form.batch_feedback || null,
      });
      const cv = {};
      Object.entries(custom).forEach(([k, v]) => { if (v !== "" && v !== null) cv[k] = coerce(v); });
      if (Object.keys(cv).length) await api.putItemCustomValues(item.id, cv);
      onSaved();
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="font-semibold">Позиция: {item.name}</span>
        <button className="btn btn-ghost !px-1.5" onClick={onClose}>×</button>
      </div>
      <div className="grid grid-cols-1 gap-2">
        <Field label="Название"><input className="input" value={form.name} onChange={(e) => set("name", e.target.value)} /></Field>
        <Field label="Количество"><input type="number" className="input" value={form.quantity} onChange={(e) => set("quantity", e.target.value)} /></Field>
        <Field label="Тех. характеристики"><textarea className="input" rows={2} value={form.tech_specs} onChange={(e) => set("tech_specs", e.target.value)} /></Field>

        <div className="grid grid-cols-2 gap-2">
          <Field label="Макет (статус)">
            <select className="input" value={form.mockup_status} onChange={(e) => set("mockup_status", e.target.value)}>
              <option value="">—</option>
              {MOCKUP_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </Field>
          <Field label="Сигнал (статус)">
            <select className="input" value={form.signal_status} onChange={(e) => set("signal_status", e.target.value)}>
              <option value="">—</option>
              {SIGNAL_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </Field>
          <Field label="ОС по сигналу">
            <select className="input" value={form.signal_feedback} onChange={(e) => set("signal_feedback", e.target.value)}>
              {SIGNAL_FEEDBACKS.map((s) => <option key={s || "empty"} value={s}>{s || "—"}</option>)}
            </select>
          </Field>
          <Field label="Тираж (статус)">
            <select className="input" value={form.batch_status} onChange={(e) => set("batch_status", e.target.value)}>
              <option value="">—</option>
              {BATCH_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </Field>
          <Field label="ОС по тиражу">
            <select className="input" value={form.batch_feedback} onChange={(e) => set("batch_feedback", e.target.value)}>
              {BATCH_FEEDBACKS.map((s) => <option key={s || "empty"} value={s}>{s || "—"}</option>)}
            </select>
          </Field>
          <label className="flex items-end pb-1.5 gap-2 text-sm">
            <input type="checkbox" className="accent-indigo-600" checked={form.signal_required} onChange={(e) => set("signal_required", e.target.checked)} />
            Нужен сигнал
          </label>
        </div>

        {itemCustomFields.length > 0 && (
          <div className="grid grid-cols-1 gap-2 border-t border-slate-200 pt-2">
            {itemCustomFields.map((cf) => (
              <Field key={cf.id} label={cf.name}>
                <CustomInput cf={cf} value={custom[cf.slug]} onChange={(v) => setCustom((c) => ({ ...c, [cf.slug]: v }))} />
              </Field>
            ))}
          </div>
        )}
      </div>
      <div className="mt-2 flex gap-2">
        <Button primary onClick={save} disabled={saving}>{saving ? "Сохранение..." : "Сохранить"}</Button>
        <Button secondary onClick={onClose}>Отмена</Button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Задачи
// ---------------------------------------------------------------------------
function TasksTab({ project, tasks, items, canCreate = true, onChanged, toast }) {
  const { members } = useMembers();
  const users = memberOptions(members);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ title: "", assignee_id: "", assignee_name: "", priority: "MEDIUM", due_date: "", project_item_id: "" });

  const create = async () => {
    if (!form.title.trim()) { toast("Укажите название задачи", "error"); return; }
    try {
      await api.createTask(project.id, {
        title: form.title.trim(),
        assignee_id: form.assignee_id || null,
        assignee_name: form.assignee_name || null,
        priority: form.priority,
        due_date: form.due_date || null,
        project_item_id: form.project_item_id || null,
      });
      toast("Задача создана");
      setOpen(false); setForm({ title: "", assignee_id: "", assignee_name: "", priority: "MEDIUM", due_date: "", project_item_id: "" });
      onChanged();
    } catch (e) { toast(e.message, "error"); }
  };

  const toggle = async (t) => {
    try {
      await api.updateTask(project.id, t.id, { status: t.status === "DONE" ? "TODO" : "DONE" });
      onChanged();
    } catch (e) { toast(e.message, "error"); }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-slate-700">Задачи · {tasks.length}</span>
        {canCreate && <Button secondary onClick={() => setOpen((v) => !v)}>+ Новая задача</Button>}
      </div>

      {open && (
        <div className="space-y-2 rounded border border-indigo-200 bg-indigo-50 p-3">
          <Field label="Название" required><input className="input" value={form.title} onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))} /></Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Ответственный">
              <select className="input" value={form.assignee_id} onChange={(e) => { const id = e.target.value; const u = users.find((x) => x.id === id); setForm((f) => ({ ...f, assignee_id: id, assignee_name: u ? u.label : "" })); }}>
                <option value="">—</option>
                {users.map((u) => <option key={u.id} value={u.id}>{u.label}</option>)}
              </select>
            </Field>
            <Field label="Приоритет">
              <select className="input" value={form.priority} onChange={(e) => setForm((f) => ({ ...f, priority: e.target.value }))}>
                {["LOW", "MEDIUM", "HIGH", "URGENT"].map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </Field>
            <Field label="Срок"><input type="date" className="input" value={form.due_date} onChange={(e) => setForm((f) => ({ ...f, due_date: e.target.value }))} /></Field>
            <Field label="Позиция">
              <select className="input" value={form.project_item_id} onChange={(e) => setForm((f) => ({ ...f, project_item_id: e.target.value }))}>
                <option value="">—</option>
                {(items || []).map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}
              </select>
            </Field>
          </div>
          <div className="flex gap-2">
            <Button primary onClick={create}>Создать</Button>
            <Button secondary onClick={() => setOpen(false)}>Отмена</Button>
          </div>
        </div>
      )}

      {tasks.length === 0 ? (
        <div className="rounded border border-dashed border-slate-200 p-6 text-center text-sm text-slate-400">Задач пока нет</div>
      ) : (
        <div className="space-y-1.5">
          {tasks.map((t) => (
            <div key={t.id} className="flex items-start gap-2 rounded border border-slate-100 px-3 py-2 hover:bg-slate-50">
              <input type="checkbox" className="mt-0.5 accent-indigo-600" checked={t.status === "DONE"} onChange={() => toggle(t)} />
              <div className="flex-1">
                <div className={t.status === "DONE" ? "text-slate-400 line-through" : ""}>{t.title}</div>
                <div className="text-xs text-slate-400">
                  {t.assignee_name && <span>{t.assignee_name} · </span>}
                  {t.priority && <span className="badge-priority">{t.priority} · </span>}
                  {t.due_date && <span>{t.due_date}</span>}
                  {t.project_item_id && <span> · позиция</span>}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Документы
// ---------------------------------------------------------------------------
const DOC_TYPES = [
  { value: "MOCKUP", label: "УПД дизайн" },
  { value: "SIGNAL", label: "УПД сигнал" },
  { value: "BATCH", label: "УПД производство" },
  { value: "UNIFIED", label: "УПД объединённый" },
];
const DOC_STATUSES = ["NOT_READY", "PREPARED", "SENT", "SIGNED"];
const DOC_STATUS_LABEL = { NOT_READY: "Не готов", PREPARED: "Подготовлен", SENT: "Отправлен", SIGNED: "Подписан" };

function DocumentsTab({ project, docs, items, canCreate = true, onChanged, toast }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ document_type: "UNIFIED", status: "NOT_READY", file_name: "", comment: "", project_item_id: "" });

  const create = async () => {
    try {
      await api.createDocument(project.id, {
        document_type: form.document_type,
        status: form.status,
        file_name: form.file_name || null,
        comment: form.comment || null,
        project_item_id: form.project_item_id || null,
      });
      toast("Документ добавлен");
      setOpen(false); setForm({ document_type: "UNIFIED", status: "NOT_READY", file_name: "", comment: "", project_item_id: "" });
      onChanged();
    } catch (e) { toast(e.message, "error"); }
  };

  const setStatus = async (d, status) => {
    try { await api.updateDocument(project.id, d.id, { status }); onChanged(); }
    catch (e) { toast(e.message, "error"); }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-slate-700">Документы · {docs.length}</span>
        {canCreate && <Button secondary onClick={() => setOpen((v) => !v)}>+ Добавить документ</Button>}
      </div>

      {open && (
        <div className="space-y-2 rounded border border-indigo-200 bg-indigo-50 p-3">
          <Field label="Тип">
            <select className="input" value={form.document_type} onChange={(e) => setForm((f) => ({ ...f, document_type: e.target.value }))}>
              {DOC_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </Field>
          <Field label="Статус">
            <select className="input" value={form.status} onChange={(e) => setForm((f) => ({ ...f, status: e.target.value }))}>
              {DOC_STATUSES.map((s) => <option key={s} value={s}>{DOC_STATUS_LABEL[s]}</option>)}
            </select>
          </Field>
          <Field label="Файл"><input className="input" value={form.file_name} onChange={(e) => setForm((f) => ({ ...f, file_name: e.target.value }))} /></Field>
          <Field label="Комментарий"><input className="input" value={form.comment} onChange={(e) => setForm((f) => ({ ...f, comment: e.target.value }))} /></Field>
          <Field label="Позиция">
            <select className="input" value={form.project_item_id} onChange={(e) => setForm((f) => ({ ...f, project_item_id: e.target.value }))}>
              <option value="">—</option>
              {(items || []).map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}
            </select>
          </Field>
          <div className="flex gap-2">
            <Button primary onClick={create}>Создать</Button>
            <Button secondary onClick={() => setOpen(false)}>Отмена</Button>
          </div>
        </div>
      )}

      {docs.length === 0 ? (
        <div className="rounded border border-dashed border-slate-200 p-6 text-center text-sm text-slate-400">Документов пока нет</div>
      ) : (
        <div className="space-y-1.5">
          {docs.map((d) => {
            const label = DOC_TYPES.find((t) => t.value === d.document_type)?.label || d.document_type;
            return (
              <div key={d.id} className="flex items-center justify-between rounded border border-slate-100 px-3 py-2">
                <div>
                  <div className="text-sm font-medium">{label}</div>
                  <div className="text-xs text-slate-400">
                    {d.file_name || "без файла"} {d.comment ? `· ${d.comment}` : ""}
                  </div>
                </div>
                <select
                  className="input !w-auto"
                  value={d.status}
                  onChange={(e) => setStatus(d, e.target.value)}
                >
                  {DOC_STATUSES.map((s) => <option key={s} value={s}>{DOC_STATUS_LABEL[s]}</option>)}
                </select>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// История (Activity)
// ---------------------------------------------------------------------------
function ActivityTab({ activity }) {
  if (!activity.length) {
    return <div className="rounded border border-dashed border-slate-200 p-6 text-center text-sm text-slate-400">История пуста</div>;
  }
  return (
    <div className="space-y-2">
      {activity.map((a, i) => (
        <div key={i} className="flex items-start gap-2 text-sm">
          <div className="w-16 shrink-0 text-xs text-slate-400">{a.created_at ? String(a.created_at).slice(0, 16).replace("T", " ") : ""}</div>
          <div className="text-slate-600">
            <span className="font-medium">{a.user_name || "Система"}</span>
            <span className="text-slate-400"> {a.action} · {a.entity_type}</span>
            {a.new_value && Object.keys(a.new_value).length > 0 && (
              <div className="text-xs text-slate-400">{Object.entries(a.new_value).slice(0, 3).map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : v}`).join(", ")}</div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------
function DetailInput({ field, value, onChange, users }) {
  if (field.kind === "date") {
    return <input type="date" className="input" value={value ? String(value).slice(0, 10) : ""} onChange={(e) => onChange(e.target.value || "")} />;
  }
  if (field.kind === "select") {
    return (
      <select className="input" value={value || ""} onChange={(e) => onChange(e.target.value)}>
        <option value="">—</option>
        {field.options.map((o) => (<option key={o} value={o}>{o}</option>))}
      </select>
    );
  }
  if (field.kind === "user") {
    return (
      <select className="input" value={value || ""} onChange={(e) => onChange(e.target.value)}>
        <option value="">—</option>
        {(users || []).map((u) => <option key={u.id} value={u.id}>{u.label}</option>)}
      </select>
    );
  }
  return <input className="input" value={value ?? ""} onChange={(e) => onChange(e.target.value)} />;
}

function coerce(v) {
  if (typeof v === "string") {
    const n = Number(v);
    if (v.trim() !== "" && !isNaN(n) && /^-?\d+(\.\d+)?$/.test(v.trim())) return n;
  }
  return v;
}