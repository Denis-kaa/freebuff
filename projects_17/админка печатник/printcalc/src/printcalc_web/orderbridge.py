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

S6 (РОАДМАП_v7 §6.1, доработка по итогам эксплуатации S5): ответы на вопросы
verdict.missing (layout/layout_with_cut_contour — «макет готов?») передаются
отдельным аргументом `question_answers` ТОЛЬКО если сотрудник дал явный ответ
(аудит S4). Закрытый словарь QUESTION_FACT_TO_POSITION:
- ответ «no» («макета нет») + подтверждённая OP-22 → дополнительная позиция
  дизайна «Макет под плоттерную резку» (design-калькулятор; уровень — Простой,
  сотрудник меняет в позиции черновика). Без подтверждённой OP-22 ответ «no»
  в позицию НЕ превращается (не молча: вопрос производства ≠ операция).
- ответ «yes» → ничего не добавляется (макет есть), ответ фиксируется в
  результатe bridge (facts_applied) для прозрачности.
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

#: Ответ «нет» на layout-вопрос + какая операция подтверждена → какая
#: позиция дизайна нужна (S6, закрытый словарь ANTI-6b). Ключ —
#: «<field>:<operation|any>»: контурная резка требует КОНТУР в макете,
#: простой макет — без требования контура.
QUESTION_NO_TO_DESIGN: dict[tuple[str, str], dict[str, str]] = {
    ("layout_with_cut_contour", "OP-22"): {
        "calculator_id": "design",
        "service": "Макет под плоттерную резку",
    },
    ("layout", "OP-22"): {
        "calculator_id": "design",
        "service": "Подготовка макета к печати",
    },
}

#: Уровень дизайн-позиции по умолчанию (options design-калькулятора:
#: Простой/Стандарт/Премиум) — сотрудник меняет уровень в позиции черновика.
QUESTION_DESIGN_DEFAULT_OPTION = "Простой"

#: Пак → калькулятор реестра (packs/*.yaml product; на случай будущих паков
#: с другим калькулятором берём из вердикта динамически, не хардкодом).
_PACK_TO_CALCULATOR: dict[str, str] = {
    "sticker": "wide",
    "banner": "wide",
    "backlit": "wide",
}


class BridgeError(ValueError):
    """Мост не может собрать параметры (нет размера/тиража/пака) — не молча."""


#: Закрытый набор полей-вопросов, чьи ответы мост принимает (S6) и
#: закрытый набор значений ответов. Всё остальное — BridgeError.
QUESTION_ANSWER_FIELDS: frozenset[str] = frozenset(
    {"layout", "layout_with_cut_contour"}
)
QUESTION_ANSWER_VALUES: frozenset[str] = frozenset({"yes", "no"})


def validate_question_answers(question_answers: Mapping[str, str]) -> None:
    """Ответы на вопросы вне закрытых наборов → BridgeError (ANTI-6b)."""
    for field, answer in question_answers.items():
        if field not in QUESTION_ANSWER_FIELDS:
            raise BridgeError(
                f"ответ на вопрос {field!r} не поддерживается мостом "
                f"(принимаются: {', '.join(sorted(QUESTION_ANSWER_FIELDS))})"
            )
        if answer not in QUESTION_ANSWER_VALUES:
            raise BridgeError(
                f"ответ {answer!r} на вопрос {field!r} вне набора "
                f"(принимаются: {', '.join(sorted(QUESTION_ANSWER_VALUES))})"
            )


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
    question_answers: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Вердикт → готовая расчётная позиция: {calculator_id, params, result}.

    question_answers — ответы сотрудника на вопросы вердикта (S4-аудит):
    {"layout": "no"|"yes", "layout_with_cut_contour": ...}. Закрытый словарь
    ANSWER_VALUES; поле вне KNOWN_MISSING_FIELDS / ответ вне набора —
    игнорируется молча? НЕТ: BridgeError (ANTI-6b — громко, не молча).

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

    # S6: ответы на вопросы производства → дополнительные позиции.
    extra_positions = question_answer_positions(
        verdict_json, question_answers or {}, accepted_operations or []
    )

    return {
        "calculator_id": bridge["calculator_id"],
        "params": params,
        "result": result_to_dict(result),
        "facts_applied": dict(question_answers or {}),
        "extra_positions": extra_positions,
    }


def question_answer_positions(
    verdict_json: Mapping[str, Any],
    question_answers: Mapping[str, str],
    accepted_operations: list[str],
) -> list[dict[str, Any]]:
    """Ответы «макета нет» → позиции дизайна (S6, только по явному ответу).

    Правила (закрытый словарь QUESTION_NO_TO_DESIGN):
    - вопрос fields layout/layout_with_cut_contour, ответ ровно «no»;
    - соответствующая операция ПОДТВЕРЖДЕНА сотрудником (OP-22) —
      без подтверждения ответ «no» не создаёт позицию (не молча:
      вернётся пусто, вопрос производства остаётся вопросом);
    - позиция считается сервером (design-калькулятор), тираж 1, уровень
      Простой — сотрудник правит в черновике.
    """
    accepted = set(accepted_operations)
    positions: list[dict[str, Any]] = []
    for (field, operation), target in QUESTION_NO_TO_DESIGN.items():
        answer = question_answers.get(field)
        if answer != "no":
            continue
        if operation not in accepted:
            continue
        positions.append(_design_position(target["calculator_id"], target["service"]))
    return positions


def _design_position(calculator_id: str, service: str) -> dict[str, Any]:
    """Посчитать дизайн-позицию сервером (тираж 1; уровень правится в UI)."""
    from printcalc.engine.errors import CalcInputError
    from printcalc.engine.registry import RegistryError, calculate
    from printcalc_web.calculators import get_registry, result_to_dict

    registry = get_registry()
    spec = registry.get(calculator_id).spec
    params: dict[str, Any] = {
        "service": service,
        "option": QUESTION_DESIGN_DEFAULT_OPTION,
        "pages": 1,
        "circulation": 1,
    }
    for fs in spec.fields:
        if fs.name not in params and fs.default is not None:
            params[fs.name] = fs.default
    try:
        result = calculate(registry, calculator_id, params)
    except CalcInputError as exc:
        raise BridgeError(f"{exc.field}: {exc.message}") from None
    except RegistryError as exc:
        raise BridgeError(str(exc)) from None
    return {
        "calculator_id": calculator_id,
        "name": service,
        "params": params,
        "result": result_to_dict(result),
    }


def verdict_ready(verdict: RuleVerdict) -> bool:
    """Готовность вердикта к расчёту (как ready_for_calculator, для UI-моста)."""
    return verdict.ready_for_calculator
