import React, { createContext, useContext, useEffect, useState } from "react";
import { api, getActiveWorkspaceId, setActiveWorkspaceId } from "../api.js";

export const AuthContext = createContext({
  can: () => true,
  role: "ADMIN",
  me: null,
  ready: false,
  refresh: async () => {},
  workspaces: [],
  workspaceId: "",
  workspace: null,
  switchWorkspace: async () => {},
  createWorkspace: async () => {},
});

export function AuthProvider({ children }) {
  const [me, setMe] = useState(null);
  const [perms, setPerms] = useState({});
  const [role, setRole] = useState("ADMIN");
  const [ready, setReady] = useState(false);
  const [workspaces, setWorkspaces] = useState([]);
  const [workspaceId, setWorkspaceIdState] = useState(getActiveWorkspaceId() || "");
  const [version, setVersion] = useState(0); // для перезагрузки данных при смене workspace

  const refresh = async () => {
    try {
      const [meRes, permRes, wsRes] = await Promise.all([
        api.getMe(),
        api.getMyPermissions(),
        api.listWorkspaces(),
      ]);
      setMe(meRes);
      setPerms(permRes.permissions || {});
      setRole(permRes.role || "ADMIN");
      setWorkspaces(wsRes || []);
      // Если активный workspace не задан или не в списке — берём первый
      const active = getActiveWorkspaceId();
      const known = (wsRes || []).some((w) => w.id === active);
      if (!known && wsRes && wsRes.length > 0) {
        setActiveWorkspaceId(wsRes[0].id);
        setWorkspaceIdState(wsRes[0].id);
      }
    } catch (_) {
      setRole("ADMIN");
      setPerms({});
    } finally {
      setReady(true);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const switchWorkspace = async (id) => {
    setActiveWorkspaceId(id);
    setWorkspaceIdState(id);
    setVersion((v) => v + 1);
    // permissions и me могут отличаться в другом workspace — перечитываем
    await refresh();
  };

  const createWorkspace = async (data) => {
    const created = await api.createWorkspace(data);
    // создатель автоматически OWNER (RBAC §29-30)
    await switchWorkspace(created.id);
    return created;
  };

  const can = (perm) => role === "OWNER" || perms[perm] === true;
  const workspace = workspaces.find((w) => w.id === workspaceId) || null;

  return (
    <AuthContext.Provider
      value={{ can, role, me, ready, refresh, workspaces, workspaceId, workspace, switchWorkspace, createWorkspace, version }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
