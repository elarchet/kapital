"""Logic package — pure, stateless financial computation modules."""

from __future__ import annotations

from src.logic.split_adjustment import compute_cost_basis, compute_split_adjusted_operations

__all__ = ["compute_cost_basis", "compute_split_adjusted_operations"]
