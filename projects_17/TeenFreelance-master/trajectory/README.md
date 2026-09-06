# trajectory — TRAJECTORY React app (Stage 1)

React-миграция концепта «Траектория» (`../задача.md`), Этапы 1–2 из системного промта: типы + Feature-Sliced Design скелет.

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

## Запуск

```bash
npm install
npm run typecheck   # tsc --noEmit
npm run smoke       # node --experimental-strip-types scripts/smoke.ts (43 проверки)
npm run dev         # vite
```

> **Termux/sdcard caveat:** `/sdcard` (FUSE) не поддерживает symlink → `npm install` в этой папке падает.
> Для проверки типов скопируйте `src/` + `tsconfig.json` в ext4-каталог (например `~/.cache/`),
> поставьте `typescript` + `@types/react` + `@types/react-dom` и запустите `tsc --noEmit` там.
> `node_modules/` в репозиторий не попадает (.gitignore).
