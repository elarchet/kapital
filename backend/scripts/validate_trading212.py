"""Validate Trading212 sample parsing against the ./data folder.

Runs the real parser + idempotency logic over every Trading212 CSV in the
repository's ``data/`` directory and asserts that every row maps cleanly to the
new schema without data loss, and that deduplication keys are stable and
collision-free.

Usage (from the backend/ directory)::

    uv run python -m scripts.validate_trading212
"""
# ruff: noqa: T201, INP001  (developer validation script: prints a report)

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

from src.logic.idempotency import compute_dedup_key
from src.services.import_row_parser import parse_csv_row
from src.services.institutions.trading212 import TRADING212_MAPPINGS

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"

_M = TRADING212_MAPPINGS
_ACTION_COL = _M["columns"]["operation_type"]


def _parse_file(path: Path) -> tuple[int, int, Counter, list[str], dict[str, dict]]:
    """Parse one CSV; return (total, skipped_blank, op_counts, failures, keys)."""
    op_counts: Counter = Counter()
    failures: list[str] = []
    keys: dict[str, dict] = {}
    total = 0
    skipped_blank = 0

    with path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            total += 1
            action = (row.get(_ACTION_COL) or "").strip()
            if not action:
                skipped_blank += 1
                continue

            parsed = parse_csv_row(
                row=row,
                columns=_M["columns"],
                type_mappings=_M.get("type_mappings", {}),
                scaling=_M.get("scaling", {}),
                transformations=_M.get("transformations", {}),
                date_formats=_M.get("date_formats", {}),
                schema_mappings=_M,
                decimal_separator=".",
            )
            if parsed is None:
                failures.append(f"{path.name}: unmapped/failed action={action!r}")
                continue
            if parsed.get("executed_at") is None or parsed.get("total_amount") is None:
                failures.append(f"{path.name}: missing required field for action={action!r}")
                continue

            op_counts[parsed["op_type"]] += 1
            key, _ = compute_dedup_key(
                row,
                scope="validate",
                native_id=parsed.get("native_transaction_id"),
            )
            if key in keys and keys[key] != row:
                failures.append(f"{path.name}: dedup collision on distinct rows (key={key})")
            keys[key] = row

    return total, skipped_blank, op_counts, failures, keys


def main() -> int:
    files = sorted(DATA_DIR.glob("*.csv"))
    if not files:
        print(f"No CSV files found in {DATA_DIR}")
        return 1

    grand_total = 0
    grand_blank = 0
    grand_ops: Counter = Counter()
    all_failures: list[str] = []

    for path in files:
        total, blank, ops, failures, keys = _parse_file(path)
        grand_total += total
        grand_blank += blank
        grand_ops.update(ops)
        all_failures.extend(failures)
        mapped = sum(ops.values())
        print(f"{path.name}: {total} rows | mapped {mapped} | blank {blank} | unique keys {len(keys)}")

    print("\n=== Operation type totals ===")
    for op_type, count in grand_ops.most_common():
        print(f"  {op_type:16} {count}")

    mapped_total = sum(grand_ops.values())
    print(
        f"\nTotal rows: {grand_total} | mapped: {mapped_total} | "
        f"blank actions: {grand_blank} | failures: {len(all_failures)}",
    )

    if all_failures:
        print("\n=== FAILURES ===")
        for failure in all_failures[:50]:
            print(f"  {failure}")
        return 1

    if mapped_total + grand_blank != grand_total:
        print("\nDATA LOSS: rows were neither mapped nor blank.")
        return 1

    print("\nSUCCESS: every row mapped cleanly with no data loss.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
