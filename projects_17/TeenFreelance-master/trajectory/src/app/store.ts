/**
 * Global ecosystem store — Zustand (concept: «State Management: Zustand»).
 * Holds the generated mock ecosystem + session state; stats and lookups are
 * pure selectors in this module (recomputable, no stale-cache problems).
 */
import { create } from 'zustand';
import type { Client, Freelancer, Mentor, SkillName } from '../types';
import { generateEcosystem, type Ecosystem } from '../shared/mock/generator.ts';
import { computeEcosystemStats, type EcosystemStats } from '../shared/mock/ecoStats.ts';

export type SessionRole = Freelancer['role'] | Mentor['role'] | Client['role'];

interface TrajectoryState {
  status: 'idle' | 'ready';
  /** Deterministic mock ecosystem (seed fixed in init). */
  eco: Ecosystem | null;
  /** «Signed in» user for demos; 'f-0001' = Максим-like profile. */
  currentUserId: string | null;
  init: (seed?: number) => void;
  setCurrentUser: (id: string | null) => void;
}

export const useTrajectoryStore = create<TrajectoryState>((set) => ({
  status: 'idle',
  eco: null,
  currentUserId: null,
  init: (seed = 20260905) =>
    set({ eco: generateEcosystem(seed), status: 'ready', currentUserId: 'f-0001' }),
  setCurrentUser: (id) => set({ currentUserId: id }),
}));

/* ------------------------- selectors ------------------------- */

export function selectStats(eco: Ecosystem | null): EcosystemStats | null {
  return eco ? computeEcosystemStats(eco) : null;
}

export function selectCurrentUser(
  eco: Ecosystem | null,
  id: string | null,
): Freelancer | Mentor | Client | null {
  if (!eco || !id) return null;
  return (
    eco.freelancers.find((f) => f.id === id) ??
    eco.mentors.find((m) => m.id === id) ??
    eco.clients.find((c) => c.id === id) ??
    null
  );
}

/**
 * Candidate search for the future TeamBuilder (concept Этап 3.2):
 * freelancers having ALL given skills at level >= minLevel, ranked by
 * average level of the matched skills.
 */
export function selectCandidates(
  eco: Ecosystem | null,
  skills: SkillName[],
  minLevel = 50,
): Freelancer[] {
  if (!eco || skills.length === 0) return [];
  const matched = eco.freelancers
    .map((f) => {
      const levels = skills.map((s) => f.skills[s]).filter((l): l is number => (l ?? 0) >= minLevel);
      return { f, hits: levels.length, avg: levels.reduce((a, b) => a + b, 0) / Math.max(1, levels.length) };
    })
    .filter(({ hits }) => hits === skills.length);
  return matched.sort((a, b) => b.avg - a.avg).map(({ f }) => f);
}

/** Tasks of one freelancer with their project titles (dashboard feed source). */
export function selectTasksOfUser(eco: Ecosystem | null, id: string | null) {
  if (!eco || !id) return [];
  return eco.tasks
    .filter((t) => t.freelancerId === id)
    .map((t) => ({ ...t, projectTitle: eco.projects.find((p) => p.id === t.projectId)?.title ?? '' }));
}
