/**
 * App root — Phase 2 proof: the store initializes the mock ecosystem and
 * renders its live stats. Phase 3 replaces this with real widgets.
 */
import { useEffect } from 'react';
import type { Freelancer } from '@entities/user';
import { useTrajectoryStore, selectStats, selectCurrentUser, selectCandidates } from './store';

export default function App() {
  const status = useTrajectoryStore((s) => s.status);
  const eco = useTrajectoryStore((s) => s.eco);
  const currentUserId = useTrajectoryStore((s) => s.currentUserId);
  const init = useTrajectoryStore((s) => s.init);

  useEffect(() => {
    if (status === 'idle') init();
  }, [status, init]);

  if (status !== 'ready' || !eco) return <main style={{ padding: 32 }}>Загрузка экосистемы…</main>;

  const stats = selectStats(eco);
  const user = selectCurrentUser(eco, currentUserId);
  const draft = selectCandidates(eco, ['Figma', 'Copywriting'], 50);

  return (
    <main style={{ fontFamily: 'monospace', padding: 32 }}>
      <h1>ТРАЕКТОРИЯ · Phase 2 — экосистема в store</h1>
      {stats && (
        <ul>
          <li>Подростки: {stats.counts.freelancers} · Менторы: {stats.counts.mentors} · Клиенты: {stats.counts.clients}</li>
          <li>Проекты: {stats.counts.projects} · Задачи: {stats.counts.tasks}</li>
          <li>Оборот: ₽{stats.turnoverRub.toLocaleString('ru-RU')} (подросткам ₽{stats.teensEarnedRub.toLocaleString('ru-RU')})</li>
          <li>Топ-навык: {stats.skillCounts[0]?.skill} × {stats.skillCounts[0]?.count}</li>
        </ul>
      )}
      {user && user.role === 'freelancer' && (
        <p>
          Текущий юзер: {(user as Freelancer).name} · репутация {user.reputation} · навыков:{' '}
          {Object.keys((user as Freelancer).skills).length}
        </p>
      )}
      <p>Драфт-кандидаты (Figma + Copywriting ≥ 50): {draft.length}</p>
    </main>
  );
}
