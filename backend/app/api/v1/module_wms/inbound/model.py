from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin, TenantMixin, UserMixin


class WmsInboundBase(ModelMixin, TenantMixin, UserMixin):
    __abstract__ = True
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by", "tenant_by"]

    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否试用数据")
    demo_batch_id: Mapped[str | None] = mapped_column(String(64), default=None, nullable=True, index=True, comment="试用数据批次")


class WmsInboundOrderModel(WmsInboundBase):
    __tablename__ = "wms_inbound_order"
    __table_args__ = (UniqueConstraint("tenant_id", "order_no", name="uq_wms_inbound_tenant_no"), {"comment": "WMS入库单"})

    order_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="入库单号")
    inspection_task_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("wms_inspection_task.id", ondelete="SET NULL"), default=None, nullable=True, index=True, comment="检验任务ID")
    arrival_order_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("wms_arrival_order.id", ondelete="SET NULL"), default=None, nullable=True, index=True, comment="到货单ID")
    warehouse_id: Mapped[int] = mapped_column(Integer, ForeignKey("wms_warehouse.id", ondelete="RESTRICT"), nullable=False, index=True, comment="仓库ID")
    location_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("wms_location.id", ondelete="SET NULL"), default=None, nullable=True, index=True, comment="库位ID")
    status: Mapped[str] = mapped_column(String(32), default="pending_confirm", nullable=False, index=True, comment="状态")
    confirmed_time: Mapped[datetime | None] = mapped_column(DateTime, default=None, nullable=True, comment="确认时间")
    external_source: Mapped[str] = mapped_column(String(32), default="manual", nullable=False, comment="外部来源")
    external_id: Mapped[str | None] = mapped_column(String(128), default=None, nullable=True, index=True, comment="外部ID")
    external_no: Mapped[str | None] = mapped_column(String(128), default=None, nullable=True, index=True, comment="外部单号")
    sync_status: Mapped[str] = mapped_column(String(32), default="not_required", nullable=False, comment="同步状态")
    workflow_instance_id: Mapped[str | None] = mapped_column(String(128), default=None, nullable=True, index=True, comment="流程实例ID")
    remark: Mapped[str | None] = mapped_column(Text, default=None, nullable=True, comment="备注")


class WmsInboundLineModel(WmsInboundBase):
    __tablename__ = "wms_inbound_line"
    __table_args__ = ({"comment": "WMS入库明细"},)

    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("wms_inbound_order.id", ondelete="CASCADE"), nullable=False, index=True, comment="入库单ID")
    inspection_line_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("wms_inspection_line.id", ondelete="SET NULL"), default=None, nullable=True, index=True, comment="检验明细ID")
    material_id: Mapped[int] = mapped_column(Integer, ForeignKey("wms_material.id", ondelete="RESTRICT"), nullable=False, index=True, comment="物料ID")
    warehouse_id: Mapped[int] = mapped_column(Integer, ForeignKey("wms_warehouse.id", ondelete="RESTRICT"), nullable=False, index=True, comment="仓库ID")
    location_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("wms_location.id", ondelete="SET NULL"), default=None, nullable=True, index=True, comment="库位ID")
    batch_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="批次号")
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, comment="入库数量")
    stock_status: Mapped[str] = mapped_column(String(32), default="available", nullable=False, index=True, comment="入库库存状态")
    status: Mapped[str] = mapped_column(String(32), default="pending_confirm", nullable=False, index=True, comment="状态")
    remark: Mapped[str | None] = mapped_column(Text, default=None, nullable=True, comment="备注")
