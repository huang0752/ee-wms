"""add tenant brand name

Revision ID: 20260628_01
Revises: 20260627_02
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260628_01"
down_revision: str | None = "20260627_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "platform_tenant",
        sa.Column("brand_name", sa.String(length=100), nullable=True, comment="品牌显示名称"),
    )


def downgrade() -> None:
    op.drop_column("platform_tenant", "brand_name")
