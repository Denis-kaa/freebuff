/**
 * Feature: skill-tree — Skill Graph Engine (concept Часть 1 §3, Этап 3.1).
 *
 * The graph logic is pure data (testable headless, like every other
 * mechanic — it lives in the feature layer, UI consumes it):
 *   - nodes = the freelancer's Skill Score (closed vocabulary, ANTI-6b);
 *   - edges = curated cross-skill boosts (e.g. UX Research → Composition);
 *   - a boost moves the *effective* level, never the stored Skill Score —
 *     evidence stays attached to the stored value (anti-gamification §2.1);
 *   - effective level > 80 ⇒ node "pulses" (ready for complex projects).
 */
import type { Freelancer, SkillLevel, SkillName } from '../../types';

/** Skill node as consumed by the visualisation layer. */
export interface SkillNode {
  skill: SkillName;
  /** Stored, evidence-backed Skill Score (0..100). */
  level: SkillLevel;
  /** Effective level after cross-skill boosts (0..100, capped). */
  effective: SkillLevel;
  /** Total boost applied from related skills. */
  boost: SkillLevel;
  /** >80 ⇒ ready for complex projects (concept Этап 3.1: node pulses). */
  pulsing: boolean;
  /** Number of evidence artefacts backing the stored level. */
  proofs: number;
}

/** Directed cross-skill relation: FROM boosts TO. Closed over SKILL_NAMES. */
interface BoostRule {
  from: SkillName;
  to: SkillName;
  /** Max contribution when `from` is at 100. */
  weight: number;
}

/**
 * Curated boost map (concept example: «UX Research → Empathy» mapped onto
 * the platform's closed vocabulary). Deliberately a closed table, not an
 * algorithm — the relations are a design decision, reviewable per-pair.
 */
export const SKILL_BOOSTS: readonly BoostRule[] = [
  { from: 'UX Research', to: 'Composition', weight: 6 },
  { from: 'UX Research', to: 'Copywriting', weight: 4 },
  { from: 'Figma', to: 'Typography', weight: 5 },
  { from: 'Figma', to: 'Composition', weight: 3 },
  { from: 'Typography', to: 'Composition', weight: 5 },
  { from: 'Composition', to: 'Typography', weight: 3 },
  { from: 'AI Tools', to: 'Figma', weight: 3 },
  { from: 'Blender', to: 'Composition', weight: 4 },
  { from: 'Python', to: 'AI Tools', weight: 4 },
];

/** The 8-skill closed vocabulary — import rule: only from @entities/skill. */
export const GRAPH_SKILLS: readonly SkillName[] = [
  'Figma',
  'Blender',
  'Python',
  'Copywriting',
  'UX Research',
  'Typography',
  'Composition',
  'AI Tools',
];

/**
 * Effective level = stored + Σ boosts·(level_from/100), capped at 100.
 * The boost is rounded to 0.1 FIRST, then effective is derived from the
 * rounded value — so the published node is self-consistent:
 * effective === min(100, level + boost) holds exactly (smoke-checked).
 */
function effectiveLevel(skill: SkillName, levels: Partial<Record<SkillName, number>>): { effective: SkillLevel; boost: SkillLevel } {
  let raw = 0;
  for (const rule of SKILL_BOOSTS) {
    if (rule.to !== skill) continue;
    const from = levels[rule.from];
    if (from === undefined) continue;
    raw += (rule.weight * from) / 100;
  }
  const boost = Math.round(raw * 10) / 10;
  const base = levels[skill] ?? 0;
  return { effective: Math.min(100, Math.round(base + boost)), boost };
}

/** Build the graph for one freelancer. Deterministic, no side effects. */
export function buildSkillGraph(freelancer: Freelancer): SkillNode[] {
  return GRAPH_SKILLS.map((skill) => {
    const level = freelancer.skills[skill] ?? 0;
    const { effective, boost } = effectiveLevel(skill, freelancer.skills);
    return {
      skill,
      level,
      effective,
      boost,
      pulsing: effective > 80,
      proofs: freelancer.proofs.filter((p) => (p.skills ?? []).includes(skill)).length,
    };
  });
}

/** Average effective level — ordering metric for "strongest skills" views. */
export function averageEffective(nodes: SkillNode[]): number {
  if (nodes.length === 0) return 0;
  return Math.round(nodes.reduce((s, n) => s + n.effective, 0) / nodes.length);
}
