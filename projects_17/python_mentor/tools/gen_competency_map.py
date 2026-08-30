"""Генератор configs/competency_map.yaml v0.1 (Phase B+C, Шаг 3).

Гарантирует строгий набор ключей (схема bluepup §1), уникальность id,
валидность prerequisites. Запуск: python3 scripts_01/gen_competency_map.py
"""
import sys
import yaml

REQUIRED = {
    "id", "name", "description", "category", "prerequisites",
    "understand_criteria", "can_do_criteria", "typical_errors",
    "verification_exercise", "project_marker", "exercism_concepts",
}
CATEGORIES = {
    "python_fundamentals", "control_flow", "collections", "functions",
    "strings", "exceptions", "modules", "oop", "files_io", "testing",
    "code_structure",
}

# Ключи задаются только внутри списка; каждый item — валидная компетенция.
COMPETENCIES = [
    # --- python_fundamentals ---
    {
        "id": "variables",
        "name": "Variables and assignment",
        "description": "Переменные, оператор присваивания, имена, динамическая типизация.",
        "category": "python_fundamentals",
        "prerequisites": [],
        "understand_criteria": "Объяснить, что переменная — имя для объекта, и что тип не фиксирован в имени.",
        "can_do_criteria": "Создавать и переприсваивать переменные, именовать по PEP-8, не путать '=' и '=='.",
        "typical_errors": ["use_before_assignment", "mutable_default_argument"],
        "verification_exercise": "guidos-gorgeous-lasagna",
        "project_marker": "Скрипт, где данные передаются между шагами через переменные.",
        "exercism_concepts": ["basics"],
    },
    {
        "id": "primitive-types",
        "name": "Primitive types (int, float, bool, None)",
        "description": "Целые и вещественные числа, булевы значения, None, преобразование типов.",
        "category": "python_fundamentals",
        "prerequisites": ["variables"],
        "understand_criteria": "Различие int/float/None и принцип преобразования типов.",
        "can_do_criteria": "Использовать int(), float(), str(), bool(); понимать /, //, %.",
        "typical_errors": ["integer_division_confusion", "string_plus_int"],
        "verification_exercise": "currency-exchange",
        "project_marker": "Калькулятор с типичным пользовательским вводом.",
        "exercism_concepts": ["numbers", "none", "number-variations"],
    },
    {
        "id": "expressions",
        "name": "Expressions and operators",
        "description": "Арифметические операторы, приоритет, скобки, сравнения.",
        "category": "python_fundamentals",
        "prerequisites": ["primitive-types"],
        "understand_criteria": "Объяснить приоритет операторов и роль скобок.",
        "can_do_criteria": "Писать выражения с предсказуемым порядком вычисления, корректно сравнивать значения.",
        "typical_errors": ["operator_precedence", "chained_compare_misuse"],
        "verification_exercise": "difference-of-squares",
        "project_marker": "Функция с математическими расчётами (скидка, площадь).",
        "exercism_concepts": ["comparisons", "rich-comparisons"],
    },
    {
        "id": "boolean-logic",
        "name": "Boolean logic and truthiness",
        "description": "and/or/not, truthiness, короткое замыкание.",
        "category": "python_fundamentals",
        "prerequisites": ["expressions"],
        "understand_criteria": "Объяснить truthiness (0, '', [], None — falsy) и логику И/ИЛИ/НЕ.",
        "can_do_criteria": "Строить условия с and/or/not и скобками, упрощать сложные выражения.",
        "typical_errors": ["confusing_and_or", "truthiness_gotcha"],
        "verification_exercise": "ghost-gobble-arcade-game",
        "project_marker": "Валидация входных данных с несколькими условиями.",
        "exercism_concepts": ["bools", "comparisons"],
    },
    # --- control_flow ---
    {
        "id": "conditionals",
        "name": "Conditionals (if/elif/else)",
        "description": "Ветвление исполнения, elif-цепочки, ранний выход.",
        "category": "control_flow",
        "prerequisites": ["boolean-logic"],
        "understand_criteria": "Объяснить выбор одного блока из многих и пользу раннего return.",
        "can_do_criteria": "Писать if/elif/else без лишней вложенности, покрывать основные ветки.",
        "typical_errors": ["nested_ifs", "missing_default_branch"],
        "verification_exercise": "log-levels",
        "project_marker": "Классификатор (например, таблица оценок).",
        "exercism_concepts": ["conditionals"],
    },
    {
        "id": "loops",
        "name": "Loops (for, while)",
        "description": "for по коллекции, range, while с условием, break/continue.",
        "category": "control_flow",
        "prerequisites": ["conditionals"],
        "understand_criteria": "Различие for/while и критерий выбора.",
        "can_do_criteria": "Обходить коллекции, писать while с явным условием завершения, применять break/continue осмысленно.",
        "typical_errors": ["infinite_loop", "mutate_while_iterating"],
        "verification_exercise": "making-the-grade",
        "project_marker": "Постраничный вывод, таблица умножения.",
        "exercism_concepts": ["loops", "iteration"],
    },
    {
        "id": "comprehensions",
        "name": "Comprehensions (list/dict/set/gen)",
        "description": "Однострочные comprehension, условия внутри, читаемость.",
        "category": "control_flow",
        "prerequisites": ["loops", "lists"],
        "understand_criteria": "Определить, когда comprehension уместен (простая логика), а когда нет.",
        "can_do_criteria": "Переписывать for+append в comprehension и обратно, использовать dict/set comprehensions.",
        "typical_errors": ["comprehension_side_effects", "too_complex_comprehension"],
        "verification_exercise": "flatten-array",
        "project_marker": "Извлечение полей из списка словарей.",
        "exercism_concepts": ["list-comprehensions", "other-comprehensions"],
    },
    # --- collections ---
    {
        "id": "lists",
        "name": "Lists",
        "description": "Создание, индексация, срезы, методы, вложенные списки.",
        "category": "collections",
        "prerequisites": ["expressions"],
        "understand_criteria": "Различие list и tuple; ссылочная природа list.",
        "can_do_criteria": "Создавать/изменять/срезать списки, работать с вложенными.",
        "typical_errors": ["index_out_of_range", "aliasing_shared_list"],
        "verification_exercise": "list-ops",
        "project_marker": "Обработка входного массива данных.",
        "exercism_concepts": ["lists", "list-methods", "sequences", "aliasing"],
    },
    {
        "id": "tuples",
        "name": "Tuples",
        "description": "Неизменяемые последовательности, распаковка, возврат нескольких значений.",
        "category": "collections",
        "prerequisites": ["lists"],
        "understand_criteria": "Чем tuple отличается от list и зачем он нужен.",
        "can_do_criteria": "Использовать tuple для фиксированной структуры, распаковывать значения.",
        "typical_errors": ["try_mutate_tuple", "tuple_vs_list_confusion"],
        "verification_exercise": "cater-waiter",
        "project_marker": "Возврат пары значений из функции.",
        "exercism_concepts": ["tuples"],
    },
    {
        "id": "dicts",
        "name": "Dicts",
        "description": "key→value, методы get/setdefault/items, словарь, порядок вставки.",
        "category": "collections",
        "prerequisites": ["lists"],
        "understand_criteria": "Почему поиск по ключу O(1) и когда dict вместо list.",
        "can_do_criteria": "Работать через методы, обходить items(), строить counter.",
        "typical_errors": ["key_error_unhandled", "dict_where_list_misuse"],
        "verification_exercise": "inventory-management",
        "project_marker": "Подсчёт, кэш, маппинг выбора.",
        "exercism_concepts": ["dicts", "dict-methods"],
    },
    {
        "id": "sets",
        "name": "Sets",
        "description": "Уникальность, union/intersection/difference, membership.",
        "category": "collections",
        "prerequisites": ["lists"],
        "understand_criteria": "Когда set уместнее list (уникальность, O(1) membership).",
        "can_do_criteria": "Составлять операции множеств, фильтровать дубликаты.",
        "typical_errors": ["unhashable_element", "set_literal_vs_dict"],
        "verification_exercise": "restaurant-rozalynn",
        "project_marker": "Проверка пересечения, фильтрация дубликатов.",
        "exercism_concepts": ["sets"],
    },
    # --- functions ---
    {
        "id": "functions",
        "name": "Functions (definition, return)",
        "description": "def, параметры, return, вызов, чистая функция, документация.",
        "category": "functions",
        "prerequisites": ["conditionals", "loops"],
        "understand_criteria": "Зачем разбивать код, польза чистой функции без сайд-эффектов.",
        "can_do_criteria": "Писать функции с явным входом/выходом и однозначным возвратом.",
        "typical_errors": ["no_return_expected", "hidden_side_effect"],
        "verification_exercise": "hello-world",
        "project_marker": "CLI с функциями-шагами.",
        "exercism_concepts": ["functions", "functional-tools", "higher-order-functions", "anonymous-functions"],
    },
    {
        "id": "function-parameters",
        "name": "Parameters, defaults, *args/**kwargs",
        "description": "Позиционные и именованные аргументы, дефолты, распаковка аргументов.",
        "category": "functions",
        "prerequisites": ["functions", "tuples"],
        "understand_criteria": "Почему mutable default — антипаттерн (None + if идиома).",
        "can_do_criteria": "Проектировать сигнатуры со здоровыми дефолтами, различать args и kwargs.",
        "typical_errors": ["mutable_default_argument", "kwargs_misuse"],
        "verification_exercise": "two-fer",
        "project_marker": "Функция API с параметрами по умолчанию.",
        "exercism_concepts": ["function-arguments", "unpacking-and-multiple-assignment"],
    },
    {
        "id": "scope-decomposition",
        "name": "Scope and decomposition",
        "description": "Локальная область видимости, global/nonlocal, разбиение монолита.",
        "category": "functions",
        "prerequisites": ["functions"],
        "understand_criteria": "Где заканчивается видимость переменной и почему маленькие функции лучше.",
        "can_do_criteria": "Разбить монолитный скрипт (40+ строк) на функции с одной ответственностью.",
        "typical_errors": ["global_mutation", "one_long_function"],
        "verification_exercise": "matching-brackets",
        "project_marker": "Рефакторинг legacy-скрипта.",
        "exercism_concepts": ["unpacking-and-multiple-assignment"],
    },
    # --- strings ---
    {
        "id": "strings",
        "name": "Strings (immutable, slicing)",
        "description": "Неизменяемость, индексирование, срезы, f-strings.",
        "category": "strings",
        "prerequisites": ["primitive-types"],
        "understand_criteria": "Неизменяемость как источник багов (новая копия каждый раз).",
        "can_do_criteria": "Строить строки через f-strings, нарезать, сравнивать.",
        "typical_errors": ["mutation_attempt_immutable", "heavy_concatenation"],
        "verification_exercise": "reverse-string",
        "project_marker": "Формат-вывод отчёта.",
        "exercism_concepts": ["strings", "string-formatting"],
    },
    {
        "id": "string-methods",
        "name": "String methods (split/join/upper…)",
        "description": "Методы str, join вместо конкатенаций в цикле, парсинг простых форматов.",
        "category": "strings",
        "prerequisites": ["strings"],
        "understand_criteria": "Выразительность методов и почему join эффективнее.",
        "can_do_criteria": "Выбирать подходящий метод, join-ить список строк, парсить простой формат.",
        "typical_errors": ["loop_concat_instead_join", "case_sensitive_gotcha"],
        "verification_exercise": "isogram",
        "project_marker": "Парсер простого текстового формата.",
        "exercism_concepts": ["string-methods", "string-methods-splitting"],
    },
    # --- exceptions ---
    {
        "id": "exceptions",
        "name": "Exceptions (raise/handle/custom)",
        "description": "try/except/else/finally, raise, типы исключений, свои исключения.",
        "category": "exceptions",
        "prerequisites": ["functions", "conditionals"],
        "understand_criteria": "Обработка ошибок как управление сбоем, а не «чтобы не падало».",
        "can_do_criteria": "Писать конкретные except (не голый), raise с сообщением, свои классы.",
        "typical_errors": ["bare_except", "swallow_exception_silently"],
        "verification_exercise": "error-handling",
        "project_marker": "CLI с обработкой ввода.",
        "exercism_concepts": ["raising-and-handling-errors", "user-defined-errors"],
    },
    # --- modules ---
    {
        "id": "modules",
        "name": "Modules and imports",
        "description": "import, from import, пакеты, __main__ guard, stdlib.",
        "category": "modules",
        "prerequisites": ["functions"],
        "understand_criteria": "Различие между запуском файла и импортом.",
        "can_do_criteria": "Структурировать код в модули, понимать __main__ guard.",
        "typical_errors": ["import_circular", "side_effect_on_import"],
        "verification_exercise": "little-sisters-vocab",
        "project_marker": "Пакет из двух модулей.",
        "exercism_concepts": [],
    },
    # --- oop ---
    {
        "id": "classes",
        "name": "Classes, instances, methods",
        "description": "class, __init__, self, методы, атрибуты, repr/dataclass.",
        "category": "oop",
        "prerequisites": ["dicts", "functions"],
        "understand_criteria": "Модель «состояние + поведение» против словарей и функций.",
        "can_do_criteria": "Оформлять простой класс с init, методом и repr; понимать self.",
        "typical_errors": ["self_missing", "mutable_attribute_leak"],
        "verification_exercise": "ellens-alien-game",
        "project_marker": "Приложение с сущностями-объектами.",
        "exercism_concepts": ["classes", "class-customization", "dataclasses"],
    },
    {
        "id": "class-inheritance",
        "name": "Inheritance and composition",
        "description": "Наследование, super, переопределение, композиция как альтернатива.",
        "category": "oop",
        "prerequisites": ["classes"],
        "understand_criteria": "Когда наследование уместно, а когда композиция чище.",
        "can_do_criteria": "Строить небольшую иерархию, переопределять методы + super, предпочитать композицию.",
        "typical_errors": ["overuse_inheritance", "forget_super_init"],
        "verification_exercise": "diamond",
        "project_marker": "Иерархия фигур (площадь/периметр).",
        "exercism_concepts": ["class-inheritance", "class-composition"],
    },
    # --- files_io ---
    {
        "id": "files-io",
        "name": "File I/O",
        "description": "open/read/write, with-контекст, кодировки, pathlib basics.",
        "category": "files_io",
        "prerequisites": ["string-methods", "modules"],
        "understand_criteria": "Утечка файлового дескриптора и гарантия закрытия через with.",
        "can_do_criteria": "Читать/писать файлы через with, обрабатывать кодировку, базово использовать pathlib.",
        "typical_errors": ["file_not_closed", "wrong_encoding"],
        "verification_exercise": "word-count",
        "project_marker": "Утилита обработки текстового файла.",
        "exercism_concepts": ["with-statement"],
    },
    # --- testing ---
    {
        "id": "testing",
        "name": "Testing with pytest",
        "description": "pytest, fixtures, assert, параметризация, edge cases.",
        "category": "testing",
        "prerequisites": ["functions", "exceptions"],
        "understand_criteria": "Тесты как контракт кода; red/green цикл.",
        "can_do_criteria": "Писать юнит-тесты с assert и параметризацией, думать об edge cases.",
        "typical_errors": ["test_no_assert", "order_dependent_tests"],
        "verification_exercise": "pytest-мини-сют (создаётся при импорте corpus)",
        "project_marker": "Свой модуль с тестами.",
        "exercism_concepts": ["testing"],
    },
    # --- code_structure ---
    {
        "id": "code-structure",
        "name": "Code structure and linting basics",
        "description": "main-guard, именование, docstring, лимиты длины, type hints.",
        "category": "code_structure",
        "prerequisites": ["functions", "scope-decomposition"],
        "understand_criteria": "Качественный код отличается структурой; линтеры — диагностика, не evidence.",
        "can_do_criteria": "Держать модуль малые (<200 строк), функцию <20 строк, подписывать type hints публичных функций.",
        "typical_errors": ["line_too_long", "no_docstring_module"],
        "verification_exercise": "собственный сопровождаемый модуль",
        "project_marker": "Пример хорошо структурированного модуля.",
        "exercism_concepts": ["type-hinting"],
    },
    # --- дополнительные (покрытие Exercism concepts) ---
    {
        "id": "iterators-generators",
        "name": "Iterators and generators",
        "description": "iter/next, протокол итерирования, yield, generator expressions.",
        "category": "control_flow",
        "prerequisites": ["loops", "functions"],
        "understand_criteria": "Как for использует протокол iter и что такое ленивость.",
        "can_do_criteria": "Писать generator-функцию с yield, применять итерируемые протоколы.",
        "typical_errors": ["generator_consumed_once", "materialize_unbounded"],
        "verification_exercise": "series",
        "project_marker": "Построчный обработчик файла.",
        "exercism_concepts": ["iterators", "generators", "generator-expressions", "itertools"],
    },
    {
        "id": "unpacking",
        "name": "Unpacking and multiple assignment",
        "description": "a, b = b, a; *rest; распаковка в вызовы; walrus.",
        "category": "functions",
        "prerequisites": ["tuples", "function-parameters"],
        "understand_criteria": "Как работает распаковка кортежей и *rest.",
        "can_do_criteria": "Распаковывать в цикле, менять местами, распаковывать в вызовы.",
        "typical_errors": ["misordered_unpacking", "too_many_nested_unpacks"],
        "verification_exercise": "making-the-grade",
        "project_marker": "Обработка пар значений из данных.",
        "exercism_concepts": ["unpacking-and-multiple-assignment", "walrus-operator"],
    },
]


