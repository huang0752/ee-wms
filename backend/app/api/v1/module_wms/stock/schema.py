from dataclasses import dataclass
from decimal import Decimal

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.common.enums import QueueEnum
from app.core.base_params import BaseQueryParam, TenantByQueryParam, UserByQueryParam
from app.core.base_schema import BaseSchema


class WmsStockMutationSchema(BaseModel):
    material_id: int = Field(..., ge=1, description="物料ID")
    warehouse_id: int = Field(..., ge=1, description="仓库ID")
    location_id: int | None = Field(default=None, ge=1, description="库位ID")
    batch_no: str = Field(..., min_length=1, max_length=64, description="批次号")
    sn_code: str | None = Field(default=None, max_length=128, description="SN码")
    quantity: Decimal = Field(..., gt=0, description="数量")
    document_type: str | None = Field(default=None, max_length=32, description="单据类型")
    document_no: str | None = Field(default=None, max_length=128, description="单据号")
    remark: str | None = Field(default=None, max_length=255, description="备注")
    is_demo: bool = Field(default=False, description="是否试用数据")
    demo_batch_id: str | None = Field(default=None, max_length=64, description="试用批次")

    @field_validator("batch_no")
    @classmethod
    def _validate_batch_no(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("批次号不能为空")
        return value


class WmsStockLockSchema(BaseModel):
    material_id: int = Field(..., ge=1, description="物料ID")
    warehouse_id: int | None = Field(default=None, ge=1, description="仓库ID")
    location_id: int | None = Field(default=None, ge=1, description="库位ID")
    quantity: Decimal = Field(..., gt=0, description="数量")
    document_type: str | None = Field(default=None, max_length=32, description="单据类型")
    document_no: str | None = Field(default=None, max_length=128, description="单据号")
    remark: str | None = Field(default=None, max_length=255, description="备注")
    is_demo: bool = Field(default=False, description="是否试用数据")
    demo_batch_id: str | None = Field(default=None, max_length=64, description="试用批次")


class WmsStockAdjustSchema(WmsStockMutationSchema):
    stock_bucket: str = Field(default="available", description="调整库存桶")


class WmsStockAuditOutSchema(BaseSchema):
    tenant_id: int | None = Field(default=None, description="租户ID")
    created_id: int | None = Field(default=None, description="创建人ID")
    updated_id: int | None = Field(default=None, description="更新人ID")
    deleted_id: int | None = Field(default=None, description="删除人ID")


class WmsStockBalanceOutSchema(WmsStockAuditOutSchema):
    model_config = ConfigDict(from_attributes=True)

    material_id: int
    warehouse_id: int
    location_id: int | None = None
    batch_no: str
    sn_code: str | None = None
    stock_status: str
    quantity: Decimal
    available_qty: Decimal
    locked_qty: Decimal
    frozen_qty: Decimal
    pending_qty: Decimal
    defective_qty: Decimal
    is_demo: bool = False
    demo_batch_id: str | None = None


class WmsStockFlowOutSchema(WmsStockAuditOutSchema):
    model_config = ConfigDict(from_attributes=True)

    flow_no: str
    flow_type: str
    direction: str
    material_id: int
    warehouse_id: int
    location_id: int | None = None
    balance_id: int | None = None
    lock_id: int | None = None
    batch_no: str
    sn_code: str | None = None
    stock_status_before: str | None = None
    stock_status_after: str | None = None
    quantity: Decimal
    document_type: str | None = None
    document_no: str | None = None
    remark: str | None = None


class WmsStockLockOutSchema(WmsStockAuditOutSchema):
    model_config = ConfigDict(from_attributes=True)

    lock_no: str
    material_id: int
    warehouse_id: int
    location_id: int | None = None
    batch_no: str
    sn_code: str | None = None
    quantity: Decimal
    released_qty: Decimal
    shipped_qty: Decimal
    status: str
    document_type: str | None = None
    document_no: str | None = None


@dataclass
class WmsStockBalanceQueryParam(BaseQueryParam, UserByQueryParam, TenantByQueryParam):
    material_id: int | None = Query(None, ge=1, description="物料ID")
    warehouse_id: int | None = Query(None, ge=1, description="仓库ID")
    location_id: int | None = Query(None, ge=1, description="库位ID")
    batch_no: str | None = Query(None, description="批次号")
    only_available: bool | None = Query(None, description="仅可用库存")
    is_demo: bool | None = Query(None, description="是否试用数据")

    def __post_init__(self) -> None:
        if isinstance(self.material_id, int):
            self.material_id = (QueueEnum.eq.value, self.material_id)
        if isinstance(self.warehouse_id, int):
            self.warehouse_id = (QueueEnum.eq.value, self.warehouse_id)
        if isinstance(self.location_id, int):
            self.location_id = (QueueEnum.eq.value, self.location_id)
        self.batch_no = (QueueEnum.like.value, self.batch_no)
        if isinstance(self.is_demo, bool):
            self.is_demo = (QueueEnum.eq.value, self.is_demo)


@dataclass
class WmsStockFlowQueryParam(BaseQueryParam, UserByQueryParam, TenantByQueryParam):
    material_id: int | None = Query(None, ge=1, description="物料ID")
    batch_no: str | None = Query(None, description="批次号")
    flow_type: str | None = Query(None, description="流水类型")
    document_no: str | None = Query(None, description="单据号")

    def __post_init__(self) -> None:
        if isinstance(self.material_id, int):
            self.material_id = (QueueEnum.eq.value, self.material_id)
        self.batch_no = (QueueEnum.like.value, self.batch_no)
        self.flow_type = (QueueEnum.eq.value, self.flow_type)
        self.document_no = (QueueEnum.like.value, self.document_no)
