from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

import polars as pl
from fastapi import status

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlmodel import Session

from src.logic.split_adjustment import compute_cost_basis, compute_split_adjusted_operations
from src.models import TradeSide
from tests.factories import (
    AllocationFactory,
    FinancialAccountFactory,
    PortfolioFactory,
    PositionFactory,
    RawTransactionFactory,
    UserFactory,
)


def test_split_adjustment_logic_single_split():
    # Setup trades and a split:
    # 2026-01-01: BUY 10 shares @ 100 (total = 1000)
    # 2026-01-05: SPLIT 4:1 (ratio = 4.0)
    # 2026-01-10: BUY 5 shares @ 30 (total = 150)
    rows = [
        {
            "operation_type": "trade",
            "trade_side": "buy",
            "executed_at": datetime(2026, 1, 1, tzinfo=UTC),
            "quantity": 10.0,
            "unit_price": 100.0,
            "total_amount": 1000.0,
        },
        {
            "operation_type": "stock_split",
            "trade_side": None,
            "executed_at": datetime(2026, 1, 5, tzinfo=UTC),
            "quantity": 30.0,  # delta
            "unit_price": None,
            "total_amount": 0.0,
            "split_ratio": 4.0,
        },
        {
            "operation_type": "trade",
            "trade_side": "buy",
            "executed_at": datetime(2026, 1, 10, tzinfo=UTC),
            "quantity": 5.0,
            "unit_price": 30.0,
            "total_amount": 150.0,
        },
    ]
    df = pl.DataFrame(rows)
    adjusted = compute_split_adjusted_operations(df)

    # First trade (pre-split) should have factor 4.0, adjusted quantity 40.0, adjusted unit price 25.0
    row1 = adjusted.filter(pl.col("executed_at") == datetime(2026, 1, 1, tzinfo=UTC)).to_dicts()[0]
    assert row1["split_factor"] == 4.0
    assert row1["adj_quantity"] == 40.0
    assert row1["adj_unit_price"] == 25.0

    # Second trade (post-split) should have factor 1.0, adjusted quantity 5.0, adjusted unit price 30.0
    row3 = adjusted.filter(pl.col("executed_at") == datetime(2026, 1, 10, tzinfo=UTC)).to_dicts()[0]
    assert row3["split_factor"] == 1.0
    assert row3["adj_quantity"] == 5.0
    assert row3["adj_unit_price"] == 30.0

    # Cost basis calculation:
    # total invested: 1000 + 150 = 1150
    # total shares (split adjusted): 40 (adjusted from trade 1) + 5 (trade 3) = 45
    # avg cost basis = 1150 / 45 ≈ 25.55555556
    metrics = compute_cost_basis(df)
    assert metrics["total_invested"] == Decimal("1150.00")
    assert metrics["total_shares"] == Decimal("45.00000000")
    assert metrics["avg_cost_basis"] == (Decimal(1150) / Decimal(45)).quantize(Decimal("0.00000001"))


def test_split_adjustment_logic_multiple_splits():
    # 2026-01-01: BUY 10 shares @ 100
    # 2026-01-05: SPLIT 2:1 (ratio = 2.0)
    # 2026-01-06: BUY 5 shares @ 50
    # 2026-01-10: SPLIT 3:1 (ratio = 3.0)
    rows = [
        {
            "operation_type": "trade",
            "trade_side": "buy",
            "executed_at": datetime(2026, 1, 1, tzinfo=UTC),
            "quantity": 10.0,
            "unit_price": 100.0,
            "total_amount": 1000.0,
        },
        {
            "operation_type": "stock_split",
            "trade_side": None,
            "executed_at": datetime(2026, 1, 5, tzinfo=UTC),
            "quantity": 10.0,
            "unit_price": None,
            "total_amount": 0.0,
            "split_ratio": 2.0,
        },
        {
            "operation_type": "trade",
            "trade_side": "buy",
            "executed_at": datetime(2026, 1, 6, tzinfo=UTC),
            "quantity": 5.0,
            "unit_price": 50.0,
            "total_amount": 250.0,
        },
        {
            "operation_type": "stock_split",
            "trade_side": None,
            "executed_at": datetime(2026, 1, 10, tzinfo=UTC),
            "quantity": 30.0,
            "unit_price": None,
            "total_amount": 0.0,
            "split_ratio": 3.0,
        },
    ]
    df = pl.DataFrame(rows)
    adjusted = compute_split_adjusted_operations(df)

    # First trade: factor should be 2.0 * 3.0 = 6.0
    row1 = adjusted.filter(pl.col("executed_at") == datetime(2026, 1, 1, tzinfo=UTC)).to_dicts()[0]
    assert row1["split_factor"] == 6.0
    assert row1["adj_quantity"] == 60.0
    assert abs(row1["adj_unit_price"] - (100.0 / 6.0)) < 1e-9

    # Second trade: factor should be 3.0
    row2 = adjusted.filter(pl.col("executed_at") == datetime(2026, 1, 6, tzinfo=UTC)).to_dicts()[0]
    assert row2["split_factor"] == 3.0
    assert row2["adj_quantity"] == 15.0
    assert abs(row2["adj_unit_price"] - (50.0 / 3.0)) < 1e-9


