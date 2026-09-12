"""Редактируемые цены доп. работ wide — runtime-слой над каноническим конфигом.

Решение Дениса (2026-09-12, РОАДМАП_v7 §10 / ревью OP-22): цены доп. работ —
настраиваемый параметр; цифры вносит владелец, код цен не содержит. Канонический
конфиг (`printcalc/calculators/wide/config.py`) остаётся замороженным каноном
(golden-тесты закрепляют значения); этот модуль накладывает ПОВЕРХ него
переопределения cost/sell по ИМЕНИ работы из YAML-файла владельца:

    /opt/printcalc/data/wide_prices.yaml   (или $PRINTCALC_WEB_PRICES)

Формат файла (переопределение ПО ИМЕНИ канонической работы, closed vocab —
ANTI-6b; неизвестное имя — loud-ошибка при загрузке, не silent-игнор):

    works:
      Плоттерная резка:
        sell: 500.0        # обязательный-хотя-бы-один ключ; cost опционален
        cost: 100.0

Дизайн-принципы:
- Ничего не ломается, когда файла нет (аддитивность): канонические дефолты
  используются как есть.
- Ошибки владельца — громкие: неизвестное имя работы, неизвестный ключ,
  отрицательная цена или не-число → PriceConfigError при загрузке.
- Кэш по sha256 содержимого: сервис перечитывает файл без рестарта после
  правки владельцем (mtime недостаточно: правка равной длины в пределах
  гранулярности mtime не меняла бы отпечаток).
- PyYAML — опциональная зависимость (урок Этапа 6): без yaml импорт модуля
  проходит, а загрузка существующего файла поднимает понятную ошибку.
"""

from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path

from printcalc.calculators.wide.config import WideConfig, WorkPrice

#: Имя override-файла в data/ (см. default_prices_path).
PRICES_FILENAME = "wide_prices.yaml"

#: Env-переопределение пути (паритет PRINTCALC_WEB_DB, CODE_QUALITY 4.7).
PRICES_ENV_VAR = "PRINTCALC_WEB_PRICES"

#: Разрешённые числовые поля записи.
_PRICE_KEYS = ("cost", "sell")

#: Модульный кэш: путь → (отпечаток, конфиг). Один файл на инстанс — намеренно.
_CACHE: dict[Path, tuple[bytes, WideConfig]] = {}


class PriceConfigError(RuntimeError):
    """Громкая ошибка конфигурации цен (владелец ошибился в YAML)."""


def default_prices_path() -> Path:
    """Путь override-файла: env PRINTCALC_WEB_PRICES или <корень printcalc>/data/wide_prices.yaml.

    Корень определяется от этого файла (src/printcalc_web → parents[2] — корень
    printcalc), паритет default_db_path() (db.py).
    """
    env_path = os.environ.get(PRICES_ENV_VAR)
    if env_path:
        return Path(env_path)
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "data" / PRICES_FILENAME


def get_wide_config(path: Path | None = None) -> WideConfig:
    """Канонический WideConfig + переопределения cost/sell из YAML-файла владельца.

    Файла нет → канон без изменений. Файл есть → merge по имени с громкой
    валидацией (PriceConfigError). Кэш по (mtime_ns, size) — правка владельцем
    подхватывается без рестарта сервиса.
    """
    file_path = default_prices_path() if path is None else Path(path)
    if not file_path.exists():
        # Файла нет — канон 1:1. Даже env-путь допустим отсутствующим:
        # владелец ещё не завёл файл.
        return WideConfig()

    stamp = _stamp(file_path)
    cached = _CACHE.get(file_path)
    if cached is not None and cached[0] == stamp:
        return cached[1]

    overrides = _load_overrides(file_path)
    merged = _merge(WideConfig(), overrides, source=file_path)
    _CACHE[file_path] = (stamp, merged)
    return merged


def _stamp(path: Path) -> bytes:
    """Отпечаток файла для кэша — sha256 содержимого.

    Не mtime/size: правка равной длины (500.0 → 600.0) в пределах гранулярности
    mtime файловой системы не меняла бы отпечаток и кэш отдавал бы устаревшую
    цену. Файл крошечный (десятки байт) — чтение на каждый расчёт ничтожно;
    кэш экономит разбор YAML, а не чтение файла.
    """
    import hashlib

    return hashlib.sha256(path.read_bytes()).digest()


def _load_overrides(path: Path) -> dict[str, dict[str, float]]:
    """Разбирает YAML-файл → {имя работы: {cost/sell: float}}. Все ошибки — громкие."""
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - окружение без PyYAML
        raise PriceConfigError(
            f"Файл {path} присутствует, но PyYAML не установлен "
            f"(pip install 'PyYAML>=6' в venv сервиса)."
        ) from exc

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise PriceConfigError(f"Файл {path} не читается как YAML: {exc}") from exc

    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise PriceConfigError(
            f"Файл {path}: ожидался словарь с ключом 'works' (словарь работ), "
            f"получено: {type(raw).__name__}."
        )
    works = raw.get("works")
    if works is None:
        # Шаблон скопирован, но ни одна работа не раскомментирована —
        # это валидное «переопределений пока нет» (канон 1:1), не ошибка.
        return {}
    if not isinstance(works, dict):
        raise PriceConfigError(
            f"Файл {path}: ключ 'works' должен быть словарём работ, "
            f"получено: {type(works).__name__}."
        )

    overrides: dict[str, dict[str, float]] = {}
    for name, entry in works.items():
        if not isinstance(entry, dict):
            raise PriceConfigError(
                f"Файл {path}: запись работы '{name}' должна быть словарём "
                f"с ключами {'/'.join(_PRICE_KEYS)}."
            )
        parsed: dict[str, float] = {}
        for key, value in entry.items():
            if key not in _PRICE_KEYS:
                raise PriceConfigError(
                    f"Файл {path}: неизвестный ключ '{key}' у работы '{name}' "
                    f"(разрешены {'/'.join(_PRICE_KEYS)})."
                )
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise PriceConfigError(
                    f"Файл {path}: '{key}' у работы '{name}' должен быть числом, "
                    f"получено: {value!r}."
                )
            if value < 0:
                raise PriceConfigError(
                    f"Файл {path}: '{key}' у работы '{name}' не может быть отрицательным."
                )
            parsed[key] = float(value)
        if not parsed:
            raise PriceConfigError(
                f"Файл {path}: запись работы '{name}' пуста — укажите cost и/или sell."
            )
        overrides[str(name)] = parsed
    return overrides


def _merge(
    base: WideConfig,
    overrides: dict[str, dict[str, float]],
    source: Path,
) -> WideConfig:
    """Накладывает переопределения на канон. Неизвестное имя — loud PriceConfigError."""
    known = {w.name for w in base.works}
    unknown = sorted(name for name in overrides if name not in known)
    if unknown:
        raise PriceConfigError(
            f"Файл {source}: неизвестные работы {unknown}; "
            f"допустимые имена: {', '.join(w.name for w in base.works)}."
        )
    merged_works: list[WorkPrice] = []
    for work in base.works:
        ov = overrides.get(work.name)
        if ov is None:
            merged_works.append(work)
            continue
        merged_works.append(
            replace(
                work,
                cost=ov.get("cost", work.cost),
                sell=ov.get("sell", work.sell),
            )
        )
    return replace(base, works=tuple(merged_works))


__all__ = [
    "PRICES_ENV_VAR",
    "PRICES_FILENAME",
    "PriceConfigError",
    "default_prices_path",
    "get_wide_config",
]
