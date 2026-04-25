from fastapi.testclient import TestClient

from app.main import app


def get_token(client: TestClient) -> str:
    response = client.post("/api/auth/login", json={"username": "admin", "password": "replace-with-a-strong-admin-password"})
    return response.json()["access_token"]


def test_history_requires_auth() -> None:
    client = TestClient(app)
    response = client.get("/api/images/history")
    assert response.status_code == 401


def test_history_returns_empty_list_for_new_admin() -> None:
    client = TestClient(app)
    token = get_token(client)
    response = client.get("/api/images/history", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["items"] == []
