import React from "react";
import { api } from "../../api.js";
import { EVENT_LABEL } from "../../calendar/meta.js";
import { useWidgetData } from "../useWidgetData.js";
import { WidgetEmpty, WidgetError, WidgetLoading, RiskChip, daysLeft, fmtDate } from "../shell.jsx";

function Row({ displayId, title, right, onClick, tone }) {
  return (
    <div
      onClick={onClick}
      className={`flex cursor-pointer items-center justify-between gap-2 rounded px-1.5 py-1 text-xs hover:bg-indigo-50 ${tone || "text-slate-700"}`}
    >
      <span className="truncate">
        {displayId && <span className="mr-1 font-mono text-[10px] text-slate-400">{displayId}</span>}
        <span className="font-medium">{title}</span>
      </span>
      {right}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ЧТО СДЕЛАТЬ СЕГОДНЯ (5.md §30, §41): CalendarService -> /calendar/today.
// Виджет не имеет собственной бизнес-логики — единый Calendar Engine.
// ---------------------------------------------------------------------------
export function TodayTasksWidget({ config = {}, onProjectClick }) {
  const max = config.max || 10;
  const showOverdue = config.show_overdue !== false;
  const showToday = config.show_today !== false;
  const showNext = config.show_next_actions !== false;
  const { data, loading, error, refresh } = useWidgetData(() => api.calendarToday(), []);
  if (loading) return <WidgetLoading rows={6} />;
  if (error) return <WidgetError message={error} onRetry={refresh} />;

  const section = (label, items, tone) =>
    items.length > 0 && (
      <div className="mb-1.5">
        <div className="mb-0.5 text-[10px] font-bold uppercase tracking-wide text-slate-400">{label}</div>
        {items.slice(0, max).map((e, i) => (
          <Row
            key={`${e.id || i}`}
            displayId={e.metadata?.project_display_id}
            title={e.title}
            tone={tone}
            onClick={() => e.project_id && onProjectClick?.(e.project_id, e.metadata?.project_display_id)}
            right={
              <span className="shrink-0 rounded bg-slate-100 px-1 py-0.5 text-[10px] text-slate-500">
                {EVENT_LABEL[e.type] || e.type}
              </span>
            }
          />
        ))}
      </div>
    );

  const todayItems = [...(data?.events || [])];
  return (
    <div className="h-full overflow-y-auto p-2">
      {showOverdue && section("⚠️ Просроченные", data?.overdue || [], "text-red-600")}
      {showToday && section("📌 Сегодня", todayItems, "text-slate-800")}
      {showNext && section("⚡ Next Action", data?.next_actions || [], "text-indigo-700")}
      {!data?.overdue?.length && !todayItems.length && !data?.next_actions?.length && (
        <WidgetEmpty>🎉 На сегодня задач нет.</WidgetEmpty>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// БЛИЖАЙШИЕ ДЕДЛАЙНЫ (4.md §13)
// ---------------------------------------------------------------------------
export function DeadlinesWidget({ config = {}, onProjectClick }) {
  const days = config.period_days || 7;
  const { data, loading, error, refresh } = useWidgetData(
    () => api.widgetData.deadlines(days),
    [days]
  );
  if (loading) return <WidgetLoading rows={5} />;
  if (error) return <WidgetError message={error} onRetry={refresh} />;
  const items = (data?.items || []).slice(0, 20);

  return (
    <div className="h-full overflow-y-auto p-2">
      {items.length === 0 && (
        <WidgetEmpty>Нет дедлайнов на ближайшие {days} дн.</WidgetEmpty>
      )}
      {items.map((d, i) => (
        <Row
          key={i}
          displayId={d.display_id}
          title={d.title}
          tone={d.days_left === 0 ? "text-amber-600" : d.days_left < 0 ? "text-red-600" : ""}
          onClick={() => d.project_id && onProjectClick?.(d.project_id, d.display_id)}
          right={
            <span className={`shrink-0 rounded px-1 text-[10px] ${d.days_left === 0 ? "bg-amber-100 text-amber-700" : "bg-slate-100 text-slate-500"}`}>
              {daysLeft(d.date)}
            </span>
          }
        />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// СРОЧНЫЕ РИСКИ (4.md §14)
// ---------------------------------------------------------------------------
export function RisksWidget({ config = {}, onProjectClick }) {
  const levels = config.levels?.length ? config.levels.join(",") : "Высокий,Критический";
  const showOverdue = config.show_overdue !== false;
  const showProduction = config.show_production !== false;
  const { data, loading, error, refresh } = useWidgetData(
    () => api.widgetData.risks(levels, showOverdue, showProduction),
    [levels, showOverdue, showProduction]
  );
  if (loading) return <WidgetLoading rows={5} />;
  if (error) return <WidgetError message={error} onRetry={refresh} />;
  const items = (data?.items || []).slice(0, 20);

  return (
    <div className="h-full overflow-y-auto p-2">
      {items.length === 0 && <WidgetEmpty>Рисков нет 🎈</WidgetEmpty>}
      {items.map((r, i) => (
        <Row
          key={i}
          displayId={r.display_id}
          title={r.reason || r.title}
          onClick={() => onProjectClick?.(r.id, r.display_id)}
          right={<RiskChip level={r.risk_level} />}
        />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ПРОЕКТЫ — компактный список (4.md §38-widget)
// ---------------------------------------------------------------------------
export function ProjectsWidget({ config = {}, onProjectClick }) {
  const limit = config.limit || 10;
  const viewId = config.view_id || "";
  const { data, loading, error, refresh } = useWidgetData(
    () => api.widgetData.projects(limit, viewId),
    [limit, viewId]
  );
  if (loading) return <WidgetLoading rows={6} />;
  if (error) return <WidgetError message={error} onRetry={refresh} />;
  return (
    <div className="h-full overflow-y-auto p-2">
      {!data?.length && <WidgetEmpty>Проектов пока нет</WidgetEmpty>}
      {data.map((p) => (
        <Row
          key={p.id}
          displayId={p.display_id}
          title={p.title}
          onClick={() => onProjectClick?.(p.id, p.display_id)}
          right={
            <span className="flex shrink-0 items-center gap-1">
              {p.stage && <span className="text-[10px] text-slate-400">{p.stage}</span>}
              {p.deadline && <span className="text-[10px] text-slate-400">{fmtDate(p.deadline)}</span>}
            </span>
          }
        />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ФИНАНСЫ (4.md §38)
// ---------------------------------------------------------------------------
export function FinanceWidget({ config = {}, onProjectClick }) {
  const { data, loading, error, refresh } = useWidgetData(() => api.widgetData.finance(), []);
  const fmtPct = (p) => (p || "").replace("%", "");
  if (loading) return <WidgetLoading rows={6} />;
  if (error) return <WidgetError message={error} onRetry={refresh} />;

  return (
    <div className="flex h-full flex-col gap-1.5 overflow-y-auto p-2">
      <div className="flex flex-wrap gap-1">
        {Object.entries(data?.currencies || {}).map(([cur, n]) => (
          <span key={cur} className="rounded bg-emerald-50 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-700">
            {cur}: {n}
          </span>
        ))}
      </div>
      <div>
        <div className="mb-0.5 text-[10px] font-bold uppercase text-slate-400">
          Не оплачены полностью ({data?.unpaid_count || 0})
        </div>
        {(data?.unpaid || []).slice(0, 8).map((p, i) => (
          <Row
            key={i}
            displayId={p.display_id}
            title={p.title}
            onClick={() => onProjectClick?.(p.id, p.display_id)}
            right={
              <span
                className={`shrink-0 rounded px-1 text-[10px] font-medium ${
                  fmtPct(p.payment_percent) === "0" || !fmtPct(p.payment_percent)
                    ? "bg-red-100 text-red-700"
                    : "bg-amber-100 text-amber-700"
                }`}
              >
                {p.payment_percent || "0%"}
              </span>
            }
          />
        ))}
        {!data?.unpaid?.length && <div className="text-xs text-slate-400">Все проекты оплачены 🎉</div>}
      </div>
      {(data?.advances_due?.length > 0 || data?.finals_due?.length > 0) && (
        <div className="grid grid-cols-2 gap-1 text-[10px] text-slate-500">
          {data?.advances_due?.length > 0 && (
            <div className="rounded bg-slate-50 p-1">
              <span className="font-semibold">Авансы (7д):</span> {data.advances_due.map((p) => `${p.display_id} (${fmtDate(p.advance_date)})`).join(", ")}
            </div>
          )}
          {data?.finals_due?.length > 0 && (
            <div className="rounded bg-slate-50 p-1">
              <span className="font-semibold">Доплаты (7д):</span> {data.finals_due.map((p) => `${p.display_id} (${fmtDate(p.final_payment_date)})`).join(", ")}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ПРОИЗВОДСТВО — счётчики позиций (4.md §38)
// ---------------------------------------------------------------------------
export function ProductionWidget({ config = {}, onProjectClick }) {
  const { data, loading, error, refresh } = useWidgetData(() => api.widgetData.production(), []);
  if (loading) return <WidgetLoading rows={3} />;
  if (error) return <WidgetError message={error} onRetry={refresh} />;

  const tone = {
    active: "border-indigo-200 bg-indigo-50 text-indigo-700",
    pending: "border-amber-200 bg-amber-50 text-amber-700",
  };
  return (
    <div className="flex h-full flex-col gap-1.5 p-2">
      <div className="grid grid-cols-3 gap-1.5">
        {(data?.items || []).map((it) => (
          <div key={it.key} className={`rounded-lg border p-2 text-center ${tone[it.status] || "border-slate-200 bg-white text-slate-700"}`}>
            <div className="text-2xl font-bold">{it.count}</div>
            <div className="text-[10px] leading-tight">{it.label}</div>
          </div>
        ))}
        {(data?.items || []).length === 0 && (
          <div className="col-span-3 py-4 text-center text-sm text-slate-400">Производство пусто</div>
        )}
      </div>
      <div className="text-[10px] text-slate-400">Всего позиций: {data?.total_items || 0}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ПОСЛЕДНИЕ ИЗМЕНЕНИЯ (Audit Activity)
// ---------------------------------------------------------------------------
export function ActivityWidget({ config = {} }) {
  const limit = config.limit || 15;
  const { data, loading, error, refresh } = useWidgetData(() => api.widgetData.activity(limit), [limit]);
  if (loading) return <WidgetLoading rows={6} />;
  if (error) return <WidgetError message={error} onRetry={refresh} />;
  const actionLabel = { create: "создал", update: "изменил", delete: "удалил" };
  return (
    <div className="h-full overflow-y-auto p-2">
      {!data?.items?.length && <WidgetEmpty>Изменений пока нет</WidgetEmpty>}
      {data?.items?.map((a, i) => (
        <div key={i} className="flex items-baseline gap-1.5 rounded px-1.5 py-0.5 text-xs text-slate-600 hover:bg-slate-50">
          <span className="font-medium text-slate-700">{a.user_name || "Система"}</span>
          <span className="text-slate-400">{actionLabel[a.action] || a.action}</span>
          <span className="truncate text-slate-500">{a.entity_type}</span>
          <span className="ml-auto shrink-0 text-[10px] text-slate-300">
            {a.created_at ? fmtDate(a.created_at) : ""}
          </span>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// KPI — универсальный счётчик, источник настраивается (4.md §40-widget)
// ---------------------------------------------------------------------------
export function KpiWidget({ config = {} }) {
  const metric = config.metric || "active_projects";
  const { data, loading, error, refresh } = useWidgetData(() => api.widgetData.kpi(metric), [metric]);
  if (loading) {
    return <div className="flex h-full items-center justify-center gap-2 p-2">
      <span className="h-6 w-6 animate-pulse rounded bg-slate-100" />
    </div>;
  }
  if (error) return <WidgetError message={error} onRetry={refresh} />;
  return (
    <div className="flex h-full flex-col items-center justify-center p-2">
      <div className="text-3xl font-extrabold text-indigo-600">{data?.value ?? 0}</div>
      <div className="text-center text-[11px] text-slate-500">{data?.label || config.metric_name || metric}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// AI ASSISTANT — архитектура (4.md §40): пока детерминированная агрегация
// ---------------------------------------------------------------------------
export function AISummaryWidget({ config = {} }) {
  const { data, loading, error, refresh } = useWidgetData(() => api.widgetData.aiSummary(), []);
  if (loading) return <WidgetLoading rows={3} />;
  if (error) return <WidgetError message={error} onRetry={refresh} />;
  return (
    <div className="flex h-full flex-col justify-center gap-1.5 p-3">
      <div className="text-[10px] font-bold uppercase tracking-wide text-indigo-400">
        ✨ Что происходит сегодня?
      </div>
      <div className="text-sm leading-snug text-slate-700">{data?.summary}</div>
      <div className="flex gap-1.5">
        {Object.entries(data?.counts || {}).map(([k, v]) => (
          <span key={k} className="rounded bg-indigo-50 px-1.5 py-0.5 text-[10px] font-medium text-indigo-700">
            {k}: {v}
          </span>
        ))}
      </div>
    </div>
  );
}