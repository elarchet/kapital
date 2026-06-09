from __future__ import annotations

from decimal import Decimal

from sqlmodel import Session, select

from src.crud import position_crud
from src.models import (
    AssetType,
    FinancialAccount,
    Institution,
    Operation,
    Position,
)
from src.schemas.position import PositionCreate


def get_or_create_institution_and_account(db: Session, institution_name: str, account_name: str) -> FinancialAccount:
    institution = db.exec(select(Institution).where(Institution.name == institution_name)).first()
    if not institution:
        institution = Institution(name=institution_name, country="GB")
        db.add(institution)
        db.commit()
        db.refresh(institution)

    if institution.id is None:
        raise ValueError("Institution ID not resolved.")

    financial_account = db.exec(
        select(FinancialAccount).where(
            FinancialAccount.name == account_name,
            FinancialAccount.institution_id == institution.id,
        ),
    ).first()
    if not financial_account:
        financial_account = FinancialAccount(
            name=account_name,
            currency="EUR",
            institution_id=institution.id,
        )
        db.add(financial_account)
        db.commit()
        db.refresh(financial_account)

    if financial_account.id is None:
        raise ValueError("Financial account ID not resolved.")

    return financial_account


def find_or_create_position(
    db: Session,
    portfolio_id: int,
    op_info: dict,
    *,
    is_cash_op: bool,
) -> tuple[Position, bool]:
    created = False
    if not is_cash_op:
        statement = select(Position).where(
            Position.portfolio_id == portfolio_id,
            Position.is_active,
        )
        if op_info["isin"]:
            statement = statement.where(Position.isin == op_info["isin"])
        elif op_info["ticker"]:
            statement = statement.where(Position.ticker == op_info["ticker"])
        else:
            statement = statement.where(Position.name == op_info["name"])

        position = db.exec(statement).first()

        if not position:
            asset_type = AssetType.STOCK
            lower_name = op_info["name"].lower()
            if any(term in lower_name for term in ("etf", "ishares", "vanguard", "xtrackers")):
                asset_type = AssetType.ETF

            position_in = PositionCreate(
                portfolio_id=portfolio_id,
                asset_type=asset_type,
                ticker=op_info["ticker"],
                name=op_info["name"],
                isin=op_info["isin"],
                quantity=Decimal("0.0"),
                currency=op_info["currency"],
            )
            position = position_crud.create(db, obj_in=position_in)
            created = True
    else:
        cash_currency = op_info["currency"]
        position = db.exec(
            select(Position).where(
                Position.portfolio_id == portfolio_id,
                Position.asset_type == AssetType.CASH,
                Position.currency == cash_currency,
                Position.is_active,
            ),
        ).first()

        if not position:
            position_in = PositionCreate(
                portfolio_id=portfolio_id,
                asset_type=AssetType.CASH,
                name=f"Cash ({cash_currency})",
                quantity=Decimal("0.0"),
                currency=cash_currency,
            )
            position = position_crud.create(db, obj_in=position_in)
            created = True
    return position, created


def check_duplicate_operation(db: Session, position_id: int, op_info: dict) -> bool:
    transaction_id = op_info["transaction_id"]
    if transaction_id:
        existing_op = db.exec(select(Operation).where(Operation.transaction_id == transaction_id)).first()
        return existing_op is not None
    statement = select(Operation).where(
        Operation.position_id == position_id,
        Operation.operation_type == op_info["op_type"],
        Operation.executed_at == op_info["executed_at"],
        Operation.total_amount == op_info["total_amount"],
    )
    if op_info["quantity"] is not None:
        statement = statement.where(Operation.quantity == op_info["quantity"])
    else:
        statement = statement.where(Operation.quantity.is_(None))

    existing_op = db.exec(statement).first()
    return existing_op is not None


def get_or_create_cash_position(db: Session, portfolio_id: int, currency: str) -> tuple[Position, bool]:
    created = False
    cash_pos = db.exec(
        select(Position).where(
            Position.portfolio_id == portfolio_id,
            Position.asset_type == AssetType.CASH,
            Position.currency == currency,
            Position.is_active,
        ),
    ).first()

    if not cash_pos:
        position_in = PositionCreate(
            portfolio_id=portfolio_id,
            asset_type=AssetType.CASH,
            name=f"Cash ({currency})",
            quantity=Decimal("0.0"),
            currency=currency,
        )
        cash_pos = position_crud.create(db, obj_in=position_in)
        created = True
    return cash_pos, created
