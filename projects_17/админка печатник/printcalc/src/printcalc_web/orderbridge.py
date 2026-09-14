"""S5-мост: вердикт правил → параметры калькулятора (РОАДМАП_v7 §6).

Связка Smart Order с расчётом (промт_6 PHASE R5):
- `ready_for_calculator=true` → параметры готового расчёта БЕЗ повторного ввода;
- подтверждённые операции (аудит S4) → флаги доп-работ wide → задания OP-* через
  СУЩЕСТВУЮЩИЙ конвейер generate_production_plan (идемпотентно, отдельного
  конвейера не создаём).

Правила перевода (закрытые словари, ANTI-6b):
- size_mm → width/height в САНТИМЕТРАХ (спека wide — legacy GUI, см);
- quantity → qty;
- operation token OP-* → work_*-флаг по OPS_TO_WORK_FLAGS (только коды,
  сидящие на wide-работах; OP-15 «Накатка» = work_laminate_mount по каталогу);
- люверсы из фактов (grommets_step_cm) → grommet_interval (см).

Чего мост НЕ делает:
- не считает цены на клиенте — результат только с сервера (движок);
- не применяет ничего сам — вызов = действие сотрудника (кнопка «В расчёт»);
- не заполняет пропуски дефолтами GUI (200×100) — нет размера/тиража →
  BridgeError с вопросом из вердикта (не молча).
"""

from __future__ import annotations

from typing import Any, Mapping

from printcalc_web.rules.engine import RuleVerdict

#: Код операции каталога → флаг доп-работы wide (WORK_SLUGS + WORK_PRICES).
#: Закрытый маппинг: коды вне его в параметры НЕ попадают (не молча —
#: операция без флага попадает в задание через план, но не в цену).
OPS_TO_WORK_FLAGS: dict[str, str] = {
    "OP-22": "work_plotter_cut",      # «Плоттерная резка» (S2)
    "OP-13": "work_eyelets",          # «Установить люверсы»
    "OP-14": "work_hemming",          # «Загибка / карман»
    "OP-15": "work_laminate_mount",   # «Накатка на основу» (монтажная плёнка)
}

#: Пак → калькулятор реестра (packs/*.yaml product; на случай будущих паков
#: с другим калькулятором берём из вердикта динамически, не хардкодом).
_PACK_TO_CALCULATOR: dict[str, str] = {
    "sticker": "wide",
    "banner": "wide",
    "backlit": "wide",
}


class BridgeError(ValueError):
    """Мост не может собрать параметры (нет размера/тиража/пака) — не молча."""


def verdict_to_calculator_params(
    verdict_json: Mapping[str, Any],
    *,
    accepted_operations: list[str] | None = None,
) -> dict[str, Any]:
    """RuleVerdict JSON (S3-контракт) → {calculator_id, params} для движка.

    accepted_operations — коды операций, подтверждённые сотрудником на S4
    (аудит /suggestions/decisions, decision='accepted', kind='operation').
    Только они превращаются в work-флаги: предложенное, но не подтверждённое
    в цену не попадает (§1 промт_6: «распознать» ≠ «предложить»).
    """
    pack = str(verdict_json.get("matched_pack") or "")
    calculator_id = _PACK_TO_CALCULATOR.get(pack)
    if calculator_id is None:
        raise BridgeError(
            f"продукт «{pack or 'не распознан'}» не привязан к калькулятору — "
            "добавьте позиции вручную через «+»"
        )

    size_mm = verdict_json.get("size_mm")
    if not isinstance(size_mm, (list, tuple)) or len(size_mm) != 2:
        raise BridgeError("размер изделия не распознан — укажите размер (например, 50×30)")
    quantity = verdict_json.get("quantity")
    if not isinstance(quantity, (int, float)) or isinstance(quantity, bool) or quantity <= 0:
        raise BridgeError("тираж не распознан — укажите количество (например, 149 шт)")

    params: dict[str, Any] = {
        # спека wide — в сантиметрах (legacy GUI var_w/var_h)
        "width": round(float(size_mm[0]) / 10.0, 3),
        "height": round(float(size_mm[1]) / 10.0, 3),
        "qty": float(quantity),
    }

    facts = verdict_json.get("facts") or {}
    step_cm = facts.get("grommets_step_cm")
    if isinstance(step_cm, (int, float)) and step_cm > 0:
        params["grommet_interval"] = float(step_cm) / 10.0  # мм → см

    accepted = set(accepted_operations or [])
    for token in accepted:
        flag = OPS_TO_WORK_FLAGS.get(token)
        if flag is not None:
            params[flag] = True

    return {"calculator_id": calculator_id, "params": params}


def bridge_from_verdict(
    verdict_json: Mapping[str, Any],
    *,
    accepted_operations: list[str] | None = None,
) -> dict[str, Any]:
    """Вердикт → готовая расчётная позиция: {calculator_id, params, result}.

    Запускает движок на сервере (цены — только с сервера); CalcInputError
    отдаётся как BridgeError с полем — API превратит в честный 400.
    """
    bridge = verdict_to_calculator_params(
        verdict_json, accepted_operations=accepted_operations
    )
    from printcalc.engine.errors import CalcInputError
    from printcalc.engine.registry import RegistryError, calculate
    from printcalc_web.calculators import get_registry

    registry = get_registry()
    spec = registry.get(bridge["calculator_id"]).spec
    params = dict(bridge["params"])
    # Дефолты спеки (материал/печать/монтаж) — как в UI-форме; размер/тираж
    # и флаги работ приходят из вердикта и НЕ перетираются.
    for fs in spec.fields:
        if fs.name not in params and fs.default is not None:
            params[fs.name] = fs.default

    try:
        result = calculate(registry, bridge["calculator_id"], params)
    except CalcInputError as exc:
        raise BridgeError(f"{exc.field}: {exc.message}") from None
    except RegistryError as exc:
        raise BridgeError(str(exc)) from None

    from printcalc_web.calculators import result_to_dict

    return {
        "calculator_id": bridge["calculator_id"],
        "params": params,
        "result": result_to_dict(result),
    }


def verdict_ready(verdict: RuleVerdict) -> bool:
    """Готовность вердикта к расчёту (как ready_for_calculator, для UI-моста)."""
    return verdict.ready_for_calculator
