"""Pydantic schemas for portfolio valuation responses."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from src.models.position import AssetType


class PriceStatus(StrEnum):
    """How a position's current price was obtained."""

    OK = "ok"  # fresh persisted close
    STALE = "stale"  # last close older than the freshness window
    COST_FALLBACK = "cost_fallback"  # no price source — valued at cost
    FIXED = "fixed"  # cash: price is 1 by definition


class ValuationPoint(BaseModel):
    """One day of the portfolio value series."""

    model_config = ConfigDict(strict=True)

    date: date
    market_value: Decimal
    net_invested: Decimal


class PositionValuation(BaseModel):
    """Current market figures for one asset row.

    A row usually maps to a single position, but positions sharing the same
    asset identity (ticker / isin / cash currency) are aggregated into one row;
    ``position_ids`` then lists every constituent position.
    """

    model_config = ConfigDict(strict=True)

    position_id: int
    position_ids: list[int]
    name: str | None = None
    ticker: str | None = None
    isin: str | None = None
    asset_type: AssetType
    currency: str
    quantity: Decimal
    price: Decimal | None = None
    price_date: date | None = None
    price_status: PriceStatus
    fx_approximate: bool = False
    market_value: Decimal
    total_invested: Decimal
    gain: Decimal
    gain_pct: Decimal | None = None


class AssetTypeSlice(BaseModel):
    """Current market value share of one asset type."""

    model_config = ConfigDict(strict=True)

    asset_type: AssetType
    market_value: Decimal
    percentage: Decimal


class CurrentTotals(BaseModel):
    """Headline figures for the KPI cards."""

    model_config = ConfigDict(strict=True)

    market_value: Decimal
    net_invested: Decimal
    gain: Decimal
    gain_pct: Decimal | None = None


class PortfolioValuation(BaseModel):
    """Full valuation payload for the portfolio page."""

    model_config = ConfigDict(strict=True)

    portfolio_id: int | str
    as_of: datetime
    currency: str
    currency_mixed: bool = False
    current: CurrentTotals
    series: list[ValuationPoint]
    positions: list[PositionValuation]
    allocation: list[AssetTypeSlice]
