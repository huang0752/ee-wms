from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

from app.common.enums import QueueEnum
from app.core.base_params import BaseQueryParam, TenantByQueryParam, UserByQueryParam
from app.core.base_schema import BaseSchema


class WmsStockWarningOutSchema(BaseSchema):
    model_config = ConfigDict(from_attributes=True)
    tenant_id: int | None = None
    created_id: int | None = None
    updated_id: int | None = None
    warning_no: str
    warning_type: str
    material_id: int
    warehouse_id: int | None = None
    batch_no: str | None = None
    current_qty: Decimal
    threshold_qty: Decimal | None = None
    status: str
    handled_time: datetime | None = None
    remark: str | None = None


class WmsWarningScanSchema(BaseModel):
    warehouse_id: int | None = Field(default=None, ge=1)


@dataclass
class WmsStockWarningQueryParam(BaseQueryParam, UserByQueryParam, TenantByQueryParam):
    warning_type: str | None = Query(None)
    status: str | None = Query(None)

    def __post_init__(self) -> None:
        self.warning_type = (QueueEnum.eq.value, self.warning_type)
        self.status = (QueueEnum.eq.value, self.status)
