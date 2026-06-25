from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel

from src.database import get_session
from src.main import app
from src.models.base import SABase
from tests.factories import (
    FinancialAccountFactory,
    InstitutionFactory,
    PortfolioFactory,
    PositionFactory,
    TradeOperationFactory,
    UserFactory,
    set_factory_session,
)


@pytest.fixture(name="engine")
def fixture_engine():
    """In-memory SQLite engine with all tables created."""
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
    with Session(engine) as s:
        set_factory_session(s)
        yield s
        set_factory_session(None)


@pytest.fixture(name="client")
def fixture_client(session):
    def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def get_auth_headers(client: TestClient, email: str, password: str = "SeedP@ss1!") -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": password},
    )
    assert response.status_code == status.HTTP_200_OK, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_crud_operations(client: TestClient, session: Session):
    user = UserFactory(email="ops@example.com")
    session.commit()
    headers = get_auth_headers(client, "ops@example.com")

    # Set up dependent objects
    portfolio = PortfolioFactory(user=user)
    position = PositionFactory(portfolio=portfolio)
    institution = InstitutionFactory()
    account = FinancialAccountFactory(institution=institution)
    session.commit()

    # 1. Create Operation
    create_payload = {
        "position_id": position.id,
        "financial_account_id": account.id,
        "operation_type": "trade",
        "executed_at": "2026-01-01T12:00:00Z",
        "total_amount": "100.00",
        "currency": "USD",
        "quantity": "10.00",
        "unit_price": "10.00",
        "trade_side": "buy",
        "order_type": "market",
        "order_status": "filled",
    }

    resp = client.post("/api/v1/operations/", json=create_payload, headers=headers)
    assert resp.status_code == status.HTTP_201_CREATED
    op_data = resp.json()
    op_id = op_data["id"]
    assert op_data["operation_type"] == "trade"
    assert op_data["trade_side"] == "buy"

    # 2. Read Operations (all for user)
    resp = client.get("/api/v1/operations/", headers=headers)
    assert resp.status_code == status.HTTP_200_OK
    all_ops = resp.json()
    assert len(all_ops) == 1

    # 3. Read Operations (filtered by position_id)
    resp = client.get(f"/api/v1/operations/?position_id={position.id}", headers=headers)
    assert resp.status_code == status.HTTP_200_OK
    pos_ops = resp.json()
    assert len(pos_ops) == 1
    assert pos_ops[0]["id"] == op_id

    # 4. Read single Operation
    resp = client.get(f"/api/v1/operations/{op_id}", headers=headers)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["id"] == op_id

    # 5. Update Operation
    update_payload = {"total_amount": "150.00"}
    resp = client.put(f"/api/v1/operations/{op_id}", json=update_payload, headers=headers)
    assert resp.status_code == status.HTTP_200_OK
    assert Decimal(resp.json()["total_amount"]) == Decimal("150.00")

    # 6. Delete Operation
    resp = client.delete(f"/api/v1/operations/{op_id}", headers=headers)
    assert resp.status_code == status.HTTP_200_OK

    resp = client.get(f"/api/v1/operations/{op_id}", headers=headers)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_operations_authorization_errors(client: TestClient, session: Session):
    UserFactory(email="ops1@example.com")
    user2 = UserFactory(email="ops2@example.com")
    session.commit()

    portfolio2 = PortfolioFactory(user=user2)
    position2 = PositionFactory(portfolio=portfolio2)
    institution = InstitutionFactory()
    account = FinancialAccountFactory(institution=institution)

    op2 = TradeOperationFactory(position=position2, financial_account=account)
    session.commit()

    headers_user1 = get_auth_headers(client, "ops1@example.com")

    # Try to read user2's operation
    resp = client.get(f"/api/v1/operations/{op2.id}", headers=headers_user1)
    assert resp.status_code == status.HTTP_404_NOT_FOUND

    # Try to update user2's operation
    resp = client.put(f"/api/v1/operations/{op2.id}", json={"total_amount": "200.00"}, headers=headers_user1)
    assert resp.status_code == status.HTTP_404_NOT_FOUND

    # Try to delete user2's operation
    resp = client.delete(f"/api/v1/operations/{op2.id}", headers=headers_user1)
    assert resp.status_code == status.HTTP_404_NOT_FOUND

    # Try to filter by user2's position
    resp = client.get(f"/api/v1/operations/?position_id={position2.id}", headers=headers_user1)
    assert resp.status_code == status.HTTP_404_NOT_FOUND

    # Try to create operation on user2's position
    create_payload = {
        "position_id": position2.id,
        "financial_account_id": account.id,
        "operation_type": "trade",
        "executed_at": "2026-01-01T12:00:00Z",
        "total_amount": "100.00",
        "currency": "USD",
        "quantity": "10.00",
        "unit_price": "10.00",
        "trade_side": "buy",
        "order_type": "market",
        "order_status": "filled",
    }
    resp = client.post("/api/v1/operations/", json=create_payload, headers=headers_user1)
    assert resp.status_code == status.HTTP_404_NOT_FOUND
