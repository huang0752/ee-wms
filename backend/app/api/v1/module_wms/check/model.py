from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin, TenantMixin, UserMixin


class WmsStockCheckBase(ModelMixin, TenantMixin, UserMixin):
    __abstract__ = True
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by", "tenant_by"]

    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否试用数据")
    demo_batch_id: Mapped[str | None] = mapped_column(String(64), default=None, nullable=True, index=True, comment="试用数据批次")


class WmsStockCheckOrderModel(WmsStockCheckBase):
    __tablename__ = "wms_stock_check_order"
    __table_args__ = (UniqueConstraint("tenant_id", "order_no", name="uq_wms_check_tenant_no"), {"comment": "WMS盘点单"})

    order_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="盘点单号")
    warehouse_id: Mapped[int] = mapped_column(Integer, ForeignKey("wms_warehouse.id", ondelete="RESTRICT"), nullable=False, index=True, comment="仓库ID")
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False, index=True, comment="状态")
    audited_time: Mapped[datetime | None] = mapped_column(DateTime, default=None, nullable=True, comment="审核时间")
    remark: Mapped[str | None] = mapped_column(Text, default=None, nullable=True, comment="备注")


class WmsStockCheckLineModel(WmsStockCheckBase):
    __tablename__ = "wms_stock_check_line"
    __table_args__ = ({"comment": "WMS盘点明细"},)

    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("wms_stock_check_order.id", ondelete="CASCADE"), nullable=False, index=True, comment="盘点单ID")
    material_id: Mapped[int] = mapped_column(Integer, ForeignKey("wms_material.id", ondelete="RESTRICT"), nullable=False, index=True, comment="物料ID")
    warehouse_id: Mapped[int] = mapped_column(Integer, ForeignKey("wms_warehouse.id", ondelete="RESTRICT"), nullable=False, index=True, comment="仓库ID")
    location_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("wms_location.id", ondelete="SET NULL"), default=None, nullable=True, index=True, comment="库位ID")
    batch_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="批次号")
    system_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, comment="系统数量")
    counted_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, comment="实盘数量")
    diff_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, comment="差异数量")
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False, index=True, comment="状态")
    remark: Mapped[str | None] = mapped_column(Text, default=None, nullable=True, comment="备注")

