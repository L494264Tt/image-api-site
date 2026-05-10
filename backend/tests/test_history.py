from fastapi.testclient import TestClient

from app.main import app
from app.repositories.image_generations import create_image_generation
from app.repositories.users import get_user_by_username


def get_token(client: TestClient) -> str:
    response = client.post("/api/auth/login", json={"username": "admin", "password": "StrongTestAdminPass123!"})
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


def seed_history_image(prompt: str):
    from app.config import get_settings
    from app.db.session import get_session_factory

    session = get_session_factory(get_settings())()
    try:
        user = get_user_by_username(session, "admin")
        assert user is not None
        return create_image_generation(
            session,
            user_id=user.id,
            prompt=prompt,
            negative_prompt=None,
            revised_prompt=None,
            model="gpt-image-2",
            responses_model="gpt-5.4",
            size="1024x1024",
            quality=None,
            mime_type="image/png",
            storage_path="/tmp/test.png",
            file_name="test.png",
            file_size_bytes=8,
        )
    finally:
        session.close()


def test_history_returns_and_filters_asset_organization_fields() -> None:
    client = TestClient(app)
    token = get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    image = seed_history_image("A clean product photo")
    other = seed_history_image("A landscape concept")

    update_response = client.patch(
        f"/api/images/{image.id}/organization",
        headers=headers,
        json={"tags": [" product ", "Launch", "product", ""], "project": " Spring Campaign "},
    )

    assert update_response.status_code == 200
    assert update_response.json()["tags"] == ["product", "Launch"]
    assert update_response.json()["project"] == "Spring Campaign"

    other_update_response = client.patch(
        f"/api/images/{other.id}/organization",
        headers=headers,
        json={"tags": ["landscape"], "project": "Archive"},
    )
    assert other_update_response.status_code == 200

    tag_response = client.get("/api/images/history?tag=product", headers=headers)
    assert tag_response.status_code == 200
    tag_items = tag_response.json()["items"]
    assert [item["id"] for item in tag_items] == [image.id]
    assert tag_items[0]["tags"] == ["product", "Launch"]
    assert tag_items[0]["project"] == "Spring Campaign"

    project_response = client.get("/api/images/history?project=Archive", headers=headers)
    assert project_response.status_code == 200
    project_items = project_response.json()["items"]
    assert [item["id"] for item in project_items] == [other.id]
