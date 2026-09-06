/**
 * Global ecosystem store — Zustand (concept: «State Management: Zustand»).
 * Holds the generated mock ecosystem + session state; stats and lookups are
 * pure selectors in this module (recomputable, no stale-cache problems).
 */
import { create } from 'zustand';
import type {
  Client,
  Freelancer,
  Mentor,
  MentorLevel,
  Project,
  SkillName,
} from '../types';
import { generateEcosystem, type Ecosystem } from '../shared/mock/generator.ts';
import { computeEcosystemStats, type EcosystemStats } from '../shared/mock/ecoStats.ts';

export type SessionRole = Freelancer['role'] | Mentor['role'] | Client['role'];

/* ------------------------------------------------------------------ */
/* Draft (TeamBuilder, concept Часть 1 §3 / Этап 3.2)                   */
/* ------------------------------------------------------------------ */

/** Mentor level gates team size (concept §8, mirrors generator L181–185). */
export const MENTOR_TEAM_LIMIT: Record<MentorLevel, number> = {
  Expert: 5,
  Senior: 4,
  Pro: 3,
  Junior: 1,
};

/** One scored search result of the draft. */
export interface DraftCandidateScore {
  freelancer: Freelancer;
  /** Selected skills the freelancer holds at >= minLevel. */
  matched: SkillName[];
  /** Average level across matched skills (ranking key). */
  avg: number;
}

/** Ephemeral TeamBuilder session state (reset after project creation). */
export interface DraftState {
  title: string;
  requiredSkills: SkillName[];
  minLevel: number;
  mentorId: string | null;
  invitedIds: string[];
  /** Recomputed on every filter change — no derived-state staleness. */
  results: DraftCandidateScore[];
}

const MIN_LEVEL_FLOOR = 0;
const MIN_LEVEL_CEIL = 100;
/** Default budget for a draft-created project (mid-range CLIENT_BUDGETS). */
const DEFAULT_BUDGET = 20_000;

function emptyDraft(): DraftState {
  return { title: '', requiredSkills: [], minLevel: 50, mentorId: null, invitedIds: [], results: [] };
}

/** Score all freelancers against the draft filters (pure, deterministic). */
function scoreCandidates(eco: Ecosystem, skills: SkillName[], minLevel: number): DraftCandidateScore[] {
  if (skills.length === 0) return [];
  return eco.freelancers
    .map((f) => {
      const matched = skills.filter((s) => (f.skills[s] ?? 0) >= minLevel);
      const avg =
        matched.length === 0
          ? 0
          : matched.reduce((acc, s) => acc + (f.skills[s] ?? 0), 0) / matched.length;
      return { freelancer: f, matched, avg };
    })
    .filter(({ matched }) => matched.length === skills.length)
    .sort((a, b) => b.avg - a.avg);
}

interface TrajectoryState {
  status: 'idle' | 'ready';
  /** Deterministic mock ecosystem (seed fixed in init). */
  eco: Ecosystem | null;
  /** «Signed in» user for demos; 'f-0001' = Максим-like profile. */
  currentUserId: string | null;
  draft: DraftState;
  init: (seed?: number) => void;
  setCurrentUser: (id: string | null) => void;
  /* --- draft actions (TeamBuilder) --- */
  toggleSkill: (skill: SkillName) => void;
  setMinLevel: (n: number) => void;
  setDraftTitle: (t: string) => void;
  pickMentor: (id: string | null) => void;
  toggleInvite: (freelancerId: string) => void;
  resetDraft: () => void;
  /** Creates a Project from the assembled team; returns it (null if no eco). */
  createProjectFromTeam: () => Project | null;
}

