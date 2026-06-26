"""add wms demo sample pool tables

Revision ID: 20260627_01
Revises:
Create Date: 2026-06-27
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260627_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "wms_demo_sample_pool",
        sa.Column("code", sa.String(length=64), nullable=False, comment="样本池编码"),
        sa.Column("name", sa.String(length=128), nullable=False, comment="样本池名称"),
        sa.Column("industry", sa.String(length=64), nullable=False, comment="行业"),
        sa.Column("is_system", sa.Boolean(), nullable=False, comment="是否系统内置"),
        sa.Column("is_active", sa.Boolean(), nullable=False, comment="是否启用"),
        sa.Column("base_pool_id", sa.Integer(), nullable=True, comment="来源样本池ID"),
        sa.Column("prompt_template", sa.Text(), nullable=True, comment="AI提示词模板"),
        sa.Column("fallback_template", sa.Text(), nullable=True, comment="兜底模板"),
        sa.Column("config", sa.JSON(), nullable=True, comment="样本池配置"),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("uuid", sa.String(length=64), nullable=False, comment="UUID全局唯一标识"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, comment="是否已删除"),
        sa.Column("created_time", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_time", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.Column("deleted_time", sa.DateTime(), nullable=True, comment="删除时间"),
        sa.Column("tenant_id", sa.Integer(), nullable=False, comment="租户ID"),
        sa.Column("created_id", sa.Integer(), nullable=True, comment="创建人ID"),
        sa.Column("updated_id", sa.Integer(), nullable=True, comment="更新人ID"),
        sa.Column("deleted_id", sa.Integer(), nullable=True, comment="删除人ID"),
        sa.ForeignKeyConstraint(["base_pool_id"], ["wms_demo_sample_pool.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["platform_tenant.id"], onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_id"], ["sys_user.id"], onupdate="CASCADE", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_id"], ["sys_user.id"], onupdate="CASCADE", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["deleted_id"], ["sys_user.id"], onupdate="CASCADE", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_wms_demo_pool_tenant_code"),
    )
    op.create_table(
        "wms_demo_sample_item",
        sa.Column("pool_id", sa.Integer(), nullable=False, comment="样本池ID"),
        sa.Column("group_key", sa.String(length=64), nullable=False, comment="样本组编码"),
        sa.Column("group_name", sa.String(length=64), nullable=False, comment="样本组名称"),
        sa.Column("item_key", sa.String(length=64), nullable=False, comment="样本项编码"),
        sa.Column("item_name", sa.String(length=128), nullable=False, comment="样本项名称"),
        sa.Column("acceptance_scope", sa.Text(), nullable=True, comment="受理范围"),
        sa.Column("spec_patterns", sa.JSON(), nullable=True, comment="规格模板"),
        sa.Column("supplier_patterns", sa.JSON(), nullable=True, comment="供应商模板"),
        sa.Column("material_patterns", sa.JSON(), nullable=True, comment="物料模板"),
        sa.Column("storage_traits", sa.JSON(), nullable=True, comment="仓储特性"),
        sa.Column("quality_traits", sa.JSON(), nullable=True, comment="质量特性"),
        sa.Column("weight", sa.Integer(), nullable=False, comment="权重"),
        sa.Column("enabled", sa.Boolean(), nullable=False, comment="是否启用"),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("uuid", sa.String(length=64), nullable=False, comment="UUID全局唯一标识"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, comment="是否已删除"),
        sa.Column("created_time", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_time", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.Column("deleted_time", sa.DateTime(), nullable=True, comment="删除时间"),
        sa.Column("tenant_id", sa.Integer(), nullable=False, comment="租户ID"),
        sa.Column("created_id", sa.Integer(), nullable=True, comment="创建人ID"),
        sa.Column("updated_id", sa.Integer(), nullable=True, comment="更新人ID"),
        sa.Column("deleted_id", sa.Integer(), nullable=True, comment="删除人ID"),
        sa.ForeignKeyConstraint(["pool_id"], ["wms_demo_sample_pool.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["platform_tenant.id"], onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_id"], ["sys_user.id"], onupdate="CASCADE", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_id"], ["sys_user.id"], onupdate="CASCADE", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["deleted_id"], ["sys_user.id"], onupdate="CASCADE", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "pool_id", "item_key", name="uq_wms_demo_item_tenant_pool_key"),
    )


def downgrade() -> None:
    op.drop_table("wms_demo_sample_item")
    op.drop_table("wms_demo_sample_pool")
