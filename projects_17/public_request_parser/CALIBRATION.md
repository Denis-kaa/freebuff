# CALIBRATION — P14 (feedback → thresholds)

> **Статус:** implemented locally, deterministic
> **Версия:** 0.1.0
> **Граница:** рекомендация не применяется автоматически; apply — явное действие.

## Назначение

Связать накопленный `feedback` (relevant/irrelevant) с порогами матчера:
для публикаций с feedback берётся сохранённая `MatchDecision.score`, строится
выборка (score, label), и подбирается порог accept, максимизирующий accuracy.
Это закрывает P14-ветку «calibration» без авто-изменений и без LLM.

## API

### `ThresholdCalibrator(storage, *, min_samples=3)`

```python
result = calibrator.calibrate(profile)
# -> CalibrationResult | None (None при samples < min_samples)
```

### `CalibrationResult`

| Поле | Смысл |
|---|---|
| `samples / positive / negative` | размер и состав выборки |
| `current_accept / suggested_accept` | текущий и рекомендуемый порог accept |
| `current_pending / suggested_pending` | то же для pending (= accept × 0.5) |
| `precision_at_suggested / recall_at_suggested` | метрики на рекомендуемом пороге |
| `changed` | совпадает ли рекомендация с текущим профилем |
| `summary()` | строка CLI/report (`calibration[CHANGE|KEEP***REMOVED*** ...`) |

### `optimal_accept_threshold(samples)`

Порог, максимизирующий accuracy; кандидаты — сами наблюдаемые score
(детерминированно, без ранжирующих моделей).

## Данные

- `storage.list_feedback(owner_scope)` — feedback-записи владельца;
- `storage.get_decision(publication_key, profile_id, version)` — score решения;
- записи feedback без сохранённого decision **исключаются** из выборки.

## Применение (не автоматическое)

1. Оператор получает `CalibrationResult` (CLI/отчёт).
2. При `changed=True` обновляет профиль `accept_threshold`/`pending_threshold`
   через `storage.save_profile()` новой версии (version+1).
3. Старая версия профиля и её decisions сохраняются — откат возможен.

## Проверки

```bash
cd projects_17/public_request_parser
PYTHONPATH=. python -m pytest tests/test_calibration.py -q
python -m mypy app tests --strict
```

## Не закрыто P14

- ranking внутри accepted (за пределами порогов);
- per-source калибровка (сейчас per-owner+profile);
- авто-применение — запрещено по дизайну (explainability, откат).