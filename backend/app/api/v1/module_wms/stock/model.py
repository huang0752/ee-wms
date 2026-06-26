from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin, TenantMixin, UserMixin


class WmsStockBase(ModelMixin, TenantMixin, UserMixin):
    __abstract__ = True
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by", "tenant_by"]

    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否试用数据")
    demo_batch_id: Mapped[str | None] = mapped_column(String(64), default=None, nullable=True, index=True, comment="试用数据批次")


class WmsStockBatchModel(WmsStockBase):
    __tablename__ = "wms_stock_batch"
    __table_args__ = (
        UniqueConstraint("tenant_id", "material_id", "batch_no", "sn_code", name="uq_wms_stock_batch_tenant_material_batch_sn"),
        {"comment": "WMS库存批次"},
    )

    material_id: Mapped[int] = mapped_column(Integer, ForeignKey("wms_material.id", ondelete="RESTRICT"), nullable=False, index=True, comment="物料ID")
    warehouse_id: Mapped[int] = mapped_column(Integer, ForeignKey("wms_warehouse.id", ondelete="RESTRICT"), nullable=False, index=True, comment="仓库ID")
    location_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("wms_location.id", ondelete="SET NULL"), default=None, nullable=True, index=True, comment="库位ID")
    batch_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="批次号")
    sn_code: Mapped[str | None] = mapped_column(String(128), default=None, nullable=True, index=True, comment="SN码")
    stock_status: Mapped[str] = mapped_column(String(32), default="pending_inspection", nullable=False, index=True, comment="库存状态")
    source_type: Mapped[str | None] = mapped_column(String(32), default=None, nullable=True, comment="来源类型")
    source_no: Mapped[str | None] = mapped_column(String(128), default=None, nullable=True, comment="来源单号")
    production_date: Mapped[datetime | None] = mapped_column(DateTime, default=None, nullable=True, comment="生产日期")
    expire_date: Mapped[datetime | None] = mapped_column(DateTime, default=None, nullable=True, comment="失效日期")


class WmsStockBalanceModel(WmsStockBase):
    __tablename__ = "wms_stock_balance"
    __table_args__ = (
        UniqueConstraint("tenant_id", "material_id", "warehouse_id", "location_id", "batch_no", name="uq_wms_stock_balance_tenant_scope_batch"),
        {"comment": "WMS库存余额"},
    )

    material_id: Mapped[int] = mapped_column(Integer, ForeignKey("wms_material.id", ondelete="RESTRICT"), nullable=False, index=True, comment="物料ID")
    warehouse_id: Mapped[int] = mapped_column(Integer, ForeignKey("wms_warehouse.id", ondelete="RESTRICT"), nullable=False, index=True, comment="仓库ID")
    location_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("wms_location.id", ondelete="SET NULL"), default=None, nullable=True, index=True, comment="库位ID")
    batch_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="批次号")
    sn_code: Mapped[str | None] = mapped_column(String(128), default=None, nullable=True, index=True, comment="SN码")
    stock_status: Mapped[str] = mapped_column(String(32), default="mixed", nullable=False, index=True, comment="汇总库存状态")
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False, comment="实物数量")
    available_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False, comment="可用数量")
    locked_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False, comment="锁定数量")
    frozen_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False, comment="冻结数量")
    pending_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False, comment="待检数量")
    defective_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False, comment="不良数量")


class WmsStockFlowModel(WmsStockBase):
    __tablename__ = "wms_stock_flow"
    __table_args__ = (UniqueConstraint("tenant_id", "flow_no", name="uq_wms_stock_flow_tenant_no"), {"comment": "WMS库存流水"})

    flow_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="流水号")
    flow_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="流水类型")
    direction: Mapped[str] = mapped_column(String(16), nullable=False, index=True, comment="方向")
    material_id: Mapped[int] = mapped_column(Integer, ForeignKey("wms_material.id", ondelete="RESTRICT"), nullable=False, index=True, comment="物料ID")
    warehouse_id: Mapped[int] = mapped_column(Integer, ForeignKey("wms_warehouse.id", ondelete="RESTRICT"), nullable=False, index=True, comment="仓库ID")
    location_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("wms_location.id", ondelete="SET NULL"), default=None, nullable=True, index=True, comment="库位ID")
    balance_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("wms_stock_balance.id", ondelete="SET NULL"), default=None, nullable=True, index=True, comment="余额ID")
    lock_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("wms_stock_lock.id", ondelete="SET NULL"), default=None, nullable=True, index=True, comment="锁库ID")
    batch_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="批次号")
    sn_code: Mapped[str | None] = mapped_column(String(128), default=None, nullable=True, index=True, comment="SN码")
    stock_status_before: Mapped[str | None] = mapped_column(String(32), default=None, nullable=True, comment="变更前状态")
    stock_status_after: Mapped[str | None] = mapped_column(String(32), default=None, nullable=True, comment="变更后状态")
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, comment="变更数量")
    document_type: Mapped[str | None] = mapped_column(String(32), default=None, nullable=True, index=True, comment="单据类型")
    document_no: Mapped[str | None] = mapped_column(String(128), default=None, nullable=True, index=True, comment="单据号")
    remark: Mapped[str | None] = mapped_column(Text, default=None, nullable=True, comment="备注")


class WmsStockLockModel(WmsStockBase):
    __tablename__ = "wms_stock_lock"
    __table_args__ = (UniqueConstraint("tenant_id", "lock_no", name="uq_wms_stock_lock_tenant_no"), {"comment": "WMS库存锁定"})

    lock_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="锁库单号")
    material_id: Mapped[int] = mapped_column(Integer, ForeignKey("wms_material.id", ondelete="RESTRICT"), nullable=False, index=True, comment="物料ID")
    warehouse_id: Mapped[int] = mapped_column(Integer, ForeignKey("wms_warehouse.id", ondelete="RESTRICT"), nullable=False, index=True, comment="仓库ID")
    location_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("wms_location.id", ondelete="SET NULL"), default=None, nullable=True, index=True, comment="库位ID")
    batch_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="批次号")
    sn_code: Mapped[str | None] = mapped_column(String(128), default=None, nullable=True, index=True, comment="SN码")
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, comment="锁定数量")
    released_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False, comment="释放数量")
    shipped_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0, nullable=False, comment="发货数量")
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True, comment="状态")
    document_type: Mapped[str | None] = mapped_column(String(32), default=None, nullable=True, index=True, comment="单据类型")
    document_no: Mapped[str | None] = mapped_column(String(128), default=None, nullable=True, index=True, comment="单据号")


class WmsTraceLinkModel(WmsStockBase):
    __tablename__ = "wms_trace_link"
    __table_args__ = ({"comment": "WMS追溯关系"},)

    source_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="来源类型")
    source_id: Mapped[int | None] = mapped_column(Integer, default=None, nullable=True, index=True, comment="来源ID")
    source_no: Mapped[str | None] = mapped_column(String(128), default=None, nullable=True, index=True, comment="来源单号")
    target_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="目标类型")
    target_id: Mapped[int | None] = mapped_column(Integer, default=None, nullable=True, index=True, comment="目标ID")
    target_no: Mapped[str | None] = mapped_column(String(128), default=None, nullable=True, index=True, comment="目标单号")
    relation_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="关系类型")
    material_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("wms_material.id", ondelete="SET NULL"), default=None, nullable=True, index=True, comment="物料ID")
    batch_no: Mapped[str | None] = mapped_column(String(64), default=None, nullable=True, index=True, comment="批次号")
