const BASE = "/api";

// Активный workspace (RBAC §29): отправляется заголовком X-Workspace-Id
let _activeWorkspaceId = localStorage.getItem("pmos_workspace_id") || "";

export function setActiveWorkspaceId(id) {
  _activeWorkspaceId = id || "";
  if (id) localStorage.setItem("pmos_workspace_id", id);
  else localStorage.removeItem("pmos_workspace_id");
}

export function getActiveWorkspaceId() {
  return _activeWorkspaceId;
}

async function request(path, method = "GET", body) {
  const opts = { method, headers: {} };
  if (_activeWorkspaceId) {
    opts.headers["X-Workspace-Id"] = _activeWorkspaceId;
  }
  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(`${BASE}${path}`, opts);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail || JSON.stringify(data);
    } catch (_) {
      /* ignore */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res.text();
}

export const api = {
  // Projects
  listProjects: (params = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "")
        qs.set(k, Array.isArray(v) ? JSON.stringify(v) : String(v));
    });
    return request(`/projects?${qs.toString()}`);
  },
  createProject: (data) => request("/projects", "POST", data),
  getProject: (id) => request(`/projects/${id}`),
  updateProject: (id, data) => request(`/projects/${id}`, "PATCH", data),
  archiveProject: (id) => request(`/projects/${id}/archive`, "POST"),
  unarchiveProject: (id) => request(`/projects/${id}/unarchive`, "POST"),
  bulkUpdate: (data) => request("/projects/bulk-update", "POST", data),
  putCustomValues: (id, values) =>
    request(`/projects/${id}/custom-values`, "PUT", { values }),
  filterOptions: () => request("/projects/filters/options"),

  // Custom fields
  listCustomFields: (entityType = "PROJECT") =>
    request(`/custom-fields?entity_type=${entityType}`),
  createCustomField: (data) => request("/custom-fields", "POST", data),
  updateCustomField: (id, data) => request(`/custom-fields/${id}`, "PATCH", data),
  deleteCustomField: (id) => request(`/custom-fields/${id}`, "DELETE"),

  // Views
  listViews: (entityType = "projects") => request(`/views?entity_type=${encodeURIComponent(entityType)}`),
  createView: (data) => request("/views", "POST", data),
  updateView: (id, data) => request(`/views/${id}`, "PATCH", data),
  deleteView: (id) => request(`/views/${id}`, "DELETE"),
  getView: (id) => request(`/views/${id}`),
  duplicateView: (id) => request(`/views/${id}/duplicate`, "POST"),
  favoriteView: (id, favorite = true) => request(`/views/${id}/favorite`, "POST", { favorite }),
  setDefaultView: (id) => request(`/views/${id}/default`, "POST"),
  queryView: (id, payload = {}) => request(`/views/${id}/query`, "POST", payload),
  globalSearch: (q) => request(`/search?q=${encodeURIComponent(q)}`),

  // ---- Этап 3: Items / Production / Tasks / Documents / Events ----
  listItems: (projectId) => request(`/project-items?project_id=${projectId}`),
  createItem: (projectId, data) =>
    request("/project-items", "POST", { project_id: projectId, ...data }),
  updateItem: (itemId, data) => request(`/project-items/${itemId}`, "PATCH", data),
  updateItemProduction: (itemId, data) =>
    request(`/project-items/${itemId}/production`, "PATCH", data),
  putItemCustomValues: (itemId, values) =>
    request(`/project-items/${itemId}/custom-values`, "PUT", { values }),

  listTasks: (projectId) => request(`/projects/${projectId}/tasks`),
  createTask: (projectId, data) => request(`/projects/${projectId}/tasks`, "POST", data),
  updateTask: (projectId, taskId, data) =>
    request(`/projects/${projectId}/tasks/${taskId}`, "PATCH", data),
  deleteTask: (projectId, taskId) =>
    request(`/projects/${projectId}/tasks/${taskId}`, "DELETE"),

  listDocuments: (projectId) => request(`/projects/${projectId}/documents`),
  createDocument: (projectId, data) =>
    request(`/projects/${projectId}/documents`, "POST", data),
  updateDocument: (projectId, docId, data) =>
    request(`/projects/${projectId}/documents/${docId}`, "PATCH", data),

  projectSummary: (projectId) => request(`/projects/${projectId}/summary`),
  projectEvents: (projectId) => request(`/projects/${projectId}/events`),
  projectActivity: (projectId) => request(`/projects/${projectId}/activity`),
  projectTimeline: (projectId, itemId) =>
    request(`/projects/${projectId}/timeline?item_id=${itemId}`),

  // ---- Этап 4: Dashboard Engine ----
  listDashboards: () => request("/dashboards"),
  getDashboard: (id) => request(`/dashboards/${id}`),
  createDashboard: (data) => request("/dashboards", "POST", data),
  updateDashboard: (id, data) => request(`/dashboards/${id}`, "PATCH", data),
  deleteDashboard: (id) => request(`/dashboards/${id}`, "DELETE"),
  duplicateDashboard: (id) => request(`/dashboards/${id}/duplicate`, "POST"),
  widgetTypes: () => request("/dashboards/widget-types"),
  dashboardTemplates: () => request("/dashboards/templates"),
  addWidget: (dashId, data) =>
    request(`/dashboards/${dashId}/widgets`, "POST", data),
  updateWidget: (widgetId, data) =>
    request(`/dashboard-widgets/${widgetId}`, "PATCH", data),
  deleteWidget: (widgetId) => request(`/dashboard-widgets/${widgetId}`, "DELETE"),

  // Widget Data API (4.md §24)
  widgetData: {
    calendar: (params = {}) => {
      const qs = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => v && qs.set(k, String(v)));
      return request(`/dashboard-data/calendar?${qs.toString()}`);
    },
    tasks: (params = {}) => {
      const qs = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => v && qs.set(k, String(v)));
      return request(`/dashboard-data/tasks?${qs.toString()}`);
    },
    deadlines: (days) => request(`/dashboard-data/deadlines?days=${days}`),
    risks: (levels, showOverdue, showProduction) =>
      request(
        `/dashboard-data/risks?levels=${encodeURIComponent(levels)}&show_overdue=${showOverdue}&show_production=${showProduction}`
      ),
    production: () => request("/dashboard-data/production"),
    finance: () => request("/dashboard-data/finance"),
    activity: (limit) => request(`/dashboard-data/activity?limit=${limit}`),
    kpi: (metric) => request(`/dashboard-data/kpi?metric=${metric}`),
    projects: (limit, viewId) => request(`/dashboard-data/projects?limit=${limit}${viewId ? `&view_id=${encodeURIComponent(viewId)}` : ""}`),
    aiSummary: () => request("/dashboard-data/ai-summary"),
  },

  // ---- Этап 5: Calendar & Events Engine ----
  calendarEvents: (params = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") qs.set(k, Array.isArray(v) ? v.join(",") : String(v));
    });
    return request(`/calendar/events?${qs.toString()}`);
  },
  calendarToday: (params = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => v && qs.set(k, String(v)));
    return request(`/calendar/today?${qs.toString()}`);
  },
  calendarUpcoming: (params = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") qs.set(k, Array.isArray(v) ? v.join(",") : String(v));
    });
    return request(`/calendar/upcoming?${qs.toString()}`);
  },
  createCalendarEvent: (data) => request("/calendar/events", "POST", data),
  updateCalendarEvent: (id, data) => request(`/calendar/events/${id}`, "PATCH", data),
  deleteCalendarEvent: (id) => request(`/calendar/events/${id}`, "DELETE"),

  // ---- Этап 6: Import / Export ----
  importUpload: async (file, sourceType = "excel") => {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(`${BASE}/imports/${sourceType}`, { method: "POST", body: fd });
    if (!res.ok) {
      let detail = res.statusText;
      try { detail = (await res.json()).detail || detail; } catch (_) { /* ignore */ }
      throw new Error(detail);
    }
    return res.json();
  },
  importSetMapping: (jobId, mapping) =>
    request(`/imports/${jobId}/mapping`, "POST", { mapping }),
  importSaveMapping: (jobId, name, mapping) =>
    request(`/imports/${jobId}/save-mapping`, "POST", { name, mapping }),
  importGetPreview: (jobId) => request(`/imports/${jobId}/preview`),
  importGetErrors: (jobId) => request(`/imports/${jobId}/errors`),
  importConfirm: (jobId, payload = {}) =>
    request(`/imports/${jobId}/confirm`, "POST", payload),
  importCancel: (jobId) => request(`/imports/${jobId}/cancel`, "POST"),
  importHistory: (limit = 30) => request(`/imports/history?limit=${limit}`),
  importTemplates: () => request("/imports/templates?kind=projects_items"),

  exportExcel: (payload) => request("/exports/excel", "POST", payload),
  exportCsv: (payload) => request("/exports/csv", "POST", payload),
  // ---- Этап 8: Notifications & Automation ----
  listAutomationTemplates: () => request("/automation-templates"),
  listAutomations: () => request("/automations"),
  createAutomation: (data) => request("/automations", "POST", data),
  updateAutomation: (id, data) => request(`/automations/${id}`, "PATCH", data),
  deleteAutomation: (id) => request(`/automations/${id}`, "DELETE"),
  enableAutomation: (id) => request(`/automations/${id}/enable`, "POST"),
  disableAutomation: (id) => request(`/automations/${id}/disable`, "POST"),
  testAutomation: (id) => request(`/automations/${id}/test`, "POST"),
  automationRuns: (id) => request(`/automations/${id}/runs`),
  getAutomationRun: (id) => request(`/automation-runs/${id}`),
  eventChain: (id) => request(`/events/${id}/chain`),
  listProjectTags: (id) => request(`/projects/${id}/tags`),
  projectTags: (id) => request(`/projects/${id}/tags`),
  listNotifications: (unreadOnly = false) => request(`/notifications?unread_only=${unreadOnly}`),
  groupedNotifications: () => request("/notifications/grouped"),
  projectTags: (id) => request(`/projects/${id}/tags`),
  markNotificationRead: (id) => request(`/notifications/${id}/read`, "POST"),
  markAllNotificationsRead: () => request("/notifications/read-all", "POST"),
  riskForProject: (id) => request(`/risk/projects/${id}`),
  getNotificationPreferences: () => request("/notification-preferences"),
  setNotificationPreferences: (data) => request("/notification-preferences", "PUT", data),
  ingestEvent: (data) => request("/events", "POST", data),
  runAutomationTick: () => request("/automations/tick", "POST"),
  refreshRisks: () => request("/risk/refresh", "POST"),
  overdueTasks: () => request("/tasks/overdue"),

  exportPresets: () => request("/exports/presets"),
  createExportPreset: (name, config) =>
    request("/exports/presets", "POST", { name, config }),
  deleteExportPreset: (id) => request(`/exports/presets/${id}`, "DELETE"),

  // ---- Этап 9: RBAC / Users / Roles / Permissions ----
  getMe: () => request("/me"),
  updateMe: (data) => request("/me", "PATCH", data),
  getMyPermissions: () => request("/permissions"),
  listAllPermissions: () => request("/permissions/list"),
  listWorkspaces: () => request("/workspaces"),
  createWorkspace: (data) => request("/workspaces", "POST", data),
  getWorkspace: (id) => request(`/workspaces/${id}`),
  updateWorkspace: (id, data) => request(`/workspaces/${id}`, "PATCH", data),
  listMembers: (workspaceId) => request(`/workspaces/${workspaceId}/members`),
  updateMember: (workspaceId, memberId, data) =>
    request(`/workspaces/${workspaceId}/members/${memberId}`, "PATCH", data),
  removeMember: (workspaceId, memberId) =>
    request(`/workspaces/${workspaceId}/members/${memberId}`, "DELETE"),
  inviteMember: (workspaceId, data) =>
    request(`/workspaces/${workspaceId}/members/invite`, "POST", data),
  listInvitations: (workspaceId) =>
    request(`/workspaces/${workspaceId}/invitations`),
  revokeInvitation: (workspaceId, invitationId) =>
    request(`/workspaces/${workspaceId}/invitations/${invitationId}`, "DELETE"),
  listRoles: (workspaceId) => request(`/workspaces/${workspaceId}/roles`),
  listTeams: (workspaceId) => request(`/workspaces/${workspaceId}/teams`),
  createTeam: (workspaceId, data) => request(`/workspaces/${workspaceId}/teams`, "POST", data),
  updateTeam: (workspaceId, teamId, data) => request(`/workspaces/${workspaceId}/teams/${teamId}`, "PATCH", data),
  deleteTeam: (workspaceId, teamId) => request(`/workspaces/${workspaceId}/teams/${teamId}`, "DELETE"),
  addTeamMember: (workspaceId, teamId, memberId) => request(`/workspaces/${workspaceId}/teams/${teamId}/members`, "POST", { member_id: memberId }),
  removeTeamMember: (workspaceId, teamId, memberId) => request(`/workspaces/${workspaceId}/teams/${teamId}/members/${memberId}`, "DELETE"),
  createRole: (workspaceId, data) =>
    request(`/workspaces/${workspaceId}/roles`, "POST", data),
  updateRole: (workspaceId, roleId, data) =>
    request(`/workspaces/${workspaceId}/roles/${roleId}`, "PATCH", data),
  duplicateRole: (workspaceId, roleId) =>
    request(`/workspaces/${workspaceId}/roles/${roleId}/duplicate`, "POST"),
  transferOwnership: (workspaceId, newOwnerMemberId) =>
    request(`/workspaces/${workspaceId}/ownership/transfer`, "POST", { new_owner_member_id: newOwnerMemberId }),
  acceptInvitation: (token) => request("/invitations/accept", "POST", { token }),
};