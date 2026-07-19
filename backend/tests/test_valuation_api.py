"""End-to-end tests for the portfolio valuation endpoint."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status

from src.models import AssetPrice, AssetType, TradeSide

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
from tests.factories import (
    AllocationFactory,
    PortfolioFactory,
    PositionFactory,
    RawTransactionFactory,
    UserFactory,
)
from tests.test_api import get_auth_headers


@pytest.fixture(autouse=True)
def _no_price_sync():
    """Valuation tests seed asset_price rows directly — never call yfinance."""
    with patch("src.services.valuation_service.ensure_price_history", new=AsyncMock(return_value={})):
        yield


def _seed_portfolio(session, *, days_ago: int = 10):
    user = UserFactory()
    portfolio = PortfolioFactory(user=user)
    position = PositionFactory(
        portfolio=portfolio,
        asset_type=AssetType.STOCK,
        ticker="AAA",
        currency="EUR",
        quantity=Decimal(10),
    )
    executed = datetime.now(UTC) - timedelta(days=days_ago)
    raw = RawTransactionFactory(
        quantity=Decimal(10),
        unit_price=Decimal(100),
        total_amount=Decimal(1000),
        currency="EUR",
        trade_side=TradeSide.BUY,
        executed_at=executed,
    )
    AllocationFactory(
        raw_transaction=raw,
        position=position,
        quantity=Decimal(10),
        amount=Decimal(1000),
        currency="EUR",
    )
    session.commit()
    return user, portfolio, position


def _seed_prices(session, symbol: str, closes: dict[date, str], currency: str = "EUR"):
    for price_date, close in closes.items():
        session.add(AssetPrice(symbol=symbol, price_date=price_date, close=Decimal(close), currency=currency))
    session.commit()


def test_valuation_returns_series_positions_and_allocation(client: TestClient, session):
    user, portfolio, position = _seed_portfolio(session)
    today = datetime.now(UTC).date()
    _seed_prices(session, "AAA", {today - timedelta(days=1): "120", today: "125"})

    headers = get_auth_headers(client, user.email)
    response = client.get(f"/api/v1/portfolios/{portfolio.id}/valuation?range=all", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["currency"] == "EUR"
    assert body["current"]["market_value"] == "1250.00"
    assert body["current"]["net_invested"] == "1000.00"
    assert body["current"]["gain"] == "250.00"

    assert len(body["series"]) == 11  # 10 days ago .. today inclusive
    assert body["series"][0]["net_invested"] == "1000.00"
    assert body["series"][-1]["market_value"] == "1250.00"

    assert len(body["positions"]) == 1
    pos = body["positions"][0]
    assert pos["position_id"] == position.id
    assert pos["position_ids"] == [position.id]
    assert pos["quantity"] == "10.00000000"
    assert pos["price_status"] == "ok"
    assert pos["market_value"] == "1250.00"
    assert pos["total_invested"] == "1000.00"

    assert body["allocation"] == [
        {"asset_type": "stock", "market_value": "1250.00", "percentage": "100.00"},
    ]


def test_valuation_marks_stale_prices(client: TestClient, session):
    user, portfolio, _position = _seed_portfolio(session)
    today = datetime.now(UTC).date()
    _seed_prices(session, "AAA", {today - timedelta(days=8): "120"})

    headers = get_auth_headers(client, user.email)
    response = client.get(f"/api/v1/portfolios/{portfolio.id}/valuation", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["positions"][0]["price_status"] == "stale"


def test_valuation_without_prices_falls_back_to_cost(client: TestClient, session):
    user, portfolio, _position = _seed_portfolio(session)

    headers = get_auth_headers(client, user.email)
    response = client.get(f"/api/v1/portfolios/{portfolio.id}/valuation", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["positions"][0]["price_status"] == "cost_fallback"
    assert body["positions"][0]["market_value"] == "1000.00"
    assert body["current"]["market_value"] == "1000.00"


def test_valuation_empty_portfolio_returns_zeroes(client: TestClient, session):
    user = UserFactory()
    portfolio = PortfolioFactory(user=user)
    session.commit()

    headers = get_auth_headers(client, user.email)
    response = client.get(f"/api/v1/portfolios/{portfolio.id}/valuation", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["series"] != []  # a flat zero line, not an error
    assert body["current"]["market_value"] == "0.00"
    assert body["positions"] == []
    assert body["allocation"] == []


def test_valuation_foreign_portfolio_404(client: TestClient, session):
    _user, portfolio, _position = _seed_portfolio(session)
    intruder = UserFactory()
    session.commit()

    headers = get_auth_headers(client, intruder.email)
    response = client.get(f"/api/v1/portfolios/{portfolio.id}/valuation", headers=headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_valuation_unassigned_pseudo_portfolio(client: TestClient, session):
    user, portfolio, _position = _seed_portfolio(session)
    portfolio.is_active = False
    session.add(portfolio)
    session.commit()

    headers = get_auth_headers(client, user.email)
    response = client.get("/api/v1/portfolios/unassigned/valuation", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["portfolio_id"] == "unassigned"
    assert len(body["positions"]) == 1


def test_valuation_rejects_bad_portfolio_id(client: TestClient, session):
    user = UserFactory()
    session.commit()

    headers = get_auth_headers(client, user.email)
    response = client.get("/api/v1/portfolios/not-a-number/valuation", headers=headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_valuation_aggregates_same_ticker_into_one_row(client: TestClient, session):
    user, portfolio, position = _seed_portfolio(session)
    sibling = PositionFactory(
        portfolio=portfolio,
        asset_type=AssetType.STOCK,
        ticker="AAA",
        currency="EUR",
        quantity=Decimal(5),
    )
    raw = RawTransactionFactory(
        quantity=Decimal(5),
        unit_price=Decimal(100),
        total_amount=Decimal(500),
        currency="EUR",
        trade_side=TradeSide.BUY,
        executed_at=datetime.now(UTC) - timedelta(days=3),
    )
    AllocationFactory(
        raw_transaction=raw,
        position=sibling,
        quantity=Decimal(5),
        amount=Decimal(500),
        currency="EUR",
    )
    session.commit()
    _seed_prices(session, "AAA", {datetime.now(UTC).date(): "120"})

    headers = get_auth_headers(client, user.email)
    response = client.get(f"/api/v1/portfolios/{portfolio.id}/valuation?range=all", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert len(body["positions"]) == 1
    row = body["positions"][0]
    assert sorted(row["position_ids"]) == sorted([position.id, sibling.id])
    assert row["quantity"] == "15.00000000"
    assert row["market_value"] == "1800.00"
    assert row["total_invested"] == "1500.00"
    assert row["gain"] == "300.00"


def test_valuation_range_clamps_to_first_transaction(client: TestClient, session):
    user, portfolio, _position = _seed_portfolio(session, days_ago=5)

    headers = get_auth_headers(client, user.email)
    response = client.get(f"/api/v1/portfolios/{portfolio.id}/valuation?range=1y", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()["series"]) == 6  # clamped to first flow, not 365 days
