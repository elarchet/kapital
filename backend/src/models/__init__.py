"""Kapital domain models.

Import everything from here for convenience::

    from src.models import User, Portfolio, Position, TradeOperation, ...
"""

from __future__ import annotations

from src.models.base import SABase, SoftDeleteMixin, TimestampMixin
from src.models.fee import Fee, FeeType
from src.models.financial_account import FinancialAccount
from src.models.import_file_schema import ImportFileSchema
from src.models.institution import Institution
from src.models.operation import (
    DividendOperation,
    ExpenseCategory,
    ExpenseOperation,
    FeeOperation,
    FxRateChangeOperation,
    InterestOperation,
    InterestType,
    Operation,
    OrderStatus,
    OrderType,
    PaymentMethod,
    RevenueCategory,
    RevenueOperation,
    StockSplitOperation,
    TaxOperation,
    TradeOperation,
    TradeSide,
    TransferInOperation,
    TransferOutOperation,
)
from src.models.portfolio import Portfolio
from src.models.position import AssetType, Position
from src.models.user import User

__all__ = [
    "AssetType",
    "DividendOperation",
    "ExpenseCategory",
    "ExpenseOperation",
    "Fee",
    "FeeOperation",
    "FeeType",
    "FinancialAccount",
    "FxRateChangeOperation",
    "ImportFileSchema",
    "Institution",
    "InterestOperation",
    "InterestType",
    "Operation",
    "OrderStatus",
    "OrderType",
    "PaymentMethod",
    "Portfolio",
    "Position",
    "RevenueCategory",
    "RevenueOperation",
    "SABase",
    "SoftDeleteMixin",
    "StockSplitOperation",
    "TaxOperation",
    "TimestampMixin",
    "TradeOperation",
    "TradeSide",
    "TransferInOperation",
    "TransferOutOperation",
    "User",
]
