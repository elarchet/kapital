"""Safe structured-formula evaluation for import column mappings.

A formula is a JSON token list built by the frontend formula builder, e.g.
``[{"col": "Qté"}, {"op": "*"}, {"col": "Prix d'éxé"}]``. Tokens are data,
never code: only whitelisted operators are applied, all math is Decimal.

Null semantics:
- A blank/missing column parses to ``None``.
- ``+``/``-`` treat a ``None`` operand as 0 (fee columns are often blank).
- ``*``/``/`` propagate ``None`` (a blank price must not become 0), and
  division by zero yields ``None``.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

from src.services.import_parsers import (
    apply_transformation,
    get_mapped_col,
    parse_decimal_safe,
    resolve_config_value,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

MAX_FORMULA_TOKENS = 64

_OPERATORS = ("+", "-", "*", "/")
_PRECEDENCE = {"+": 1, "-": 1, "*": 2, "/": 2}


class _MalformedFormulaError(Exception):
    """Internal sentinel raised while shunting a malformed token sequence."""


def _consume_operator(op: str, output: list[dict], op_stack: list[str], *, expect_operand: bool) -> None:
    if op not in _OPERATORS or expect_operand:
        raise _MalformedFormulaError
    while op_stack and op_stack[-1] in _OPERATORS and _PRECEDENCE[op_stack[-1]] >= _PRECEDENCE[op]:
        output.append({"op": op_stack.pop()})
    op_stack.append(op)


def _consume_paren(paren: str, output: list[dict], op_stack: list[str], *, expect_operand: bool) -> bool:
    if paren == "(":
        if not expect_operand:
            raise _MalformedFormulaError
        op_stack.append("(")
        return True
    if paren == ")":
        if expect_operand:
            raise _MalformedFormulaError
        while op_stack and op_stack[-1] != "(":
            output.append({"op": op_stack.pop()})
        if not op_stack:
            raise _MalformedFormulaError
        op_stack.pop()
        return False
    raise _MalformedFormulaError


def _consume_token(token: dict, output: list[dict], op_stack: list[str], *, expect_operand: bool) -> bool:
    """Shunt one infix token; returns whether an operand is expected next."""
    if not isinstance(token, dict) or len(token) != 1:
        raise _MalformedFormulaError
    if "col" in token or "num" in token:
        if not expect_operand:
            raise _MalformedFormulaError
        output.append(token)
        return False
    if "op" in token:
        _consume_operator(token["op"], output, op_stack, expect_operand=expect_operand)
        return True
    if "paren" in token:
        return _consume_paren(token["paren"], output, op_stack, expect_operand=expect_operand)
    raise _MalformedFormulaError


def _to_rpn(tokens: list[dict]) -> list[dict] | None:
    """Shunting-yard: infix token list -> RPN. Returns None when malformed."""
    output: list[dict] = []
    op_stack: list[str] = []
    # Track infix validity: an operand must alternate with an operator.
    expect_operand = True
    try:
        for token in tokens:
            expect_operand = _consume_token(token, output, op_stack, expect_operand=expect_operand)
    except _MalformedFormulaError:
        return None
    if expect_operand or "(" in op_stack:
        return None
    while op_stack:
        output.append({"op": op_stack.pop()})
    return output


def _apply_op(op: str, left: Decimal | None, right: Decimal | None) -> Decimal | None:
    if op in ("+", "-"):
        left = left if left is not None else Decimal(0)
        right = right if right is not None else Decimal(0)
        return left + right if op == "+" else left - right
    if left is None or right is None:
        return None
    if op == "/":
        return left / right if right != 0 else None
    return left * right


def evaluate_formula(
    tokens: list[dict],
    row: Mapping[str, str],
    decimal_separator: str = ".",
) -> Decimal | None:
    """Evaluate a structured formula against a raw CSV row."""
    if not isinstance(tokens, list) or not tokens or len(tokens) > MAX_FORMULA_TOKENS:
        return None
    rpn = _to_rpn(tokens)
    if rpn is None:
        return None

    stack: list[Decimal | None] = []
    for token in rpn:
        if "col" in token:
            stack.append(parse_decimal_safe(row.get(token["col"]), decimal_separator))
        elif "num" in token:
            try:
                stack.append(Decimal(str(token["num"])))
            except InvalidOperation, ValueError, TypeError:
                return None
        else:
            if len(stack) < 2:  # noqa: PLR2004
                return None
            right = stack.pop()
            left = stack.pop()
            try:
                stack.append(_apply_op(token["op"], left, right))
            except ArithmeticError, InvalidOperation:
                return None
    return stack[0] if len(stack) == 1 else None


def resolve_numeric_value(
    db_key: str,
    row: Mapping[str, str],
    columns: dict,
    schema_mappings: dict,
    transformations: dict,
    decimal_separator: str,
    op_type: str | None,
    csv_action: str | None,
) -> Decimal | None:
    """Single choke point for numeric fields: formula if configured, else mapped column.

    A formula-mapped field may legally have no ``columns`` entry. The
    divisor/multiplier transformation applies on top of either source.
    """
    formula = resolve_config_value(schema_mappings.get("formulas"), db_key, op_type, csv_action)
    if formula:
        val = evaluate_formula(formula, row, decimal_separator)
    else:
        col = get_mapped_col(columns, db_key, op_type, csv_action)
        val = parse_decimal_safe(row.get(col, ""), decimal_separator) if col else None
    return apply_transformation(transformations, db_key, val, op_type, csv_action)
