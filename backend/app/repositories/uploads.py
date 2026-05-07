from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.upload import Upload


def create_upload(
    session: Session,
    *,
    user_id: int,
    mime_type: str,
    storage_path: str,
    file_name: str,
    original_name: str,
    file_size_bytes: int,
    sha256: str,
) -> Upload:
    upload = Upload(
        user_id=user_id,
        mime_type=mime_type,
        storage_path=storage_path,
        file_name=file_name,
        original_name=original_name,
        file_size_bytes=file_size_bytes,
        sha256=sha256,
    )
    session.add(upload)
    session.commit()
    session.refresh(upload)
    return upload


def get_upload_for_user(session: Session, *, upload_id: int, user_id: int) -> Upload | None:
    return session.scalar(
        select(Upload).where(Upload.id == upload_id, Upload.user_id == user_id, Upload.is_deleted.is_(False))
    )


def list_uploads_for_user(session: Session, *, upload_ids: list[int], user_id: int) -> list[Upload]:
    if not upload_ids:
        return []
    return list(
        session.scalars(
            select(Upload).where(Upload.id.in_(upload_ids), Upload.user_id == user_id, Upload.is_deleted.is_(False))
        )
    )


def mark_uploads_used(session: Session, *, upload_ids: list[int], user_id: int) -> None:
    uploads = list_uploads_for_user(session, upload_ids=upload_ids, user_id=user_id)
    now = datetime.now(timezone.utc)
    for upload in uploads:
        upload.used_at = now
    session.commit()


def cleanup_expired_uploads(
    session: Session,
    *,
    unused_after_hours: int = 24,
    used_after_days: int = 7,
) -> int:
    now = datetime.now(timezone.utc)
    unused_cutoff = now - timedelta(hours=unused_after_hours)
    used_cutoff = now - timedelta(days=used_after_days)
    uploads = list(
        session.scalars(
            select(Upload).where(
                Upload.is_deleted.is_(False),
                (
                    ((Upload.used_at.is_(None)) & (Upload.created_at < unused_cutoff))
                    | ((Upload.used_at.is_not(None)) & (Upload.used_at < used_cutoff))
                ),
            )
        )
    )
    for upload in uploads:
        path = Path(upload.storage_path)
        if path.exists():
            path.unlink()
        upload.is_deleted = True
    session.commit()
    return len(uploads)
