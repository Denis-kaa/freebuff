# Freeстарт — концепт-презентация + интерактивный макет

> Продуктовое имя: **Freeстарт** (Free латиницей + старт кириллицей). «Траектория» — концептуальное описание направления, НЕ название проекта (pompts_11/122.md §3).

React-приложение: концепт-презентация по `FreeStart_Concept.docx` + интерактивный макет экосистемы (миграция концепта «Траектория» из `../задача.md`).

## Статус Freeстарт-рework (pompts_11/122.md, готово)

- **Концепт-презентация** — `widgets/concept-view` + `shared/concept/content.ts` (единственный источник текстов). Все блоки из документа: диагноз → видение/траектория → командная механика → свобода (нет «владельца») → Skill Score → соло-порог → компании → бренд-блок → защита от копирования → открытые вопросы. Каждый блок несёт статус-бейдж: **концепция / механика / гипотеза / открытый вопрос** — гипотезы не выдаются за принятые решения (§1/§7 промта).
- **Брендинг** — хедер: аутентичный знак, извлечённый из промо-кадра (`public/logo-mark.png`, alpha-keying уголка `media/promo.jpg`) + текстовый воркмарк «Freeстарт_» (сиенна-акцент). Favicon/иконки: `favicon-32.png`, `icon-192.png`, `apple-touch-icon.png` (знак на paper-плитке), `icon-192-dark.png` (инверсия), `logo-ink-512.png` (мастер). Черновые SVG-варианты удалены — используется существующий рабочий знак (§3: «не изобретать заново»).
- **Медиа** — `public/media/promo.jpg` (промо-кадр 1380×752 в hero) и `public/media/concept.mp4` (видео-манифест 10s): автовоспроизведение muted+loop+playsInline, poster `concept-poster.jpg`, controls, `<source>`-fallback со ссылкой на файл (§5: корректное воспроизведение и деградация).
- **index.html** — title/description/OG, favicon-связки, theme-color.

## Статус Stage 1 (готово)

- `src/types/index.ts` — канонические доменные типы (Freelancer/Mentor/Client/Parent, Project/Task, Skill Score, Proof, ParentalConsent, BudgetDistribution, imagePrompts-модель).
- FSD-скелет: `entities/{user,project,task,skill}`, `features/{team-builder,review-system,skill-tree}`, `widgets/{dashboard,parent-control}`, `shared/{api,mock}`, `app/`.
- `shared/mock/imagePrompts.ts` — реестр промтов IMG-01..07, перенесён 1:1 из прототипа.

## Статус Phase 2 (готово)

- `shared/mock/rng.ts` — сидированный PRNG (mulberry32): same seed ⇒ same ecosystem.
- `shared/mock/generator.ts` — детерминированная генерация 200 фрилансеров / 50 менторов / 100 клиентов / 200 проектов + задачи команд (IDs per-prefix: `f-0001` всегда первый фрилансер).
- `shared/mock/ecoStats.ts` — статистика экосистемы (оборот, доли 51/20/20/9, топы, skillCounts).
- `app/store.ts` — Zustand store + селекторы (`selectStats`, `selectCurrentUser`, `selectCandidates` — прообраз драфта, `selectTasksOfUser`).
- `scripts/smoke.ts` — 26 инвариантов генератора и селекторов: **SMOKE PASSED**.

Ещё нет (Phase 4+): TeamBuilder UI, Review Loop, Skill Graph, Parental Gate UI, React Router v6, TanStack Query.

## Статус Phase 3 (готово)

- `shared/ui/theme.css` — дизайн-токены прототипа (paper/ink/sienna, типографика, кнопки, badges, economy-bar).
- `shared/ui/ImgPlaceholder.tsx` — React-компонент плейсхолдеров: промт-слой снизу, `<img>` сверху (registry IMG-01..07).
- `widgets/dashboard` — дашборд подростка: статус-хедер, активная задача (прогресс, награда, обложка-плейсхолдер), лента доказательств, навыки, предложения драфта.
- `widgets/parent-control` — read-only родительский вид: безопасность, финансы с economy-bar 51/20/20/9, история проектов.
- `app/router.ts` — hash-роутер (intro/dashboard/parent), `app/App.tsx` — хост с хедером (оборот экосистемы, аватар-плейсхолдер).

