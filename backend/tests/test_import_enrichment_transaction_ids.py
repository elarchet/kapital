from __future__ import annotations

from typing import cast

import pytest
from sqlmodel import select

from src.models import (
    Operation,
    Portfolio,
    User,
)
from src.schemas.operation import OperationRead
from src.services.import_service import import_portfolio_transactions
from tests.factories import (
    PortfolioFactory,
    UserFactory,
)


@pytest.mark.asyncio
async def test_import_generates_auto_transaction_id(session):
    user = cast("User", UserFactory())
    portfolio = cast("Portfolio", PortfolioFactory(user=user))
    session.commit()
    session.refresh(user)
    session.refresh(portfolio)

    custom_mappings = {
        "columns": {
            "operation_type": "Type",
            "executed_at": "Date",
            "ticker": "Ticker",
            "name": "AssetName",
            "total_amount": "Total",
            "currency": "Currency",
            "quantity": "Qty",
            "transaction_id": "TxID",
        },
        "type_mappings": {
            "buy": ["BUY"],
        },
        "date_formats": {
            "executed_at": "%Y-%m-%d %H:%M:%S",
        },
    }

    # Row has transaction ID column mapped but cell value is empty
    csv_content = (
        b"Type,Date,Ticker,AssetName,Total,Currency,Qty,TxID\nBUY,2026-06-01 15:30:00,MSFT,Microsoft,150.0,USD,10,\n"
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

    assert summary["operations_imported"] == 1
    op = session.exec(select(Operation)).first()
    assert op is not None

    assert op.transaction_id is not None
    assert op.transaction_id.startswith("auto-")

    op_read = OperationRead.model_validate(op)
    assert op_read.is_transaction_id_auto_generated is True


@pytest.mark.asyncio
async def test_import_distinct_tx_with_same_values_and_different_ids(session):
    user = cast("User", UserFactory())
    portfolio = cast("Portfolio", PortfolioFactory(user=user))
    session.commit()
    session.refresh(user)
    session.refresh(portfolio)

    custom_mappings = {
        "columns": {
            "operation_type": "Type",
            "executed_at": "Date",
            "ticker": "Ticker",
            "name": "AssetName",
            "total_amount": "Total",
            "currency": "Currency",
            "quantity": "Qty",
            "transaction_id": "TxID",
        },
        "type_mappings": {
            "buy": ["BUY"],
        },
        "date_formats": {
            "executed_at": "%Y-%m-%d %H:%M:%S",
        },
    }

    # Two rows with identical values but DIFFERENT transaction IDs
    csv_content = (
        b"Type,Date,Ticker,AssetName,Total,Currency,Qty,TxID\n"
        b"BUY,2026-06-01 15:30:00,TSLA,Tesla,150.0,USD,10,TX-1\n"
        b"BUY,2026-06-01 15:30:00,TSLA,Tesla,150.0,USD,10,TX-2\n"
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

    assert summary["operations_imported"] == 2
    assert summary["operations_skipped"] == 0


@pytest.mark.asyncio
async def test_import_with_generate_auto_ids_disabled(session):
    user = cast("User", UserFactory())
    portfolio = cast("Portfolio", PortfolioFactory(user=user))
    session.commit()
    session.refresh(user)
    session.refresh(portfolio)

    custom_mappings = {
        "columns": {
            "operation_type": "Type",
            "executed_at": "Date",
            "ticker": "Ticker",
            "name": "AssetName",
            "total_amount": "Total",
            "currency": "Currency",
            "quantity": "Qty",
            "transaction_id": "TxID",
        },
        "type_mappings": {
            "buy": ["BUY"],
        },
        "date_formats": {
            "executed_at": "%Y-%m-%d %H:%M:%S",
        },
        "generate_auto_ids": False,
    }

    csv_content = (
        b"Type,Date,Ticker,AssetName,Total,Currency,Qty,TxID\nBUY,2026-06-01 15:30:00,AAPL,Apple,150.0,USD,10,\n"
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

    assert summary["operations_imported"] == 1
    op = session.exec(select(Operation)).first()
    assert op is not None
    assert op.transaction_id is None


@pytest.mark.asyncio
async def test_import_with_enrich_transaction_ids_always(session):
    user = cast("User", UserFactory())
    portfolio = cast("Portfolio", PortfolioFactory(user=user))
    session.commit()
    session.refresh(user)
    session.refresh(portfolio)

    custom_mappings = {
        "columns": {
            "operation_type": "Type",
            "executed_at": "Date",
            "ticker": "Ticker",
            "name": "AssetName",
            "total_amount": "Total",
            "currency": "Currency",
            "quantity": "Qty",
            "transaction_id": "TxID",
        },
        "type_mappings": {
            "buy": ["BUY"],
        },
        "date_formats": {
            "executed_at": "%Y-%m-%d %H:%M:%S",
        },
        "enrich_transaction_ids": "always",
    }

    # CSV has transaction ID TxID set to 'TX-123'
    csv_content = (
        b"Type,Date,Ticker,AssetName,Total,Currency,Qty,TxID\nBUY,2026-06-01 15:30:00,AAPL,Apple,150.0,USD,10,TX-123\n"
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

    assert summary["operations_imported"] == 1
    op = session.exec(select(Operation)).first()
    assert op is not None
    assert op.transaction_id is not None
    assert op.transaction_id.startswith("auto-")


@pytest.mark.asyncio
async def test_import_with_enrich_transaction_ids_when_empty(session):
    user = cast("User", UserFactory())
    portfolio = cast("Portfolio", PortfolioFactory(user=user))
    session.commit()
    session.refresh(user)
    session.refresh(portfolio)

    custom_mappings = {
        "columns": {
            "operation_type": "Type",
            "executed_at": "Date",
            "ticker": "Ticker",
            "name": "AssetName",
            "total_amount": "Total",
            "currency": "Currency",
            "quantity": "Qty",
            "transaction_id": "TxID",
        },
        "type_mappings": {
            "buy": ["BUY"],
        },
        "date_formats": {
            "executed_at": "%Y-%m-%d %H:%M:%S",
        },
        "enrich_transaction_ids": "when_empty",
    }

    # CSV has 2 rows: one with transaction ID, one without
    csv_content = (
        b"Type,Date,Ticker,AssetName,Total,Currency,Qty,TxID\n"
        b"BUY,2026-06-01 15:30:00,AAPL,Apple,150.0,USD,10,TX-123\n"
        b"BUY,2026-06-02 15:30:00,MSFT,Microsoft,250.0,USD,5,\n"
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

    assert summary["operations_imported"] == 2
    ops = session.exec(select(Operation).order_by(Operation.executed_at)).all()
    assert len(ops) == 2
    assert ops[0].transaction_id == "TX-123"
    assert ops[1].transaction_id is not None
    assert ops[1].transaction_id.startswith("auto-")
