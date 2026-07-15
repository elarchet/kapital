from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from fastapi import status

from tests.factories import (
    AllocationFactory,
    FinancialAccountFactory,
    PortfolioFactory,
    PositionFactory,
    RawTransactionFactory,
    UserFactory,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlmodel import Session


def get_auth_headers(client: TestClient, email: str, password: str = "SeedP@ss1!") -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": password},
    )
    assert response.status_code == status.HTTP_200_OK, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _make_transaction(session: Session, *, user, **txn_kwargs):
    """Create a RawTransaction owned by ``user`` via a default allocation."""
    portfolio = PortfolioFactory(user=user)
    position = PositionFactory(portfolio=portfolio)
    account = FinancialAccountFactory()
    txn = RawTransactionFactory(financial_account=account, **txn_kwargs)
    AllocationFactory(raw_transaction=txn, position=position)
    session.commit()
    session.refresh(txn)
    session.refresh(position)
    return txn, position


def test_read_and_delete_transactions(client: TestClient, session: Session):
    user = UserFactory(email="ops@example.com")
    session.commit()
    headers = get_auth_headers(client, "ops@example.com")

    txn, position = _make_transaction(session, user=user)

    # 1. Read transactions (all for user)
    resp = client.get("/api/v1/transactions/", headers=headers)
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.json()) == 1

    # 2. Read transactions filtered by position_id
    resp = client.get(f"/api/v1/transactions/?position_id={position.id}", headers=headers)
    assert resp.status_code == status.HTTP_200_OK
    pos_txns = resp.json()
    assert len(pos_txns) == 1
    assert pos_txns[0]["id"] == txn.id

    # 3. Read a single transaction
    resp = client.get(f"/api/v1/transactions/{txn.id}", headers=headers)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["id"] == txn.id
    assert resp.json()["operation_type"] == "trade"

    # 4. Read its default allocation
    resp = client.get(f"/api/v1/transactions/{txn.id}/allocations", headers=headers)
    assert resp.status_code == status.HTTP_200_OK
    allocs = resp.json()
    assert len(allocs) == 1
    assert allocs[0]["is_default"] is True

    # 5. Delete the transaction (cascades to allocations)
    resp = client.delete(f"/api/v1/transactions/{txn.id}", headers=headers)
    assert resp.status_code == status.HTTP_200_OK

    resp = client.get(f"/api/v1/transactions/{txn.id}", headers=headers)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_split_transaction_across_positions(client: TestClient, session: Session):
    user = UserFactory(email="split@example.com")
    session.commit()
    headers = get_auth_headers(client, "split@example.com")

    txn, position = _make_transaction(
        session,
        user=user,
        quantity=Decimal(40),
        total_amount=Decimal(1000),
    )
    pos_b = PositionFactory(portfolio=position.portfolio)
    session.commit()
    session.refresh(pos_b)

    payload = {
        "raw_transaction_id": txn.id,
        "lines": [
            {"position_id": position.id, "method": "percentage", "value": "25"},
            {"position_id": pos_b.id, "method": "percentage", "value": "75"},
        ],
    }
    resp = client.post(f"/api/v1/transactions/{txn.id}/allocations", json=payload, headers=headers)
    assert resp.status_code == status.HTTP_201_CREATED
    allocs = resp.json()
    assert len(allocs) == 2

    by_pos = {a["position_id"]: a for a in allocs}
    assert Decimal(by_pos[position.id]["quantity"]) == Decimal(10)
    assert Decimal(by_pos[position.id]["amount"]) == Decimal(250)
    assert Decimal(by_pos[pos_b.id]["quantity"]) == Decimal(30)
    assert Decimal(by_pos[pos_b.id]["amount"]) == Decimal(750)


def test_split_transaction_rejects_over_allocation(client: TestClient, session: Session):
    user = UserFactory(email="over@example.com")
    session.commit()
    headers = get_auth_headers(client, "over@example.com")

    txn, position = _make_transaction(
        session,
        user=user,
        quantity=Decimal(40),
        total_amount=Decimal(1000),
    )

    payload = {
        "raw_transaction_id": txn.id,
        "lines": [{"position_id": position.id, "method": "quantity", "value": "50"}],
    }
    resp = client.post(f"/api/v1/transactions/{txn.id}/allocations", json=payload, headers=headers)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_transactions_authorization_errors(client: TestClient, session: Session):
    UserFactory(email="ops1@example.com")
    user2 = UserFactory(email="ops2@example.com")
    session.commit()

    txn2, _position2 = _make_transaction(session, user=user2)
    headers_user1 = get_auth_headers(client, "ops1@example.com")

    # User 1 cannot read user 2's transaction
    resp = client.get(f"/api/v1/transactions/{txn2.id}", headers=headers_user1)
    assert resp.status_code == status.HTTP_404_NOT_FOUND

    # User 1 cannot read user 2's allocations
    resp = client.get(f"/api/v1/transactions/{txn2.id}/allocations", headers=headers_user1)
    assert resp.status_code == status.HTTP_404_NOT_FOUND

    # User 1 cannot delete user 2's transaction
    resp = client.delete(f"/api/v1/transactions/{txn2.id}", headers=headers_user1)
    assert resp.status_code == status.HTTP_404_NOT_FOUND
