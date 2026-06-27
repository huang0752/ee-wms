import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.common.enums import QueueEnum
from app.core.base_params import BaseQueryParam, TenantByQueryParam, UserByQueryParam
from app.core.base_schema import BaseSchema, TenantBySchema, UserBySchema

WmsMasterResource = Literal[
    "warehouse",
    "zone",
    "location",
    "material",
    "supplier",
    "customer",
    "barcode-rule",
]


class WmsMasterCreateSchema(BaseModel):
    code: str = Field(..., min_length=1, max_length=64, description="编码")
    name: str = Field(..., min_length=1, max_length=128, description="名称")
    status: int = Field(default=0, ge=0, le=1, description="状态(0:启用 1:停用)")
    description: str | None = Field(default=None, max_length=255, description="备注")
    dept_id: int | None = Field(default=None, ge=1, description="部门ID")
    warehouse_id: int | None = Field(default=None, ge=1, description="仓库ID")
    zone_id: int | None = Field(default=None, ge=1, description="库区ID")
    type: str | None = Field(default=None, max_length=32, description="类型")
    manager: str | None = Field(default=None, max_length=64, description="负责人")
    usage: str | None = Field(default=None, max_length=64, description="用途")
    capacity: Decimal | None = Field(default=None, ge=0, description="容量")
    category_constraints: list[str] | None = Field(default=None, description="类别限制")
    mix_rule: str | None = Field(default=None, max_length=32, description="混放规则")
    spec: str | None = Field(default=None, max_length=128, description="规格")
    unit: str | None = Field(default=None, max_length=32, description="单位")
    category: str | None = Field(default=None, max_length=64, description="类别")
    batch_flag: bool = Field(default=True, description="批次管理")
    sn_flag: bool = Field(default=False, description="SN管理")
    safety_stock: Decimal | None = Field(default=None, ge=0, description="安全库存")
    contact: str | None = Field(default=None, max_length=64, description="联系人")
    phone: str | None = Field(default=None, max_length=32, description="电话")
    email: str | None = Field(default=None, max_length=128, description="邮箱")
    address: str | None = Field(default=None, max_length=255, description="地址")
    object_type: str | None = Field(default=None, max_length=32, description="对象类型")
    prefix: str | None = Field(default=None, max_length=32, description="条码前缀")
    segment_strategy: dict | None = Field(default=None, description="分段策略")
    is_demo: bool = Field(default=False, description="是否试用数据")
    demo_batch_id: str | None = Field(default=None, max_length=64, description="试用批次")

    @field_validator("code")
    @classmethod
    def _validate_code(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("编码不能为空")
        if len(value) < 2 or len(value) > 64:
            raise ValueError("编码长度需在 2-64 个字符之间")
        if not re.match(r"^[A-Za-z][A-Za-z0-9_\-\u4e00-\u9fff]*$", value):
            raise ValueError("编码需以字母开头，仅允许字母、数字、下划线、连字符和中文")
        return value

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("名称不能为空")
        return value

    @field_validator("status")
    @classmethod
    def _validate_status(cls, value: int) -> int:
        if value not in {0, 1}:
            raise ValueError("状态仅支持 0(正常) 或 1(禁用)")
        return value


class WmsMasterUpdateSchema(WmsMasterCreateSchema):
    pass


class WmsMasterOutSchema(WmsMasterCreateSchema, BaseSchema, UserBySchema, TenantBySchema):
    model_config = ConfigDict(from_attributes=True)


@dataclass
class WmsMasterQueryParam(BaseQueryParam, UserByQueryParam, TenantByQueryParam):
    code: str | None = Query(None, description="编码")
    name: str | None = Query(None, description="名称")
    status: int | None = Query(None, ge=0, le=1, description="状态")
    warehouse_id: int | None = Query(None, ge=1, description="仓库ID")
    zone_id: int | None = Query(None, ge=1, description="库区ID")
    category: str | None = Query(None, description="类别")
    is_demo: bool | None = Query(None, description="是否试用数据")

    def __post_init__(self) -> None:
        self.code = (QueueEnum.like.value, self.code)
        self.name = (QueueEnum.like.value, self.name)
        self.category = (QueueEnum.like.value, self.category)
        if isinstance(self.status, int):
            self.status = (QueueEnum.eq.value, self.status)
        if isinstance(self.warehouse_id, int):
            self.warehouse_id = (QueueEnum.eq.value, self.warehouse_id)
        if isinstance(self.zone_id, int):
            self.zone_id = (QueueEnum.eq.value, self.zone_id)
        if isinstance(self.is_demo, bool):
            self.is_demo = (QueueEnum.eq.value, self.is_demo)
