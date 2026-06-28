"""add tenant enterprise profile fields

Revision ID: 20260628_02
Revises: 20260628_01
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260628_02"
down_revision: str | None = "20260628_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "platform_tenant",
        sa.Column("social_credit_code", sa.String(length=32), nullable=True, comment="统一社会信用代码"),
    )
    op.add_column(
        "platform_tenant",
        sa.Column("industry", sa.String(length=64), nullable=True, comment="所属行业"),
    )


def downgrade() -> None:
    op.drop_column("platform_tenant", "industry")
    op.drop_column("platform_tenant", "social_credit_code")
