"""Kapital domain models.

Import everything from here for convenience::

    from src.models import User, Portfolio, Position, BuyOperation, ...
"""

from __future__ import annotations

from src.models.base import SABase, SoftDeleteMixin, TimestampMixin
from src.models.financial_account import FinancialAccount
from src.models.institution import Institution
from src.models.operation import (
    BuyOperation,
    DividendOperation,
    FeeOperation,
    FxRateChangeOperation,
    InterestOperation,
    LimitBuyOperation,
    LimitSellOperation,
    Operation,
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
    "FeeOperation",
    "FinancialAccount",
    "FxRateChangeOperation",
    "Institution",
    "InterestOperation",
    "LimitBuyOperation",
    "LimitSellOperation",
    "Operation",
    "Portfolio",
    "Position",
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
