import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api.js";

/**
 * Общий хук календаря (5.md §22, §28): Widget и страница /calendar используют
 * один и тот же Calendar Engine через GET /calendar/events (фильтры на бэкенде).
 */
export function useCalendar(frm, to, filters = {}, deps = []) {
  const cfgRef = useRef(null);
  const [state, setState] = useState({ items: [], loading: true, error: null });

  const refresh = useCallback(() => {
    cfgRef.current = {};
    setState((s) => ({ ...s, loading: true, error: null }));
    api
      .calendarEvents({ from: frm, to, ...filters })
      .then((res) => setState({ items: res.items || [], loading: false, error: null }))
      .catch((e) => setState((s) => ({ ...s, loading: false, error: e.message || "Ошибка" })));
  }, [frm, to, JSON.stringify(filters)]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    const onRefresh = () => refresh();
    window.addEventListener("pmos-widget-refresh", onRefresh);
    return () => window.removeEventListener("pmos-widget-refresh", onRefresh);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { ...state, refresh };
}

/** Группирует события по дате: { 'YYYY-MM-DD': [...events] } */
export function groupByDate(items) {
  const map = {};
  items.forEach((e) => {
    const day = (e.start_at || "").slice(0, 10);
    (map[day] = map[day] || []).push(e);
  });
  return map;
}

export const WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

export function toISO(d) {
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${mm}-${dd}`;
}

export function monthRange(viewDate) {
  const y = viewDate.getFullYear();
  const m = viewDate.getMonth();
  const from = new Date(y, m, 1);
  const firstDow = (from.getDay() + 6) % 7;
  return { y, m, from: toISO(from), gridStart: new Date(y, m, 1 - firstDow) };
}