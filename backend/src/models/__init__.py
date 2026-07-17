"""Kapital domain models.

Import everything from here for convenience::

    from src.models import User, Portfolio, Position, RawTransaction, Allocation, ...
"""

from __future__ import annotations

from src.models.allocation import Allocation, AllocationMethod
from src.models.base import SABase, SoftDeleteMixin, TimestampMixin
from src.models.fee import Fee, FeeType
from src.models.financial_account import FinancialAccount
from src.models.import_file_schema import ImportFileSchema
from src.models.imported_file import ImportedFile
from src.models.institution import Institution
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
from src.models.raw_transaction import RawTransaction
from src.models.user import User

__all__ = [
    "Allocation",
    "AllocationMethod",
    "AssetType",
    "ExpenseCategory",
    "Fee",
    "FeeType",
    "FinancialAccount",
    "ImportFileSchema",
    "ImportedFile",
    "Institution",
    "InterestType",
    "OrderStatus",
    "OrderType",
    "PaymentMethod",
    "Portfolio",
    "Position",
    "RawTransaction",
    "RevenueCategory",
    "SABase",
    "SoftDeleteMixin",
    "TimestampMixin",
    "TradeSide",
    "User",
]
