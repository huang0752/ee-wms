from decimal import Decimal

from sqlalchemy import func, select

from app.core.assembly import get_assembly
from app.core.base_schema import AuthSchema

from ..arrival.model import WmsArrivalOrderModel
from ..check.model import WmsStockCheckOrderModel
from ..inbound.model import WmsInboundOrderModel
from ..issue.model import WmsIssueOrderModel
from ..master.model import WmsMaterialModel, WmsWarehouseModel
from ..outbound.model import WmsOutboundOrderModel
from ..stock.model import WmsStockBalanceModel, WmsStockFlowModel
from ..transfer.model import WmsTransferOrderModel
from ..warning.model import WmsStockWarningModel
from .schema import WmsDashboardMetric, WmsDashboardStockStructure, WmsDashboardSummary, WmsDashboardTask, WmsDashboardTrendItem


class WmsDashboardService:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        self.db = auth.db

    async def summary(self) -> WmsDashboardSummary:
        assembly = get_assembly()
        warehouse_count = await self._count(WmsWarehouseModel)
        material_count = await self._count(WmsMaterialModel)
        batch_count = await self._count(WmsStockBalanceModel)
        pending_docs = 0
        for model in [WmsArrivalOrderModel, WmsInboundOrderModel, WmsOutboundOrderModel, WmsIssueOrderModel, WmsTransferOrderModel, WmsStockCheckOrderModel]:
            pending_docs += await self._count(model, model.status.not_in(["closed", "confirmed", "audited", "cancelled"]))
        open_warnings = await self._count(WmsStockWarningModel, WmsStockWarningModel.status == "open")
        return WmsDashboardSummary(
            assembly=assembly.name,
            metrics=[
                WmsDashboardMetric(label="仓库", value=warehouse_count, unit="个", status="normal"),
                WmsDashboardMetric(label="物料", value=material_count, unit="种", status="normal"),
                WmsDashboardMetric(label="库存批次", value=batch_count, unit="批", status="normal"),
                WmsDashboardMetric(label="待处理单据", value=pending_docs, unit="张", status="warning" if pending_docs else "normal"),
                WmsDashboardMetric(label="未关闭预警", value=open_warnings, unit="条", status="warning" if open_warnings else "normal"),
            ],
            tasks=[
                WmsDashboardTask(title="处理到货检验与入库", status="active", time=f"{await self._count(WmsArrivalOrderModel, WmsArrivalOrderModel.status != 'closed')} 张"),
                WmsDashboardTask(title="处理出库与生产领料", status="active", time=f"{await self._count(WmsOutboundOrderModel, WmsOutboundOrderModel.status.not_in(['confirmed','cancelled'])) + await self._count(WmsIssueOrderModel, WmsIssueOrderModel.status.not_in(['confirmed','cancelled']))} 张"),
                WmsDashboardTask(title="处理库存预警", status="active", time=f"{open_warnings} 条"),
            ],
            next_steps=[
                "按预警处理安全库存与短缺物料",
                "通过批次追溯核对入库、调拨、出库流水",
                "继续补齐试用数据和集成契约",
            ],
        )

    async def tasks(self) -> list[WmsDashboardTask]:
        summary = await self.summary()
        return summary.tasks

    async def stock_structure(self) -> WmsDashboardStockStructure:
        sums = {}
        for field in ["available_qty", "locked_qty", "frozen_qty", "pending_qty", "defective_qty"]:
            stmt = select(func.coalesce(func.sum(getattr(WmsStockBalanceModel, field)), 0)).where(WmsStockBalanceModel.tenant_id == self._tenant_id(), WmsStockBalanceModel.is_deleted.is_(False))
            sums[field] = str((await self.db.execute(stmt)).scalar_one() or Decimal("0"))
        return WmsDashboardStockStructure(**sums)

    async def trends(self) -> list[WmsDashboardTrendItem]:
        stmt = (
            select(WmsStockFlowModel.flow_type, func.coalesce(func.sum(WmsStockFlowModel.quantity), 0))
            .where(WmsStockFlowModel.tenant_id == self._tenant_id(), WmsStockFlowModel.is_deleted.is_(False))
            .group_by(WmsStockFlowModel.flow_type)
            .order_by(WmsStockFlowModel.flow_type.asc())
        )
        return [WmsDashboardTrendItem(flow_type=row[0], quantity=str(row[1])) for row in (await self.db.execute(stmt)).all()]

    async def warnings(self):
        rows = (await self.db.execute(select(WmsStockWarningModel).where(WmsStockWarningModel.tenant_id == self._tenant_id(), WmsStockWarningModel.is_deleted.is_(False)).order_by(WmsStockWarningModel.id.desc()).limit(10))).scalars().all()
        return rows

    async def latest_flows(self):
        rows = (await self.db.execute(select(WmsStockFlowModel).where(WmsStockFlowModel.tenant_id == self._tenant_id(), WmsStockFlowModel.is_deleted.is_(False)).order_by(WmsStockFlowModel.id.desc()).limit(20))).scalars().all()
        return rows

    async def _count(self, model: type, extra=None) -> int:
        stmt = select(func.count()).select_from(model).where(model.tenant_id == self._tenant_id(), model.is_deleted.is_(False))
        if extra is not None:
            stmt = stmt.where(extra)
        return (await self.db.execute(stmt)).scalar_one() or 0

    def _tenant_id(self) -> int:
        return self.auth.tenant_id or 1
