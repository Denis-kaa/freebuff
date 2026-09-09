"""REST API printcalc_web: прайс-каталог, расчёты, заказы, отчёты.

Границы доверия: клиент присылает только выбор (id позиции, параметры
калькулятора, название+цена ручной позиции); все цены позиций из
каталога и все расчёты выполняются на сервере.
"""

from __future__ import annotations

import csv
import io
import sqlite3
from collections.abc import Iterator
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from printcalc.engine.errors import CalcInputError, RegistryError
from printcalc.engine.registry import calculate as engine_calculate
from printcalc_web import export, parser, store
from printcalc_web.calculators import get_registry, list_calculators, result_to_dict
from printcalc_web.db import connect

router = APIRouter(prefix="/api")


def get_conn(request: Request) -> Iterator[sqlite3.Connection]:
    """Зависимость: соединение с БД приложения (один коннект на запрос)."""
    db_path = request.app.state.db_path
    conn = connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


def _store_guard(call: Any, *args: Any, **kwargs: Any) -> Any:
    try:
        return call(*args, **kwargs)
    except store.StoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


class PriceItemIn(BaseModel):
    """Создание позиции каталога (Р5а: Наименование + Значение, остальное опционально)."""

    name: str = Field(min_length=1)
    price: float = Field(ge=0)
    unit: str | None = None
    category: str | None = None


class PriceItemPatch(BaseModel):
    """Частичная правка позиции каталога (админка прайса)."""

    name: str | None = Field(default=None, min_length=1)
    price: float | None = Field(default=None, ge=0)
    unit: str | None = None
    category: str | None = None
    unverified: bool | None = None
    synonyms: list[str] | None = None


class SynonymIn(BaseModel):
    """Добавление синонима (идея №5)."""

    word: str = Field(min_length=1)


class ImportIn(BaseModel):
    """Массовый импорт списком (идея №6)."""

    text: str


class CalculateIn(BaseModel):
    """Запуск калькулятора движка."""

    calculator_id: str
    params: dict[str, Any] = Field(default_factory=dict)


class OrderItemIn(BaseModel):
    """Позиция черновика заказа (Р5б)."""

    kind: Literal["price_list", "calculator", "manual"]
    price_list_item_id: int | None = None
    qty: float = Field(default=1.0, gt=0)
    calculator_id: str | None = None
    params: dict[str, Any] | None = None
    name: str | None = None
    price: float | None = Field(default=None, ge=0)
    save_to_catalog: bool = True


class OrderIn(BaseModel):
    """Сохранение заказа («Добавить» на главном экране)."""

    status: str = store.ORDER_STATUSES[0]
    payment_method: str = Field(min_length=1)
    items: list[OrderItemIn] = Field(min_length=1)
    wishes: str = ""
    section_values: dict[str, str | None] = Field(default_factory=dict)
    client_id: int | None = None


class OrderPatch(BaseModel):
    """Смена статуса/оплаты/пожеланий существующего заказа (Р2)."""

    status: str | None = None
    payment_method: str | None = None
    wishes: str | None = None


class SectionIn(BaseModel):
    """Создание раздела конструктора."""

    title: str = Field(min_length=1)
    kind: str
    required: bool = False
    options: list[str] = Field(default_factory=list)


class SectionPatch(BaseModel):
    """Правка/архив раздела конструктора."""

    title: str | None = Field(default=None, min_length=1)
    kind: str | None = None
    required: bool | None = None
    options: list[str] | None = None
    archived: bool | None = None


class SectionReorderIn(BaseModel):
    """Пересортировка разделов: полный список id в новом порядке."""

    ids: list[int] = Field(min_length=1)


class ParseIn(BaseModel):
    """Быстрый ввод свободным текстом (Р6, ступень 1)."""

    text: str = Field(min_length=1)


class PaymentMethodsIn(BaseModel):
    """Редактирование списка способов оплаты (решение Q2)."""

    methods: list[str] = Field(min_length=1)


# ---------- настройки ----------


