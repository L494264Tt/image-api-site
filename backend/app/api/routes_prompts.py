from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.config import Settings, get_settings
from app.errors import UpstreamAPIError
from app.models.user import User
from app.schemas import PromptImproveRequest, PromptImproveResponse
from app.services.openai_images import OpenAIImageService

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


def get_prompt_service(settings: Settings = Depends(get_settings)) -> OpenAIImageService:
    return OpenAIImageService(settings)


@router.post("/improve", response_model=PromptImproveResponse)
async def improve_prompt(
    request: PromptImproveRequest,
    user: User = Depends(get_current_user),
    service: OpenAIImageService = Depends(get_prompt_service),
) -> PromptImproveResponse:
    try:
        improved = await service.improve_prompt(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            model=request.model,
            style=request.style,
        )
    except UpstreamAPIError as exc:
        raise HTTPException(status_code=502, detail="提示词优化暂时不可用，请稍后重试。") from exc

    prompt = improved.get("prompt")
    if not prompt:
        raise HTTPException(status_code=502, detail="提示词优化暂时不可用，请稍后重试。")
    return PromptImproveResponse(prompt=prompt, negative_prompt=improved.get("negative_prompt"))
