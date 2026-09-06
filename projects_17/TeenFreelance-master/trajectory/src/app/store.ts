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
  TaskStatus,
  TaskVersion,
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
  /* --- review loop (Review Loop, concept Part 1 §2) --- */
  /** Task opened from the dashboard/queue; null = auto-pick first queue item. */
  selectedReviewTaskId: string | null;
  selectReviewTask: (id: string | null) => void;
  /** Freelancer submits a new version (from in_progress/changes_requested). */
  submitVersion: (taskId: string, comment: string) => TaskVersion | null;
  /** Mentor opens the review: submitted → in_review. */
  startReview: (taskId: string) => boolean;
  /** Mentor pins a note to an area of the latest version (in_review only). */
  addReviewNote: (taskId: string, area: string, note: string, authorId: string) => boolean;
  /** Mentor requests changes: in_review → changes_requested. */
  requestChanges: (taskId: string) => boolean;
  /** Mentor approves: in_review → done, progress 100. */
  approveTask: (taskId: string) => boolean;
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

  /* --- review loop actions --- */
  selectedReviewTaskId: null,
  selectReviewTask: (id) => set({ selectedReviewTaskId: id }),
  submitVersion: (taskId, comment) => {
    const { eco } = get();
    if (!eco) return null;
    const task = eco.tasks.find((t) => t.id === taskId);
    // State machine gate: only work-in-progress accepts submissions.
    if (!task || (task.status !== 'in_progress' && task.status !== 'changes_requested')) return null;
    const version: TaskVersion = {
      id: `v-${task.id}-${task.versions.length + 1}`,
      version: task.versions.length + 1,
      attachments: [],
      comment: comment.trim(),
      submittedAt: new Date().toISOString().slice(0, 10),
      reviewNotes: [],
    };
    set({
      eco: {
        ...eco,
        tasks: eco.tasks.map((t) =>
          t.id === taskId ? { ...t, versions: [...t.versions, version], status: 'submitted' as TaskStatus } : t,
        ),
      },
    });
    return version;
  },
  startReview: (taskId) => {
    const { eco } = get();
    if (!eco) return false;
    const task = eco.tasks.find((t) => t.id === taskId);
    if (!task || task.status !== 'submitted') return false;
    set({
      eco: {
        ...eco,
        tasks: eco.tasks.map((t) => (t.id === taskId ? { ...t, status: 'in_review' as TaskStatus } : t)),
      },
    });
    return true;
  },
  addReviewNote: (taskId, area, note, authorId) => {
    const { eco } = get();
    if (!eco) return false;
    const task = eco.tasks.find((t) => t.id === taskId);
    // Pinned notes attach to the latest submitted version during review.
    if (!task || task.status !== 'in_review' || task.versions.length === 0) return false;
    const trimmed = note.trim();
    if (!trimmed) return false;
    set({
      eco: {
        ...eco,
        tasks: eco.tasks.map((t) => {
          if (t.id !== taskId) return t;
          const versions = t.versions.slice();
          const latest = versions[versions.length - 1];
          if (!latest) return t;
          versions[versions.length - 1] = {
            ...latest,
            reviewNotes: [...(latest.reviewNotes ?? []), { area, note: trimmed, authorId }],
          };
          return { ...t, versions };
        }),
      },
    });
    return true;
  },
  requestChanges: (taskId) =>
    transitionReviewTask(set, get, taskId, 'in_review', 'changes_requested'),
  approveTask: (taskId) => {
    const ok = transitionReviewTask(set, get, taskId, 'in_review', 'done');
    if (!ok) return false;
    // Approved ⇒ the assignment is complete: progress pinned to 100.
    const eco = get().eco;
    if (!eco) return false;
    set({
      eco: {
        ...eco,
        tasks: eco.tasks.map((t) => (t.id === taskId ? { ...t, progress: 100 } : t)),
      },
    });
    return true;
  },
}));

/** Shared status-transition helper for mentor review actions. */
function transitionReviewTask(
  set: (partial: { eco: Ecosystem }) => void,
  get: () => TrajectoryState,
  taskId: string,
  from: TaskStatus,
  to: TaskStatus,
): boolean {
  const eco = get().eco;
  if (!eco) return false;
  const task = eco.tasks.find((t) => t.id === taskId);
  if (!task || task.status !== from) return false;
  set({
    eco: {
      ...eco,
      tasks: eco.tasks.map((t) => (t.id === taskId ? { ...t, status: to } : t)),
    },
  });
  return true;
}

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

/**
 * Mentor's review queue: all tasks currently in the review cycle,
 * enriched with project/freelancer context for the queue list.
 */
export function selectReviewQueue(eco: Ecosystem | null) {
  if (!eco) return [];
  const IN_CYCLE: readonly TaskStatus[] = ['submitted', 'in_review', 'changes_requested'];
  return eco.tasks
    .filter((t) => IN_CYCLE.includes(t.status))
    .map((t) => {
      const project = eco.projects.find((p) => p.id === t.projectId);
      const freelancer = eco.freelancers.find((f) => f.id === t.freelancerId);
      return {
        task: t,
        projectTitle: project?.title ?? '',
        mentorId: project?.mentorId ?? null,
        freelancerName: freelancer?.name ?? '',
      };
    });
}

/** One task + its project metadata (review detail view). */
export function selectTaskDetail(eco: Ecosystem | null, taskId: string | null) {
  if (!eco || !taskId) return null;
  const task = eco.tasks.find((t) => t.id === taskId);
  if (!task) return null;
  const project = eco.projects.find((p) => p.id === task.projectId);
  const freelancer = eco.freelancers.find((f) => f.id === task.freelancerId);
  return {
    task,
    projectTitle: project?.title ?? '',
    projectCoverImgId: project?.coverImgId,
    mentorId: project?.mentorId ?? null,
    freelancerName: freelancer?.name ?? '',
  };
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
