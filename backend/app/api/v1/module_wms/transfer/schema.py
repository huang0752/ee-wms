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


class WmsTransferLineCreateSchema(BaseModel):
    material_id: int = Field(..., ge=1)
    from_location_id: int | None = Field(default=None, ge=1)
    to_location_id: int | None = Field(default=None, ge=1)
    batch_no: str = Field(..., min_length=1, max_length=64)
    quantity: Decimal = Field(..., gt=0)
    remark: str | None = Field(default=None, max_length=255)


class WmsTransferCreateSchema(BaseModel):
    order_no: str | None = Field(default=None, max_length=64)
    from_warehouse_id: int = Field(..., ge=1)
    to_warehouse_id: int = Field(..., ge=1)
    remark: str | None = Field(default=None, max_length=255)
    lines: list[WmsTransferLineCreateSchema] = Field(..., min_length=1)


class WmsTransferOrderOutSchema(WmsDocOutSchema):
    model_config = ConfigDict(from_attributes=True)
    order_no: str
    from_warehouse_id: int
    to_warehouse_id: int
    status: str
    confirmed_time: datetime | None = None
    remark: str | None = None
    is_demo: bool = False
    demo_batch_id: str | None = None


class WmsTransferLineOutSchema(WmsDocOutSchema):
    model_config = ConfigDict(from_attributes=True)
    order_id: int
    material_id: int
    from_warehouse_id: int
    from_location_id: int | None = None
    to_warehouse_id: int
    to_location_id: int | None = None
    batch_no: str
    quantity: Decimal
    status: str
    remark: str | None = None


@dataclass
class WmsTransferQueryParam(BaseQueryParam, UserByQueryParam, TenantByQueryParam):
    order_no: str | None = Query(None)
    status: str | None = Query(None)

    def __post_init__(self) -> None:
        self.order_no = (QueueEnum.like.value, self.order_no)
        self.status = (QueueEnum.eq.value, self.status)

