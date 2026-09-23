# PHASE_H4_REPORT.md — H4: diff между генерациями + summaries.json

> **Статус:** COMPLETE · **Дата:** 2026-09-16
> **Этап:** H4 потока B (Reports Hub) · РОАДМАП_v7 §7 · reports-hub-spec.md §14.4 (тесты 4, 8)
> **Верификация:** 65 passed (H1–H4 отчётные сьюты; было 40 → +25) · mypy clean (22 файла) · живая генерация: 13 проектов / 229 доков / history для всех

---

## 1. Что сделано

| Артефакт | Файл | Суть |
|---|---|---|
| Diff-слой | `report/diff.py` | `MetricChange` + `ModelDiff` (timeline_added, docs_added/removed, metric_changes, new/removed_sections, item_deltas; `summary()` «+2 этапов · тесты 249→261 · +1 новых доков», `has_changes()`, `to_json()`) · `diff_models(current, previous)` посекционно · `save_history` атомарно (tmp → `os.replace`) / `load_history` (битый файл, будущая schema_version → None) |
| Проводка генерации | `report/generate.py` | `generate_site`: перед записью модели — `load_history` → `diff_models`, после — `save_history`; `GenerateResult.diffs` + `SiteModel.diffs` (slug → ModelDiff) |
| Рендер | `report/render.py` | `render_project_page(model, diff)` — блок «Изменения» под «Кратко» (`_diff_block`: diff-block + NEW-бейдж / «первая генерация» / «без изменений»); главная — diff-строка на карточке + NEW-бейдж; manifest.json — `diffs`-агрегат (спека §8) |
| CSS | `design/tokens.py` | `.diff-block` (card-фон, левая полоса accent-good), `.badge-new` уже был |
| CLI | `cli.py` | `diff` — вместо заглушки: history vs текущие модели, печать «slug → сводка», `--project`/`--projects-root`; сайт не пишет |
| Override-файл | `summaries.json` | Коммитится рядом с кодом (спека §9): exec-резюме печатника, schema_version=1 |

## 2. Тесты спеки (12 новых)

**Тест 4 `test_reports_hub_diff.py` (15):** first_generation; изменения (timeline_added=2, docs_added, метрика 249→261, item_deltas); формат сводки; удалённые доки → `has_changes()` + «−1 доков»; идентичные модели → «без изменений»; `to_json`-контракт; history round-trip + битый JSON + schema_version=999 → None; рендер (diff-block + NEW в странице, отсутствие блока без diff, NEW-бейдж на главной); сквозной e2e: две генерации подряд — первая «первая генерация», вторая «без изменений»; history-файл переживает регенерацию.

**Тест 8 `test_reports_hub_summaries.py` (10):** приоритет override > фолбэка; отсутствие ключа → фолбэк; `orphans()`/`used()`; from_file (ок, не-dict, битый JSON → пустой override); пропуск пустых/не-строковых значений; DeterministicProvider passthrough; e2e: сирота в `result.diagnostics` («осиротевшие ключи summaries») + override в HTML проекта; нет сирот → нет диагностики; отсутствующий файл → no-op.

## 3. Решения по ходу (и почему)

1. **`diff.py` был повреждён посреди записи** (def внутри return-словаря) — перезаписан целиком по восстановленным фрагментам; structure фиксируется тестом 4.
2. **Duck-typing в рендере:** существующий HTML-escape тест подаёт заглушку SiteModel без `diffs` → `getattr(site, "diffs", {})` вместо ломающего `AttributeError`. Поле dataclass имеет default, заглушки — валидные потребители.
3. **`history_path` под `slugify()`** — консистентно со слагами страниц (`site/data/history/adminka-pechatnik.json`).
4. **manifest-агрегат diffs** добавлен (спека §8 требует его явно), ключи отсортированы — стабильный JSON для diff'а самого манифеста.
5. **CLI `diff` не пишет сайт** — показывает, что изменится при следующей генерации; запись только через `generate`.
6. **Сохранение history сразу после build** (не после write_site): сбой рендера не теряет факт успешного сравнения; файл всё равно перезапишется следующей генерацией.

## 4. Живая генерация (FACT, whimco)

```
generate --all → 13 проектов · 229 страниц доков
diff --project "админка печатник" → adminka-pechatnik: без изменений (после 2-й генерации)
site/data/history/ → 13 JSON-файлов
Страница печатника: diff-блок «Изменения: первая генерация» + override-резюме из summaries.json
manifest.json: "diffs": {13 слагов → to_json()}
```

## 5. Что НЕ входит (следующие этапы)

- **H5:** сервер (token-гейт 401/200, raw/zip) + отчёт платформы (`--platform`) + тест 7.
- **H6:** systemd `reports-hub.service` (:8310) + деплой + смоук.
- Бейдж «тяжёлый» карточек — уже в H3; NEW-подсветка самих пунктов roadmap (сейчас — сводка) — кандидаты в доработку по эксплуатации.
