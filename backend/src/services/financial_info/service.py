from __future__ import annotations

from typing import TYPE_CHECKING

from .models import FinancialProviderName
from .yfinance_provider import YFinanceProvider

if TYPE_CHECKING:
    from .base import BaseFinancialProvider
    from .models import FinancialsReport, HistoricalPrice, TickerProfile, TickerQuote


class FinancialInfoService:
    """Orchestrates market data providers and handles queries."""

    def __init__(self, default_provider_name: FinancialProviderName | str = FinancialProviderName.YFINANCE) -> None:
        self._providers: dict[str, BaseFinancialProvider] = {}
        self.register_provider(FinancialProviderName.YFINANCE, YFinanceProvider())
        self._default_provider_name = str(default_provider_name)

    def register_provider(self, name: FinancialProviderName | str, provider: BaseFinancialProvider) -> None:
        """Register a new financial provider."""
        self._providers[str(name)] = provider

    def get_provider(self, name: FinancialProviderName | str | None = None) -> BaseFinancialProvider:
        """Retrieve a provider by name, falling back to default."""
        provider_name = str(name) if name is not None else self._default_provider_name
        if provider_name not in self._providers:
            raise ValueError(f"Financial provider '{provider_name}' is not registered.")
        return self._providers[provider_name]

    async def get_profile(self, ticker: str, provider: FinancialProviderName | str | None = None) -> TickerProfile:
        """Fetch ticker metadata profile using the selected/default provider."""
        return await self.get_provider(provider).get_profile(ticker)

    async def get_quote(self, ticker: str, provider: FinancialProviderName | str | None = None) -> TickerQuote:
        """Fetch real-time ticker quote using the selected/default provider."""
        return await self.get_provider(provider).get_quote(ticker)

    async def get_history(
        self,
        ticker: str,
        period: str = "1mo",
        interval: str = "1d",
        provider: FinancialProviderName | str | None = None,
    ) -> list[HistoricalPrice]:
        """Fetch historical price points using the selected/default provider."""
        return await self.get_provider(provider).get_history(ticker, period=period, interval=interval)

    async def get_financials(
        self,
        ticker: str,
        provider: FinancialProviderName | str | None = None,
    ) -> FinancialsReport:
        """Fetch fundamental financials report using the selected/default provider."""
        return await self.get_provider(provider).get_financials(ticker)
