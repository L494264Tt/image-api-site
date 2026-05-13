from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    image_generation_id: Mapped[int | None] = mapped_column(ForeignKey("image_generations.id"), nullable=True)
    prompt: Mapped[str] = mapped_column(Text)
    negative_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str] = mapped_column(String(64))
    size: Mapped[str] = mapped_column(String(32))
    quality: Mapped[str | None] = mapped_column(String(32), nullable=True)
    request_payload: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=dict)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    progress_message: Mapped[str] = mapped_column(String(255), default="Queued")
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=2)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    endpoint_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
