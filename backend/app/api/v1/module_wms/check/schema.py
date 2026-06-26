from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

from app.common.enums import QueueEnum
from app.core.base_params import BaseQueryParam, TenantByQueryParam, UserByQueryParam
from app.core.base_schema import BaseSchema


class WmsDocOutSchema(BaseSchema):
    tenant_id: int | None = None
    created_id: int | None = None
    updated_id: int | None = None
    deleted_id: int | None = None


class WmsStockCheckLineCreateSchema(BaseModel):
    material_id: int = Field(..., ge=1)
    location_id: int | None = Field(default=None, ge=1)
    batch_no: str = Field(..., min_length=1, max_length=64)
    system_qty: Decimal = Field(..., ge=0)
    counted_qty: Decimal = Field(..., ge=0)
    remark: str | None = Field(default=None, max_length=255)


class WmsStockCheckCreateSchema(BaseModel):
    order_no: str | None = Field(default=None, max_length=64)
    warehouse_id: int = Field(..., ge=1)
    remark: str | None = Field(default=None, max_length=255)
    lines: list[WmsStockCheckLineCreateSchema] = Field(..., min_length=1)


class WmsStockCheckOrderOutSchema(WmsDocOutSchema):
    model_config = ConfigDict(from_attributes=True)
    order_no: str
    warehouse_id: int
    status: str
    audited_time: datetime | None = None
    remark: str | None = None


class WmsStockCheckLineOutSchema(WmsDocOutSchema):
    model_config = ConfigDict(from_attributes=True)
    order_id: int
    material_id: int
    warehouse_id: int
    location_id: int | None = None
    batch_no: str
    system_qty: Decimal
    counted_qty: Decimal
    diff_qty: Decimal
    status: str
    remark: str | None = None


@dataclass
class WmsStockCheckQueryParam(BaseQueryParam, UserByQueryParam, TenantByQueryParam):
    order_no: str | None = Query(None)
    status: str | None = Query(None)

    def __post_init__(self) -> None:
        self.order_no = (QueueEnum.like.value, self.order_no)
        self.status = (QueueEnum.eq.value, self.status)

