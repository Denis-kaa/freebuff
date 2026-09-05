/**
 * Ecosystem-wide statistics — the «Live Market» / useEcosystemStats surface
 * from the concept (Часть 4 §1: live projects, money pool, recent completions).
 * Pure functions over Ecosystem — the store will expose them via selectors.
 */
import type { Client, Freelancer, Mentor, SkillName } from '../../types';
import type { Ecosystem } from './generator.ts';
import { totalTurnover } from './generator.ts';

export interface EcosystemStats {
  counts: { freelancers: number; mentors: number; clients: number; projects: number; tasks: number };
  /** ₽ in active + completed projects (mock «оборот» metric). */
  turnoverRub: number;
  /** ₽ paid out to teens (51% share of turnover, concept §11). */
  teensEarnedRub: number;
  /** ₽ paid to mentors (20% share). */
  mentorsEarnedRub: number;
  /** Skill → how many freelancers hold it at level >= 40. */
  skillCounts: Array<{ skill: SkillName; count: number }>;
  /** Most active mentors by students count (top N). */
  topMentors: Array<Pick<Mentor, 'id' | 'name' | 'level' | 'studentsCount'>>;
  /** Newest completed projects (for the Live feed). */
  recentCompleted: Array<Pick<Ecosystem['projects'][number], 'id' | 'title' | 'budget' | 'status'>>;
  /** Freelancers with the highest reputation. */
  topFreelancers: Array<Pick<Freelancer, 'id' | 'name' | 'reputation' | 'skills'>>;
  /** Clients ranked by unspent budget. */
  topClients: Array<Pick<Client, 'id' | 'companyName' | 'budget'>>;
}

export function computeEcosystemStats(eco: Ecosystem, topN = 5): EcosystemStats {
  const TEEN_SHARE = 0.51;
  const MENTOR_SHARE = 0.2;

  const turnoverRub = totalTurnover(eco);

  return {
    counts: {
      freelancers: eco.freelancers.length,
      mentors: eco.mentors.length,
      clients: eco.clients.length,
      projects: eco.projects.length,
      tasks: eco.tasks.length,
    },
    turnoverRub,
    teensEarnedRub: Math.round(turnoverRub * TEEN_SHARE),
    mentorsEarnedRub: Math.round(turnoverRub * MENTOR_SHARE),
    skillCounts: countSkills(eco.freelancers),
    topMentors: [...eco.mentors]
      .sort((a, b) => b.studentsCount - a.studentsCount)
      .slice(0, topN)
      .map(({ id, name, level, studentsCount }) => ({ id, name, level, studentsCount })),
    recentCompleted: eco.projects
      .filter((p) => p.status === 'completed')
      .slice(0, topN)
      .map(({ id, title, budget, status }) => ({ id, title, budget, status })),
    topFreelancers: [...eco.freelancers]
      .sort((a, b) => b.reputation - a.reputation)
      .slice(0, topN)
      .map(({ id, name, reputation, skills }) => ({ id, name, reputation, skills })),
    topClients: [...eco.clients]
      .sort((a, b) => b.budget - a.budget)
      .slice(0, topN)
      .map(({ id, companyName, budget }) => ({ id, companyName, budget })),
  };
}

/** Count freelancers holding each skill at level >= MIN_LEVEL. */
function countSkills(freelancers: Freelancer[]): Array<{ skill: SkillName; count: number }> {
  const MIN_LEVEL = 40;
  const acc = new Map<SkillName, number>();
  for (const f of freelancers) {
    for (const [skill, level] of Object.entries(f.skills) as Array<[SkillName, number]>) {
      if (level >= MIN_LEVEL) {
        acc.set(skill, (acc.get(skill) ?? 0) + 1);
      }
    }
  }
  return [...acc.entries()]
    .map(([skill, count]) => ({ skill, count }))
    .sort((a, b) => b.count - a.count);
}
