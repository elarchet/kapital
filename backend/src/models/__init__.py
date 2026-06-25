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
    ExpenseOperation,
    FeeOperation,
    FxRateChangeOperation,
    InterestOperation,
    Operation,
    RevenueOperation,
    StockSplitOperation,
    TaxOperation,
    TradeOperation,
    TransferInOperation,
    TransferOutOperation,
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
from src.models.portfolio import Portfolio
from src.models.position import AssetType, Position
from src.models.ui_marketplace import UIComponentOverride, UIComponentVariant
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
    "UIComponentOverride",
    "UIComponentVariant",
    "User",
]
