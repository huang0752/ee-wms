from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin, TenantMixin, UserMixin


class WmsInspectionBase(ModelMixin, TenantMixin, UserMixin):
    __abstract__ = True
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by", "tenant_by"]

    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否试用数据")
    demo_batch_id: Mapped[str | None] = mapped_column(String(64), default=None, nullable=True, index=True, comment="试用数据批次")


class WmsInspectionTaskModel(WmsInspectionBase):
    __tablename__ = "wms_inspection_task"
    __table_args__ = (UniqueConstraint("tenant_id", "task_no", name="uq_wms_inspection_tenant_no"), {"comment": "WMS检验任务"})

    task_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="检验任务号")
    arrival_order_id: Mapped[int] = mapped_column(Integer, ForeignKey("wms_arrival_order.id", ondelete="CASCADE"), nullable=False, index=True, comment="到货单ID")
    arrival_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="到货单号")
    status: Mapped[str] = mapped_column(String(32), default="pending_inspection", nullable=False, index=True, comment="状态")
    result: Mapped[str | None] = mapped_column(String(32), default=None, nullable=True, index=True, comment="检验结果")
    inspector_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="SET NULL"), default=None, nullable=True, index=True, comment="检验人ID")
    inspected_time: Mapped[datetime | None] = mapped_column(DateTime, default=None, nullable=True, comment="检验时间")
    attachment_refs: Mapped[str | None] = mapped_column(Text, default=None, nullable=True, comment="附件引用")
    external_quality_id: Mapped[str | None] = mapped_column(String(128), default=None, nullable=True, index=True, comment="外部质量ID")
    remark: Mapped[str | None] = mapped_column(Text, default=None, nullable=True, comment="备注")


class WmsInspectionLineModel(WmsInspectionBase):
    __tablename__ = "wms_inspection_line"
    __table_args__ = ({"comment": "WMS检验明细"},)

    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("wms_inspection_task.id", ondelete="CASCADE"), nullable=False, index=True, comment="检验任务ID")
    arrival_line_id: Mapped[int] = mapped_column(Integer, ForeignKey("wms_arrival_line.id", ondelete="CASCADE"), nullable=False, index=True, comment="到货明细ID")
    material_id: Mapped[int] = mapped_column(Integer, ForeignKey("wms_material.id", ondelete="RESTRICT"), nullable=False, index=True, comment="物料ID")
    batch_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="批次号")
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, comment="检验数量")
    accepted_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False, comment="合格数量")
    rejected_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False, comment="不合格数量")
    result: Mapped[str | None] = mapped_column(String(32), default=None, nullable=True, index=True, comment="明细结果")
    status: Mapped[str] = mapped_column(String(32), default="pending_inspection", nullable=False, index=True, comment="状态")
    remark: Mapped[str | None] = mapped_column(Text, default=None, nullable=True, comment="备注")
