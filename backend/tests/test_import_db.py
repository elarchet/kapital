from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel

from src.models import AssetType, OrderStatus, OrderType, TradeOperation, TradeSide
from src.models.base import SABase
from src.services.import_db import (
    check_duplicate_operation,
    find_or_create_position,
    get_or_create_cash_position,
    get_or_create_institution_and_account,
)


@pytest.fixture(name="engine")
def fixture_engine():
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
    with Session(engine) as session:
        yield session


def test_get_or_create_institution_and_account(session: Session):
    # Test neither exists
    acc = get_or_create_institution_and_account(session, "Inst1", "Acc1")
    assert acc.name == "Acc1"
    assert acc.institution.name == "Inst1"

    # Test institution exists, account doesn't
    acc2 = get_or_create_institution_and_account(session, "Inst1", "Acc2")
    assert acc2.name == "Acc2"
    assert acc2.institution.name == "Inst1"
    assert acc.institution.id == acc2.institution.id

    # Test both exist
    acc3 = get_or_create_institution_and_account(session, "Inst1", "Acc1")
    assert acc3.id == acc.id


def test_find_or_create_position(session: Session):
    op_info_cash = {"currency": "USD"}

    # 1. Cash, does not exist
    pos1, created1 = find_or_create_position(session, 1, op_info_cash, is_cash_op=True)
    assert created1 is True
    assert pos1.asset_type == AssetType.CASH
    assert pos1.currency == "USD"

    # 2. Cash, exists
    pos2, created2 = find_or_create_position(session, 1, op_info_cash, is_cash_op=True)
    assert created2 is False
    assert pos2.id == pos1.id

    # 3. Non-cash, does not exist (Stock)
    op_info_stock = {
        "isin": "US123",
        "ticker": "AAPL",
        "name": "Apple Inc",
        "currency": "USD",
    }
    pos3, created3 = find_or_create_position(session, 1, op_info_stock, is_cash_op=False)
    assert created3 is True
    assert pos3.asset_type == AssetType.STOCK

    # 4. Non-cash, does not exist (ETF)
    op_info_etf = {
        "isin": "IE123",
        "ticker": "VWCE",
        "name": "Vanguard FTSE All-World",
        "currency": "EUR",
    }
    pos4, created4 = find_or_create_position(session, 1, op_info_etf, is_cash_op=False)
    assert created4 is True
    assert pos4.asset_type == AssetType.ETF

    # 5. Non-cash, exists by ISIN
    pos5, created5 = find_or_create_position(session, 1, op_info_stock, is_cash_op=False)
    assert created5 is False
    assert pos5.id == pos3.id

    # 6. Non-cash, exists by Ticker
    op_info_ticker = {
        "isin": "",
        "ticker": "AAPL",
        "name": "Apple Inc",
        "currency": "USD",
    }
    pos6, created6 = find_or_create_position(session, 1, op_info_ticker, is_cash_op=False)
    assert created6 is False
    assert pos6.id == pos3.id

    # 7. Non-cash, exists by Name
    op_info_name = {
        "isin": "",
        "ticker": "",
        "name": "Apple Inc",
        "currency": "USD",
    }
    pos7, created7 = find_or_create_position(session, 1, op_info_name, is_cash_op=False)
    assert created7 is False
    assert pos7.id == pos3.id


def test_check_duplicate_operation(session: Session):
    # Needs a real operation to test
    op = TradeOperation(
        position_id=1,
        financial_account_id=1,
        operation_type="trade",
        executed_at=datetime(2026, 1, 1, tzinfo=UTC),
        total_amount=Decimal(100),
        quantity=Decimal(10),
        unit_price=Decimal(10),
        currency="USD",
        transaction_id="tx_123",
        trade_side=TradeSide.BUY,
        order_type=OrderType.MARKET,
        order_status=OrderStatus.FILLED,
    )
    session.add(op)
    session.commit()

    # Match by transaction_id
    op_info1 = {"transaction_id": "tx_123"}
    assert check_duplicate_operation(session, 1, op_info1) is True

    # No match by transaction_id
    op_info2 = {"transaction_id": "tx_999"}
    assert check_duplicate_operation(session, 1, op_info2) is False

    # Match by attributes (with quantity)
    op_info3 = {
        "transaction_id": "",
        "op_type": "trade",
        "executed_at": datetime(2026, 1, 1, tzinfo=UTC),
        "total_amount": Decimal(100),
        "quantity": Decimal(10),
    }
    assert check_duplicate_operation(session, 1, op_info3) is True

    # Match by attributes (without quantity - None)
    op2 = TradeOperation(
        position_id=1,
        financial_account_id=1,
        operation_type="trade",
        executed_at=datetime(2026, 1, 2, tzinfo=UTC),
        total_amount=Decimal(200),
        quantity=None,
        unit_price=None,
        currency="USD",
        transaction_id="",
        trade_side=TradeSide.BUY,
        order_type=OrderType.MARKET,
        order_status=OrderStatus.FILLED,
    )
    session.add(op2)
    session.commit()

    op_info4 = {
        "transaction_id": "",
        "op_type": "trade",
        "executed_at": datetime(2026, 1, 2, tzinfo=UTC),
        "total_amount": Decimal(200),
        "quantity": None,
    }
    assert check_duplicate_operation(session, 1, op_info4) is True


def test_get_or_create_cash_position(session: Session):
    # 1. Does not exist
    pos1, created1 = get_or_create_cash_position(session, 1, "USD")
    assert created1 is True
    assert pos1.currency == "USD"

    # 2. Exists
    pos2, created2 = get_or_create_cash_position(session, 1, "USD")
    assert created2 is False
    assert pos2.id == pos1.id
