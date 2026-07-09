from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock, patch

import pytest
from sqlmodel import select

from src.models import (
    Portfolio,
    Position,
    User,
)
from src.services.financial_info import TickerProfile
from src.services.import_service import import_portfolio_transactions
from tests.factories import (
    PortfolioFactory,
    UserFactory,
)


@pytest.mark.asyncio
async def test_import_resolves_missing_asset_name_using_ticker(session):
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
        },
        "type_mappings": {
            "buy": ["BUY"],
        },
        "date_formats": {
            "executed_at": "%Y-%m-%d %H:%M:%S",
        },
    }

    csv_content = b"Type,Date,Ticker,AssetName,Total,Currency,Qty\nBUY,2026-06-01 15:30:00,AAPL,,150.0,USD,10\n"

    mock_get_profile = AsyncMock(
        return_value=TickerProfile(
            symbol="AAPL",
            name="Apple Inc.",
        ),
    )

    with patch(
        "src.services.import_service.FinancialInfoService.get_profile",
        mock_get_profile,
    ):
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
    pos = session.exec(select(Position).where(Position.portfolio_id == portfolio.id, Position.ticker == "AAPL")).first()
    assert pos is not None
    assert pos.name == "Apple Inc."


@pytest.mark.asyncio
async def test_import_with_enrich_asset_names_never(session):
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
        },
        "type_mappings": {
            "buy": ["BUY"],
        },
        "date_formats": {
            "executed_at": "%Y-%m-%d %H:%M:%S",
        },
        "enrich_asset_names": "never",
    }

    csv_content = b"Type,Date,Ticker,AssetName,Total,Currency,Qty\nBUY,2026-06-01 15:30:00,AAPL,,150.0,USD,10\n"

    mock_get_profile = AsyncMock(
        return_value=TickerProfile(
            symbol="AAPL",
            name="Apple Inc.",
        ),
    )

    with patch(
        "src.services.import_service.FinancialInfoService.get_profile",
        mock_get_profile,
    ):
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
    pos = session.exec(select(Position).where(Position.portfolio_id == portfolio.id, Position.ticker == "AAPL")).first()
    assert pos is not None
    assert pos.name == "AAPL"


@pytest.mark.asyncio
async def test_import_with_enrich_asset_names_always(session):
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
        },
        "type_mappings": {
            "buy": ["BUY"],
        },
        "date_formats": {
            "executed_at": "%Y-%m-%d %H:%M:%S",
        },
        "enrich_asset_names": "always",
    }

    # CSV has name "Apple" set, but we want it resolved and overwritten with "Apple Inc."
    csv_content = b"Type,Date,Ticker,AssetName,Total,Currency,Qty\nBUY,2026-06-01 15:30:00,AAPL,Apple,150.0,USD,10\n"

    mock_get_profile = AsyncMock(
        return_value=TickerProfile(
            symbol="AAPL",
            name="Apple Inc.",
        ),
    )

    with patch(
        "src.services.import_service.FinancialInfoService.get_profile",
        mock_get_profile,
    ):
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
    pos = session.exec(select(Position).where(Position.portfolio_id == portfolio.id, Position.ticker == "AAPL")).first()
    assert pos is not None
    assert pos.name == "Apple Inc."


@pytest.mark.asyncio
async def test_import_with_enrich_asset_names_when_empty(session):
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
        },
        "type_mappings": {
            "buy": ["BUY"],
        },
        "date_formats": {
            "executed_at": "%Y-%m-%d %H:%M:%S",
        },
        "enrich_asset_names": "when_empty",
    }

    csv_content = (
        b"Type,Date,Ticker,AssetName,Total,Currency,Qty\nBUY,2026-06-01 15:30:00,AAPL,Apple Custom,150.0,USD,10\n"
    )

    mock_get_profile = AsyncMock(
        return_value=TickerProfile(
            symbol="AAPL",
            name="Apple Inc.",
        ),
    )

    with patch(
        "src.services.import_service.FinancialInfoService.get_profile",
        mock_get_profile,
    ):
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
    pos = session.exec(select(Position).where(Position.portfolio_id == portfolio.id, Position.ticker == "AAPL")).first()
    assert pos is not None
    assert pos.name == "Apple Custom"


@pytest.mark.asyncio
async def test_import_with_enrich_asset_names_fails_when_ticker_not_found(session):
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
        },
        "type_mappings": {
            "buy": ["BUY"],
        },
        "date_formats": {
            "executed_at": "%Y-%m-%d %H:%M:%S",
        },
        "enrich_asset_names": "always",
    }

    csv_content = (
        b"Type,Date,Ticker,AssetName,Total,Currency,Qty\nBUY,2026-06-01 15:30:00,INVALID_TICKER,,150.0,USD,10\n"
    )

    mock_get_profile = AsyncMock(return_value=None)

    with (
        patch(
            "src.services.import_service.FinancialInfoService.get_profile",
            mock_get_profile,
        ),
        pytest.raises(ValueError, match=r"Ticker 'INVALID_TICKER' could not be resolved to a valid asset name\."),
    ):
        await import_portfolio_transactions(
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
