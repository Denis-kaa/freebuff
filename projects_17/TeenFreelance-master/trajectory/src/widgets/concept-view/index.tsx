/**
 * ConceptView — презентация концепции Freeстарт (pompts_11/122.md).
 *
 * Источник содержания: FreeStart_Concept.docx (единственный источник смыслов).
 * Каждый блок несёт статус (concept | mechanic | hypothesis | open) — презентация
 * остаётся концепт-предложением для обсуждения, а не ТЗ.
 *
 * Структура: hero (промо-кадр + видео) → диагноз → траектория → командная
 * механика → свобода (нет «владельца») → Skill Score → соло-порог (механика)
 * → компании (гипотеза) → Freeстарт/FreeStarter → защита от копирования →
 * открытые вопросы.
 */
import type { BlockStatus } from '@shared/concept/content';
import {
  BRAND,
  CHAIN,
  COMPANIES,
  DIAGNOSIS,
  FREEDOM,
  MOAT,
  OPEN_QUESTIONS,
  SKILL_SCORE,
  SOLO_RULE,
  STATUS_LABEL,
  TEAM_FLOW,
  BRAND_STORY,
  DEMO_INTRO,
} from '@shared/concept/content';
import { navigate } from '@app/router';

function StatusBadge({ status }: { status: BlockStatus }) {
  return <span className={`status-badge status-${status}`}>{STATUS_LABEL[status]}</span>;
}

function SectionHead({ title, status }: { title: string; status: BlockStatus }) {
  return (
    <div className="concept-head">
      <h2 className="type-h2" style={{ margin: 0 }}>
        {title}
      </h2>
      <StatusBadge status={status} />
    </div>
  );
}

