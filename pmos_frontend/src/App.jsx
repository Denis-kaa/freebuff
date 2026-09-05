import React, { useCallback, useEffect, useState } from "react";
import { Calendar, LayoutDashboard, FolderKanban, RefreshCw } from "lucide-react";
import { ToastProvider, useToast } from "./components/ui.jsx";
import GlobalSearch from "./components/GlobalSearch.jsx";
import NotificationCenter from "./components/NotificationCenter.jsx";
import ProjectsView from "./views/ProjectsView.jsx";
import ProjectDetail from "./views/ProjectDetail.jsx";
import DashboardView from "./dashboard/DashboardView.jsx";
import CalendarPage from "./calendar/CalendarPage.jsx";
import AutomationsView from "./views/AutomationsView.jsx";
import NotificationSettingsView from "./views/NotificationSettingsView.jsx";
import AutomationHistoryView from "./views/AutomationHistoryView.jsx";
import TeamView from "./views/TeamView.jsx";
import RolesView from "./views/RolesView.jsx";
import ProfileView from "./views/ProfileView.jsx";
import WorkspaceSwitcher from "./components/WorkspaceSwitcher.jsx";
import { api } from "./api.js";
import { AuthProvider, useAuth } from "./rbac/AuthContext.jsx";

function usePath() {
  const [path, setPath] = useState(window.location.pathname);
  useEffect(() => {
    const onPop = () => setPath(window.location.pathname);
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);
  const nav = useCallback((p) => {
    window.history.pushState({}, "", p);
    setPath(p);
  }, []);
  return [path, nav];
}

function Shell() {
  const [path, nav] = usePath();
  const toast = useToast();
  const { can } = useAuth();
  const [drawerProject, setDrawerProject] = useState(null);
  const [drawerFields, setDrawerFields] = useState({ customFields: [], itemCustomFields: [] });

  const isProjects = path.startsWith("/projects");
  const isCalendar = path.startsWith("/calendar");
  const isAutomations = path.startsWith("/automations");
  const isNotificationSettings = path.startsWith("/notification-settings");
  const isAutomationHistory = path.startsWith("/automation-history");
  const isTeam = path.startsWith("/team");
  const isRoles = path.startsWith("/roles");
  const isProfile = path.startsWith("/profile");

  const openProject = useCallback(async (projectId, displayId) => {
    try {
      const [project, customFields, itemCustomFields] = await Promise.all([
        api.getProject(projectId),
        api.listCustomFields("PROJECT"),
        api.listCustomFields("PROJECT_ITEM"),
      ]);
      setDrawerFields({ customFields, itemCustomFields });
      setDrawerProject(project);
    } catch (e) {
      toast(`${displayId || projectId}: ${e.message}`, "error");
    }
  }, [toast]);

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-[1400px] items-center gap-4 px-4 py-2.5">
          <div className="flex items-center gap-2 text-base font-bold">
            <span className="rounded-lg bg-indigo-600 px-1.5 py-0.5 text-sm text-white">PM</span>
            <span className="text-slate-700">OS</span>
            <span className="hidden text-xs font-normal text-slate-400 sm:inline">Configurable Workspace</span>
          </div>
          <nav className="flex items-center gap-1">
            <button
              onClick={() => nav("/")}
              className={`btn !px-2.5 ${!isProjects && !isCalendar ? "btn-indigo" : "btn-ghost"}`}
            >
              <LayoutDashboard className="h-4 w-4" /> Дашборды
            </button>
            <button
              onClick={() => nav("/calendar")}
              className={`btn !px-2.5 ${isCalendar ? "btn-indigo" : "btn-ghost"}`}
            >
              <Calendar className="h-4 w-4" /> Календарь
            </button>
            <button
              onClick={() => nav("/projects")}
              className={`btn !px-2.5 ${isProjects ? "btn-indigo" : "btn-ghost"}`}
            >
              <FolderKanban className="h-4 w-4" /> Проекты
            </button>
            {can("automation.read") && (
              <button onClick={() => nav("/automations")} className={`btn !px-2.5 ${isAutomations ? "btn-indigo" : "btn-ghost"}`}>⚙ Автоматизации</button>
            )}
            {can("member.read") && (
              <button onClick={() => nav("/notification-settings")} className={`btn !px-2.5 ${isNotificationSettings ? "btn-indigo" : "btn-ghost"}`}>🔔 Настройки</button>
            )}
            {can("automation.read") && (
              <button onClick={() => nav("/automation-history")} className={`btn !px-2.5 ${isAutomationHistory ? "btn-indigo" : "btn-ghost"}`}>История</button>
            )}
            {can("member.read") && (
              <button onClick={() => nav("/team")} className={`btn !px-2.5 ${isTeam ? "btn-indigo" : "btn-ghost"}`}>Команда</button>
            )}
            {can("role.manage") && (
              <button onClick={() => nav("/roles")} className={`btn !px-2.5 ${isRoles ? "btn-indigo" : "btn-ghost"}`}>Роли</button>
            )}
            <button onClick={() => nav("/profile")} className={`btn !px-2.5 ${isProfile ? "btn-indigo" : "btn-ghost"}`}>Профиль</button>
          </nav>
          <WorkspaceSwitcher />
          <GlobalSearch onProjectClick={openProject} />
          <NotificationCenter />
          <button
            onClick={() => window.dispatchEvent(new CustomEvent("pmos-widget-refresh"))}
            className="btn btn-ghost ml-auto !px-2"
            title="Обновить дашборд"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </header>

      <main>
        {isProjects ? (
          <ProjectsView />
        ) : isAutomations ? (
          <AutomationsView />
        ) : isNotificationSettings ? (
          <NotificationSettingsView />
        ) : isAutomationHistory ? (
          <AutomationHistoryView />
        ) : isTeam ? (
          <TeamView />
        ) : isRoles ? (
          <RolesView />
        ) : isProfile ? (
          <ProfileView />
        ) : isCalendar ? (
          <CalendarPage onProjectClick={openProject} />
        ) : (
          <DashboardView
            onProjectClick={openProject}
            onOpenCalendar={(date, view) => nav(`/calendar?date=${date}&view=${view || "month"}`)}
          />
        )}
      </main>

      <ProjectDetail
        project={drawerProject}
        customFields={drawerFields.customFields}
        itemCustomFields={drawerFields.itemCustomFields}
        onClose={() => setDrawerProject(null)}
        onSaved={() => setDrawerProject(null)}
      />
    </div>
  );
}

export default function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <Shell />
      </AuthProvider>
    </ToastProvider>
  );
}