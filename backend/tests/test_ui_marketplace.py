from __future__ import annotations

from pathlib import Path

import factory
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel

from src.config import settings
from src.database import get_session
from src.main import app
from src.models import SABase
from src.models.ui_marketplace import UIComponentVariant
from tests.factories import BaseFactory, UserFactory, set_factory_session


class UIComponentVariantFactory(BaseFactory):
    class Meta:
        model = UIComponentVariant

    component_key = "sidebar"
    name = factory.Faker("word")
    description = factory.Faker("sentence")
    asset_url = "https://sandbox-assets.kapital.app/sidebar-custom.js"
    is_public = False
    user = factory.SubFactory(UserFactory)


@pytest.fixture(name="engine")
def fixture_engine():
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
        UIComponentVariantFactory._meta.sqlalchemy_session = s  # noqa: SLF001
        yield s
        set_factory_session(None)
        UIComponentVariantFactory._meta.sqlalchemy_session = None  # noqa: SLF001


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


def test_theme_update(client: TestClient, session: Session):
    user = UserFactory(email="testtheme@example.com")
    session.commit()
    headers = get_auth_headers(client, user.email)

    # Check default theme
    response = client.get("/api/v1/user/preferences/", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["theme"] == "slate-light"
    assert response.json()["overrides"] == {}

    # Update theme
    update_response = client.put(
        "/api/v1/user/preferences/theme",
        json={"theme": "slate-dark"},
        headers=headers,
    )
    assert update_response.status_code == status.HTTP_200_OK
    assert update_response.json()["theme"] == "slate-dark"

    # Verify update persisted
    verify_response = client.get("/api/v1/user/preferences/", headers=headers)
    assert verify_response.status_code == status.HTTP_200_OK
    assert verify_response.json()["theme"] == "slate-dark"


def test_variant_crud(client: TestClient, session: Session):
    user = UserFactory(email="testvariant@example.com")
    session.commit()
    headers = get_auth_headers(client, user.email)

    # Register custom variant
    payload = {
        "component_key": "sidebar",
        "name": "Custom glass sidebar",
        "description": "Premium theme sidebar variant",
        "asset_url": "https://sandbox-assets.kapital.app/glass-sidebar.js",
        "is_public": False,
    }
    response = client.post("/api/v1/user/preferences/variants", json=payload, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    variant_data = response.json()
    assert variant_data["name"] == "Custom glass sidebar"
    assert variant_data["user_id"] == user.id

    # List variants (should contain our created variant)
    list_response = client.get("/api/v1/user/preferences/variants", headers=headers)
    assert list_response.status_code == status.HTTP_200_OK
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["name"] == "Custom glass sidebar"

    # List with component key filter
    filtered_response = client.get(
        "/api/v1/user/preferences/variants?component_key=sidebar",
        headers=headers,
    )
    assert len(filtered_response.json()) == 1

    filtered_empty = client.get(
        "/api/v1/user/preferences/variants?component_key=custom-dropdown",
        headers=headers,
    )
    assert len(filtered_empty.json()) == 0


def test_component_override_flow(client: TestClient, session: Session):
    user = UserFactory(email="testoverride@example.com")
    # Create public variant and private variant
    var_public = UIComponentVariantFactory(
        component_key="custom-dropdown",
        name="Public Dropdown",
        is_public=True,
        user=None,
    )
    UIComponentVariantFactory(
        component_key="sidebar",
        name="Private Sidebar",
        is_public=False,
        user=user,
    )
    session.commit()

    headers = get_auth_headers(client, user.email)

    # Set override for dropdown to public variant
    override_payload = {"component_key": "custom-dropdown", "variant_id": var_public.id}
    response = client.post("/api/v1/user/preferences/components", json=override_payload, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "Public Dropdown"

    # Check preferences GET contains it
    prefs_response = client.get("/api/v1/user/preferences/", headers=headers)
    assert prefs_response.status_code == status.HTTP_200_OK
    assert prefs_response.json()["overrides"]["custom-dropdown"]["id"] == var_public.id

    # Try setting override with an invalid / non-accessible variant
    other_user = UserFactory(email="other@example.com")
    var_other = UIComponentVariantFactory(
        component_key="sidebar",
        name="Other User Private Sidebar",
        is_public=False,
        user=other_user,
    )
    session.commit()

    invalid_payload = {"component_key": "sidebar", "variant_id": var_other.id}
    invalid_response = client.post(
        "/api/v1/user/preferences/components",
        json=invalid_payload,
        headers=headers,
    )
    assert invalid_response.status_code == status.HTTP_404_NOT_FOUND

    # Revert to default fallback
    revert_response = client.delete("/api/v1/user/preferences/components/custom-dropdown", headers=headers)
    assert revert_response.status_code == status.HTTP_200_OK

    # Verify fallback (no override entry in preferences)
    final_prefs = client.get("/api/v1/user/preferences/", headers=headers)
    overrides_res = final_prefs.json()["overrides"]
    assert "custom-dropdown" not in overrides_res or overrides_res["custom-dropdown"] is None


def test_upload_component_variant_success(client: TestClient, session: Session):
    user = UserFactory(email="testuploadsuccess@example.com")
    session.commit()
    headers = get_auth_headers(client, user.email)

    component_key = "sidebar"
    name = "Success Widget"
    description = "A valid custom ESM widget variant"
    js_content = b"export default { name: 'SuccessWidget' };"

    # Use FastAPI TestClient's files parameter
    files = {
        "file": ("widget.js", js_content, "application/javascript"),
    }
    data = {
        "component_key": component_key,
        "name": name,
        "description": description,
    }

    uploaded_file: Path | None = None
    try:
        response = client.post(
            "/api/v1/user/preferences/upload",
            headers=headers,
            data=data,
            files=files,
        )
        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert response_data["component_key"] == component_key
        assert response_data["name"] == name
        assert response_data["description"] == description
        assert response_data["user_id"] == user.id

        # Verify that the DB row was correctly created
        variant_id = response_data["id"]
        db_variant = session.get(UIComponentVariant, variant_id)
        assert db_variant is not None
        assert db_variant.component_key == component_key
        assert db_variant.name == name
        assert db_variant.description == description
        assert db_variant.user_id == user.id
        assert db_variant.asset_url.startswith(settings.ASSETS_BASE_URL)

        # Get safe filename from asset_url and assert it's on disk
        safe_filename = db_variant.asset_url.split("/")[-1]
        uploaded_file = Path(settings.UPLOAD_DIR) / safe_filename
        assert uploaded_file.exists()

        # Verify file content
        with uploaded_file.open("rb") as f:
            assert f.read() == js_content

    finally:
        # Clean up the generated file from disk
        if uploaded_file and uploaded_file.exists():
            uploaded_file.unlink()


def test_upload_component_variant_invalid_extension(client: TestClient, session: Session):
    user = UserFactory(email="testuploadinvalid@example.com")
    session.commit()
    headers = get_auth_headers(client, user.email)

    component_key = "sidebar"
    name = "Invalid Widget"
    description = "A variant with an invalid txt file extension"
    txt_content = b"hello world"

    files = {
        "file": ("widget.txt", txt_content, "text/plain"),
    }
    data = {
        "component_key": component_key,
        "name": name,
        "description": description,
    }

    response = client.post(
        "/api/v1/user/preferences/upload",
        headers=headers,
        data=data,
        files=files,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Only compiled ESM bundles (.js files) are accepted." in response.json()["detail"]
