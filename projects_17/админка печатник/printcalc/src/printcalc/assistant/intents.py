"""Ассистентские intents (ASST-INTENTS): TOP-20 MVP-сценариев исследования.

Каждый intent — «мост» между вольной фразой клиента и параметрами заказа:
- phrases — РЕАЛЬНЫЕ формулировки из research/04_customer_requests.md,
  каждая с ссылкой CR-NN (линковка корпуса: 108 записей CR-01…CR-111,
  номера 17–19 не используются). §2 промта запрещает выдумывать
  формулировки; фразы без CR-ссылки допускаются только с явной пометкой
  источника в notes (прайс-фразы из 12_intents.json / 03_price_lists.csv);
- params — REQUIRED/OPTIONAL из research/06_parameters.md;
- infer / never_infer — правила INFERRED≠KNOWN (research/06, 14 R7);
- dialog_rules — ссылки на правила R1–R10 (research/14_dialog_rules.md);
- calculator_id — связка с существующими калькуляторами (None, если такого
  калькулятора в engine ещё нет — добавление калькулятора НЕ входит в этот
  аддитивный шаг).

Реестр закрытый (ANTI-6b): дубликат id и неизвестный id — ошибки.
Совместимость calculator_id с CalculatorRegistry проверяется тестом.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from printcalc.engine.errors import RegistryError

__all__ = [
    "MvpPriority",
    "AssistantIntentSpec",
    "AssistantIntentRegistry",
    "build_default_registry",
    "INTENT_IDS_TOP20",
    "match_intent",
    "clarification_for",
    "missing_required",
    "intent_sources",
    "warnings_for",
    "SynonymToken",
    "SynonymMatch",
    "SYNONYM_TABLE",
    "UNMAPPED_RESEARCH_INTENTS",
    "match_synonym",
    "ASSISTANT_SOURCE",
]


class MvpPriority(StrEnum):
    """Приоритет MVP из research/15_mvp.md (P0–P3)."""

    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


#: Происхождение данных (трассируемость в исследование).
ASSISTANT_SOURCE = (
    "research/12_intents.json v1.0 + research/11_nefteyugansk.md TOP-20"
    " + research/04_customer_requests.md CR-01…CR-111"
)


@dataclass(frozen=True)
class AssistantIntentSpec:
    """Спека одного ассистентского intent (неизменяемая)."""

    id: str
    title: str
    mvp: MvpPriority
    category: str
    #: Реальные клиентские формулировки из корпуса; пусто => phrases_verified=False.
    phrases: tuple[str, ...] = ()
    #: True, если phrases непустой (верифицированные формулировки есть).
    phrases_verified: bool = False
    #: CR-ссылки корпуса research/04, из которого взяты phrases.
    source_cr: tuple[str, ...] = ()
    required_params: tuple[str, ...] = ()
    optional_params: tuple[str, ...] = ()
    #: Что МОЖНО вывести автоматически (показывать клиенту для подтверждения).
    infer: tuple[str, ...] = ()
    #: Что НЕЛЬЗЯ угадывать никогда (research/14, R7/R9).
    never_infer: tuple[str, ...] = ()
    #: Минимальный уточняющий вопрос (§18 промта; research/14, R1).
    clarification: str = ""
    #: Правила диалога, применяемые к intent (research/14).
    dialog_rules: tuple[str, ...] = ()
    #: Связка с калькулятором engine; None — калькулятора ещё нет.
    calculator_id: str | None = None
    #: Уровень эскалации к человеку (research/09_automation.md).
    automation: str = "AUTO"  # AUTO | PARTIAL | HUMAN
    human_check: bool = False
    #: Знания, которые ассистент обязан учитывать/предупреждать (не параметры).
    knowledge: tuple[str, ...] = field(default=())
    notes: tuple[str, ...] = field(default=())


class AssistantIntentRegistry:
    """Закрытый реестр «id -> spec» (в духе CALC-REGISTRY)."""

    def __init__(self) -> None:
        self._items: dict[str, AssistantIntentSpec] = {}

    def register(self, spec: AssistantIntentSpec) -> None:
        if spec.id in self._items:
            raise RegistryError(f"intent '{spec.id}' уже зарегистрирован")
        self._items[spec.id] = spec

    def get(self, intent_id: str) -> AssistantIntentSpec:
        try:
            return self._items[intent_id]
        except KeyError:
            raise RegistryError(f"неизвестный intent: '{intent_id}'") from None

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._items))

    def by_priority(self, priority: MvpPriority) -> tuple[str, ...]:
        return tuple(
            i.id for i in sorted(self._items.values(), key=lambda s: s.id)
            if i.mvp == priority
        )

    def __contains__(self, intent_id: str) -> bool:
        return intent_id in self._items


# --------------------------------------------------------------------------
# TOP-20 MVP (research/11_nefteyugansk.md §TOP-20).
# ЛИНКОВКА КОРПУСА: каждая фраза помечена CR-NN из research/04_customer_requests.md.
# Порядок регистрации == порядок TOP-20.
# --------------------------------------------------------------------------

_TOP20: tuple[AssistantIntentSpec, ...] = (
    AssistantIntentSpec(
        id="photo_print",
        title="Печать фотографий",
        mvp=MvpPriority.P0,
        category="photo",
        phrases=(
            "Хочу распечатать фотографии на 10×15",  # CR-02 (otvet.mail.ru)
            "Распечатывала здесь фото, 10 штук, одно фото за 25 руб",  # CR-12 (2ГИС, Мир Фото ХМ)
            "Даже с телефона можно",  # CR-02 (тред CR-02)
            "Сколько стоит распечатать фото?",  # CR-26 (ФотоОтель FAQ)
            "Несколько раз обращалась распечатать фотографии",  # CR-73 (2ГИС-сниппет, Точка печати)
            "Первый раз зашла распечатать фотографию, которую мне сделали в другом салоне",  # CR-74 (Фуджифильм)
        ),
        source_cr=("CR-02", "CR-12", "CR-26", "CR-73", "CR-74"),
        phrases_verified=True,
        required_params=("size", "quantity", "files"),
        optional_params=("paper", "deadline", "delivery", "color_correction"),
        infer=(
            "тиражная ступень из quantity",
            "paper=глянец (стандарт рынка, подтверждение)",
        ),
        never_infer=("кадрирование клиента (обрезка/поля)",),
        clarification="Сколько фото и какого размера? Файлы с флешки или с телефона?",
        dialog_rules=("R1", "R3", "R4"),
        automation="AUTO",
        human_check=False,
        knowledge=(
            "печать 10×15 требует кадрирования под 2:3, иначе обрезка/поля (CR-02)",
            "формат 10×15 = 102×152 мм по таблице ФотоСферы (CR-41)",
        ),
        notes=("CR-03: печать ГОТОВОГО файла ≠ document_photo",),
    ),
    AssistantIntentSpec(
        id="copy_bw",
        title="Ксерокопия ч/б",
        mvp=MvpPriority.P0,
        category="copy",
        phrases=(
            "Сколько стоит распечатать лист А4 черно белый?",  # CR-64 (SEO-FAQ kopirovalnya.ru)
            "Почему сканирование стоит дороже распечатки?",  # CR-30 (otvet.mail.ru)
            "Ксерокопия чёрно-белая — 15 ₽",  # прайс Точка Печати (12_intents.json, Яндекс.Карты)
        ),
        source_cr=("CR-64", "CR-30"),
        phrases_verified=True,
        required_params=("pages",),
        optional_params=("color", "scale"),
        infer=(),
        never_infer=("цветность при неоднозначном «печатать»",),
        clarification="Сколько страниц и нужна ли цветная?",
        dialog_rules=("R1",),
        automation="AUTO",
        human_check=False,
        notes=("прайс-фраза «Ксерокопия чёрно-белая — 15 ₽» — из 12_intents.json (Яндекс.Карты)",),
    ),
    AssistantIntentSpec(
        id="print_document",
        title="Печать документов из файла",
        mvp=MvpPriority.P0,
        category="copy",
        phrases=(
            "Распечатка текстов, документов, рефератов, курсовых и дипломных работ",  # CR-16 (Avito Югорск)
            "Сколько стоит распечатать цветной лист А4?",  # CR-64 (SEO-FAQ kopirovalnya.ru)
            "Нужно было срочно распечатать дипломы. Сделали за пару часов",  # CR-103 (2ГИС-сниппет)
            "Как распечатать файл документа, если он только на телефоне? Флешки нет, оригинала документа тоже",  # CR-83 (otvet.mail.ru)
        ),
        source_cr=("CR-16", "CR-64", "CR-83", "CR-103"),
        phrases_verified=True,
        required_params=("pages", "color", "files"),
        optional_params=("paper", "duplex", "deadline"),
        infer=(),
        never_infer=("печать Word-макета без предупреждения",),
        clarification="Сколько страниц, чёрно-белая или цветная? Файл PDF или Word?",
        dialog_rules=("R4",),
        automation="AUTO",
        human_check=False,
        knowledge=(
            "файл с телефона без флешки: файл пересылают на почту точки печати (CR-83)",
            "приём с телефона может быть с наценкой ~50 ₽ (CR-82)",
        ),
        notes=("двусторонняя печать — отдельный запрос (CR-66)",),
    ),
    AssistantIntentSpec(
        id="scan",
        title="Сканирование",
        mvp=MvpPriority.P0,
        category="copy",
        phrases=(
            "Сканирование документов и фотографий — 20 ₽",  # прайс Zoon (12_intents.json)
            "Почему сканирование стоит дороже распечатки?",  # CR-30 (otvet.mail.ru)
        ),
        source_cr=("CR-30",),
        phrases_verified=True,
        required_params=("pages",),
        optional_params=("output_format", "resolution"),
        infer=(),
        never_infer=(),
        clarification="Сколько страниц?",
        automation="AUTO",
        human_check=False,
        notes=("прайс-фраза «Сканирование… — 20 ₽» — из 12_intents.json (Zoon)",),
    ),
    AssistantIntentSpec(
        id="laminate",
        title="Ламинирование",
        mvp=MvpPriority.P0,
        category="postprint",
        phrases=(
            "Сколько стоит ламинация свидетельства о рождении?",  # CR-67 (Instagram-комментарий)
            "Хотела заламинировать свидетельство о браке, но мне отказали",  # CR-110 (otvet.mail.ru)
        ),
        source_cr=("CR-67", "CR-110"),
        phrases_verified=True,
        required_params=("format",),
        optional_params=("quantity",),
        infer=(),
        never_infer=("толщину плёнки (в прайсах не тарифицируется)",),
        clarification="Формат документа — А4, А5 или меньше?",
        dialog_rules=("R1",),
        automation="AUTO",
        human_check=False,
        knowledge=(
            "ламинированные документы ЗАГСа могут быть признаны недействительными — предупреждать (CR-109)",
            "на свидетельстве о браке могут отказать — предупреждать (CR-110)",
        ),
        notes=("прайс-фраза «Ламинация документа — 60 ₽» — из 12_intents.json (Яндекс.Карты)",),
    ),
    AssistantIntentSpec(
        id="document_photo",
        title="Фото на документы (съёмка)",
        mvp=MvpPriority.P0,
        category="photo",
        phrases=(
            "фото на документы паспорт визу 3х4",  # CR-11 (VK Фото Мир НфЮ)
            "В моем городе две фотографии размером 3*4 стоят 200р",  # CR-01
            "Заказывал в этой компании печать фото на документы",  # CR-15 (jsprav, Советский)
            "сколько стоит 2 фото 3на4 черно-белые",  # CR-80 (otvet.mail.ru)
            "Фотографирую тут для паспорта уже не первый раз",  # CR-101 (jsprav-сниппет, Сургут)
            "Сколько по времени делают фото на документы? 3х4",  # CR-78 (otvet.mail.ru)
        ),
        source_cr=("CR-01", "CR-11", "CR-15", "CR-78", "CR-80", "CR-101"),
        phrases_verified=True,
        required_params=("document_type", "package_or_print"),
        optional_params=("quantity", "retouch", "digital_copy", "urgent"),
        infer=("размер блока по document_type (только с подтверждением)",),
        never_infer=("число штук без пакета", "требования документа"),
        clarification="На какой документ? Снимаем здесь или печатать ваш готовый файл?",
        dialog_rules=("R1", "R2"),
        automation="PARTIAL",
        human_check=True,
        knowledge=(
            "пакет 3×4: 6 шт — 250 ₽, доп. копия 3 шт — 50 ₽ (ФотоДок, CR-33)",
            "пакеты варьируются: 2 по 100 ₽, 4 — 150 ₽, 6 — 200 ₽ (CR-79)",
            "срок: от 5 минут до суток (CR-78)",
            "учебные комплекты: «3 комплекта для 3 ВУЗов» (CR-79)",
        ),
        notes=("съёмка офлайн; пакет варьируется 200–650 ₽",),
    ),
    AssistantIntentSpec(
        id="document_photo_from_file",
        title="Фото на документы: печать готового файла",
        mvp=MvpPriority.P0,
        category="photo",
        phrases=(
            "делаю сам дома... потом на флешку, иду распечатывать в ближайший пункт",  # CR-03
            "прислать онлайн готовое фото в хорошем качестве",  # Кадр Сургут (02_services.md)
        ),
        source_cr=("CR-03",),
        phrases_verified=True,
        required_params=("document_type", "quantity", "files"),
        optional_params=("quality_check",),
        infer=(),
        never_infer=("требования документа",),
        clarification="Печатаем как есть, без коррекции?",
        dialog_rules=("R4",),
        automation="AUTO",
        human_check=False,
        notes=("отдельный intent от document_photo (CR-03, A); «прислать онлайн…» — 02_services.md",),
    ),
    AssistantIntentSpec(
        id="photo_print_mobile",
        title="Печать фото с телефона/мессенджера",
        mvp=MvpPriority.P0,
        category="photo",
        phrases=(
            "Даже с телефона можно",  # CR-02
            "Обязательно ли для распечатки цветных картинок в центре печати имень флешку? Можно просто с телефона им скинуть",  # CR-82 (otvet.mail.ru)
            "Как распечатать файл документа, если он только на телефоне? Флешки нет, оригинала документа тоже",  # CR-83 (otvet.mail.ru)
        ),
        source_cr=("CR-02", "CR-82", "CR-83"),
        phrases_verified=True,
        required_params=("size", "quantity", "files"),
        optional_params=("paper",),
        infer=("источник файлов = телефон/мессенджер",),
        never_infer=("кадрирование",),
        clarification="Сколько и какого размера? Пришлите файлы сюда.",
        dialog_rules=("R1", "R3"),
        automation="AUTO",
        human_check=False,
        knowledge=(
            "приём с телефона/носителя может идти с наценкой ~50 ₽ (CR-82)",
            "мессенджеры сжимают картинки — предупреждать о качестве (CR-82)",
        ),
        notes=("MVP-сценарий 8; подвид photo_print",),
    ),
    AssistantIntentSpec(
        id="business_cards",
        title="Визитки",
        mvp=MvpPriority.P1,
        category="polygraphy",
        phrases=(
            "Где в Сургуте заказать визитки недорого?",  # CR-07 (otvet.mail.ru)
            "Печатала визитки. Отдала 700 за 100 штук(минимальный тираж)",  # CR-13 (2ГИС, Полиграф Нвартовск)
            "Каков размер визитки 90х50 мм в пикселях?",  # CR-63 (Google PAA)
        ),
        source_cr=("CR-07", "CR-13", "CR-63"),
        phrases_verified=True,
        required_params=("quantity", "artwork_ready"),
        optional_params=("sides", "paper", "lamination", "corners"),
        infer=("двусторонность по макету (проверкой файла)",),
        never_infer=("минимальный тираж",),
        clarification="Сколько штук и макет уже готов?",
        dialog_rules=("R4", "R5"),
        automation="PARTIAL",
        human_check=True,
        knowledge=(
            "Word-макет → отказ («ни одна типография не возьмётся», CR-08)",
            "визитка 90×50 мм + 2 мм под обрез; лучше TIFF из Corel/Illustrator (CR-09)",
        ),
        notes=("Word-макет → отказ (CR-08)",),
    ),
    AssistantIntentSpec(
        id="business_cards_design",
        title="Визитки: нужен дизайн",
        mvp=MvpPriority.P1,
        category="design",
        phrases=(),
        phrases_verified=False,
        source_cr=(),
        required_params=("quantity", "brief"),
        optional_params=("deadline", "references"),
        infer=(),
        never_infer=("объём работ",),
        clarification="Что должно быть на визитке? Есть примеры/пожелания?",
        dialog_rules=("R9",),
        automation="HUMAN",
        human_check=True,
        notes=("MVP-сценарий 11; передача дизайнеру; верифицированных фраз в корпусе нет",),
    ),
    AssistantIntentSpec(
        id="mug_print_single",
        title="Кружка с печатью (1 шт)",
        mvp=MvpPriority.P1,
        category="souvenir",
        phrases=(
            "При заказе 1 штуки - 850 р",  # express72 (P38 в 03_price_lists.csv)
            "напечатала кружки на 23 февраля всем коллегам",  # CR-99 (zoon-отзыв)
        ),
        source_cr=("CR-99",),
        phrases_verified=True,
        required_params=("quantity",),
        optional_params=("artwork", "base_owner"),
        infer=(),
        never_infer=("цену тиражной ступени (1 шт ≠ 15+)",),
        clarification="Одна кружка — 850 ₽. Макет есть?",
        dialog_rules=("R6",),
        automation="PARTIAL",
        human_check=False,
        notes=("прайс-фраза express72 (03_price_lists.csv P38); CR-99 — реальный заказ-контекст",),
    ),
    AssistantIntentSpec(
        id="mug_print_bulk",
        title="Кружки с печатью (15+)",
        mvp=MvpPriority.P1,
        category="souvenir",
        phrases=(
            "от 15 штук цена 450 рублей",  # express72 (P39 в 03_price_lists.csv)
            "Заказывали кружку и футболку, качество на высшем уровне",  # CR-100 (zoon-сниппет, Нвартовск)
        ),
        source_cr=("CR-100",),
        phrases_verified=True,
        required_params=("quantity", "artwork"),
        optional_params=("base_owner",),
        infer=(),
        never_infer=(),
        clarification="От 15 штук — по 450 ₽. Сколько нужно и с каким макетом?",
        dialog_rules=("R6",),
        automation="PARTIAL",
        human_check=False,
        notes=("прайс-фраза express72 (03_price_lists.csv P39); CR-100 — комбо кружка+футболка",),
    ),
    AssistantIntentSpec(
        id="tshirt_print",
        title="Печать на футболках",
        mvp=MvpPriority.P1,
        category="souvenir",
        phrases=(
            "Заказывала футболку с двух сторонней печатью… заказывала 46-48 р., а по ощущениям 44 р.",  # CR-92 (ФотоСфера)
            "Заказывали кружку и футболку, качество на высшем уровне",  # CR-100 (zoon-сниппет)
        ),
        source_cr=("CR-92", "CR-100"),
        phrases_verified=True,
        required_params=("print_zone", "quantity"),
        optional_params=("base_owner", "size_clothes"),
        infer=(),
        never_infer=("технологию нанесения (зависит от ткани)",),
        clarification="Своё футболка или наша? Что и где печатаем (грудь/спина)?",
        dialog_rules=("R7",),
        automation="PARTIAL",
        human_check=True,
        knowledge=("двусторонняя печать — опция; размерная сетка ±2 размера (CR-92)",),
        notes=("«Сколько держится принт на футболке?» — PAA-фраза (B), без CR-номера; см. 08_synonyms.md",),
    ),
    AssistantIntentSpec(
        id="banner",
        title="Баннер (широкоформатная печать)",
        mvp=MvpPriority.P2,
        category="outdoor",
        phrases=(
            "Это так и называетяся - печать на баннере. И попросите люверсы по периметру",  # CR-10 (otvet.mail.ru)
            "Сколько стоит баннер 2 на 3?",  # CR-62 (Google PAA)
            "Что такое люверсы у баннера?",  # CR-61 (Google PAA)
        ),
        source_cr=("CR-10", "CR-61", "CR-62"),
        phrases_verified=True,
        required_params=("size_m2", "material"),
        optional_params=("eyelets", "quantity", "files", "deadline", "montage"),
        infer=("площадь из размера (автоматически)",),
        never_infer=("материал", "люверсы", "крепёж"),
        clarification="Какой размер и куда повесим? Люверсы нужны? Файл есть?",
        dialog_rules=("R1", "R7"),
        automation="PARTIAL",
        human_check=True,
        knowledge=("«люверсы» клиенту-новичку предлагать как опцию (CR-10, CR-61)",),
        notes=("ценообразование баннера: размер + плотность + доработки (FAQ y-ivanycha.ru, 08_synonyms.md)",),
    ),
    AssistantIntentSpec(
        id="sign_pvc",
        title="Табличка ПВХ/акрил/АКП",
        mvp=MvpPriority.P2,
        category="outdoor",
        phrases=(),
        phrases_verified=False,
        source_cr=(),
        required_params=("material", "size", "content"),
        optional_params=("mounting", "sides"),
        infer=(),
        never_infer=("материал (разброс цены ×4)",),
        clarification="Из какого материала (ПВХ/акрил/металл)? Какой размер и что написать?",
        dialog_rules=("R7",),
        automation="HUMAN",
        human_check=True,
        notes=(
            "верифицированных фраз в корпусе нет — язык заявок совпадает с address_plate (CR-111); intent HUMAN: разброс цены по материалу ×4",
        ),
    ),
    AssistantIntentSpec(
        id="address_plate",
        title="Адресная табличка",
        mvp=MvpPriority.P2,
        category="outdoor",
        phrases=(
            "адресную табличку из алюминиевого композита(АКП), пластика(ПВХ), акрила",  # CR-111 (Avito НфЮ)
        ),
        source_cr=("CR-111",),
        phrases_verified=True,
        required_params=("material",),
        optional_params=("size", "mounting"),
        infer=(),
        never_infer=("крепёж",),
        clarification="Из какого материала? Куда крепим?",
        dialog_rules=("R7",),
        automation="HUMAN",
        human_check=True,
        notes=("CR-111 — язык объявления; intent остаётся HUMAN — заказ требует замера/согласования",),
    ),
    AssistantIntentSpec(
        id="bind",
        title="Переплёт/брошюровка на пружину",
        mvp=MvpPriority.P1,
        category="postprint",
        phrases=(
            "Сколько стоит переплёт? Переплёт на пружину — от 550 ₸ за экземпляр",  # CR-68 (FAQ global-print.kz)
            "Обязательно ли нужен переплет для дипломной работы? И возможно ли это не делать?",  # CR-84 (otvet.mail.ru)
        ),
        source_cr=("CR-68", "CR-84"),
        phrases_verified=True,
        required_params=("binding_type", "sheet_count"),
        optional_params=("cover", "embossing"),
        infer=(),
        never_infer=(),
        clarification="Пружина или твёрдый переплёт? Сколько листов?",
        automation="AUTO",
        human_check=False,
        knowledge=(
            "переплёт диплома может быть обязателен по требованиям вуза (CR-84)",
            "цена может разбиваться: переплёт 400 + зашивание 600 (CR-84)",
        ),
        notes=("«Можно ли перешить диплом?» — PAA-фраза (B), без CR-номера; см. 08_synonyms.md",),
    ),
    AssistantIntentSpec(
        id="photo_print_large",
        title="Печать фото большого формата (А3+)",
        mvp=MvpPriority.P1,
        category="photo",
        phrases=(
            "печать фотографий до А1",  # CR-11 (VK Фото Мир НфЮ, язык услуг)
            "Нужна была срочно широкоформатная печать для выставки, и я очень волновалась, успеют",  # CR-102 (zoon-сниппет)
            "Сколько времени нужно ждать для распечатки листа А1 в Магазине? 3 листа чертежа А1 и 1 лист плаката цветной А1",  # CR-85 (otvet.mail.ru)
        ),
        source_cr=("CR-11", "CR-85", "CR-102"),
        phrases_verified=True,
        required_params=("size", "files"),
        optional_params=("paper", "framing"),
        infer=(),
        never_infer=("технологию (фотолаб vs плоттер)",),
        clarification="Какой размер точно? Файл в хорошем разрешении есть?",
        dialog_rules=("R4",),
        automation="PARTIAL",
        human_check=True,
        knowledge=("печать А1 при заказчике ~20 минут (CR-85)",),
    ),
    AssistantIntentSpec(
        id="photo_multi_format_order",
        title="Комбинированный фото-заказ (несколько форматов)",
        mvp=MvpPriority.P1,
        category="photo",
        phrases=(
            "Можно ли заказать печать фотографий разных размеров в одном заказе?",  # CR-28 (ФотоОтель FAQ)
            "к фотографиям заказывала магнитики, в редакторе сама добавила надпись",  # CR-51 (ФотоСфера)
        ),
        source_cr=("CR-28", "CR-51"),
        phrases_verified=True,
        required_params=(),
        optional_params=(),
        infer=(),
        never_infer=(),
        clarification="Перечислите позиции: сколько и каких размеров.",
        dialog_rules=("R8",),
        automation="PARTIAL",
        human_check=False,
        notes=("контейнер мультизаказа; items[] по 13_order_schema.json; CR-51 — фото+магнитики в одном заказе",),
    ),
    AssistantIntentSpec(
        id="passport_photo_bring_file_advice",
        title="Онбординг новичка (что принести, как проходит)",
        mvp=MvpPriority.P0,
        category="dialog",
        phrases=(
            "Что нужно принести для фотопечати в салоне?",  # CR-20
            "Флешка и больше ничего",  # ответ из треда CR-02
            "иначе фото будут либо обрезаны, либо напечатаны с полями",  # предупреждение из треда CR-02
        ),
        source_cr=("CR-02", "CR-20"),
        phrases_verified=True,
        required_params=(),
        optional_params=(),
        infer=(),
        never_infer=(),
        clarification="Принесите флешку или пришлите файлы в чат — остальное подскажем.",
        dialog_rules=("R3",),
        automation="AUTO",
        human_check=False,
        notes=("скрипт-подсказка, не заказ",),
    ),
)

#: Идентификаторы TOP-20 в порядке регистрации.
INTENT_IDS_TOP20: tuple[str, ...] = tuple(s.id for s in _TOP20)


def build_default_registry() -> AssistantIntentRegistry:
    """Собирает реестр из TOP-20 MVP (идемпотентно — новый реестр каждый раз)."""
    registry = AssistantIntentRegistry()
    for spec in _TOP20:
        registry.register(spec)
    return registry


# --------------------------------------------------------------------------
# Мини-хелперы диалога (без NLP: точный/нормализованный матчинг по словарю).
# Полный разбор вольного текста — следующий аддитивный шаг.
# --------------------------------------------------------------------------

def match_intent(registry: AssistantIntentRegistry, text: str) -> str | None:
    """Ищет intent по реальным фразам/подстрокам (без фантазий).

    Возвращает id первого совпавшего intent или None. Совпадение — по
    подстроке (регистронезависимо) по фразам-эвиденциям; это осознанно
    узкий матчинг: широкий NLP — вне скоупа данного шага.
    """
    lowered = text.lower().strip()
    if not lowered:
        return None
    for spec in registry._items.values():  # noqa: SLF001 — внутренний обход, порядок регистрации
        for phrase in spec.phrases:
            probe = phrase.lower()
            # Служебные пометки источника в комментарии не участвуют в матчинге;
            # прайс-фразы с тире-ценой усекаются до «—».
            probe = probe.split("(")[0].split(" — ")[0].strip(" —-«»\"'")
            if len(probe) >= 12 and probe in lowered:
                return spec.id
    return None


def clarification_for(registry: AssistantIntentRegistry, intent_id: str) -> str:
    """Возвращает минимальный уточняющий вопрос intent (§18 промта)."""
    return registry.get(intent_id).clarification


def missing_required(
    registry: AssistantIntentRegistry,
    intent_id: str,
    known_params: set[str] | frozenset[str],
) -> tuple[str, ...]:
    """REQUIRED-параметры, которых нет среди известных (§16 промта)."""
    spec = registry.get(intent_id)
    return tuple(p for p in spec.required_params if p not in known_params)


def intent_sources(registry: AssistantIntentRegistry) -> dict[str, tuple[str, ...]]:
    """CR-ссылки по каждому intent (трассируемость в корпус research/04)."""
    return {spec.id: spec.source_cr for spec in registry._items.values()}  # noqa: SLF001


def warnings_for(registry: AssistantIntentRegistry, intent_id: str) -> tuple[str, ...]:
    """Знания-предупреждения intent (knowledge), обязанные к озвучиванию.

    Источник — research/09_automation.md + CR-корпус (CR-08 Word-макет,
    CR-109/110 ламинация ЗАГС, CR-82 сжатие в мессенджерах и т.п.).
    Возвращает пустой кортеж для intents без знаний — это валидно.
    """
    return registry.get(intent_id).knowledge


# --------------------------------------------------------------------------
# Синоним-слой (research/08_synonyms.md): токен → intent id.
# Закрытый словарь (ANTI-6b): каждый токен маппится ТОЛЬКО на id из
# TOP-20-реестра; intent'ы исследования вне TOP-20 честно перечислены в
# UNMAPPED_RESEARCH_INTENTS (не теряются, но и не попадают в замкнутый
# словарь без интента-цели). Правило §21 «не сливать разные услуги»
# соблюдается: photo_print ≠ document_photo, copy ≠ print_document,
# sign ≠ signage — у каждого свои токены.
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class SynonymToken:
    """Один токен словаря (research/08_synonyms.md)."""

    token: str
    intent_id: str  # обязан существовать в TOP-20 (проверяется тестом)
    confidence: str  # A | B | C — уровень уверенности из 08_synonyms.md


@dataclass(frozen=True)
class SynonymMatch:
    """Результат матчинга токена: intent + вернувший токен."""

    intent_id: str
    token: str
    confidence: str


#: Словарь: токен (lowercase) → intent_id TOP-20. Уверенность — из 08.
SYNONYM_TABLE: tuple[SynonymToken, ...] = (
    # --- фотопечать (08: «распечатать фото/фотки/фотокарточки», A) ---
    SynonymToken("распечатать фото", "photo_print", "A"),
    SynonymToken("распечатать фотки", "photo_print", "A"),
    SynonymToken("распечатать фотокарточки", "photo_print", "A"),
    SynonymToken("печать фотографий", "photo_print", "A"),
    SynonymToken("печать фото", "photo_print", "A"),
    SynonymToken("фотки 10 15", "photo_print", "B"),  # опущен знак ×
    SynonymToken("с телефона", "photo_print_mobile", "B"),
    SynonymToken("с флешки", "photo_print", "B"),
    # --- фото на документы (08: A) ---
    SynonymToken("фото на документы", "document_photo", "A"),
    SynonymToken("фото на паспорт", "document_photo", "A"),
    SynonymToken("фото на загран", "document_photo", "A"),
    SynonymToken("фото на визу", "document_photo", "A"),
    SynonymToken("фото на права", "document_photo", "A"),
    SynonymToken("фотка на паспорт", "document_photo", "B"),
    SynonymToken("фотографировать на паспорт", "document_photo", "B"),
    SynonymToken("3 на 4", "document_photo", "A"),
    SynonymToken("3х4", "document_photo", "A"),
    SynonymToken("3*4", "document_photo", "A"),
    # --- ксерокопия / копия (08: B) ---
    SynonymToken("ксерокс", "copy_bw", "B"),
    SynonymToken("ксерокопия", "copy_bw", "B"),
    SynonymToken("сделать копию", "copy_bw", "B"),
    # --- печать документов (08: C) ---
    SynonymToken("распечатать доки", "print_document", "C"),
    SynonymToken("распечатать реферат", "print_document", "C"),
    SynonymToken("распечатать курсовую", "print_document", "C"),
    SynonymToken("распечатать документ", "print_document", "C"),
    # --- сканирование / ламинация ---
    SynonymToken("отсканировать", "scan", "B"),
    SynonymToken("сканирование", "scan", "B"),
    SynonymToken("заламинировать", "laminate", "A"),
    SynonymToken("ламинация", "laminate", "A"),
    # --- переплёт (08: B) ---
    SynonymToken("прошить", "bind", "B"),
    SynonymToken("переплести", "bind", "B"),
    SynonymToken("переплёт", "bind", "B"),
    SynonymToken("переплет", "bind", "B"),
    SynonymToken("пружина", "bind", "B"),
    # --- визитки (08: A) ---
    SynonymToken("визитки", "business_cards", "A"),
    SynonymToken("визиточка", "business_cards", "A"),
    # --- баннер (08: A/C) ---
    SynonymToken("баннер", "banner", "A"),
    SynonymToken("банер", "banner", "A"),  # частая опечатка
    SynonymToken("растяжка", "banner", "C"),
    SynonymToken("печать на баннере", "banner", "A"),
    # «люверсы» в 08 — параметр finishing=eyelets; до появления параметр-матчера
    # мостим токен на banner (клиент с люверсами имеет в виду баннер).
    SynonymToken("люверсы", "banner", "A"),
    # --- таблички (08: B/C; sign ≠ signage — §21) ---
    SynonymToken("табличка на дверь", "sign_pvc", "B"),
    SynonymToken("адресная табличка", "address_plate", "C"),
    # --- сувениры (08: B) ---
    SynonymToken("кружка с фото", "mug_print_single", "B"),
    SynonymToken("кружка с логотипом", "mug_print_bulk", "B"),
    SynonymToken("печать на кружках", "mug_print_bulk", "B"),
    SynonymToken("футболка с принтом", "tshirt_print", "B"),
    SynonymToken("футболка с фото", "tshirt_print", "B"),
    # --- крупный формат (CR-11: «печать фотографий до А1») ---
    SynonymToken("печать фотографий до а1", "photo_print_large", "B"),
    SynonymToken("широкоформатная печать", "photo_print_large", "B"),
)

#: Intent'ы исследования (12_intents.json), НЕ попавшие в TOP-20-словарь.
#: Честный учёт (§2): не теряются, ждут отдельного решения о включении.
UNMAPPED_RESEARCH_INTENTS: tuple[str, ...] = (
    "flyers",
    "stamp",
    "design",
    "sign",
    "signage",
    "photo_restore",
    "photo_book",
    "photo_canvas",
    "photo_digitize",
)

#: Токены-носители файлов (CR-82): фотопечать с этих источников = mobile-подвид.
_PHONE_SOURCE_TOKENS: tuple[str, ...] = (
    "с телефона",
    "с телефона,",
    "с вотсапа",
    "из ватсапа",
    "из мессенджера",
    "с телефона в чат",
)


def match_synonym(text: str) -> SynonymMatch | None:
    """Матчит вольный текст по закрытому словарю 08_synonyms.md.

    Без NLP: нормализованный текст (lowercase) проверяется на вхождение
    токена; побеждает самый длинный совпавший токен (специфичное важнее
    общего). Композиция источника: photo_print + токен-носитель («с
    телефона» и т.п.) → photo_print_mobile — источник файла влияет на
    цену/путь приёма (CR-82). Ничего не нашли — None (вопрос клиенту,
    не фантазия §2).
    """
    lowered = text.lower().strip()
    if not lowered:
        return None
    best: SynonymMatch | None = None
    for entry in SYNONYM_TABLE:
        if entry.token in lowered:
            if best is None or len(entry.token) > len(best.token):
                best = SynonymMatch(
                    intent_id=entry.intent_id,
                    token=entry.token,
                    confidence=entry.confidence,
                )
    # Композиция источника (CR-82): фотопечать + носитель = мобильный подвид.
    if best is not None and best.intent_id == "photo_print":
        if any(src in lowered for src in _PHONE_SOURCE_TOKENS):
            return SynonymMatch(
                intent_id="photo_print_mobile",
                token=f"{best.token}+источник",
                confidence="B",
            )
    return best
