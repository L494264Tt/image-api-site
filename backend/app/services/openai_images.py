import json
import time
from typing import Any

import httpx

from app.config import Settings
from app.errors import UpstreamAPIError
from app.schemas import ImageGenerationRequest


class OpenAIImageService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def generate_image(self, request: ImageGenerationRequest) -> dict[str, Any]:
        payload = self._build_responses_payload(request)
        endpoint = f"{self.settings.upstream_base_url.rstrip('/')}{self.settings.upstream_image_path}"
        headers = {
            "Authorization": f"Bearer {self.settings.upstream_api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.settings.upstream_timeout_seconds) as client:
                async with client.stream("POST", endpoint, headers=headers, json=payload) as response:
                    if response.status_code >= 400:
                        body = await response.aread()
                        raise UpstreamAPIError(
                            self._extract_error_message(body) or "Upstream request failed",
                            status_code=response.status_code,
                        )

                    return await self._parse_responses_stream(response)

        except httpx.TimeoutException as exc:
            raise UpstreamAPIError("Upstream request timed out", status_code=504) from exc
        except httpx.HTTPError as exc:
            raise UpstreamAPIError("Failed to contact upstream service", status_code=502) from exc

    def _build_responses_payload(self, request: ImageGenerationRequest) -> dict[str, Any]:
        prompt = request.prompt.strip()
        if request.negative_prompt:
            prompt = f"{prompt}\n\nAvoid: {request.negative_prompt.strip()}"
        if request.style:
            prompt = f"{prompt}\n\nPreferred style: {request.style}."

        tool: dict[str, Any] = {
            "type": "image_generation",
            "model": request.model or self.settings.upstream_model,
            "size": request.size,
        }
        if request.quality == "high":
            tool["quality"] = "high"
        if request.background and request.background != "auto":
            tool["background"] = request.background

        return {
            "model": self.settings.upstream_responses_model,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt,
                        }
                    ],
                }
            ],
            "tools": [tool],
            "stream": True,
        }

    async def _parse_responses_stream(self, response: httpx.Response) -> dict[str, Any]:
        created = int(time.time())
        images_by_index: dict[int, dict[str, str | None]] = {}
        latest_image: str | None = None
        latest_revised_prompt: str | None = None

        async for line in response.aiter_lines():
            if not line.startswith("data: "):
                continue

            data = line.removeprefix("data: ").strip()
            if not data or data == "[DONE]":
                continue

            try:
                event = json.loads(data)
            except json.JSONDecodeError:
                continue

            event_type = event.get("type")
            if event_type == "response.created":
                event_created = event.get("response", {}).get("created_at")
                if isinstance(event_created, int):
                    created = event_created
            elif event_type == "response.failed":
                message = (
                    event.get("response", {})
                    .get("error", {})
                    .get("message")
                    or "Upstream image generation failed"
                )
                raise UpstreamAPIError(str(message), status_code=502)
            elif event_type == "response.image_generation_call.partial_image":
                image = event.get("partial_image_b64") or event.get("delta")
                index = event.get("partial_image_index", 0)
                if isinstance(image, str) and image:
                    latest_image = image
                    if not isinstance(index, int):
                        index = 0
                    images_by_index[index] = {
                        "b64_json": image,
                        "revised_prompt": latest_revised_prompt,
                    }
            elif event_type == "response.output_item.done":
                item = event.get("item") or {}
                if item.get("type") != "image_generation_call":
                    continue

                image = item.get("result")
                revised_prompt = item.get("revised_prompt")
                if isinstance(revised_prompt, str) and revised_prompt:
                    latest_revised_prompt = revised_prompt
                if isinstance(image, str) and image:
                    latest_image = image
                    images_by_index[0] = {
                        "b64_json": image,
                        "revised_prompt": latest_revised_prompt,
                    }

        if not images_by_index and latest_image:
            images_by_index[0] = {
                "b64_json": latest_image,
                "revised_prompt": latest_revised_prompt,
            }

        data = [
            {
                "b64_json": item["b64_json"],
                "url": None,
                "revised_prompt": item.get("revised_prompt"),
                "mime_type": "image/png",
            }
            for _, item in sorted(images_by_index.items())
            if item.get("b64_json")
        ]
        if not data:
            raise UpstreamAPIError("Upstream response did not include an image", status_code=502)

        return {"created": created, "data": data}

    def _extract_error_message(self, body: bytes) -> str | None:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return None

        if not isinstance(payload, dict):
            return None

        error = payload.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return error["message"]
        if isinstance(payload.get("detail"), str):
            return payload["detail"]
        return None
