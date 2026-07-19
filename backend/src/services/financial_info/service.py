from __future__ import annotations

import asyncio
import contextlib
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import yfinance as yf

from .models import (
    DailyCloseSeries,
    FinancialsReport,
    FinancialStatementRow,
    HistoricalPrice,
    TickerProfile,
    TickerQuote,
)

if TYPE_CHECKING:
    from datetime import date

    import pandas as pd


def _get_fast_info_attr(fi: object, keys: list[str]) -> float | int | str | None:
    """Helper to safely fetch fast_info attributes across different yfinance versions."""
    for k in keys:
        with contextlib.suppress(Exception):
            val = fi.get(k) if hasattr(fi, "get") else getattr(fi, k, None)
            if val is not None:
                return val
        with contextlib.suppress(Exception):
            val = fi[k]
            if val is not None:
                return val
    return None


class FinancialInfoService:
    """Financial info service using yfinance directly."""

    async def get_profile(self, ticker: str) -> TickerProfile:
        """Fetch metadata profile for a ticker."""

        def _fetch() -> dict[str, Any]:
            t = yf.Ticker(ticker)
            return t.info

        info = await asyncio.to_thread(_fetch)

        # Read fields defensively
        symbol = info.get("symbol") or ticker
        long_name = info.get("longName")
        short_name = info.get("shortName")
        if not long_name and not short_name:
            raise ValueError(f"No company name found for ticker '{ticker}'.")
        name = long_name or short_name

        market_cap_val = info.get("marketCap")
        market_cap = None
        if market_cap_val is not None:
            with contextlib.suppress(ArithmeticError, ValueError, TypeError):
                market_cap = Decimal(str(market_cap_val))

        return TickerProfile(
            symbol=symbol,
            name=name,
            sector=info.get("sector"),
            industry=info.get("industry"),
            summary=info.get("longBusinessSummary"),
            website=info.get("website"),
            country=info.get("country"),
            exchange=info.get("exchange"),
            currency=info.get("financialCurrency") or info.get("currency"),
            market_cap=market_cap,
        )

    async def get_quote(self, ticker: str) -> TickerQuote:
        """Fetch real-time quote for a ticker."""

        def _fetch() -> dict[str, Any]:
            t = yf.Ticker(ticker)
            fast_data = {}
            with contextlib.suppress(Exception):
                fi = t.fast_info
                fast_data = {
                    "price": _get_fast_info_attr(fi, ["lastPrice", "last_price"]),
                    "open": _get_fast_info_attr(fi, ["open"]),
                    "high": _get_fast_info_attr(fi, ["dayHigh", "day_high"]),
                    "low": _get_fast_info_attr(fi, ["dayLow", "day_low"]),
                    "previous_close": _get_fast_info_attr(fi, ["previousClose", "previous_close"]),
                    "volume": _get_fast_info_attr(fi, ["volume"]),
                    "currency": _get_fast_info_attr(fi, ["currency"]),
                }

            # Also fetch info for details (like bid/ask)
            inf = {}
            with contextlib.suppress(Exception):
                inf = t.info

            return {"fast": fast_data, "info": inf}

        data = await asyncio.to_thread(_fetch)
        fast = data["fast"]
        info = data["info"]

        # Consolidate values
        price_val = (
            fast.get("price") or info.get("currentPrice") or info.get("regularMarketPrice") or info.get("lastPrice")
        )
        if price_val is None:
            raise ValueError(f"Could not retrieve quote price for ticker {ticker}")

        price = Decimal(str(price_val))

        prev_close_val = (
            fast.get("previous_close") or info.get("regularMarketPreviousClose") or info.get("previousClose")
        )
        prev_close = Decimal(str(prev_close_val)) if prev_close_val is not None else None

        change = None
        change_percent = None
        if prev_close is not None:
            change = price - prev_close
            if prev_close != 0:
                change_percent = (change / prev_close) * Decimal(100)

        open_val = fast.get("open") or info.get("regularMarketOpen") or info.get("open")
        high_val = fast.get("high") or info.get("regularMarketDayHigh") or info.get("dayHigh")
        low_val = fast.get("low") or info.get("regularMarketDayLow") or info.get("dayLow")
        volume_val = fast.get("volume") or info.get("regularMarketVolume") or info.get("volume")

        bid_val = info.get("bid")
        ask_val = info.get("ask")

        return TickerQuote(
            symbol=ticker,
            price=price,
            change=change,
            change_percent=change_percent,
            open=Decimal(str(open_val)) if open_val is not None else None,
            high=Decimal(str(high_val)) if high_val is not None else None,
            low=Decimal(str(low_val)) if low_val is not None else None,
            previous_close=prev_close,
            volume=int(volume_val) if volume_val is not None else None,
            bid=Decimal(str(bid_val)) if bid_val is not None else None,
            ask=Decimal(str(ask_val)) if ask_val is not None else None,
        )

    async def get_history(
        self,
        ticker: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> list[HistoricalPrice]:
        """Fetch historical price points for a ticker."""

        def _fetch() -> pd.DataFrame:
            t = yf.Ticker(ticker)
            return t.history(period=period, interval=interval)

        df = await asyncio.to_thread(_fetch)

        prices = []
        if df is None or df.empty:
            return prices

        for index, row in df.iterrows():
            # index is typically timestamp
            date = index.to_pydatetime() if hasattr(index, "to_pydatetime") else index
            prices.append(
                HistoricalPrice(
                    date=date,
                    open=Decimal(str(row["Open"])),
                    high=Decimal(str(row["High"])),
                    low=Decimal(str(row["Low"])),
                    close=Decimal(str(row["Close"])),
                    volume=int(row["Volume"]),
                ),
            )
        return prices

    async def get_daily_closes(
        self,
        ticker: str,
        start: date,
        end: date | None = None,
    ) -> DailyCloseSeries:
        """Fetch daily closing prices for an explicit date range.

        ``end`` is exclusive per yfinance semantics; ``None`` means "through
        today". The quote currency is fetched in the same thread hop so
        callers persisting closes don't need a second network round-trip.
        """

        def _fetch() -> tuple[pd.DataFrame, str | None]:
            t = yf.Ticker(ticker)
            df = t.history(start=start, end=end, interval="1d")
            currency = None
            with contextlib.suppress(Exception):
                currency = _get_fast_info_attr(t.fast_info, ["currency"])
            return df, currency

        df, currency = await asyncio.to_thread(_fetch)

        prices: list[HistoricalPrice] = []
        if df is not None and not df.empty:
            for index, row in df.iterrows():
                point_date = index.to_pydatetime() if hasattr(index, "to_pydatetime") else index
                prices.append(
                    HistoricalPrice(
                        date=point_date,
                        open=Decimal(str(row["Open"])),
                        high=Decimal(str(row["High"])),
                        low=Decimal(str(row["Low"])),
                        close=Decimal(str(row["Close"])),
                        volume=int(row["Volume"]),
                    ),
                )
        return DailyCloseSeries(
            symbol=ticker,
            currency=str(currency) if currency is not None else None,
            prices=prices,
        )

    async def get_financials(self, ticker: str) -> FinancialsReport:
        """Fetch fundamental financial statements."""

        def _fetch() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
            t = yf.Ticker(ticker)
            return t.income_stmt, t.balance_sheet, t.cashflow

        inc, bal, cf = await asyncio.to_thread(_fetch)

        def _parse_df(df: pd.DataFrame) -> list[FinancialStatementRow]:
            if df is None or df.empty:
                return []
            rows = []
            for metric, row in df.iterrows():
                metric_str = str(metric)
                for date_col, val in row.items():
                    date_str = str(date_col.date()) if hasattr(date_col, "date") else str(date_col)
                    decimal_val = None
                    if val is not None and str(val) != "nan" and str(val) != "None":
                        with contextlib.suppress(ArithmeticError, ValueError, TypeError):
                            decimal_val = Decimal(str(val))
                    rows.append(
                        FinancialStatementRow(
                            date=date_str,
                            metric=metric_str,
                            value=decimal_val,
                        ),
                    )
            return rows

        return FinancialsReport(
            income_statement=_parse_df(inc),
            balance_sheet=_parse_df(bal),
            cashflow_statement=_parse_df(cf),
        )
