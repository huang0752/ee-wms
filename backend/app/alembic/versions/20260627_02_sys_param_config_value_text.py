"""expand sys_param config_value

Revision ID: 20260627_02
Revises: 20260627_01
Create Date: 2026-06-27
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260627_02"
down_revision: str | None = "20260627_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "sys_param",
        "config_value",
        existing_type=sa.String(length=500),
        type_=sa.Text(),
        existing_nullable=True,
        existing_comment="参数键值",
    )


def downgrade() -> None:
    op.alter_column(
        "sys_param",
        "config_value",
        existing_type=sa.Text(),
        type_=sa.String(length=500),
        existing_nullable=True,
        existing_comment="参数键值",
    )
