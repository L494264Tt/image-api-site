from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.image_generation import ImageGeneration

TAG_SEPARATOR = "\n"


def normalize_tags(tags: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for tag in tags:
        value = " ".join(tag.strip().split())
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            normalized.append(value[:64])
    return normalized


def encode_tags(tags: list[str]) -> str:
    normalized = normalize_tags(tags)
    if not normalized:
        return ""
    return f"{TAG_SEPARATOR}{TAG_SEPARATOR.join(normalized)}{TAG_SEPARATOR}"


def decode_tags(tags: str | None) -> list[str]:
    if not tags:
        return []
    return [tag.strip() for tag in tags.split(TAG_SEPARATOR) if tag.strip()]


def normalize_project(project: str | None) -> str | None:
    if project is None:
        return None
    value = " ".join(project.strip().split())
    return value[:120] if value else None


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
    requested_model: str | None = None,
    endpoint_type: str | None = None,
) -> ImageGeneration:
    image = ImageGeneration(
        user_id=user_id,
        prompt=prompt,
        negative_prompt=negative_prompt,
        revised_prompt=revised_prompt,
        model=model,
        requested_model=requested_model,
        endpoint_type=endpoint_type,
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
    search: str | None = None,
    model: str | None = None,
    size: str | None = None,
    favorite: bool | None = None,
    tag: str | None = None,
    project: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> tuple[list[ImageGeneration], int]:
    filters = [
        ImageGeneration.user_id == user_id,
        ImageGeneration.deleted_at.is_(None),
    ]
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(or_(ImageGeneration.prompt.ilike(pattern), ImageGeneration.revised_prompt.ilike(pattern)))
    if model:
        filters.append(ImageGeneration.model == model)
    if size:
        filters.append(ImageGeneration.size == size)
    if favorite is not None:
        filters.append(ImageGeneration.is_favorite.is_(favorite))
    if tag:
        normalized_tag = normalize_tags([tag])
        if normalized_tag:
            filters.append(ImageGeneration.tags.ilike(f"%{TAG_SEPARATOR}{normalized_tag[0]}{TAG_SEPARATOR}%"))
    if project:
        normalized_project = normalize_project(project)
        if normalized_project:
            filters.append(ImageGeneration.project == normalized_project)
    if created_from is not None:
        filters.append(ImageGeneration.created_at >= created_from)
    if created_to is not None:
        filters.append(ImageGeneration.created_at <= created_to)

    total = session.scalar(select(func.count()).select_from(ImageGeneration).where(*filters)) or 0
    offset = max(page - 1, 0) * page_size
    items = list(
        session.scalars(
            select(ImageGeneration)
            .where(*filters)
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
            ImageGeneration.deleted_at.is_(None),
        )
    )


def set_image_favorite(session: Session, *, image_id: int, user_id: int, is_favorite: bool) -> ImageGeneration | None:
    image = get_image_for_user(session, image_id=image_id, user_id=user_id)
    if image is None:
        return None
    image.is_favorite = is_favorite
    session.commit()
    session.refresh(image)
    return image


def set_image_organization(
    session: Session,
    *,
    image_id: int,
    user_id: int,
    tags: list[str],
    project: str | None,
) -> ImageGeneration | None:
    image = get_image_for_user(session, image_id=image_id, user_id=user_id)
    if image is None:
        return None
    image.tags = encode_tags(tags)
    image.project = normalize_project(project)
    session.commit()
    session.refresh(image)
    return image


def soft_delete_images_for_user(session: Session, *, image_ids: list[int], user_id: int) -> int:
    if not image_ids:
        return 0
    items = list(
        session.scalars(
            select(ImageGeneration).where(
                ImageGeneration.id.in_(image_ids),
                ImageGeneration.user_id == user_id,
                ImageGeneration.deleted_at.is_(None),
            )
        )
    )
    now = datetime.now(timezone.utc)
    for item in items:
        item.deleted_at = now
    session.commit()
    return len(items)
