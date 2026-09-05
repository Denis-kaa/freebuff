"""Formula Engine (7.md §24-25, §51).

Безопасный DSL для вычисляемых полей. НЕ использует eval/exec.

Разрешены:
- операции: + - * / ( )
- числа, строки, ссылки на поля (deadline, quantity, unit_price, ...)
- функции-whitelist: IF, SUM, MIN, MAX, DATE_DIFF, TODAY, ROUND

Pipeline (7.md §51):
1. parse — лексер + рекурсивный спуск → AST
2. validate — только whitelist функций/операторов
3. eval — типизированное значение
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable, Optional

# --- Исключения -----------------------------------------------------------
class FormulaError(ValueError):
    pass


# --- Лексер ---------------------------------------------------------------
class Token:
    __slots__ = ("kind", "value", "pos")

    def __init__(self, kind: str, value: Any, pos: int):
        self.kind = kind  # NUM | STR | IDENT | OP | LPAREN | RPAREN | COMMA | EOF
        self.value = value
        self.pos = pos


def tokenize(src: str) -> list[Token]:
    tokens: list[Token] = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c.isspace():
            i += 1
            continue
        if c.isdigit() or (c == "-" and i + 1 < n and (src[i + 1].isdigit() or src[i + 1] == ".")):
            # число (включая отрицательное в позиции числа)
            j = i + 1
            while j < n and (src[j].isdigit() or src[j] == "."):
                j += 1
            try:
                val = float(src[i:j])
            except ValueError:
                raise FormulaError(f"Неверное число на позиции {i}")
            tokens.append(Token("NUM", val, i))
            i = j
            continue
        if c == '"' or c == "'":
            quote = c
            j = i + 1
            buf = []
            while j < n and src[j] != quote:
                buf.append(src[j])
                j += 1
            if j >= n:
                raise FormulaError("Незакрытая строка")
            tokens.append(Token("STR", "".join(buf), i))
            i = j + 1
            continue
        if c.isalpha() or c == "_":
            j = i + 1
            while j < n and (src[j].isalnum() or src[j] == "_"):
                j += 1
            tokens.append(Token("IDENT", src[i:j], i))
            i = j
            continue
        if c == "(":
            tokens.append(Token("LPAREN", c, i)); i += 1; continue
        if c == ")":
            tokens.append(Token("RPAREN", c, i)); i += 1; continue
        if c == ",":
            tokens.append(Token("COMMA", c, i)); i += 1; continue
        if c in "+-*/":
            tokens.append(Token("OP", c, i)); i += 1; continue
        raise FormulaError(f"Неизвестный символ '{c}' на позиции {i}")
    tokens.append(Token("EOF", None, n))
    return tokens


# --- AST ------------------------------------------------------------------
@dataclass
class BinOp:
    op: str
    left: Any
    right: Any


@dataclass
class Number:
    value: float


@dataclass
class StrLit:
    value: str


@dataclass
class FieldRef:
    name: str


@dataclass
class FuncCall:
    name: str
    args: list[Any]


# --- Парсер (рекурсивный спуск) -------------------------------------------
class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def next(self) -> Token:
        t = self.tokens[self.pos]
        self.pos += 1
        return t

    def expect(self, kind: str) -> Token:
        t = self.next()
        if t.kind != kind:
            raise FormulaError(f"Ожидался {kind}, найден {t.kind}")
        return t

    def parse(self) -> Any:
        node = self.expr()
        if self.peek().kind != "EOF":
            raise FormulaError("Лишние символы после выражения")
        return node

    def expr(self) -> Any:
        return self.add_sub()

    def add_sub(self) -> Any:
        node = self.mul_div()
        while self.peek().kind == "OP" and self.peek().value in ("+", "-"):
            op = self.next().value
            right = self.mul_div()
            node = BinOp(op, node, right)
        return node

    def mul_div(self) -> Any:
        node = self.unary()
        while self.peek().kind == "OP" and self.peek().value in ("*", "/"):
            op = self.next().value
            right = self.unary()
            node = BinOp(op, node, right)
        return node

    def unary(self) -> Any:
        t = self.peek()
        if t.kind == "OP" and t.value == "-":
            self.next()
            return BinOp("-", Number(0), self.unary())
        return self.primary()

    def primary(self) -> Any:
        t = self.peek()
        if t.kind == "NUM":
            self.next()
            return Number(t.value)
        if t.kind == "STR":
            self.next()
            return StrLit(t.value)
        if t.kind == "LPAREN":
            self.next()
            node = self.expr()
            self.expect("RPAREN")
            return node
        if t.kind == "IDENT":
            name = t.value
            self.next()
            if self.peek().kind == "LPAREN":
                self.next()
                args: list[Any] = []
                if self.peek().kind != "RPAREN":
                    args.append(self.expr())
                    while self.peek().kind == "COMMA":
                        self.next()
                        args.append(self.expr())
                self.expect("RPAREN")
                return FuncCall(name, args)
            return FieldRef(name)
        raise FormulaError(f"Неожиданный токен {t.kind}")


# --- Whitelist функций -----------------------------------------------------
def _fn_today() -> date:
    return date.today()


def _fn_date_diff(a: date, b: date) -> int:
    return (a - b).days


def _fn_if(cond: Any, yes: Any, no: Any) -> Any:
    return yes if bool(cond) else no


def _fn_sum(args: list) -> float:
    total = 0.0
    for a in args:
        if isinstance(a, (list, tuple)):
            total += sum(float(x) for x in a if x is not None)
        elif a is not None:
            total += float(a)
    return total


def _fn_min(args: list) -> Any:
    vals = []
    for a in args:
        if isinstance(a, (list, tuple)):
            vals.extend(x for x in a if x is not None)
        elif a is not None:
            vals.append(a)
    return min(vals) if vals else 0


def _fn_max(args: list) -> Any:
    vals = []
    for a in args:
        if isinstance(a, (list, tuple)):
            vals.extend(x for x in a if x is not None)
        elif a is not None:
            vals.append(a)
    return max(vals) if vals else 0


def _fn_round(x: Any, digits: Any = 0) -> float:
    return round(float(x), int(digits))


FUNCTIONS: dict[str, Callable] = {
    "IF": _fn_if,
    "SUM": _fn_sum,
    "MIN": _fn_min,
    "MAX": _fn_max,
    "DATE_DIFF": _fn_date_diff,
    "TODAY": lambda: _fn_today(),
    "ROUND": _fn_round,
}

# Функции с фиксированной арностью: name -> (min_args, max_args)
FUNCTION_ARITY: dict[str, tuple[int, int]] = {
    "IF": (3, 3),
    "SUM": (1, 99),
    "MIN": (1, 99),
    "MAX": (1, 99),
    "DATE_DIFF": (2, 2),
    "TODAY": (0, 0),
    "ROUND": (1, 2),
}

ALLOWED_FIELDS: set[str] = {
    "deadline", "quantity", "unit_price", "cost", "amount", "price",
    "payment_percent", "advance_date", "final_payment_date",
    "next_action_date", "signal_shipping_date", "created_at", "updated_at",
}


# --- Валидация AST (7.md §51.2) --------------------------------------------
def validate_ast(node: Any, allowed_fields: Optional[set[str]] = None) -> None:
    fields = allowed_fields or ALLOWED_FIELDS
    if isinstance(node, (Number, StrLit)):
        return
    if isinstance(node, BinOp):
        if node.op not in ("+", "-", "*", "/"):
            raise FormulaError(f"Оператор {node.op} запрещён")
        validate_ast(node.left, fields)
        validate_ast(node.right, fields)
        return
    if isinstance(node, FieldRef):
        if node.name not in fields:
            raise FormulaError(f"Поле {node.name} недоступно в формулах")
        return
    if isinstance(node, FuncCall):
        if node.name.upper() not in FUNCTIONS:
            raise FormulaError(f"Функция {node.name} запрещена")
        arity = FUNCTION_ARITY[node.name.upper()]
        if not (arity[0] <= len(node.args) <= arity[1]):
            raise FormulaError(f"Функция {node.name}: ожидалось {arity[0]}..{arity[1]} аргументов, получено {len(node.args)}")
        for a in node.args:
            validate_ast(a, fields)
        return
    raise FormulaError("Неизвестный узел AST")


# --- Вычисление ------------------------------------------------------------
def eval_ast(node: Any, ctx: dict[str, Any]) -> Any:
    if isinstance(node, Number):
        return node.value
    if isinstance(node, StrLit):
        return node.value
    if isinstance(node, FieldRef):
        return ctx.get(node.name)
    if isinstance(node, BinOp):
        left = eval_ast(node.left, ctx)
        right = eval_ast(node.right, ctx)
        if node.op == "+":
            if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                return left + right
            return f"{left or ''}{right or ''}"
        if node.op == "-":
            return _num(left) - _num(right)
        if node.op == "*":
            return _num(left) * _num(right)
        if node.op == "/":
            if _num(right) == 0:
                raise FormulaError("Деление на ноль")
            return _num(left) / _num(right)
    if isinstance(node, FuncCall):
        fn = FUNCTIONS[node.name.upper()]
        args = [eval_ast(a, ctx) for a in node.args]
        if node.name.upper() == "IF":
            return _fn_if(args[0], args[1], args[2])
        if node.name.upper() == "SUM":
            return _fn_sum(args)
        if node.name.upper() in ("MIN", "MAX"):
            return _fn_min(args) if node.name.upper() == "MIN" else _fn_max(args)
        if node.name.upper() == "ROUND":
            return _fn_round(*args)
        if node.name.upper() == "DATE_DIFF":
            a, b = _as_date(args[0]), _as_date(args[1])
            return _fn_date_diff(a, b)
        if node.name.upper() == "TODAY":
            return _fn_today()
    raise FormulaError("Не удалось вычислить выражение")


def _num(v: Any) -> float:
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.replace("%", "").strip())
        except ValueError:
            return 0.0
    return 0.0


def _as_date(v: Any) -> date:
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        from datetime import datetime

        try:
            return datetime.fromisoformat(v).date()
        except ValueError:
            try:
                from datetime import date as _d

                return _d.fromisoformat(v[:10])
            except ValueError:
                raise FormulaError(f"Не дата: {v}")
    raise FormulaError(f"Не дата: {v!r}")


# --- Публичный API ----------------------------------------------------------
def compile_formula(src: str, allowed_fields: Optional[set[str]] = None) -> Callable[[dict[str, Any]], Any]:
    """Компилирует формулу в функцию. Кидает FormulaError при невалидности."""
    if not src or not src.strip():
        raise FormulaError("Пустая формула")
    tokens = tokenize(src)
    parser = Parser(tokens)
    ast = parser.parse()
    validate_ast(ast, allowed_fields)
    return lambda ctx: eval_ast(ast, ctx)


def evaluate(src: str, context: dict[str, Any]) -> Any:
    """Однократное вычисление (для тестов и API)."""
    fn = compile_formula(src)
    return fn(context)