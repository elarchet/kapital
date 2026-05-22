from __future__ import annotations

from sqlmodel import Session, select

from src.crud.base import CRUDBase
from src.models.portfolio import Portfolio
from src.schemas.portfolio import PortfolioCreate, PortfolioUpdate


class CRUDPortfolio(CRUDBase[Portfolio, PortfolioCreate, PortfolioUpdate]):
    """Portfolio CRUD operations, gated by owner User ID."""

    def get_by_owner(self, db: Session, *, id: int, user_id: int) -> Portfolio | None:
        """Fetch a portfolio by ID, validating that it belongs to the user."""
        statement = select(Portfolio).where(
            Portfolio.id == id,
            Portfolio.user_id == user_id,
            Portfolio.is_active == True,  # noqa: E712
        )
        return db.exec(statement).first()

    def get_multi_by_owner(
        self,
        db: Session,
        *,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Portfolio]:
        """Fetch all active portfolios belonging to a specific user."""
        statement = (
            select(Portfolio)
            .where(Portfolio.user_id == user_id, Portfolio.is_active == True)  # noqa: E712
            .offset(skip)
            .limit(limit)
        )
        return list(db.exec(statement).all())

    def create_with_owner(
        self,
        db: Session,
        *,
        obj_in: PortfolioCreate,
        user_id: int,
    ) -> Portfolio:
        """Create a portfolio bound to the authenticated owner."""
        db_obj = Portfolio(
            name=obj_in.name,
            description=obj_in.description,
            user_id=user_id,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


portfolio_crud = CRUDPortfolio(Portfolio)
