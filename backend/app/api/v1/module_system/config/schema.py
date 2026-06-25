from pydantic import BaseModel, Field


class AssemblySummaryOut(BaseModel):
    """前端可见的能力装配摘要。"""

    name: str = Field(..., description="装配名称")
    title: str = Field(..., description="装配标题")
    enabledRouteGroups: list[str] = Field(default_factory=list, description="启用的前端 route group，空表示全部启用")
    disabledRouteGroups: list[str] = Field(default_factory=list, description="禁用的前端 route group")
    featureFlags: dict[str, bool] = Field(default_factory=dict, description="前端功能开关")


class PublicConfigInfoOut(BaseModel):
    """公开配置摘要。"""

    assembly: AssemblySummaryOut = Field(..., description="能力装配摘要")
