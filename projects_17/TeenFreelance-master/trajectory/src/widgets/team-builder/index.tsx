/**
 * Widget: team-builder — the «Драфт» (concept Часть 1 §3, Этап 3.2).
 * Client-like flow over the mock ecosystem:
 *   1) pick required skills + min level  →  scored candidate list
 *   2) pick a mentor — level gates team size (concept §8)
 *   3) invite up to the cap → create project (status draft/in_progress)
 */
import { useState } from 'react';
import type { SkillName } from '@entities/skill';
import { SKILL_NAMES } from '@shared/mock/generator.ts';
import { MENTOR_TEAM_LIMIT } from '../../app/store';
import {
  useTrajectoryStore,
  selectMentorCapacity,
} from '../../app/store';

/** Sorted skill list = stable picker order (closed vocabulary ANTI-6b). */
const SKILL_OPTIONS: readonly SkillName[] = [...SKILL_NAMES].sort((a, b) => a.localeCompare(b));

export function TeamBuilder() {
  const eco = useTrajectoryStore((s) => s.eco);
  const draft = useTrajectoryStore((s) => s.draft);
  const toggleSkill = useTrajectoryStore((s) => s.toggleSkill);
  const setMinLevel = useTrajectoryStore((s) => s.setMinLevel);
  const setDraftTitle = useTrajectoryStore((s) => s.setDraftTitle);
  const pickMentor = useTrajectoryStore((s) => s.pickMentor);
  const toggleInvite = useTrajectoryStore((s) => s.toggleInvite);
  const resetDraft = useTrajectoryStore((s) => s.resetDraft);
  const createProjectFromTeam = useTrajectoryStore((s) => s.createProjectFromTeam);
  const [justCreated, setJustCreated] = useState<string | null>(null);

  if (!eco) return <main className="container section-padding">Экосистема ещё не собрана.</main>;

  const { mentor, activeProjects } = selectMentorCapacity(eco, draft.mentorId);
  const cap = mentor ? MENTOR_TEAM_LIMIT[mentor.level] : 1;
  const canInvite = draft.invitedIds.length < cap;

  return (
    <main className="container section-padding">
      <h2 className="type-h2">Драфт команды</h2>
      <p className="type-caption" style={{ marginTop: 'var(--spacing-sm)' }}>
        Шаг 1 — навыки · Шаг 2 — наставник · Шаг 3 — приглашения
        {draft.requiredSkills.length === 0 && ' · выбери хотя бы один навык'}
      </p>

      {/* 1) required skills */}
      <section style={{ margin: 'var(--spacing-lg) 0' }}>
        <h4 className="type-h4" style={{ marginBottom: 'var(--spacing-md)' }}>1 · Требуемые навыки</h4>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {SKILL_OPTIONS.map((skill) => {
            const active = draft.requiredSkills.includes(skill);
            return (
              <button
                key={skill}
                className={`badge ${active ? 'badge-level-high' : 'badge-level-mid'}`}
                style={{ cursor: 'pointer', padding: '6px 12px' }}
                onClick={() => toggleSkill(skill)}
              >
                {active ? '✓ ' : '+ '}
                {skill}
              </button>
            );
          })}
        </div>

        {/* min-level slider */}
        <div style={{ marginTop: 'var(--spacing-md)', maxWidth: 420 }}>
          <div className="flex-between">
            <span className="type-caption">Мин. уровень Skill Score</span>
            <span className="type-mono">{draft.minLevel}</span>
          </div>
          <input
            type="range"
            min={0}
            max={100}
            step={5}
            value={draft.minLevel}
            onChange={(e) => setMinLevel(Number(e.target.value))}
            style={{ width: '100%', accentColor: 'var(--c-accent)' }}
          />
        </div>
      </section>

      {/* 2) mentor picker */}
      <section style={{ margin: 'var(--spacing-lg) 0' }}>
        <h4 className="type-h4" style={{ marginBottom: 'var(--spacing-md)' }}>2 · Наставник</h4>
        <div className="flex-between" style={{ gap: 8, flexWrap: 'wrap' }}>
          <select
            className="type-body"
            value={draft.mentorId ?? ''}
            onChange={(e) => pickMentor(e.target.value || null)}
            style={{ padding: '8px 12px', border: '1px solid var(--c-border)', background: '#fff' }}
          >
            <option value="">— без наставника (соло, лимит 1) —</option>
            {eco.mentors.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name} · {m.specialization} · {m.level}
              </option>
            ))}
          </select>
          {mentor && (
            <span className="type-mono">
              лимит {cap} · в работе {activeProjects} · success {mentor.successRate}%
            </span>
          )}
        </div>
      </section>

      {/* 3) candidates + roster */}
      <section className="two-pane pane-list-first">
        <div>
          <div className="flex-between" style={{ marginBottom: 'var(--spacing-md)' }}>
            <h4 className="type-h4">Кандидаты ({draft.results.length})</h4>
            <span className="type-mono">сорт: средний уровень</span>
          </div>
          <div style={{ display: 'grid', gap: 'var(--spacing-sm)' }}>
            {draft.results.slice(0, 20).map(({ freelancer: f, matched, avg }) => {
              const invited = draft.invitedIds.includes(f.id);
              return (
                <div key={f.id} className="card" style={{ padding: 14 }}>
                  <div className="flex-between">
                    <div>
                      <strong>{f.name}</strong>
                      <span className="type-caption" style={{ marginLeft: 8 }}>
                        {f.age} лет · репутация {f.reputation}
                      </span>
                    </div>
                    <div className="type-mono">avg {Math.round(avg)}</div>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, margin: '10px 0' }}>
                    {matched.map((s) => (
                      <span key={s} className="badge badge-level-high">
                        {s} {f.skills[s] ?? 0}
                      </span>
                    ))}
                  </div>
                  <button
                    className={`btn ${invited ? 'btn-outline' : 'btn-primary'}`}
                    disabled={!invited && !canInvite}
                    onClick={() => toggleInvite(f.id)}
                  >
                    {invited ? '✓ Приглашён' : canInvite ? '+ Пригласить' : 'Лимит команды'}
                  </button>
                </div>
              );
            })}
            {draft.results.length === 0 && (
              <p className="type-body">Никого не найдено — снизь порог уровня или убери навык.</p>
            )}
          </div>
        </div>

        <aside className="card" style={{ alignSelf: 'start', position: 'sticky', top: 90 }}>
          <h4 className="type-h4" style={{ marginBottom: 'var(--spacing-md)' }}>
            Команда ({draft.invitedIds.length}/{cap})
          </h4>
          {draft.invitedIds.length === 0 && <p className="type-body">Пригласи хотя бы одного участника.</p>}
          {draft.invitedIds.map((id) => {
            const f = eco.freelancers.find((x) => x.id === id);
            if (!f) return null;
            return (
              <div
                key={id}
                className="flex-between"
                style={{ padding: '8px 0', borderBottom: '1px solid var(--c-border)' }}
              >
                <span>
                  {f.name}
                  <span className="type-caption" style={{ marginLeft: 8 }}>{f.age} л.</span>
                </span>
                <button
                  className="btn btn-outline"
                  style={{ padding: '2px 8px', fontSize: '0.7rem' }}
                  onClick={() => toggleInvite(id)}
                >
                  ✕
                </button>
              </div>
            );
          })}

          <div style={{ marginTop: 'var(--spacing-md)' }}>
            <input
              className="type-body"
              placeholder="Название проекта…"
              value={draft.title}
              onChange={(e) => setDraftTitle(e.target.value)}
              style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--c-border)', background: '#fff' }}
            />
            <button
              className="btn btn-primary"
              style={{ marginTop: 'var(--spacing-sm)', width: '100%' }}
              onClick={() => {
                const p = createProjectFromTeam();
                if (p) {
                  setJustCreated(p.id);
                  resetDraft();
                }
              }}
            >
              Создать проект
            </button>
            {justCreated && draft.invitedIds.length === 0 && (
              <p className="type-mono" style={{ marginTop: 'var(--spacing-sm)', color: 'var(--c-success)' }}>
                ✓ Проект {justCreated} создан
              </p>
            )}
          </div>
        </aside>
      </section>
    </main>
  );
}
