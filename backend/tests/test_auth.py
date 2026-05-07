from fastapi.testclient import TestClient

from app.main import app


def test_login_rejects_bad_password() -> None:
    client = TestClient(app)
    response = client.post("/api/auth/login", json={"username": "admin", "password": "bad"})
    assert response.status_code == 401


def test_login_accepts_default_admin() -> None:
    client = TestClient(app)
    response = client.post("/api/auth/login", json={"username": "admin", "password": "StrongTestAdminPass123!"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["user"]["username"] == "admin"
    assert payload["access_token"]


def test_login_rate_limits_repeated_bad_passwords() -> None:
    client = TestClient(app)
    for _ in range(5):
        response = client.post("/api/auth/login", json={"username": "admin", "password": "bad"})
        assert response.status_code == 401

    response = client.post("/api/auth/login", json={"username": "admin", "password": "bad"})
    assert response.status_code == 429


def test_me_requires_auth() -> None:
    client = TestClient(app)
    response = client.get("/api/auth/me")
    assert response.status_code == 401
