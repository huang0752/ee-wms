from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin, TenantMixin, UserMixin


class WmsArrivalBase(ModelMixin, TenantMixin, UserMixin):
    __abstract__ = True
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by", "tenant_by"]

    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否试用数据")
    demo_batch_id: Mapped[str | None] = mapped_column(String(64), default=None, nullable=True, index=True, comment="试用数据批次")


class WmsArrivalOrderModel(WmsArrivalBase):
    __tablename__ = "wms_arrival_order"
    __table_args__ = (UniqueConstraint("tenant_id", "order_no", name="uq_wms_arrival_tenant_no"), {"comment": "WMS到货单"})

    order_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="到货单号")
    supplier_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("wms_supplier.id", ondelete="SET NULL"), default=None, nullable=True, index=True, comment="供应商ID")
    warehouse_id: Mapped[int] = mapped_column(Integer, ForeignKey("wms_warehouse.id", ondelete="RESTRICT"), nullable=False, index=True, comment="仓库ID")
    status: Mapped[str] = mapped_column(String(32), default="pending_receive", nullable=False, index=True, comment="状态")
    expected_time: Mapped[datetime | None] = mapped_column(DateTime, default=None, nullable=True, comment="预计到货时间")
    received_time: Mapped[datetime | None] = mapped_column(DateTime, default=None, nullable=True, comment="收货时间")
    external_source: Mapped[str] = mapped_column(String(32), default="manual", nullable=False, comment="外部来源")
    external_id: Mapped[str | None] = mapped_column(String(128), default=None, nullable=True, index=True, comment="外部ID")
    external_no: Mapped[str | None] = mapped_column(String(128), default=None, nullable=True, index=True, comment="外部单号")
    sync_status: Mapped[str] = mapped_column(String(32), default="not_required", nullable=False, comment="同步状态")
    workflow_instance_id: Mapped[str | None] = mapped_column(String(128), default=None, nullable=True, index=True, comment="流程实例ID")
    remark: Mapped[str | None] = mapped_column(Text, default=None, nullable=True, comment="备注")


class WmsArrivalLineModel(WmsArrivalBase):
    __tablename__ = "wms_arrival_line"
    __table_args__ = ({"comment": "WMS到货明细"},)

    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("wms_arrival_order.id", ondelete="CASCADE"), nullable=False, index=True, comment="到货单ID")
    material_id: Mapped[int] = mapped_column(Integer, ForeignKey("wms_material.id", ondelete="RESTRICT"), nullable=False, index=True, comment="物料ID")
    planned_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, comment="计划数量")
    received_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False, comment="实收数量")
    inspected_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False, comment="已检数量")
    accepted_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False, comment="合格数量")
    rejected_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False, comment="不合格数量")
    batch_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="批次号")
    status: Mapped[str] = mapped_column(String(32), default="pending_receive", nullable=False, index=True, comment="状态")
    remark: Mapped[str | None] = mapped_column(Text, default=None, nullable=True, comment="备注")