function ChainBlock() {
  return (
    <section className="concept-section" id="trajectory">
      <div className="container">
        <SectionHead title="Видение: не биржа, а профессиональная траектория" status="concept" />
        <p className="type-body" style={{ maxWidth: 640 }}>
          Вместо «найти подработку» — путь. Главная идея: к 18 годам человек приходит не с нулевым
          опытом, а с историей профессионального развития — навыки, проекты, команды, отзывы.
        </p>
        <div className="chain">
          {CHAIN.map((step, i) => (
            <span key={step} style={{ display: 'inline-flex', alignItems: 'center', gap: 'var(--spacing-sm)' }}>
              {i > 0 && <span className="chain-arrow">→</span>}
              <span className="chain-step">{step}</span>
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}

export default function ConceptView() {
  return (
    <main>
      {/* HERO — промо-кадр как обложка концепции + видео как эмоциональное подтверждение тезиса */}
      <section style={{ paddingTop: 'var(--spacing-xl)' }}>
        <div className="container">
          <p className="type-caption" style={{ marginBottom: 'var(--spacing-md)' }}>
            {DEMO_INTRO.caption}
          </p>
          <h1 className="type-display-xl">
            Не биржа для школьников.
            <br />
            Профессиональная траектория.
          </h1>
          <p className="type-body" style={{ margin: 'var(--spacing-lg) 0', maxWidth: 620 }}>
            {BRAND} — это место, где начинается профессиональный путь подростка: интерес → навык →
            практика → ментор → команда → реальный проект → портфолио.
          </p>
          <div style={{ display: 'flex', gap: 'var(--spacing-md)', flexWrap: 'wrap' }}>
            <a className="btn btn-primary" href="#concept-diagnosis" style={{ textDecoration: 'none' }}>
              Читать концепцию
            </a>
            <button className="btn btn-outline" onClick={() => navigate('dashboard')}>
              {DEMO_INTRO.skip}
            </button>
          </div>

          <figure className="promo-figure">
            <img src="/media/promo.jpg" alt="Freeстарт — промо-кадр: подросток делает первый шаг" loading="eager" />
            <figcaption>Промо-кадр · первый шаг</figcaption>
          </figure>

          <div className="hero-media">
            {/* Автовоспроизведение без звука как атмосферный носитель тезиса «первого шага»;
                poster показывается до загрузки, fallback-ссылка — если видео не поддерживается. */}
            <video
              controls
              autoPlay
              muted
              loop
              playsInline
              preload="metadata"
              poster="/media/concept-poster.jpg"
            >
              <source src="/media/concept.mp4" type="video/mp4" />
              Ваш браузер не поддерживает встроенное видео.{' '}
              <a href="/media/concept.mp4">Скачать видео</a>.
            </video>
          </div>
          <p className="hero-media-note">Видео-манифест: первый шаг → следующий шаг → свой путь</p>
        </div>
      </section>

      {/* ДИАГНОЗ — концепция */}
      <section className="concept-section" id="concept-diagnosis">
        <div className="container">
          <SectionHead title={DIAGNOSIS.title} status={DIAGNOSIS.status} />
          <p className="type-body" style={{ maxWidth: 680 }}>
            {DIAGNOSIS.lead}
          </p>
          <div className="diag-grid">
            {DIAGNOSIS.items.map((it) => (
              <div key={it.who} className="card diag-card">
                <div className="diag-who">{it.who}</div>
                <p className="type-body" style={{ margin: 0 }}>
                  {it.text}
                </p>
              </div>
            ))}
          </div>
          <p className="concept-quote">{DIAGNOSIS.quote}</p>
        </div>
      </section>

      {/* ТРАЕКТОРИЯ — концепция */}
      <ChainBlock />

      {/* КОМАНДНАЯ МЕХАНИКА — концепция */}
      <section className="concept-section" id="team-mechanic">
        <div className="container">
          <SectionHead title={TEAM_FLOW.title} status={TEAM_FLOW.status} />
          <div style={{ maxWidth: 720 }}>
            {TEAM_FLOW.steps.map((s, i) => (
              <div key={s} style={{ display: 'flex', gap: 'var(--spacing-md)', alignItems: 'baseline', padding: '10px 0', borderBottom: '1px solid var(--c-border)' }}>
                <span className="type-mono" style={{ color: 'var(--c-accent)' }}>
                  {String(i + 1).padStart(2, '0')}
                </span>
                <span>{s}</span>
              </div>
            ))}
          </div>
          <p className="concept-quote">{TEAM_FLOW.quote}</p>
        </div>
      </section>

      {/* СВОБОДА — концепция */}
      <section className="concept-section" id="freedom">
        <div className="container">
          <SectionHead title={FREEDOM.title} status={FREEDOM.status} />
          <div className="diag-grid">
            {FREEDOM.blocks.map((b) => (
              <div key={b.head} className="card">
                <h3 className="type-h4" style={{ marginTop: 0 }}>
                  {b.head}
                </h3>
                <p className="type-body" style={{ marginBottom: 0 }}>
                  {b.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* SKILL SCORE — концепция */}
      <section className="concept-section" id="skill-score">
        <div className="container">
          <SectionHead title={SKILL_SCORE.title} status={SKILL_SCORE.status} />
          <p className="type-body" style={{ maxWidth: 640 }}>
            {SKILL_SCORE.lead}
          </p>
          <div className="score-grid">
            {SKILL_SCORE.skills.map((s) => (
              <div key={s.name} style={{ display: 'contents' }}>
                <span className="score-name">{s.name}</span>
                <span className="score-val">{s.score}</span>
              </div>
            ))}
          </div>
          <div className="score-counters">
            {SKILL_SCORE.counters.map((c) => (
              <div key={c.label}>
                <div className="num">{c.value}</div>
                <div className="type-caption">{c.label}</div>
              </div>
            ))}
          </div>
          <p className="concept-quote">{SKILL_SCORE.quote}</p>
        </div>
      </section>

      {/* СОЛО-ПОРОГ — предлагаемая механика */}
      <section className="concept-section" id="solo-rule">
        <div className="container">
          <SectionHead title={SOLO_RULE.title} status={SOLO_RULE.status} />
          <p className="type-body" style={{ maxWidth: 640 }}>
            {SOLO_RULE.lead}
          </p>
          <div className="solo-split">
            <div className="solo-yes">
              <p className="type-body" style={{ margin: 0 }}>
                Исполнитель ниже порога самостоятельности?
              </p>
              <p className="solo-verdict">{SOLO_RULE.yes}</p>
            </div>
            <div className="solo-no">
              <p className="type-body" style={{ margin: 0 }}>
                Уже самостоятелен?
              </p>
              <p className="solo-verdict" style={{ color: 'var(--c-text-secondary)' }}>
                {SOLO_RULE.no}
              </p>
            </div>
          </div>
          <p className="type-body" style={{ marginTop: 'var(--spacing-md)', maxWidth: 680 }}>
            {SOLO_RULE.note}
          </p>
          <p className="concept-quote">{SOLO_RULE.quote}</p>
        </div>
      </section>

      {/* КОМПАНИИ — гипотеза */}
      <section className="concept-section" id="companies">
        <div className="container">
          <SectionHead title={COMPANIES.title} status={COMPANIES.status} />
          <div className="diag-grid">
            {COMPANIES.blocks.map((b) => (
              <div key={b.head} className="card">
                <h3 className="type-h4" style={{ marginTop: 0 }}>
                  {b.head}
                </h3>
                <p className="type-body" style={{ marginBottom: 0 }}>
                  {b.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FREEСТАРТ — бренд-блок, концепция */}
      <section className="concept-section" id="brand">
        <div className="container">
          <SectionHead title={BRAND_STORY.title} status={BRAND_STORY.status} />
          <p className="type-body" style={{ maxWidth: 680 }}>
            {BRAND_STORY.main}
          </p>
          <div className="freestart-grid">
            <div className="card">
              <h3 className="type-h4" style={{ marginTop: 0, color: 'var(--c-accent)' }}>
                FREE — свобода
              </h3>
              <ul className="open-list" style={{ margin: 0 }}>
                {BRAND_STORY.free.map((x) => (
                  <li key={x}>{x}</li>
                ))}
              </ul>
            </div>
            <div className="card">
              <h3 className="type-h4" style={{ marginTop: 0 }}>
                START — начало
              </h3>
              <ul className="open-list" style={{ margin: 0 }}>
                {BRAND_STORY.start.map((x) => (
                  <li key={x}>{x}</li>
                ))}
              </ul>
            </div>
          </div>
          <p className="type-h3" style={{ marginTop: 'var(--spacing-xl)' }}>
            {BRAND_STORY.phrase}
          </p>
          <div className="ladder">
            {BRAND_STORY.ladder.map((step, i) => (
              <span key={step} style={{ display: 'inline-flex', alignItems: 'center', gap: 'var(--spacing-sm)' }}>
                {i > 0 && <span className="chain-arrow">→</span>}
                <span className={`ladder-step${i === 0 ? ' first' : ''}`}>{step}</span>
              </span>
            ))}
          </div>
          <p className="concept-quote">{BRAND_STORY.logoNote}</p>
        </div>
      </section>

      {/* ЗАЩИТА ОТ КОПИРОВАНИЯ — концепция */}
      <section className="concept-section" id="moat">
        <div className="container">
          <SectionHead title={MOAT.title} status={MOAT.status} />
          <p className="type-body" style={{ maxWidth: 720, fontSize: '1.05rem' }}>
            {MOAT.text}
          </p>
        </div>
      </section>

      {/* ОТКРЫТЫЕ ВОПРОСЫ — на обсуждение фаундерам */}
      <section className="concept-section" id="open-questions">
        <div className="container">
          <SectionHead title={OPEN_QUESTIONS.title} status={OPEN_QUESTIONS.status} />
          <ol className="open-list">
            {OPEN_QUESTIONS.items.map((q) => (
              <li key={q}>{q}</li>
            ))}
          </ol>
          <p className="type-body" style={{ marginTop: 'var(--spacing-lg)', maxWidth: 720 }}>
            {OPEN_QUESTIONS.pilot}
          </p>
          <p className="type-caption" style={{ marginTop: 'var(--spacing-lg)' }}>
            {BRAND} — концепт-предложение (черновик для обсуждения). Гипотезы и открытые вопросы
            помечены соответствующими статусами и не являются принятыми решениями.
          </p>
        </div>
      </section>
    </main>
  );
}
