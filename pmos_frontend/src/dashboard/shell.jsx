import React from "react";

/** Скелетон загрузки виджета (4.md §28). */
export function WidgetLoading({ rows = 4 }) {
  return (
    <div className="space-y-2 p-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-3 animate-pulse rounded bg-slate-100" style={{ width: `${90 - i * 12}%` }} />
      ))}
    </div>
  );
}

/** Ошибка виджета изолирована: retry, никаких 500 пользователю (4.md §29). */
export function WidgetError({ message, onRetry }) {
  return (
    <div className="flex flex-col items-center gap-2 p-5 text-sm">
      <span className="text-red-500">⚠️</span>
      <div className="text-center text-slate-500">
        {message || "Не удалось загрузить данные."}
      </div>
      <button onClick={onRetry} className="btn btn-secondary btn-sm">
        Повторить
      </button>
    </div>
  );
}

/** Пустой виджет объясняет, почему ничего нет (4.md §27). */
export function WidgetEmpty({ children }) {
  return <div className="flex items-center justify-center p-6 text-sm text-slate-400">{children}</div>;
}

export const LEVEL_COLORS = {
  Критический: "bg-red-100 text-red-700",
  Высокий: "bg-orange-100 text-orange-700",
  Средний: "bg-amber-100 text-amber-700",
  Низкий: "bg-emerald-100 text-emerald-700",
  default: "bg-slate-100 text-slate-600",
};

export function RiskChip({ level }) {
  const cls = LEVEL_COLORS[level] || LEVEL_COLORS.default;
  return (
    <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-medium ${cls}`}>
      {level || "—"}
    </span>
  );
}

export function fmtDate(iso) {
  if (!iso) return "";
  const d = new Date(iso.endsWith("Z") || iso.includes("T") ? iso : `${iso}T00:00:00`);
  if (Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit" });
}

export function daysLeft(iso) {
  if (!iso) return "";
  const d = new Date(`${iso}T00:00:00`);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diff = Math.round((d - today) / 86400000);
  if (diff < 0) return `просрочено ${-diff} дн.`;
  if (diff === 0) return "сегодня";
  if (diff === 1) return "завтра";
  return `через ${diff} дн.`;
}