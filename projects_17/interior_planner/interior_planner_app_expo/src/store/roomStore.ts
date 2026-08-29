// src/store/roomStore.ts — Zustand store for room state, AsyncStorage persistence.
// Project-local. NO interaction with Freebuff core (separate concern).

import { create ***REMOVED*** from "zustand";
import { persist, createJSONStorage, type StateStorage ***REMOVED*** from "zustand/middleware";
import AsyncStorage from "@react-native-async-storage/async-storage";
import type { FurnitureObject, Project, Room ***REMOVED*** from "../types/domain";

/* ─── Storage adapter ──────────────────────────────────────────────────── */
// AsyncStorage adapter required by Zustand persist middleware.
// AsyncStorage has async API; StateStorage expects sync — we approximate via
// getItem/setItem/removeItem (React Native's AsyncStorage is fire-and-forget
// but returns a Promise that we resolve eagerly; on first render value can
// be null).

const storage: StateStorage = {
  getItem: async (key) => (await AsyncStorage.getItem(key)) ?? null,
  setItem: async (key, value) => { await AsyncStorage.setItem(key, value); ***REMOVED***,
  removeItem: async (key) => { await AsyncStorage.removeItem(key); ***REMOVED***,
***REMOVED***;

/* ─── State + Actions ──────────────────────────────────────────────────── */

interface RoomState {
  project: Project | null;
  hasHydrated: boolean;
  setProject: (p: Project | null) => void;
  setRoom: (r: Room) => void;
  setStyle: (style_id: string) => void;
  addObject: (o: FurnitureObject) => void;
  moveObject: (id: string, x: number, y: number) => void;
  rotateObject: (id: string, rotation_deg: number) => void;
  deleteObject: (id: string) => void;
  clearProject: () => void;
  _setHydrated: (v: boolean) => void;
***REMOVED***

const genId = (): string =>
  `${Date.now().toString(36)***REMOVED***-${Math.random().toString(36).slice(2, 8)***REMOVED***`;

export const useRoomStore = create<RoomState>()(
  persist(
    (set) => ({
      project: null,
      hasHydrated: false,

      setProject: (p) => set({ project: p ***REMOVED***),
      setRoom: (r) =>
        set((s) =>
          s.project
            ? { project: { ...s.project, room: r, updated_at: new Date().toISOString() ***REMOVED*** ***REMOVED***
            : s,
        ),
      setStyle: (style_id) =>
        set((s) =>
          s.project
            ? { project: { ...s.project, style_id, updated_at: new Date().toISOString() ***REMOVED*** ***REMOVED***
            : s,
        ),

      addObject: (o) =>
        set((s) =>
          s.project
            ? {
                project: {
                  ...s.project,
                  objects: [...s.project.objects, o***REMOVED***,
                  updated_at: new Date().toISOString(),
                ***REMOVED***,
              ***REMOVED***
            : s,
        ),
      moveObject: (id, x, y) =>
        set((s) =>
          s.project
            ? {
                project: {
                  ...s.project,
                  objects: s.project.objects.map((o) =>
                    o.id === id ? { ...o, position_m: [x, y***REMOVED*** ***REMOVED*** : o,
                  ),
                  updated_at: new Date().toISOString(),
                ***REMOVED***,
              ***REMOVED***
            : s,
        ),
      rotateObject: (id, rotation_deg) =>
        set((s) =>
          s.project
            ? {
                project: {
                  ...s.project,
                  objects: s.project.objects.map((o) =>
                    o.id === id ? { ...o, rotation_deg ***REMOVED*** : o,
                  ),
                  updated_at: new Date().toISOString(),
                ***REMOVED***,
              ***REMOVED***
            : s,
        ),
      deleteObject: (id) =>
        set((s) =>
          s.project
            ? {
                project: {
                  ...s.project,
                  objects: s.project.objects.filter((o) => o.id !== id),
                  updated_at: new Date().toISOString(),
                ***REMOVED***,
              ***REMOVED***
            : s,
        ),

      clearProject: () => set({ project: null ***REMOVED***),
      _setHydrated: (v) => set({ hasHydrated: v ***REMOVED***),
    ***REMOVED***),
    {
      name: "interior-planner-storage",
      version: 1,
      storage: createJSONStorage(() => storage),
      partialize: (s) => ({ project: s.project ***REMOVED***),
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
