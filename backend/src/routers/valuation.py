"""Portfolio valuation router — value over time, positions, allocation rollup."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlmodel import Session

from src.auth import get_current_user
from src.database import get_session
from src.models.user import User
from src.schemas.valuation import PortfolioValuation
from src.services.valuation_service import PortfolioNotFoundError, RangeKey, get_portfolio_valuation

router = APIRouter(prefix="/portfolios", tags=["valuation"])


@router.get("/{portfolio_id}/valuation", response_model=PortfolioValuation)
async def read_portfolio_valuation(
    portfolio_id: Annotated[str, Path(description="Portfolio ID, or 'unassigned'")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
    range: Annotated[RangeKey, Query(description="Series time range")] = "1y",  # noqa: A002
) -> PortfolioValuation:
    """Full valuation payload for one portfolio (or the unassigned pseudo-portfolio)."""
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current user lacks an identifier.")

    resolved: int | Literal["unassigned"]
    if portfolio_id == "unassigned":
        resolved = "unassigned"
    else:
        try:
            resolved = int(portfolio_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="portfolio_id must be an integer or 'unassigned'.",
            ) from exc

    try:
        return await get_portfolio_valuation(db, user_id=current_user.id, portfolio_id=resolved, range_key=range)
    except PortfolioNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
