// Системные колонки проекта (спец. 2.md §3).
// Системное поле НЕ удаляется при скрытии — только из отображения.
export const SYSTEM_COLUMNS = [
  { key: "display_id", label: "ID", field: "display_id", kind: "text" },
  { key: "title", label: "Проект", field: "title", kind: "text" },
  { key: "client_legal_name", label: "Юр. лицо", field: "client_legal_name", kind: "text" },
  { key: "manager_name", label: "Менеджер", field: "manager_name", kind: "text" },
  { key: "stage", label: "Этап", field: "stage", kind: "text" },
  { key: "deadline", label: "Дедлайн", field: "deadline", kind: "date", sortable: true },
  { key: "payment_percent", label: "Оплата %", field: "payment_percent", kind: "text" },
  { key: "currency", label: "Валюта", field: "currency", kind: "text" },
  { key: "risk_level", label: "Риск", field: "risk_level", kind: "text" },
  { key: "next_action", label: "Следующее действие", field: "next_action", kind: "text" },
  { key: "advance_date", label: "Дата аванса", field: "advance_date", kind: "date" },
  { key: "final_payment_date", label: "Дата доплаты", field: "final_payment_date", kind: "date" },
  { key: "delivery_address", label: "Адрес доставки", field: "delivery_address", kind: "text" },
  { key: "delivery_paid", label: "Оплата доставки", field: "delivery_paid", kind: "text" },
];

// Доступные для фильтрации системные колонки (как на бэкенде FILTERABLE_COLUMNS).
export const FILTERABLE_SYSTEM = [
  "display_id",
  "title",
  "client_legal_name",
  "manager_name",
  "stage",
  "deadline",
  "risk_level",
  "payment_percent",
  "currency",
  "advance_date",
  "final_payment_date",
  "next_action_date",
];

export const FIELD_TYPES = [
  { value: "TEXT", label: "Текст" },
  { value: "LONG_TEXT", label: "Длинный текст" },
  { value: "NUMBER", label: "Число" },
  { value: "DATE", label: "Дата" },
  { value: "DATETIME", label: "Дата и время" },
  { value: "BOOLEAN", label: "Да/Нет" },
  { value: "SELECT", label: "Выпадающий список" },
  { value: "MULTI_SELECT", label: "Множественный выбор" },
  { value: "PERCENT", label: "Процент" },
  { value: "CURRENCY", label: "Валюта" },
  { value: "URL", label: "Ссылка" },
  { value: "FORMULA", label: "Формула" },
];

export const FIELD_TYPE_LABEL = Object.fromEntries(FIELD_TYPES.map((t) => [t.value, t.label]));

// Операторы фильтров по типу поля (спец. 2.md §15).
export const OPERATORS_BY_KIND = {
  text: ["contains", "equals", "starts_with", "empty", "not_empty"],
  number: ["equals", "not_equals", "gt", "gte", "lt", "lte", "empty", "not_empty"],
  date: ["equals", "before", "after", "before_or_equal", "after_or_equal", "empty", "not_empty"],
  select: ["equals", "not_equals", "empty", "not_empty"],
};

export const OPERATOR_LABEL = {
  contains: "содержит",
  equals: "равно",
  not_equals: "не равно",
  starts_with: "начинается с",
  empty: "пусто",
  not_empty: "не пусто",
  gt: ">",
  gte: ">=",
  lt: "<",
  lte: "<=",
  before: "раньше",
  after: "позже",
  before_or_equal: "раньше или равно",
  after_or_equal: "позже или равно",
};

export function fieldKindForCustom(cf) {
  switch (cf.field_type) {
    case "NUMBER":
    case "PERCENT":
    case "CURRENCY":
      return "number";
    case "DATE":
    case "DATETIME":
      return "date";
    case "SELECT":
    case "MULTI_SELECT":
    case "BOOLEAN":
      return "select";
    default:
      return "text";
  }
}

// Базовый набор видимых колонок по умолчанию (id системных колонок).
export const DEFAULT_VISIBLE = [
  "display_id",
  "title",
  "client_legal_name",
  "manager_name",
  "stage",
  "deadline",
  "payment_percent",
  "currency",
  "risk_level",
  "next_action",
];