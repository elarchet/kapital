from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, select

from src.database import get_session
from src.main import app
from src.models import AssetType, FeeType, InterestType, Operation, Portfolio, Position, User
from src.models.base import SABase
from src.models.import_file_schema import ImportFileSchema
from src.services.import_service import autodetect_schema, import_portfolio_transactions
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


def test_import_portfolio_transactions(session):  # noqa: PLR0915
    # Setup test portfolio and user
    user = cast("User", UserFactory())
    portfolio = cast("Portfolio", PortfolioFactory(user=user))
    session.commit()
    session.refresh(user)
    session.refresh(portfolio)

    assert user.id is not None
    assert portfolio.id is not None

    # Get schema ID
    schema = session.exec(select(ImportFileSchema).where(ImportFileSchema.name == "Trading 212")).first()
    assert schema is not None
    assert schema.id is not None

    # Read the actual CSV file
    csv_path = Path(__file__).parent.parent.parent / "from_2026-01-01_to_2026-05-25_MTc3OTczMDI0NzIwNw.csv"
    assert csv_path.exists(), f"CSV file not found at {csv_path}"

    file_content = csv_path.read_bytes()

    # Run the import
    summary = import_portfolio_transactions(
        db=session,
        portfolio_id=portfolio.id,
        user_id=user.id,
        file_content=file_content,
        schema_id=schema.id,
    )

    # Basic summary verification
    assert summary["operations_imported"] > 0
    assert summary["positions_created"] > 0

    # 1. Assert SoftBank stock split
    # Let's find SFTBY position and operations
    sftby_position = session.exec(
        select(Position).where(Position.portfolio_id == portfolio.id, Position.ticker == "SFTBY"),
    ).first()
    assert sftby_position is not None

    # Stock split close was at 8:18:00 on 2026-01-08
    # Stock split open was at 8:18:00 on 2026-01-08
    # Close: 46.1859230000, Open: 184.7436920000
    # Our split ratio should be 4.0, net quantity added is 138.557769
    split_op = session.exec(
        select(Operation).where(Operation.position_id == sftby_position.id, Operation.operation_type == "stock_split"),
    ).first()
    assert split_op is not None
    assert split_op.split_ratio == Decimal("4.0")
    assert split_op.quantity == Decimal("138.55776900")

    # 2. Check child Fee records
    # - Withholding tax on DELL dividend (Line 109 in CSV)
    # Dell Technologies is US24703L2025. Withholding tax: 1.02 USD
    dell_pos = session.exec(
        select(Position).where(Position.portfolio_id == portfolio.id, Position.ticker == "DELL"),
    ).first()
    assert dell_pos is not None

    dell_dividend_op = session.exec(
        select(Operation).where(Operation.position_id == dell_pos.id, Operation.operation_type == "dividend"),
    ).first()
    assert dell_dividend_op is not None
    assert len(dell_dividend_op.fees) > 0

    tax_fee = next(f for f in dell_dividend_op.fees if f.fee_type == FeeType.WITHHOLDING_TAX)
    assert tax_fee.amount == Decimal("1.02")
    assert tax_fee.currency == "USD"

    # - Currency conversion fee on BRK.A market buy (Line 149 in CSV)
    # Berkshire Hathaway (Class A) is BRK.A. Conversion fee: 0.54 EUR
    brk_pos = session.exec(
        select(Position).where(Position.portfolio_id == portfolio.id, Position.ticker == "BRK.A"),
    ).first()
    assert brk_pos is not None

    brk_buy_op = session.exec(
        select(Operation).where(Operation.position_id == brk_pos.id, Operation.operation_type == "trade"),
    ).first()
    assert brk_buy_op is not None
    assert len(brk_buy_op.fees) > 0

    conversion_fee = next(f for f in brk_buy_op.fees if f.fee_type == FeeType.CONVERSION)
    assert conversion_fee.amount == Decimal("0.54")
    assert conversion_fee.currency == "EUR"
    assert brk_buy_op.price_currency == "USD"
    assert brk_buy_op.currency == "EUR"
    assert brk_buy_op.source_currency == "EUR"
    assert brk_buy_op.target_currency == "USD"

    # 3. Check cash positions are created and updated correctly
    cash_eur = session.exec(
        select(Position).where(
            Position.portfolio_id == portfolio.id,
            Position.asset_type == AssetType.CASH,
            Position.currency == "EUR",
        ),
    ).first()
    assert cash_eur is not None
    assert cash_eur.quantity != Decimal("0.0")

    # 4. Check duplicate operations are skipped on re-import
    # If we run the import again, it should skip all operations
    summary_reimport = import_portfolio_transactions(
        db=session,
        portfolio_id=portfolio.id,
        user_id=user.id,
        file_content=file_content,
        schema_id=schema.id,
    )
    assert summary_reimport["operations_imported"] == 0
    assert summary_reimport["operations_skipped"] == summary["operations_imported"]

    # 5. Check Card debits are imported as ExpenseOperation (with merchant name & category)
    # Line 4 in CSV: TRAINLINE, TRANSPORT, Card debit, -20.50 EUR
    expense_ops = session.exec(select(Operation).where(Operation.operation_type == "expense")).all()
    assert len(expense_ops) > 0

    trainline_op = next(o for o in expense_ops if o.merchant_name == "TRAINLINE")
    assert trainline_op.merchant_category == "TRANSPORT"
    assert trainline_op.total_amount == Decimal("-20.50")
    assert trainline_op.currency == "EUR"

    # Check Card credits are imported as RevenueOperation (with merchant name & category)
    # Line 134 in CSV: Card credit, AMAZON.BE* BI0DY8UH5, RETAIL_STORES, 31.20 EUR
    revenue_ops = session.exec(select(Operation).where(Operation.operation_type == "revenue")).all()
    assert len(revenue_ops) > 0
    amazon_op = next(o for o in revenue_ops if o.merchant_name == "AMAZON.BE* BI0DY8UH5")
    assert amazon_op.merchant_category == "RETAIL_STORES"
    assert amazon_op.total_amount == Decimal("31.20")
    assert amazon_op.currency == "EUR"

    # 6. Check Interest operations are imported with correct types
    interest_ops = session.exec(select(Operation).where(Operation.operation_type == "interest")).all()
    assert len(interest_ops) > 0

    # Line 2: Interest on cash -> cash_interest
    cash_interest_op = next(
        (o for o in interest_ops if o.transaction_id == "7e830324-42b5-4bb0-bee9-56d12d3c591c"),
        None,
    )
    assert cash_interest_op is not None
    assert cash_interest_op.interest_type == InterestType.CASH_INTEREST
    assert cash_interest_op.total_amount == Decimal("0.02")

    # Line 3: Lending interest -> lending_interest
    lending_interest_op = next(
        (o for o in interest_ops if o.transaction_id == "d9700e57-3f5f-4389-99fb-231eb592fea3"),
        None,
    )
    assert lending_interest_op is not None
    assert lending_interest_op.interest_type == InterestType.LENDING_INTEREST
    assert lending_interest_op.total_amount == Decimal("0.01")

    # Line 9: Spending cashback -> cashback
    cashback_op = next((o for o in interest_ops if o.transaction_id == "7a0f01e5-1075-4731-91b6-a71fa4e3d7a8"), None)
    assert cashback_op is not None
    assert cashback_op.interest_type == InterestType.CASHBACK
    assert cashback_op.total_amount == Decimal("0.06")


def test_get_import_metadata(client, session):
    user = cast("User", UserFactory(email="import_meta@example.com"))
    session.commit()
    session.refresh(user)

    response = client.post(
        "/api/auth/token",
        data={"username": "import_meta@example.com", "password": "SeedP@ss1!"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/portfolios/import-metadata", headers=headers)
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


def test_import_with_custom_date_format(session):
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

    summary = import_portfolio_transactions(
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
        "/api/auth/token",
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
        f"/api/import-file-schemas/{schema1.id}",
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
        f"/api/import-file-schemas/{schema2.id}",
        json={"name": "Stolen Template"},
        headers=headers1,
    )
    assert response.status_code == 404

    # 3. User 1 tries to update a public template
    public_schema = session.exec(select(ImportFileSchema).where(ImportFileSchema.is_public)).first()
    assert public_schema is not None
    response = client.put(
        f"/api/import-file-schemas/{public_schema.id}",
        json={"name": "Malicious public edit"},
        headers=headers1,
    )
    assert response.status_code == 404


def test_import_dividend_without_price_per_share(session):
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

    summary = import_portfolio_transactions(
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
