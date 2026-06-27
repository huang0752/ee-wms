from uuid import uuid4

from sqlalchemy import delete, func, select

from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException
from app.plugin.module_task.business.task.model import BusinessTaskModel
from app.plugin.module_task.business.task.schema import BusinessTaskCreateSchema, BusinessTaskUpdateSchema
from app.plugin.module_task.business.task.service import BusinessTaskService

from ..arrival.model import WmsArrivalLineModel, WmsArrivalOrderModel
from ..check.model import WmsStockCheckLineModel, WmsStockCheckOrderModel
from ..inbound.model import WmsInboundLineModel, WmsInboundOrderModel
from ..inspection.model import WmsInspectionLineModel, WmsInspectionTaskModel
from ..issue.model import WmsIssueLineModel, WmsIssueOrderModel
from ..master.model import (
    WmsBarcodeRuleModel,
    WmsCustomerModel,
    WmsLocationModel,
    WmsMaterialModel,
    WmsSupplierModel,
    WmsWarehouseModel,
    WmsZoneModel,
)
from ..outbound.model import WmsOutboundLineModel, WmsOutboundOrderModel
from ..stock.model import WmsStockBalanceModel, WmsStockBatchModel, WmsStockFlowModel, WmsStockLockModel, WmsTraceLinkModel
from ..transfer.model import WmsTransferLineModel, WmsTransferOrderModel
from ..warning.model import WmsStockWarningModel
from .enrichment_service import WmsDemoEnrichmentService
from .planner import WmsDemoPlanner
from .quality import WmsDemoQualityService
from .schema import WmsDemoBatchOut, WmsDemoCleanOut, WmsDemoInitSchema
from .writer import WmsDemoWriter


class WmsDemoGenerator:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        if auth.db is None:
            raise CustomException(msg="数据库会话不存在")
        self.db = auth.db

    async def generate(self, data: WmsDemoInitSchema) -> WmsDemoBatchOut:
        await self._handle_batch_policy(data)
        demo_batch_id = f"demo_wms_{uuid4().hex[:12]}"
        plan = await WmsDemoPlanner(self.auth).build(data, demo_batch_id=demo_batch_id)
        plan.enrichment = await WmsDemoEnrichmentService(self.auth).enrich(data, plan.product_mix)
        preview_snapshot = plan.preview().model_dump(mode="json")
        task = await BusinessTaskService(self.auth).create(
            BusinessTaskCreateSchema(
                module="wms",
                biz_type="demo_batch_init",
                biz_id=demo_batch_id,
                title=f"{data.profile.company_name} WMS试用数据初始化",
                status="running",
                progress=30,
                payload=data.model_dump(mode="json"),
                is_demo=True,
                demo_batch_id=demo_batch_id,
            )
        )
        try:
            counts, summary = await WmsDemoWriter(self.auth).write(plan, demo_batch_id)
            quality_report = WmsDemoQualityService.persisted_report(plan, counts)
            result = WmsDemoBatchOut(
                module="wms",
                scenario=data.profile.scenario,
                demo_batch_id=demo_batch_id,
                task_id=task.id or 0,
                counts=counts,
                summary=summary,
                preview_snapshot=preview_snapshot,
                quality_report=quality_report,
            )
            await BusinessTaskService(self.auth).update_status(
                task.id or 0,
                BusinessTaskUpdateSchema(
                    status="success",
                    progress=100,
                    result={
                        "counts": result.counts,
                        "summary": result.summary,
                        "preview_snapshot": preview_snapshot,
                        "quality_report": quality_report,
                    },
                ),
            )
            await self.db.commit()
            return result
        except Exception as exc:
            if task.id:
                await BusinessTaskService(self.auth).update_status(
                    task.id,
                    BusinessTaskUpdateSchema(status="failed", progress=100, error=str(exc)),
                )
                await self.db.commit()
            raise

    async def clean(self, demo_batch_id: str) -> WmsDemoCleanOut:
        counts = await self._delete_demo_rows(demo_batch_id)
        await self.db.commit()
        return WmsDemoCleanOut(demo_batch_id=demo_batch_id, counts=counts)

    async def _delete_demo_rows(self, demo_batch_id: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for label, model in self._delete_order():
            stmt = (
                delete(model)
                .where(
                    model.tenant_id == self._tenant_id(),
                    model.is_demo.is_(True),
                    model.demo_batch_id == demo_batch_id,
                )
                .execution_options(synchronize_session=False)
            )
            result = await self.db.execute(stmt)
            counts[label] = result.rowcount or 0
        return counts

    def _tenant_id(self) -> int:
        return self.auth.tenant_id or 1

    async def _handle_batch_policy(self, data: WmsDemoInitSchema) -> None:
        existing = await self._latest_demo_batch_id()
        if not existing or data.batch_policy == "append":
            return
        if data.batch_policy == "reject_if_exists":
            raise CustomException(msg=f"已存在试用数据批次 {existing}，请先清理或选择覆盖重建", status_code=400)
        await self._delete_demo_rows(existing)

    async def _latest_demo_batch_id(self) -> str | None:
        stmt = (
            select(BusinessTaskModel.demo_batch_id)
            .where(
                BusinessTaskModel.module == "wms",
                BusinessTaskModel.biz_type == "demo_batch_init",
                BusinessTaskModel.tenant_id == self._tenant_id(),
                BusinessTaskModel.is_demo.is_(True),
                BusinessTaskModel.demo_batch_id.is_not(None),
                BusinessTaskModel.is_deleted.is_(False),
            )
            .order_by(BusinessTaskModel.created_time.desc())
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalars().first()

    @staticmethod
    def _delete_order() -> list[tuple[str, type]]:
        return [
            ("warning", WmsStockWarningModel),
            ("trace_link", WmsTraceLinkModel),
            ("stock_check_line", WmsStockCheckLineModel),
            ("stock_check_order", WmsStockCheckOrderModel),
            ("transfer_line", WmsTransferLineModel),
            ("transfer_order", WmsTransferOrderModel),
            ("outbound_line", WmsOutboundLineModel),
            ("issue_line", WmsIssueLineModel),
            ("stock_flow", WmsStockFlowModel),
            ("stock_lock", WmsStockLockModel),
            ("stock_balance", WmsStockBalanceModel),
            ("stock_batch", WmsStockBatchModel),
            ("outbound_order", WmsOutboundOrderModel),
            ("issue_order", WmsIssueOrderModel),
            ("inbound_line", WmsInboundLineModel),
            ("inbound_order", WmsInboundOrderModel),
            ("inspection_line", WmsInspectionLineModel),
            ("inspection_task", WmsInspectionTaskModel),
            ("arrival_line", WmsArrivalLineModel),
            ("arrival_order", WmsArrivalOrderModel),
            ("barcode_rule", WmsBarcodeRuleModel),
            ("customer", WmsCustomerModel),
            ("supplier", WmsSupplierModel),
            ("material", WmsMaterialModel),
            ("location", WmsLocationModel),
            ("zone", WmsZoneModel),
            ("warehouse", WmsWarehouseModel),
            ("business_task", BusinessTaskModel),
        ]

    async def demo_count(self, model: type, demo_batch_id: str) -> int:
        stmt = select(func.count()).select_from(model).where(
            model.tenant_id == self._tenant_id(),
            model.is_demo.is_(True),
            model.demo_batch_id == demo_batch_id,
        )
        return (await self.db.execute(stmt)).scalar_one() or 0
