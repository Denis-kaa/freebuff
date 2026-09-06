/**
 * Widget: dashboard — teen workspace, ported from the prototype's
 * #view-dashboard (задача.md) onto the Phase 2 store.
 */
import { useEffect } from 'react';
import type { Freelancer } from '@entities/user';
import type { TaskStatus } from '@entities/task';
import { ImgPlaceholder } from '@shared/ui';
import { useTrajectoryStore, selectStats, selectCurrentUser, selectTasksOfUser, selectCandidates } from '../../app/store';
import { navigate } from '../../app/router';

const STATUS_BADGE: Record<TaskStatus, { label: string; cls: string }> = {
  todo: { label: 'Ожидает старта', cls: 'badge-status-pending' },
  in_progress: { label: 'В процессе', cls: 'badge-status-pending' },
  submitted: { label: 'Отправлено', cls: 'badge-status-pending' },
  in_review: { label: 'На ревью', cls: 'badge-status-pending' },
  changes_requested: { label: 'Правки', cls: 'badge-status-pending' },
  done: { label: 'Завершено', cls: 'badge-status-approved' },
};

export function Dashboard() {
  const eco = useTrajectoryStore((s) => s.eco);
  const currentUserId = useTrajectoryStore((s) => s.currentUserId);
  const setCurrentUser = useTrajectoryStore((s) => s.setCurrentUser);

  const stats = selectStats(eco);
  const user = selectCurrentUser(eco, currentUserId);
  const tasks = selectTasksOfUser(eco, currentUserId);
  const draftOffers = selectCandidates(eco, ['Figma', 'Copywriting'], 70).slice(0, 3);
  const activeTask = tasks.find((t) => t.status === 'in_progress') ?? tasks[0] ?? null;

  useEffect(() => {
    if (!currentUserId && eco) setCurrentUser(eco.freelancers[0]?.id ?? null);
  }, [currentUserId, eco, setCurrentUser]);

  if (!stats || !user || user.role !== 'freelancer') {
    return <main className="container section-padding">Профиль фрилансера не найден.</main>;
  }

  const me = user as Freelancer;

  return (
    <main className="container section-padding">
      {/* Header */}
      <div className="flex-between">
        <div>
          <h2 className="type-h1">Привет, {me.name.split(' ')[0]}.</h2>
          <p className="type-caption">
            Статус: {me.status === 'looking' ? 'Активный поиск проектов' : me.status === 'busy' ? 'Занят' : 'В работе'} ·
            Репутация: {me.reputation}/100
          </p>
        </div>
        <div className="type-mono" style={{ textAlign: 'right' }}>
          <div>
            Заработано: <span style={{ color: 'var(--c-success)', fontWeight: 700 }}>₽{me.earnings.toLocaleString('ru-RU')}</span>
          </div>
          <div>Активные задачи: {tasks.filter((t) => t.status !== 'done').length}</div>
        </div>
      </div>

      <div className="dashboard-grid">
        {/* Main column */}
        <div style={{ display: 'grid', gap: 'var(--spacing-lg)' }}>
          {activeTask && (
            <div className="card">
              <div className="flex-between" style={{ marginBottom: 'var(--spacing-md)' }}>
                <span className={`badge ${STATUS_BADGE[activeTask.status]?.cls ?? 'badge-status-pending'}`}>
                  {STATUS_BADGE[activeTask.status]?.label ?? activeTask.status}
                </span>
                {activeTask.deadline && <span className="type-mono">Дедлайн: {activeTask.deadline}</span>}
              </div>
              <h3 className="type-h2">{activeTask.projectTitle}</h3>
              <p className="type-body" style={{ margin: 'var(--spacing-md) 0' }}>
                {activeTask.description}
              </p>
              {activeTask.projectCoverImgId && (
                <ImgPlaceholder imgId={activeTask.projectCoverImgId} height={200} />
              )}
              <div className="flex-between" style={{ marginTop: 'var(--spacing-md)' }}>
                <div className="type-mono">Прогресс: {activeTask.progress}%</div>
                <div className="type-mono">Награда: ₽{activeTask.reward.toLocaleString('ru-RU')}</div>
              </div>
              <div className="progress-track" style={{ marginTop: 'var(--spacing-sm)' }}>
                <div className="progress-fill" style={{ width: `${activeTask.progress}%` }} />
              </div>
            </div>
          )}

          <div className="card">
            <h4 className="type-h4" style={{ marginBottom: 'var(--spacing-md)' }}>Лента доказательств</h4>
            {me.proofs.length === 0 && <p className="type-body">Первые доказательства появятся после проектов.</p>}
            {me.proofs.map((p) => (
              <div key={p.id} style={{ padding: '10px 0', borderBottom: '1px solid var(--c-border)' }}>
                <div style={{ fontWeight: 500 }}>
                  {p.type === 'project' ? '🎨' : '⭐'} {p.title}
                </div>
                <div className="type-caption" style={{ marginTop: 2 }}>{p.date}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Sidebar */}
        <div style={{ display: 'grid', gap: 'var(--spacing-lg)' }}>
          <div className="card">
            <h4 className="type-h4" style={{ marginBottom: 'var(--spacing-md)' }}>Навыки (доказанные)</h4>
            {Object.entries(me.skills).map(([skill, level]) => (
              <div key={skill} className="skill-node">
                <div>
                  <div style={{ fontWeight: 600 }}>{skill}</div>
                  <div className="skill-meta">
                    {me.proofs.filter((p) => p.title.includes(skill)).length} подтверждений
                  </div>
                </div>
                <div className="type-mono">{level}%</div>
              </div>
            ))}
            <button
              type="button"
              className="btn btn-secondary skill-graph-link"
              onClick={() => navigate('skills')}
            >
              Граф навыков: {me.name.split(' ')[0]} →
            </button>
          </div>

          <div className="card skill-graph-teaser">
            <div>
              <h4 className="type-h4" style={{ margin: 0 }}>Граф навыков</h4>
              <p className="type-caption" style={{ marginTop: 'var(--spacing-sm)' }}>
                Skill Score + кросс-навыковые бусты · бусты двигают только эффективный уровень, не хранимый Score
              </p>
            </div>
            <button type="button" className="btn btn-primary" onClick={() => navigate('skills')}>
              Открыть граф →
            </button>
          </div>

          <div className="card" style={{ background: 'var(--c-text-primary)', color: 'var(--c-bg-primary)' }}>
            <h4 className="type-h4" style={{ marginBottom: 'var(--spacing-md)', borderBottom: '1px solid #333', paddingBottom: 10 }}>
              Предложения драфта
            </h4>
            {draftOffers.map((f) => (
              <div key={f.id} style={{ padding: '10px 0', borderBottom: '1px solid #333' }}>
                <div className="type-mono" style={{ color: '#aaa' }}>Сильный кандидат</div>
                <div style={{ fontWeight: 600, margin: '5px 0' }}>
                  {f.name} · {Object.keys(f.skills).join(', ')}
                </div>
                <div className="flex-between" style={{ marginTop: 10 }}>
                  <span className="type-mono" style={{ fontSize: '0.7rem' }}>Репутация {f.reputation}</span>
                  <button className="btn btn-primary" style={{ padding: '4px 8px', fontSize: '0.7rem' }}>
                    Инвайт
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
