from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel

from src.database import get_session
from src.main import app
from src.models import SABase
from src.services.financial_info import (
    FinancialInfoService,
)
from tests.factories import UserFactory, set_factory_session
from tests.test_api import get_auth_headers


@pytest.fixture(name="engine")
def fixture_engine():
    """In-memory SQLite engine with all tables created."""
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    SQLModel.metadata.create_all(eng)
    SABase.metadata.create_all(eng)
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
async def test_service_get_profile():
    mock_info = {
        "symbol": "AAPL",
        "longName": "Apple Inc.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "longBusinessSummary": "Summary of Apple...",
        "website": "https://apple.com",
        "country": "US",
        "exchange": "NMS",
        "financialCurrency": "USD",
        "marketCap": 3000000000000,
    }

    with patch("src.services.financial_info.service.yf.Ticker") as mock_ticker_cls:
        mock_ticker = MagicMock()
        mock_ticker.info = mock_info
        mock_ticker_cls.return_value = mock_ticker

        provider = FinancialInfoService()
        profile = await provider.get_profile("AAPL")

        assert profile.symbol == "AAPL"
        assert profile.name == "Apple Inc."
        assert profile.sector == "Technology"
        assert profile.market_cap == Decimal(3000000000000)


@pytest.mark.asyncio
async def test_service_get_quote():
    mock_fast_info = MagicMock()
    mock_fast_info.last_price = 150.50
    mock_fast_info.open = 149.00
    mock_fast_info.day_high = 151.00
    mock_fast_info.day_low = 148.00
    mock_fast_info.previous_close = 149.50
    mock_fast_info.volume = 1000000
    mock_fast_info.currency = "USD"

    mock_fast_info.get.side_effect = {
        "lastPrice": 150.50,
        "open": 149.00,
        "dayHigh": 151.00,
        "dayLow": 148.00,
        "previousClose": 149.50,
        "volume": 1000000,
        "currency": "USD",
    }.get

    mock_info = {
        "bid": 150.45,
        "ask": 150.55,
    }

    with patch("src.services.financial_info.service.yf.Ticker") as mock_ticker_cls:
        mock_ticker = MagicMock()
        mock_ticker.fast_info = mock_fast_info
        mock_ticker.info = mock_info
        mock_ticker_cls.return_value = mock_ticker

        provider = FinancialInfoService()
        quote = await provider.get_quote("AAPL")

        assert quote.symbol == "AAPL"
        assert quote.price == Decimal("150.50")
        assert quote.change == Decimal("1.00")  # 150.50 - 149.50
        assert quote.open == Decimal("149.00")
        assert quote.bid == Decimal("150.45")
        assert quote.ask == Decimal("150.55")


@pytest.mark.asyncio
async def test_service_get_history():
    df_history = pd.DataFrame(
        [
            {"Open": 150.0, "High": 152.0, "Low": 149.0, "Close": 151.5, "Volume": 5000000},
        ],
        index=pd.DatetimeIndex(["2026-06-01"]),
    )

    with patch("src.services.financial_info.service.yf.Ticker") as mock_ticker_cls:
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = df_history
        mock_ticker_cls.return_value = mock_ticker

        provider = FinancialInfoService()
        history = await provider.get_history("AAPL")

        assert len(history) == 1
        assert history[0].open == Decimal("150.0")
        assert history[0].close == Decimal("151.5")
        assert history[0].volume == 5000000


@pytest.mark.asyncio
async def test_service_get_financials():
    df_income = pd.DataFrame(
        {pd.Timestamp("2023-09-30"): [383285000000, 96995000000]},
        index=["Total Revenue", "Net Income"],
    )
    df_balance = pd.DataFrame(
        {pd.Timestamp("2023-09-30"): [352585000000, 62146000000]},
        index=["Total Assets", "Stockholders Equity"],
    )
    df_cashflow = pd.DataFrame(
        {pd.Timestamp("2023-09-30"): [110543000000, -95738000000]},
        index=["Operating Cash Flow", "Investing Cash Flow"],
    )

    with patch("src.services.financial_info.service.yf.Ticker") as mock_ticker_cls:
        mock_ticker = MagicMock()
        mock_ticker.income_stmt = df_income
        mock_ticker.balance_sheet = df_balance
        mock_ticker.cashflow = df_cashflow
        mock_ticker_cls.return_value = mock_ticker

        provider = FinancialInfoService()
        report = await provider.get_financials("AAPL")

        assert len(report.income_statement) == 2
        assert report.income_statement[0].metric == "Total Revenue"
        assert report.income_statement[0].value == Decimal(383285000000)


def test_api_endpoints(client: TestClient, session: Session):
    user = UserFactory(email="marketuser@example.com")
    session.commit()
    headers = get_auth_headers(client, user.email)

    mock_info = {
        "symbol": "AAPL",
        "longName": "Apple Inc.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "longBusinessSummary": "Summary...",
        "website": "https://apple.com",
        "country": "US",
        "exchange": "NMS",
        "financialCurrency": "USD",
        "marketCap": 3000000000000,
    }

    mock_fast_info = MagicMock()
    mock_fast_info.last_price = 150.50
    mock_fast_info.open = 149.00
    mock_fast_info.day_high = 151.00
    mock_fast_info.day_low = 148.00
    mock_fast_info.previous_close = 149.50
    mock_fast_info.volume = 1000000
    mock_fast_info.currency = "USD"
    mock_fast_info.get.side_effect = {
        "lastPrice": 150.50,
        "open": 149.00,
        "dayHigh": 151.00,
        "dayLow": 148.00,
        "previousClose": 149.50,
        "volume": 1000000,
        "currency": "USD",
    }.get

    df_history = pd.DataFrame(
        [{"Open": 150.0, "High": 152.0, "Low": 149.0, "Close": 151.5, "Volume": 5000000}],
        index=pd.DatetimeIndex(["2026-06-01"]),
    )

    df_income = pd.DataFrame(
        {pd.Timestamp("2023-09-30"): [383285000000]},
        index=["Total Revenue"],
    )
    df_balance = pd.DataFrame(
        {pd.Timestamp("2023-09-30"): [352585000000]},
        index=["Total Assets"],
    )
    df_cashflow = pd.DataFrame(
        {pd.Timestamp("2023-09-30"): [110543000000]},
        index=["Operating Cash Flow"],
    )

    with patch("src.services.financial_info.service.yf.Ticker") as mock_ticker_cls:
        mock_ticker = MagicMock()
        mock_ticker.info = mock_info
        mock_ticker.fast_info = mock_fast_info
        mock_ticker.history.return_value = df_history
        mock_ticker.income_stmt = df_income
        mock_ticker.balance_sheet = df_balance
        mock_ticker.cashflow = df_cashflow
        mock_ticker_cls.return_value = mock_ticker

        # 1. Profile Endpoint
        response = client.get("/api/v1/financial-info/profile/AAPL", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == "Apple Inc."

        # 2. Quote Endpoint
        response = client.get("/api/v1/financial-info/quote/AAPL", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        assert Decimal(response.json()["price"]) == Decimal("150.50")

        # 3. History Endpoint
        response = client.get("/api/v1/financial-info/history/AAPL?period=1mo&interval=1d", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 1
        assert Decimal(response.json()[0]["close"]) == Decimal("151.5")

        # 4. Financials Endpoint
        response = client.get("/api/v1/financial-info/financials/AAPL", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["income_statement"][0]["metric"] == "Total Revenue"
