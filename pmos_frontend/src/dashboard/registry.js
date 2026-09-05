import React from "react";
import {
  Activity,
  AlertTriangle,
  Calendar,
  CheckSquare,
  Clock,
  Factory,
  Folder,
  Gauge,
  Sparkles,
  Wallet,
} from "lucide-react";
import CalendarWidget from "./widgets/CalendarWidget.jsx";
import {
  ActivityWidget,
  AISummaryWidget,
  DeadlinesWidget,
  FinanceWidget,
  KpiWidget,
  ProductionWidget,
  ProjectsWidget,
  RisksWidget,
  TodayTasksWidget,
} from "./widgets/WidgetsList.jsx";

/**
 * Widget Registry (4.md §2, §39).
 * Новый виджет = Widget Definition + Component + Data Provider — движок не трогаем.
 * settings: группы полей настроек (4.md §11-15), рендерятся WidgetSettingsModal.
 */
export const WIDGET_REGISTRY = {
  calendar: {
    type: "calendar",
    name: "Календарь",
    description: "Проекты, задачи и события по датам",
    icon: Calendar,
    category: "planning",
    defaultSize: { w: 6, h: 4 },
    component: CalendarWidget,
    settings: [
      {
        section: "Режим",
        fields: [
          { key: "view", label: "Режим", type: "radio", options: [
            { value: "month", label: "Месяц" },
            { value: "week", label: "Неделя" },
            { value: "day", label: "День" }], default: "month" },
        ],
      },
      {
        section: "Показывать",
        fields: [
          { key: "show_deadlines", label: "Дедлайны", type: "check", default: true },
          { key: "show_tasks", label: "Задачи", type: "check", default: true },
          { key: "show_payments", label: "Оплаты", type: "check", default: true },
          { key: "show_production", label: "Производство", type: "check", default: true },
        ],
      },
    ],
  },
  "today-tasks": {
    type: "today-tasks",
    name: "Что сделать сегодня",
    description: "Задачи на сегодня, просроченные и Next Action",
    icon: CheckSquare,
    category: "planning",
    defaultSize: { w: 4, h: 4 },
    component: TodayTasksWidget,
    settings: [
      {
        section: "Показывать",
        fields: [
          { key: "show_overdue", label: "Просроченные", type: "check", default: true },
          { key: "show_today", label: "Сегодня", type: "check", default: true },
          { key: "show_next_actions", label: "Next Action", type: "check", default: true },
        ],
      },
      {
        section: "Лимит",
        fields: [
          { key: "max", label: "Максимум", type: "number", min: 5, max: 50, default: 10 },
        ],
      },
    ],
  },
  deadlines: {
    type: "deadlines",
    name: "Ближайшие дедлайны",
    description: "Дедлайны проектов и позиций ближайших N дней",
    icon: Clock,
    category: "planning",
    defaultSize: { w: 6, h: 2 },
    component: DeadlinesWidget,
    settings: [
      {
        section: "Период",
        fields: [
          { key: "period_days", label: "Дней вперёд", type: "select", options: [
            { value: 7, label: "7 дней" }, { value: 14, label: "14 дней" },
            { value: 30, label: "30 дней" }, { value: 90, label: "90 дней" }], default: 7 },
        ],
      },
    ],
  },
  projects: {
    type: "projects",
    name: "Проекты",
    description: "Компактный список проектов",
    icon: Folder,
    category: "projects",
    defaultSize: { w: 3, h: 4 },
    component: ProjectsWidget,
    settings: [
      {
        section: "Список",
        fields: [
          { key: "limit", label: "Максимум проектов", type: "number", min: 5, max: 50, default: 10 },
          { key: "view_id", label: "ID View (необязательно)", type: "text", default: "" },
        ],
      },
    ],
  },
  risks: {
    type: "risks",
    name: "Срочные риски",
    description: "High/Critical, просроченные, проблемы производства",
    icon: AlertTriangle,
    category: "projects",
    defaultSize: { w: 3, h: 4 },
    component: RisksWidget,
    settings: [
      {
        section: "Уровни",
        fields: [
          { key: "levels", label: "Уровни риска", type: "multi", options: [
            { value: "Критический", label: "Критический" },
            { value: "Высокий", label: "Высокий" },
            { value: "Средний", label: "Средний" }], default: ["Критический", "Высокий"] },
        ],
      },
      {
        section: "Показывать",
        fields: [
          { key: "show_overdue", label: "Просроченные", type: "check", default: true },
          { key: "show_production", label: "Производственные проблемы", type: "check", default: true },
        ],
      },
    ],
  },
  finance: {
    type: "finance",
    name: "Финансы",
    description: "Неоплаченные проекты, авансы, доплаты, валюты",
    icon: Wallet,
    category: "finance",
    defaultSize: { w: 6, h: 3 },
    component: FinanceWidget,
    settings: [],
  },
  production: {
    type: "production",
    name: "Производство",
    description: "Состояние Project Items: макеты, сигналы, тираж, отгрузка",
    icon: Factory,
    category: "production",
    defaultSize: { w: 6, h: 2 },
    component: ProductionWidget,
    settings: [],
  },
  activity: {
    type: "activity",
    name: "Последние изменения",
    description: "Audit Activity: кто и что менял",
    icon: Activity,
    category: "overview",
    defaultSize: { w: 6, h: 3 },
    component: ActivityWidget,
    settings: [
      {
        section: "Лимит",
        fields: [
          { key: "limit", label: "Максимум записей", type: "number", min: 5, max: 100, default: 15 },
        ],
      },
    ],
  },
  kpi: {
    type: "kpi",
    name: "KPI",
    description: "Универсальный счётчик метрики",
    icon: Gauge,
    category: "overview",
    defaultSize: { w: 2, h: 1 },
    component: KpiWidget,
    settings: [
      {
        section: "Источник метрики",
        fields: [
          { key: "metric", label: "Метрика", type: "select", options: [
            { value: "active_projects", label: "Активные проекты" },
            { value: "open_tasks", label: "Открытые задачи" },
            { value: "deadlines_7d", label: "Дедлайны 7 дней" },
            { value: "overdue_projects", label: "Просроченные проекты" },
            { value: "unpaid_projects", label: "Не оплачены полностью" },
            { value: "signals_in_work", label: "Сигналы в работе" },
            { value: "batch_in_work", label: "Тираж в работе" },
            { value: "shipments_pending", label: "Ожидают отгрузки" },
            { value: "awaiting_feedback", label: "Ждут ОС" },
            { value: "mockup_revision", label: "Правки макетов" },
            { value: "advances_7d", label: "Авансы 7 дней" },
            { value: "finals_7d", label: "Доплаты 7 дней" },], default: "active_projects" },
          { key: "metric_name", label: "Подпись (необязательно)", type: "text", default: "" },
        ],
      },
    ],
  },
  ai_summary: {
    type: "ai_summary",
    name: "AI Assistant",
    description: "Что происходит сегодня?",
    icon: Sparkles,
    category: "overview",
    defaultSize: { w: 6, h: 2 },
    component: AISummaryWidget,
    settings: [],
  },
  // legacy-типы (этап 1): не удаляем из реестра (Additive Architecture)
  tasks: {
    type: "tasks", name: "Задачи (legacy)", description: "Старый тип — сегодня-задачи",
    icon: CheckSquare, category: "planning", defaultSize: { w: 2, h: 2 }, component: TodayTasksWidget, settings: [],
  },
  payments: {
    type: "payments", name: "Оплаты (legacy)", description: "Старый тип — финансы",
    icon: Wallet, category: "finance", defaultSize: { w: 2, h: 2 }, component: FinanceWidget, settings: [],
  },
  chart: {
    type: "chart", name: "График (legacy)", description: "Старый тип",
    icon: Gauge, category: "overview", defaultSize: { w: 2, h: 2 }, component: KpiWidget, settings: [],
  },
  table: {
    type: "table", name: "Таблица (legacy)", description: "Старый тип",
    icon: Folder, category: "overview", defaultSize: { w: 3, h: 2 }, component: ProjectsWidget, settings: [],
  },
  note: {
    type: "note", name: "Заметка (legacy)", description: "Старый тип",
    icon: CheckSquare, category: "overview", defaultSize: { w: 1, h: 1 }, component: AISummaryWidget, settings: [],
  },
};

// Новые типы для Picker (legacy-типы не предлагаются при добавлении)
export const PICKABLE_TYPES = [
  "calendar", "today-tasks", "deadlines", "projects", "risks",
  "finance", "production", "activity", "kpi", "ai_summary",
];

export const CATEGORY_NAMES = {
  planning: "Планирование",
  projects: "Проекты",
  finance: "Финансы",
  production: "Производство",
  overview: "Обзор",
};

export const DASHBOARD_TEMPLATES = [
  { key: "empty", name: "Пустой" },
  { key: "manager", name: "Менеджер" },
  { key: "production", name: "Производство" },
  { key: "finance", name: "Финансы" },
  { key: "director", name: "Руководитель" },
];

export function widgetDef(type) {
  return WIDGET_REGISTRY[type] || null;
}