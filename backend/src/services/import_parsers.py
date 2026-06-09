from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from decimal import Decimal


def parse_decimal_safe(val: str | None, decimal_sep: str = ".") -> Decimal | None:
    """Parse a string to Decimal safely, replacing decimal separator if needed."""
    if not val or not val.strip():
        return None
    cleaned = val.strip()
    if decimal_sep != ".":
        cleaned = cleaned.replace(decimal_sep, ".")
    # Remove any thousands separators
    cleaned = cleaned.replace(",", "") if decimal_sep == "." else cleaned.replace(".", "").replace(" ", "")

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


def get_date_format(
    date_formats: dict,
    db_key: str,
    op_type: str | None,
    raw_action: str | None = None,
) -> str | None:
    val = date_formats.get(db_key)
    if isinstance(val, dict):
        if raw_action and raw_action in val:
            return val[raw_action]
        if op_type and op_type in val:
            return val[op_type]
        return val.get("global")
    return val


def get_mapped_col(
    columns: dict,
    db_key: str,
    op_type: str | None,
    raw_action: str | None = None,
) -> str | None:
    val = columns.get(db_key)
    if isinstance(val, dict):
        if raw_action and raw_action in val:
            return val[raw_action]
        if op_type and op_type in val:
            return val[op_type]
        return val.get("global")
    return val


def get_transformation(
    transformations: dict,
    db_key: str,
    op_type: str | None,
    raw_action: str | None = None,
) -> dict:
    val = transformations.get(db_key, {})
    if "divisor" in val or "multiplier" in val:
        return val
    if raw_action and raw_action in val:
        return val[raw_action]
    if op_type and op_type in val:
        return val[op_type]
    return val.get("global", {})


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
    """Combine split close and split open rows into a single stock_split operation."""
    processed_ops = []
    skip_indices = set()

    for i in range(len(parsed_operations)):
        if i in skip_indices:
            continue

        op_data = parsed_operations[i]
        is_split_close = op_data["csv_action"] == "Stock split close"
        if is_split_close and i + 1 < len(parsed_operations):
            next_op = parsed_operations[i + 1]
            if (
                next_op["csv_action"] == "Stock split open"
                and next_op["ticker"] == op_data["ticker"]
                and abs((next_op["executed_at"] - op_data["executed_at"]).total_seconds()) <= 60  # noqa: PLR2004
            ):
                close_qty = op_data["quantity"] or Decimal(1)
                open_qty = next_op["quantity"] or Decimal(1)
                split_ratio = open_qty / close_qty

                op_data["op_type"] = "stock_split"
                op_data["split_ratio"] = split_ratio
                op_data["quantity"] = open_qty - close_qty
                op_data["notes"] = f"Stock split 1 to {split_ratio:.4f}"
                skip_indices.add(i + 1)

        processed_ops.append(op_data)
    return processed_ops
