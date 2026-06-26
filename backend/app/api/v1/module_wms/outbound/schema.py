from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

from app.common.enums import QueueEnum
from app.core.base_params import BaseQueryParam, TenantByQueryParam, UserByQueryParam
from app.core.base_schema import BaseSchema


class WmsOutboundAuditOutSchema(BaseSchema):
    tenant_id: int | None = Field(default=None, description="租户ID")
    created_id: int | None = Field(default=None, description="创建人ID")
    updated_id: int | None = Field(default=None, description="更新人ID")
    deleted_id: int | None = Field(default=None, description="删除人ID")


class WmsOutboundLineCreateSchema(BaseModel):
    material_id: int = Field(..., ge=1, description="物料ID")
    requested_qty: Decimal = Field(..., gt=0, description="需求数量")
    remark: str | None = Field(default=None, max_length=255, description="备注")


class WmsOutboundCreateSchema(BaseModel):
    order_no: str | None = Field(default=None, max_length=64, description="出库单号")
    customer_id: int | None = Field(default=None, ge=1, description="客户ID")
    warehouse_id: int = Field(..., ge=1, description="仓库ID")
    external_source: str = Field(default="manual", max_length=32, description="外部来源")
    external_id: str | None = Field(default=None, max_length=128, description="外部ID")
    external_no: str | None = Field(default=None, max_length=128, description="外部单号")
    sync_status: str = Field(default="not_required", max_length=32, description="同步状态")
    workflow_instance_id: str | None = Field(default=None, max_length=128, description="流程实例ID")
    remark: str | None = Field(default=None, max_length=255, description="备注")
    lines: list[WmsOutboundLineCreateSchema] = Field(..., min_length=1, description="出库明细")


class WmsOutboundOrderOutSchema(WmsOutboundAuditOutSchema):
    model_config = ConfigDict(from_attributes=True)

    order_no: str
    customer_id: int | None = None
    warehouse_id: int
    status: str
    picked_time: datetime | None = None
    reviewed_time: datetime | None = None
    confirmed_time: datetime | None = None
    external_source: str
    external_id: str | None = None
    external_no: str | None = None
    sync_status: str
    workflow_instance_id: str | None = None
    remark: str | None = None
    is_demo: bool = False
    demo_batch_id: str | None = None


class WmsOutboundLineOutSchema(WmsOutboundAuditOutSchema):
    model_config = ConfigDict(from_attributes=True)

    order_id: int
    material_id: int
    warehouse_id: int
    location_id: int | None = None
    batch_no: str | None = None
    requested_qty: Decimal
    locked_qty: Decimal
    shipped_qty: Decimal
    stock_lock_id: int | None = None
    status: str
    remark: str | None = None
    is_demo: bool = False
    demo_batch_id: str | None = None


@dataclass
class WmsOutboundQueryParam(BaseQueryParam, UserByQueryParam, TenantByQueryParam):
    order_no: str | None = Query(None, description="出库单号")
    status: str | None = Query(None, description="状态")

    def __post_init__(self) -> None:
        self.order_no = (QueueEnum.like.value, self.order_no)
        self.status = (QueueEnum.eq.value, self.status)
