/**
 * Widget: review-loop — async review cycle (concept Часть 1 §2).
 * Freelancer submits versions (v1..vFinal); mentor opens review, pins
 * notes to zones of the submission, then approves or requests changes.
 * State machine lives in the store; this widget renders it.
 */
import { useState } from 'react';
import type { TaskStatus } from '@entities/task';
import { ImgPlaceholder } from '@shared/ui';
import {
  useTrajectoryStore,
  selectReviewQueue,
  selectTaskDetail,
} from '../../app/store';

const STATUS_BADGE: Record<TaskStatus, { label: string; cls: string }> = {
  todo: { label: 'Ожидает старта', cls: 'badge-level-mid' },
  in_progress: { label: 'В работе', cls: 'badge-level-mid' },
  submitted: { label: 'Отправлено', cls: 'badge-level-high' },
  in_review: { label: 'На ревью', cls: 'badge-level-high' },
  changes_requested: { label: 'Правки', cls: 'badge-status-pending' },
  done: { label: 'Завершено', cls: 'badge-status-approved' },
};

/** Pin zones over the submission preview (mock of «клик по области макета»). */
const ZONES = ['A', 'B', 'C', 'D', 'E', 'F'] as const;

export function ReviewLoop() {
  const eco = useTrajectoryStore((s) => s.eco);
  const selectedId = useTrajectoryStore((s) => s.selectedReviewTaskId);
  const selectReviewTask = useTrajectoryStore((s) => s.selectReviewTask);
  const submitVersion = useTrajectoryStore((s) => s.submitVersion);
  const startReview = useTrajectoryStore((s) => s.startReview);
  const addReviewNote = useTrajectoryStore((s) => s.addReviewNote);
  const requestChanges = useTrajectoryStore((s) => s.requestChanges);
  const approveTask = useTrajectoryStore((s) => s.approveTask);

  const [versionComment, setVersionComment] = useState('');
  const [noteText, setNoteText] = useState('');
  const [zone, setZone] = useState<string>('A');
  const [feedback, setFeedback] = useState<string | null>(null);

  if (!eco) return <main className="container section-padding">Экосистема ещё не собрана.</main>;

  const queue = selectReviewQueue(eco);
  const detail = selectTaskDetail(eco, selectedId ?? queue[0]?.task.id ?? null);
  const task = detail?.task ?? null;

  const run = (ok: boolean, msg: string) => {
    setFeedback(ok ? `✓ ${msg}` : `✗ ${msg}`);
  };

  return (
    <main className="container section-padding">
      <h2 className="type-h2">Ревью-луп</h2>
      <p className="type-caption" style={{ marginTop: 'var(--spacing-sm)' }}>
        Асинхронный цикл: версия → ревью → пины/правки → аппрув (concept §2)
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: '300px minmax(0, 1fr)', gap: 'var(--spacing-lg)', marginTop: 'var(--spacing-lg)' }}>
        {/* Queue */}
        <aside>
          <h4 className="type-h4" style={{ marginBottom: 'var(--spacing-md)' }}>
            Очередь ({queue.length})
          </h4>
          <div style={{ display: 'grid', gap: 8 }}>
            {queue.map(({ task: t, projectTitle, freelancerName }) => (
              <button
                key={t.id}
                onClick={() => selectReviewTask(t.id)}
                className="card"
                style={{
                  textAlign: 'left',
                  cursor: 'pointer',
                  padding: 12,
                  border: task?.id === t.id ? '1px solid var(--c-accent)' : '1px solid var(--c-border)',
                }}
              >
                <div className="type-mono" style={{ fontSize: '0.7rem' }}>{t.id}</div>
                <div style={{ fontWeight: 600, margin: '4px 0' }}>{projectTitle}</div>
                <div className="type-caption">{freelancerName}</div>
                <span className={`badge ${STATUS_BADGE[t.status].cls}`} style={{ marginTop: 6, display: 'inline-block' }}>
                  {STATUS_BADGE[t.status].label}
                </span>
              </button>
            ))}
            {queue.length === 0 && <p className="type-body">Очередь пуста — все задачи вне цикла ревью.</p>}
          </div>
        </aside>

        {/* Detail */}
        {detail && task ? (
          <section style={{ display: 'grid', gap: 'var(--spacing-lg)' }}>
            <div className="card">
              <div className="flex-between">
                <div>
                  <span className={`badge ${STATUS_BADGE[task.status].cls}`}>{STATUS_BADGE[task.status].label}</span>
                  <h3 className="type-h3" style={{ marginTop: 'var(--spacing-sm)' }}>{detail.projectTitle}</h3>
                  <p className="type-caption">
                    {detail.freelancerName} · {task.title} · награда ₽{task.reward.toLocaleString('ru-RU')}
                  </p>
                </div>
                <div className="type-mono">прогресс {task.progress}%</div>
              </div>
              {detail.projectCoverImgId && (
                <div style={{ marginTop: 'var(--spacing-md)' }}>
                  <ImgPlaceholder imgId={detail.projectCoverImgId} height={160} />
                </div>
              )}
              <p className="type-body" style={{ marginTop: 'var(--spacing-md)' }}>{task.description}</p>
            </div>

            {/* Version history */}
            <div className="card">
              <h4 className="type-h4" style={{ marginBottom: 'var(--spacing-md)' }}>
                Версии ({task.versions.length})
              </h4>
              {task.versions.length === 0 && (
                <p className="type-body">Версий ещё нет — отправь первую на ревью.</p>
              )}
              {[...task.versions].reverse().map((v) => (
                <div key={v.id} style={{ padding: '12px 0', borderBottom: '1px solid var(--c-border)' }}>
                  <div className="flex-between">
                    <strong className="type-mono">v{v.version}</strong>
                    <span className="type-caption">{v.submittedAt}</span>
                  </div>
                  <p className="type-body" style={{ margin: '6px 0' }}>{v.comment || '— без комментария —'}</p>
                  {(v.reviewNotes?.length ?? 0) > 0 && (
                    <div style={{ display: 'grid', gap: 6, marginTop: 8 }}>
                      {v.reviewNotes?.map((n, i) => (
                        <div key={i} className="type-caption" style={{ borderLeft: '2px solid var(--c-accent)', paddingLeft: 8 }}>
                          [зона {n.area}] {n.note}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}

              {/* Freelancer action: submit a version */}
              {(task.status === 'in_progress' || task.status === 'changes_requested') && (
                <div style={{ marginTop: 'var(--spacing-md)' }}>
                  <textarea
                    className="type-body"
                    placeholder="Комментарий к версии (что сделано)…"
                    value={versionComment}
                    onChange={(e) => setVersionComment(e.target.value)}
                    style={{ width: '100%', minHeight: 60, padding: 10, border: '1px solid var(--c-border)', background: '#fff' }}
                  />
                  <button
                    className="btn btn-primary"
                    style={{ marginTop: 8 }}
                    onClick={() => {
                      const v = submitVersion(task.id, versionComment);
                      run(v !== null, v ? `версия v${v.version} отправлена` : 'отправка отклонена стейт-машиной');
                      setVersionComment('');
                    }}
                  >
                    Отправить версию
                  </button>
                </div>
              )}

              {/* Mentor actions */}
              {task.status === 'submitted' && (
                <button
                  className="btn btn-primary"
                  style={{ marginTop: 'var(--spacing-md)' }}
                  onClick={() => run(startReview(task.id), 'ревью открыто')}
                >
                  Начать ревью
                </button>
              )}
              {task.status === 'in_review' && (
                <div style={{ marginTop: 'var(--spacing-md)', display: 'grid', gap: 10 }}>
                  <div>
                    <div className="type-caption" style={{ marginBottom: 6 }}>Пин к зоне последней версии:</div>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 8 }}>
                      {ZONES.map((z) => (
                        <button
                          key={z}
                          className={`badge ${zone === z ? 'badge-level-high' : 'badge-level-mid'}`}
                          style={{ cursor: 'pointer', padding: '4px 10px' }}
                          onClick={() => setZone(z)}
                        >
                          {zone === z ? `✓ зона ${z}` : `зона ${z}`}
                        </button>
                      ))}
                    </div>
                    <input
                      className="type-body"
                      placeholder="Комментарий к зоне…"
                      value={noteText}
                      onChange={(e) => setNoteText(e.target.value)}
                      style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--c-border)', background: '#fff' }}
                    />
                  </div>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <button
                      className="btn btn-outline"
                      onClick={() => {
                        const ok = addReviewNote(task.id, zone, noteText, detail.mentorId ?? 'm-0001');
                        run(ok, ok ? `пин в зону ${zone} добавлен` : 'пин отклонён');
                        setNoteText('');
                      }}
                    >
                      📌 Пин
                    </button>
                    <button
                      className="btn btn-outline"
                      onClick={() => run(requestChanges(task.id), 'правки запрошены')}
                    >
                      Запросить правки
                    </button>
                    <button
                      className="btn btn-primary"
                      onClick={() => run(approveTask(task.id), 'задача завершена')}
                    >
                      Одобрить
                    </button>
                  </div>
                </div>
              )}
              {feedback && (
                <p className="type-mono" style={{ marginTop: 'var(--spacing-sm)' }}>{feedback}</p>
              )}
            </div>
          </section>
        ) : (
          <section>
            <p className="type-body">Задача не выбрана — возьми первую из очереди.</p>
          </section>
        )}
      </div>
    </main>
  );
}
