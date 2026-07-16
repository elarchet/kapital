from __future__ import annotations

import json
from decimal import Decimal
from typing import cast

import pytest
from sqlmodel import select

from src.models import Allocation, Portfolio, Position, RawTransaction, User
from src.models.import_file_schema import ImportFileSchema
from src.services.import_service import import_portfolio_transactions
from tests.factories import (
    PortfolioFactory,
    UserFactory,
)


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

    assert summary["raw_transactions_imported"] == 1
    op = session.exec(select(RawTransaction)).first()
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

    assert summary["raw_transactions_imported"] == 1
    op = session.exec(select(RawTransaction).where(RawTransaction.operation_type == "dividend")).first()
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
    # - 2 RawTransactions imported (the first and third row)
    # - 1 duplicate skipped (the second duplicate row)
    assert summary["positions_created"] == 2
    assert summary["raw_transactions_imported"] == 2
    assert summary["skipped_duplicates"] == 1

    # Verify the asset position balance in the database
    pos = session.exec(
        select(Position).where(Position.portfolio_id == portfolio.id, Position.name == "NewAsset"),
    ).first()
    assert pos is not None
    assert pos.quantity == Decimal("20.0")  # 10 + 10

    # RawTransactions carry no position_id; they are queried by their asset fields
    # and traced to the position through their default allocations.
    txns = session.exec(select(RawTransaction).where(RawTransaction.name == "NewAsset")).all()
    assert len(txns) == 2

    allocations = session.exec(select(Allocation).where(Allocation.position_id == pos.id)).all()
    assert len(allocations) == 2
    assert all(a.raw_transaction.name == "NewAsset" for a in allocations)


