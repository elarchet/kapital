"""Persistence helpers for the import pipeline.

Translate parsed canonical rows into ``RawTransaction`` records and cache
portfolio positions in-memory to avoid N+1 queries during bulk ingestion.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlmodel import Session, select

from src.models import (
    AssetType,
    FinancialAccount,
    Institution,
    Position,
    RawTransaction,
)
from src.models.operation_enums import (
    ExpenseCategory,
    InterestType,
    OrderStatus,
    OrderType,
    PaymentMethod,
    RevenueCategory,
    TradeSide,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

# Maps op_info keys to the enum class used to coerce their raw string values.
_ENUM_FIELDS: dict[str, type] = {
    "trade_side": TradeSide,
    "order_type": OrderType,
    "order_status": OrderStatus,
    "interest_type": InterestType,
    "expense_category": ExpenseCategory,
    "revenue_category": RevenueCategory,
    "payment_method": PaymentMethod,
}

# op_info keys copied verbatim onto the RawTransaction.
_SCALAR_FIELDS = (
    "quantity",
    "unit_price",
    "price_currency",
    "total_amount",
    "currency",
    "executed_at",
    "notes",
    "exchange_rate",
    "source_currency",
    "target_currency",
    "ticker",
    "isin",
    "name",
    "limit_price",
    "stop_price",
    "execution_price",
    "order_placed_at",
    "filled_at",
    "dividend_per_share",
    "fee_category",
    "tax_category",
    "source_reference",
    "destination_reference",
    "split_ratio",
    "pre_split_quantity",
    "merchant_name",
    "merchant_category",
)

_ETF_HINTS = ("etf", "ishares", "vanguard", "xtrackers")


def get_or_create_institution_and_account(
    db: Session,
    institution_name: str,
    account_name: str,
    *,
    country: str | None = None,
) -> FinancialAccount:
    """Resolve (or create) the institution and its default financial account."""
    institution = db.exec(select(Institution).where(Institution.name == institution_name)).first()
    if not institution:
        institution = Institution(name=institution_name, country=country)
        db.add(institution)
        db.commit()
        db.refresh(institution)

    if institution.id is None:
        raise ValueError("Institution ID not resolved.")

    account = db.exec(
        select(FinancialAccount).where(
            FinancialAccount.name == account_name,
            FinancialAccount.institution_id == institution.id,
        ),
    ).first()
    if not account:
        account = FinancialAccount(name=account_name, currency="EUR", institution_id=institution.id)
        db.add(account)
        db.commit()
        db.refresh(account)

    if account.id is None:
        raise ValueError("Financial account ID not resolved.")

    return account


def load_existing_dedup_keys(db: Session, financial_account_id: int) -> set[str]:
    """Return every dedup_key already stored for the given financial account."""
    rows = db.exec(
        select(RawTransaction.dedup_key).where(
            RawTransaction.financial_account_id == financial_account_id,
        ),
    ).all()
    return set(rows)


def build_raw_transaction(
    op_info: Mapping[str, Any],
    *,
    dedup_key: str,
    is_auto_id: bool,
    native_transaction_id: str | None,
    financial_account_id: int,
    raw_payload: Mapping[str, Any] | None = None,
) -> RawTransaction:
    """Construct a RawTransaction from a parsed canonical row."""
    total_amount = op_info.get("total_amount")
    txn = RawTransaction(
        operation_type=op_info["op_type"],
        dedup_key=dedup_key,
        is_auto_id=is_auto_id,
        native_transaction_id=native_transaction_id,
        financial_account_id=financial_account_id,
        total_amount=total_amount if total_amount is not None else Decimal(0),
        raw_payload=json.dumps(raw_payload, default=str) if raw_payload else None,
    )

    for key in _SCALAR_FIELDS:
        if op_info.get(key) is not None:
            setattr(txn, key, op_info[key])

    for key, enum_cls in _ENUM_FIELDS.items():
        raw_val = op_info.get(key)
        if raw_val is None:
            continue
        try:
            setattr(txn, key, raw_val if isinstance(raw_val, enum_cls) else enum_cls(raw_val))
        except ValueError:
            continue

    if txn.currency is None:
        txn.currency = "EUR"
    return txn


class PositionCache:
    """In-memory cache of a portfolio's positions for bulk ingestion."""

    def __init__(self, db: Session, portfolio_id: int) -> None:
        self._db = db
        self._portfolio_id = portfolio_id
        positions = db.exec(
            select(Position).where(Position.portfolio_id == portfolio_id, Position.is_active),
        ).all()
        self._by_isin = {p.isin: p for p in positions if p.isin}
        self._by_ticker = {p.ticker: p for p in positions if p.ticker}
        self._by_name = {p.name: p for p in positions if p.name}
        self._cash = {p.currency: p for p in positions if p.asset_type == AssetType.CASH}
        self.created = 0

    def _register(self, position: Position) -> None:
        if position.isin:
            self._by_isin[position.isin] = position
        if position.ticker:
            self._by_ticker[position.ticker] = position
        if position.name:
            self._by_name[position.name] = position

    def get_or_create_asset(self, op_info: Mapping[str, Any]) -> Position:
        """Find or create a non-cash asset position for the parsed row."""
        position = None
        if op_info.get("isin"):
            position = self._by_isin.get(op_info["isin"])
        elif op_info.get("ticker"):
            position = self._by_ticker.get(op_info["ticker"])
        else:
            position = self._by_name.get(op_info.get("name"))

        if position:
            return position

        lower_name = (op_info.get("name") or "").lower()
        asset_type = AssetType.ETF if any(h in lower_name for h in _ETF_HINTS) else AssetType.STOCK
        position = Position(
            portfolio_id=self._portfolio_id,
            asset_type=asset_type,
            ticker=op_info.get("ticker"),
            name=op_info.get("name"),
            isin=op_info.get("isin"),
            quantity=Decimal("0.0"),
            currency=op_info.get("currency") or "EUR",
        )
        self._db.add(position)
        self._register(position)
        self.created += 1
        return position

    def get_or_create_cash(self, currency: str) -> Position:
        """Find or create the cash position for a currency."""
        position = self._cash.get(currency)
        if position:
            return position

        position = Position(
            portfolio_id=self._portfolio_id,
            asset_type=AssetType.CASH,
            name=f"Cash ({currency})",
            quantity=Decimal("0.0"),
            currency=currency,
        )
        self._db.add(position)
        self._cash[currency] = position
        self.created += 1
        return position
