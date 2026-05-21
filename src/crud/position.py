from __future__ import annotations

from sqlmodel import Session, select

from src.crud.base import CRUDBase
from src.models.portfolio import Portfolio
from src.models.position import Position
from src.schemas.position import PositionCreate, PositionUpdate


class CRUDPosition(CRUDBase[Position, PositionCreate, PositionUpdate]):
    """Position CRUD operations, ensuring parent portfolio belongs to user."""

    def get_by_owner(self, db: Session, *, id: int, user_id: int) -> Position | None:
        """Fetch a position by ID, validating that its parent portfolio is owned by the user."""
        statement = (
            select(Position)
            .join(Portfolio)
            .where(
                Position.id == id,
                Portfolio.user_id == user_id,
                Position.is_active == True,  # noqa: E712
            )
        )
        return db.exec(statement).first()

    def get_multi_by_portfolio(
        self,
        db: Session,
        *,
        portfolio_id: int,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Position]:
        """Fetch active positions in a specific portfolio, verifying ownership."""
        statement = (
            select(Position)
            .join(Portfolio)
            .where(
                Position.portfolio_id == portfolio_id,
                Portfolio.user_id == user_id,
                Position.is_active == True,  # noqa: E712
            )
            .offset(skip)
            .limit(limit)
        )
        return list(db.exec(statement).all())


position_crud = CRUDPosition(Position)
