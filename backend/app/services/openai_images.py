import json
import base64
import time
from typing import Any

import httpx

from app.config import Settings
from app.errors import UpstreamAPIError
from app.schemas import ImageGenerationRequest


class OpenAIImageService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def endpoint_type_for_request(self, request: ImageGenerationRequest) -> str:
        return "images.edits" if any(reference_image.data_url for reference_image in request.reference_images) else "responses"

    async def generate_image(self, request: ImageGenerationRequest) -> dict[str, Any]:
        if any(reference_image.data_url for reference_image in request.reference_images):
            return await self.edit_image(request)

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

    async def edit_image(self, request: ImageGenerationRequest) -> dict[str, Any]:
        endpoint = f"{self.settings.upstream_base_url.rstrip('/')}{self.settings.upstream_image_edit_path}"
        headers = {"Authorization": f"Bearer {self.settings.upstream_api_key}"}
        data = self._build_edit_form_data(request)
        files = self._build_edit_files(request)

        try:
            async with httpx.AsyncClient(timeout=self.settings.upstream_timeout_seconds) as client:
                response = await client.post(endpoint, headers=headers, data=data, files=files)
        except httpx.TimeoutException as exc:
            raise UpstreamAPIError("Upstream request timed out", status_code=504) from exc
        except httpx.HTTPError as exc:
            raise UpstreamAPIError("Failed to contact upstream service", status_code=502) from exc

        if response.status_code >= 400:
            raise UpstreamAPIError(
                self._extract_error_message(response.content) or response.text or "Upstream request failed",
                status_code=response.status_code,
            )

        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise UpstreamAPIError("Upstream response was not valid JSON", status_code=502) from exc

        data_items = []
        for item in payload.get("data", []):
            if not isinstance(item, dict):
                continue
            data_items.append(
                {
                    "url": item.get("url"),
                    "b64_json": item.get("b64_json"),
                    "revised_prompt": item.get("revised_prompt"),
                    "mime_type": "image/png",
                }
            )
        if not data_items:
            raise UpstreamAPIError("Upstream response did not include an image", status_code=502)

        return {"created": int(payload.get("created") or time.time()), "data": data_items}

    def _build_edit_form_data(self, request: ImageGenerationRequest) -> dict[str, str]:
        prompt = request.prompt.strip()
        if request.negative_prompt:
            prompt = f"{prompt}\n\nAvoid: {request.negative_prompt.strip()}"
        if request.style:
            prompt = f"{prompt}\n\nPreferred style: {request.style}."

        data = {
            "model": request.model or self._default_edit_model(),
            "prompt": prompt,
            "size": request.size,
        }
        if request.quality and request.quality != "auto":
            data["quality"] = request.quality
        if request.n:
            data["n"] = str(request.n)
        return data

    def _build_edit_files(self, request: ImageGenerationRequest) -> list[tuple[str, tuple[str, bytes, str]]]:
        files: list[tuple[str, tuple[str, bytes, str]]] = []
        for index, reference_image in enumerate(request.reference_images):
            if not reference_image.data_url:
                continue
            mime_type, raw = self._decode_data_url(reference_image.data_url)
            file_name = reference_image.name or f"reference-{index + 1}.png"
            files.append(("image", (file_name, raw, reference_image.mime_type or mime_type)))
        if not files:
            raise UpstreamAPIError("Reference image was missing", status_code=400)
        return files

    def _decode_data_url(self, data_url: str) -> tuple[str, bytes]:
        if not data_url.startswith("data:") or "," not in data_url:
            raise UpstreamAPIError("Reference image data URL was invalid", status_code=400)
        header, encoded = data_url.split(",", 1)
        mime_type = header.removeprefix("data:").split(";", 1)[0] or "image/png"
        try:
            return mime_type, base64.b64decode(encoded)
        except ValueError as exc:
            raise UpstreamAPIError("Reference image data was invalid", status_code=400) from exc

    def _default_edit_model(self) -> str:
        for model in self.settings.image_model_list():
            if model != self.settings.upstream_model:
                return model
        return self.settings.upstream_model

    def _build_responses_payload(self, request: ImageGenerationRequest) -> dict[str, Any]:
        prompt = request.prompt.strip()
        if request.negative_prompt:
            prompt = f"{prompt}\n\nAvoid: {request.negative_prompt.strip()}"
        if request.style:
            prompt = f"{prompt}\n\nPreferred style: {request.style}."

        content: list[dict[str, Any]] = [
            {
                "type": "input_text",
                "text": prompt,
            }
        ]
        for reference_image in request.reference_images:
            if not reference_image.data_url:
                continue
            content.append(
                {
                    "type": "input_image",
                    "image_url": reference_image.data_url,
                }
            )

        tool: dict[str, Any] = {
            "type": "image_generation",
            "model": request.model or self.settings.upstream_model,
            "size": request.size,
        }
        if request.quality and request.quality != "auto":
            tool["quality"] = request.quality
        if request.background and request.background != "auto":
            tool["background"] = request.background
        if request.reference_images and request.input_fidelity and request.input_fidelity != "auto":
            tool["input_fidelity"] = request.input_fidelity
        if request.reference_images:
            tool["action"] = "edit"

        return {
            "model": self.settings.upstream_responses_model,
            "input": [
                {
                    "role": "user",
                    "content": content,
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
