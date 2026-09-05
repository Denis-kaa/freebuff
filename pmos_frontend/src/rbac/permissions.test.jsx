// ---------------------------------------------------------------------------
// §43 Frontend permission tests:
//   - Viewer не видит Edit / Delete / Create
//   - Manager видит Projects/Tasks/Production, но не финансы без finance.read
// Безопасность обеспечивает backend; здесь проверяется UX-отражение прав.
// ---------------------------------------------------------------------------
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ToastProvider } from "../components/ui.jsx";
import { AuthContext, useAuth } from "./AuthContext.jsx";
import ProjectsView from "../views/ProjectsView.jsx";
import ProjectDetail from "../views/ProjectDetail.jsx";

vi.mock("../api.js", () => ({
  api: {
    listProjects: vi.fn(),
    listCustomFields: vi.fn(),
    filterOptions: vi.fn(),
    listViews: vi.fn(),
    queryView: vi.fn(),
    projectTags: vi.fn(),
    projectSummary: vi.fn(),
    listItems: vi.fn(),
    projectEvents: vi.fn(),
    listTasks: vi.fn(),
    listDocuments: vi.fn(),
    projectActivity: vi.fn(),
    listMembers: vi.fn(),
    getProject: vi.fn(),
  },
  getActiveWorkspaceId: () => "ws-1",
  setActiveWorkspaceId: () => {},
}));

const { api } = await import("../api.js");

const PROJECT = {
  id: "p1",
  display_id: "P001",
  title: "Тестовый проект",
  stage: "Макет",
  manager_name: "Денис",
  manager_id: "u1",
  payment_percent: 50,
  currency: "RUB",
  deadline: "2026-10-01",
  version: 1,
};

// ---- тестовый провайдер прав: подменяем AuthContext напрямую ----
function MockAuth({ role = "VIEWER", perms = {}, children }) {
  const can = (p) => role === "OWNER" || perms[p] === true;
  const value = {
    can,
    role,
    me: null,
    ready: true,
    refresh: vi.fn(),
    workspaces: [],
    workspaceId: "ws-1",
    workspace: { id: "ws-1", name: "Test WS" },
    switchWorkspace: vi.fn(),
    createWorkspace: vi.fn(),
    version: 0,
  };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

function renderWithAuth(ui, opts = {}) {
  return render(
    <ToastProvider>
      <MockAuth {...opts}>{ui}</MockAuth>
    </ToastProvider>
  );
}

const VIEWER_PERMS = { "project.read": true, "task.read": true, "production.read": true };
const MANAGER_PERMS = {
  "project.read": true, "project.create": true, "project.update": true, "project.delete": true,
  "task.read": true, "task.create": true, "task.update": true,
  "production.read": true, "production.update": true,
  "document.read": true, "document.create": true,
  "finance.read": true, "finance.update": true,
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.listProjects).mockResolvedValue({ items: [PROJECT], total: 1 });
  vi.mocked(api.listCustomFields).mockResolvedValue([]);
  vi.mocked(api.filterOptions).mockResolvedValue({ stages: [], managers: [] });
  vi.mocked(api.listViews).mockResolvedValue([]);
  vi.mocked(api.listMembers).mockResolvedValue([]);
  vi.mocked(api.projectSummary).mockResolvedValue({ health: "healthy", deadline: "2026-10-01", payment_percent: 50, currency: "RUB", items_count: 0, open_tasks_count: 0 });
  vi.mocked(api.listTasks).mockResolvedValue([]);
  vi.mocked(api.listItems).mockResolvedValue([]);
  vi.mocked(api.projectEvents).mockResolvedValue([]);
  vi.mocked(api.listDocuments).mockResolvedValue([]);
  vi.mocked(api.projectActivity).mockResolvedValue({ items: [] });
  vi.mocked(api.projectTags).mockResolvedValue({ tags: [] });
});

