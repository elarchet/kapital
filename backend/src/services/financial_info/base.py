from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import FinancialsReport, HistoricalPrice, TickerProfile, TickerQuote


class BaseFinancialProvider(ABC):
    """Abstract base class representing a market data provider."""

    @abstractmethod
    async def get_profile(self, ticker: str) -> TickerProfile:
        """Fetch metadata profile for a ticker."""

    @abstractmethod
    async def get_quote(self, ticker: str) -> TickerQuote:
        """Fetch real-time quote for a ticker."""

    @abstractmethod
    async def get_history(
        self,
        ticker: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> list[HistoricalPrice]:
        """Fetch historical price points for a ticker."""

    @abstractmethod
    async def get_financials(self, ticker: str) -> FinancialsReport:
        """Fetch fundamental financial statements (income statement, balance sheet, cash flow)."""
