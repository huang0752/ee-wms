from dataclasses import dataclass
from typing import Literal

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.common.enums import QueueEnum
from app.core.base_params import BaseQueryParam, TenantByQueryParam, UserByQueryParam
from app.core.base_schema import BaseSchema, TenantBySchema, UserBySchema

BusinessTaskStatus = Literal["pending", "running", "success", "failed", "canceled"]


class BusinessTaskCreateSchema(BaseModel):
    """业务长任务创建模型。"""

    module: str = Field(..., min_length=1, max_length=64, description="业务模块")
    biz_type: str = Field(..., min_length=1, max_length=64, description="业务类型")
    biz_id: str | None = Field(default=None, max_length=128, description="业务对象ID")
    title: str | None = Field(default=None, max_length=128, description="任务标题")
    status: BusinessTaskStatus = Field(default="pending", description="任务状态")
    progress: int = Field(default=0, ge=0, le=100, description="进度百分比")
    payload: dict | None = Field(default=None, description="任务输入")
    result: dict | None = Field(default=None, description="任务结果")
    error: str | None = Field(default=None, max_length=65535, description="错误信息")
    is_demo: bool = Field(default=False, description="是否试用数据")
    demo_batch_id: str | None = Field(default=None, max_length=64, description="试用数据批次ID")
    description: str | None = Field(default=None, max_length=255, description="备注")

    @field_validator("module", "biz_type", "biz_id", "title", "demo_batch_id")
    @classmethod
    def _strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        return value or None


class BusinessTaskUpdateSchema(BaseModel):
    """业务长任务状态更新模型。"""

    status: BusinessTaskStatus | None = Field(default=None, description="任务状态")
    progress: int | None = Field(default=None, ge=0, le=100, description="进度百分比")
    result: dict | None = Field(default=None, description="任务结果")
    error: str | None = Field(default=None, max_length=65535, description="错误信息")


class BusinessTaskOutSchema(BusinessTaskCreateSchema, BaseSchema, UserBySchema, TenantBySchema):
    """业务长任务响应模型。"""

    model_config = ConfigDict(from_attributes=True)


@dataclass
class BusinessTaskQueryParam(BaseQueryParam, UserByQueryParam, TenantByQueryParam):
    """业务长任务查询参数。"""

    module: str | None = Query(None, description="业务模块")
    biz_type: str | None = Query(None, description="业务类型")
    biz_id: str | None = Query(None, description="业务对象ID")
    status: str | None = Query(None, description="任务状态")
    is_demo: bool | None = Query(None, description="是否试用数据")
    demo_batch_id: str | None = Query(None, description="试用数据批次ID")

    def __post_init__(self) -> None:
        if self.module:
            self.module = (QueueEnum.eq.value, self.module)
        if self.biz_type:
            self.biz_type = (QueueEnum.eq.value, self.biz_type)
        if self.biz_id:
            self.biz_id = (QueueEnum.eq.value, self.biz_id)
        if self.status:
            self.status = (QueueEnum.eq.value, self.status)
        if self.is_demo is not None:
            self.is_demo = (QueueEnum.eq.value, self.is_demo)
        if self.demo_batch_id:
            self.demo_batch_id = (QueueEnum.eq.value, self.demo_batch_id)


class DemoBatchTriggerSchema(BaseModel):
    """试用数据初始化触发模型。"""

    module: str = Field(..., min_length=1, max_length=64, description="业务模块")
    scenario: str = Field(default="starter", min_length=1, max_length=64, description="试用场景")
    payload: dict | None = Field(default=None, description="初始化参数")


class DemoBatchOutSchema(BaseModel):
    """试用数据批次响应模型。"""

    module: str
    scenario: str
    is_demo: bool = True
    demo_batch_id: str
    task_id: int


class DemoBatchCleanOutSchema(BaseModel):
    """试用数据清理响应模型。"""

    demo_batch_id: str
    task_id: int
