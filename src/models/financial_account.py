"""FinancialAccount model — a specific account at an Institution."""

from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from src.models.base import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from src.models.institution import Institution
    from src.models.operation import Operation


class FinancialAccount(TimestampMixin, SoftDeleteMixin, SQLModel, table=True):
    """A financial account (brokerage, savings, etc.) held at an Institution."""

    __tablename__ = "financial_account"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(nullable=False, max_length=300)
    account_number: str | None = Field(default=None, max_length=100)
    currency: str = Field(default="EUR", nullable=False, max_length=3)

    # -- foreign keys ----------------------------------------------------------
    institution_id: int = Field(
        foreign_key="institution.id",
        nullable=False,
        index=True,
    )

    # -- relationships ---------------------------------------------------------
    institution: "Institution" = Relationship(back_populates="financial_accounts")
    operations: list["Operation"] = Relationship(
        back_populates="financial_account",
        sa_relationship_kwargs={"foreign_keys": "[Operation.financial_account_id]"},
    )
