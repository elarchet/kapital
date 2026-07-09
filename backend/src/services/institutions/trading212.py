"""Trading212 export parser profile.

Canonical column and type mappings covering every ``Action`` value emitted in
Trading212 CSV exports, including all dividend variants, stop orders, currency
conversions, cashback/lending interest, and card debit/credit rows.
"""

from __future__ import annotations

from typing import Any

# Column header -> canonical field mapping for Trading212 exports.
_COLUMNS: dict[str, str] = {
    "operation_type": "Action",
    "executed_at": "Time",
    "isin": "ISIN",
    "ticker": "Ticker",
    "name": "Name",
    "notes": "Notes",
    "transaction_id": "ID",
    "quantity": "No. of shares",
    "unit_price": "Price / share",
    "price_currency": "Currency (Price / share)",
    "currency": "Currency (Total)",
    "total_amount": "Total",
    "exchange_rate": "Exchange rate",
    "fee_amount": "Currency conversion fee",
    "fee_currency": "Currency (Currency conversion fee)",
    "tax_amount": "Withholding tax",
    "tax_currency": "Currency (Withholding tax)",
    "merchant_name": "Merchant name",
    "merchant_category": "Merchant category",
    "interest_type": "Action",
}

# Trading212 ``Action`` value -> canonical operation type.
_TYPE_MAPPINGS: dict[str, list[str]] = {
    "buy": ["Market buy", "Limit buy", "Stop buy", "Stock split open"],
    "sell": ["Market sell", "Limit sell", "Stop sell", "Stock split close"],
    "dividend": [
        "Dividend (Dividend)",
        "Dividend (Ordinary)",
        "Dividend (Dividends paid by us corporations)",
        "Dividend (Dividend manufactured payment)",
        "Dividend (Tax exempted)",
        "Dividend (Return of capital)",
        "Dividend (Bonus)",
        "Dividend adjustment",
    ],
    "interest": ["Interest on cash", "Lending interest", "Spending cashback"],
    "transfer_in": ["Deposit"],
    "transfer_out": ["Withdrawal"],
    "expense": ["Card debit"],
    "revenue": ["Card credit", "Result adjustment"],
    "fx_rate_change": ["Currency conversion"],
}

_ENUM_MAPPINGS: dict[str, dict[str, list[str]]] = {
    "interest_type": {
        "cash_interest": ["Interest on cash"],
        "lending_interest": ["Lending interest"],
        "cashback": ["Spending cashback"],
    },
}

# GBX (pence) values are scaled to GBP.
_SCALING: dict[str, dict[str, float]] = {
    "unit_price": {"GBX": 0.01},
    "total_amount": {"GBX": 0.01},
}

TRADING212_MAPPINGS: dict[str, Any] = {
    "columns": _COLUMNS,
    "type_mappings": _TYPE_MAPPINGS,
    "enum_mappings": _ENUM_MAPPINGS,
    "scaling": _SCALING,
    "enrich_transaction_ids": "when_empty",
}

TRADING212_PROFILE_DATA: dict[str, Any] = {
    "key": "trading212",
    "name": "Trading 212",
    "default_account_name": "Trading 212 Account",
    "country": "GB",
    "mappings": TRADING212_MAPPINGS,
}
