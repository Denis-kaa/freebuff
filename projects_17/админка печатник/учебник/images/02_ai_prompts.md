# images/02_ai_prompts.md — промпты генерации иллюстраций для незакрытых слотов

> Альтернатива съёмке (см. `01_shooting_plan.md`): 17 TODO-слотов закрываются
> генерированными **иллюстрациями**. Промпты универсальные (Midjourney / Flux /
> SDXL / DALL-E), на английском — генераторы лучше держат английский.
> Для каждого слота: назначение по-русски + EN-промпт + пропорции.
> После генерации — те же шаги, что и для съёмки (§ «Заливка в реестр»).

## 0. Правила честности (обязательны, без исключений)

1. **Иллюстрация ≠ фото.** Статус в реестре: `READY(AI)`. Подпись в карточке
   и на странице главы начинается со слова **«Иллюстрация:»** и показывает
   принцип, а не «как выглядит у нас».
2. **Provenance.** В карточке реестра: генератор, дата, ссылка на промт
   (этот файл, §-номер). Без этого — не READY.
3. **Никаких брендов и логотипов** в кадре (Canon, Océ, Oracal… — запрещено
   и юридически, и по честности). Все машины — «generic».
4. **Никакого текста в изображении** — генераторы портят буквы; вывески и
   макеты — с пустыми/условными панелями.
5. **Фото > иллюстрация.** Если позже появится реальный кадр слота — фото
   заменяет иллюстрацию, старая остаётся в истории git.
6. Стиль по умолчанию — **чистая предметная фотография/макро** (не арт):
   нейтральный фон, студийный свет, как в `01_shooting_plan.md`.

## 1. Универсальный негатив-промпт (SDXL/Flux; Midjourney — через `--no`)

```
text, letters, caption, watermark, logo, brand name, signature, deformed,
blurry, jpeg artifacts, low quality, cluttered background, human faces
```

## 2. Пропорции

Большинство слотов — `3:2` (Midjourney: `--ar 3:2 --style raw`). Исключения
отмечены в промптах (ролл-ап `2:3`, триптих `16:9`).

---

## 3. Сессия 1 — материалы (макро)

### §3.1 pb-c03 — сетка на просвет
Назначение: гл. 3.3.5 — показать сетку-основу и просвет.
```
Extreme close-up of white PVC banner mesh fabric stretched against bright
soft backlight, visible woven polyester grid with small evenly spaced
perforations letting light through, glossy vinyl coating, dark neutral
background, shallow depth of field, technical material study
```

### §3.2 pb-c04 — ПВХ vs акрил, срезы
Назначение: гл. 3.4.1/3.4.3 — главная пара «пена vs стекло».
```
Side-by-side macro comparison of two sheet material edges standing vertically
on a neutral gray studio table: left a white foamed PVC sheet edge with matte
porous cellular core, right a clear acrylic PMMA sheet edge with glassy
transparent polished finish, aluminum ruler for scale, soft diffused light,
ultra sharp product photography
```

### §3.3 pb-c06 — перфорированная плёнка
Назначение: гл. 3.2.5/9 — устройство One Way Vision.
```
Extreme macro of white perforated one-way vision vinyl film on glass, evenly
spaced round micro-holes in a regular grid, small area of bright printed
graphics on the surface, soft daylight, shallow depth of field, material
texture study
```

### §3.4 pb-m02 — самоклейка: три слоя с торца
Назначение: гл. 3.2.1 — анатомия самоклейки.
```
Macro photo of a white self-adhesive vinyl sheet corner peeled back showing
three separated layers: glossy white vinyl face, shiny tacky adhesive layer
with slight sheen, kraft paper release liner with faint printed grid below,
neutral background, studio product macro
```

### §3.5 pb-m03 — фактура литого баннера
Назначение: гл. 3.3.2 — чем литой отличается от ламинированного.
```
Very close-up texture of a white cast vinyl banner surface, subtle fine
orange-peel coating relief emphasized by soft raking side light, uniform
neutral tone, no text, industrial material study
```

### §3.6 pb-m04 — стопа ПВХ 3/5/10 мм
Назначение: гл. 3.4.1 — толщины как выбор.
```
Three white expanded PVC foam boards of clearly different thicknesses stacked
with cut edges facing the camera, side view, aluminum ruler along the edge for
scale, clean studio background, soft even lighting, product photography
```

### §3.7 pb-m08 — фотобумага глянец vs мат
Назначение: гл. 3.1.6 — выбор покрытия.
```
Two photo paper sheets side by side under angled studio light: left glossy
sheet with a bright specular reflection streak, right matte sheet with fully
diffuse non-reflective white surface, dark neutral background, macro product
comparison
```

