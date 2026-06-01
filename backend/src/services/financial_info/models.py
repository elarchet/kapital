from __future__ import annotations

from datetime import datetime  # noqa: TC003
from decimal import Decimal  # noqa: TC003
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class FinancialProviderName(StrEnum):
    """Available financial data provider choices."""

    YFINANCE = "yfinance"
    DUMMY = "dummy"


class TickerProfile(BaseModel):
    """Company profile and metadata."""

    model_config = ConfigDict(strict=True)

    symbol: str
    name: str
    sector: str | None = None
    industry: str | None = None
    summary: str | None = None
    website: str | None = None
    country: str | None = None
    exchange: str | None = None
    currency: str | None = None
    market_cap: Decimal | None = None


class TickerQuote(BaseModel):
    """Real-time / current market quote."""

    model_config = ConfigDict(strict=True)

    symbol: str
    price: Decimal
    change: Decimal | None = None
    change_percent: Decimal | None = None
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    previous_close: Decimal | None = None
    volume: int | None = None
    bid: Decimal | None = None
    ask: Decimal | None = None


class HistoricalPrice(BaseModel):
    """Historical stock price point."""

    model_config = ConfigDict(strict=True)

    date: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


class FinancialStatementRow(BaseModel):
    """Single row of a financial statement for a specific date."""

    model_config = ConfigDict(strict=True)

    date: str
    metric: str
    value: Decimal | None = None


class FinancialsReport(BaseModel):
    """Fundamental financial statements report."""

    model_config = ConfigDict(strict=True)

    income_statement: list[FinancialStatementRow]
    balance_sheet: list[FinancialStatementRow]
    cashflow_statement: list[FinancialStatementRow]
