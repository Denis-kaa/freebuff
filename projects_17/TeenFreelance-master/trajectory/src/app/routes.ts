/**
 * App: routing placeholder (React Router v6 lands in Phase 2).
 * Routes map 1:1 to the prototype views (../задача.md):
 *   /intro · /dashboard · /practice/:taskId · /portfolio · /parent
 */
export const routes = {
  intro: '/intro',
  dashboard: '/dashboard',
  practice: '/practice/:taskId',
  portfolio: '/portfolio',
  parent: '/parent',
} as const;

export type RouteName = keyof typeof routes;
