from unittest.mock import patch

from fastapi.testclient import TestClient

from medibot.auth import create_access_token
from medibot.config import Settings, get_settings
from medibot.main import app
from medibot.models import Role


def test_health_and_login() -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        jwt_secret_key="b" * 32,
        demo_password="test-password",
    )
    client = TestClient(app)

    assert client.get("/health").json() == {"status": "ok"}
    response = client.post(
        "/login",
        json={"username": "dr.mehta", "password": "test-password"},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "doctor"
    app.dependency_overrides.clear()


def test_chat_requires_authentication() -> None:
    client = TestClient(app)

    response = client.post("/chat", json={"question": "What is the leave policy?"})

    assert response.status_code == 401


def test_collections_returns_role_access() -> None:
    client = TestClient(app)

    response = client.get(f"/collections/{Role.DOCTOR.value}")

    assert response.status_code == 200
    assert response.json() == {
        "role": "doctor",
        "collections": ["clinical", "general"],
    }


def test_collections_rejects_unknown_role() -> None:
    client = TestClient(app)

    response = client.get("/collections/unknown")

    assert response.status_code == 422


def test_chat_reports_dependency_readiness_failure() -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        jwt_secret_key="b" * 32,
        demo_password="test-password",
    )
    client = TestClient(app)
    settings = Settings(jwt_secret_key="b" * 32, demo_password="test-password")
    token = create_access_token("dr.mehta", Role.DOCTOR, settings)

    with (
        patch("medibot.main.get_settings", return_value=settings),
        patch(
            "medibot.main.answer_question",
            side_effect=RuntimeError("Qdrant is already in use"),
        ),
    ):
        response = client.post(
            "/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": "What is the leave policy?"},
        )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "MediBot is not ready to answer this question."
    }
    app.dependency_overrides.clear()
