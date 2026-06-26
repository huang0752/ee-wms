from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.common.enums import QueueEnum
from app.core.base_params import BaseQueryParam, TenantByQueryParam, UserByQueryParam
from app.core.base_schema import BaseSchema

InboundContract = Literal["material", "purchase_arrival", "sales_order", "mes_work_order", "bom_demand", "completion_inbound"]
OutboundContract = Literal["available_stock", "shortage_result", "issue_result", "inbound_result", "trace_result"]
IntegrationSource = Literal["erp", "mes", "pda", "excel", "manual", "api"]


class WmsIntegrationLine(BaseModel):
    material_code: str = Field(..., min_length=1, max_length=64, description="物料编码")
    quantity: Decimal = Field(..., gt=0, description="数量")
    batch_no: str | None = Field(default=None, max_length=64, description="批次号")
    warehouse_code: str | None = Field(default=None, max_length=64, description="仓库编码")
    location_code: str | None = Field(default=None, max_length=64, description="库位编码")
    remark: str | None = Field(default=None, max_length=255, description="备注")


class WmsMaterialInboundPayload(BaseModel):
    material_code: str = Field(..., min_length=1, max_length=64, description="物料编码")
    material_name: str = Field(..., min_length=1, max_length=128, description="物料名称")
    spec: str | None = Field(default=None, max_length=128, description="规格")
    unit: str | None = Field(default=None, max_length=32, description="单位")
    category: str | None = Field(default=None, max_length=64, description="类别")


class WmsDocumentInboundPayload(BaseModel):
    external_no: str = Field(..., min_length=1, max_length=128, description="外部单号")
    warehouse_code: str | None = Field(default=None, max_length=64, description="仓库编码")
    supplier_code: str | None = Field(default=None, max_length=64, description="供应商编码")
    customer_code: str | None = Field(default=None, max_length=64, description="客户编码")
    work_order_no: str | None = Field(default=None, max_length=128, description="生产工单号")
    lines: list[WmsIntegrationLine] = Field(default_factory=list, description="明细")


class WmsIntegrationInboundSchema(BaseModel):
    source: IntegrationSource = Field(description="来源系统")
    contract: InboundContract = Field(description="入站契约")
    idempotency_key: str = Field(..., min_length=1, max_length=128, description="幂等键")
    payload: WmsMaterialInboundPayload | WmsDocumentInboundPayload = Field(description="请求载荷")
    is_demo: bool = Field(default=False, description="是否试用数据")
    demo_batch_id: str | None = Field(default=None, max_length=64, description="试用批次")

    @field_validator("idempotency_key")
    @classmethod
    def _strip_key(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("幂等键不能为空")
        return value


class WmsIntegrationRequestOut(BaseSchema):
    model_config = ConfigDict(from_attributes=True)

    tenant_id: int | None = None
    created_id: int | None = None
    updated_id: int | None = None
    source: str
    contract: str
    idempotency_key: str
    external_no: str | None = None
    status: str
    payload: dict
    result: dict | None = None
    error: str | None = None
    is_demo: bool = False
    demo_batch_id: str | None = None


class WmsIntegrationAcceptedOut(BaseModel):
    request: WmsIntegrationRequestOut
    reused: bool = Field(description="是否复用已有幂等结果")


class WmsIntegrationOutboundQuery(BaseModel):
    contract: OutboundContract = Field(description="出站契约")
    material_code: str | None = Field(default=None, max_length=64, description="物料编码")
    batch_no: str | None = Field(default=None, max_length=64, description="批次号")
    document_no: str | None = Field(default=None, max_length=128, description="单据号")


class WmsIntegrationOutboundOut(BaseModel):
    contract: OutboundContract
    items: list[dict] = Field(default_factory=list, description="契约数据")


@dataclass
class WmsIntegrationRequestQueryParam(BaseQueryParam, UserByQueryParam, TenantByQueryParam):
    source: str | None = Query(None, description="来源系统")
    contract: str | None = Query(None, description="契约")
    idempotency_key: str | None = Query(None, description="幂等键")
    status: str | None = Query(None, description="状态")

    def __post_init__(self) -> None:
        self.source = (QueueEnum.eq.value, self.source)
        self.contract = (QueueEnum.eq.value, self.contract)
        self.idempotency_key = (QueueEnum.eq.value, self.idempotency_key)
        self.status = (QueueEnum.eq.value, self.status)
