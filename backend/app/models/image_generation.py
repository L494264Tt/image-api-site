from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ImageGeneration(Base):
    __tablename__ = "image_generations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    negative_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    revised_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str] = mapped_column(String(64))
    requested_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    endpoint_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    responses_model: Mapped[str] = mapped_column(String(64))
    size: Mapped[str] = mapped_column(String(32))
    quality: Mapped[str | None] = mapped_column(String(32), nullable=True)
    mime_type: Mapped[str] = mapped_column(String(64), default="image/png")
    storage_path: Mapped[str] = mapped_column(Text)
    file_name: Mapped[str] = mapped_column(String(255))
    file_size_bytes: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(32), default="succeeded")
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
