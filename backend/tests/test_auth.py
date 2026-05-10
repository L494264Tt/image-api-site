from fastapi.testclient import TestClient

from app.main import app


def auth_headers(client: TestClient, username: str = "admin", password: str = "StrongTestAdminPass123!") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


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


def test_current_user_can_change_password() -> None:
    client = TestClient(app)
    headers = auth_headers(client)

    response = client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"current_password": "StrongTestAdminPass123!", "new_password": "NewStrongPass123!"},
    )
    assert response.status_code == 200
    assert response.json() == {"success": True}

    old_login = client.post("/api/auth/login", json={"username": "admin", "password": "StrongTestAdminPass123!"})
    assert old_login.status_code == 401

    new_login = client.post("/api/auth/login", json={"username": "admin", "password": "NewStrongPass123!"})
    assert new_login.status_code == 200


def test_change_password_rejects_wrong_current_password() -> None:
    client = TestClient(app)
    headers = auth_headers(client)

    response = client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"current_password": "wrong-password", "new_password": "NewStrongPass123!"},
    )

    assert response.status_code == 400


def test_admin_can_create_list_disable_and_enable_user() -> None:
    client = TestClient(app)
    headers = auth_headers(client)

    create_response = client.post(
        "/api/admin/users",
        headers=headers,
        json={"username": "editor", "password": "EditorStrongPass123!", "role": "user"},
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["username"] == "editor"
    assert created["role"] == "user"
    assert created["is_active"] is True
    assert created["last_login_at"] is None
    assert "password" not in created
    assert "password_hash" not in created

    list_response = client.get("/api/admin/users", headers=headers)
    assert list_response.status_code == 200
    usernames = [user["username"] for user in list_response.json()]
    assert usernames == ["admin", "editor"]

    disable_response = client.patch(
        f"/api/admin/users/{created['id']}/status",
        headers=headers,
        json={"is_active": False},
    )
    assert disable_response.status_code == 200
    assert disable_response.json()["is_active"] is False

    disabled_login = client.post("/api/auth/login", json={"username": "editor", "password": "EditorStrongPass123!"})
    assert disabled_login.status_code == 403

    enable_response = client.patch(
        f"/api/admin/users/{created['id']}/status",
        headers=headers,
        json={"is_active": True},
    )
    assert enable_response.status_code == 200
    assert enable_response.json()["is_active"] is True

    enabled_login = client.post("/api/auth/login", json={"username": "editor", "password": "EditorStrongPass123!"})
    assert enabled_login.status_code == 200


def test_admin_user_create_rejects_duplicate_username() -> None:
    client = TestClient(app)
    headers = auth_headers(client)

    response = client.post(
        "/api/admin/users",
        headers=headers,
        json={"username": "admin", "password": "AnotherStrongPass123!", "role": "admin"},
    )

    assert response.status_code == 409


def test_admin_routes_reject_non_admin_user() -> None:
    client = TestClient(app)
    admin_headers = auth_headers(client)
    client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={"username": "editor", "password": "EditorStrongPass123!", "role": "user"},
    )
    user_headers = auth_headers(client, username="editor", password="EditorStrongPass123!")

    response = client.get("/api/admin/users", headers=user_headers)

    assert response.status_code == 403


def test_admin_cannot_disable_self() -> None:
    client = TestClient(app)
    headers = auth_headers(client)

    response = client.patch("/api/admin/users/1/status", headers=headers, json={"is_active": False})

    assert response.status_code == 400
