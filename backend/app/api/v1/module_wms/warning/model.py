from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin, TenantMixin, UserMixin


class WmsStockWarningModel(ModelMixin, TenantMixin, UserMixin):
    __tablename__ = "wms_stock_warning"
    __table_args__ = ({"comment": "WMS库存预警"},)
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by", "tenant_by"]

    warning_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="预警编号")
    warning_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="预警类型")
    material_id: Mapped[int] = mapped_column(Integer, ForeignKey("wms_material.id", ondelete="RESTRICT"), nullable=False, index=True, comment="物料ID")
    warehouse_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("wms_warehouse.id", ondelete="SET NULL"), default=None, nullable=True, index=True, comment="仓库ID")
    batch_no: Mapped[str | None] = mapped_column(String(64), default=None, nullable=True, index=True, comment="批次号")
    current_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False, comment="当前数量")
    threshold_qty: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), default=None, nullable=True, comment="阈值数量")
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False, index=True, comment="状态")
    handled_time: Mapped[datetime | None] = mapped_column(DateTime, default=None, nullable=True, comment="处理时间")
    remark: Mapped[str | None] = mapped_column(Text, default=None, nullable=True, comment="备注")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否试用数据")
    demo_batch_id: Mapped[str | None] = mapped_column(String(64), default=None, nullable=True, index=True, comment="试用数据批次")
