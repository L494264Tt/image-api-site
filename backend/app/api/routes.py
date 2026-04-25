from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.schemas import AppConfigResponse, ModelListResponse, ModelOption

router = APIRouter(prefix="/api")


@router.get("/config", response_model=AppConfigResponse)
async def get_config(settings: Settings = Depends(get_settings)) -> AppConfigResponse:
    return AppConfigResponse(
        siteName=settings.app_name,
        appName=settings.app_name,
        tagLine="OpenAI-compatible image generation through your local backend relay.",
        defaultImagePath="/api/images/generations",
        defaultModel=settings.upstream_model,
        modelOptions=[settings.upstream_model],
        supportedSizes=["1024x1024", "1024x1536", "1536x1024"],
        sizeOptions=["1024x1024", "1024x1536", "1536x1024"],
        qualityOptions=["standard", "high"],
        styleOptions=["vivid", "natural"],
        backgroundOptions=["auto", "transparent", "opaque"],
        supportedResponseFormats=["b64_json"],
        responseFormatOptions=["b64_json"],
        maxImages=1,
    )


@router.get("/models", response_model=ModelListResponse)
async def get_models(settings: Settings = Depends(get_settings)) -> ModelListResponse:
    return ModelListResponse(data=[ModelOption(id=settings.upstream_model, label=settings.upstream_model)])
