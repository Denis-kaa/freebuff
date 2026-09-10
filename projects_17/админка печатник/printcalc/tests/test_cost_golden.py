"""Golden-тесты Себестоимости: паритет с legacy universal_calc.py.

Ожидаемые значения получены независимой деривацией формул из исходника
(«Калькулятор себестоимости/universal_calc.py», machine_hour_cost
строки 432–439, total_machine_hours_per_month 442–448,
calc_price_for_job 449–587) и equipment.json; зафиксированы как
литералы. Менять их допустимо только вместе с осознанным изменением
формулы/оборудования (новая редакция контракта, см. README).

Общие константы деривации (дефолты GUI, строки 192–202):
    накладные/мес = 30000+8000+25000+5000+3000+9000 = 80000
    машино-часы всех станков/мес = (2000+2000+3000+1200+800+800)/12·0.8
                                 = 9800/12·0.8 = 653.3̅
    overhead/час = 80000 / 653.3̅ = 122.44897959183673
    наценка = 30%
"""

from __future__ import annotations

import pytest

from printcalc.calculators.cost import CostConfig, compute
from printcalc.calculators.cost.config import default_equipment
from printcalc.engine.errors import CalcInputError

_OVERHEAD_PER_HOUR = 122.44897959183673


def _cfg() -> CostConfig:
    return CostConfig()


# ---------- машино-час ----------


def test_machine_hour_costs_parity() -> None:
    eq = default_equipment()
    # VP540: 700000/10000 + 5000·12/10000 + 2.5·6 = 70+6+15 = 91.0
    assert eq["Roland VP540"].machine_hour_cost() == 91.0
    # Xerox: 100000/15000 + 2000·12/15000 + 1.5·6 = 6.66̅+1.6+9
    assert abs(eq["Xerox Phaser 7760"].machine_hour_cost() - 17.266666666666666) < 1e-9


# ---------- golden-кейсы по kind ----------


def test_golden_wide_vp540_banner_10sqm() -> None:
    # Баннер 10 м²: mat=80·10=800; cons=7·6·10=420; hours=10/12;
    # machine=91·(10/12); labor=300·(10/12); oh=122.449·(10/12);
    # total=1647.874149659864; price=total·1.3
    result = compute(
        {"equipment": "Roland VP540", "material": "Баннер (обычный)", "qty": 10},
        _cfg(),
    )
    assert result.lines[0].amount == 800.0
    assert result.lines[1].amount == 420.0
    assert abs(result.price - 2142.2363945578236) < 1e-6
    assert result.cost == 1647.8741496598639


def test_golden_digital_custom_layout() -> None:
    # Визитка 90×50 на А4: per_sheet = floor(210/90)·floor(297/50) = 2·5 = 10;
    # 500 шт → 50 листов; mat=0.6·50=30; cons=0.8·2·50=80; hours=50/40=1.25;
    # machine=17.266̅·1.25; labor=375; oh=153.061…; total=660.413…; ×1.3
    result = compute(
        {
            "equipment": "Xerox Phaser 7760",
            "material": "Бумага А4 80г",
            "qty": 500,
            "use_custom": True,
            "custom_width": 90,
            "custom_height": 50,
        },
        _cfg(),
    )
    assert result.details["sheets"] == 50
    assert result.details["sheet_format"] == "A4 (по 10 шт/лист)"
    # mat=30; cons=80; machine=17.266̅·1.25=21.583̅; labor=375; oh=153.061…;
    # total=659.6445578231293; ×1.3
    assert abs(result.price - 857.5379251700681) < 1e-6


def test_golden_offset_riso_master_price() -> None:
    # Riso 100 оттисков А4: mat=0.5·100=50; cons=(100/1000)·(20/1000)·3000
    # + 2500 = 2506 (мастер — на задачу); hours=100/120;
    # machine=(500000/8400 + 3000·12/8400 + 9)·(100/120) = 72.8095…·0.8̅;
    # total=2967.179…; ×1.3 = 3859.33
    result = compute(
        {"equipment": "Riso RZ300EP", "material": "Бумага А4 80г", "qty": 100},
        _cfg(),
    )
    # Кириллица «А4» не совпадает с латинским форматом «A4» и в legacy —
    # срабатывает fallback-ветка (масштаб от A4-шаблона, tpl_area == sheet_area
    # → числа те же, что exact): mat=50; cons=2506;
    # machine=72.8095…·(100/120)=60.6746…; labor=250; oh=102.0408…;
    # total=2968.715419501134; ×1.3
    assert result.details["sheets"] == 100.0
    assert abs(result.price - 3859.3300453514744) < 1e-6


def test_golden_lamination_area_based() -> None:
    # Ламинация 5 листов А4: area=0.21·0.297·5=0.311850;
    # mat=30·0.31185=9.3555; cons=0; hours=0.31185/5=0.06237;
    # machine=(25+1.5+12)·hours=38.5·hours; total=10.0920…; ×1.3
    result = compute(
        {
            "equipment": "Ламинатор Bulros FM650A",
            "material": "Плёнка глянцевая 32 мкм",
            "qty": 5,
        },
        _cfg(),
    )
    assert result.lines[1].amount == 0.0  # consumables
    assert abs(result.price - 49.5364) < 1e-3


# ---------- ветки fallback ----------


def test_unknown_material_falls_back_to_first() -> None:
    # Неизвестный материал → первый ключ словаря (parity 470–474).
    result = compute(
        {"equipment": "Roland VP540", "material": "Чеготонет", "qty": 1}, _cfg()
    )
    assert result.details["material"] == "Баннер (обычный)"


def test_scale_from_a4_template() -> None:
    # Латиница/кириллица: «A4» (формат) не входит в «Бумага А4 80г»
    # (кириллическая А) — и в legacy тоже → fallback-ветка, tpl_area ==
    # sheet_area → mat = 0.6·10 = 6, метка «(масштаб A4)» (parity legacy).
    result = compute(
        {"equipment": "Xerox Phaser 7760", "material": "Бумага А4 80г", "qty": 10},
        _cfg(),
    )
    assert result.details["material_used"] == "Бумага А4 80г (масштаб A4)"
    assert result.lines[0].amount == 6.0  # 0.6·10


# ---------- валидация ----------


def test_unknown_equipment_raises() -> None:
    with pytest.raises(CalcInputError):
        compute({"equipment": "Станок-невидимка", "qty": 1}, _cfg())


def test_zero_qty_raises() -> None:
    with pytest.raises(CalcInputError):
        compute({"equipment": "Roland VP540", "qty": 0}, _cfg())


def test_item_not_fitting_sheet_raises() -> None:
    # Изделие 300×400 не помещается на А4 (210×297) → n_x или n_y == 0.
    with pytest.raises(CalcInputError):
        compute(
            {
                "equipment": "Xerox Phaser 7760",
                "material": "Бумага А4 80г",
                "qty": 10,
                "use_custom": True,
                "custom_width": 300,
                "custom_height": 400,
            },
            _cfg(),
        )
