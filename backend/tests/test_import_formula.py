"""Tests for the structured import formula engine."""

from __future__ import annotations

from decimal import Decimal

from src.services.import_formula import evaluate_formula, resolve_numeric_value

ROW = {"Qty": "5", "Price": "166.72", "FeeA": "1.10", "FeeB": "", "FeeC": "0.25"}


def _f(*tokens):
    return list(tokens)


def col(name: str) -> dict:
    return {"col": name}


def op(symbol: str) -> dict:
    return {"op": symbol}


def num(value: str) -> dict:
    return {"num": value}


def paren(p: str) -> dict:
    return {"paren": p}


def test_multiplication():
    assert evaluate_formula(_f(col("Qty"), op("*"), col("Price")), ROW) == Decimal("833.60")


def test_operator_precedence():
    # 5 + 166.72 * 2 = 338.44, not 343.44
    tokens = _f(col("Qty"), op("+"), col("Price"), op("*"), num("2"))
    assert evaluate_formula(tokens, ROW) == Decimal("338.44")


def test_parentheses_override_precedence():
    tokens = _f(paren("("), col("Qty"), op("+"), col("Price"), paren(")"), op("*"), num("2"))
    assert evaluate_formula(tokens, ROW) == Decimal("343.44")


def test_blank_column_counts_as_zero_for_addition():
    tokens = _f(col("FeeA"), op("+"), col("FeeB"), op("+"), col("FeeC"))
    assert evaluate_formula(tokens, ROW) == Decimal("1.35")


def test_blank_column_propagates_none_for_multiplication():
    assert evaluate_formula(_f(col("Qty"), op("*"), col("FeeB")), ROW) is None


def test_missing_column_behaves_like_blank():
    assert evaluate_formula(_f(col("Nope"), op("+"), col("FeeA")), ROW) == Decimal("1.10")
    assert evaluate_formula(_f(col("Nope"), op("*"), col("FeeA")), ROW) is None


def test_division_by_zero_yields_none():
    assert evaluate_formula(_f(col("Qty"), op("/"), num("0")), ROW) is None


def test_decimal_exactness():
    row = {"A": "0.1", "B": "0.2"}
    assert evaluate_formula(_f(col("A"), op("+"), col("B")), row) == Decimal("0.3")


def test_european_decimal_separator():
    row = {"A": "1,5", "B": "2,5"}
    assert evaluate_formula(_f(col("A"), op("*"), col("B")), row, decimal_separator=",") == Decimal("3.75")


def test_malformed_sequences_rejected():
    assert evaluate_formula(_f(col("Qty"), col("Price")), ROW) is None  # operand operand
    assert evaluate_formula(_f(col("Qty"), op("*")), ROW) is None  # trailing operator
    assert evaluate_formula(_f(op("*"), col("Qty")), ROW) is None  # leading operator
    assert evaluate_formula(_f(paren("("), col("Qty")), ROW) is None  # unbalanced paren
    assert evaluate_formula(_f(col("Qty"), paren(")")), ROW) is None
    assert evaluate_formula(_f({"op": "**"}, col("Qty")), ROW) is None  # non-whitelisted op
    assert evaluate_formula(_f({"evil": "x"}), ROW) is None  # unknown token kind
    assert evaluate_formula([], ROW) is None
    assert evaluate_formula("Qty * Price", ROW) is None  # type: ignore[arg-type]


def test_bad_numeric_literal_rejected():
    assert evaluate_formula(_f(col("Qty"), op("*"), num("abc")), ROW) is None


def test_token_cap():
    tokens = _f(col("Qty"))
    for _ in range(40):
        tokens += _f(op("+"), col("Qty"))
    assert evaluate_formula(tokens, ROW) is None  # 81 tokens > cap


def test_resolve_numeric_value_prefers_formula_over_column():
    schema_mappings = {"formulas": {"total_amount": {"trade": _f(col("Qty"), op("*"), col("Price"))}}}
    val = resolve_numeric_value(
        "total_amount",
        ROW,
        columns={"total_amount": "FeeA"},
        schema_mappings=schema_mappings,
        transformations={},
        decimal_separator=".",
        op_type="trade",
        csv_action=None,
    )
    assert val == Decimal("833.60")


def test_resolve_numeric_value_falls_back_to_column():
    val = resolve_numeric_value(
        "total_amount",
        ROW,
        columns={"total_amount": "Price"},
        schema_mappings={},
        transformations={},
        decimal_separator=".",
        op_type="trade",
        csv_action=None,
    )
    assert val == Decimal("166.72")


def test_resolve_numeric_value_applies_transformation_on_formula_result():
    schema_mappings = {"formulas": {"unit_price": _f(col("Price"), op("*"), num("100"))}}
    val = resolve_numeric_value(
        "unit_price",
        ROW,
        columns={},
        schema_mappings=schema_mappings,
        transformations={"unit_price": {"divisor": 100}},
        decimal_separator=".",
        op_type="trade",
        csv_action=None,
    )
    assert val == Decimal("166.72")


def test_resolve_numeric_value_unmapped_returns_none():
    val = resolve_numeric_value(
        "quantity",
        ROW,
        columns={},
        schema_mappings={},
        transformations={},
        decimal_separator=".",
        op_type="trade",
        csv_action=None,
    )
    assert val is None