@pytest.mark.asyncio
async def test_import_stock_split_schema_driven(session):
    # Setup test portfolio and user
    user = cast("User", UserFactory())
    portfolio = cast("Portfolio", PortfolioFactory(user=user))
    session.commit()

    # Custom mapping config utilizing split_sub_type column and enum_mappings
    custom_mappings = {
        "columns": {
            "operation_type": "Type",
            "executed_at": "Date",
            "name": "Asset",
            "ticker": "Symbol",
            "total_amount": "Total",
            "currency": "Curr",
            "quantity": "Shares",
            "split_sub_type": "SubType",
        },
        "type_mappings": {
            "buy": ["BUY"],
            "stock_split": ["SPLIT"],
        },
        "enum_mappings": {
            "split_sub_type": {
                "close": ["PRE_SPLIT"],
                "open": ["POST_SPLIT"],
            },
        },
    }

    # CSV has buy trade followed by stock split pre/post rows mapped via split_sub_type
    csv_content = (
        b"Type,Date,Asset,Symbol,Total,Curr,Shares,SubType\n"
        b"BUY,2026-06-01 12:00:00,Nvidia,NVDA,1000.0,USD,10.0,\n"
        b"SPLIT,2026-06-02 12:00:00,Nvidia,NVDA,0.0,USD,10.0,PRE_SPLIT\n"
        b"SPLIT,2026-06-02 12:00:00,Nvidia,NVDA,0.0,USD,100.0,POST_SPLIT\n"
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

    assert summary["raw_transactions_imported"] == 2  # 1 buy trade, 1 combined stock split
    pos = session.exec(
        select(Position).where(Position.portfolio_id == portfolio.id, Position.ticker == "NVDA"),
    ).first()
    assert pos is not None
    # 10 shares bought, then split 1 to 10 (+90 shares). Net = 100.0 shares.
    assert pos.quantity == Decimal("100.0")

    # Verify the combined stock split RawTransaction details
    split_op = session.exec(
        select(RawTransaction).where(
            RawTransaction.operation_type == "stock_split",
            RawTransaction.ticker == "NVDA",
        ),
    ).first()
    assert split_op is not None
    assert split_op.split_ratio == Decimal("10.0")
    assert split_op.pre_split_quantity == Decimal("10.0")
    assert split_op.quantity == Decimal("90.0")  # net delta shares added


@pytest.mark.asyncio
async def test_import_with_formula_total_amount(session):
    """total_amount computed as Qty * Price with no direct column mapping (Fortuneo case)."""
    user = cast("User", UserFactory())
    portfolio = cast("Portfolio", PortfolioFactory(user=user))
    session.commit()

    custom_mappings = {
        "columns": {
            "operation_type": "Type",
            "executed_at": "Date",
            "name": "Asset",
            "ticker": "Ticker",
            "currency": "Currency",
            "quantity": "Qty",
            "unit_price": "Price",
        },
        "type_mappings": {"buy": ["BUY"]},
        "formulas": {
            "total_amount": {"trade": [{"col": "Qty"}, {"op": "*"}, {"col": "Price"}]},
        },
    }
    csv_content = b"Type,Date,Asset,Ticker,Qty,Price,Currency\nBUY,2026-06-01 15:30:00,Apple,AAPL,10,150.5,USD\n"

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

    assert summary["raw_transactions_imported"] == 1
    op = session.exec(select(RawTransaction)).first()
    assert op is not None
    assert op.total_amount == Decimal("1505.0")


@pytest.mark.asyncio
async def test_import_with_fee_sum_formula(session):
    """fee_amount summed across several fee columns, blanks counting as zero (T212 case)."""
    user = cast("User", UserFactory())
    portfolio = cast("Portfolio", PortfolioFactory(user=user))
    session.commit()

    custom_mappings = {
        "columns": {
            "operation_type": "Type",
            "executed_at": "Date",
            "name": "Asset",
            "ticker": "Ticker",
            "currency": "Currency",
            "quantity": "Qty",
            "unit_price": "Price",
            "total_amount": "Total",
        },
        "type_mappings": {"buy": ["BUY"]},
        "formulas": {
            "fee_amount": [{"col": "FeeA"}, {"op": "+"}, {"col": "FeeB"}, {"op": "+"}, {"col": "FeeC"}],
        },
    }
    csv_content = (
        b"Type,Date,Asset,Ticker,Qty,Price,Total,Currency,FeeA,FeeB,FeeC\n"
        b"BUY,2026-06-01 15:30:00,Apple,AAPL,10,150.5,1505.0,USD,0.11,,0.25\n"
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

    assert summary["raw_transactions_imported"] == 1
    op = session.exec(select(RawTransaction)).first()
    assert op is not None
    assert len(op.fees) == 1
    assert op.fees[0].amount == Decimal("0.36")


@pytest.mark.asyncio
async def test_auto_id_without_transaction_id_column(session):
    """Brokers without any transaction-id column (Fortuneo) still get auto-generated IDs."""
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
        "type_mappings": {"buy": ["BUY"]},
        "enrich_transaction_ids": "when_empty",
    }
    csv_content = b"Type,Date,Asset,Total,Currency,Qty\nBUY,2026-06-01 15:30:00,Apple,150.0,USD,10\n"

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

    assert summary["raw_transactions_imported"] == 1
    op = session.exec(select(RawTransaction)).first()
    assert op is not None
    assert op.is_auto_id is True
    assert op.dedup_key.startswith("auto-")


@pytest.mark.asyncio
async def test_hash_columns_subset_stabilizes_dedup(session):
    """Changing a column excluded from hash_columns must not create a new transaction."""
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
        "type_mappings": {"buy": ["BUY"]},
        "hash_columns": ["Type", "Date", "Asset", "Qty"],
    }
    config = {
        "mappings": custom_mappings,
        "delimiter": ",",
        "decimal_separator": ".",
    }
    csv_v1 = b"Type,Date,Asset,Total,Currency,Qty\nBUY,2026-06-01 15:30:00,Apple,150.0,USD,10\n"
    # Same row, but the excluded 'Total' column changed.
    csv_v2 = b"Type,Date,Asset,Total,Currency,Qty\nBUY,2026-06-01 15:30:00,Apple,999.0,USD,10\n"

    summary1 = await import_portfolio_transactions(
        db=session,
        portfolio_id=portfolio.id,
        user_id=user.id,
        file_content=csv_v1,
        custom_schema_config=config,
    )
    summary2 = await import_portfolio_transactions(
        db=session,
        portfolio_id=portfolio.id,
        user_id=user.id,
        file_content=csv_v2,
        custom_schema_config=config,
    )

    assert summary1["raw_transactions_imported"] == 1
    assert summary2["raw_transactions_imported"] == 0
    assert summary2["skipped_duplicates"] == 1


@pytest.mark.asyncio
async def test_hash_columns_too_sparse_row_skipped(session):
    """A hash subset yielding <2 meaningful fields is rejected as invalid, not imported."""
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
        },
        "type_mappings": {"buy": ["BUY"]},
        "hash_columns": ["Empty1", "Empty2"],
    }
    csv_content = b"Type,Date,Asset,Total,Currency,Empty1,Empty2\nBUY,2026-06-01 15:30:00,Apple,150.0,USD,,\n"

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

    assert summary["raw_transactions_imported"] == 0
    assert summary["skipped_invalid"] == 1


