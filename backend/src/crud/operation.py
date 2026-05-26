from __future__ import annotations

from sqlmodel import Session, select

from src.crud.base import CRUDBase
from src.models.fee import Fee
from src.models.operation import (
    BuyOperation,
    DividendOperation,
    ExpenseOperation,
    FeeOperation,
    FxRateChangeOperation,
    InterestOperation,
    LimitBuyOperation,
    LimitSellOperation,
    Operation,
    RevenueOperation,
    SellOperation,
    StockSplitOperation,
    TaxOperation,
    TransferInOperation,
    TransferOutOperation,
)
from src.models.portfolio import Portfolio
from src.models.position import Position
from src.schemas.operation import OperationCreate, OperationUpdate

# Map string discriminator to actual polymorphic STI model subclass
OPERATION_TYPE_MAP: dict[str, type[Operation]] = {
    "buy": BuyOperation,
    "sell": SellOperation,
    "limit_buy": LimitBuyOperation,
    "limit_sell": LimitSellOperation,
    "dividend": DividendOperation,
    "fee": FeeOperation,
    "tax": TaxOperation,
    "interest": InterestOperation,
    "transfer_in": TransferInOperation,
    "transfer_out": TransferOutOperation,
    "stock_split": StockSplitOperation,
    "fx_rate_change": FxRateChangeOperation,
    "expense": ExpenseOperation,
    "revenue": RevenueOperation,
}


class CRUDOperation(CRUDBase[Operation, OperationCreate, OperationUpdate]):
    """Operation CRUD supporting STI polymorphism and ownership verification."""

    def get_by_owner(self, db: Session, *, id: int, user_id: int) -> Operation | None:
        """Fetch an operation by ID, validating that its parent position is owned by the user."""
        statement = (
            select(Operation)
            .join(Position, Operation.position_id == Position.id)
            .join(Portfolio, Position.portfolio_id == Portfolio.id)
            .where(
                Operation.id == id,
                Portfolio.user_id == user_id,
            )
        )
        # Note: SQLAlchemy's select on SABase (Operation) returns mapped instances,
        # but we use execute().scalars().first() to guarantee clean polymorphic loading.
        return db.execute(statement).scalars().first()

    def get_multi_by_position(
        self,
        db: Session,
        *,
        position_id: int,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Operation]:
        """Fetch operations for a position, validating ownership first."""
        statement = (
            select(Operation)
            .join(Position, Operation.position_id == Position.id)
            .join(Portfolio, Position.portfolio_id == Portfolio.id)
            .where(
                Operation.position_id == position_id,
                Portfolio.user_id == user_id,
            )
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(statement).scalars().all())

    def create(self, db: Session, *, obj_in: OperationCreate) -> Operation:
        """Override create to dynamically instantiate the correct polymorphic STI subclass."""
        op_type = obj_in.operation_type
        model_cls = OPERATION_TYPE_MAP.get(op_type)
        if not model_cls:
            raise ValueError(f"Unknown operation type: {op_type}")

        # Extract data from Pydantic schema
        obj_data = obj_in.model_dump()

        # Handle 'fees' separately because setting it directly as None/dicts is invalid for SQLAlchemy relationship
        fees_data = obj_data.pop("fees", None)

        # Filter obj_data to only include attributes that are valid for the specific subclass.
        # This prevents passing null subclass-specific fields (e.g. limit_price) to incorrect subclasses.
        mapper = model_cls.__mapper__
        valid_keys = set(mapper.attrs.keys())
        filtered_data = {k: v for k, v in obj_data.items() if k in valid_keys or hasattr(model_cls, k)}

        # Instantiate specific subclass
        db_obj = model_cls(**filtered_data)

        # Convert and attach fees if provided
        if fees_data:
            db_obj.fees = [Fee(**fee) for fee in fees_data]

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


operation_crud = CRUDOperation(Operation)
