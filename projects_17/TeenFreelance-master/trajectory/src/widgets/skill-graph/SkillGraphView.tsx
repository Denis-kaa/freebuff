/**
 * SkillGraphView — #skills view: freelancer picker, the graph itself,
 * and a per-skill table (stored vs effective, boost, proof count).
 */
import { useMemo, useState } from 'react';
import { useTrajectoryStore } from '@app/store';
import { buildSkillGraph, averageEffective } from '@features/skill-tree';
import { SkillGraph } from './SkillGraph.tsx';

export function SkillGraphView() {
  const eco = useTrajectoryStore((s) => s.eco);
  const currentUserId = useTrajectoryStore((s) => s.currentUserId);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const freelancer = useMemo(() => {
    if (!eco) return null;
    const id = selectedId ?? currentUserId;
    return eco.freelancers.find((f) => f.id === id) ?? eco.freelancers[0] ?? null;
  }, [eco, selectedId, currentUserId]);

  if (!eco || !freelancer) {
    return <main className="container section-padding">Экосистема ещё не собрана.</main>;
  }

  const nodes = buildSkillGraph(freelancer);
  const avg = averageEffective(nodes);
  const pulsing = nodes.filter((n) => n.pulsing);

  return (
    <main className="container section-padding">
      <div className="flex-between" style={{ flexWrap: 'wrap', gap: 'var(--spacing-md)' }}>
        <div>
          <h2 className="type-h2">Граф навыков</h2>
          <p className="type-caption" style={{ marginTop: 'var(--spacing-sm)' }}>
            Skill Score + кросс-навыковые бусты (concept Этап 3.1) · узлы с эффективным уровнем &gt; 80 пульсируют
          </p>
        </div>
        <div className="type-mono" style={{ textAlign: 'right' }}>
          <div>
            Средний эффективный: <strong>{avg}</strong>
          </div>
          <div className="type-caption">пульсируют: {pulsing.length} из {nodes.length}</div>
        </div>
      </div>

      <div style={{ margin: 'var(--spacing-md) 0 var(--spacing-lg)' }}>
        <select
          aria-label="Выбор фрилансера"
          value={freelancer.id}
          onChange={(e) => setSelectedId(e.target.value)}
          style={{ width: '100%', maxWidth: 420, padding: '8px 12px', border: '1px solid var(--c-border)', background: '#fff' }}
        >
          {eco.freelancers.map((f) => (
            <option key={f.id} value={f.id}>
              {f.name} · {f.id}
            </option>
          ))}
        </select>
      </div>

      <SkillGraph nodes={nodes} name={freelancer.name} />

      <div className="two-pane pane-list-first" style={{ marginTop: 'var(--spacing-lg)' }}>
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--c-text-primary)' }}>
                <th style={{ padding: 10 }}>Навык</th>
                <th style={{ padding: 10 }}>Stored</th>
                <th style={{ padding: 10 }}>Effective</th>
                <th style={{ padding: 10 }}>Буст</th>
                <th style={{ padding: 10 }}>Proofs</th>
              </tr>
            </thead>
            <tbody className="type-mono" style={{ fontSize: '0.8rem' }}>
              {[...nodes]
                .sort((a, b) => b.effective - a.effective)
                .map((n) => (
                  <tr key={n.skill} style={{ borderBottom: '1px solid var(--c-border)' }}>
                    <td style={{ padding: 10 }}>
                      {n.skill}
                      {n.pulsing && <span className="status-badge status-open" style={{ marginLeft: 8 }}>&gt;80</span>}
                    </td>
                    <td style={{ padding: 10 }}>{n.level}</td>
                    <td style={{ padding: 10, fontWeight: 700 }}>{n.effective}</td>
                    <td style={{ padding: 10, color: n.boost > 0 ? 'var(--c-success)' : undefined }}>
                      {n.boost > 0 ? `+${n.boost}` : '—'}
                    </td>
                    <td style={{ padding: 10 }}>{n.proofs}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>

        <aside className="card">
          <h4 className="type-h4" style={{ marginTop: 0 }}>
            Как читать граф
          </h4>
          <p className="type-body">
            Круг — Skill Score, число в узле — <strong>эффективный</strong> уровень: stored + бусты от связанных
            навыков (зелёные «+N»). Пунктирные рёбра — связи, у пока отсутствующих навыков.
          </p>
          <p className="type-body">
            Пульсирующие узлы (&gt;80) — готовность к сложным проектам. Хранимый Score бусты не меняют —
            доказательства привязаны к нему (анти-геймификация, §2.1).
          </p>
        </aside>
      </div>
    </main>
  );
}
