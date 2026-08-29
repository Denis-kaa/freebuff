[SYSTEM INITIALIZED***REMOVED***
ROLE: Prompt Architect 2.0
PIPELINE: Stages 0–8 executed.
STYLE FILTER: ANTI-DUST 2.0 (Active).

---

### STAGE 1 — CRITICAL ANALYSIS
**Главная цель:** Разработать мобильное приложение — 2D планировщик интерьера с генерацией промптов для AI-генераторов.
**Критические уязвимости:**
1. Canvas на мобильных может тормозить при большом количестве объектов.
2. База знаний материалов/мебели требует постоянного обновления.
**Вердикт:** viable. Задача четкая, реализуема на React Native + Skia.

### STAGE 2 — IDEA REFINEMENT
**Исходная идея:** 2D планировщик с drag & drop объектов + генерация промптов.
**Улучшенная версия:**
1. **MVP:** Базовый canvas + минимальная база знаний (10-20 объектов) + экспорт промпта.
2. **V2:** Расширенная база (100+ объектов) + интеграция с магазинами (IKEA API).
3. **V3:** AR-режим (наложение 3D-моделей на камеру).

### STAGE 3 — CONTROL LAYER
- **DEPTH:** deep
- **TOKEN_BUDGET:** high
- **ITERATION_MODE:** off
- **OUTPUT_STRICTNESS:** high
- **CREATIVITY:** low

---

### STAGE 7 — OUTPUT

--- BASE PROMPT ---

**ROLE:** Senior Mobile Developer (React Native) & UX/UI Designer.

**OBJECTIVE:** Design and implement a mobile app (iOS + Android) — a 2D interior planner with AI prompt generation. Users create room layouts by placing furniture/materials on a top-down canvas, then export optimized prompts for Midjourney/Stable Diffusion.

**CONTEXT:**
Target user: interior designer or homeowner who wants to quickly visualize room concepts without 3D modeling. The app must be lightweight, fast, and intuitive (touch-based UI).

**TASK BREAKDOWN:**

1. **Core Architecture:**
   - **Tech Stack:** React Native + `react-native-skia` (for fast canvas rendering) + Redux/Zustand (state management).
   - **Canvas:** Top-down 2D view, zoomable/pannable, touch gestures (drag, pinch, tap).
   - **Data Model:**
     ```
     Project → Room → { dimensions, surfaces (walls/floor/ceiling), objects[***REMOVED*** ***REMOVED***
     Object → { type, model, position {x, y***REMOVED***, size {w, h***REMOVED***, rotation ***REMOVED***
     ```

2. **UI/UX Flow:**
   - **Home Screen:** List of projects (cards) + "+" button to create new room.
   - **Room Editor:**
     - Top bar: room name, dimensions (editable), save/export buttons.
     - Center: 2D canvas (grid background, shows room boundaries).
     - Bottom toolbar: icons for "Walls", "Floor", "Ceiling", "Lighting", "Furniture", "Appliances".
   - **Interaction:**
     - Tap on toolbar icon → opens category menu (bottom sheet).
     - Tap on object in catalog → adds to canvas (default position: center).
     - Drag object → moves it.
     - Double-tap object → opens properties (size, rotation, delete).
     - Pinch canvas → zoom in/out.

3. **Knowledge Base (Templates):**
   - **Materials:**
     - Walls: wallpaper (10 patterns), paint (color picker), wood panels.
     - Floors: laminate (5 colors), tile, linoleum, parquet.
     - Ceilings: suspended, painted, gypsum board.
   - **Furniture (with real dimensions):**
     - Sofas: IKEA Kivik (2.2x0.9m), IKEA Friheten (2.3x0.9m), corner sofa (3x2m).
     - Tables: dining (1.4x0.8m), coffee (1x0.6m), desk (1.2x0.6m).
     - Storage: wardrobe (1.5x0.6m), bookshelf (0.8x0.3m).
   - **Appliances:**
     - Refrigerator: standard (0.6x0.6m), side-by-side (0.9x0.7m).
     - TV: 43" (0.9x0.5m), 55" (1.2x0.7m), 65" (1.4x0.8m).
   - **Lighting:** chandelier, spotlights, floor lamp.

4. **Prompt Generation Logic:**
   - **Input:** Room data (dimensions, surfaces, objects with positions).
   - **Output:** Structured prompt for Midjourney/SD.
   - **Example:**
     ```
     Input: Kitchen 4x3m, brick wallpaper walls, oak laminate floor, white ceiling, IKEA Kivik sofa at (2,1), Samsung fridge at (0.5,0.5).
     Output: "scandinavian kitchen, 4x3 meters, brick pattern wallpaper walls, oak laminate floor, white suspended ceiling, IKEA Kivik sofa in corner, Samsung refrigerator, warm lighting, photorealistic, 8k --ar 4:3 --v 6"
     ```
   - **Logic:** Concatenate room type + surfaces + objects (with relative positions: "in corner", "center", "against wall") + lighting + style modifiers.

5. **Implementation Plan (4 Sprints):**
   - **Sprint 1:** Basic canvas + room creation + drag/drop objects (5-10 items in catalog).
   - **Sprint 2:** Expand catalog (50+ items) + prompt generation + export to clipboard.
   - **Sprint 3:** Add materials (walls/floor/ceiling) + lighting + save/load projects.
   - **Sprint 4:** (Optional) Integrate IKEA API for real furniture models + AR preview.

**OUTPUT FORMAT:**
Provide:
- Architecture diagram (Mermaid.js).
- Data model (TypeScript interfaces).
- UI wireframes (text-based description or Figma link).
- Step-by-step development roadmap with milestones.
- Prompt generation algorithm (pseudocode).

**CONSTRAINTS:**
- Use `react-native-skia` for canvas (not HTML5 Canvas — it's slower on mobile).
- Keep the app under 50MB (optimize assets: use SVG icons, compress images).
- Support offline mode (cache knowledge base locally).
- Do not implement 3D rendering — this is strictly 2D top-down.

**ANTI-HALLUCINATION PROTOCOL:**
- If a specific library version or API endpoint is uncertain, mark it as [UNCERTAIN***REMOVED***.
- Base furniture dimensions on real IKEA/Leroy Merlin data (verify before hardcoding).

--- EXTENSIONS ---

**EXTENSION 1: Анти-галлюцинация**
- проверка пройдена: да.
- корректировки: Жестко зафиксирован стек (React Native + Skia), чтобы разработчик не предложил тяжелые решения (Unity, Flutter).

**EXTENSION 2: Улучшение идеи**
- что изменено: Добавлена структура данных и логика генерации промптов.
- почему: Чтобы разработчик сразу понял, как хранить данные и конвертировать их в промпт.

**EXTENSION 3: Масштабирование**
- Этап 1: MVP с базовым canvas и 10 объектами.
- Этап 2: Расширенная база (100+ объектов) + интеграция с магазинами.
- Этап 3: AR-режим (наложение 3D-моделей на камеру через ARKit/ARCore).
- Этап 4: Экспорт в 3D (генерация .obj/.fbx из 2D-плана).

**EXTENSION 4: Optimization Notes**
- Экономия токенов: Промпт сфокусирован на архитектуре, не требует написания кода.
- Усиление результата: Четкий UI/UX flow + примеры промптов помогут разработчику сразу понять логику.

---

### STAGE 8 — SELF-CRITIQUE
1. **Слабое место:** База знаний материалов/мебели требует ручного обновления (нет автоматического парсинга сайтов магазинов в MVP).
2. **Где модель может ошибиться:** Разработчик может предложить использовать `react-native-canvas` вместо `react-native-skia` (первый медленнее на мобильных).
3. **Что улучшить:** При следующем запуске добавить требование бенчмарка производительности canvas (60 FPS при 50+ объектах).

---

**Итог:** Промпт готов. Можешь передать его разработчику. Если нужно упростить (например, убрать AR и интеграцию с магазинами) — скажи, пересоберу.