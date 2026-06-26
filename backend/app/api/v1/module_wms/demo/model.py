from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin, TenantMixin, UserMixin


class WmsDemoSamplePoolModel(ModelMixin, TenantMixin, UserMixin):
    __tablename__ = "wms_demo_sample_pool"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_wms_demo_pool_tenant_code"), {"comment": "WMS演示数据样本池"})
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by", "tenant_by"]

    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="样本池编码")
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="样本池名称")
    industry: Mapped[str] = mapped_column(String(64), default="electrical_equipment", nullable=False, index=True, comment="行业")
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True, comment="是否系统内置")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True, comment="是否启用")
    base_pool_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("wms_demo_sample_pool.id", ondelete="SET NULL"), default=None, nullable=True, index=True, comment="来源样本池ID")
    prompt_template: Mapped[str | None] = mapped_column(Text, default=None, nullable=True, comment="AI提示词模板")
    fallback_template: Mapped[str | None] = mapped_column(Text, default=None, nullable=True, comment="兜底模板")
    config: Mapped[dict | None] = mapped_column(JSON, default=None, nullable=True, comment="样本池配置")


class WmsDemoSampleItemModel(ModelMixin, TenantMixin, UserMixin):
    __tablename__ = "wms_demo_sample_item"
    __table_args__ = (UniqueConstraint("tenant_id", "pool_id", "item_key", name="uq_wms_demo_item_tenant_pool_key"), {"comment": "WMS演示数据样本项"})
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by", "tenant_by"]

    pool_id: Mapped[int] = mapped_column(Integer, ForeignKey("wms_demo_sample_pool.id", ondelete="CASCADE"), nullable=False, index=True, comment="样本池ID")
    group_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="样本组编码")
    group_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="样本组名称")
    item_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="样本项编码")
    item_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="样本项名称")
    acceptance_scope: Mapped[str | None] = mapped_column(Text, default=None, nullable=True, comment="受理范围")
    spec_patterns: Mapped[list | None] = mapped_column(JSON, default=None, nullable=True, comment="规格模板")
    supplier_patterns: Mapped[list | None] = mapped_column(JSON, default=None, nullable=True, comment="供应商模板")
    material_patterns: Mapped[list | None] = mapped_column(JSON, default=None, nullable=True, comment="物料模板")
    storage_traits: Mapped[list | None] = mapped_column(JSON, default=None, nullable=True, comment="仓储特性")
    quality_traits: Mapped[list | None] = mapped_column(JSON, default=None, nullable=True, comment="质量特性")
    weight: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="权重")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True, comment="是否启用")
