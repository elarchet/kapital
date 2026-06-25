from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from src.auth import get_current_user
from src.models.user import User
from src.services.financial_info import (
    FinancialInfoService,
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


@router.get(
    "/profile/{ticker}",
    response_model=TickerProfile,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Failed to fetch profile information."},
    },
)
async def get_profile(
    ticker: Annotated[str, Path(description="The ticker symbol to fetch (e.g. AAPL)")],
    current_user: Annotated[User, Depends(get_current_user)],  # noqa: ARG001
    service: Annotated[FinancialInfoService, Depends(get_financial_info_service)],
) -> TickerProfile:
    """Fetch company metadata profile for a ticker symbol."""
    try:
        return await service.get_profile(ticker)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch profile: {e}",
        ) from e


@router.get(
    "/quote/{ticker}",
    response_model=TickerQuote,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Failed to fetch stock quote."},
    },
)
async def get_quote(
    ticker: Annotated[str, Path(description="The ticker symbol to fetch (e.g. AAPL)")],
    current_user: Annotated[User, Depends(get_current_user)],  # noqa: ARG001
    service: Annotated[FinancialInfoService, Depends(get_financial_info_service)],
) -> TickerQuote:
    """Fetch real-time ticker quote."""
    try:
        return await service.get_quote(ticker)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch quote: {e}",
        ) from e


@router.get(
    "/history/{ticker}",
    response_model=list[HistoricalPrice],
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Failed to fetch historical prices."},
    },
)
async def get_history(
    ticker: Annotated[str, Path(description="The ticker symbol to fetch (e.g. AAPL)")],
    current_user: Annotated[User, Depends(get_current_user)],  # noqa: ARG001
    service: Annotated[FinancialInfoService, Depends(get_financial_info_service)],
    period: Annotated[str, Query(description="Historical period (e.g. 1mo, 1y)")] = "1mo",
    interval: Annotated[str, Query(description="Data points interval (e.g. 1d, 1wk)")] = "1d",
) -> list[HistoricalPrice]:
    """Fetch historical price points for chart visualization."""
    try:
        return await service.get_history(ticker, period=period, interval=interval)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch history: {e}",
        ) from e


@router.get(
    "/financials/{ticker}",
    response_model=FinancialsReport,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Failed to fetch financials statements."},
    },
)
async def get_financials(
    ticker: Annotated[str, Path(description="The ticker symbol to fetch (e.g. AAPL)")],
    current_user: Annotated[User, Depends(get_current_user)],  # noqa: ARG001
    service: Annotated[FinancialInfoService, Depends(get_financial_info_service)],
) -> FinancialsReport:
    """Fetch fundamental financial statements (income statement, balance sheet, cashflow)."""
    try:
        return await service.get_financials(ticker)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch financials: {e}",
        ) from e
