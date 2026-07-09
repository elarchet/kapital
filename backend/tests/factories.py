from __future__ import annotations

from datetime import UTC
from decimal import Decimal

import factory
from factory.alchemy import SQLAlchemyModelFactory

from src.models import (
    Allocation,
    AllocationMethod,
    AssetType,
    FinancialAccount,
    Institution,
    OrderStatus,
    OrderType,
    Portfolio,
    Position,
    RawTransaction,
    TradeSide,
    User,
)


class BaseFactory(SQLAlchemyModelFactory):
    class Meta:
        abstract = True


def set_factory_session(session):
    """Binds the session to the base factory so created objects are saved to the DB."""

    def _set_session(cls):
        cls._meta.sqlalchemy_session = session
        for subcls in cls.__subclasses__():
            _set_session(subcls)

    _set_session(BaseFactory)


class UserFactory(BaseFactory):
    class Meta:
        model = User

    email = factory.Faker("safe_email")
    hashed_password = ""

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.set_password(extracted)  # type: ignore[attr-defined]
        else:
            self.set_password("SeedP@ss1!")  # type: ignore[attr-defined]


class PortfolioFactory(BaseFactory):
    class Meta:
        model = Portfolio

    name = factory.Faker("catch_phrase")
    user = factory.SubFactory(UserFactory)


class InstitutionFactory(BaseFactory):
    class Meta:
        model = Institution

    name = factory.Faker("company")
    country = factory.Faker("country_code")


class FinancialAccountFactory(BaseFactory):
    class Meta:
        model = FinancialAccount

    name = factory.Faker("iban")
    institution = factory.SubFactory(InstitutionFactory)
    currency = factory.Faker("currency_code")


class PositionFactory(BaseFactory):
    class Meta:
        model = Position

    asset_type = AssetType.ETF
    ticker = factory.Faker("lexify", text="????")
    name = factory.Faker("company")
    isin = factory.Faker("bothify", text="??##########")
    quantity = factory.Faker("pydecimal", left_digits=4, right_digits=8, positive=True)
    currency = factory.Faker("currency_code")
    portfolio = factory.SubFactory(PortfolioFactory)


class BaseRawTransactionFactory(BaseFactory):
    class Meta:
        model = RawTransaction
        abstract = True

    operation_type = "trade"
    dedup_key = factory.Sequence(lambda n: f"auto-txn-{n}")
    is_auto_id = True
    total_amount = factory.Faker("pydecimal", left_digits=6, right_digits=2, positive=True)
    currency = factory.Faker("currency_code")
    executed_at = factory.Faker("date_time_this_year", tzinfo=UTC)
    financial_account = factory.SubFactory(FinancialAccountFactory)


class RawTransactionFactory(BaseRawTransactionFactory):
    """A trade raw transaction with sensible defaults."""

    quantity = factory.LazyFunction(lambda: Decimal("10.00"))
    unit_price = factory.LazyFunction(lambda: Decimal("100.00"))
    trade_side = TradeSide.BUY
    order_type = OrderType.MARKET
    order_status = OrderStatus.FILLED


class AllocationFactory(BaseFactory):
    class Meta:
        model = Allocation

    method = AllocationMethod.PERCENTAGE
    value = factory.LazyFunction(lambda: Decimal(100))
    quantity = factory.LazyFunction(lambda: Decimal("10.00"))
    amount = factory.LazyFunction(lambda: Decimal("1000.00"))
    currency = factory.Faker("currency_code")
    is_default = True
    raw_transaction = factory.SubFactory(RawTransactionFactory)
    position = factory.SubFactory(PositionFactory)
