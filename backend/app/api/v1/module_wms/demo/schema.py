from pydantic import BaseModel, Field


class WmsDemoEnterpriseProfile(BaseModel):
    company_name: str = Field(default="华南智能制造有限公司", max_length=128, description="企业名称")
    industry: str = Field(default="智能制造", max_length=64, description="行业")
    warehouse_count: int = Field(default=1, ge=1, le=3, description="仓库数量")
    material_count: int = Field(default=3, ge=1, le=20, description="物料数量")
    scenario: str = Field(default="starter", max_length=64, description="样例场景")


class WmsDemoInitSchema(BaseModel):
    profile: WmsDemoEnterpriseProfile = Field(default_factory=WmsDemoEnterpriseProfile, description="企业画像")


class WmsDemoBatchOut(BaseModel):
    module: str = Field(default="wms", description="模块")
    scenario: str = Field(description="样例场景")
    demo_batch_id: str = Field(description="试用数据批次")
    task_id: int = Field(description="业务任务ID")
    counts: dict[str, int] = Field(default_factory=dict, description="生成数量")
    summary: list[str] = Field(default_factory=list, description="初始化摘要")


class WmsDemoCleanOut(BaseModel):
    demo_batch_id: str = Field(description="试用数据批次")
    counts: dict[str, int] = Field(default_factory=dict, description="清理数量")
