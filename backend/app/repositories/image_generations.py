from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.image_generation import ImageGeneration


def create_image_generation(
    session: Session,
    *,
    user_id: int,
    prompt: str,
    negative_prompt: str | None,
    revised_prompt: str | None,
    model: str,
    responses_model: str,
    size: str,
    quality: str | None,
    mime_type: str,
    storage_path: str,
    file_name: str,
    file_size_bytes: int,
) -> ImageGeneration:
    image = ImageGeneration(
        user_id=user_id,
        prompt=prompt,
        negative_prompt=negative_prompt,
        revised_prompt=revised_prompt,
        model=model,
        responses_model=responses_model,
        size=size,
        quality=quality,
        mime_type=mime_type,
        storage_path=storage_path,
        file_name=file_name,
        file_size_bytes=file_size_bytes,
    )
    session.add(image)
    session.commit()
    session.refresh(image)
    return image


def list_images_for_user(
    session: Session,
    *,
    user_id: int,
    page: int,
    page_size: int,
) -> tuple[list[ImageGeneration], int]:
    total = session.scalar(select(func.count()).select_from(ImageGeneration).where(ImageGeneration.user_id == user_id)) or 0
    offset = max(page - 1, 0) * page_size
    items = list(
        session.scalars(
            select(ImageGeneration)
            .where(ImageGeneration.user_id == user_id)
            .order_by(ImageGeneration.created_at.desc(), ImageGeneration.id.desc())
            .offset(offset)
            .limit(page_size)
        )
    )
    return items, total


def get_image_for_user(session: Session, *, image_id: int, user_id: int) -> ImageGeneration | None:
    return session.scalar(
        select(ImageGeneration).where(
            ImageGeneration.id == image_id,
            ImageGeneration.user_id == user_id,
        )
    )
