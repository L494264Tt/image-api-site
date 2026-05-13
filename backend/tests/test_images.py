import asyncio
import base64
import httpx
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.config import get_settings
from app.db.session import get_session_factory
from app.main import app
from app.repositories.generation_jobs import create_generation_job
from app.repositories.users import create_user
from app.services.generation_runner import run_generation_job
from app.services.auth import hash_password
from app.services.openai_images import OpenAIImageService


def test_get_config_returns_frontend_bootstrap_data() -> None:
    client = TestClient(app)

    response = client.get("/api/config")

    assert response.status_code == 200
    assert response.json()["siteName"] == "Image API Site Backend Test"
    assert "1024x1024" in response.json()["supportedSizes"]
    assert response.json()["styleOptions"] == ["vivid", "natural"]
    assert response.json()["inputFidelityOptions"] == ["auto", "low", "high"]
    assert response.json()["maxImages"] == 1
    assert response.json()["modelCapabilities"][0]["supports_image_to_image"] is True


def test_get_models_returns_backend_defined_model() -> None:
    client = TestClient(app)

    response = client.get("/api/models")

    assert response.status_code == 200
    assert response.json() == {
        "data": [
            {
                "id": "gpt-image-2",
                "label": "gpt-image-2",
            }
        ]
    }


def test_post_images_generations_proxies_upstream_response() -> None:
    client = TestClient(app)
    login = client.post("/api/auth/login", json={"username": "admin", "password": "StrongTestAdminPass123!"})
    token = login.json()["access_token"]
    payload = {
        "prompt": "A cinematic fox in a snowy forest",
        "negative_prompt": "blurry",
        "model": "gpt-image-2",
        "size": "1024x1024",
        "n": 1,
        "quality": "high",
        "style": "vivid",
    }

    mocked_response = {
        "created": 1234567890,
        "data": [
            {
                "url": None,
                "b64_json": base64.b64encode(b"fake-png").decode(),
                "mime_type": "image/png",
                "revised_prompt": "A cinematic fox in a snowy forest",
            }
        ],
    }

    with patch("app.api.routes_images.OpenAIImageService.generate_image", new=AsyncMock(return_value=mocked_response)):
        response = client.post(
            "/api/images/generations",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["created"] == 1234567890
    assert body["data"][0]["url"].startswith("/api/images/")
    assert body["data"][0]["b64_json"] is None
    assert body["data"][0]["mime_type"] == "image/png"


def test_build_responses_payload_uses_image_generation_tool() -> None:
    service = OpenAIImageService(get_settings())
    payload = service._build_responses_payload(
        request=service_request(
            prompt="A cinematic fox in a snowy forest",
            negative_prompt="blurry",
            quality="high",
        )
    )

    assert payload["model"] == "gpt-5.4"
    assert payload["stream"] is True
    assert payload["tools"] == [
        {
            "type": "image_generation",
            "model": "gpt-image-2",
            "size": "1024x1024",
            "quality": "high",
        }
    ]
    assert payload["input"][0]["content"][0]["type"] == "input_text"
    assert "Avoid: blurry" in payload["input"][0]["content"][0]["text"]


def test_build_responses_payload_includes_reference_images() -> None:
    service = OpenAIImageService(get_settings())
    payload = service._build_responses_payload(
        request=service_request(
            prompt="Keep the product, change the background to a marble studio",
            input_fidelity="high",
            reference_images=[
                {
                    "data_url": "data:image/png;base64,ZmFrZQ==",
                    "mime_type": "image/png",
                    "name": "product.png",
                }
            ],
        )
    )

    content = payload["input"][0]["content"]
    assert content[0]["type"] == "input_text"
    assert content[1] == {
        "type": "input_image",
        "image_url": "data:image/png;base64,ZmFrZQ==",
    }
    assert payload["tools"][0]["input_fidelity"] == "high"
    assert payload["tools"][0]["action"] == "edit"


def test_build_edit_form_data_includes_edit_options() -> None:
    service = OpenAIImageService(get_settings())

    form_data = service._build_edit_form_data(
        service_request(
            prompt="Keep the product, change the background to a marble studio",
            quality="high",
            background="transparent",
            input_fidelity="high",
            reference_images=[
                {
                    "data_url": "data:image/png;base64,ZmFrZQ==",
                    "mime_type": "image/png",
                    "name": "product.png",
                }
            ],
        )
    )

    assert form_data["model"] == "gpt-image-2"
    assert form_data["quality"] == "high"
    assert form_data["background"] == "transparent"
    assert form_data["input_fidelity"] == "high"


def test_parse_responses_stream_extracts_image_generation_result() -> None:
    service = OpenAIImageService(get_settings())
    body = "\n".join(
        [
            'data: {"type":"response.created","response":{"created_at":1234567890}}',
            'data: {"type":"response.image_generation_call.partial_image","partial_image_index":0,"partial_image_b64":"YWJj"}',
            'data: {"type":"response.output_item.done","item":{"type":"image_generation_call","result":"ZGVm","revised_prompt":"A sharper fox"}}',
            "data: [DONE]",
        ]
    )
    response = httpx.Response(200, content=body.encode())

    parsed = asyncio.run(service._parse_responses_stream(response))

    assert parsed == {
        "created": 1234567890,
        "data": [
            {
                "url": None,
                "b64_json": "ZGVm",
                "revised_prompt": "A sharper fox",
                "mime_type": "image/png",
            }
        ],
    }


def test_generated_image_is_saved_to_history() -> None:
    client = TestClient(app)
    token = client.post("/api/auth/login", json={"username": "admin", "password": "StrongTestAdminPass123!"}).json()["access_token"]
    payload = {
        "prompt": "A cinematic fox in a snowy forest",
        "model": "gpt-image-2",
        "size": "1024x1024",
    }
    mocked_response = {
        "created": 1234567890,
        "data": [
            {
                "url": None,
                "b64_json": base64.b64encode(b"fake-png").decode(),
                "mime_type": "image/png",
                "revised_prompt": "A cinematic fox in a snowy forest",
            }
        ],
    }

    with patch("app.api.routes_images.OpenAIImageService.generate_image", new=AsyncMock(return_value=mocked_response)):
        create_response = client.post(
            "/api/images/generations",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

    assert create_response.status_code == 200

    history_response = client.get("/api/images/history", headers={"Authorization": f"Bearer {token}"})
    assert history_response.status_code == 200
    items = history_response.json()["items"]
    assert len(items) == 1
    assert items[0]["prompt"] == payload["prompt"]


def test_generations_rejects_multiple_images_until_persistence_supports_them() -> None:
    client = TestClient(app)
    token = client.post("/api/auth/login", json={"username": "admin", "password": "StrongTestAdminPass123!"}).json()["access_token"]

    response = client.post(
        "/api/images/generations",
        json={"prompt": "A cinematic fox in a snowy forest", "size": "1024x1024", "n": 2},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_generation_job_rejects_inline_reference_image_data_url() -> None:
    client = TestClient(app)
    token = client.post("/api/auth/login", json={"username": "admin", "password": "StrongTestAdminPass123!"}).json()["access_token"]

    response = client.post(
        "/api/images/generation-jobs",
        json={
            "prompt": "Use this reference",
            "size": "1024x1024",
            "reference_images": [{"data_url": "data:image/png;base64,ZmFrZQ=="}],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400


def test_generation_job_quota_limits_active_jobs() -> None:
    client = TestClient(app)
    token = client.post("/api/auth/login", json={"username": "admin", "password": "StrongTestAdminPass123!"}).json()["access_token"]

    for index in range(3):
        response = client.post(
            "/api/images/generation-jobs",
            json={"prompt": f"Queued image {index}", "size": "1024x1024"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 202
        assert response.json()["raw_error_message"] is None

    response = client.post(
        "/api/images/generation-jobs",
        json={"prompt": "One too many", "size": "1024x1024"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 429


def test_generation_job_events_requires_short_lived_event_token() -> None:
    client = TestClient(app)
    token = client.post("/api/auth/login", json={"username": "admin", "password": "StrongTestAdminPass123!"}).json()["access_token"]
    create_response = client.post(
        "/api/images/generation-jobs",
        json={"prompt": "Queued image", "size": "1024x1024"},
        headers={"Authorization": f"Bearer {token}"},
    )
    job_id = create_response.json()["id"]

    unauthorized = client.get(f"/api/images/generation-jobs/{job_id}/events?token={token}")

    assert unauthorized.status_code == 401


def test_generation_job_events_streams_owned_job_status() -> None:
    client = TestClient(app)
    token = client.post("/api/auth/login", json={"username": "admin", "password": "StrongTestAdminPass123!"}).json()["access_token"]
    create_response = client.post(
        "/api/images/generation-jobs",
        json={"prompt": "Queued image", "size": "1024x1024"},
        headers={"Authorization": f"Bearer {token}"},
    )
    job_id = create_response.json()["id"]
    event_token_response = client.post(
        f"/api/images/generation-jobs/{job_id}/events-token",
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.get(f"/api/images/generation-jobs/{job_id}/events?token={event_token_response.json()['token']}")

    assert event_token_response.status_code == 200
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: job" in response.text
    assert '"status":"queued"' in response.text


def test_generation_job_events_token_is_user_scoped() -> None:
    client = TestClient(app)
    settings = get_settings()
    session = get_session_factory(settings)()
    try:
        other_user = create_user(
            session,
            username="other",
            password_hash=hash_password("StrongOtherPass123!"),
            role="user",
        )
        other_job = create_generation_job(
            session,
            user_id=other_user.id,
            prompt="Other user job",
            negative_prompt=None,
            model=settings.upstream_model,
            size="1024x1024",
            quality=None,
            request_payload={"prompt": "Other user job", "size": "1024x1024"},
        )
        other_job_id = other_job.id
    finally:
        session.close()
    token = client.post("/api/auth/login", json={"username": "admin", "password": "StrongTestAdminPass123!"}).json()["access_token"]

    response = client.post(
        f"/api/images/generation-jobs/{other_job_id}/events-token",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_generation_job_with_reference_keeps_gpt_image_2_model() -> None:
    client = TestClient(app)
    settings = get_settings()
    session = get_session_factory(settings)()
    try:
        user = create_user(
            session,
            username="reference-owner",
            password_hash=hash_password("StrongOwnerPass123!"),
            role="user",
        )
        job = create_generation_job(
            session,
            user_id=user.id,
            prompt="Edit this product",
            negative_prompt=None,
            model="gpt-image-2",
            size="1024x1024",
            quality=None,
            request_payload={
                "prompt": "Edit this product",
                "model": "gpt-image-2",
                "size": "1024x1024",
                "reference_images": [{"data_url": "data:image/png;base64,ZmFrZQ=="}],
            },
        )
        with patch(
            "app.services.generation_runner.OpenAIImageService.generate_image",
            new=AsyncMock(side_effect=RuntimeError("stop before storage")),
        ):
            asyncio.run(run_generation_job(session=session, job=job, settings=settings))
            session.refresh(job)
            assert job.effective_model == "gpt-image-2"
            assert job.endpoint_type == "images.edits"
    finally:
        session.close()


def test_delete_generation_job_soft_deletes_and_hides_job() -> None:
    client = TestClient(app)
    settings = get_settings()
    session = get_session_factory(settings)()
    try:
        user = create_user(
            session,
            username="job-owner",
            password_hash=hash_password("StrongOwnerPass123!"),
            role="user",
        )
        active_job = create_generation_job(
            session,
            user_id=user.id,
            prompt="Active job",
            negative_prompt=None,
            model=settings.upstream_model,
            size="1024x1024",
            quality=None,
            request_payload={"prompt": "Active job", "size": "1024x1024"},
        )
        active_job_id = active_job.id
    finally:
        session.close()

    token = client.post("/api/auth/login", json={"username": "job-owner", "password": "StrongOwnerPass123!"}).json()["access_token"]

    delete_response = client.delete(
        f"/api/images/generation-jobs/{active_job_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    detail_response = client.get(
        f"/api/images/generation-jobs/{active_job_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    list_response = client.get("/api/images/generation-jobs", headers={"Authorization": f"Bearer {token}"})

    assert delete_response.status_code == 204
    assert detail_response.status_code == 404
    assert list_response.status_code == 200
    assert all(item["id"] != active_job_id for item in list_response.json())


def service_request(**overrides):
    from app.schemas import ImageGenerationRequest

    values = {"prompt": "test", "size": "1024x1024", "n": 1}
    values.update(overrides)
    return ImageGenerationRequest.model_validate(values)
