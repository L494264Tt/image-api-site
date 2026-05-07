from fastapi.testclient import TestClient

from app.main import app


def test_upload_rejects_invalid_image_bytes() -> None:
    client = TestClient(app)
    token = client.post("/api/auth/login", json={"username": "admin", "password": "StrongTestAdminPass123!"}).json()["access_token"]

    response = client.post(
        "/api/uploads",
        files={"file": ("fake.png", b"not actually an image", "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