## Статус Phase 4a — TeamBuilder (готово)

- `app/store.ts` — draft-состояние (requiredSkills, minLevel, mentorId, invitedIds) + скоринг кандидатов (`results`: только те, у кого ВСЕ выбранные навыки ≥ порога, ранжирование по среднему уровню); действия `toggleSkill/setMinLevel/pickMentor/toggleInvite/createProjectFromTeam`.
- `widgets/team-builder` — интерфейс драфта: пикер навыков (закрытый словарь `SKILL_NAMES`), слайдер минимального уровня, выбор наставника с **гейтом размера команды** (Expert→5 / Senior→4 / Pro→3 / Junior→1, concept §8; без наставника — соло-лимит 1), ростер и «Создать проект» (уникальный `p-XXXX`, статус `draft`/`in_progress` по правилу «наставник + команда»).
- `app/router.ts` — новый вид `#team`, навигация в `App.tsx`.
- Smoke расширен до **43 инвариантов** (+17: скоринг, кэп, дедупликация приглашений, создание проекта, сброс драфта, соло-режим).

## Статус Phase 4b — Ревью-луп (готово)

- `app/store.ts` — стейт-машина ревью: `submitVersion` (только из `in_progress`/`changes_requested`, авто-нумерация v1..vN → `submitted`), `startReview` (`submitted` → `in_review`), `addReviewNote` (пин `{area, note, authorId}` на последнюю версию, только в `in_review`, пустые отклоняются), `requestChanges` / `approveTask` (→ `done`, progress 100). Селекторы: `selectReviewQueue` (все задачи цикла с контекстом), `selectTaskDetail`.
- `widgets/review-loop` — очередь + карточка задачи: история версий (новые сверху) с пинами, форма сабмита версии, зоны пинов A–F над превью, менторские действия. Новый вид `#review` в роутере и навигации.
- Smoke расширен до **58 инвариантов** (+15: гейты стейт-машины на каждый неверный переход, пины, аппрув, null-safety селектора).

## Статус Phase 4c — Parental Gate (готово)

- **Генератор:** 100 родителей (по 2 детей — точное разбиение 200 подростков) + стартовый консент `platform_rules` на каждого ребёнка. `Rng.hex()` — детерминированные токены (сид сохранён).
- **Тип `ParentalConsent`:** lifecycle `pending → granted | denied` (по одному консенту на (подросток, проект)), `granted → revoked`; токен выдаётся только при grant, не при запросе.
- **Store:** `requestConsent` (идемпотентен: активный/pending побеждает), `grantConsent`, `denyConsent`, `revokeConsent`; **гейт в `approveTask`** — аппрув без активного `project_payment`-консента отклоняется (деньги не двигаются, concept Часть 1 §5). Селекторы: `selectConsentInbox` (pending/active/history с контекстом), `selectConsentForProject`.
- **`widgets/parent-control`:** консент-инбокс — выдача/отказ/отзыв согласия; это единственная action-поверхность родителя, остальное остаётся read-only (concept §1).
- Smoke: **82 инварианта** (+24: гейт без/pending/после отказа/после отзыва, идемпотентность, токены, инбокс, разбиение родителей).

## Запуск

```bash
npm install
npm run typecheck   # tsc --noEmit
npm run smoke       # node --experimental-strip-types scripts/smoke.ts (82 проверки)
npm run dev         # vite
npm run build       # прод-сборка в dist/
```

> **Termux/sdcard caveat:** `/sdcard` (FUSE) не поддерживает symlink → `npm install` в этой папке падает.
> Для проверки типов скопируйте `src/` + `tsconfig.json` в ext4-каталог (например `~/.cache/`),
> поставьте `typescript` + `@types/react` + `@types/react-dom` и запустите `tsc --noEmit` там.
> `node_modules/` в репозиторий не попадает (.gitignore).
