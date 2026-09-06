/**
 * App host — Phase 3: hash-routed views over the store.
 * intro → dashboard (teen) → parent (read-only), mirroring the prototype flow.
 */
import { useEffect } from 'react';
import { useTrajectoryStore, selectStats, selectCurrentUser } from './store';
import { useHashRoute, navigate, type ViewName } from './router';
import { Dashboard } from '@widgets/dashboard';
import { ParentControl } from '@widgets/parent-control';
import { TeamBuilder } from '@widgets/team-builder';
import { ImgPlaceholder } from '@shared/ui';

function Intro() {
  return (
    <main className="container" style={{ minHeight: '80vh', display: 'flex', flexDirection: 'column', justifyContent: 'center', position: 'relative' }}>
      <div style={{ position: 'absolute', inset: 0, opacity: 0.15, zIndex: -1, filter: 'grayscale(100%) contrast(1.2)' }}>
        <ImgPlaceholder imgId="IMG-01" height={480} />
      </div>
      <div style={{ position: 'relative', zIndex: 2, maxWidth: 800 }}>
        <p className="type-caption" style={{ marginBottom: 'var(--spacing-md)' }}>
          Система профессиональной ориентации v2.6
        </p>
        <h1 className="type-h1">
          Тебе 14.
          <br />
          У тебя есть четыре года,
          <br />
          чтобы создать что-то настоящее.
        </h1>
        <p className="type-body" style={{ margin: 'var(--spacing-lg) 0', maxWidth: 500 }}>
          Никаких игр. Никаких бейджей. Только реальные проекты, менторы из индустрии и портфолио, которое работает на тебя.
        </p>
        <button className="btn btn-primary" onClick={() => navigate('dashboard')}>
          Войти в систему
        </button>
      </div>
    </main>
  );
}

const NAV: Array<{ id: ViewName; label: string }> = [
  { id: 'dashboard', label: 'Обзор' },
  { id: 'team', label: 'Драфт' },
  { id: 'parent', label: 'Родитель' },
];

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
          <span className="type-mono" style={{ fontWeight: 700, fontSize: '1.2rem' }}>TRAJECTORY_</span>
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

      {view === 'intro' && <Intro />}
      {view === 'dashboard' && <Dashboard />}
      {view === 'team' && <TeamBuilder />}
      {view === 'parent' && <ParentControl />}

      {view === 'intro' && (
        <div className="container" style={{ paddingBottom: 'var(--spacing-xl)' }}>
          <p className="type-caption">
            Демо-режим: экосистема {stats?.counts.freelancers} подростков / {stats?.counts.mentors} менторов /{' '}
            {stats?.counts.clients} клиентов · вид {view.toUpperCase()} · юзер: {user?.name ?? '—'}
          </p>
          <button className="btn btn-outline" style={{ marginTop: 'var(--spacing-sm)' }} onClick={() => setView('dashboard')}>
            Пропустить → дашборд
          </button>
        </div>
      )}
    </>
  );
}
