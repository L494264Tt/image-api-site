from fastapi.testclient import TestClient

from app.main import app


def test_login_rejects_bad_password() -> None:
    client = TestClient(app)
    response = client.post("/api/auth/login", json={"username": "admin", "password": "bad"})
    assert response.status_code == 401


def test_login_accepts_default_admin() -> None:
    client = TestClient(app)
    response = client.post("/api/auth/login", json={"username": "admin", "password": "replace-with-a-strong-admin-password"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["user"]["username"] == "admin"
    assert payload["access_token"]


def test_me_requires_auth() -> None:
    client = TestClient(app)
    response = client.get("/api/auth/me")
    assert response.status_code == 401
