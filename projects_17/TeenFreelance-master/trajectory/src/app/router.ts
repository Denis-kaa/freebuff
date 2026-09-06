/**
 * Hash router — mirrors the prototype's view model (#intro/#dashboard/#parent).
 * React Router v6 replaces this if the app moves to real multi-page routing.
 */
import { useEffect, useState } from 'react';

export type ViewName = 'intro' | 'dashboard' | 'parent' | 'team' | 'review';

const VALID: readonly ViewName[] = ['intro', 'dashboard', 'parent', 'team', 'review'];

export function parseHash(): ViewName {
  const h = window.location.hash.replace('#', '') as ViewName;
  return VALID.includes(h) ? h : 'intro';
}

export function useHashRoute(): [ViewName, (v: ViewName) => void] {
  const [view, setView] = useState<ViewName>(parseHash);

  useEffect(() => {
    const onHash = () => setView(parseHash());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  const navigate = (v: ViewName) => {
    window.location.hash = v;
    setView(v);
  };

  return [view, navigate];
}

export function navigate(v: ViewName): void {
  window.location.hash = v;
}
