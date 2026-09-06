# ROADMAP — TRAJECTORY: система плейсхолдеров с промтами

> **Контекст:** `задача.md` (концепт «Траектория», HTML-прототип + React-архитектура) содержит 3 ссылки на `image.qwenlm.ai` — **эфемерный хост генерации**, ссылки умрут. Плюс 2 слота вообще без изображений (workspace, Tech Blog Article).
> **Задача:** заменить всё на систему плейсхолдеров с готовыми промтами — прототип становится самодостаточным (работает офлайн), а промты = ТЗ для будущей генерации.
> **Дата:** 2026-09-05 · **Статус:** Этап 0 → 4 в этой сессии

---

## 1. Инвентаризация слотов (7 найдено, факт по строкам `задача.md`)

| ID | Расположение | Назначение | Сейчас | Проблема |
|---|---|---|---|---|
| IMG-01 | L513–515, `.hero-bg` | Кинематографичный hero-фон (grayscale, opacity 0.15) | qwenlm.ai URL | эфемерная ссылка |
| IMG-02 | L499, header `.user-profile-mini` | Аватар пользователя 32px | qwenlm.ai URL (**тот же файл, что и hero**) | эфемерная + семантически неверное переиспользование |
| IMG-03 | L561–563, dashboard `data-role="practice"` | Обложка задачи «Ребрендинг "Зерно"» | qwenlm.ai URL | эфемерная ссылка |
| IMG-04 | L635, practice `data-role="workspace"` | Рабочая область загрузки (высота 400px) | пустой div с текстом | нет ни картинки, ни промта |
| IMG-05 | L858, `Data.portfolioItems[0]` | «EcoFarm Landing» (Web) | qwenlm.ai URL | эфемерная ссылка |
| IMG-06 | L859, `Data.portfolioItems[1]` | «Neon Poster Series» (Graphic) | qwenlm.ai URL | эфемерная ссылка |
| IMG-07 | L860, `Data.portfolioItems[2]` | «Tech Blog Article» (Text) | `image: ""` | нет ни картинки, ни промта |

Дополнительно: шаблон рендера портфолио (L989) выводит `<span>No Image</span>` для пустых — заменяется на плейсхолдер с промтом.

## 2. Целевой дизайн системы

### 2.1 Принцип: промт живёт в коде, картинка — опция

```html
<div class="img-placeholder" data-img-id="IMG-01">
  <img src="" alt="" onerror="this.style.display='none'">
  <div class="ph-prompt">[моно-текст промта + метка]</div>
</div>
```

- **Слой 1 (низ):** `.ph-prompt` — всегда виден как fallback: метка `IMG-01`, тип, соотношение сторон и сам промт моноширинным шрифтом (вписывается в editorial-стиль прототипа, как тех-аннотация).
- **Слой 2 (верх):** `<img>` — если `src` задан и загрузился, накрывает промт. `onerror`/пустой `src` → промт остаётся виден.
- **Промты хранятся в `Data.imagePrompts`** (JS-реестр) — единый источник истины; статические слоты получают текст при инициализации, чтобы не дублировать длинные строки в HTML.

### 2.2 CSS-добавки (аддитивно, существующие классы не трогаем)

```css
.ph-prompt { position:absolute; inset:0; display:flex; flex-direction:column;
  align-items:center; justify-content:center; gap:8px; padding:16px;
  background:repeating-linear-gradient(45deg,#ddd,#ddd 8px,#d6d6d6 8px,#d6d6d6 16px);
  z-index:1; }
.ph-tag { font:600 0.65rem var(--font-mono); letter-spacing:.08em;
  border:1px solid #666; padding:2px 6px; text-transform:uppercase; background:#eee; }
.ph-text { font:400 0.68rem/1.4 var(--font-mono); color:#444; max-width:90%;
  text-align:center; white-space:pre-line; }
.img-placeholder img { position:relative; z-index:2; }
```

### 2.3 Единый шаблон промта (все 7 в одном стиле Editorial/Cinematic)

`[тип кадра] + [субъект и действие] + [среда] + [стиль: тёплая бумага #F4F2EE / ink #1A1A1A / burnt sienna #C93D28, швейцарская типографика, editorial] + [свет] + [негативы: no text, no watermark, no childish cartoon] + [параметры: 16:9|1:1|4:3, grayscale для фонов]`

## 3. Этапы

