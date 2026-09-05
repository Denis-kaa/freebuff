import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Хук данных виджета (4.md §22): Widget -> Data Hook -> API -> Service -> DB.
 * Каждый виджет имеет собственный loading/error; один сломанный виджет не
 * ломает весь Dashboard (§28-29).
 *
 * fetcher — функция, возвращающая Promise<data> (вызов api.widgetData.*).
 * deps — значения, при изменении которых данные перезагружаются (например
 * конфигурация виджета).
 */
export function useWidgetData(fetcher, deps = []) {
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const [state, setState] = useState({ data: null, loading: true, error: null });
  const [tick, setTick] = useState(0);

  const refresh = useCallback(() => {
    setTick((t) => t + 1);
  }, []);

  const depsKey = JSON.stringify(deps);

  // Глобальный рефреш Dashboard (4.md §30) + архитектура совместима с realtime
  // (WebSocket/SSE в будущем заменит событие — компоненты менять не придётся, §31).
  useEffect(() => {
    const onRefresh = () => setTick((t) => t + 1);
    window.addEventListener("pmos-widget-refresh", onRefresh);
    return () => window.removeEventListener("pmos-widget-refresh", onRefresh);
  }, []);

  useEffect(() => {
    let alive = true;
    setState((s) => ({ ...s, loading: true, error: null }));
    Promise.resolve()
      .then(() => fetcherRef.current())
      .then((data) => alive && setState({ data, loading: false, error: null }))
      .catch((err) =>
        alive && setState((s) => ({ ...s, loading: false, error: err?.message || "Ошибка загрузки" }))
      );
    return () => {
      alive = false;
    };
  }, [depsKey, tick]); // eslint-disable-line react-hooks/exhaustive-deps

  return { ...state, refresh };
}