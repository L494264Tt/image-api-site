"""add image asset tags and project

Revision ID: 20260510_03
Revises: 20260426_02
Create Date: 2026-05-10
"""

from alembic import op
import sqlalchemy as sa


revision = "20260510_03"
down_revision = "20260426_02"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}


def upgrade() -> None:
    columns = _columns("image_generations")
    if "tags" not in columns:
        op.add_column(
            "image_generations",
            sa.Column("tags", sa.Text(), nullable=False, server_default=""),
        )
    if "project" not in columns:
        op.add_column("image_generations", sa.Column("project", sa.String(length=120), nullable=True))
    if "ix_image_generations_project" not in _indexes("image_generations"):
        op.create_index("ix_image_generations_project", "image_generations", ["project"])


def downgrade() -> None:
    indexes = _indexes("image_generations")
    if "ix_image_generations_project" in indexes:
        op.drop_index("ix_image_generations_project", table_name="image_generations")

    columns = _columns("image_generations")
    if "project" in columns:
        op.drop_column("image_generations", "project")
    if "tags" in columns:
        op.drop_column("image_generations", "tags")
