"""Enumerations for Operation models."""

from enum import StrEnum


class TradeSide(StrEnum):
    """Direction of a trade."""

    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    """How the trade order was placed."""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(StrEnum):
    """Lifecycle status of a trade order."""

    PENDING = "pending"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class InterestType(StrEnum):
    """Categorization of interest operations."""

    CASH_INTEREST = "cash_interest"
    CASHBACK = "cashback"
    LENDING_INTEREST = "lending_interest"
    BOND_INTEREST = "bond_interest"
    SAVINGS_INTEREST = "savings_interest"
    MARGIN_INTEREST = "margin_interest"
    STAKING_REWARDS = "staking_rewards"
    PEER_TO_PEER_INTEREST = "peer_to_peer_interest"
    OTHER = "other"


class ExpenseCategory(StrEnum):
    """Categorization of everyday expenses."""

    GROCERIES = "groceries"
    DINING = "dining"
    TRANSPORT = "transport"
    UTILITIES = "utilities"
    ENTERTAINMENT = "entertainment"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    SHOPPING = "shopping"
    TRAVEL = "travel"
    SUBSCRIPTION = "subscription"
    RENT = "rent"
    INSURANCE = "insurance"
    OTHER = "other"


class RevenueCategory(StrEnum):
    """Categorization of everyday revenue."""

    SALARY = "salary"
    FREELANCE = "freelance"
    RENTAL_INCOME = "rental_income"
    REFUND = "refund"
    GIFT = "gift"
    OTHER = "other"


class PaymentMethod(StrEnum):
    """Channel through which a payment was made or received."""

    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    CASH = "cash"
    MOBILE_PAYMENT = "mobile_payment"
    CRYPTO = "crypto"
    OTHER = "other"