@pytest.mark.asyncio
async def test_latin1_file_decodes(session):
    """Latin-1 exports (Fortuneo) must not crash the utf-8 decode path."""
    user = cast("User", UserFactory())
    portfolio = cast("Portfolio", PortfolioFactory(user=user))
    session.commit()

    custom_mappings = {
        "columns": {
            "operation_type": "Type",
            "executed_at": "Date",
            "name": "libellé",
            "total_amount": "Total",
            "currency": "Currency",
        },
        "type_mappings": {"buy": ["Achat Comptant"]},
    }
    csv_text = "Type,Date,libellé,Total,Currency\nAchat Comptant,2026-06-01 15:30:00,Société Générale,150.0,EUR\n"
    csv_content = csv_text.encode("latin-1")

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

    assert summary["raw_transactions_imported"] == 1
    op = session.exec(select(RawTransaction)).first()
    assert op is not None
    assert op.name == "Société Générale"


@pytest.mark.asyncio
async def test_import_multiple_fee_tax_groups(session):
    """Indexed fee/tax groups (fee_amount__2, ...) each become their own Fee row,
    with per-group transformations and enum mappings applied."""
    user = cast("User", UserFactory())
    portfolio = cast("Portfolio", PortfolioFactory(user=user))
    session.commit()

    custom_mappings = {
        "columns": {
            "operation_type": "Type",
            "executed_at": "Date",
            "name": "Asset",
            "ticker": "Ticker",
            "currency": "Currency",
            "quantity": "Qty",
            "unit_price": "Price",
            "total_amount": "Total",
            "fee_amount": "ConvFee",
            "fee_currency": "ConvFeeCur",
            "fee_amount__2": "Commission",
            "fee_type__2": "FeeKind",
            "tax_amount": "WHT",
        },
        "type_mappings": {"buy": ["BUY"]},
        "transformations": {
            "fee_amount__2": {"divisor": 100},
        },
        "enum_mappings": {
            "fee_type__2": {"commission": ["COM"]},
        },
    }
    csv_content = (
        b"Type,Date,Asset,Ticker,Qty,Price,Total,Currency,ConvFee,ConvFeeCur,Commission,FeeKind,WHT\n"
        b"BUY,2026-06-01 15:30:00,Apple,AAPL,10,150.5,1505.0,USD,0.15,EUR,250,COM,1.2\n"
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

    assert summary["raw_transactions_imported"] == 1
    op = session.exec(select(RawTransaction)).first()
    assert op is not None
    assert len(op.fees) == 3

    by_amount = {f.amount: f for f in op.fees}
    base_fee = by_amount[Decimal("0.15")]
    assert base_fee.currency == "EUR"
    assert base_fee.fee_type == "conversion"

    second_fee = by_amount[Decimal("2.5")]  # 250 / 100 via fee_amount__2 divisor
    assert second_fee.currency == "USD"  # falls back to the row currency
    assert second_fee.fee_type == "commission"  # via fee_type__2 enum mapping

    tax = by_amount[Decimal("1.2")]
    assert tax.currency == "USD"
    assert tax.fee_type == "withholding_tax"


@pytest.mark.asyncio
async def test_import_rawaction_columns_override_optype(session):
    """Split-type mappings key columns by raw action; those override the opType-keyed
    mapping for matching rows while other raw actions fall back to the opType key."""
    user = cast("User", UserFactory())
    portfolio = cast("Portfolio", PortfolioFactory(user=user))
    session.commit()

    custom_mappings = {
        "columns": {
            "operation_type": "Type",
            "executed_at": "Date",
            "name": "Asset",
            "currency": "Currency",
            "quantity": "Qty",
            "total_amount": {"DIV CASH": "TotalA", "dividend": "TotalB"},
        },
        "type_mappings": {"dividend": ["DIV CASH", "DIV ADJ"]},
        "split_types": ["dividend"],  # ignored by the backend, round-tripped for the UI
    }
    csv_content = (
        b"Type,Date,Asset,Qty,TotalA,TotalB,Currency\n"
        b"DIV CASH,2026-06-01 15:30:00,Apple,10,50.0,999.0,USD\n"
        b"DIV ADJ,2026-06-02 15:30:00,Apple,10,999.0,7.5,USD\n"
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

    assert summary["raw_transactions_imported"] == 2
    ops = session.exec(select(RawTransaction).order_by(RawTransaction.executed_at)).all()
    assert [op.total_amount for op in ops] == [Decimal("50.0"), Decimal("7.5")]
