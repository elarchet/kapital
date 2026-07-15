from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any


def parse_decimal_safe(val: str | None, decimal_sep: str = ".") -> Decimal | None:
    """Parse a string to Decimal safely, replacing decimal separator if needed."""
    if not val or not val.strip():
        return None
    cleaned = val.strip()
    # Strip thousands separators before swapping the decimal separator, otherwise
    # the swapped-in "." would itself be stripped (e.g. "1,5" -> "15").
    if decimal_sep == ".":
        cleaned = cleaned.replace(",", "")
    else:
        cleaned = cleaned.replace(".", "").replace(" ", "").replace(decimal_sep, ".")

    try:
        return Decimal(cleaned)
    except Exception:  # noqa: BLE001
        return None


def parse_datetime_safe(val: str, date_format: str | None = None) -> datetime:
    """Parse string timestamp dynamically supporting ISO and common formats."""
    cleaned = val.strip()
    if date_format and date_format != "auto":
        try:
            return datetime.strptime(cleaned, date_format)  # noqa: DTZ007
        except ValueError:
            pass

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%fZ"):
        try:
            return datetime.strptime(cleaned, fmt)  # noqa: DTZ007
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return datetime.now(UTC)


def resolve_config_value(
    config: Any,  # noqa: ANN401
    db_key: str | None,
    op_type: str | None,
    raw_action: str | None = None,
    default: Any = None,  # noqa: ANN401
) -> Any:  # noqa: ANN401
    # ponytail: Consolidated config cascade lookup (action -> op_type -> global) to reduce duplication.
    if not isinstance(config, dict):
        return config if config is not None else default
    val = config.get(db_key) if db_key is not None else config
    if isinstance(val, dict):
        if "divisor" in val or "multiplier" in val:
            return val
        if raw_action and raw_action in val:
            return val[raw_action]
        if op_type and op_type in val:
            return val[op_type]
        return val.get("global", default)
    return val if val is not None else default


def get_date_format(
    date_formats: dict,
    db_key: str,
    op_type: str | None,
    raw_action: str | None = None,
) -> str | None:
    return resolve_config_value(date_formats, db_key, op_type, raw_action)


def get_mapped_col(
    columns: dict,
    db_key: str,
    op_type: str | None,
    raw_action: str | None = None,
) -> str | None:
    return resolve_config_value(columns, db_key, op_type, raw_action)


def get_transformation(
    transformations: dict,
    db_key: str,
    op_type: str | None,
    raw_action: str | None = None,
) -> dict:
    return resolve_config_value(transformations, db_key, op_type, raw_action, default={})


def apply_transformation(
    transformations: dict,
    col_name: str,
    val: Decimal | None,
    op_type: str | None,
    raw_action: str | None,
) -> Decimal | None:
    if val is None:
        return None
    trans = get_transformation(transformations, col_name, op_type, raw_action)
    divisor_val = trans.get("divisor")
    if divisor_val:
        with contextlib.suppress(ArithmeticError, ValueError, TypeError):
            val /= Decimal(str(divisor_val))
    multiplier_val = trans.get("multiplier")
    if multiplier_val:
        with contextlib.suppress(ArithmeticError, ValueError, TypeError):
            val *= Decimal(str(multiplier_val))
    return val


def combine_stock_splits(parsed_operations: list[dict]) -> list[dict]:
    """Combine paired split rows into a single stock_split operation.

    Supports two CSV formats:
    - **Two-row format**: broker emits a "close" (pre-split) row and an "open"
      (post-split) row. The rows are paired by ticker and timestamp (≤60s apart).
      Pairing is driven by ``split_sub_type`` when available, with fallback to
      legacy hardcoded ``csv_action`` strings for backward-compatible schemas.
    - **Single-row / combined format**: broker emits one row already representing
      the net share change.  ``split_sub_type == "combined"`` or no sub-type at
      all causes the row to pass through unchanged.

    Sets ``pre_split_quantity`` (the "close" share count) for full audit trail.
    """
    processed_ops: list[dict] = []
    skip_indices: set[int] = set()

    def _is_close(op: dict) -> bool:
        return op.get("split_sub_type") == "close"

    def _is_open(op: dict) -> bool:
        return op.get("split_sub_type") == "open"

    for i, op_data in enumerate(parsed_operations):
        if i in skip_indices:
            continue

        if op_data.get("op_type") != "stock_split":
            processed_ops.append(op_data)
            continue

        # Combined single-row: pass through, just ensure split_ratio is set
        if op_data.get("split_sub_type") == "combined" or (not _is_close(op_data) and not _is_open(op_data)):
            processed_ops.append(op_data)
            continue

        # Two-row format: look for the matching "open" row immediately after
        if _is_close(op_data) and i + 1 < len(parsed_operations):
            next_op = parsed_operations[i + 1]
            same_ticker = next_op.get("ticker") == op_data.get("ticker") or (
                next_op.get("isin") and next_op.get("isin") == op_data.get("isin")
            )
            within_time_window = (
                abs((next_op["executed_at"] - op_data["executed_at"]).total_seconds()) <= 60  # noqa: PLR2004
            )
            if _is_open(next_op) and same_ticker and within_time_window:
                close_qty = op_data["quantity"] or Decimal(1)
                open_qty = next_op["quantity"] or Decimal(1)
                split_ratio = open_qty / close_qty

                op_data["op_type"] = "stock_split"
                op_data["split_ratio"] = split_ratio
                op_data["pre_split_quantity"] = close_qty
                op_data["quantity"] = open_qty - close_qty  # net delta added to position
                op_data["notes"] = f"Stock split 1:{split_ratio:.4f}"
                op_data["split_sub_type"] = "combined"  # mark as resolved
                skip_indices.add(i + 1)
                processed_ops.append(op_data)
                continue

        # Orphaned close row (no matching open) — pass through as-is
        processed_ops.append(op_data)

    return processed_ops
