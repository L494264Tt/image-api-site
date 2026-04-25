import asyncio
import base64
import httpx
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.services.openai_images import OpenAIImageService


def test_get_config_returns_frontend_bootstrap_data() -> None:
    client = TestClient(app)

    response = client.get("/api/config")

    assert response.status_code == 200
    assert response.json()["siteName"] == "Image API Site Backend Test"
    assert "1024x1024" in response.json()["supportedSizes"]
    assert response.json()["styleOptions"] == ["vivid", "natural"]
    assert response.json()["responseFormatOptions"] == ["b64_json"]
    assert response.json()["maxImages"] == 1


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
    login = client.post("/api/auth/login", json={"username": "admin", "password": "replace-with-a-strong-admin-password"})
    token = login.json()["access_token"]
    payload = {
        "prompt": "A cinematic fox in a snowy forest",
        "negative_prompt": "blurry",
        "model": "gpt-image-2",
        "size": "1024x1024",
        "n": 1,
        "quality": "high",
        "style": "vivid",
        "response_format": "b64_json",
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
    token = client.post("/api/auth/login", json={"username": "admin", "password": "replace-with-a-strong-admin-password"}).json()["access_token"]
    payload = {
        "prompt": "A cinematic fox in a snowy forest",
        "model": "gpt-image-2",
        "size": "1024x1024",
        "response_format": "b64_json",
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


def service_request(**overrides):
    from app.schemas import ImageGenerationRequest

    values = {"prompt": "test", "size": "1024x1024", "n": 1, "response_format": "b64_json"}
    values.update(overrides)
    return ImageGenerationRequest.model_validate(values)
