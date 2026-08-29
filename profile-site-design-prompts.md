# Промты и визуальное направление сайта Дениса Литвинова

## Цель

Создать визуальные материалы для гибридного портфолио AI-инженера и **Visual Systems Creator**. Изображения должны показывать не абстрактный «AI magic», а системность: связи, слои, проверку, данные, интерфейсы и превращение идеи в работающий продукт.

## Арт-дирекшн

- настроение: matte obsidian, immersive, tactile, quiet premium;
- палитра: почти чёрный обсидиан, графит, мокрый камень, приглушённый jade/cyan, редкий amber;
- поверхность: матовая, слегка зернистая, без дешёвого glossy glassmorphism;
- свет: мягкий направленный, volumetric, тонкие отражения по граням;
- композиция: много воздуха, editorial grid, крупные формы и понятный визуальный фокус;
- motion-friendly: оставлять спокойные зоны и ясные контрастные края, чтобы изображения хорошо работали с reveal/parallax;
- исключить: роботов, мозги, неоновые киберпанк-сети, случайный код, читаемый псевдотекст, логотипы брендов, лица без разрешения, обещания «полной автономности».

## Общий negative prompt

`neon cyberpunk, glossy plastic, excessive glassmorphism, busy composition, random unreadable text, fake logos, humanoid robot, glowing brain, sci-fi cliché, oversaturated colors, stock photo smile, watermark, UI text, low contrast, distorted geometry, extra limbs, duplicated objects`

## Prompt 1 — Hero: Idea → System

`Cinematic abstract editorial illustration for a personal AI systems portfolio, a single matte obsidian monolith opening into four precise internal layers: idea, model, validation, product, subtle jade and warm amber edge light, tactile volcanic stone texture, dark graphite background, quiet premium art direction, large negative space on the left for headline, centered right-side composition, soft volumetric light, no text, no logos, 16:9`

## Prompt 2 — Freebuff / Workspace OS

`Abstract product architecture visualization, layered obsidian workspace with interconnected memory strata, small luminous nodes representing context, RAG, model routing, MCP and orchestration, restrained jade/cyan accents, matte mineral material, precise editorial composition, technical but human, dark background, no readable labels, no logos, 4:3`

## Prompt 3 — Production stabilization

`Visual metaphor for stabilizing a complex media processing pipeline, chaotic broken translucent fragments becoming one clean continuous matte-black flow through five controlled stages, subtle amber checkpoints and jade validation marks, premium technical editorial style, dark obsidian palette, no people, no text, no logos, 4:3`

## Prompt 4 — Investment analytics

`Abstract data visualization for an investment analytics platform, irregular CSV and spreadsheet fragments entering a calm geometric obsidian dashboard landscape and becoming ordered constellations, muted jade, amber and graphite palette, tactile matte surfaces, high-end editorial technology illustration, no numbers, no text, no logos, 4:3`

## Prompt 5 — Visual Systems Creator

`Editorial still life of a visual systems creator's desk: matte obsidian cards, typographic grid sheets without readable text, color swatches in graphite jade amber, wireframe fragments and a small architectural model, soft side light, understated premium design studio atmosphere, no hands, no logos, no readable text, 3:2`

## Prompt 6 — Creative Lab

`Atmospheric abstract scene combining a dark literary room, a thin glowing crack, guitar-string-like lines and an architectural star map, matte obsidian and warm bronze, psychological depth, restrained cinematic lighting, poetic but minimal, generous negative space, no text, no people, no logos, 3:2`

## Prompt 7 — Social preview / OG image

`Minimal premium social preview for Denis Litvinov, matte obsidian field with a single geometric jade line transforming into a structured system diagram, subtle amber point of light, strong contrast, empty space for later typography overlay, no text, no logo, 1200x630`

## Правила использования изображений

1. Генерировать изображения без встроенного текста; заголовки добавлять в HTML/CSS.
2. Хранить оптимизированные WebP/AVIF-версии в `assets/images/`.
3. Для hero использовать `loading="eager"`, для остальных изображений — `loading="lazy"`.
4. Обязательно добавить `alt`-описания и `prefers-reduced-motion` режим.
5. До генерации можно использовать аккуратные remote placeholders, но перед публичным релизом заменить их на собственные или проверить лицензию.

## Референсы и rationale

- [Figma — Portfolio website examples***REMOVED***(https://www.figma.com/resource-library/portfolio-website-examples/) — структура портфолио, ясность кейсов и иерархия.
- [Awwwards — Portfolio websites***REMOVED***(https://www.awwwards.com/websites/portfolio/) — референсы арт-дирекшна и motion, использовать выборочно, не копировать эффектность в ущерб скорости.
- [Product Design Portfolios***REMOVED***(https://www.productdesignportfolios.com/) — способы показывать problem/solution/result.
- [Site Builder Report — Motion design portfolios***REMOVED***(https://www.sitebuilderreport.com/inspiration/motion-design-portfolios) — идеи для переходов и case-preview.
- [IxDF — Visual Design***REMOVED***(https://ixdf.org/courses/visual-design-the-ultimate-guide) — базовые принципы композиции, цвета, типографики и сеток.
- [Figma — Web design trends***REMOVED***(https://www.figma.com/resource-library/web-design-trends/) — актуальные направления; glassmorphism применять умеренно и проверять контраст.
- [UX Design — accessibility concerns with glassmorphism***REMOVED***(https://uxdesign.cc/the-most-popular-experience-design-trends-of-2026-3ca85c8a3e3d) — учитывать проблемы читаемости прозрачных поверхностей.

## Карточки дизайнерских навыков

Показывать не титул «профессиональный дизайнер», а наблюдаемые capability:

- **Visual direction** — палитра, атмосфера, визуальная метафора и единый арт-дирекшн;
- **Interface composition** — сетка, иерархия, ритм, responsive-композиция;
- **Interaction design** — понятные состояния, раскрытия, фильтры и feedback;
- **Motion design** — reveal, easing, parallax, transition choreography без перегруза;
- **Design systems** — токены, повторяемые компоненты, консистентность;
- **AI-assisted visual prototyping** — быстрый переход от идеи к визуальному прототипу с последующей ручной проверкой.

Уровень формулировать как `Applied / portfolio-proven`, пока нет отдельной профессиональной истории в дизайне.
