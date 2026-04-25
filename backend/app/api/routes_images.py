from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.config import Settings, get_settings
from app.errors import UpstreamAPIError
from app.models.user import User
from app.repositories.image_generations import create_image_generation, get_image_for_user, list_images_for_user
from app.schemas import ImageGenerationRequest, ImageGenerationResponse, ImageHistoryItem, ImageHistoryResponse
from app.services.image_storage import delete_image_file, save_base64_image
from app.services.openai_images import OpenAIImageService

router = APIRouter(prefix="/api/images", tags=["images"])


def get_image_service(settings: Settings = Depends(get_settings)) -> OpenAIImageService:
    return OpenAIImageService(settings)


@router.post("/generations", response_model=ImageGenerationResponse)
async def create_image(
    request: ImageGenerationRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    service: OpenAIImageService = Depends(get_image_service),
) -> ImageGenerationResponse:
    try:
        data = await service.generate_image(request)
    except UpstreamAPIError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "message": exc.message,
                "type": "upstream_error",
                "status_code": exc.status_code,
            },
        ) from exc

    image = data["data"][0]
    encoded = image.get("b64_json")
    if not encoded:
        raise HTTPException(status_code=502, detail="Upstream response did not include an image")

    created_at = datetime.fromtimestamp(data["created"], tz=timezone.utc)
    saved = save_base64_image(
        base_dir=settings.image_storage_dir,
        user_id=user.id,
        created_at=created_at,
        encoded_image=encoded,
        mime_type=image.get("mime_type") or "image/png",
    )
    try:
        record = create_image_generation(
            session,
            user_id=user.id,
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            revised_prompt=image.get("revised_prompt"),
            model=request.model or settings.upstream_model,
            responses_model=settings.upstream_responses_model,
            size=request.size,
            quality=request.quality,
            mime_type=saved.mime_type,
            storage_path=str(saved.absolute_path),
            file_name=saved.file_name,
            file_size_bytes=saved.file_size_bytes,
        )
    except Exception:
        delete_image_file(str(saved.absolute_path))
        raise

    return ImageGenerationResponse(
        created=data["created"],
        data=[
            {
                "url": f"/api/images/{record.id}/file",
                "b64_json": None,
                "mime_type": saved.mime_type,
                "revised_prompt": image.get("revised_prompt"),
            }
        ],
    )


@router.get("/history", response_model=ImageHistoryResponse)
def history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ImageHistoryResponse:
    items, total = list_images_for_user(session, user_id=user.id, page=page, page_size=page_size)
    return ImageHistoryResponse(
        items=[
            ImageHistoryItem(
                id=item.id,
                prompt=item.prompt,
                revised_prompt=item.revised_prompt,
                model=item.model,
                size=item.size,
                mime_type=item.mime_type,
                image_url=f"/api/images/{item.id}/file",
                created_at=item.created_at,
            )
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{image_id}", response_model=ImageHistoryItem)
def image_detail(
    image_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ImageHistoryItem:
    item = get_image_for_user(session, image_id=image_id, user_id=user.id)
    if item is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return ImageHistoryItem(
        id=item.id,
        prompt=item.prompt,
        revised_prompt=item.revised_prompt,
        model=item.model,
        size=item.size,
        mime_type=item.mime_type,
        image_url=f"/api/images/{item.id}/file",
        created_at=item.created_at,
    )


@router.get("/{image_id}/file")
def image_file(
    image_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> FileResponse:
    item = get_image_for_user(session, image_id=image_id, user_id=user.id)
    if item is None:
        raise HTTPException(status_code=404, detail="Image not found")

    file_path = Path(item.storage_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image file missing")

    return FileResponse(path=file_path, media_type=item.mime_type, filename=item.file_name)
