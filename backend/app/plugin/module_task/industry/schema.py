from pydantic import BaseModel, Field


class IndustrySamplePackOut(BaseModel):
    """行业样例包。"""

    code: str = Field(..., description="样例包编码")
    name: str = Field(..., description="样例包名称")
    module: str = Field(..., description="适用模块")
    industry: str = Field(..., description="行业")
    description: str | None = Field(default=None, description="描述")
    examples: list[dict] = Field(default_factory=list, description="样例数据")


class IndustryTermOut(BaseModel):
    """行业词条。"""

    term: str = Field(..., description="词条")
    module: str = Field(..., description="适用模块")
    industry: str = Field(..., description="行业")
    aliases: list[str] = Field(default_factory=list, description="别名")
    description: str | None = Field(default=None, description="描述")
