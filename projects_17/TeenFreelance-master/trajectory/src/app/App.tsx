/**
 * App host — Freeстарт (pompts_11/122.md): концепт-презентация как главный вид,
 * демо-дашборд/драфт/ревью/родитель — интерактивный макет за ней.
 */
import { useEffect } from 'react';
import { useTrajectoryStore, selectStats } from './store';
import { useHashRoute, type ViewName } from './router';
import { ConceptView } from '@widgets/concept-view';
import { Dashboard } from '@widgets/dashboard';
import { ParentControl } from '@widgets/parent-control';
import { TeamBuilder } from '@widgets/team-builder';
import { ReviewLoop } from '@widgets/review-loop';
import { SkillGraphView } from '@widgets/skill-graph';
import { ImgPlaceholder } from '@shared/ui';
import { BRAND, BRAND_LOGO } from '@shared/concept/content';

const NAV: Array<{ id: ViewName; label: string }> = [
  { id: 'intro', label: 'Концепция' },
  { id: 'dashboard', label: 'Обзор' },
  { id: 'team', label: 'Драфт' },
  { id: 'review', label: 'Ревью' },
  { id: 'skills', label: 'Навыки' },
  { id: 'parent', label: 'Родитель' },
];

function BrandMark() {
  return (
    <a className="brand-mark" href="#intro" title={BRAND}>
      <img src={BRAND_LOGO} alt={BRAND} style={{ height: 26, width: 'auto', display: 'block' }} />
      <span className="brand-word" style={{ fontSize: '1.15rem' }}>
        Free<span style={{ color: 'var(--c-accent)' }}>старт</span>
        <span className="type-mono" style={{ color: 'var(--c-accent)' }}>
          _
        </span>
      </span>
    </a>
  );
}

export default function App() {
  const status = useTrajectoryStore((s) => s.status);
  const eco = useTrajectoryStore((s) => s.eco);
  const init = useTrajectoryStore((s) => s.init);
  const [view] = useHashRoute();

  useEffect(() => {
    if (status === 'idle') init();
  }, [status, init]);

  if (status !== 'ready' || !eco) {
    return <main className="boot-splash">Freeстарт · загрузка экосистемы…</main>;
  }

  const stats = selectStats(eco);

  return (
    <>
      <header className="app-header">
        <div className="container">
          <BrandMark />
          <nav className="header-nav">
            {NAV.map((n) => (
              <a key={n.id} href={`#${n.id}`} className={`type-mono${view === n.id ? ' active' : ''}`}>
                {n.label}
              </a>
            ))}
          </nav>
          <div className="header-eco">
            <div className="type-mono">
              {stats ? `₽${stats.turnoverRub.toLocaleString('ru-RU')}` : '₽0'} · оборот
            </div>
            <div style={{ width: 32, height: 32, borderRadius: '50%', overflow: 'hidden' }}>
              <ImgPlaceholder imgId="IMG-02" height={32} />
            </div>
          </div>
        </div>
      </header>

      {view === 'intro' && <ConceptView />}
      {view === 'dashboard' && <Dashboard />}
      {view === 'team' && <TeamBuilder />}
      {view === 'review' && <ReviewLoop />}
      {view === 'skills' && <SkillGraphView />}
      {view === 'parent' && <ParentControl />}

      {view === 'intro' && (
        <div className="container" style={{ paddingBottom: 'var(--spacing-xl)' }}>
          <p className="type-caption">
            Демо-режим: экосистема {stats?.counts.freelancers} подростков / {stats?.counts.mentors} менторов /{' '}
            {stats?.counts.clients} клиентов · интерактивный макет за презентацией
          </p>
        </div>
      )}
    </>
  );
}
