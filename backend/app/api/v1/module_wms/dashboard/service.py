from app.core.assembly import get_assembly

from .schema import WmsDashboardMetric, WmsDashboardSummary, WmsDashboardTask


class WmsDashboardService:
    @staticmethod
    async def summary() -> WmsDashboardSummary:
        assembly = get_assembly()
        return WmsDashboardSummary(
            assembly=assembly.name,
            metrics=[
                WmsDashboardMetric(label="仓库", value=0, unit="个", status="pending"),
                WmsDashboardMetric(label="物料", value=0, unit="种", status="pending"),
                WmsDashboardMetric(label="库存批次", value=0, unit="批", status="pending"),
                WmsDashboardMetric(label="待处理单据", value=0, unit="张", status="pending"),
            ],
            tasks=[
                WmsDashboardTask(title="建立仓储基础资料", status="next", time="Phase 1"),
                WmsDashboardTask(title="实现库存台账核心", status="planned", time="Phase 2"),
                WmsDashboardTask(title="打通出入库闭环", status="planned", time="Phase 3-4"),
            ],
            next_steps=[
                "补齐仓库、库区、库位、物料等主数据",
                "建立批次库存、流水和锁库服务",
                "在入库、出库、盘点流程中统一调用库存台账",
            ],
        )
