"""create users and image_generations tables

Revision ID: 20260422_01
Revises:
Create Date: 2026-04-22
"""

from alembic import op
import sqlalchemy as sa


revision = "20260422_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "image_generations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("negative_prompt", sa.Text(), nullable=True),
        sa.Column("revised_prompt", sa.Text(), nullable=True),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("responses_model", sa.String(length=64), nullable=False),
        sa.Column("size", sa.String(length=32), nullable=False),
        sa.Column("quality", sa.String(length=32), nullable=True),
        sa.Column("mime_type", sa.String(length=64), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_image_generations_user_id", "image_generations", ["user_id"], unique=False)
    op.create_index("ix_image_generations_created_at", "image_generations", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_image_generations_created_at", table_name="image_generations")
    op.drop_index("ix_image_generations_user_id", table_name="image_generations")
    op.drop_table("image_generations")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
