"""Tests for the pure allocation-split math."""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.logic.allocation_split import resolve_allocation, validate_split_totals
from src.models.allocation import AllocationMethod


def test_percentage_split():
    qty, amt = resolve_allocation(
        AllocationMethod.PERCENTAGE,
        Decimal(25),
        parent_quantity=Decimal(40),
        parent_amount=Decimal(1000),
    )
    assert qty == Decimal(10)
    assert amt == Decimal(250)


def test_quantity_split_derives_proportional_amount():
    qty, amt = resolve_allocation(
        AllocationMethod.QUANTITY,
        Decimal(10),
        parent_quantity=Decimal(40),
        parent_amount=Decimal(1000),
    )
    assert qty == Decimal(10)
    assert amt == Decimal(250)


def test_amount_split_derives_proportional_quantity():
    qty, amt = resolve_allocation(
        AllocationMethod.AMOUNT,
        Decimal(250),
        parent_quantity=Decimal(40),
        parent_amount=Decimal(1000),
    )
    assert qty == Decimal(10)
    assert amt == Decimal(250)


def test_split_with_zero_parent_quantity_is_safe():
    qty, amt = resolve_allocation(
        AllocationMethod.AMOUNT,
        Decimal(50),
        parent_quantity=Decimal(0),
        parent_amount=Decimal(100),
    )
    assert qty == Decimal(0)
    assert amt == Decimal(50)


def test_validate_split_totals_accepts_exact_fill():
    resolved = [(Decimal(10), Decimal(250)), (Decimal(30), Decimal(750))]
    validate_split_totals(resolved, parent_quantity=Decimal(40), parent_amount=Decimal(1000))


def test_validate_split_totals_rejects_over_allocation_quantity():
    resolved = [(Decimal(30), Decimal(750)), (Decimal(20), Decimal(500))]
    with pytest.raises(ValueError, match="exceeds parent quantity"):
        validate_split_totals(resolved, parent_quantity=Decimal(40), parent_amount=Decimal(2000))


def test_validate_split_totals_rejects_over_allocation_amount():
    resolved = [(Decimal(10), Decimal(900)), (Decimal(10), Decimal(900))]
    with pytest.raises(ValueError, match="exceeds parent amount"):
        validate_split_totals(resolved, parent_quantity=Decimal(100), parent_amount=Decimal(1000))


def test_validate_split_totals_allows_under_allocation_by_default():
    resolved = [(Decimal(10), Decimal(250))]
    validate_split_totals(resolved, parent_quantity=Decimal(40), parent_amount=Decimal(1000))


def test_require_full_rejects_under_allocation_quantity():
    resolved = [(Decimal(10), Decimal(250))]
    with pytest.raises(ValueError, match="does not cover parent quantity"):
        validate_split_totals(
            resolved,
            parent_quantity=Decimal(40),
            parent_amount=Decimal(1000),
            require_full=True,
        )


def test_require_full_rejects_under_allocation_amount_when_no_quantity():
    resolved = [(Decimal(0), Decimal(300))]
    with pytest.raises(ValueError, match="does not cover parent amount"):
        validate_split_totals(
            resolved,
            parent_quantity=None,
            parent_amount=Decimal(500),
            require_full=True,
        )


def test_require_full_accepts_exact_fill():
    resolved = [(Decimal(10), Decimal(250)), (Decimal(30), Decimal(750))]
    validate_split_totals(
        resolved,
        parent_quantity=Decimal(40),
        parent_amount=Decimal(1000),
        require_full=True,
    )


def test_unsupported_method_raises():
    with pytest.raises(ValueError, match="Unsupported allocation method"):
        resolve_allocation("bogus", Decimal(1), parent_quantity=Decimal(1), parent_amount=Decimal(1))  # type: ignore[arg-type]
