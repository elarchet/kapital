from __future__ import annotations

import json
from decimal import Decimal
from typing import cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, select

from src.database import get_session
from src.main import app
from src.models import Operation, Portfolio, Position, User
from src.models.base import SABase
from src.models.import_file_schema import ImportFileSchema
from src.services.import_service import import_portfolio_transactions
from tests.factories import (
    PortfolioFactory,
    UserFactory,
    set_factory_session,
)


@pytest.fixture(name="engine")
def fixture_engine():
    """In-memory SQLite engine with all tables created and default schema seeded."""
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    SQLModel.metadata.create_all(eng)
    SABase.metadata.create_all(eng)

    # Seed default templates
    with Session(eng) as session:
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

    return eng


@pytest.fixture(name="session")
def fixture_session(engine):
    """Yield a fresh session per test."""
    with Session(engine) as s:
        set_factory_session(s)
        yield s
        set_factory_session(None)


@pytest.fixture(name="client")
def fixture_client(session):
    """Yield a TestClient with database session overridden."""

    def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_import_with_custom_date_format(session):
    # Setup test portfolio and user
    user = cast("User", UserFactory())
    portfolio = cast("Portfolio", PortfolioFactory(user=user))
    session.commit()
    session.refresh(user)
    session.refresh(portfolio)

    # Custom mapping config using custom date format
    custom_mappings = {
        "columns": {
            "operation_type": "Type",
            "executed_at": "Date",
            "name": "Asset",
            "total_amount": "Total",
            "currency": "Currency",
            "quantity": "Qty",
        },
        "type_mappings": {
            "buy": ["BUY"],
        },
        "date_formats": {
            "executed_at": "%d/%m/%Y %H:%M:%S",
        },
    }

    # CSV content with date format "01/06/2026 15:30:00" (June 1st, 2026)
    csv_content = b"Type,Date,Asset,Total,Currency,Qty\nBUY,01/06/2026 15:30:00,Apple,150.0,USD,10\n"

    summary = await import_portfolio_transactions(
        db=session,
        portfolio_id=portfolio.id,
        user_id=user.id,
        file_content=csv_content,
        custom_schema_config={
            "mappings": custom_mappings,
            "delimiter": ",",
            "decimal_separator": ".",
        },
    )

    assert summary["operations_imported"] == 1
    op = session.exec(select(Operation)).first()
    assert op is not None
    assert op.executed_at.year == 2026
    assert op.executed_at.month == 6
    assert op.executed_at.day == 1
    assert op.executed_at.hour == 15
    assert op.executed_at.minute == 30


