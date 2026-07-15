"""Pure allocation-split math — Decimal only, no I/O.

Resolves a user's split intent (``method`` + ``value``) into concrete
``(quantity, amount)`` figures against a parent raw transaction, and validates
that a set of splits never over-allocates the parent.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from src.models.allocation import AllocationMethod

if TYPE_CHECKING:
    from collections.abc import Sequence

# Absolute tolerance when comparing summed splits against the parent total.
_TOLERANCE = Decimal("0.00000001")


def resolve_allocation(
    method: AllocationMethod,
    value: Decimal,
    *,
    parent_quantity: Decimal | None,
    parent_amount: Decimal | None,
) -> tuple[Decimal, Decimal]:
    """Resolve a split value into ``(quantity, amount)``.

    Args:
        method: How ``value`` is interpreted.
        value: The user-supplied split value in the method's unit.
        parent_quantity: The parent transaction's total quantity/shares.
        parent_amount: The parent transaction's total fiat amount.

    Returns:
        The resolved ``(quantity, amount)`` for this split, as ``Decimal``.
    """
    parent_qty = parent_quantity if parent_quantity is not None else Decimal(0)
    parent_amt = parent_amount if parent_amount is not None else Decimal(0)

    if method == AllocationMethod.PERCENTAGE:
        fraction = value / Decimal(100)
        return parent_qty * fraction, parent_amt * fraction

    if method == AllocationMethod.QUANTITY:
        fraction = value / parent_qty if parent_qty else Decimal(0)
        return value, parent_amt * fraction

    if method == AllocationMethod.AMOUNT:
        fraction = value / parent_amt if parent_amt else Decimal(0)
        return parent_qty * fraction, value

    msg = f"Unsupported allocation method: {method!r}"
    raise ValueError(msg)


def validate_split_totals(
    resolved: Sequence[tuple[Decimal, Decimal]],
    *,
    parent_quantity: Decimal | None,
    parent_amount: Decimal | None,
) -> None:
    """Ensure summed splits do not exceed the parent quantity or amount.

    Raises:
        ValueError: If the splits over-allocate the parent (beyond tolerance).
    """
    parent_qty = abs(parent_quantity) if parent_quantity is not None else Decimal(0)
    parent_amt = abs(parent_amount) if parent_amount is not None else Decimal(0)

    total_qty = sum((abs(q) for q, _ in resolved), Decimal(0))
    total_amt = sum((abs(a) for _, a in resolved), Decimal(0))

    if parent_qty and total_qty - parent_qty > _TOLERANCE:
        msg = f"Split quantity {total_qty} exceeds parent quantity {parent_qty}."
        raise ValueError(msg)
    if parent_amt and total_amt - parent_amt > _TOLERANCE:
        msg = f"Split amount {total_amt} exceeds parent amount {parent_amt}."
        raise ValueError(msg)
