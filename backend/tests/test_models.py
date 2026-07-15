"""Pytest suite verifying all Kapital models end-to-end.

Covers:
 1. Shared metadata — all tables created together (SQLModel + SABase).
 2. User: CRUD, argon2id password hashing & verification.
 3. Full relationship chain: User → Portfolio → Position → Allocation → RawTransaction.
 4. RawTransaction field persistence + Allocation splitting.
 5. Timestamp & SoftDelete mixins behave correctly.
 6. AssetType / AllocationMethod enums.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import inspect

from src.models import (
    Allocation,
    AllocationMethod,
    AssetType,
    ExpenseCategory,
    Institution,
    InterestType,
    PaymentMethod,
    RawTransaction,
    User,
)
from tests.factories import (
    AllocationFactory,
    FinancialAccountFactory,
    InstitutionFactory,
    PortfolioFactory,
    PositionFactory,
    RawTransactionFactory,
    UserFactory,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
        "raw_transaction",
        "allocation",
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

    def test_raw_transaction_account_fk(self, session, seed):
        txn: RawTransaction = RawTransactionFactory(  # type: ignore[assignment]
            financial_account=seed["account"],
        )
        session.commit()
        session.refresh(txn)
        assert txn.financial_account_id == seed["account"].id

    def test_allocation_links_transaction_to_position(self, session, seed):
        txn = RawTransactionFactory(financial_account=seed["account"])
        alloc: Allocation = AllocationFactory(  # type: ignore[assignment]
            raw_transaction=txn,
            position=seed["position"],
        )
        session.commit()
        session.refresh(alloc)

        assert alloc.position_id == seed["position"].id
        assert alloc.raw_transaction_id == txn.id

    def test_navigate_portfolio_positions(self, session, seed):
        session.refresh(seed["portfolio"])
        assert len(seed["portfolio"].positions) == 1
        assert seed["portfolio"].positions[0].ticker == seed["position"].ticker

    def test_navigate_position_allocations(self, session, seed):
        txn = RawTransactionFactory(financial_account=seed["account"])
        AllocationFactory(raw_transaction=txn, position=seed["position"])
        session.commit()

        session.refresh(seed["position"])
        assert len(seed["position"].allocations) == 1
        assert seed["position"].allocations[0].raw_transaction.operation_type == "trade"

    def test_navigate_transaction_allocations(self, session, seed):
        txn = RawTransactionFactory(financial_account=seed["account"])
        AllocationFactory(raw_transaction=txn, position=seed["position"])
        session.commit()

        session.refresh(txn)
        assert len(txn.allocations) == 1
        assert txn.allocations[0].position_id == seed["position"].id

    def test_navigate_institution_accounts(self, session, seed):
        session.refresh(seed["institution"])
        assert len(seed["institution"].financial_accounts) == 1

    def test_navigate_user_portfolios(self, session, seed):
        session.refresh(seed["user"])
        assert len(seed["user"].portfolios) == 1


# ---------------------------------------------------------------------------
# 4. RawTransaction field persistence + Allocation splitting
# ---------------------------------------------------------------------------


class TestRawTransaction:
    """RawTransaction persists its category-specific and enum fields."""

    def test_split_and_dividend_fields_roundtrip(self, session, seed):
        txn: RawTransaction = RawTransactionFactory(  # type: ignore[assignment]
            financial_account=seed["account"],
            operation_type="stock_split",
            trade_side=None,
            split_ratio=Decimal("4.0"),
            pre_split_quantity=Decimal("10.0"),
            dividend_per_share=Decimal("0.82"),
        )
        session.commit()
        session.refresh(txn)

        assert txn.split_ratio == Decimal("4.0")
        assert txn.pre_split_quantity == Decimal("10.0")
        assert txn.dividend_per_share == Decimal("0.82")

    def test_enum_fields_roundtrip(self, session, seed):
        txn: RawTransaction = RawTransactionFactory(  # type: ignore[assignment]
            financial_account=seed["account"],
            operation_type="expense",
            trade_side=None,
            expense_category=ExpenseCategory.SHOPPING,
            payment_method=PaymentMethod.CARD,
            interest_type=InterestType.CASH_INTEREST,
        )
        session.commit()
        session.refresh(txn)

        assert txn.expense_category == ExpenseCategory.SHOPPING
        assert txn.payment_method == PaymentMethod.CARD
        assert txn.interest_type == InterestType.CASH_INTEREST

    def test_dedup_and_provenance_fields(self, session, seed):
        txn: RawTransaction = RawTransactionFactory(  # type: ignore[assignment]
            financial_account=seed["account"],
            dedup_key="TX-NATIVE-1",
            native_transaction_id="TX-NATIVE-1",
            is_auto_id=False,
        )
        session.commit()
        session.refresh(txn)

        assert txn.dedup_key == "TX-NATIVE-1"
        assert txn.native_transaction_id == "TX-NATIVE-1"
        assert txn.is_auto_id is False


class TestAllocation:
    """Allocation stores the resolved split figures routed to a position."""

    def test_default_allocation_fields(self, session, seed):
        txn = RawTransactionFactory(financial_account=seed["account"])
        alloc: Allocation = AllocationFactory(  # type: ignore[assignment]
            raw_transaction=txn,
            position=seed["position"],
            method=AllocationMethod.PERCENTAGE,
            value=Decimal(100),
            quantity=Decimal(10),
            amount=Decimal(1000),
        )
        session.commit()
        session.refresh(alloc)

        assert alloc.method == AllocationMethod.PERCENTAGE
        assert alloc.value == Decimal(100)
        assert alloc.quantity == Decimal(10)
        assert alloc.amount == Decimal(1000)
        assert alloc.is_default is True

    @pytest.mark.parametrize(
        "member,value",
        [
            ("QUANTITY", "quantity"),
            ("PERCENTAGE", "percentage"),
            ("AMOUNT", "amount"),
        ],
    )
    def test_method_enum_values(self, member, value):
        assert getattr(AllocationMethod, member) == value


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