export const useTrajectoryStore = create<TrajectoryState>((set, get) => ({
  status: 'idle',
  eco: null,
  currentUserId: null,
  draft: emptyDraft(),
  init: (seed = 20260905) =>
    set({ eco: generateEcosystem(seed), status: 'ready', currentUserId: 'f-0001', draft: emptyDraft() }),
  setCurrentUser: (id) => set({ currentUserId: id }),

  /* --- draft actions --- */
  toggleSkill: (skill) => {
    const { eco, draft } = get();
    if (!eco) return;
    const requiredSkills = draft.requiredSkills.includes(skill)
      ? draft.requiredSkills.filter((s) => s !== skill)
      : [...draft.requiredSkills, skill];
    set({ draft: { ...draft, requiredSkills, results: scoreCandidates(eco, requiredSkills, draft.minLevel) } });
  },
  setMinLevel: (n) => {
    const { eco, draft } = get();
    if (!eco) return;
    const minLevel = Math.min(MIN_LEVEL_CEIL, Math.max(MIN_LEVEL_FLOOR, Math.round(n)));
    set({ draft: { ...draft, minLevel, results: scoreCandidates(eco, draft.requiredSkills, minLevel) } });
  },
  setDraftTitle: (t) => {
    set({ draft: { ...get().draft, title: t } });
  },
  pickMentor: (id) => {
    const { eco, draft } = get();
    if (!eco) return;
    const mentor = id ? (eco.mentors.find((m) => m.id === id) ?? null) : null;
    const limit = mentor ? MENTOR_TEAM_LIMIT[mentor.level] : 1; // без наставника — соло-режим (лимит Junior)
    const invitedIds = draft.invitedIds.slice(0, limit);
    set({ draft: { ...draft, mentorId: mentor?.id ?? null, invitedIds } });
  },
  toggleInvite: (freelancerId) => {
    const { eco, draft } = get();
    if (!eco) return;
    const mentor = draft.mentorId ? (eco.mentors.find((m) => m.id === draft.mentorId) ?? null) : null;
    const limit = mentor ? MENTOR_TEAM_LIMIT[mentor.level] : 1;
    const invitedIds = draft.invitedIds.includes(freelancerId)
      ? draft.invitedIds.filter((id) => id !== freelancerId)
      : draft.invitedIds.length < limit
        ? [...draft.invitedIds, freelancerId]
        : draft.invitedIds; // gate: team size capped by mentor level (concept §8)
    set({ draft: { ...draft, invitedIds } });
  },
  resetDraft: () => set({ draft: emptyDraft() }),
  createProjectFromTeam: () => {
    const { eco, draft } = get();
    if (!eco) return null;
    const maxNum = eco.projects.reduce((acc, p) => {
      const m = /^p-(\d{4})$/.exec(p.id);
      return m ? Math.max(acc, Number(m[1])) : acc;
    }, 0);
    const clientId = eco.clients.find((c) => c.budget >= DEFAULT_BUDGET)?.id ?? 'c-0001';
    const project: Project = {
      id: `p-${String(maxNum + 1).padStart(4, '0')}`,
      title: draft.title.trim() || 'Проект из драфта',
      description: `Команда собрана в драфте: ${draft.invitedIds.length} участник(ов); навыки: ${draft.requiredSkills.join(', ') || '—'}.`,
      budget: DEFAULT_BUDGET,
      clientId,
      mentorId: draft.mentorId,
      teamIds: [...draft.invitedIds],
      status: draft.mentorId !== null && draft.invitedIds.length > 0 ? 'in_progress' : 'draft',
      requiredSkills: [...draft.requiredSkills],
      coverImgId: 'IMG-06',
      createdAt: new Date().toISOString().slice(0, 10),
    };
    set({ eco: { ...eco, projects: [project, ...eco.projects] }, draft: emptyDraft() });
    return project;
  },
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
 * Candidate search (concept Этап 3.2) — dashboard preview helper.
 * The interactive TeamBuilder uses the scored `draft.results` slice instead
 * (per-skill levels + ranking), built by `scoreCandidates` above.
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

/**
 * Mentor capacity for the draft UI: team-size limit by level (concept §8)
 * plus how many active projects the mentor already leads (context info).
 */
export function selectMentorCapacity(
  eco: Ecosystem | null,
  mentorId: string | null,
): { mentor: Mentor | null; limit: number; activeProjects: number } {
  const mentor = (eco?.mentors.find((m) => m.id === mentorId) ?? null) as Mentor | null;
  if (!eco || !mentor) return { mentor: null, limit: 0, activeProjects: 0 };
  const activeProjects = eco.projects.filter(
    (p) => p.mentorId === mentor.id && (p.status === 'in_progress' || p.status === 'review'),
  ).length;
  return { mentor, limit: MENTOR_TEAM_LIMIT[mentor.level], activeProjects };
}

/** Tasks of one freelancer with their project metadata (dashboard source). */
export function selectTasksOfUser(eco: Ecosystem | null, id: string | null) {
  if (!eco || !id) return [];
  return eco.tasks
    .filter((t) => t.freelancerId === id)
    .map((t) => {
      const project = eco.projects.find((p) => p.id === t.projectId);
      return {
        ...t,
        projectTitle: project?.title ?? '',
        projectCoverImgId: project?.coverImgId,
        projectStatus: project?.status,
      };
    });
}