def main() -> int:
    errors: list[str] = []
    ids: set[str] = set()
    for i, c in enumerate(COMPETENCIES):
        keys = set(c)
        missing = REQUIRED - keys
        if missing:
            errors.append(f"[{i}] {c.get('id', '?')}: missing {sorted(missing)}")
        extra = keys - REQUIRED
        if extra:
            errors.append(f"[{i}] {c.get('id', '?' )}: extra keys {sorted(extra)}")
        if c.get("category") not in CATEGORIES:
            errors.append(f"[{i}] {c.get('id', '?')}: bad category {c.get('category')!r}")
        if not isinstance(c.get("typical_errors"), list):
            errors.append(f"[{i}] typical_errors must be list")
        if not isinstance(c.get("exercism_concepts"), list):
            errors.append(f"[{i}] exercism_concepts must be list")
        cid = c.get("id")
        if cid in ids:
            errors.append(f"[{i}] duplicate id {cid!r}")
        ids.add(cid)
    # Непроверенные prerequisites
    for c in COMPETENCIES:
        for p in c.get("prerequisites", []):
            if isinstance(p, str) and p not in ids:
                errors.append(f"{c['id']}: unknown prerequisite {p!r}")
    if errors:
        for e in errors:
            print("ERROR:", e)
        return 2
    doc = {
        "version": "0.1",
        "unmapped_exercism_concepts": [
            # Честный список непокрытых concepts v0.1 (advanced / вне ядра первой версии).
            # Каждый пункт — кандидат на новую компетенцию в Phase D+ (recursion, decorators, …).
            "binary-data",
            "binary-octal-hexadecimal",
            "bitflags",
            "bitwise-operators",
            "bytes",
            "class-interfaces",
            "collections",
            "complex-numbers",
            "context-manager-customization",
            "decorators",
            "descriptors",
            "enums",
            "fractions",
            "functools",
            "memoryview",
            "operator-overloading",
            "random",
            "recursion",
            "regular-expressions",
            "secrets",
            "text-processing",
            "unicode-regular-expressions",
        ],
        "competencies": COMPETENCIES,
    }
    with open("configs/competency_map.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False, width=100)
    print(f"OK: {len(COMPETENCIES)} competencies -> configs/competency_map.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())