from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from src.auth import get_current_user
from src.models.user import User
from src.services.financial_info import (
    FinancialInfoService,
    FinancialProviderName,
    FinancialsReport,
    HistoricalPrice,
    TickerProfile,
    TickerQuote,
)

router = APIRouter(prefix="/financial-info", tags=["financial-info"])

_financial_info_service = FinancialInfoService()


def get_financial_info_service() -> FinancialInfoService:
    """Dependency provider for FinancialInfoService."""
    return _financial_info_service


@router.get("/profile/{ticker}", response_model=TickerProfile)
async def get_profile(
    ticker: str,
    current_user: Annotated[User, Depends(get_current_user)],  # noqa: ARG001
    service: Annotated[FinancialInfoService, Depends(get_financial_info_service)],
    provider: FinancialProviderName = FinancialProviderName.YFINANCE,
) -> TickerProfile:
    """Fetch company metadata profile for a ticker symbol."""
    try:
        return await service.get_profile(ticker, provider=provider)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch profile: {e}",
        ) from e


@router.get("/quote/{ticker}", response_model=TickerQuote)
async def get_quote(
    ticker: str,
    current_user: Annotated[User, Depends(get_current_user)],  # noqa: ARG001
    service: Annotated[FinancialInfoService, Depends(get_financial_info_service)],
    provider: FinancialProviderName = FinancialProviderName.YFINANCE,
) -> TickerQuote:
    """Fetch real-time ticker quote."""
    try:
        return await service.get_quote(ticker, provider=provider)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch quote: {e}",
        ) from e


@router.get("/history/{ticker}", response_model=list[HistoricalPrice])
async def get_history(
    ticker: str,
    current_user: Annotated[User, Depends(get_current_user)],  # noqa: ARG001
    service: Annotated[FinancialInfoService, Depends(get_financial_info_service)],
    period: str = "1mo",
    interval: str = "1d",
    provider: FinancialProviderName = FinancialProviderName.YFINANCE,
) -> list[HistoricalPrice]:
    """Fetch historical price points for chart visualization."""
    try:
        return await service.get_history(ticker, period=period, interval=interval, provider=provider)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch history: {e}",
        ) from e


@router.get("/financials/{ticker}", response_model=FinancialsReport)
async def get_financials(
    ticker: str,
    current_user: Annotated[User, Depends(get_current_user)],  # noqa: ARG001
    service: Annotated[FinancialInfoService, Depends(get_financial_info_service)],
    provider: FinancialProviderName = FinancialProviderName.YFINANCE,
) -> FinancialsReport:
    """Fetch fundamental financial statements (income statement, balance sheet, cashflow)."""
    try:
        return await service.get_financials(ticker, provider=provider)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch financials: {e}",
        ) from e
