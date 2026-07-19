"""AssetPrice model — persisted daily market closes per ticker symbol.

Prices are global (no user FK): a close for ``AAPL`` on a given date is the
same for every user, so rows are shared. History is backfilled lazily from
yfinance the first time a portfolio valuation needs a symbol, then topped up
incrementally (see ``services.price_service``). Positions without a ticker
never get rows here — valuation falls back to cost for them.
"""

from datetime import date
from decimal import Decimal

from sqlmodel import Field, SQLModel, UniqueConstraint

from src.models.base import TimestampMixin


class AssetPrice(TimestampMixin, SQLModel, table=True):
    """One daily closing price for a ticker symbol."""

    __tablename__ = "asset_price"
    __table_args__ = (UniqueConstraint("symbol", "price_date", name="uq_asset_price_symbol_date"),)

    id: int | None = Field(default=None, primary_key=True)
    symbol: str = Field(nullable=False, max_length=20, index=True)
    price_date: date = Field(nullable=False, index=True)
    close: Decimal = Field(nullable=False, max_digits=20, decimal_places=8)
    # Currency the source quotes this symbol in — may differ from the
    # position's transaction currency (FX handling lives in valuation).
    currency: str = Field(default="EUR", nullable=False, max_length=3)
    source: str = Field(default="yfinance", nullable=False, max_length=20)
