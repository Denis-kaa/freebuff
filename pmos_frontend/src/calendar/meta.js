import {
  AlertTriangle,
  CheckSquare,
  Factory,
  FileText,
  HandCoins,
  Phone,
  Star,
  StickyNote,
  Truck,
} from "lucide-react";

/**
 * Метаданные типов событий (5.md §27): icon + label + цвет.
 * Цвет не единственный способ определения типа — всегда есть иконка и подпись.
 */
export const EVENT_META = {
  PROJECT_DEADLINE: { label: "Дедлайн", color: "text-red-600 bg-red-50 border-red-200", dot: "bg-red-500", icon: AlertTriangle },
  TASK_DEADLINE: { label: "Задача", color: "text-emerald-600 bg-emerald-50 border-emerald-200", dot: "bg-emerald-500", icon: CheckSquare },
  PAYMENT_ADVANCE: { label: "Аванс", color: "text-violet-600 bg-violet-50 border-violet-200", dot: "bg-violet-500", icon: HandCoins },
  PAYMENT_FINAL: { label: "Доплата", color: "text-indigo-600 bg-indigo-50 border-indigo-200", dot: "bg-indigo-500", icon: HandCoins },
  SIGNAL_SHIPMENT: { label: "Отгрузка сигнала", color: "text-amber-600 bg-amber-50 border-amber-200", dot: "bg-amber-500", icon: Truck },
  BATCH_SHIPMENT: { label: "Отгрузка тиража", color: "text-amber-700 bg-amber-50 border-amber-200", dot: "bg-amber-600", icon: Truck },
  PRODUCTION: { label: "Производство", color: "text-sky-600 bg-sky-50 border-sky-200", dot: "bg-sky-500", icon: Factory },
  BATCH_READY: { label: "Тираж готов", color: "text-teal-600 bg-teal-50 border-teal-200", dot: "bg-teal-500", icon: Factory },
  SIGNAL_FEEDBACK: { label: "ОС по сигналу", color: "text-orange-600 bg-orange-50 border-orange-200", dot: "bg-orange-500", icon: Factory },
  DOCUMENT: { label: "Документ", color: "text-slate-600 bg-slate-100 border-slate-300", dot: "bg-slate-400", icon: FileText },
  REMINDER: { label: "Напоминание", color: "text-fuchsia-600 bg-fuchsia-50 border-fuchsia-200", dot: "bg-fuchsia-500", icon: StickyNote },
  MEETING: { label: "Встреча", color: "text-pink-600 bg-pink-50 border-pink-200", dot: "bg-pink-500", icon: StickyNote },
  CALL: { label: "Звонок", color: "text-cyan-600 bg-cyan-50 border-cyan-200", dot: "bg-cyan-500", icon: Phone },
  OTHER: { label: "Событие", color: "text-slate-500 bg-slate-50 border-slate-200", dot: "bg-slate-400", icon: StickyNote },
  CUSTOM: { label: "Событие", color: "text-slate-500 bg-slate-50 border-slate-200", dot: "bg-slate-400", icon: Star },
};

export const EVENT_LABEL = {
  PROJECT_DEADLINE: "🔴 Дедлайн",
  TASK_DEADLINE: "✓ Задача",
  PAYMENT_ADVANCE: "💳 Аванс",
  PAYMENT_FINAL: "💳 Доплата",
  SIGNAL_SHIPMENT: "🚚 Отгрузка сигнала",
  BATCH_SHIPMENT: "🚚 Отгрузка тиража",
  PRODUCTION: "🏭 Производство",
  BATCH_READY: "🏭 Тираж готов",
  SIGNAL_FEEDBACK: "🟡 ОС по сигналу",
  DOCUMENT: "📄 Документ",
  REMINDER: "📌 Напоминание",
  MEETING: "📅 Встреча",
  CALL: "📞 Звонок",
  OTHER: "⭐ Событие",
  CUSTOM: "⭐ Событие",
};

export function eventMeta(type) {
  return EVENT_META[type] || EVENT_META.CUSTOM;
}

export const CUSTOM_EVENT_TYPES = [
  { value: "REMINDER", label: "Напоминание" },
  { value: "MEETING", label: "Встреча" },
  { value: "CALL", label: "Звонок" },
  { value: "OTHER", label: "Другое" },
];

// Группы фильтров (5.md §11)
export const FILTER_GROUPS = [
  { key: "deadline", label: "Дедлайны", types: ["PROJECT_DEADLINE"] },
  { key: "task", label: "Задачи", types: ["TASK_DEADLINE"] },
  { key: "payment", label: "Оплаты", types: ["PAYMENT_ADVANCE", "PAYMENT_FINAL"] },
  { key: "production", label: "Производство", types: ["PRODUCTION", "SIGNAL_FEEDBACK", "BATCH_READY"] },
  { key: "shipment", label: "Отгрузки", types: ["SIGNAL_SHIPMENT", "BATCH_SHIPMENT"] },
  { key: "document", label: "Документы", types: ["DOCUMENT"] },
  { key: "custom", label: "Пользовательские", types: ["CUSTOM", "REMINDER", "MEETING", "CALL", "OTHER"] },
];

export function fmtEventDate(iso, allDay) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit" });
}

export function fmtEventTime(iso, allDay) {
  if (allDay) return "весь день";
  const d = new Date(iso);
  return d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
}