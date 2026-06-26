from pydantic import BaseModel, Field


class WmsDashboardMetric(BaseModel):
    label: str = Field(description="指标名称")
    value: int | str = Field(description="指标值")
    unit: str | None = Field(default=None, description="单位")
    status: str = Field(default="normal", description="状态")


class WmsDashboardTask(BaseModel):
    title: str = Field(description="任务标题")
    status: str = Field(description="状态")
    time: str = Field(description="时间描述")


class WmsDashboardSummary(BaseModel):
    assembly: str = Field(default="wms", description="当前产品装配")
    phase: str = Field(default="v1-running-loop", description="建设阶段")
    metrics: list[WmsDashboardMetric] = Field(default_factory=list, description="指标")
    tasks: list[WmsDashboardTask] = Field(default_factory=list, description="近期任务")
    next_steps: list[str] = Field(default_factory=list, description="下一步")


class WmsDashboardStockStructure(BaseModel):
    available_qty: str = Field(default="0", description="可用库存")
    locked_qty: str = Field(default="0", description="锁定库存")
    frozen_qty: str = Field(default="0", description="冻结库存")
    pending_qty: str = Field(default="0", description="待检库存")
    defective_qty: str = Field(default="0", description="不良库存")


class WmsDashboardTrendItem(BaseModel):
    flow_type: str = Field(description="流水类型")
    quantity: str = Field(description="数量")
