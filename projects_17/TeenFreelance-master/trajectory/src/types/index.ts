/**
 * TRAJECTORY — canonical domain types (Stage 1 of React migration).
 *
 * Source of truth: concept «Траектория» (../задача.md):
 *   - «Архитектура данных (TypeScript Interfaces)» section
 *   - «СИСТЕМНЫЙ ПРОМТ» §4 Этап 1 (Типизация и Данные)
 *   - Business rules from the vision section (Skill Score, Mentor Score,
 *     parental consent, economy split).
 *
 * Import rule: layers import domain types only from `./types` (re-exported
 * by entity barrels) — never redefine entity shapes locally.
 */

/* ------------------------------------------------------------------ */
/* Shared primitives                                                    */
/* ------------------------------------------------------------------ */

export type ISODate = string; // 'YYYY-MM-DD' — mock data keeps this human-readable

/** Runtime environments a user account can operate in. */
export type UserRole = 'freelancer' | 'mentor' | 'client' | 'parent';

/** Lifecycle of a project, per concept §«Главная механика». */
export type ProjectStatus = 'draft' | 'in_progress' | 'review' | 'completed' | 'cancelled';

/** Skill name vocabulary — closed set mirrors mock-data generator. */
export type SkillName =
  | 'Figma'
  | 'Blender'
  | 'Python'
  | 'Copywriting'
  | 'UX Research'
  | 'Typography'
  | 'Composition'
  | 'AI Tools';

/** Skill levels are integers 0..100 (Skill Score, concept §6). */
export type SkillLevel = number;

/* ------------------------------------------------------------------ */
/* Proofs — evidence-based skill system (no XP, concept §2.1)          */
/* ------------------------------------------------------------------ */

/** What kind of artefact backs a skill claim. */
export type ProofType = 'project' | 'course' | 'review';

/** A single verifiable artefact attached to skills. */
export interface Proof {
  id: string;
  type: ProofType;
  title: string;
  /** ISODate of the artefact creation. */
  date: ISODate;
  /** Project/URL reference that makes the proof checkable. */
  ref?: string;
}

/* ------------------------------------------------------------------ */
/* Users                                                               */
/* ------------------------------------------------------------------ */

/** Base fields shared by every account. */
export interface User {
  id: string;
  name: string;
  role: UserRole;
  /** Reputation 0..100 (concept §6: not stars — evidence-backed). */
  reputation: number;
  avatarImgId?: string; // IMG-0X key from the imagePrompts registry
}

/**
 * Teen freelancer (concept §1 «Подросток», §5-6 Skill Score).
 * Invariants enforced at data layer:
 *   - 14 <= age <= 18 while active on the platform;
 *   - every non-zero skill level should reference at least one proof
 *     (anti-gamification: no skill without evidence).
 */
export interface Freelancer extends User {
  role: 'freelancer';
  age: number;
  /** Skill Score table: skill name -> level 0..100. */
  skills: Partial<Record<SkillName, SkillLevel>>;
  /** Evidence for skills; Proof.id may be shared across skill entries. */
  proofs: Proof[];
  /** Total money earned on the platform (RUB). */
  earnings: number;
  status: 'active' | 'busy' | 'looking';
}

/** Mentor levels gate project complexity (concept §8). */
export type MentorLevel = 'Junior' | 'Pro' | 'Senior' | 'Expert';

/**
 * Mentor (concept §1 «Наставник», §7 Mentor Score, §8 levels, §10 economy).
 * Invariants:
 *   - successRate 0..100;
 *   - mentorScore components must sum consistently (see MentorScore).
 */
export interface Mentor extends User {
  role: 'mentor';
  specialization: SkillName;
  level: MentorLevel;
  studentsCount: number;
  /** % of students who completed their program. */
  successRate: number;
}

/** Client-facing analytics view (concept §12 Talent Pool). */
export interface TalentPoolSnapshot {
  companyId: string;
  /** e.g. 'Blender' — tracked specialty. */
  specialty: SkillName;
  region: string;
  /** # of freelancers who reached junior-equivalent level this month. */
  juniorsReadyThisMonth: number;
  freelancerIds: string[];
}

