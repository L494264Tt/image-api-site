"""add queue persistence, uploads, history flags, and prompt templates

Revision ID: 20260426_02
Revises: 20260422_01
Create Date: 2026-04-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260426_02"
down_revision = "20260422_01"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if column.name not in _columns(table_name):
        op.add_column(table_name, column)


def _create_index_if_missing(index_name: str, table_name: str, columns: list[str]) -> None:
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}
    if index_name not in indexes:
        op.create_index(index_name, table_name, columns)


def _json_payload_type():
    return sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    tables = _table_names()

    if "image_generations" in tables:
        _add_column_if_missing(
            "image_generations",
            sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
        _add_column_if_missing("image_generations", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        _add_column_if_missing("image_generations", sa.Column("requested_model", sa.String(length=64), nullable=True))
        _add_column_if_missing("image_generations", sa.Column("endpoint_type", sa.String(length=64), nullable=True))

    if "generation_jobs" not in tables:
        op.create_table(
            "generation_jobs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("image_generation_id", sa.Integer(), sa.ForeignKey("image_generations.id"), nullable=True),
            sa.Column("prompt", sa.Text(), nullable=False),
            sa.Column("negative_prompt", sa.Text(), nullable=True),
            sa.Column("model", sa.String(length=64), nullable=False),
            sa.Column("size", sa.String(length=32), nullable=False),
            sa.Column("quality", sa.String(length=32), nullable=True),
            sa.Column("request_payload", _json_payload_type(), nullable=False, server_default="{}"),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
            sa.Column("progress_message", sa.String(length=255), nullable=False, server_default="Queued"),
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="2"),
            sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("locked_by", sa.String(length=128), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("error_code", sa.String(length=64), nullable=True),
            sa.Column("error_category", sa.String(length=64), nullable=True),
            sa.Column("raw_error_message", sa.Text(), nullable=True),
            sa.Column("effective_model", sa.String(length=64), nullable=True),
            sa.Column("endpoint_type", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        )
    else:
        _add_column_if_missing("generation_jobs", sa.Column("request_payload", _json_payload_type(), nullable=False, server_default="{}"))
        _add_column_if_missing("generation_jobs", sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"))
        _add_column_if_missing("generation_jobs", sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="2"))
        _add_column_if_missing("generation_jobs", sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True))
        _add_column_if_missing("generation_jobs", sa.Column("locked_by", sa.String(length=128), nullable=True))
        _add_column_if_missing("generation_jobs", sa.Column("error_code", sa.String(length=64), nullable=True))
        _add_column_if_missing("generation_jobs", sa.Column("error_category", sa.String(length=64), nullable=True))
        _add_column_if_missing("generation_jobs", sa.Column("raw_error_message", sa.Text(), nullable=True))
        _add_column_if_missing("generation_jobs", sa.Column("effective_model", sa.String(length=64), nullable=True))
        _add_column_if_missing("generation_jobs", sa.Column("endpoint_type", sa.String(length=64), nullable=True))

    _create_index_if_missing("ix_generation_jobs_user_id", "generation_jobs", ["user_id"])
    _create_index_if_missing("ix_generation_jobs_status", "generation_jobs", ["status"])
    _create_index_if_missing("ix_generation_jobs_created_at", "generation_jobs", ["created_at"])

    if "uploads" not in _table_names():
        op.create_table(
            "uploads",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("mime_type", sa.String(length=64), nullable=False),
            sa.Column("storage_path", sa.Text(), nullable=False),
            sa.Column("file_name", sa.String(length=255), nullable=False),
            sa.Column("original_name", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
            sa.Column("sha256", sa.String(length=64), nullable=False),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        )
    _create_index_if_missing("ix_uploads_user_id", "uploads", ["user_id"])
    _create_index_if_missing("ix_uploads_sha256", "uploads", ["sha256"])
    _create_index_if_missing("ix_uploads_created_at", "uploads", ["created_at"])

    if "prompt_templates" not in _table_names():
        op.create_table(
            "prompt_templates",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("title", sa.String(length=120), nullable=False),
            sa.Column("description", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("category", sa.String(length=64), nullable=False, server_default="general"),
            sa.Column("prompt", sa.Text(), nullable=False),
            sa.Column("negative_prompt", sa.Text(), nullable=False, server_default=""),
            sa.Column("variables", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    _create_index_if_missing("ix_prompt_templates_user_id", "prompt_templates", ["user_id"])
    _create_index_if_missing("ix_prompt_templates_category", "prompt_templates", ["category"])
    _create_index_if_missing("ix_prompt_templates_created_at", "prompt_templates", ["created_at"])


def downgrade() -> None:
    for index_name, table_name in [
        ("ix_prompt_templates_created_at", "prompt_templates"),
        ("ix_prompt_templates_category", "prompt_templates"),
        ("ix_prompt_templates_user_id", "prompt_templates"),
        ("ix_uploads_created_at", "uploads"),
        ("ix_uploads_sha256", "uploads"),
        ("ix_uploads_user_id", "uploads"),
        ("ix_generation_jobs_created_at", "generation_jobs"),
        ("ix_generation_jobs_status", "generation_jobs"),
        ("ix_generation_jobs_user_id", "generation_jobs"),
    ]:
        if table_name in _table_names() and index_name in {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}:
            op.drop_index(index_name, table_name=table_name)

    for table_name in ["prompt_templates", "uploads", "generation_jobs"]:
        if table_name in _table_names():
            op.drop_table(table_name)

    if "image_generations" in _table_names():
        columns = _columns("image_generations")
        if "deleted_at" in columns:
            op.drop_column("image_generations", "deleted_at")
        if "is_favorite" in columns:
            op.drop_column("image_generations", "is_favorite")
