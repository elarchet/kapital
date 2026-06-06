"""Pytest suite verifying all Kapital models end-to-end.

Covers:
 1. Shared metadata — all tables created together (SQLModel + SABase).
 2. User: CRUD, argon2id password hashing & verification.
 3. Full relationship chain: User → Portfolio → Position → Operation.
 4. STI polymorphism: querying Operation returns correct subclass.
 5. Timestamp & SoftDelete mixins behave correctly.
 6. Each Operation subclass can be instantiated.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import inspect, select
from sqlmodel import Session, SQLModel, create_engine

from src.models import (
    AssetType,
    BuyOperation,
    DividendOperation,
    FeeOperation,
    FxRateChangeOperation,
    Institution,
    InterestOperation,
    InterestType,
    LimitBuyOperation,
    LimitSellOperation,
    Operation,
    SABase,
    SellOperation,
    StockSplitOperation,
    TaxOperation,
    TransferInOperation,
    TransferOutOperation,
    User,
)
from tests.factories import (
    BuyOperationFactory,
    DividendOperationFactory,
    FeeOperationFactory,
    FinancialAccountFactory,
    FxRateChangeOperationFactory,
    InstitutionFactory,
    InterestOperationFactory,
    LimitBuyOperationFactory,
    LimitSellOperationFactory,
    PortfolioFactory,
    PositionFactory,
    SellOperationFactory,
    StockSplitOperationFactory,
    TaxOperationFactory,
    TransferInOperationFactory,
    TransferOutOperationFactory,
    UserFactory,
    set_factory_session,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(name="engine")
def fixture_engine():
    """In-memory SQLite engine with all tables created."""
    eng = create_engine("sqlite://", echo=False)
    SQLModel.metadata.create_all(eng)
    SABase.metadata.create_all(eng)
    return eng


@pytest.fixture(name="session")
def fixture_session(engine):
    """Yield a fresh session per test."""
    with Session(engine) as s:
        set_factory_session(s)
        yield s
        set_factory_session(None)


@pytest.fixture(name="seed")
def fixture_seed(session):
    """Insert a minimal entity graph and return it as a dict.

    Creates: User → Portfolio → Position + Institution → FinancialAccount.
    """
    user = UserFactory()
    portfolio = PortfolioFactory(user=user)
    institution = InstitutionFactory()
    account = FinancialAccountFactory(institution=institution)
    position = PositionFactory(portfolio=portfolio)
    session.commit()

    session.refresh(user)
    session.refresh(portfolio)
    session.refresh(institution)
    session.refresh(account)
    session.refresh(position)

    return {
        "user": user,
        "portfolio": portfolio,
        "institution": institution,
        "account": account,
        "position": position,
    }


# ---------------------------------------------------------------------------
# 1. Table creation
# ---------------------------------------------------------------------------


class TestTableCreation:
    """Verify shared metadata produces all expected tables."""

    EXPECTED_TABLES = {
        "user",
        "portfolio",
        "position",
        "institution",
        "financial_account",
        "operation",
    }

    def test_all_tables_exist(self, engine):
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        assert self.EXPECTED_TABLES.issubset(tables), f"Missing tables: {self.EXPECTED_TABLES - tables}"

    @pytest.mark.parametrize("table_name", sorted(EXPECTED_TABLES))
    def test_individual_table(self, engine, table_name):
        inspector = inspect(engine)
        assert table_name in inspector.get_table_names()


# ---------------------------------------------------------------------------
# 2. User model — CRUD + password
# ---------------------------------------------------------------------------


class TestUser:
    """User CRUD and argon2id password lifecycle."""

    def test_create_and_persist(self, session):
        user: User = UserFactory()  # type: ignore[assignment]
        session.commit()
        session.refresh(user)

        assert user.id is not None
        assert user.public_id is not None

    def test_password_hash_format(self, session):
        user: User = UserFactory()  # type: ignore[assignment]
        assert user.hashed_password.startswith("$argon2")

    def test_password_verify_correct(self, session):
        user: User = UserFactory(password="KnownP@ss1!")  # type: ignore[assignment]
        assert user.verify_password("KnownP@ss1!") is True

    def test_password_verify_wrong(self, session):
        user: User = UserFactory(password="KnownP@ss1!")  # type: ignore[assignment]
        assert user.verify_password("wrong") is False

    def test_defaults(self, session):
        user: User = UserFactory()  # type: ignore[assignment]
        session.commit()
        session.refresh(user)

        assert user.is_active is True
        assert user.created_at is not None
        assert user.updated_at is not None


# ---------------------------------------------------------------------------
# 3. Full relationship chain
# ---------------------------------------------------------------------------


class TestRelationships:
    """Verify the complete FK / relationship graph."""

    def test_portfolio_user_fk(self, session, seed):
        assert seed["portfolio"].user_id == seed["user"].id

    def test_position_portfolio_fk(self, session, seed):
        assert seed["position"].portfolio_id == seed["portfolio"].id

    def test_operation_position_fk(self, session, seed):
        buy: BuyOperation = BuyOperationFactory(  # type: ignore[assignment]
            position=seed["position"],
            financial_account=seed["account"],
            quantity=Decimal(10),
            unit_price=Decimal("95.50"),
        )
        session.commit()
        session.refresh(buy)

        assert buy.position_id == seed["position"].id
        assert buy.financial_account_id == seed["account"].id

    def test_navigate_portfolio_positions(self, session, seed):
        session.refresh(seed["portfolio"])
        assert len(seed["portfolio"].positions) == 1
        assert seed["portfolio"].positions[0].ticker == seed["position"].ticker

    def test_navigate_position_operations(self, session, seed):
        BuyOperationFactory(
            position=seed["position"],
            financial_account=seed["account"],
            quantity=Decimal(5),
            unit_price=Decimal(100),
        )
        session.commit()

        session.refresh(seed["position"])
        assert len(seed["position"].operations) == 1
        assert seed["position"].operations[0].operation_type == "buy"

    def test_navigate_institution_accounts(self, session, seed):
        session.refresh(seed["institution"])
        assert len(seed["institution"].financial_accounts) == 1

    def test_navigate_user_portfolios(self, session, seed):
        session.refresh(seed["user"])
        assert len(seed["user"].portfolios) == 1


# ---------------------------------------------------------------------------
# 4. STI polymorphism
# ---------------------------------------------------------------------------


class TestPolymorphicDispatch:
    """Querying ``Operation`` must return the correct subclass instances."""

    ALL_SUBCLASSES: list[tuple[str, type[Operation]]] = [
        ("BuyOperation", BuyOperation),
        ("SellOperation", SellOperation),
        ("DividendOperation", DividendOperation),
        ("FeeOperation", FeeOperation),
        ("TaxOperation", TaxOperation),
        ("InterestOperation", InterestOperation),
        ("TransferInOperation", TransferInOperation),
        ("TransferOutOperation", TransferOutOperation),
        ("StockSplitOperation", StockSplitOperation),
        ("FxRateChangeOperation", FxRateChangeOperation),
        ("LimitBuyOperation", LimitBuyOperation),
        ("LimitSellOperation", LimitSellOperation),
    ]

    @pytest.fixture(name="ops_map")
    def fixture_ops_map(self, session, seed):
        """Insert all 12 operation types and return a {class_name: instance} map."""
        common = dict(
            position=seed["position"],
            financial_account=seed["account"],
            total_amount=Decimal(100),
        )

        [
            BuyOperationFactory(**common),
            SellOperationFactory(**common),
            DividendOperationFactory(**common),
            FeeOperationFactory(**common),
            TaxOperationFactory(**common),
            InterestOperationFactory(**common),
            TransferInOperationFactory(**common),
            TransferOutOperationFactory(**common),
            StockSplitOperationFactory(**common),
            FxRateChangeOperationFactory(**common),
            LimitBuyOperationFactory(**common),
            LimitSellOperationFactory(**common),
        ]
        session.commit()

        # NOTE: Use execute().scalars() — Operation is a pure SQLAlchemy
        # model (SABase), and SQLModel's exec() returns Rows instead of
        # mapped instances for non-SQLModel classes.
        results = (
            session.execute(
                select(Operation).where(
                    Operation.position_id == seed["position"].id,
                ),
            )
            .scalars()
            .all()
        )

        return {type(op).__name__: op for op in results}

    def test_total_count(self, ops_map):
        assert len(ops_map) == 12

    @pytest.mark.parametrize(
        "class_name,cls",
        ALL_SUBCLASSES,
        ids=[name for name, _ in ALL_SUBCLASSES],
    )
    def test_isinstance(self, ops_map, class_name, cls):
        assert isinstance(ops_map[class_name], cls)

    def test_dividend_per_share_roundtrip(self, ops_map):
        assert ops_map["DividendOperation"].dividend_per_share == Decimal("0.82")

    def test_fx_exchange_rate_roundtrip(self, ops_map):
        assert ops_map["FxRateChangeOperation"].exchange_rate == Decimal("0.9200000000")

    def test_split_ratio_roundtrip(self, ops_map):
        assert ops_map["StockSplitOperation"].split_ratio == Decimal("4.0")

    def test_limit_price_roundtrip(self, ops_map):
        assert ops_map["LimitBuyOperation"].limit_price == Decimal("89.50")

    def test_fee_category_roundtrip(self, ops_map):
        assert ops_map["FeeOperation"].fee_category == "custody"

    def test_tax_category_roundtrip(self, ops_map):
        assert ops_map["TaxOperation"].tax_category == "withholding"

    def test_transfer_references_roundtrip(self, ops_map):
        assert ops_map["TransferInOperation"].source_reference == "BANK-REF-001"
        assert ops_map["TransferOutOperation"].destination_reference == "EXT-REF-002"

    def test_interest_type_roundtrip(self, ops_map):
        assert ops_map["InterestOperation"].interest_type == InterestType.CASH_INTEREST


# ---------------------------------------------------------------------------
# 5. Mixins
# ---------------------------------------------------------------------------


class TestTimestampMixin:
    """TimestampMixin auto-populates created_at and updated_at."""

    def test_created_at_set(self, session):
        inst: Institution = InstitutionFactory(name="TSMixin1")  # type: ignore[assignment]
        session.commit()
        session.refresh(inst)
        assert inst.created_at is not None

    def test_updated_at_set(self, session):
        inst: Institution = InstitutionFactory(name="TSMixin2")  # type: ignore[assignment]
        session.commit()
        session.refresh(inst)
        assert inst.updated_at is not None


class TestSoftDeleteMixin:
    """SoftDeleteMixin defaults and soft-delete behaviour."""

    def test_defaults(self, session):
        inst: Institution = InstitutionFactory(name="SDMixin1")  # type: ignore[assignment]
        session.commit()
        session.refresh(inst)
        assert inst.is_active is True
        assert inst.deleted_at is None

    def test_soft_delete(self, session):
        inst: Institution = InstitutionFactory(name="SDMixin2")  # type: ignore[assignment]
        session.commit()
        session.refresh(inst)

        inst.is_active = False
        inst.deleted_at = datetime.now(UTC)
        session.add(inst)
        session.commit()
        session.refresh(inst)

        assert inst.is_active is False
        assert inst.deleted_at is not None


# ---------------------------------------------------------------------------
# 6. AssetType enum
# ---------------------------------------------------------------------------


class TestAssetTypeEnum:
    """AssetType StrEnum has expected members and string values."""

    @pytest.mark.parametrize(
        "member,value",
        [
            ("CASH", "cash"),
            ("CRYPTO", "crypto"),
            ("ETF", "etf"),
            ("STOCK", "stock"),
            ("BOND", "bond"),
            ("COMMODITY", "commodity"),
            ("FUND", "fund"),
            ("OTHER", "other"),
        ],
    )
    def test_member_value(self, member, value):
        assert getattr(AssetType, member) == value
