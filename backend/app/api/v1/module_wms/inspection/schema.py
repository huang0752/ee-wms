from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

from app.common.enums import QueueEnum
from app.core.base_params import BaseQueryParam, TenantByQueryParam, UserByQueryParam
from app.core.base_schema import BaseSchema


class WmsInspectionAuditOutSchema(BaseSchema):
    tenant_id: int | None = Field(default=None, description="租户ID")
    created_id: int | None = Field(default=None, description="创建人ID")
    updated_id: int | None = Field(default=None, description="更新人ID")
    deleted_id: int | None = Field(default=None, description="删除人ID")


class WmsInspectionJudgeLineSchema(BaseModel):
    line_id: int = Field(..., ge=1, description="检验明细ID")
    accepted_qty: Decimal = Field(default=0, ge=0, description="合格数量")
    rejected_qty: Decimal = Field(default=0, ge=0, description="不合格数量")
    result: str | None = Field(default=None, max_length=32, description="明细结果")
    remark: str | None = Field(default=None, max_length=255, description="备注")


class WmsInspectionJudgeSchema(BaseModel):
    result: str | None = Field(default=None, max_length=32, description="检验结果")
    attachment_refs: str | None = Field(default=None, max_length=1024, description="附件引用")
    external_quality_id: str | None = Field(default=None, max_length=128, description="外部质量ID")
    remark: str | None = Field(default=None, max_length=255, description="备注")
    lines: list[WmsInspectionJudgeLineSchema] = Field(..., min_length=1, description="检验明细")


class WmsInspectionTaskOutSchema(WmsInspectionAuditOutSchema):
    model_config = ConfigDict(from_attributes=True)

    task_no: str
    arrival_order_id: int
    arrival_no: str
    status: str
    result: str | None = None
    inspector_id: int | None = None
    inspected_time: datetime | None = None
    attachment_refs: str | None = None
    external_quality_id: str | None = None
    remark: str | None = None
    is_demo: bool = False
    demo_batch_id: str | None = None


class WmsInspectionLineOutSchema(WmsInspectionAuditOutSchema):
    model_config = ConfigDict(from_attributes=True)

    task_id: int
    arrival_line_id: int
    material_id: int
    batch_no: str
    quantity: Decimal
    accepted_qty: Decimal
    rejected_qty: Decimal
    result: str | None = None
    status: str
    remark: str | None = None
    is_demo: bool = False
    demo_batch_id: str | None = None


@dataclass
class WmsInspectionQueryParam(BaseQueryParam, UserByQueryParam, TenantByQueryParam):
    task_no: str | None = Query(None, description="检验任务号")
    status: str | None = Query(None, description="状态")
    arrival_no: str | None = Query(None, description="到货单号")

    def __post_init__(self) -> None:
        self.task_no = (QueueEnum.like.value, self.task_no)
        self.status = (QueueEnum.eq.value, self.status)
        self.arrival_no = (QueueEnum.like.value, self.arrival_no)
