"""Kapital domain models.

Import everything from here for convenience::

    from src.models import User, Portfolio, Position, BuyOperation, ...
"""

from __future__ import annotations

from src.models.base import SABase, SoftDeleteMixin, TimestampMixin
from src.models.fee import Fee, FeeType
from src.models.financial_account import FinancialAccount
from src.models.import_file_schema import ImportFileSchema
from src.models.institution import Institution
from src.models.operation import (
    BuyOperation,
    DividendOperation,
    ExpenseOperation,
    FeeOperation,
    FxRateChangeOperation,
    InterestOperation,
    InterestType,
    LimitBuyOperation,
    LimitSellOperation,
    Operation,
    RevenueOperation,
    SellOperation,
    StockSplitOperation,
    TaxOperation,
    TransferInOperation,
    TransferOutOperation,
)
from src.models.portfolio import Portfolio
from src.models.position import AssetType, Position
from src.models.user import User

__all__ = [
    "AssetType",
    "BuyOperation",
    "DividendOperation",
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
    "LimitBuyOperation",
    "LimitSellOperation",
    "Operation",
    "Portfolio",
    "Position",
    "RevenueOperation",
    "SABase",
    "SellOperation",
    "SoftDeleteMixin",
    "StockSplitOperation",
    "TaxOperation",
    "TimestampMixin",
    "TransferInOperation",
    "TransferOutOperation",
    "User",
]