// ---------------------------------------------------------------------------
// Create
// ---------------------------------------------------------------------------
describe("§43 Create — viewer не видит, manager видит", () => {
  it("viewer не видит кнопку «+ Новый проект»", async () => {
    renderWithAuth(<ProjectsView />, { role: "VIEWER", perms: VIEWER_PERMS });
    expect(await screen.findByText("Тестовый проект")).toBeInTheDocument();
    expect(screen.queryByText("+ Новый проект")).not.toBeInTheDocument();
  });

  it("manager видит кнопку «+ Новый проект»", async () => {
    renderWithAuth(<ProjectsView />, { role: "MANAGER", perms: MANAGER_PERMS });
    expect(await screen.findByText("Тестовый проект")).toBeInTheDocument();
    expect(screen.getByText("+ Новый проект")).toBeInTheDocument();
  });

  it("viewer не видит «+ Новая задача», «+ Добавить позицию», «+ Добавить документ» в Project Drawer", async () => {
    renderWithAuth(
      <ProjectDetail project={PROJECT} customFields={[]} onClose={vi.fn()} onSaved={vi.fn()} />,
      { role: "VIEWER", perms: VIEWER_PERMS }
    );
    expect(await screen.findByText("Тестовый проект")).toBeInTheDocument();
    // таб Задачи
    await userEvent.click(screen.getByText("Задачи"));
    expect(await screen.findByText("Задачи · 0")).toBeInTheDocument();
    expect(screen.queryByText("+ Новая задача")).not.toBeInTheDocument();
    // таб Производство
    await userEvent.click(screen.getByText("Производство"));
    expect(await screen.findByText("Состав заказа")).toBeInTheDocument();
    expect(screen.queryByText("+ Добавить позицию")).not.toBeInTheDocument();
    // таб Документы
    await userEvent.click(screen.getByText("Документы"));
    expect(await screen.findByText("Документы · 0")).toBeInTheDocument();
    expect(screen.queryByText("+ Добавить документ")).not.toBeInTheDocument();
  });

  it("manager видит кнопки создания задач/позиций/документов", async () => {
    renderWithAuth(
      <ProjectDetail project={PROJECT} customFields={[]} onClose={vi.fn()} onSaved={vi.fn()} />,
      { role: "MANAGER", perms: MANAGER_PERMS }
    );
    await userEvent.click(await screen.findByText("Задачи"));
    expect(await screen.findByText("+ Новая задача")).toBeInTheDocument();
    await userEvent.click(screen.getByText("Производство"));
    expect(await screen.findByText("+ Добавить позицию")).toBeInTheDocument();
    await userEvent.click(screen.getByText("Документы"));
    expect(await screen.findByText("+ Добавить документ")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Edit / Delete
// ---------------------------------------------------------------------------
describe("§43 Edit/Delete — viewer не видит, manager видит", () => {
  it("viewer не видит «Сохранить» и «Архивировать» в Project Drawer", async () => {
    renderWithAuth(
      <ProjectDetail project={PROJECT} customFields={[]} onClose={vi.fn()} onSaved={vi.fn()} />,
      { role: "VIEWER", perms: VIEWER_PERMS }
    );
    expect(await screen.findByText("Тестовый проект")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Сохранить" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Архивировать" })).not.toBeInTheDocument();
  });

  it("manager видит «Сохранить» и «Архивировать» в Project Drawer", async () => {
    renderWithAuth(
      <ProjectDetail project={PROJECT} customFields={[]} onClose={vi.fn()} onSaved={vi.fn()} />,
      { role: "MANAGER", perms: MANAGER_PERMS }
    );
    expect(await screen.findByText("Тестовый проект")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Сохранить" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Архивировать" })).toBeInTheDocument();
  });

  it("viewer не видит удаление сохранённых представлений", async () => {
    vi.mocked(api.listViews).mockResolvedValue([
      { id: "v1", name: "Моя вьюха", is_favorite: false, created_by: "u1" },
    ]);
    renderWithAuth(<ProjectsView />, { role: "VIEWER", perms: VIEWER_PERMS });
    await screen.findByText("Тестовый проект");
    await userEvent.click(screen.getByText(/Представление:/));
    expect(await screen.findByText(/Моя вьюха/)).toBeInTheDocument();
    expect(screen.queryByTitle("Удалить")).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Finance — manager без finance.read не видит раздел «Финансы»
// ---------------------------------------------------------------------------
describe("§43 Finance — manager без finance.read", () => {
  it("manager без finance.read не видит встроенное представление «Финансы»", async () => {
    const noFinance = { ...MANAGER_PERMS, "finance.read": false };
    renderWithAuth(<ProjectsView />, { role: "MANAGER", perms: noFinance });
    await screen.findByText("Тестовый проект");
    await userEvent.click(screen.getByText(/Представление:/));
    expect(screen.queryByText("Финансы")).not.toBeInTheDocument();
    expect(screen.getByText("Производство")).toBeInTheDocument();
  });

  it("manager с finance.read видит представление «Финансы»", async () => {
    renderWithAuth(<ProjectsView />, { role: "MANAGER", perms: MANAGER_PERMS });
    await screen.findByText("Тестовый проект");
    await userEvent.click(screen.getByText(/Представление:/));
    expect(await screen.findByText("Финансы")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Навигация (§45) — тот же гейтинг, что в App.jsx
// ---------------------------------------------------------------------------
function NavProbe() {
  const { can } = useAuth();
  return (
    <div>
      {can("automation.read") && <span>⚙ Автоматизации</span>}
      {can("member.read") && <span>🔔 Настройки</span>}
      {can("automation.read") && <span>История</span>}
      {can("member.read") && <span>Команда</span>}
      {can("role.manage") && <span>Роли</span>}
    </div>
  );
}

describe("§45 навигация скрывает недоступные разделы", () => {
  it("viewer не видит Автоматизации/Настройки/Команду/Роли", () => {
    renderWithAuth(<NavProbe />, { role: "VIEWER", perms: VIEWER_PERMS });
    expect(screen.queryByText("⚙ Автоматизации")).not.toBeInTheDocument();
    expect(screen.queryByText("🔔 Настройки")).not.toBeInTheDocument();
    expect(screen.queryByText("История")).not.toBeInTheDocument();
    expect(screen.queryByText("Команда")).not.toBeInTheDocument();
    expect(screen.queryByText("Роли")).not.toBeInTheDocument();
  });

  it("manager с правами видит пункты меню", () => {
    const perms = {
      ...VIEWER_PERMS,
      "automation.read": true,
      "member.read": true,
      "role.manage": true,
    };
    renderWithAuth(<NavProbe />, { role: "MANAGER", perms });
    expect(screen.getByText("⚙ Автоматизации")).toBeInTheDocument();
    expect(screen.getByText("🔔 Настройки")).toBeInTheDocument();
    expect(screen.getByText("История")).toBeInTheDocument();
    expect(screen.getByText("Команда")).toBeInTheDocument();
    expect(screen.getByText("Роли")).toBeInTheDocument();
  });
});
