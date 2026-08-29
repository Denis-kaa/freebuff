// src/store/roomStore.ts — Web-adapted Zustand store (localStorage persistence).
// Replaces @react-native-async-storage/async-storage with localStorage.

import { create ***REMOVED*** from "zustand";
import { persist, createJSONStorage, type StateStorage ***REMOVED*** from "zustand/middleware";
import type { FurnitureObject, Project, Room ***REMOVED*** from "../types/domain";

/* ─── Storage adapter (localStorage for web) ─────────────────────────── */

const storage: StateStorage = {
  getItem: async (key) => localStorage.getItem(key) ?? null,
  setItem: async (key, value) => { localStorage.setItem(key, value); ***REMOVED***,
  removeItem: async (key) => { localStorage.removeItem(key); ***REMOVED***,
***REMOVED***;

/* ─── Undo/Redo (push-AFTER: history[idx***REMOVED*** = текущее состояние) ─────────── */

const HISTORY_LIMIT = 50;

function pushSnapshot(
  history: Project[***REMOVED***,
  historyIndex: number,
  newProject: Project,
): { history: Project[***REMOVED***; historyIndex: number ***REMOVED*** {
  // Обрезаем future после отката (undo → новое изменение)
  const next = history.slice(0, historyIndex + 1);
  next.push(JSON.parse(JSON.stringify(newProject)));
  if (next.length > HISTORY_LIMIT) next.shift();
  return { history: next, historyIndex: next.length - 1 ***REMOVED***;
***REMOVED***

interface RoomState {
  project: Project | null;
  hasHydrated: boolean;
  history: Project[***REMOVED***;
  historyIndex: number;
  setProject: (p: Project | null) => void;
  setRoom: (r: Room) => void;
  setStyle: (style_id: string) => void;
  addObject: (o: FurnitureObject) => void;
  moveObject: (id: string, x: number, y: number) => void;
  rotateObject: (id: string, rotation_deg: number) => void;
  deleteObject: (id: string) => void;
  clearProject: () => void;
  undo: () => void;
  redo: () => void;
  canUndo: () => boolean;
  canRedo: () => boolean;
  _setHydrated: (v: boolean) => void;
***REMOVED***

const genId = (): string =>
  `${Date.now().toString(36)***REMOVED***-${Math.random().toString(36).slice(2, 8)***REMOVED***`;

export const useRoomStore = create<RoomState>()(
  persist(
    (set, get) => {
      let lastMovePushTime = 0; // дебаунс снапшотов при drag (300ms)
      return {
      project: null,
      hasHydrated: false,
      history: [***REMOVED***,
      historyIndex: -1,

      setProject: (p) =>
        set({
          project: p,
          history: p ? [JSON.parse(JSON.stringify(p))***REMOVED*** : [***REMOVED***,
          historyIndex: p ? 0 : -1,
        ***REMOVED***),
      setRoom: (r) =>
        set((s) => {
          if (!s.project) return s;
          const newProject = { ...s.project, room: r, updated_at: new Date().toISOString() ***REMOVED***;
          const h = pushSnapshot(s.history, s.historyIndex, newProject);
          return { ...h, project: newProject ***REMOVED***;
        ***REMOVED***),
      setStyle: (style_id) =>
        set((s) => {
          if (!s.project) return s;
          const newProject = { ...s.project, style_id, updated_at: new Date().toISOString() ***REMOVED***;
          const h = pushSnapshot(s.history, s.historyIndex, newProject);
          return { ...h, project: newProject ***REMOVED***;
        ***REMOVED***),

      addObject: (o) =>
        set((s) => {
          if (!s.project) return s;
          const newProject = {
            ...s.project,
            objects: [...s.project.objects, o***REMOVED***,
            updated_at: new Date().toISOString(),
          ***REMOVED***;
          const h = pushSnapshot(s.history, s.historyIndex, newProject);
          return { ...h, project: newProject ***REMOVED***;
        ***REMOVED***),
      moveObject: (id, x, y) =>
        set((s) => {
          if (!s.project) return s;
          const newProject = {
            ...s.project,
            objects: s.project.objects.map((o) =>
              o.id === id ? { ...o, position_m: [x, y***REMOVED*** ***REMOVED*** : o,
            ),
            updated_at: new Date().toISOString(),
          ***REMOVED***;
          // Дебаунс: раз в 300ms — новый снапшот; между пушами — заменяем хвост
          // истории in-place (только на frontier), чтобы инвариант history[last***REMOVED***==project
          // сохранялся. После undo (idx < len-1) — всегда pushSnapshot (обрезает future).
          const now = Date.now();
          if (
            now - lastMovePushTime > 300 ||
            s.history.length === 0 ||
            s.historyIndex < s.history.length - 1
          ) {
            lastMovePushTime = now;
            const h = pushSnapshot(s.history, s.historyIndex, newProject);
            return { ...h, project: newProject ***REMOVED***;
          ***REMOVED***
          return {
            history: [...s.history.slice(0, -1), JSON.parse(JSON.stringify(newProject))***REMOVED***,
            historyIndex: s.historyIndex,
            project: newProject,
          ***REMOVED***;
        ***REMOVED***),
      rotateObject: (id, rotation_deg) =>
        set((s) => {
          if (!s.project) return s;
          const newProject = {
            ...s.project,
            objects: s.project.objects.map((o) =>
              o.id === id ? { ...o, rotation_deg ***REMOVED*** : o,
            ),
            updated_at: new Date().toISOString(),
          ***REMOVED***;
          const h = pushSnapshot(s.history, s.historyIndex, newProject);
          return { ...h, project: newProject ***REMOVED***;
        ***REMOVED***),
      deleteObject: (id) =>
        set((s) => {
          if (!s.project) return s;
          const newProject = {
            ...s.project,
            objects: s.project.objects.filter((o) => o.id !== id),
            updated_at: new Date().toISOString(),
          ***REMOVED***;
          const h = pushSnapshot(s.history, s.historyIndex, newProject);
          return { ...h, project: newProject ***REMOVED***;
        ***REMOVED***),

      undo: () =>
        set((s) => {
          if (s.historyIndex <= 0) return s;
          const idx = s.historyIndex - 1;
          return { historyIndex: idx, project: JSON.parse(JSON.stringify(s.history[idx***REMOVED***)) ***REMOVED***;
        ***REMOVED***),

      redo: () =>
        set((s) => {
          if (s.historyIndex >= s.history.length - 1) return s;
          const idx = s.historyIndex + 1;
          return { historyIndex: idx, project: JSON.parse(JSON.stringify(s.history[idx***REMOVED***)) ***REMOVED***;
        ***REMOVED***),

      canUndo: () => get().historyIndex > 0,
      canRedo: () => get().historyIndex < get().history.length - 1,

      clearProject: () => set({ project: null, history: [***REMOVED***, historyIndex: -1 ***REMOVED***),
      _setHydrated: (v) => set({ hasHydrated: v ***REMOVED***),
      ***REMOVED***;
    ***REMOVED***,
    {
      name: "interior-planner-storage",
      version: 2,
      storage: createJSONStorage(() => storage),
      partialize: (s) => ({
        project: s.project,
        history: s.history,
        historyIndex: s.historyIndex,
      ***REMOVED***),
      // Миграция v1→v2: сеем историю из сохранённого project, чтобы не потерять данные
      migrate: (persisted: unknown, version: number) => {
        const p = persisted as Partial<RoomState>;
        if (version < 2 && p.project) {
          return {
            ...p,
            history: [JSON.parse(JSON.stringify(p.project))***REMOVED***,
            historyIndex: 0,
          ***REMOVED***;
        ***REMOVED***
        return persisted as Partial<RoomState>;
      ***REMOVED***,
      onRehydrateStorage: () => (state) => {
        if (state) state._setHydrated(true);
      ***REMOVED***,
    ***REMOVED***,
  ),
);

/* ─── Helpers ──────────────────────────────────────────────────────────── */

export const makeProject = (name: string, room: Room, style_id: string): Project => {
  const now = new Date().toISOString();
  return {
    id: genId(),
    name,
    created_at: now,
    updated_at: now,
    room,
    objects: [***REMOVED***,
    style_id,
  ***REMOVED***;
***REMOVED***;

export const makeObject = (
  catalog_id: string,
  size_m: [number, number***REMOVED***,
  position_m: [number, number***REMOVED***,
  z_index: number,
): FurnitureObject => ({
  id: genId(),
  catalog_id,
  position_m,
  size_m,
  rotation_deg: 0,
  z_index,
***REMOVED***);
