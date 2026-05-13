from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.config import get_settings
from app.errors import UpstreamAPIError
from app.main import app
from app.services.openai_images import OpenAIImageService


def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": "admin", "password": "StrongTestAdminPass123!"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_prompt_improve_requires_auth() -> None:
    client = TestClient(app)

    response = client.post("/api/prompts/improve", json={"prompt": "一杯咖啡"})

    assert response.status_code == 401


def test_prompt_improve_returns_upstream_result() -> None:
    client = TestClient(app)
    headers = auth_headers(client)

    with patch(
        "app.api.routes_prompts.OpenAIImageService.improve_prompt",
        new=AsyncMock(return_value={"prompt": "一杯咖啡，柔和晨光，干净桌面，细节清晰", "negative_prompt": "水印，文字"}),
    ) as mocked_improve:
        response = client.post(
            "/api/prompts/improve",
            headers=headers,
            json={"prompt": "一杯咖啡", "negative_prompt": "模糊", "style": "natural"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "prompt": "一杯咖啡，柔和晨光，干净桌面，细节清晰",
        "negative_prompt": "水印，文字",
    }
    mocked_improve.assert_awaited_once_with(
        prompt="一杯咖啡",
        negative_prompt="模糊",
        model=None,
        style="natural",
    )


def test_prompt_improve_hides_upstream_error_details() -> None:
    client = TestClient(app)
    headers = auth_headers(client)

    with patch(
        "app.api.routes_prompts.OpenAIImageService.improve_prompt",
        new=AsyncMock(side_effect=UpstreamAPIError("raw upstream provider error with account details", status_code=500)),
    ):
        response = client.post("/api/prompts/improve", headers=headers, json={"prompt": "一杯咖啡"})

    assert response.status_code == 502
    assert response.json() == {"detail": "提示词优化暂时不可用，请稍后重试。"}


def test_prompt_improve_uses_json_schema_format() -> None:
    service = OpenAIImageService(get_settings())
    captured = {}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, headers=None, json=None):
            captured["json"] = json

            class FakeResponse:
                status_code = 200

                def json(self):
                    return {"output_text": '{"prompt":"更清晰的咖啡","negative_prompt":null}'}

            return FakeResponse()

    with patch("app.services.openai_images.httpx.AsyncClient", return_value=FakeClient()):
        result = __import__("asyncio").run(service.improve_prompt(prompt="咖啡"))

    assert result == {"prompt": "更清晰的咖啡", "negative_prompt": None}
    assert captured["json"]["text"]["format"]["type"] == "json_schema"
    assert captured["json"]["text"]["format"]["strict"] is True
