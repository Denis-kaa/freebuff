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

Ещё нет (Phase 3+): UI-виджеты, React Router, TanStack Query, TeamBuilder UI.

## Запуск

```bash
npm install
npm run typecheck   # tsc --noEmit
npm run smoke       # node --experimental-strip-types scripts/smoke.ts (26 проверок)
npm run dev         # vite
```

> **Termux/sdcard caveat:** `/sdcard` (FUSE) не поддерживает symlink → `npm install` в этой папке падает.
> Для проверки типов скопируйте `src/` + `tsconfig.json` в ext4-каталог (например `~/.cache/`),
> поставьте `typescript` + `@types/react` + `@types/react-dom` и запустите `tsc --noEmit` там.
> `node_modules/` в репозиторий не попадает (.gitignore).
