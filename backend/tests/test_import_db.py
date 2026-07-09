from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from src.models import AssetType, RawTransaction, TradeSide
from src.services.import_db import (
    PositionCache,
    build_raw_transaction,
    get_or_create_institution_and_account,
    load_existing_dedup_keys,
)
from tests.factories import FinancialAccountFactory, PortfolioFactory

if TYPE_CHECKING:
    from sqlmodel import Session


def test_get_or_create_institution_and_account(session: Session):
    # Test neither exists
    acc = get_or_create_institution_and_account(session, "Inst1", "Acc1", country="US")
    assert acc.name == "Acc1"
    assert acc.institution.name == "Inst1"
    assert acc.institution.country == "US"

    # Test institution exists, account doesn't
    acc2 = get_or_create_institution_and_account(session, "Inst1", "Acc2")
    assert acc2.name == "Acc2"
    assert acc2.institution.name == "Inst1"
    assert acc.institution.id == acc2.institution.id

    # Test both exist
    acc3 = get_or_create_institution_and_account(session, "Inst1", "Acc1")
    assert acc3.id == acc.id


def test_position_cache_get_or_create_asset(session: Session):
    portfolio = PortfolioFactory()
    session.commit()
    cache = PositionCache(session, portfolio.id)

    # 1. Stock, does not exist -> created
    stock = cache.get_or_create_asset(
        {"isin": "US123", "ticker": "AAPL", "name": "Apple Inc", "currency": "USD"},
    )
    session.flush()
    assert stock.asset_type == AssetType.STOCK
    assert cache.created == 1

    # 2. ETF detection via name hint
    etf = cache.get_or_create_asset(
        {"isin": "IE123", "ticker": "VWCE", "name": "Vanguard FTSE All-World", "currency": "EUR"},
    )
    session.flush()
    assert etf.asset_type == AssetType.ETF
    assert cache.created == 2

    # 3. Exists by ISIN
    by_isin = cache.get_or_create_asset(
        {"isin": "US123", "ticker": "AAPL", "name": "Apple Inc", "currency": "USD"},
    )
    assert by_isin is stock
    assert cache.created == 2

    # 4. Exists by ticker (no ISIN)
    by_ticker = cache.get_or_create_asset(
        {"isin": "", "ticker": "AAPL", "name": "Apple Inc", "currency": "USD"},
    )
    assert by_ticker is stock

    # 5. Exists by name (no ISIN / ticker)
    by_name = cache.get_or_create_asset(
        {"isin": "", "ticker": "", "name": "Apple Inc", "currency": "USD"},
    )
    assert by_name is stock
    assert cache.created == 2


def test_position_cache_get_or_create_cash(session: Session):
    portfolio = PortfolioFactory()
    session.commit()
    cache = PositionCache(session, portfolio.id)

    # 1. Does not exist -> created
    cash = cache.get_or_create_cash("USD")
    session.flush()
    assert cash.asset_type == AssetType.CASH
    assert cash.currency == "USD"
    assert cache.created == 1

    # 2. Exists -> returns the same instance, no new creation
    cash_again = cache.get_or_create_cash("USD")
    assert cash_again is cash
    assert cache.created == 1


def test_build_raw_transaction_maps_fields_and_enums():
    op_info = {
        "op_type": "trade",
        "quantity": Decimal(10),
        "unit_price": Decimal(100),
        "total_amount": Decimal(1000),
        "currency": "USD",
        "executed_at": datetime(2026, 1, 1, tzinfo=UTC),
        "ticker": "AAPL",
        "isin": "US123",
        "name": "Apple Inc",
        "trade_side": "buy",
        "order_type": "market",
        "order_status": "filled",
    }
    txn = build_raw_transaction(
        op_info,
        dedup_key="TX-1",
        is_auto_id=False,
        native_transaction_id="TX-1",
        financial_account_id=1,
        raw_payload={"Action": "Market buy"},
    )

    assert txn.operation_type == "trade"
    assert txn.dedup_key == "TX-1"
    assert txn.native_transaction_id == "TX-1"
    assert txn.is_auto_id is False
    assert txn.total_amount == Decimal(1000)
    assert txn.quantity == Decimal(10)
    assert txn.ticker == "AAPL"
    assert txn.trade_side == TradeSide.BUY  # coerced from the raw string
    assert txn.raw_payload is not None  # original row serialized to JSON


def test_build_raw_transaction_defaults():
    txn = build_raw_transaction(
        {"op_type": "dividend"},
        dedup_key="auto-abc",
        is_auto_id=True,
        native_transaction_id=None,
        financial_account_id=1,
    )
    assert txn.operation_type == "dividend"
    assert txn.is_auto_id is True
    assert txn.native_transaction_id is None
    assert txn.total_amount == Decimal(0)  # defaults when total_amount is absent
    assert txn.currency == "EUR"  # default currency
    assert txn.raw_payload is None


def test_load_existing_dedup_keys(session: Session):
    account = FinancialAccountFactory()
    session.commit()

    # No transactions yet.
    assert load_existing_dedup_keys(session, account.id) == set()

    for key in ("TX-1", "TX-2", "auto-abc"):
        session.add(
            RawTransaction(
                operation_type="trade",
                dedup_key=key,
                financial_account_id=account.id,
                total_amount=Decimal(100),
                currency="USD",
                executed_at=datetime(2026, 1, 1, tzinfo=UTC),
            ),
        )
    session.commit()

    assert load_existing_dedup_keys(session, account.id) == {"TX-1", "TX-2", "auto-abc"}

    # Keys are scoped to the financial account.
    other = FinancialAccountFactory()
    session.commit()
    assert load_existing_dedup_keys(session, other.id) == set()
