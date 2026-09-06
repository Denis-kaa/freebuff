/**
 * Widget: parent-control — read-only transparency layer + consent inbox
 * (prototype #view-parent + Parental Gate, concept §1/Часть 1 §5).
 * Родитель видит безопасность, финансы (с economy-bar 51/20/20/9) и историю
 * проектов; вмешиваться в рабочий процесс нельзя, НО решения по деньгам —
 * через консент-инбокс (grant/deny/revoke) — это зона родителя.
 */
import { useState } from 'react';
import type { Freelancer } from '@entities/user';
import { ImgPlaceholder } from '@shared/ui';
import {
  useTrajectoryStore,
  selectCurrentUser,
  selectTasksOfUser,
  selectConsentInbox,
} from '../../app/store';

export function ParentControl() {
  const eco = useTrajectoryStore((s) => s.eco);
  const childId = useTrajectoryStore((s) => s.currentUserId); // demo: observe the current user
  const grantConsent = useTrajectoryStore((s) => s.grantConsent);
  const denyConsent = useTrajectoryStore((s) => s.denyConsent);
  const revokeConsent = useTrajectoryStore((s) => s.revokeConsent);
  const [feedback, setFeedback] = useState<string | null>(null);
  const user = selectCurrentUser(eco, childId);
  const tasks = selectTasksOfUser(eco, childId);

  // Demo identity: parent of the current teen (perfect 2-children partition).
  const parentId = eco?.consents.find((c) => c.freelancerId === childId)?.parentId ?? null;
  const inbox = selectConsentInbox(eco, parentId);

  if (!user || user.role !== 'freelancer') {
    return <main className="container section-padding">Профиль ребёнка не найден.</main>;
  }

  const teen = user as Freelancer;
  const mentor = eco?.mentors.find((m) => m.id === eco.projects.find((p) => tasks.some((t) => t.projectId === p.id))?.mentorId);

  return (
    <main className="container section-padding">
      <div style={{ background: '#FFF8E1', padding: 'var(--spacing-md)', borderLeft: '4px solid #FFC107', marginBottom: 'var(--spacing-lg)' }}>
        <h3 className="type-h3" style={{ color: '#856404' }}>Режим Родителя (Read-Only)</h3>
        <p className="type-body" style={{ color: '#856404', marginTop: 5 }}>
          Вы просматриваете профиль {teen.name}. Вы не можете редактировать данные или отправлять сообщения от его имени.
        </p>
      </div>

      <div className="dashboard-grid">
        <div className="card">
          <h3 className="type-h3">Безопасность и активность</h3>
          <div style={{ marginTop: 'var(--spacing-md)' }}>
            <div className="flex-between" style={{ padding: '10px 0', borderBottom: '1px solid #eee' }}>
              <span>Возраст</span>
              <span className="type-mono">{teen.age} лет</span>
            </div>
            <div className="flex-between" style={{ padding: '10px 0', borderBottom: '1px solid #eee' }}>
              <span>Верификация личности</span>
              <span className="badge badge-status-approved">Подтверждено</span>
            </div>
            <div className="flex-between" style={{ padding: '10px 0', borderBottom: '1px solid #eee' }}>
              <span>Менторский контроль</span>
              <span className="type-mono">
                {mentor ? `${mentor.name} (успех ${mentor.successRate}%)` : '—'}
              </span>
            </div>
          </div>
        </div>

        <div className="card">
          <h3 className="type-h3">Финансы</h3>
          <div className="type-mono" style={{ fontSize: '2rem', fontWeight: 700, margin: 'var(--spacing-md) 0' }}>
            ₽{teen.earnings.toLocaleString('ru-RU')}
          </div>
          <p className="type-body">Заработано за текущий период. Средства распределены по экономике платформы:</p>
          <div className="economy-bar">
            <div className="eco-segment eco-team" style={{ width: '51%' }} title="Подросток" />
            <div className="eco-segment eco-mentor" style={{ width: '20%' }} title="Ментор" />
            <div className="eco-segment eco-platform" style={{ width: '20%' }} title="Платформа" />
            <div className="eco-segment eco-reserve" style={{ width: '9%' }} title="Резерв" />
          </div>
          <div className="flex-between type-caption" style={{ marginTop: 5 }}>
            <span>Подросток (51%)</span>
            <span>Платформа/Налоги</span>
          </div>
        </div>
      </div>

      {/* Consent inbox — the parent's ONLY action surface (scope-scoped, per project) */}
      <div className="card" style={{ marginTop: 'var(--spacing-lg)' }}>
        <h3 className="type-h3">Консент-инбокс — решения по деньгам</h3>
        <p className="type-body" style={{ margin: 'var(--spacing-sm) 0' }}>
          Без активного согласия родителя деньги за проект не двигаются (Parental Gate, concept §5).
        </p>

        {inbox.pending.length > 0 && (
          <>
            <h4 className="type-h4" style={{ margin: 'var(--spacing-md) 0 var(--spacing-sm)' }}>
              Ожидают решения ({inbox.pending.length})
            </h4>
            {inbox.pending.map(({ consent, childName, projectTitle }) => (
              <div
                key={consent.id}
                className="flex-between"
                style={{ padding: '10px 0', borderBottom: '1px solid var(--c-border)', gap: 10 }}
              >
                <div>
                  <strong>{childName}</strong> · «{projectTitle}»
                  <div className="type-caption">запрос от {consent.requestedAt ?? '—'} · {consent.id}</div>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button
                    className="btn btn-primary"
                    onClick={() => {
                      const ok = grantConsent(consent.id);
                      setFeedback(ok ? `✓ Согласие выдано (${consent.id})` : '✗ Не удалось выдать');
                    }}
                  >
                    Выдать согласие
                  </button>
                  <button
                    className="btn btn-outline"
                    onClick={() => {
                      const ok = denyConsent(consent.id);
                      setFeedback(ok ? `✓ Отказано (${consent.id})` : '✗ Не удалось отказать');
                    }}
                  >
                    Отказать
                  </button>
                </div>
              </div>
            ))}
          </>
        )}
        {inbox.pending.length === 0 && (
          <p className="type-caption" style={{ margin: 'var(--spacing-sm) 0' }}>Нет запросов, ожидающих решения.</p>
        )}

        {inbox.active.length > 0 && (
          <>
            <h4 className="type-h4" style={{ margin: 'var(--spacing-md) 0 var(--spacing-sm)' }}>
              Активные согласия ({inbox.active.length}) — можно отозвать
            </h4>
            {inbox.active.map(({ consent, childName, projectTitle }) => (
              <div
                key={consent.id}
                className="flex-between"
                style={{ padding: '10px 0', borderBottom: '1px solid var(--c-border)', gap: 10 }}
              >
                <div>
                  <strong>{childName}</strong> · «{projectTitle}»
                  <div className="type-caption">выдано {consent.grantedAt ?? '—'} · {consent.id}</div>
                </div>
                <button
                  className="btn btn-outline"
                  onClick={() => {
                    const ok = revokeConsent(consent.id);
                    setFeedback(ok ? `✓ Согласие отозвано (${consent.id})` : '✗ Не удалось отозвать');
                  }}
                >
                  Отозвать
                </button>
              </div>
            ))}
          </>
        )}
        {feedback && <p className="type-mono" style={{ marginTop: 'var(--spacing-sm)' }}>{feedback}</p>}
      </div>

      <div className="card" style={{ marginTop: 'var(--spacing-lg)' }}>
        <h3 className="type-h3">История проектов</h3>
        <table style={{ width: '100%', textAlign: 'left', marginTop: 'var(--spacing-md)', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid var(--c-text-primary)' }}>
              <th style={{ padding: 10 }}>Проект</th>
              <th style={{ padding: 10 }}>Статус</th>
              <th style={{ padding: 10 }}>Прогресс</th>
              <th style={{ padding: 10 }}>Награда</th>
            </tr>
          </thead>
          <tbody className="type-mono" style={{ fontSize: '0.8rem' }}>
            {tasks.map((t) => (
              <tr key={t.id} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: 10 }}>{t.projectTitle}</td>
                <td style={{ padding: 10 }}>
                  <span className={`badge ${t.status === 'done' ? 'badge-status-approved' : 'badge-status-pending'}`}>
                    {t.status}
                  </span>
                </td>
                <td style={{ padding: 10 }}>{t.progress}%</td>
                <td style={{ padding: 10 }}>₽{t.reward.toLocaleString('ru-RU')}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {tasks[0]?.projectCoverImgId && (
          <div style={{ marginTop: 'var(--spacing-md)' }}>
            <ImgPlaceholder imgId={tasks[0].projectCoverImgId} height={160} />
          </div>
        )}
      </div>
    </main>
  );
}
