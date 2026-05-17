from fastapi.testclient import TestClient

from app.main import app
from app.repositories.generation_jobs import create_generation_job, get_generation_job_for_user, mark_job_succeeded
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


def test_bulk_delete_removes_history_and_associated_generation_job() -> None:
    from app.config import get_settings
    from app.db.session import get_session_factory

    client = TestClient(app)
    token = get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    image = seed_history_image("A product render to delete")

    session = get_session_factory(get_settings())()
    try:
        user = get_user_by_username(session, "admin")
        assert user is not None
        job = create_generation_job(
            session,
            user_id=user.id,
            prompt=image.prompt,
            negative_prompt=None,
            model=image.model,
            size=image.size,
            quality=image.quality,
            request_payload={"prompt": image.prompt, "model": image.model, "size": image.size},
        )
        job_id = job.id
        mark_job_succeeded(session, job, image_generation_id=image.id)
    finally:
        session.close()


def test_deleted_history_can_be_listed_and_restored_with_associated_job() -> None:
    from app.config import get_settings
    from app.db.session import get_session_factory

    client = TestClient(app)
    token = get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    image = seed_history_image("A recoverable product render")

    session = get_session_factory(get_settings())()
    try:
        user = get_user_by_username(session, "admin")
        assert user is not None
        job = create_generation_job(
            session,
            user_id=user.id,
            prompt=image.prompt,
            negative_prompt=None,
            model=image.model,
            size=image.size,
            quality=image.quality,
            request_payload={"prompt": image.prompt, "model": image.model, "size": image.size},
        )
        job_id = job.id
        mark_job_succeeded(session, job, image_generation_id=image.id)
    finally:
        session.close()

    delete_response = client.post("/api/images/bulk-delete", headers=headers, json={"image_ids": [image.id]})
    assert delete_response.status_code == 200

    active_response = client.get("/api/images/history", headers=headers)
    assert active_response.status_code == 200
    assert active_response.json()["items"] == []

    trash_response = client.get("/api/images/history?include_deleted=true", headers=headers)
    assert trash_response.status_code == 200
    trash_items = trash_response.json()["items"]
    assert [item["id"] for item in trash_items] == [image.id]
    assert trash_items[0]["deleted_at"] is not None

    restore_response = client.post(f"/api/images/{image.id}/restore", headers=headers)
    assert restore_response.status_code == 200
    assert restore_response.json()["deleted_at"] is None

    restored_history = client.get("/api/images/history", headers=headers)
    assert restored_history.status_code == 200
    assert [item["id"] for item in restored_history.json()["items"]] == [image.id]

    restored_jobs = client.get("/api/images/generation-jobs", headers=headers)
    assert restored_jobs.status_code == 200
    assert any(item["id"] == job_id for item in restored_jobs.json())

    delete_response = client.post("/api/images/bulk-delete", headers=headers, json={"image_ids": [image.id]})

    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] == 1

    history_response = client.get("/api/images/history", headers=headers)
    assert history_response.status_code == 200
    assert history_response.json()["items"] == []

    jobs_response = client.get("/api/images/generation-jobs", headers=headers)
    assert jobs_response.status_code == 200
    assert all(item["id"] != job_id for item in jobs_response.json())

    session = get_session_factory(get_settings())()
    try:
        user = get_user_by_username(session, "admin")
        assert user is not None
        assert get_generation_job_for_user(session, job_id=job_id, user_id=user.id) is None
    finally:
        session.close()
