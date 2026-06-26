from decimal import Decimal

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin, TenantMixin, UserMixin


class WmsMasterBase(ModelMixin, TenantMixin, UserMixin):
    __abstract__ = True
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by", "tenant_by"]

    code: Mapped[str] = mapped_column(String(64), nullable=False, comment="编码")
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="名称")
    status: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="状态(0:启用 1:停用)", index=True)
    description: Mapped[str | None] = mapped_column(Text, default=None, nullable=True, comment="备注")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否试用数据")
    demo_batch_id: Mapped[str | None] = mapped_column(String(64), default=None, nullable=True, index=True, comment="试用数据批次")


class WmsWarehouseModel(WmsMasterBase):
    __tablename__ = "wms_warehouse"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_wms_warehouse_tenant_code"), {"comment": "WMS仓库"})

    type: Mapped[str | None] = mapped_column(String(32), default=None, nullable=True, comment="仓库类型")
    manager: Mapped[str | None] = mapped_column(String(64), default=None, nullable=True, comment="负责人")
    dept_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sys_dept.id", ondelete="SET NULL"), default=None, nullable=True, index=True, comment="部门ID")


class WmsZoneModel(WmsMasterBase):
    __tablename__ = "wms_zone"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_wms_zone_tenant_code"), {"comment": "WMS库区"})

    warehouse_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("wms_warehouse.id", ondelete="SET NULL"), default=None, nullable=True, index=True, comment="仓库ID")
    usage: Mapped[str | None] = mapped_column(String(64), default=None, nullable=True, comment="用途")


class WmsLocationModel(WmsMasterBase):
    __tablename__ = "wms_location"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_wms_location_tenant_code"), {"comment": "WMS库位"})

    warehouse_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("wms_warehouse.id", ondelete="SET NULL"), default=None, nullable=True, index=True, comment="仓库ID")
    zone_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("wms_zone.id", ondelete="SET NULL"), default=None, nullable=True, index=True, comment="库区ID")
    capacity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), default=None, nullable=True, comment="容量")
    category_constraints: Mapped[list[str] | None] = mapped_column(JSON, default=None, nullable=True, comment="物料类别限制")
    mix_rule: Mapped[str | None] = mapped_column(String(32), default=None, nullable=True, comment="混放规则")


class WmsMaterialModel(WmsMasterBase):
    __tablename__ = "wms_material"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_wms_material_tenant_code"), {"comment": "WMS物料"})

    spec: Mapped[str | None] = mapped_column(String(128), default=None, nullable=True, comment="规格型号")
    unit: Mapped[str | None] = mapped_column(String(32), default=None, nullable=True, comment="单位")
    category: Mapped[str | None] = mapped_column(String(64), default=None, nullable=True, comment="物料类别")
    batch_flag: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否批次管理")
    sn_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否SN管理")
    safety_stock: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), default=None, nullable=True, comment="安全库存")


class WmsSupplierModel(WmsMasterBase):
    __tablename__ = "wms_supplier"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_wms_supplier_tenant_code"), {"comment": "WMS供应商"})

    contact: Mapped[str | None] = mapped_column(String(64), default=None, nullable=True, comment="联系人")
    phone: Mapped[str | None] = mapped_column(String(32), default=None, nullable=True, comment="电话")
    email: Mapped[str | None] = mapped_column(String(128), default=None, nullable=True, comment="邮箱")
    address: Mapped[str | None] = mapped_column(String(255), default=None, nullable=True, comment="地址")


class WmsCustomerModel(WmsMasterBase):
    __tablename__ = "wms_customer"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_wms_customer_tenant_code"), {"comment": "WMS客户"})

    contact: Mapped[str | None] = mapped_column(String(64), default=None, nullable=True, comment="联系人")
    phone: Mapped[str | None] = mapped_column(String(32), default=None, nullable=True, comment="电话")
    email: Mapped[str | None] = mapped_column(String(128), default=None, nullable=True, comment="邮箱")
    address: Mapped[str | None] = mapped_column(String(255), default=None, nullable=True, comment="地址")


class WmsBarcodeRuleModel(WmsMasterBase):
    __tablename__ = "wms_barcode_rule"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_wms_barcode_rule_tenant_code"), {"comment": "WMS条码规则"})

    object_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="对象类型")
    prefix: Mapped[str | None] = mapped_column(String(32), default=None, nullable=True, comment="前缀")
    segment_strategy: Mapped[dict | None] = mapped_column(JSON, default=None, nullable=True, comment="分段策略")