## 4. Сессия 2 — производство

### §4.1 pb-e10 — сварной шов баннера
Назначение: гл. 5.8/6 — операция «сварка».
```
Close-up of large format PVC banner welding: an automatic hot-air welding
machine pressing a straight overlap seam joining two white banner panels,
a hand guiding a pressure roller right behind the machine, blurred workshop
background, daylight, documentary style
```

### §4.2 pb-e13 — сублимационный рулонный принтер
Назначение: гл. 5.15/4.5 — класс машины для флаговки.
```
Large format roll-to-roll dye sublimation printer in a clean print shop,
a roll of white polyester fabric mounted and a colorful printed flag fabric
emerging from the output, neutral daylight, generic unbranded machine,
industrial interior
```

### §4.3 бонус — контурная резка, триптих (хвост pb-c10) — `16:9`
Назначение: гл. 6.4а — до/выборка/готово одним кадром.
```
Triptych of the vinyl contour cutting process, three equal panels side by
side: left a white vinyl sheet with faint cut contour lines on a cutting
plotter bed, middle weeding stage with excess vinyl being lifted away by
tweezers revealing cut shapes, right finished die-cut stickers applied to a
glass wall, consistent lighting across panels, clean workshop
```

## 5. Сессия 3 — изделия

### §5.1 pb-i01 — световой короб на фасаде, сумерки
Назначение: гл. 7.5 — зачем подсветка.
```
Small shop storefront at blue hour with a large glowing rectangular lightbox
sign above the entrance, evenly illuminated white panel face, warm light
spilling onto the sidewalk, simple clean architecture, urban street,
architectural photography
```

### §5.2 pb-i04 — панель-кронштейн двусторонняя
Назначение: гл. 7.6 — тип «консоль».
```
Double-sided flat rectangular projecting sign panel mounted on a metal bracket
arm extending from a building wall above a shop entrance, low three-quarter
angle showing the bracket arm and the thin panel edge, daytime, clean European
street, architectural photography
```

### §5.3 pb-i05 — ролл-ап собранный — `2:3`
Назначение: гл. 10 — изделие целиком.
```
Empty white roll-up banner stand fully assembled indoors, visible base cassette
feet, top bar and side support rail, blank white print area, neutral exhibition
hall background, even soft lighting, product photography
```

### §5.4 pb-i09 — брошюра на скрепке, разворот
Назначение: гл. 11.4 — скрепа и разворот.
```
Open A5 saddle-stitched booklet lying flat on a light wooden table, center
metal staples visible along the spine fold, clean layout spread with neutral
placeholder blocks, top-down flat lay, soft daylight
```

### §5.5 pb-i10 — визитки стопой, скругление
Назначение: гл. 11.1 — операция «скругление углов».
```
Stack of thick matte business cards with rounded corners on a dark table,
high angle macro showing the rounded corner radius and clean cut edge of the
stack, shallow depth of field, product photography
```

### §5.6 pb-i12 — кружка после сублимации
Назначение: гл. 13 — результат термопресса.
```
White ceramic mug with a vibrant full-color abstract printed design wrapping
the body, standing on a light table, soft studio lighting, gentle reflection
on the glossy polymer coating, product photography
```

### §5.7 pb-i13 — футболка с DTF-принтом
Назначение: гл. 13 — «аппликация на ощупь».
```
Close-up of a cotton t-shirt laid flat with a vivid full-color DTF transfer
print, the slightly raised glossy transfer film edge visible against the
fabric weave, soft daylight, macro product photography
```

---

## 6. Заливка в реестр после генерации

1. Отобрать 1 кадр на слот (правило «1 файл = 1 слот»), переименовать в якорное
   имя из `00_photo_bank.md`, положить в `учебник/images/`.
2. Реестр: TODO → **READY(AI)**; карточка: подпись из 3 частей, начинающаяся с
   «Иллюстрация:», генератор + дата + ссылка на § этого файла.
3. Главы уже ссылаются якорями `📷 [pb-XXX]` — контент подхватится сам.
4. Коммит по каденции: «фотобанк: AI-иллюстрации — N слотов (генератор …)».

## 7. Что лучше оставить фото

Съёмку в цеху (план `01_shooting_plan.md`) не отменяет: **m04 (реальные толщины),
m02 (реальные слои), e10 (живой шов), i10 (свой тираж)** информативнее любых
рендеров. Иллюстрации — быстрый путь закрыть слоты до съёмки; фото заменяют их
по мере появления (правило §0.5).
