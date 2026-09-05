# trajectory — TRAJECTORY React app (Stage 1)

React-миграция концепта «Траектория» (`../задача.md`), Этапы 1–2 из системного промта: типы + Feature-Sliced Design скелет.

## Статус Stage 1

- `src/types/index.ts` — канонические доменные типы (Freelancer/Mentor/Client/Parent, Project/Task, Skill Score, Proof, ParentalConsent, BudgetDistribution, imagePrompts-модель).
- FSD-скелет: `entities/{user,project,task,skill}`, `features/{team-builder,review-system,skill-tree}`, `widgets/{dashboard,parent-control}`, `shared/{api,mock}`, `app/`.
- `shared/mock/imagePrompts.ts` — реестр промтов IMG-01..07, перенесён 1:1 из прототипа.
- `app/App.tsx` — минимальный root, доказывающий сборку слоёв через алиасы.

Ещё нет (Phase 2+): UI, Zustand store, генератор 350 пользователей, React Router, TanStack Query.

## Запуск

```bash
npm install
npm run typecheck   # tsc --noEmit
npm run dev         # vite
```

> **Termux/sdcard caveat:** `/sdcard` (FUSE) не поддерживает symlink → `npm install` в этой папке падает.
> Для проверки типов скопируйте `src/` + `tsconfig.json` в ext4-каталог (например `~/.cache/`),
> поставьте `typescript` + `@types/react` + `@types/react-dom` и запустите `tsc --noEmit` там.
> `node_modules/` в репозиторий не попадает (.gitignore).
