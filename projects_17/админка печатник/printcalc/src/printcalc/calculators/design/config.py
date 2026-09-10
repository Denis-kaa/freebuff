"""Канонический прайс-лист дизайна — дословный перенос из legacy-исходника.

Источник: «Калькулятор макетов/design_calc.py», build_prices() (строки 15–33).
Legacy-калькулятор НЕ СЧИТАЕТ формулой: цена = позиция прайса, найденная по
тройке (услуга, сторона 4+N, вариант/уровень); price == 0 → «Цена по запросу»
(Вывеска), нет совпадения → «по договорённости». Наценка/налог/тираж
отсутствуют — parity сохранён (price == price_no_tax, profit = 0).
Golden-тесты закрепляют значения: менять только осознанно, новой редакцией.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Уровни/варианты прайса (legacy UI-селекты macro_level/print_side).
LEVELS: tuple[str, ...] = ("Простой", "Средний", "Сложный")
WIDE_LEVELS: tuple[str, ...] = ("Простой", "Стандарт", "Премиум")


@dataclass(frozen=True)
class DesignPriceItem:
    """Одна позиция прайса (элемент legacy price_list)."""

    name: str
    option: str  # вариант/уровень («» = без варианта)
    category: str
    price: int  # 0 = «Цена по запросу»


def build_prices() -> tuple[DesignPriceItem, ...]:
    """Канонический прайс — порт build_prices() 1:1 (порядок сохранён)."""
    prices: list[DesignPriceItem] = []

    # Дизайн Вёрстка (строка 17).
    for name, price in (
        ("Вёрстка каталога / журнала (за полосу)", 455),
        ("Вёрстка книги (простой текст, ч/б за полосу)", 65),
        ("Вёрстка книги с иллюстрациями (за полосу)", 220),
        ("Вёрстка презентации (за страницу)", 750),
        ("Дизайн обложки книги / журнала", 4000),
        ("Вёрстка меню (за полосу)", 455),
    ):
        prices.append(DesignPriceItem(name, "", "Дизайн Вёрстка", price))

    # Дизайн Логотип и стиль (строки 18–19).
    logo: list[tuple[str, dict[str, int]]] = [
        ("Отрисовка логотипа по эскизу", {"Простой": 500, "Стандарт": 750, "Премиум": 1250}),
        ("Доработка / редизайн логотипа", {"Простой": 1000, "Стандарт": 1500, "Премиум": 2250}),
        ("Разработка логотипа (2 варианта)", {"Простой": 2500, "Стандарт": 3200, "Премиум": 3900}),
        ("Разработка логотипа (3+ варианта)", {"Премиум": 7000}),
        ("Логотип + базовый фирменный стиль", {"Премиум": 15000}),
        ("Фирменный стиль (полный набор)", {"Премиум": 25000}),
    ]
    for name, variants in logo:
        for option, price in variants.items():
            prices.append(DesignPriceItem(name, option, "Дизайн Логотип и стиль", price))

    # Дизайн полиграфия (строки 20–26).
    poly: list[tuple[str, dict[str, list[int]], tuple[str, ...]]] = []
    poly.append(
        ("Дизайн визитки", {"4+0": [600, 900, 1500], "4+4": [900, 1350, 2000]}, LEVELS)
    )
    poly.append(
        ("Листовка", {"4+0": [1000, 1500, 2000], "4+4": [1500, 1950, 3000]}, LEVELS)
    )
    poly.append(("Буклет А4 (евро 2 фальца)", {"4+0": [2000, 2600, 4000]}, LEVELS))
    for name, levels in (
        ("Плакат А3", [2000, 2600, 3500]),
        ("Плакат А2", [2500, 3250, 4500]),
        ("Плакат А1", [3000, 3900, 6000]),
        ("Плакат А0", [4000, 5200, 6000]),
    ):
        poly.append((name, {"": levels}, LEVELS))
    for name, levels in (
        ("Грамота | Диплом | Сертификат", [1000, 1300, 2000]),
        ("Открытка | Приглашение", [1200, 1560, 2400]),
        ("Прайс лист до 3х стр.", [1000, 1500, 2000]),
        ("Меню (до 5 страниц)", [3000, 4100, 6000]),
        ("Меню (до 10 страниц)", [5000, 6500, 10000]),
        ("Карманный календарь", [800, 1040, 1600]),
        ("Календарь-домик (настольный)", [2000, 2600, 4000]),
        ("Квартальный календарь (трио)", [3000, 3900, 6000]),
        ("Настенный перекидной (12 листов)", [5000, 6500, 10000]),
        ("Фотокалендарь (индивидуальный)", [2500, 3250, 5000]),
    ):
        poly.append((name, {"": levels}, LEVELS))
    for name, sides, per_levels in poly:
        for side, level_prices in sides.items():
            full = name + (" " + side if side else "")
            for i, level_name in enumerate(LEVELS):
                prices.append(
                    DesignPriceItem(
                        full,
                        level_name,
                        "Дизайн полиграфия",
                        level_prices[i] if i < len(level_prices) else 0,
                    )
                )

    # Дизайн широкоформатная печать (строки 27–29).
    wide: list[tuple[str, list[int]]] = [
        ("Баннер (до 3 м.кв.)", [1000, 1500, 2500]),
        ("Баннер (до 9 м.кв.)", [2000, 3000, 4000]),
        ("Баннер (от 9 м.кв.)", [3000, 4200, 6500]),
        ("Вывеска", [0, 0, 0]),  # «Цена по запросу»
        ("Информационный стенд", [2000, 2850, 4400]),
        ("Макет под плоттерную резку", [500, 1000, 1500]),
        ("Оформление витрины (плёнка)", [2000, 2600, 5000]),
        ("Пресс-волл (3*2м.)", [2000, 3000, 5000]),
        ("Ролл-ап / Паук", [1500, 2250, 3750]),
        ("Табличка / Указатель", [500, 1500, 2250]),
    ]
    for name, levels in wide:
        for i, option in enumerate(WIDE_LEVELS):
            prices.append(
                DesignPriceItem(name, option, "Дизайн широкоформатная печать", levels[i])
            )

    # Дизайн прочие услуги (строки 30–32).
    misc: list[tuple[str, list[int]]] = [
        ("Подготовка макета к печати", [500, 750, 1000]),
        ("Внесение правок в готовый макет", [300, 390, 600]),
        ("Трассировка (перевод растра в вектор)", [1000, 1300, 2000]),
    ]
    for name, levels in misc:
        for i, option in enumerate(WIDE_LEVELS):
            prices.append(
                DesignPriceItem(name, option, "Дизайн прочие услуги", levels[i])
            )

    return tuple(prices)


@dataclass(frozen=True)
class DesignConfig:
    """Инъекционный конфиг дизайна (замена legacy settings.json price_list)."""

    prices: tuple[DesignPriceItem, ...] = build_prices()

    def services(self) -> tuple[str, ...]:
        """Уникальные имена услуг по базовому имени (legacy collectServices/get_base_name)."""
        return tuple(dict.fromkeys(_base_name(p.name) for p in self.prices))

    def options_for(self, service: str) -> tuple[str, ...]:
        """Варианты услуги (уникальные option по базовому имени)."""
        return tuple(
            dict.fromkeys(p.option for p in self.prices if _base_name(p.name) == service)
        )

    def sides_for(self, service: str) -> tuple[str, ...]:
        """Стороны печати услуги («4+0»/«4+4», legacy hasSide)."""
        sides: list[str] = []
        for p in self.prices:
            if _base_name(p.name) != service:
                continue
            for side in ("4+0", "4+4"):
                if side in p.name and side not in sides:
                    sides.append(side)
        return tuple(sides)

    def lookup(self, service: str, side: str, option: str) -> DesignPriceItem | None:
        """Поиск цены (паритет export_pdf, строки 118–126 / updatePrice JS):
        базовое имя == услуга, option == уровень; если сторона задана —
        она должна входить в имя, иначе имя не должно содержать «4+».
        """
        for p in self.prices:
            if _base_name(p.name) != service:
                continue
            if p.option != option:
                continue
            if side:
                if side not in p.name:
                    continue
            else:
                if "4+" in p.name:
                    continue
            return p
        return None


def _base_name(name: str) -> str:
    """Базовое имя услуги без стороны печати (legacy get_base_name)."""
    out: list[str] = []
    i = 0
    while i < len(name):
        if name[i] == "4" and i + 1 < len(name) and name[i + 1] == "+":
            j = i + 2
            while j < len(name) and name[j].isdigit():
                j += 1
            i = j  # пропускаем «4+N» (пробелы съедаются добавлением ниже)
        else:
            out.append(name[i])
            i += 1
    return "".join(out).replace("  ", " ").strip()


__all__ = ["DesignConfig", "DesignPriceItem", "LEVELS", "WIDE_LEVELS", "build_prices"]
