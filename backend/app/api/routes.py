from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.config import Settings, get_settings
from app.model_capabilities import DEFAULT_BACKGROUNDS, DEFAULT_INPUT_FIDELITIES, DEFAULT_QUALITIES, DEFAULT_SIZES, capability_for_model
from app.models.prompt_template import PromptTemplate
from app.models.user import User
from app.schemas import AppConfigResponse, FavoriteRequest, ModelCapability, ModelListResponse, ModelOption, PromptTemplateRequest, PromptTemplateResponse

router = APIRouter(prefix="/api")

SYSTEM_PROMPT_TEMPLATES = [
    PromptTemplateResponse(
        title="产品海报",
        description="适合电商主图和发布海报",
        category="商业",
        prompt="高端消费电子产品的商业海报，产品居中摆放，柔和棚拍布光，干净背景，细节锐利，真实材质，专业广告摄影，4K",
        negative_prompt="低清晰度，文字水印，变形，杂乱背景，过曝，廉价质感",
        variables=["产品名", "材质", "背景"],
        is_system=True,
    ),
    PromptTemplateResponse(
        title="人物肖像",
        description="适合头像、角色和宣传图",
        category="人物",
        prompt="半身人物肖像，电影感侧逆光，自然皮肤质感，浅景深，情绪稳定，背景简洁，专业人像摄影，细节丰富",
        negative_prompt="多余手指，五官扭曲，塑料皮肤，模糊，水印，过度磨皮",
        variables=["人物", "情绪", "光线"],
        is_system=True,
    ),
    PromptTemplateResponse(
        title="室内空间",
        description="适合家装和建筑氛围图",
        category="空间",
        prompt="现代室内客厅设计，晨光从大窗洒入，木质和织物材质，整洁构图，真实建筑摄影，温暖但不过饱和",
        negative_prompt="透视错误，家具变形，杂乱，低清晰度，过度广角，水印",
        variables=["空间", "风格", "时间"],
        is_system=True,
    ),
    PromptTemplateResponse(
        title="插画场景",
        description="适合封面和故事画面",
        category="插画",
        prompt="温暖的故事书插画场景，傍晚街角的小咖啡店，窗内灯光柔和，人物自然互动，丰富细节，统一色彩，精致构图",
        negative_prompt="脏乱线条，比例错误，文字，水印，过饱和，低质量",
        variables=["场景", "风格", "时间"],
        is_system=True,
    ),
]


@router.get("/config", response_model=AppConfigResponse)
async def get_config(settings: Settings = Depends(get_settings)) -> AppConfigResponse:
    image_models = settings.image_model_list()
    capabilities = [capability_for_model(model) for model in image_models]
    return AppConfigResponse(
        siteName=settings.app_name,
        appName=settings.app_name,
        tagLine="OpenAI-compatible image generation through your local backend relay.",
        defaultImagePath="/api/images/generations",
        defaultModel=settings.upstream_model,
        modelOptions=image_models,
        supportedSizes=DEFAULT_SIZES,
        sizeOptions=DEFAULT_SIZES,
        qualityOptions=DEFAULT_QUALITIES,
        styleOptions=["vivid", "natural"],
        backgroundOptions=DEFAULT_BACKGROUNDS,
        inputFidelityOptions=DEFAULT_INPUT_FIDELITIES,
        maxImages=1,
        modelCapabilities=[
            ModelCapability(
                id=capability.id,
                label=capability.label,
                sizes=capability.sizes,
                qualities=capability.qualities,
                backgrounds=capability.backgrounds,
                supports_text_to_image=capability.supports_text_to_image,
                supports_image_to_image=capability.supports_image_to_image,
                supports_image_input=capability.supports_image_to_image,
                default_endpoint=capability.default_endpoint,
                input_fidelities=capability.input_fidelities,
                supports_transparent_background=capability.supports_transparent_background,
                estimated_seconds=capability.estimated_seconds,
            )
            for capability in capabilities
        ],
    )


@router.get("/models", response_model=ModelListResponse)
async def get_models(settings: Settings = Depends(get_settings)) -> ModelListResponse:
    return ModelListResponse(
        data=[ModelOption(id=model, label=model) for model in settings.image_model_list()],
    )


def template_response(template: PromptTemplate) -> PromptTemplateResponse:
    return PromptTemplateResponse(
        id=template.id,
        title=template.title,
        description=template.description,
        category=template.category,
        prompt=template.prompt,
        negative_prompt=template.negative_prompt,
        variables=[item.strip() for item in template.variables.split(",") if item.strip()],
        is_favorite=template.is_favorite,
        is_system=template.is_system,
    )


@router.get("/prompt-templates", response_model=list[PromptTemplateResponse])
def list_prompt_templates(
    category: str | None = None,
    favorite: bool | None = None,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[PromptTemplateResponse]:
    query = select(PromptTemplate).where(or_(PromptTemplate.user_id == user.id, PromptTemplate.user_id.is_(None)))
    if category:
        query = query.where(PromptTemplate.category == category)
    if favorite is not None:
        query = query.where(PromptTemplate.is_favorite.is_(favorite))
    user_templates = [template_response(item) for item in session.scalars(query.order_by(PromptTemplate.created_at.desc()))]
    system_templates = SYSTEM_PROMPT_TEMPLATES if favorite is not True else []
    if category:
        system_templates = [item for item in system_templates if item.category == category]
    return [*system_templates, *user_templates]


@router.post("/prompt-templates", response_model=PromptTemplateResponse)
def create_prompt_template(
    request: PromptTemplateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> PromptTemplateResponse:
    template = PromptTemplate(
        user_id=user.id,
        title=request.title,
        description=request.description,
        category=request.category,
        prompt=request.prompt,
        negative_prompt=request.negative_prompt,
        variables=",".join(request.variables),
        is_favorite=request.is_favorite,
        is_system=False,
    )
    session.add(template)
    session.commit()
    session.refresh(template)
    return template_response(template)


@router.delete("/prompt-templates/{template_id}")
def delete_prompt_template(
    template_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> dict[str, bool]:
    template = session.scalar(select(PromptTemplate).where(PromptTemplate.id == template_id, PromptTemplate.user_id == user.id))
    if template is None:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    session.delete(template)
    session.commit()
    return {"success": True}


@router.patch("/prompt-templates/{template_id}/favorite", response_model=PromptTemplateResponse)
def favorite_prompt_template(
    template_id: int,
    request: FavoriteRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> PromptTemplateResponse:
    template = session.scalar(select(PromptTemplate).where(PromptTemplate.id == template_id, PromptTemplate.user_id == user.id))
    if template is None:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    template.is_favorite = request.is_favorite
    session.commit()
    session.refresh(template)
    return template_response(template)