| Этап | Что | Проверка |
|---|---|---|
| **0. Роадмап** (этот файл) | Инвентаризация + дизайн системы | — |
| **1. Инфраструктура** | CSS `.ph-prompt/.ph-tag/.ph-text` + `Data.imagePrompts` + хелпер `PH.init()`/`PH.apply()` в JS | код в `задача.md` без конфликтов классов |
| **2. Статические слоты** | IMG-01 hero, IMG-02 аватар, IMG-03 обложка задачи, IMG-04 workspace — промты + fallback-слой | `data-img-id` × 4, qwen-ссылки в HTML удалены |
| **3. Портфолио** | IMG-05/06/07 — промты в `Data.imagePrompts`, `renderPortfolio()` строит плейсхолдер через общий шаблон | `No Image` заглушка исчезла, все 3 карточки с промтами |
| **4. Валидация** | Счётчики: 7× `data-img-id`, 0× `qwenlm.ai`, HTML-парс без ошибок | grep + python html.parser |
| **5. (будущее) Генерация** | Прогнать 7 промтов через генератор → `assets/img/IMG-0X.png` → вставить `src` | слои `img` накрывают промты |
| **6. React-миграция — Stage 1** ✅ (2026-09-05) | `trajectory/`: канонические типы (`src/types/index.ts`), FSD-скелет (entities/features/widgets/shared/app), реестр промтов → `src/shared/mock/imagePrompts.ts`, алиасы `@entities/*` и т.д. | `tsc --noEmit` strict: clean |
| **7. (Phase 2) React-миграция — state/data** ✅ (2026-09-05) | Zustand store (`app/store.ts`), генератор экосистемы 200/50/100/200 (`shared/mock/generator.ts`, seed-детерминированный), ecoStats, селектор-драфт; smoke 26 инвариантов | `tsc` clean + SMOKE PASSED |
| **8. (Phase 3) React-миграция — UI** ✅ (2026-09-05) | `shared/ui` (theme.css токены из прототипа + `<ImgPlaceholder imgId />`), widgets/dashboard (дашборд подростка), widgets/parent-control (read-only + economy-bar), hash-router (intro/dashboard/parent), App-host с хедером | `tsc` clean + smoke passed |
| **9. (Phase 4a) Драфт — TeamBuilder** ✅ (2026-09-06) | `widgets/team-builder`: пикер навыков (закрытый словарь) + min-level слайдер → скоринг кандидатов (`draft.results` в store), выбор наставника с гейтом размера команды (Expert→5/Senior→4/Pro→3/Junior→1, §8), ростер + «Создать проект» (`createProjectFromTeam`: p-XXXX уникальный id, статус draft/in_progress по правилу наставник+команда); смоук +17 проверок (43 всего) | `tsc` clean + SMOKE PASSED |
| **10. (Phase 4b) Остальной интерактив** | Review Loop (версии + пины на макете), Skill Graph (пульсация >80), Parental Gate UI, TanStack Query | `npm run dev` + e2e-смоук |

## 4. Промты (итоговые формулировки, v1)

- **IMG-01 hero:** `Cinematic wide shot, teenagers working at a shared studio table with laptops and drafting tools, warm paper tones #F4F2EE and ink black, burnt sienna accent light, editorial photography style, swiss composition, natural window light, grayscale background atmosphere, no text, no watermark, 21:9`
- **IMG-02 avatar:** `Minimal editorial portrait of a 17-year-old designer, neutral warm background, confident calm expression, soft daylight, muted palette with burnt sienna accent, square crop 1:1, no text`
- **IMG-03 task cover:** `Brand identity workspace flatlay: logo sketches, typography specimen sheets, warm coffee-house color palette drafts, swiss grid layout, top-down cinematic photography, paper texture, no readable text, 16:9`
- **IMG-04 workspace:** `Clean minimal upload dropzone background: abstract paper texture with subtle swiss grid lines and a burnt sienna corner mark, generous negative space, editorial print aesthetic, no text, 4:3`
- **IMG-05 EcoFarm:** `Modern eco-farm landing page hero visual: greenhouse with young plants, warm morning light, editorial minimalism, muted green and paper tones, no text, 16:9`
- **IMG-06 Neon Poster:** `Poster design mockup on concrete wall: abstract neon geometric shapes, dark background, single burnt sienna accent, swiss typography layout without readable text, cinematic lighting, 4:3`
- **IMG-07 Tech Blog:** `Editorial article illustration: minimal 3D paper abstract shape composition on warm paper background, subtle shadows, ink black and burnt sienna palette, no text, 16:9`

## 5. Границы и правила

- **Additive:** существующие классы `.img-placeholder`, router, State — не переписываются; только новые классы/хелперы и замена `src`-строк.
- Промты — часть кода прототипа → попадут в git при коммите (git = бэкап промтов).
- Документ регистрируется в MANIFEST.md проекта (индекс документов).