/**
 * Client / company account (concept §1 «Клиент»: buys a result, not people).
 */
export interface Client extends User {
  role: 'client';
  companyName: string;
  /** Unspent project budget (RUB). */
  budget: number;
  talentPool?: TalentPoolSnapshot;
}

/**
 * Parent account: read-only transparency layer + consent authority
 * (concept §1 «Родитель», §2.3). Parents never participate in workflow.
 */
export interface Parent extends User {
  role: 'parent';
  /** Linked teen accounts this parent may observe. */
  childIds: string[];
}

/* ------------------------------------------------------------------ */
/* Money & parental consent                                            */
/* ------------------------------------------------------------------ */

/**
 * Economy split of a paid project (concept §11). Percentages must sum to 100.
 * Mirrors the dashboard economy-bar: teen 51 / mentor 20 / platform 20 / reserve 9.
 */
export interface BudgetDistribution {
  teenPercent: number; // → split across team members
  mentorPercent: number;
  platformPercent: number;
  reservePercent: number;
}

/** Hard gate: no money moves without it (Parental Gate, concept Часть 1 §5). */
export interface ParentalConsent {
  id: string;
  parentId: string;
  freelancerId: string;
  /** What exactly is being consented to (project payment, mentor change...). */
  scope: 'project_payment' | 'mentor_change' | 'platform_rules';
  projectId?: string;
  grantedAt: ISODate;
  revokedAt?: ISODate;
  /** Opaque confirmation token issued to the parent channel. */
  token: string;
}

/* ------------------------------------------------------------------ */
/* Projects & tasks                                                    */
/* ------------------------------------------------------------------ */

/**
 * Project = client task executed by a mentor-led team (concept §2).
 * Invariants:
 *   - budget > 0 for paid projects;
 *   - teamIds.length >= 1 and mentorId set once status leaves 'draft';
 *   - financial operations require an active ParentalConsent per teen.
 */
export interface Project {
  id: string;
  title: string;
  description: string;
  budget: number;
  clientId: string;
  mentorId: string | null;
  /** Freelancer ids working on the project (the «драфт» result). */
  teamIds: string[];
  status: ProjectStatus;
  /** Skills the team must cover — used by TeamBuilder filters. */
  requiredSkills: SkillName[];
  coverImgId?: string; // IMG-0X key from the imagePrompts registry
  createdAt: ISODate;
  deadline?: ISODate;
}

/** Task state inside the review loop (concept Часть 1 §2). */
export type TaskStatus = 'todo' | 'in_progress' | 'submitted' | 'in_review' | 'changes_requested' | 'done';

/** Versioned submission inside the Review Loop (v1, v2 ... vFinal). */
export interface TaskVersion {
  id: string;
  version: number;
  /** File refs or Figma links submitted for this version. */
  attachments: string[];
  comment: string;
  submittedAt: ISODate;
  /** Pinned review comments: area key -> note. */
  reviewNotes?: Array<{ area: string; note: string; authorId: string }>;
}

/**
 * A concrete assignment of one freelancer inside a project.
 */
export interface Task {
  id: string;
  projectId: string;
  freelancerId: string;
  title: string;
  description: string;
  status: TaskStatus;
  /** 0..100 manual progress shown on the dashboard. */
  progress: number;
  deadline?: ISODate;
  versions: TaskVersion[];
  reward: number; // teen's share (RUB) after BudgetDistribution split
}

/* ------------------------------------------------------------------ */
/* Misc UI models (dashboard mock surface)                             */
/* ------------------------------------------------------------------ */

/** One entry of the dashboard «Лента доказательств». */
export interface ActivityEntry {
  id: string;
  type: 'skill_up' | 'payment' | 'review' | 'project' | 'system';
  text: string;
  time: string;
}

/** Static image-prompt placeholder registry entry (IMG-0X, ../задача.md). */
export interface ImagePromptDef {
  id: string; // 'IMG-01'...
  label: string;
  prompt: string;
  aspect: '21:9' | '16:9' | '4:3' | '1:1';
}
