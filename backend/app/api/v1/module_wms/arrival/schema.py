from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

from app.common.enums import QueueEnum
from app.core.base_params import BaseQueryParam, TenantByQueryParam, UserByQueryParam
from app.core.base_schema import BaseSchema


class WmsDocumentOutSchema(BaseSchema):
    tenant_id: int | None = Field(default=None, description="租户ID")
    created_id: int | None = Field(default=None, description="创建人ID")
    updated_id: int | None = Field(default=None, description="更新人ID")
    deleted_id: int | None = Field(default=None, description="删除人ID")


class WmsArrivalLineCreateSchema(BaseModel):
    material_id: int = Field(..., ge=1, description="物料ID")
    planned_qty: Decimal = Field(..., gt=0, description="计划数量")
    batch_no: str = Field(..., min_length=1, max_length=64, description="批次号")
    remark: str | None = Field(default=None, max_length=255, description="备注")


class WmsArrivalCreateSchema(BaseModel):
    order_no: str | None = Field(default=None, max_length=64, description="到货单号")
    supplier_id: int | None = Field(default=None, ge=1, description="供应商ID")
    warehouse_id: int = Field(..., ge=1, description="仓库ID")
    expected_time: datetime | None = Field(default=None, description="预计到货时间")
    external_source: str = Field(default="manual", max_length=32, description="外部来源")
    external_id: str | None = Field(default=None, max_length=128, description="外部ID")
    external_no: str | None = Field(default=None, max_length=128, description="外部单号")
    sync_status: str = Field(default="not_required", max_length=32, description="同步状态")
    workflow_instance_id: str | None = Field(default=None, max_length=128, description="流程实例ID")
    remark: str | None = Field(default=None, max_length=255, description="备注")
    lines: list[WmsArrivalLineCreateSchema] = Field(..., min_length=1, description="到货明细")


class WmsArrivalLineOutSchema(WmsDocumentOutSchema):
    model_config = ConfigDict(from_attributes=True)

    order_id: int
    material_id: int
    planned_qty: Decimal
    received_qty: Decimal
    inspected_qty: Decimal
    accepted_qty: Decimal
    rejected_qty: Decimal
    batch_no: str
    status: str
    remark: str | None = None
    is_demo: bool = False
    demo_batch_id: str | None = None


class WmsArrivalOrderOutSchema(WmsDocumentOutSchema):
    model_config = ConfigDict(from_attributes=True)

    order_no: str
    supplier_id: int | None = None
    warehouse_id: int
    status: str
    expected_time: datetime | None = None
    received_time: datetime | None = None
    external_source: str
    external_id: str | None = None
    external_no: str | None = None
    sync_status: str
    workflow_instance_id: str | None = None
    remark: str | None = None
    is_demo: bool = False
    demo_batch_id: str | None = None


@dataclass
class WmsArrivalQueryParam(BaseQueryParam, UserByQueryParam, TenantByQueryParam):
    order_no: str | None = Query(None, description="到货单号")
    status: str | None = Query(None, description="状态")

    def __post_init__(self) -> None:
        self.order_no = (QueueEnum.like.value, self.order_no)
        self.status = (QueueEnum.eq.value, self.status)
