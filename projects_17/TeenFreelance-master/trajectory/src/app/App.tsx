/**
 * App host — Freeстарт (pompts_11/122.md): концепт-презентация как главный вид,
 * демо-дашборд/драфт/ревью/родитель — интерактивный макет за ней.
 */
import { useEffect } from 'react';
import { useTrajectoryStore, selectStats, selectCurrentUser } from './store';
import { useHashRoute, type ViewName } from './router';
import { ConceptView } from '@widgets/concept-view';
import { Dashboard } from '@widgets/dashboard';
import { ParentControl } from '@widgets/parent-control';
import { TeamBuilder } from '@widgets/team-builder';
import { ReviewLoop } from '@widgets/review-loop';
import { ImgPlaceholder } from '@shared/ui';
import { BRAND, BRAND_LOGO } from '@shared/concept/content';

const NAV: Array<{ id: ViewName; label: string }> = [
  { id: 'dashboard', label: 'Обзор' },
  { id: 'team', label: 'Драфт' },
  { id: 'review', label: 'Ревью' },
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
  const currentUserId = useTrajectoryStore((s) => s.currentUserId);
  const init = useTrajectoryStore((s) => s.init);
  const [view, setView] = useHashRoute();

  useEffect(() => {
    if (status === 'idle') init();
  }, [status, init]);

  if (status !== 'ready' || !eco) {
    return <main className="container" style={{ padding: 32 }}>Загрузка экосистемы…</main>;
  }

  const user = selectCurrentUser(eco, currentUserId);
  const stats = selectStats(eco);

  return (
    <>
      <header
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 1000,
          background: 'rgba(244, 242, 238, 0.95)',
          backdropFilter: 'blur(10px)',
          borderBottom: '1px solid var(--c-border)',
          padding: 'var(--spacing-md) 0',
        }}
      >
        <div className="container flex-between">
          <BrandMark />
          <nav>
            {NAV.map((n) => (
              <a
                key={n.id}
                href={`#${n.id}`}
                className="type-mono"
                style={{
                  marginRight: 'var(--spacing-lg)',
                  textDecoration: 'none',
                  color: view === n.id ? 'var(--c-text-primary)' : 'var(--c-text-secondary)',
                  borderBottom: view === n.id ? '1px solid var(--c-accent)' : 'none',
                  paddingBottom: 2,
                }}
              >
                {n.label}
              </a>
            ))}
          </nav>
          <div className="flex-between" style={{ gap: 10 }}>
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
      {view === 'parent' && <ParentControl />}

      {view === 'intro' && (
        <div className="container" style={{ paddingBottom: 'var(--spacing-xl)' }}>
          <p className="type-caption">
            Демо-режим: экосистема {stats?.counts.freelancers} подростков / {stats?.counts.mentors} менторов /{' '}
            {stats?.counts.clients} клиентов · юзер: {user?.name ?? '—'}
          </p>
          <button className="btn btn-outline" style={{ marginTop: 'var(--spacing-sm)' }} onClick={() => setView('dashboard')}>
            {view === 'intro' ? 'Пропустить → демо-дашборд' : 'Назад к концепции'}
          </button>
        </div>
      )}
    </>
  );
}
