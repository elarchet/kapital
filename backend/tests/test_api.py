from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel

from src.database import get_session
from src.main import app
from src.models import (
    SABase,
)
from src.models.import_file_schema import ImportFileSchema
from tests.factories import (
    FinancialAccountFactory,
    InstitutionFactory,
    PortfolioFactory,
    PositionFactory,
    UserFactory,
    set_factory_session,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(name="engine")
def fixture_engine():
    """In-memory SQLite engine with all tables created."""
    # SQLite in-memory DB with StaticPool to share connection between threads
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
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


@pytest.fixture(name="client")
def fixture_client(session):
    """Yield a TestClient with database session dependency overridden."""

    def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# Helper to get standard auth headers for a user
def get_auth_headers(client: TestClient, email: str, password: str = "SeedP@ss1!") -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": password},
    )
    assert response.status_code == status.HTTP_200_OK, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 1. Auth Endpoint Tests
# ---------------------------------------------------------------------------


def test_register_and_login(client: TestClient):
    # Register a new user
    register_payload = {
        "email": "testapi@example.com",
        "password": "SecurePassword1!",
    }
    response = client.post("/api/v1/auth/register", json=register_payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "public_id" in data
    assert data["email"] == "testapi@example.com"
    assert "password" not in data
    assert "hashed_password" not in data

    # Double register must fail
    response = client.post("/api/v1/auth/register", json=register_payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    # Login to obtain token
    login_response = client.post(
        "/api/v1/auth/token",
        data={"username": "testapi@example.com", "password": "SecurePassword1!"},
    )
    assert login_response.status_code == status.HTTP_200_OK
    token_data = login_response.json()
    assert token_data["token_type"] == "bearer"
    assert "access_token" in token_data

    # Fetch profile (/auth/me)
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    me_response = client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == status.HTTP_200_OK
    assert me_response.json()["email"] == "testapi@example.com"


# ---------------------------------------------------------------------------
# 2. Portfolio CRUD Tests with Gating
# ---------------------------------------------------------------------------


def test_portfolio_crud_and_gating(client: TestClient, session: Session):
    # Create two users
    user1 = UserFactory(email="user1@example.com")
    user2 = UserFactory(email="user2@example.com")
    session.commit()

    headers1 = get_auth_headers(client, user1.email)
    headers2 = get_auth_headers(client, user2.email)

    # User 1 creates portfolio
    portfolio_payload = {
        "name": "User 1 Portfolio",
        "description": "My first wealth allocation",
    }
    response = client.post("/api/v1/portfolios/", json=portfolio_payload, headers=headers1)
    assert response.status_code == status.HTTP_201_CREATED
    portfolio_data = response.json()
    p1_id = portfolio_data["id"]
    assert portfolio_data["name"] == "User 1 Portfolio"

    # User 2 lists portfolios (should be empty for them)
    response = client.get("/api/v1/portfolios/", headers=headers2)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 0

    # User 2 tries to fetch User 1's portfolio (should fail with 404)
    response = client.get(f"/api/v1/portfolios/{p1_id}", headers=headers2)
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # User 1 lists portfolios (should have 1 portfolio)
    response = client.get("/api/v1/portfolios/", headers=headers1)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == p1_id

    # User 1 updates portfolio
    update_payload = {"name": "User 1 Updated Portfolio Name"}
    response = client.put(f"/api/v1/portfolios/{p1_id}", json=update_payload, headers=headers1)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "User 1 Updated Portfolio Name"

    # User 2 tries to update User 1's portfolio (should fail)
    response = client.put(f"/api/v1/portfolios/{p1_id}", json=update_payload, headers=headers2)
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # User 1 deletes portfolio
    response = client.delete(f"/api/v1/portfolios/{p1_id}", headers=headers1)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["is_active"] is False

    # Portfolio is now inactive, listing should be empty
    response = client.get("/api/v1/portfolios/", headers=headers1)
    assert len(response.json()) == 0


# ---------------------------------------------------------------------------
# 3. Position CRUD Tests with Portfolio Gating
# ---------------------------------------------------------------------------


def test_position_crud_and_gating(client: TestClient, session: Session):
    user1 = UserFactory(email="u1@example.com")
    user2 = UserFactory(email="u2@example.com")
    p1 = PortfolioFactory(user=user1)
    p2 = PortfolioFactory(user=user2)
    session.commit()

    h1 = get_auth_headers(client, user1.email)
    h2 = get_auth_headers(client, user2.email)

    # User 1 creates position in their portfolio
    position_payload = {
        "asset_type": "stock",
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "isin": "US0378331005",
        "quantity": "10.5",
        "currency": "USD",
        "portfolio_id": p1.id,
    }
    response = client.post("/api/v1/positions/", json=position_payload, headers=h1)
    assert response.status_code == status.HTTP_201_CREATED
    pos_data = response.json()
    pos_id = pos_data["id"]
    assert pos_data["ticker"] == "AAPL"
    # Verify decimal parsing was successful
    assert Decimal(pos_data["quantity"]) == Decimal("10.5")

    # User 1 tries to create a position in User 2's portfolio (should fail 404)
    invalid_position_payload = position_payload.copy()
    invalid_position_payload["portfolio_id"] = p2.id
    response = client.post("/api/v1/positions/", json=invalid_position_payload, headers=h1)
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # User 2 tries to fetch User 1's position (should fail 404)
    response = client.get(f"/api/v1/positions/{pos_id}", headers=h2)
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # User 1 updates position
    update_payload = {"ticker": "AAPL-NEW", "quantity": "12.0"}
    response = client.put(f"/api/v1/positions/{pos_id}", json=update_payload, headers=h1)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["ticker"] == "AAPL-NEW"
    assert Decimal(response.json()["quantity"]) == Decimal("12.0")


# ---------------------------------------------------------------------------
# 4. Master Data: Institution & Financial Account CRUD
# ---------------------------------------------------------------------------


def test_reference_data_crud(client: TestClient, session: Session):
    user = UserFactory()
    session.commit()
    h = get_auth_headers(client, user.email)

    # Create Institution
    inst_payload = {
        "name": "Interactive Brokers",
        "country": "US",
        "website": "https://www.interactivebrokers.com",
    }
    response = client.post("/api/v1/institutions/", json=inst_payload, headers=h)
    assert response.status_code == status.HTTP_201_CREATED
    inst_id = response.json()["id"]

    # Create Financial Account
    acc_payload = {
        "name": "USD Margin Account",
        "account_number": "U1234567",
        "currency": "USD",
        "institution_id": inst_id,
    }
    response = client.post("/api/v1/financial-accounts/", json=acc_payload, headers=h)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["id"] is not None
    assert response.json()["name"] == "USD Margin Account"

    # Try creating account for invalid institution
    bad_acc_payload = acc_payload.copy()
    bad_acc_payload["institution_id"] = 99999
    response = client.post("/api/v1/financial-accounts/", json=bad_acc_payload, headers=h)
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# 5. Polymorphic STI Operations CRUD & Validation
# ---------------------------------------------------------------------------


def test_polymorphic_operation_validation_and_crud(client: TestClient, session: Session):
    user = UserFactory()
    portfolio = PortfolioFactory(user=user)
    position = PositionFactory(portfolio=portfolio)
    institution = InstitutionFactory()
    account = FinancialAccountFactory(institution=institution)
    session.commit()

    h = get_auth_headers(client, user.email)

    # 1. Successful Buy Operation creation (as trade with trade_side=buy)
    buy_payload = {
        "operation_type": "trade",
        "trade_side": "buy",
        "quantity": "50.0",
        "unit_price": "145.50",
        "total_amount": "7275.00",
        "currency": "USD",
        "executed_at": datetime.now(UTC).isoformat(),
        "notes": "Long-term tech stack investment",
        "position_id": position.id,
        "financial_account_id": account.id,
    }
    response = client.post("/api/v1/operations/", json=buy_payload, headers=h)
    assert response.status_code == status.HTTP_201_CREATED
    op_data = response.json()
    assert op_data["operation_type"] == "trade"
    assert op_data["trade_side"] == "buy"
    assert Decimal(op_data["quantity"]) == Decimal(50)

    # 2. Limit Buy Operation fails if limit_price is missing
    limit_buy_bad_payload = {
        "operation_type": "trade",
        "trade_side": "buy",
        "order_type": "limit",
        "quantity": "10",
        "unit_price": "90",
        "total_amount": "900",
        "executed_at": datetime.now(UTC).isoformat(),
        "position_id": position.id,
        "financial_account_id": account.id,
    }
    response = client.post("/api/v1/operations/", json=limit_buy_bad_payload, headers=h)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    # 3. Successful Limit Buy Operation with limit_price
    limit_buy_good_payload = limit_buy_bad_payload.copy()
    limit_buy_good_payload["limit_price"] = "89.50"
    response = client.post("/api/v1/operations/", json=limit_buy_good_payload, headers=h)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["operation_type"] == "trade"
    assert response.json()["order_type"] == "limit"
    assert Decimal(response.json()["limit_price"]) == Decimal("89.50")

    # 4. Successful Dividend Operation with dividend_per_share
    div_payload = {
        "operation_type": "dividend",
        "dividend_per_share": "1.25",
        "total_amount": "12.50",
        "executed_at": datetime.now(UTC).isoformat(),
        "position_id": position.id,
        "financial_account_id": account.id,
    }
    response = client.post("/api/v1/operations/", json=div_payload, headers=h)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["operation_type"] == "dividend"
    assert Decimal(response.json()["dividend_per_share"]) == Decimal("1.25")

    # 5. Double-check ownership boundary: User 2 tries to create operation on User 1's position
    user2 = UserFactory(email="intruder@example.com")
    session.commit()
    h2 = get_auth_headers(client, user2.email)

    intruder_payload = buy_payload.copy()
    intruder_payload["position_id"] = position.id
    response = client.post("/api/v1/operations/", json=intruder_payload, headers=h2)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_import_portfolio_csv_endpoint(client: TestClient, session: Session):
    user = UserFactory(email="importer@example.com")
    portfolio = PortfolioFactory(user=user)
    session.commit()
    session.refresh(user)
    session.refresh(portfolio)

    headers = get_auth_headers(client, user.email)

    # Seed the ImportFileSchema
    t212_mappings = {
        "columns": {
            "operation_type": "Action",
            "executed_at": "Time",
            "isin": "ISIN",
            "ticker": "Ticker",
            "name": "Name",
            "notes": "Notes",
            "transaction_id": "ID",
            "quantity": "No. of shares",
            "unit_price": "Price / share",
            "currency": "Currency (Total)",
            "total_amount": "Total",
            "exchange_rate": "Exchange rate",
        },
        "type_mappings": {
            "buy": ["Market buy"],
        },
    }
    schema = ImportFileSchema(
        name="Trading 212 API Test",
        is_public=True,
        delimiter=",",
        decimal_separator=".",
        mappings=json.dumps(t212_mappings),
        user_id=user.id,
    )
    session.add(schema)
    session.commit()
    session.refresh(schema)

    csv_data = (
        "Action,Time,ISIN,Ticker,Name,Notes,ID,No. of shares,Price / share,Currency (Total),Total,Exchange rate\n"
        "Market buy,2026-01-08 08:18:00,US0378331005,AAPL,Apple Inc.,Notes,12345,10,150.00,USD,1500.00,1.0\n"
    )

    files = {"file": ("test.csv", csv_data, "text/csv")}
    form_data = {"schema_id": str(schema.id)}

    response = client.post(
        f"/api/v1/portfolios/{portfolio.id}/import",
        headers=headers,
        files=files,
        data=form_data,
    )

    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert "positions_created" in data
    assert "operations_imported" in data
    assert "operations_skipped" in data
    assert data["positions_created"] == 2
    assert data["operations_imported"] == 1
    assert data["operations_skipped"] == 0
