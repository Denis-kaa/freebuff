/**
 * SkillGraph — SVG visualisation of a freelancer's Skill Graph
 * (concept Этап 3.1): nodes on a circle, boost edges between related
 * skills, nodes with effective > 80 pulse.
 *
 * Consumes the pure feature-layer data (buildSkillGraph); no logic here.
 */
import type { SkillNode } from '@features/skill-tree';
import { SKILL_BOOSTS } from '@features/skill-tree';

const SIZE = 520;
const CX = SIZE / 2;
const CY = SIZE / 2;
const R = 180;

function nodePos(i: number, total: number): { x: number; y: number } {
  const angle = (2 * Math.PI * i) / total - Math.PI / 2;
  return { x: CX + R * Math.cos(angle), y: CY + R * Math.sin(angle) };
}

export function SkillGraph({ nodes, name }: { nodes: SkillNode[]; name: string }) {
  const pos = new Map(nodes.map((n, i) => [n.skill, nodePos(i, nodes.length)]));

  return (
    <svg
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      role="img"
      aria-label={`Граф навыков: ${name}`}
      style={{ width: '100%', maxWidth: 560, display: 'block', margin: '0 auto' }}
    >
      {/* boost edges: only between skills the freelancer actually has */}
      {SKILL_BOOSTS.map(({ from, to, weight }) => {
        const a = pos.get(from);
        const b = pos.get(to);
        if (!a || !b) return null;
        const active = nodes.some((n) => n.skill === from && n.level > 0) && nodes.some((n) => n.skill === to && n.level > 0);
        return (
          <line
            key={`${from}->${to}`}
            x1={a.x}
            y1={a.y}
            x2={b.x}
            y2={b.y}
            stroke="var(--c-border)"
            strokeWidth={active ? Math.max(1, weight / 2) : 0.6}
            strokeDasharray={active ? undefined : '3 5'}
            opacity={active ? 0.9 : 0.35}
          />
        );
      })}

      {/* spokes + nodes */}
      {nodes.map((n) => {
        const { x, y } = pos.get(n.skill)!;
        const rr = 14 + (n.effective / 100) * 22; // 14..36
        const fill = n.level === 0 ? 'var(--c-bg-secondary)' : n.pulsing ? 'var(--c-accent)' : 'var(--c-text-primary)';
        return (
          <g key={n.skill}>
            <line x1={CX} y1={CY} x2={x} y2={y} stroke="var(--c-border)" strokeWidth={1} opacity={0.6} />
            {n.pulsing && (
              <circle className="skill-pulse" cx={x} cy={y} r={rr + 6} fill="none" stroke="var(--c-accent)" strokeWidth={2} />
            )}
            <circle cx={x} cy={y} r={rr} fill={fill} stroke="var(--c-text-primary)" strokeWidth={1.5} />
            <text x={x} y={y + 4} textAnchor="middle" className="skill-node-num" fill={n.level === 0 ? 'var(--c-text-secondary)' : '#F4F2EE'}>
              {n.effective}
            </text>
            <text x={x} y={y + rr + 16} textAnchor="middle" className="skill-node-label">
              {n.skill}
              {n.boost > 0 && <tspan fill="var(--c-success)"> +{n.boost}</tspan>}
            </text>
          </g>
        );
      })}

      <text x={CX} y={CY - 6} textAnchor="middle" className="skill-center-name">
        {name}
      </text>
    </svg>
  );
}