@router.get("/settings/payment-methods")
def read_payment_methods(conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    return {"methods": store.get_payment_methods(conn)}


@router.put("/settings/payment-methods")
def replace_payment_methods(
    payload: PaymentMethodsIn, conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:
    return {"methods": _store_guard(store.set_payment_methods, conn, payload.methods)}


# ---------- прайс-каталог ----------


@router.get("/price-list")
def read_price_list(
    q: str | None = None,
    unverified: bool | None = None,
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict[str, Any]:
    items = _store_guard(
        store.list_price_items, conn, query=q, unverified=unverified
    )
    return {"items": items}


@router.post("/price-list", status_code=201)
def create_price_item(
    payload: PriceItemIn, conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:
    return _store_guard(
        store.add_price_item,
        conn,
        name=payload.name,
        price=payload.price,
        unit=payload.unit,
        category=payload.category,
    )


@router.patch("/price-list/{item_id}")
def patch_price_item(
    item_id: int, payload: PriceItemPatch, conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:
    return _store_guard(store.update_price_item, conn, item_id, payload.model_dump())


@router.post("/price-list/{item_id}/synonyms")
def post_synonym(
    item_id: int, payload: SynonymIn, conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:
    return _store_guard(store.add_synonym, conn, item_id, payload.word)


@router.get("/price-list/similar")
def read_similar(
    q: str, conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:
    """Fuzzy-подсказка «похожее уже есть» (идея №8) — не блокирует создание."""
    return {"items": store.find_similar(conn, q)}


@router.post("/price-list/import")
def import_price_list(
    payload: ImportIn, conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:
    """Массовый импорт «Название - Цена» (идея №6)."""
    return _store_guard(store.import_price_items, conn, payload.text)


@router.get("/price-list/export.csv")
def export_price_list_csv(conn: sqlite3.Connection = Depends(get_conn)) -> Response:
    """Выгрузка всего каталога CSV (идея №9) — страховка от потери данных."""
    items = store.export_price_items(conn)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["name", "price", "unit", "category", "synonyms", "usage_count", "unverified"]
    )
    for item in items:
        writer.writerow(
            [
                item["name"],
                item["price"],
                item["unit"] or "",
                item["category"] or "",
                " | ".join(item["synonyms"]),
                item["usage_count"],
                1 if item["unverified"] else 0,
            ]
        )
    content = "\ufeff" + buffer.getvalue()  # BOM — чтобы Excel читал UTF-8
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="price-list.csv"'},
    )


# ---------- калькуляторы ----------


@router.get("/calculators")
def read_calculators() -> dict[str, Any]:
    """Спеки калькуляторов для schema-driven диалога (Р7)."""
    return {"calculators": list_calculators()}


@router.post("/calculate")
def run_calculation(
    payload: CalculateIn, conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:
    """Запускает калькулятор движка: валидация схемы → compute()."""
    _ = conn
    try:
        result = engine_calculate(get_registry(), payload.calculator_id, payload.params)
    except CalcInputError as exc:
        raise HTTPException(
            status_code=400, detail={"field": exc.field, "message": exc.message}
        ) from None
    except RegistryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    return result_to_dict(result)


class ConsumptionCalculateIn(BaseModel):
    """Расход материала для изделия (Этап 3, §48 промт_4).

    Материал — из реестра (id); размеры в см (интерфейс оператора);
    policy_overrides — необязательные припуски (bleed/gap/margins, мм).
    """

    material_id: int = Field(ge=1)
    width_cm: float = Field(gt=0)
    height_cm: float = Field(gt=0)
    quantity: float = Field(default=1, gt=0)
    policy_overrides: dict[str, Any] | None = None
    roll_width_mm: float | None = Field(default=None, gt=0)


@router.post("/consumption/calculate")
def calculate_consumption(
    payload: ConsumptionCalculateIn, conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:
    """Физический расход материала (не цена): раскрой, отход, трассировка.

    roll_width_mm — ручная ширина загруженного рулона (правило владельца:
    сменил плоттер на 3 м — ввёл фактическую ширину в расчёте).
    """
    return _store_guard(
        store.calculate_material_consumption,
        conn,
        material_id=payload.material_id,
        width_cm=payload.width_cm,
        height_cm=payload.height_cm,
        quantity=payload.quantity,
        policy_overrides=payload.policy_overrides,
        roll_width_mm=payload.roll_width_mm,
    )


@router.post("/parse")
def parse_text(
    payload: ParseIn, conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:
    """Быстрый ввод (Р6 ступень 1): словарь, без silent fallback."""
    return parser.parse(conn, payload.text)


# ---------- заказы ----------


@router.post("/orders", status_code=201)
def create_order(
    payload: OrderIn, conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:
    order = _store_guard(
        store.create_order,
        conn,
        status=payload.status,
        payment_method=payload.payment_method,
        items=[item.model_dump() for item in payload.items],
        wishes=payload.wishes,
        section_values=payload.section_values,
        client_id=payload.client_id,
    )
    return order


@router.get("/orders")
def read_orders(
    status: str | None = None, conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:
    return {"orders": _store_guard(store.list_orders, conn, status=status)}


@router.get("/orders/{order_id}")
def read_order(order_id: int, conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    return _store_guard(store.get_order, conn, order_id)


@router.patch("/orders/{order_id}")
def patch_order(
    order_id: int, payload: OrderPatch, conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:
    return _store_guard(
        store.update_order,
        conn,
        order_id,
        status=payload.status,
        payment_method=payload.payment_method,
        wishes=payload.wishes,
    )


@router.get("/orders/{order_id}/export.txt", response_class=Response)
def export_order_txt(
    order_id: int, conn: sqlite3.Connection = Depends(get_conn)
) -> Response:
    """OrderExport (Р1): текст для ручного переноса в WF."""
    order = _store_guard(store.get_order, conn, order_id)
    sections = _store_guard(store.get_order_sections, conn, order_id)
    return Response(
        content=export.order_to_text(order, sections),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="order-{order_id}.txt"'},
    )


# ---------- конструктор разделов ----------


@router.get("/sections")
def read_sections(
    include_archived: bool = False, conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:
    """Разделы главного экрана (конструктор)."""
    store.seed_sections(conn)
    return {
        "sections": _store_guard(store.list_sections, conn, include_archived=include_archived)
    }


@router.post("/sections", status_code=201)
def create_section(
    payload: SectionIn, conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:
    return _store_guard(
        store.add_section,
        conn,
        title=payload.title,
        kind=payload.kind,
        required=payload.required,
        options=payload.options,
    )


@router.patch("/sections/{section_id}")
def patch_section(
    section_id: int, payload: SectionPatch, conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:
    return _store_guard(store.update_section, conn, section_id, **payload.model_dump(exclude_none=True))


@router.post("/sections/reorder")
def reorder_sections(
    payload: SectionReorderIn, conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:
    return {"sections": _store_guard(store.reorder_sections, conn, payload.ids)}


@router.get("/orders/{order_id}/sections")
def read_order_sections(
    order_id: int, conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:
    """Значения разделов конкретного заказа."""
    return {"sections": _store_guard(store.get_order_sections, conn, order_id)}


# ---------- отчёты ----------


@router.get("/report/off-catalog")
def read_off_catalog_report(
    date_from: str | None = None,
    date_to: str | None = None,
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict[str, Any]:
    """Отчёт «что вводилось мимо каталога» (идея №10)."""
    return {
        "items": _store_guard(
            store.off_catalog_report, conn, date_from=date_from, date_to=date_to
        )
    }


# ---------- клиенты (Этап 1, §6 промт_4: клиент ≠ контакт) ----------


class ClientIn(BaseModel):
    """Создание клиента."""

    name: str = Field(min_length=1)
    kind: str = "физлицо"
    note: str = ""


class ClientPatch(BaseModel):
    """Правка/архив клиента."""

    name: str | None = Field(default=None, min_length=1)
    kind: str | None = None
    note: str | None = None
    archived: bool | None = None


class ContactIn(BaseModel):
    """Добавление контакта клиенту (канал из закрытого словаря store)."""

    channel: str
    value: str = Field(min_length=1)


@router.get("/clients")
def list_clients(
    q: str | None = None,
    include_archived: bool = False,
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict[str, Any]:
    """Список клиентов; q — поиск по имени и контактам (глобальный поиск §53)."""
    return {"clients": store.list_clients(conn, query=q, include_archived=include_archived)}


@router.post("/clients", status_code=201)
def create_client(payload: ClientIn, conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    return _store_guard(store.create_client, conn, name=payload.name, kind=payload.kind, note=payload.note)


@router.get("/clients/lookup")
def lookup_client(
    channel: str, value: str, conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:
    """Client matching по контакту (§45 промт_4): вернуть клиента или null."""
    found = store.find_client_by_contact(conn, channel=channel, value=value)
    return {"client": found}


@router.get("/clients/{client_id}")
def read_client(client_id: int, conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    client = store.get_client(conn, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail=f"клиент {client_id} не найден")
    return {**client, "contacts": store.list_contacts(conn, client_id)}


@router.patch("/clients/{client_id}")
def patch_client(
    client_id: int, payload: ClientPatch, conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:
    return _store_guard(
        store.update_client,
        conn,
        client_id,
        name=payload.name,
        kind=payload.kind,
        note=payload.note,
        archived=payload.archived,
    )


@router.post("/clients/{client_id}/contacts", status_code=201)
def add_contact(
    client_id: int, payload: ContactIn, conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:
    return _store_guard(store.add_contact, conn, client_id, channel=payload.channel, value=payload.value)


@router.delete("/clients/{client_id}/contacts/{contact_id}", status_code=204)
def remove_contact(
    client_id: int, contact_id: int, conn: sqlite3.Connection = Depends(get_conn)
) -> Response:
    _store_guard(store.delete_contact, conn, contact_id)
    return Response(status_code=204)


class OrderClientPatch(BaseModel):
    """Привязка клиента к заказу (None — отвязать)."""

    client_id: int | None = None


@router.patch("/orders/{order_id}/client")
def patch_order_client(
    order_id: int, payload: OrderClientPatch, conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:
    return _store_guard(store.assign_order_client, conn, order_id, payload.client_id)


# ---------- реестр материалов (Этап 1, §18 промт_4) ----------


class MaterialIn(BaseModel):
    """Создание материала (режим/единицы — закрытые словари store)."""

    name: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)
    category: str = "general"
    consumption_mode: str = "AREA"
    base_unit: str = "m2"
    purchase_unit: str | None = None
    purchase_cost: float = Field(default=0, ge=0)
    price_unit: str | None = None
    roll_width: float | None = Field(default=None, gt=0)
    roll_length: float | None = Field(default=None, gt=0)
    sheet_width: float | None = Field(default=None, gt=0)
    sheet_height: float | None = Field(default=None, gt=0)
    min_stock: float = Field(default=0, ge=0)
    supplier: str | None = None
    active: bool = True


@router.get("/materials")
def list_materials(
    active_only: bool = False,
    category: str | None = None,
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict[str, Any]:
    """Список материалов (active_only — для подбора в UI заказа)."""
    return {"materials": store.list_materials(conn, active_only=active_only, category=category)}


@router.post("/materials", status_code=201)
def create_material(payload: MaterialIn, conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    fields = payload.model_dump()
    if fields.get("purchase_unit") is None:
        fields["purchase_unit"] = fields["base_unit"]
    if fields.get("price_unit") is None:
        fields["price_unit"] = fields["base_unit"]
    return _store_guard(store.create_material, conn, fields=fields)


@router.get("/materials/lookup")
def lookup_material(
    name: str, conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:
    """Поиск материала по имени или алиасу (BR-W1: защита от дрейфа словаря)."""
    return {"material": store.find_material_by_name(conn, name)}


@router.get("/materials/{material_id}")
def read_material(material_id: int, conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    material = store.get_material(conn, material_id)
    if material is None:
        raise HTTPException(status_code=404, detail=f"материал {material_id} не найден")
    return material


@router.patch("/materials/{material_id}")
def patch_material(
    material_id: int, payload: dict[str, Any], conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:        return _store_guard(store.update_material, conn, material_id, fields=payload)


# ---------- сметы (Этап 2 роадмапа v6) ----------


class EstimateItemIn(BaseModel):
    """Позиция сметы — тот же контракт, что у позиций заказа."""

    kind: Literal["price_list", "calculator", "manual"]
    price_list_item_id: int | None = None
    qty: float = Field(default=1, gt=0)
    calculator_id: str | None = None
    params: dict[str, Any] | None = None
    name: str | None = None
    price: float | None = Field(default=None, ge=0)
    save_to_catalog: bool = True


class EstimateIn(BaseModel):
    """Создание сметы (§22): позиции + клиент + примечание + срок действия."""

    items: list[EstimateItemIn] = Field(min_length=1)
    client_id: int | None = None
    note: str = ""
    valid_until: str | None = None


class EstimatePatch(BaseModel):
    """Правка meta-полей сметы (запрещена после ACCEPTED — §49)."""

    client_id: int | None = None
    note: str | None = None
    valid_until: str | None = None


class EstimateStatusPatch(BaseModel):
    """Перевод статуса (§24) или принятие (accept — отдельный алиас)."""

    status: Literal["draft", "sent", "viewed", "accepted", "rejected", "expired"]


class OrderFromEstimateIn(BaseModel):
    """Заказ из принятой сметы: оператор выбирает только способ оплаты (§9)."""

    payment_method: str = Field(min_length=1)
    status: str = Field(default="новый")


@router.get("/estimates")
def list_estimates(
    status: str | None = None,
    client_id: int | None = None,
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict[str, Any]:
    """Список смет с фильтрами (для страницы «Сметы»)."""
    return {
        "estimates": _store_guard(
            store.list_estimates, conn, status=status, client_id=client_id
        )
    }


@router.post("/estimates", status_code=201)
def create_estimate(
    payload: EstimateIn, conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:
    """Создаёт смету из позиций (цены резолвит сервер)."""
    return _store_guard(
        store.create_estimate,
        conn,
        items=[item.model_dump() for item in payload.items],
        client_id=payload.client_id,
        note=payload.note,
        valid_until=payload.valid_until,
    )


@router.get("/estimates/{estimate_id}")
def read_estimate(
    estimate_id: int, conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:
    """Смета целиком: позиции + snapshot (если принят)."""
    return _store_guard(store.get_estimate, conn, estimate_id)


@router.patch("/estimates/{estimate_id}")
def patch_estimate(
    estimate_id: int,
    payload: EstimatePatch,
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict[str, Any]:
    """Правка примечания/срока/клиента до принятия (§49).

    exclude_unset: отсутствие поля в запросе ≠ «очистить поле» — иначе
    патч одного note сбрасывал бы клиента в NULL.
    """
    fields = payload.model_dump(exclude_unset=True)
    return _store_guard(store.update_estimate, conn, estimate_id, **fields)


@router.post("/estimates/{estimate_id}/status")
def change_estimate_status(
    estimate_id: int,
    payload: EstimateStatusPatch,
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict[str, Any]:
    """Перевод по статусам (§24); accept фиксирует snapshot (§49)."""
    return _store_guard(store.transition_estimate, conn, estimate_id, payload.status)


@router.post("/estimates/{estimate_id}/accept")
def accept_estimate(
    estimate_id: int, conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:
    """Принять смету: snapshot версий калькулятора/каталога (§49)."""
    return _store_guard(store.accept_estimate, conn, estimate_id)


@router.post("/estimates/{estimate_id}/order", status_code=201)
def create_order_from_estimate(
    estimate_id: int,
    payload: OrderFromEstimateIn,
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict[str, Any]:
    """Заказ из принятой сметы без ручного переноса (§9 промт_4)."""
    return _store_guard(
        store.create_order_from_estimate,
        conn,
        estimate_id,
        payment_method=payload.payment_method,
        status=payload.status,
    )


# ---------- производство (Этап 4 роадмапа v6) ----------


class TaskCompleteIn(BaseModel):
    """Завершение задания: чек-лист обязателен (§10 OPERATIONS_CATALOG)."""

    checklist: list[bool] = Field(default_factory=list)
    notes: str = ""


class TaskBlockIn(BaseModel):
    """Блокировка задания с причиной."""

    reason: str = Field(min_length=1)


@router.get("/operations")
def list_operations(
    enabled_only: bool = False, conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:
    """Каталог операций (данные, редактируются в настройках)."""
    return {"operations": store.list_operations(conn, enabled_only=enabled_only)}


@router.post("/orders/{order_id}/production/generate", status_code=201)
def generate_production(
    order_id: int, conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:
    """Генерирует задания заказа по правилам (идемпотентно)."""
    created = _store_guard(store.generate_production_plan, conn, order_id)
    return {"created": created, "progress": store.production_progress(conn, order_id)}


@router.get("/orders/{order_id}/production")
def read_production(
    order_id: int, conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:
    """Задания заказа + прогресс."""
    return {
        "tasks": store.list_production_tasks(conn, order_id=order_id),
        "progress": store.production_progress(conn, order_id),
    }


@router.get("/production/tasks")
def read_production_tasks(
    status: str | None = None,
    order_id: int | None = None,
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict[str, Any]:
    """Все задания (раздел «Производство»), фильтры по статусу/заказу."""
    return {
        "tasks": _store_guard(
            store.list_production_tasks, conn, order_id=order_id, status=status
        )
    }


@router.post("/production/tasks/{task_id}/start")
def start_task(
    task_id: int, conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:
    return _store_guard(store.start_task, conn, task_id)


@router.post("/production/tasks/{task_id}/complete")
def complete_task(
    task_id: int,
    payload: TaskCompleteIn,
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict[str, Any]:
    """Завершить задание: без полного чек-листа — 400 (§10)."""
    return _store_guard(
        store.complete_task, conn, task_id, checklist=payload.checklist, notes=payload.notes
    )


@router.post("/production/tasks/{task_id}/block")
def block_task(
    task_id: int,
    payload: TaskBlockIn,
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict[str, Any]:
    return _store_guard(store.block_task, conn, task_id, reason=payload.reason)
