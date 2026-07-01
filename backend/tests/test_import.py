from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

import pytest

from src.models.import_file_schema import ImportFileSchema
from src.services.import_service import autodetect_schema
from tests.factories import (
    UserFactory,
)

if TYPE_CHECKING:
    from src.models import User


@pytest.fixture(autouse=True)
def seed_trading_212(session):
    t212_mappings = {
        "columns": {
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
        },
        "type_mappings": {
            "buy": ["Market buy", "Limit buy", "Stock split open"],
            "sell": ["Market sell", "Limit sell", "Stock split close"],
            "dividend": ["Dividend (Dividend)", "Dividend (Dividend manufactured payment)", "Dividend adjustment"],
            "interest": ["Interest on cash", "Lending interest", "Spending cashback"],
            "transfer_in": ["Deposit"],
            "transfer_out": ["Withdrawal"],
            "expense": ["Card debit"],
            "revenue": ["Card credit"],
            "fx_rate_change": ["Currency conversion"],
        },
        "enum_mappings": {
            "interest_type": {
                "cash_interest": ["Interest on cash"],
                "lending_interest": ["Lending interest"],
                "cashback": ["Spending cashback"],
            },
        },
        "scaling": {
            "unit_price": {
                "GBX": 0.01,
            },
            "total_amount": {
                "GBX": 0.01,
            },
        },
    }
    schema_obj = ImportFileSchema(
        name="Trading 212",
        is_public=True,
        delimiter=",",
        decimal_separator=".",
        mappings=json.dumps(t212_mappings),
    )
    session.add(schema_obj)
    session.commit()


def test_autodetect_schema(session):
    # Test valid headers (Trading 212)
    headers = [
        "Action",
        "Time",
        "ISIN",
        "Ticker",
        "Name",
        "Notes",
        "ID",
        "No. of shares",
        "Price / share",
        "Currency (Price / share)",
        "Exchange rate",
        "Result",
        "Currency (Result)",
        "Total",
        "Currency (Total)",
        "Withholding tax",
        "Currency (Withholding tax)",
    ]
    schema_id = autodetect_schema(session, headers, user_id=1)
    assert schema_id is not None

    # Test invalid headers
    bad_headers = ["random", "columns", "with", "no", "matches"]
    bad_schema_id = autodetect_schema(session, bad_headers, user_id=1)
    assert bad_schema_id is None


def test_get_import_metadata(client, session):
    user = cast("User", UserFactory(email="import_meta@example.com"))
    session.commit()
    session.refresh(user)

    response = client.post(
        "/api/v1/auth/token",
        data={"username": "import_meta@example.com", "password": "SeedP@ss1!"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/portfolios/import-metadata", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "fields" in data
    fields = data["fields"]

    op_type_field = next(f for f in fields if f["key"] == "operation_type")
    assert op_type_field["is_required"] is True
    assert op_type_field["type"] == "enum"
    assert "trade" in op_type_field["enum_values"]

    executed_at_field = next(f for f in fields if f["key"] == "executed_at")
    assert executed_at_field["is_required"] is True
    assert executed_at_field["type"] == "datetime"
