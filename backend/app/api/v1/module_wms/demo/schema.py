from typing import Literal

from pydantic import BaseModel, Field


class WmsDemoEnterpriseProfile(BaseModel):
    company_name: str = Field(default="华南智能制造有限公司", max_length=128, description="企业名称")
    industry: str = Field(default="智能制造", max_length=64, description="行业")
    company_size: Literal["small", "medium", "large"] = Field(default="medium", description="企业规模")
    warehouse_count: int | None = Field(default=None, ge=1, le=8, description="兼容旧版：仓库数量")
    material_count: int | None = Field(default=None, ge=1, le=600, description="兼容旧版：物料数量")
    scenario: str = Field(default="starter", max_length=64, description="样例场景")


class WmsDemoQuantityTargets(BaseModel):
    warehouse_count: int | None = Field(default=None, ge=1, le=8, description="仓库数量")
    location_count: int | None = Field(default=None, ge=10, le=1000, description="库位数量")
    material_count: int | None = Field(default=None, ge=10, le=600, description="物料数量")
    stock_flow_count: int | None = Field(default=None, ge=20, le=5000, description="库存流水数量")
    business_doc_count: int | None = Field(default=None, ge=20, le=1500, description="业务单据数量")
    warning_count: int | None = Field(default=None, ge=0, le=200, description="预警数量")


class WmsDemoCustomProduct(BaseModel):
    name: str = Field(..., min_length=1, max_length=80, description="产品名称")
    category: str | None = Field(default=None, max_length=64, description="品类")
    voltage_level: str | None = Field(default=None, max_length=32, description="电压等级")
    spec_examples: list[str] = Field(default_factory=list, max_length=20, description="规格示例")
    unit: str | None = Field(default=None, max_length=16, description="单位")
    storage_traits: list[str] = Field(default_factory=list, max_length=10, description="仓储特性")
    quality_requirements: str | None = Field(default=None, max_length=500, description="质量要求")
    supplier_requirement: str | None = Field(default=None, max_length=300, description="供应商要求")
    weight: int = Field(default=1, ge=1, le=10, description="权重")


class WmsDemoNumberingProfile(BaseModel):
    tenant_short_code: str | None = Field(default=None, max_length=16, description="租户短码")
    numbering_style: Literal["default", "tenant", "traceable_demo"] = Field(default="tenant", description="编号风格")
    date_format: Literal["yyyyMMdd", "yyMMdd", "yyyyMM"] = Field(default="yyyyMMdd", description="日期格式")
    sequence_digits: int = Field(default=4, ge=4, le=8, description="流水位数")
    include_demo_suffix: bool = Field(default=False, description="是否附加演示批次短码")
    prefixes: dict[str, str] = Field(default_factory=dict, description="对象前缀")


class WmsDemoInitSchema(BaseModel):
    profile: WmsDemoEnterpriseProfile = Field(default_factory=WmsDemoEnterpriseProfile, description="企业画像")
    sample_pool_id: int | None = Field(default=None, ge=1, description="样本池ID")
    numbering: WmsDemoNumberingProfile = Field(default_factory=WmsDemoNumberingProfile, description="编号规则")
    product_directions: list[str] = Field(default_factory=list, max_length=20, description="产品方向")
    custom_products: list[WmsDemoCustomProduct] = Field(default_factory=list, max_length=80, description="自定义产品")
    warehouse_scenarios: list[str] = Field(default_factory=list, max_length=10, description="仓储场景")
    scale_mode: Literal["quick", "standard", "rich", "custom"] = Field(default="standard", description="规模模式")
    quantity_targets: WmsDemoQuantityTargets = Field(default_factory=WmsDemoQuantityTargets, description="数量目标")
    time_range_days: int = Field(default=90, ge=7, le=180, description="时间范围")
    naming_style: Literal["industrial", "compact", "tenant"] = Field(default="industrial", description="命名风格")
    quality_requirements: str | None = Field(default=None, max_length=1000, description="质量要求")
    generation_instructions: str | None = Field(default=None, max_length=1500, description="生成要求")
    use_ai_enrichment: bool = Field(default=True, description="是否启用AI增强")


class WmsDemoPreviewOut(BaseModel):
    sample_pool_name: str = Field(description="样本池名称")
    scale_mode: str = Field(description="规模模式")
    estimated_counts: dict[str, int] = Field(default_factory=dict, description="预估数量")
    product_mix: list[dict] = Field(default_factory=list, description="产品混合")
    workflow_coverage: list[str] = Field(default_factory=list, description="流程覆盖")
    warnings: list[str] = Field(default_factory=list, description="预览警告")
    preview_names: dict[str, list[str]] = Field(default_factory=dict, description="预览名称")


class WmsDemoBatchOut(BaseModel):
    module: str = Field(default="wms", description="模块")
    scenario: str = Field(description="样例场景")
    demo_batch_id: str = Field(description="试用数据批次")
    task_id: int = Field(description="业务任务ID")
    counts: dict[str, int] = Field(default_factory=dict, description="生成数量")
    summary: list[str] = Field(default_factory=list, description="初始化摘要")
    preview_snapshot: dict | None = Field(default=None, description="预览快照")
    quality_report: dict | None = Field(default=None, description="质量报告")


class WmsDemoCleanOut(BaseModel):
    demo_batch_id: str = Field(description="试用数据批次")
    counts: dict[str, int] = Field(default_factory=dict, description="清理数量")


class WmsDemoHistoryOut(BaseModel):
    id: int = Field(description="任务ID")
    demo_batch_id: str | None = Field(default=None, description="试用数据批次")
    title: str = Field(description="任务标题")
    status: str = Field(description="状态")
    progress: int | None = Field(default=None, description="进度")
    payload: dict | None = Field(default=None, description="请求载荷")
    result: dict | None = Field(default=None, description="任务结果")
