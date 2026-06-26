from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin, TenantMixin, UserMixin


class WmsIssueBase(ModelMixin, TenantMixin, UserMixin):
    __abstract__ = True
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by", "tenant_by"]

    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否试用数据")
    demo_batch_id: Mapped[str | None] = mapped_column(String(64), default=None, nullable=True, index=True, comment="试用数据批次")


class WmsIssueOrderModel(WmsIssueBase):
    __tablename__ = "wms_issue_order"
    __table_args__ = (UniqueConstraint("tenant_id", "order_no", name="uq_wms_issue_tenant_no"), {"comment": "WMS生产领料单"})

    order_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="领料单号")
    work_order_no: Mapped[str | None] = mapped_column(String(128), default=None, nullable=True, index=True, comment="生产工单号")
    warehouse_id: Mapped[int] = mapped_column(Integer, ForeignKey("wms_warehouse.id", ondelete="RESTRICT"), nullable=False, index=True, comment="仓库ID")
    status: Mapped[str] = mapped_column(String(32), default="pending_reserve", nullable=False, index=True, comment="状态")
    picked_time: Mapped[datetime | None] = mapped_column(DateTime, default=None, nullable=True, comment="拣货时间")
    reviewed_time: Mapped[datetime | None] = mapped_column(DateTime, default=None, nullable=True, comment="复核时间")
    confirmed_time: Mapped[datetime | None] = mapped_column(DateTime, default=None, nullable=True, comment="确认时间")
    external_source: Mapped[str] = mapped_column(String(32), default="manual", nullable=False, comment="外部来源")
    external_id: Mapped[str | None] = mapped_column(String(128), default=None, nullable=True, index=True, comment="外部ID")
    external_no: Mapped[str | None] = mapped_column(String(128), default=None, nullable=True, index=True, comment="外部单号")
    sync_status: Mapped[str] = mapped_column(String(32), default="not_required", nullable=False, comment="同步状态")
    workflow_instance_id: Mapped[str | None] = mapped_column(String(128), default=None, nullable=True, index=True, comment="流程实例ID")
    remark: Mapped[str | None] = mapped_column(Text, default=None, nullable=True, comment="备注")


class WmsIssueLineModel(WmsIssueBase):
    __tablename__ = "wms_issue_line"
    __table_args__ = ({"comment": "WMS生产领料明细"},)

    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("wms_issue_order.id", ondelete="CASCADE"), nullable=False, index=True, comment="领料单ID")
    material_id: Mapped[int] = mapped_column(Integer, ForeignKey("wms_material.id", ondelete="RESTRICT"), nullable=False, index=True, comment="物料ID")
    warehouse_id: Mapped[int] = mapped_column(Integer, ForeignKey("wms_warehouse.id", ondelete="RESTRICT"), nullable=False, index=True, comment="仓库ID")
    location_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("wms_location.id", ondelete="SET NULL"), default=None, nullable=True, index=True, comment="库位ID")
    batch_no: Mapped[str | None] = mapped_column(String(64), default=None, nullable=True, index=True, comment="批次号")
    requested_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, comment="需求数量")
    locked_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False, comment="锁定数量")
    shipped_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False, comment="领用数量")
    stock_lock_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("wms_stock_lock.id", ondelete="SET NULL"), default=None, nullable=True, index=True, comment="锁库ID")
    status: Mapped[str] = mapped_column(String(32), default="pending_reserve", nullable=False, index=True, comment="状态")
    remark: Mapped[str | None] = mapped_column(Text, default=None, nullable=True, comment="备注")
