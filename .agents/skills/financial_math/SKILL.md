---
name: financial_math
description: Procedural rules and templates for financial mathematics, Decimal-only calculations, and Polars-based aggregations.
---

# Financial Mathematics & Calculation Rules

This skill defines instructions for all financial math operations in the Kapital codebase.

## 1. Float Avoidance
- **Never** use `float` or representation that can lose precision for currency, prices, assets, or PnL.
- Always import and use `decimal.Decimal`.
- Explicitly convert numeric input data (from JSON, CSV, DB) to `Decimal` before performing arithmetic.
- When formatting currency for representation, round using standard accounting methods:
  ```python
  from decimal import Decimal, ROUND_HALF_UP
  value = Decimal("123.456").quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
  ```

## 2. Polars Data Handling & Performance Trap
- **Performance Warning**: Avoid using Python `Decimal` objects in Polars (`pl.Object`) inside loops or `.map_elements()`, as it triggers Python interpreter overhead.
- Utilize native Arrow-backed `pl.Decimal` types for vectorization where possible:
  ```python
  import polars as pl
  # Explicitly cast columns using native Decimal definitions
  df = df.with_columns(pl.col("amount").cast(pl.Decimal(precision=18, scale=4)))
  ```
- Use native Polars arithmetic expressions rather than custom mapping functions.

## 3. PnL & Net Worth Calculation
- **Asset Valuation**: Current holdings multiplied by the latest available price.
- **Unrealized PnL**: Valuation minus acquisition cost (cost basis).
- **Realized PnL**: Sale proceeds minus original cost basis of the specific sold assets.
- If data might contain `None` or missing values, default to `Decimal("0")` defensively.
