import { useCallback, useEffect, useState } from "react";
import { api, getActiveWorkspaceId } from "../api.js";

/**
 * Загружает участников активного workspace (RBAC §39) для выбора
 * менеджера проекта / исполнителя задачи.
 */
export function useMembers() {
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    const wsId = getActiveWorkspaceId();
    if (!wsId) return;
    setLoading(true);
    try {
      const rows = await api.listMembers(wsId);
      setMembers(rows || []);
    } catch (_) {
      // member.read может быть недоступен — просто оставляем пустой список
      setMembers([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return { members, loading, reload: load };
}

/** Опции для <select>: id → display_name/email */
export function memberOptions(members) {
  return members
    .filter((m) => m.status === "ACTIVE")
    .map((m) => ({
      id: m.user_id,
      label: m.display_name || m.email || m.user_id,
    }));
}
