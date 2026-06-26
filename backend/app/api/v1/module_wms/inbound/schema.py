from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

from app.common.enums import QueueEnum
from app.core.base_params import BaseQueryParam, TenantByQueryParam, UserByQueryParam
from app.core.base_schema import BaseSchema


class WmsInboundAuditOutSchema(BaseSchema):
    tenant_id: int | None = Field(default=None, description="租户ID")
    created_id: int | None = Field(default=None, description="创建人ID")
    updated_id: int | None = Field(default=None, description="更新人ID")
    deleted_id: int | None = Field(default=None, description="删除人ID")


class WmsInboundCreateFromInspectionSchema(BaseModel):
    location_id: int | None = Field(default=None, ge=1, description="默认入库库位ID")
    remark: str | None = Field(default=None, max_length=255, description="备注")


class WmsLocationRecommendOutSchema(BaseModel):
    id: int
    code: str
    name: str
    capacity: Decimal | None = None
    mix_rule: str | None = None


class WmsInboundOrderOutSchema(WmsInboundAuditOutSchema):
    model_config = ConfigDict(from_attributes=True)

    order_no: str
    inspection_task_id: int | None = None
    arrival_order_id: int | None = None
    warehouse_id: int
    location_id: int | None = None
    status: str
    confirmed_time: datetime | None = None
    external_source: str
    external_id: str | None = None
    external_no: str | None = None
    sync_status: str
    workflow_instance_id: str | None = None
    remark: str | None = None
    is_demo: bool = False
    demo_batch_id: str | None = None


class WmsInboundLineOutSchema(WmsInboundAuditOutSchema):
    model_config = ConfigDict(from_attributes=True)

    order_id: int
    inspection_line_id: int | None = None
    material_id: int
    warehouse_id: int
    location_id: int | None = None
    batch_no: str
    quantity: Decimal
    stock_status: str
    status: str
    remark: str | None = None
    is_demo: bool = False
    demo_batch_id: str | None = None


@dataclass
class WmsInboundQueryParam(BaseQueryParam, UserByQueryParam, TenantByQueryParam):
    order_no: str | None = Query(None, description="入库单号")
    status: str | None = Query(None, description="状态")

    def __post_init__(self) -> None:
        self.order_no = (QueueEnum.like.value, self.order_no)
        self.status = (QueueEnum.eq.value, self.status)
