from __future__ import annotations

from datetime import UTC
from decimal import Decimal

import factory
from factory.alchemy import SQLAlchemyModelFactory

from src.models import (
    AssetType,
    BuyOperation,
    DividendOperation,
    FeeOperation,
    FinancialAccount,
    FxRateChangeOperation,
    Institution,
    InterestOperation,
    LimitBuyOperation,
    LimitSellOperation,
    Operation,
    Portfolio,
    Position,
    SellOperation,
    StockSplitOperation,
    TaxOperation,
    TransferInOperation,
    TransferOutOperation,
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


class BaseOperationFactory(BaseFactory):
    class Meta:
        model = Operation
        abstract = True

    total_amount = factory.Faker("pydecimal", left_digits=6, right_digits=2, positive=True)
    currency = factory.Faker("currency_code")
    executed_at = factory.Faker("date_time_this_year", tzinfo=UTC)
    position = factory.SubFactory(PositionFactory)
    financial_account = factory.SubFactory(FinancialAccountFactory)


class BuyOperationFactory(BaseOperationFactory):
    class Meta:
        model = BuyOperation

    quantity = factory.LazyFunction(lambda: Decimal("1.00"))
    unit_price = factory.LazyFunction(lambda: Decimal("100.00"))


class SellOperationFactory(BaseOperationFactory):
    class Meta:
        model = SellOperation

    quantity = factory.LazyFunction(lambda: Decimal("1.00"))
    unit_price = factory.LazyFunction(lambda: Decimal("100.00"))


class DividendOperationFactory(BaseOperationFactory):
    class Meta:
        model = DividendOperation

    dividend_per_share = factory.LazyFunction(lambda: Decimal("0.82"))


class FeeOperationFactory(BaseOperationFactory):
    class Meta:
        model = FeeOperation

    fee_category = "custody"


class TaxOperationFactory(BaseOperationFactory):
    class Meta:
        model = TaxOperation

    tax_category = "withholding"


class InterestOperationFactory(BaseOperationFactory):
    class Meta:
        model = InterestOperation


class TransferInOperationFactory(BaseOperationFactory):
    class Meta:
        model = TransferInOperation

    source_reference = "BANK-REF-001"


class TransferOutOperationFactory(BaseOperationFactory):
    class Meta:
        model = TransferOutOperation

    destination_reference = "EXT-REF-002"


class StockSplitOperationFactory(BaseOperationFactory):
    class Meta:
        model = StockSplitOperation

    split_ratio = factory.LazyFunction(lambda: Decimal("4.0"))


class FxRateChangeOperationFactory(BaseOperationFactory):
    class Meta:
        model = FxRateChangeOperation

    source_currency = "USD"
    target_currency = "EUR"
    exchange_rate = factory.LazyFunction(lambda: Decimal("0.9200000000"))


class LimitBuyOperationFactory(BaseOperationFactory):
    class Meta:
        model = LimitBuyOperation

    quantity = factory.LazyFunction(lambda: Decimal("5.00"))
    unit_price = factory.LazyFunction(lambda: Decimal("90.00"))
    limit_price = factory.LazyFunction(lambda: Decimal("89.50"))


class LimitSellOperationFactory(BaseOperationFactory):
    class Meta:
        model = LimitSellOperation

    quantity = factory.LazyFunction(lambda: Decimal("5.00"))
    unit_price = factory.LazyFunction(lambda: Decimal("110.00"))
    limit_price = factory.LazyFunction(lambda: Decimal("111.00"))