def test_split_adjustment_logic_reverse_split():
    # 2026-01-01: BUY 100 shares @ 5
    # 2026-01-05: REVERSE SPLIT 1:10 (ratio = 0.1)
    rows = [
        {
            "operation_type": "trade",
            "trade_side": "buy",
            "executed_at": datetime(2026, 1, 1, tzinfo=UTC),
            "quantity": 100.0,
            "unit_price": 5.0,
            "total_amount": 500.0,
        },
        {
            "operation_type": "stock_split",
            "trade_side": None,
            "executed_at": datetime(2026, 1, 5, tzinfo=UTC),
            "quantity": -90.0,
            "unit_price": None,
            "total_amount": 0.0,
            "split_ratio": 0.1,
        },
    ]
    df = pl.DataFrame(rows)
    adjusted = compute_split_adjusted_operations(df)

    # First trade: factor 0.1, adj quantity 10.0, adj price 50.0
    row1 = adjusted.filter(pl.col("executed_at") == datetime(2026, 1, 1, tzinfo=UTC)).to_dicts()[0]
    assert row1["split_factor"] == 0.1
    assert row1["adj_quantity"] == 10.0
    assert row1["adj_unit_price"] == 50.0


def get_auth_headers(client: TestClient, email: str, password: str = "SeedP@ss1!") -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": password},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_cost_basis_endpoint(client: TestClient, session: Session):
    user = UserFactory(email="split_test@example.com")
    session.commit()
    headers = get_auth_headers(client, "split_test@example.com")

    portfolio = PortfolioFactory(user=user)
    position = PositionFactory(portfolio=portfolio)
    account = FinancialAccountFactory()
    session.commit()

    # 1. A BUY trade routed to the position via its default allocation.
    buy = RawTransactionFactory(
        financial_account=account,
        operation_type="trade",
        trade_side=TradeSide.BUY,
        executed_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
        quantity=Decimal("10.00"),
        unit_price=Decimal("100.00"),
        total_amount=Decimal("1000.00"),
    )
    AllocationFactory(
        raw_transaction=buy,
        position=position,
        quantity=Decimal("10.00"),
        amount=Decimal("1000.00"),
    )

    # 2. A stock split (4:1) routed to the same position.
    split = RawTransactionFactory(
        financial_account=account,
        operation_type="stock_split",
        trade_side=None,
        executed_at=datetime(2026, 1, 5, 12, 0, 0, tzinfo=UTC),
        split_ratio=Decimal("4.0"),
        pre_split_quantity=Decimal("10.00"),
        quantity=Decimal("30.00"),
        total_amount=Decimal("0.00"),
    )
    AllocationFactory(
        raw_transaction=split,
        position=position,
        quantity=Decimal("30.00"),
        amount=Decimal("0.00"),
    )
    session.commit()

    resp = client.get(f"/api/v1/positions/{position.id}/cost_basis", headers=headers)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()

    assert data["position_id"] == position.id
    assert Decimal(data["avg_cost_basis"]) == Decimal("25.00000000")
    assert Decimal(data["total_invested"]) == Decimal("1000.00")
    assert Decimal(data["total_shares"]) == Decimal("40.00000000")
    assert len(data["split_events"]) == 1
    assert Decimal(data["split_events"][0]["split_ratio"]) == Decimal("4.0")
    assert Decimal(data["split_events"][0]["pre_split_quantity"]) == Decimal("10.00")
    assert Decimal(data["split_events"][0]["post_split_quantity"]) == Decimal("40.00")
