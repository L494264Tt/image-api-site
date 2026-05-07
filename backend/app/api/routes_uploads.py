from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.config import Settings, get_settings
from app.models.user import User
from app.repositories.uploads import create_upload
from app.schemas import UploadResponse
from app.services.image_storage import normalize_upload_image, save_raw_upload

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_reference_image(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UploadResponse:
    mime_type = file.content_type or ""
    if mime_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="仅支持 PNG、JPEG 或 WebP 图片。")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="上传文件为空。")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="单张参考图不能超过 10MB。")
    raw, mime_type = normalize_upload_image(raw, mime_type)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="单张参考图不能超过 10MB。")

    created_at = datetime.now(timezone.utc)
    saved = save_raw_upload(
        base_dir=settings.image_storage_dir,
        user_id=user.id,
        created_at=created_at,
        raw=raw,
        mime_type=mime_type,
        original_name=file.filename or "",
    )
    record = create_upload(
        session,
        user_id=user.id,
        mime_type=saved.mime_type,
        storage_path=str(saved.absolute_path),
        file_name=saved.file_name,
        original_name=file.filename or "",
        file_size_bytes=saved.file_size_bytes,
        sha256=saved.sha256,
    )
    return UploadResponse(
        id=record.id,
        file_name=record.file_name,
        mime_type=record.mime_type,
        file_size_bytes=record.file_size_bytes,
        created_at=record.created_at,
    )
