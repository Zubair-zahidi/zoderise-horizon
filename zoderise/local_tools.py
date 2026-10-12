from __future__ import annotations

import ast
import hashlib
import json
import math
from typing import Any


_ALLOWED_BINOPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.FloorDiv: lambda a, b: a // b,
    ast.Mod: lambda a, b: a % b,
    ast.Pow: lambda a, b: a**b,
}
_ALLOWED_UNARY = {ast.UAdd: lambda a: +a, ast.USub: lambda a: -a}
_ALLOWED_FUNCS = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
}
_ALLOWED_NAMES = {"pi": math.pi, "e": math.e, "tau": math.tau}


def safe_calculate(expression: str) -> float | int:
    if len(expression) > 300:
        raise ValueError("Expression is too long.")
    node = ast.parse(expression, mode="eval")

    if sum(1 for _ in ast.walk(node)) > 100:
        raise ValueError("Expression is too complex.")

    def bounded(value):
        if isinstance(value, bool) or isinstance(value, complex):
            raise ValueError("Use real numbers only.")
        if isinstance(value, int) and value.bit_length() > 4096:
            raise ValueError("Result is too large.")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("Result is not finite.")
        return value

    def evaluate(n: ast.AST) -> Any:
        if isinstance(n, ast.Expression):
            return evaluate(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return bounded(n.value)
        if isinstance(n, ast.Name) and n.id in _ALLOWED_NAMES:
            return _ALLOWED_NAMES[n.id]
        if isinstance(n, ast.BinOp) and type(n.op) in _ALLOWED_BINOPS:
            left = evaluate(n.left)
            right = evaluate(n.right)
            if isinstance(n.op, ast.Pow) and abs(float(right)) > 1000:
                raise ValueError("Exponent is too large.")
            if isinstance(n.op, ast.Pow) and isinstance(left, int) and right > 0 and left.bit_length() * right > 4096:
                raise ValueError("Power result is too large.")
            return bounded(_ALLOWED_BINOPS[type(n.op)](left, right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _ALLOWED_UNARY:
            return _ALLOWED_UNARY[type(n.op)](evaluate(n.operand))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _ALLOWED_FUNCS:
            if n.keywords:
                raise ValueError("Keyword arguments are not supported.")
            args = [evaluate(a) for a in n.args]
            return bounded(_ALLOWED_FUNCS[n.func.id](*args))
        raise ValueError("Unsupported expression.")

    result = evaluate(node)
    if isinstance(result, complex) or not isinstance(result, (int, float)):
        raise ValueError("Result is not a real number.")
    if isinstance(result, float) and (math.isnan(result) or math.isinf(result)):
        raise ValueError("Result is not finite.")
    return result


UNIT_GROUPS = {
    "Length": {
        "m": 1.0,
        "km": 1000.0,
        "cm": 0.01,
        "mm": 0.001,
        "mile": 1609.344,
        "yard": 0.9144,
        "ft": 0.3048,
        "in": 0.0254,
    },
    "Mass": {
        "kg": 1.0,
        "g": 0.001,
        "mg": 0.000001,
        "lb": 0.45359237,
        "oz": 0.028349523125,
    },
    "Time": {
        "s": 1.0,
        "min": 60.0,
        "h": 3600.0,
        "day": 86400.0,
    },
    "Area": {
        "m²": 1.0,
        "km²": 1_000_000.0,
        "cm²": 0.0001,
        "hectare": 10_000.0,
        "acre": 4046.8564224,
    },
}


def convert_unit(group: str, value: float, from_unit: str, to_unit: str) -> float:
    units = UNIT_GROUPS[group]
    return value * units[from_unit] / units[to_unit]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def format_json(text: str) -> str:
    obj = json.loads(text)
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)
