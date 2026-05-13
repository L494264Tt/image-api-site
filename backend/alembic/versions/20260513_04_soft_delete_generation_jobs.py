"""add soft delete flag to generation jobs

Revision ID: 20260513_04
Revises: 20260510_03
Create Date: 2026-05-13 22:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260513_04"
down_revision: str | None = "20260510_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    if "deleted_at" not in _columns("generation_jobs"):
        op.add_column("generation_jobs", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    if "deleted_at" in _columns("generation_jobs"):
        op.drop_column("generation_jobs", "deleted_at")