def test_update_import_file_schema(client, session):
    # Create two users
    user1 = cast("User", UserFactory(email="user1@example.com"))
    user2 = cast("User", UserFactory(email="user2@example.com"))
    session.commit()
    session.refresh(user1)
    session.refresh(user2)

    # Authenticate user 1
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "user1@example.com", "password": "SeedP@ss1!"},
    )
    assert response.status_code == 200
    token1 = response.json()["access_token"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    # Create a template owned by user 1
    schema1 = ImportFileSchema(
        name="User 1 Template",
        is_public=False,
        delimiter=",",
        decimal_separator=".",
        mappings="{}",
        user_id=user1.id,
    )
    # Create a template owned by user 2
    schema2 = ImportFileSchema(
        name="User 2 Template",
        is_public=False,
        delimiter=";",
        decimal_separator=",",
        mappings="{}",
        user_id=user2.id,
    )
    session.add(schema1)
    session.add(schema2)
    session.commit()
    session.refresh(schema1)
    session.refresh(schema2)

    # 1. User 1 updates their own template
    update_data = {
        "name": "User 1 Template Updated",
        "delimiter": ";",
        "is_incomplete": True,
    }
    response = client.put(
        f"/api/v1/import-file-schemas/{schema1.id}",
        json=update_data,
        headers=headers1,
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["name"] == "User 1 Template Updated"
    assert updated["delimiter"] == ";"
    assert updated["is_incomplete"] is True

    # 2. User 1 tries to update User 2's template
    response = client.put(
        f"/api/v1/import-file-schemas/{schema2.id}",
        json={"name": "Stolen Template"},
        headers=headers1,
    )
    assert response.status_code == 404

    # 3. User 1 tries to update a public template
    public_schema = session.exec(select(ImportFileSchema).where(ImportFileSchema.is_public)).first()
    assert public_schema is not None
    response = client.put(
        f"/api/v1/import-file-schemas/{public_schema.id}",
        json={"name": "Malicious public edit"},
        headers=headers1,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_import_dividend_without_price_per_share(session):
    user = cast("User", UserFactory())
    portfolio = cast("Portfolio", PortfolioFactory(user=user))
    session.commit()

    custom_mappings = {
        "columns": {
            "operation_type": "Type",
            "executed_at": "Date",
            "name": "Asset",
            "total_amount": "Total",
            "currency": "Currency",
            "quantity": "Qty",
        },
        "type_mappings": {
            "dividend": ["DIV"],
        },
        "date_formats": {
            "executed_at": "%Y-%m-%d %H:%M:%S",
        },
    }

    csv_content = b"Type,Date,Asset,Total,Currency,Qty\nDIV,2026-06-01 15:30:00,Apple,50.0,USD,10\n"

    summary = await import_portfolio_transactions(
        db=session,
        portfolio_id=portfolio.id,
        user_id=user.id,
        file_content=csv_content,
        custom_schema_config={
            "mappings": custom_mappings,
            "delimiter": ",",
            "decimal_separator": ".",
        },
    )

    assert summary["operations_imported"] == 1
    op = session.exec(select(Operation).where(Operation.operation_type == "dividend")).first()
    assert op is not None
    assert op.dividend_per_share == Decimal("0.0")


@pytest.mark.asyncio
async def test_import_without_transaction_id(session):
    # Setup test portfolio and user
    user = cast("User", UserFactory())
    portfolio = cast("Portfolio", PortfolioFactory(user=user))
    session.commit()
    session.refresh(user)
    session.refresh(portfolio)

    # Custom mapping config without transaction_id mapping
    custom_mappings = {
        "columns": {
            "operation_type": "Type",
            "executed_at": "Date",
            "name": "Asset",
            "total_amount": "Total",
            "currency": "Currency",
            "quantity": "Qty",
        },
        "type_mappings": {
            "buy": ["BUY"],
        },
        "date_formats": {
            "executed_at": "%Y-%m-%d %H:%M:%S",
        },
    }

    # CSV content with two buy operations for the SAME asset (which will create a new position)
    # The first row will create the position, and since there is no transaction ID,
    # it will test the fallback path. The second row is a duplicate, which should be skipped.
    # The third row is a distinct buy for the same asset at a different time, which should be imported.
    csv_content = (
        b"Type,Date,Asset,Total,Currency,Qty\n"
        b"BUY,2026-06-01 15:30:00,NewAsset,150.0,USD,10\n"
        b"BUY,2026-06-01 15:30:00,NewAsset,150.0,USD,10\n"
        b"BUY,2026-06-01 16:30:00,NewAsset,150.0,USD,10\n"
    )

    summary = await import_portfolio_transactions(
        db=session,
        portfolio_id=portfolio.id,
        user_id=user.id,
        file_content=csv_content,
        custom_schema_config={
            "mappings": custom_mappings,
            "delimiter": ",",
            "decimal_separator": ".",
        },
    )

    # Verification:
    # - 2 Positions created (NewAsset stock position + USD cash position)
    # - 2 Operations imported (the first and third row)
    # - 1 Operation skipped (the second duplicate row)
    assert summary["positions_created"] == 2
    assert summary["operations_imported"] == 2
    assert summary["operations_skipped"] == 1

    # Verify positions and operations in database
    pos = session.exec(select(Position).where(Position.portfolio_id == portfolio.id)).first()
    assert pos is not None
    assert pos.name == "NewAsset"
    assert pos.quantity == Decimal("20.0")  # 10 + 10

    ops = session.exec(select(Operation).where(Operation.position_id == pos.id)).all()
    assert len(ops) == 2
