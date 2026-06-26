from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import delete, func, select

from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException
from app.plugin.module_task.business.task.model import BusinessTaskModel
from app.plugin.module_task.business.task.schema import BusinessTaskCreateSchema, BusinessTaskUpdateSchema
from app.plugin.module_task.business.task.service import BusinessTaskService

from ..arrival.model import WmsArrivalLineModel, WmsArrivalOrderModel
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
from ..stock.ledger_service import WmsStockLedgerService
from ..stock.model import WmsStockBalanceModel, WmsStockBatchModel, WmsStockFlowModel, WmsStockLockModel, WmsTraceLinkModel
from ..stock.schema import WmsStockMutationSchema
from ..warning.model import WmsStockWarningModel
from .schema import WmsDemoBatchOut, WmsDemoCleanOut, WmsDemoInitSchema


class WmsDemoGenerator:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        if auth.db is None:
            raise CustomException(msg="数据库会话不存在")
        self.db = auth.db
        self.counts: dict[str, int] = {}

    async def generate(self, data: WmsDemoInitSchema) -> WmsDemoBatchOut:
        demo_batch_id = f"demo_wms_{uuid4().hex[:12]}"
        profile = data.profile
        task = await BusinessTaskService(self.auth).create(
            BusinessTaskCreateSchema(
                module="wms",
                biz_type="demo_batch_init",
                biz_id=demo_batch_id,
                title=f"{profile.company_name} WMS试用数据初始化",
                status="running",
                progress=30,
                payload=profile.model_dump(),
                is_demo=True,
                demo_batch_id=demo_batch_id,
            )
        )
        try:
            result = await self._generate_rows(demo_batch_id=demo_batch_id, data=data)
            await BusinessTaskService(self.auth).update_status(
                task.id or 0,
                BusinessTaskUpdateSchema(status="success", progress=100, result={"counts": result.counts, "summary": result.summary}),
            )
            await self.db.commit()
            return result.model_copy(update={"task_id": task.id or 0})
        except Exception as exc:
            if task.id:
                await BusinessTaskService(self.auth).update_status(
                    task.id,
                    BusinessTaskUpdateSchema(status="failed", progress=100, error=str(exc)),
                )
            raise

    async def clean(self, demo_batch_id: str) -> WmsDemoCleanOut:
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
        await self.db.commit()
        return WmsDemoCleanOut(demo_batch_id=demo_batch_id, counts=counts)

    async def _generate_rows(self, demo_batch_id: str, data: WmsDemoInitSchema) -> WmsDemoBatchOut:
        suffix = demo_batch_id[-6:].upper()
        now = datetime.now()
        warehouse = self._add(
            "warehouse",
            WmsWarehouseModel(
                code=f"DEMO-WH-{suffix}",
                name=f"{data.profile.company_name} 总仓",
                type="finished_and_raw",
                manager="试用管理员",
                status=0,
                description="WMS试用数据",
                **self._demo_fields(demo_batch_id),
            ),
        )
        await self.db.flush()
        for index in range(2, data.profile.warehouse_count + 1):
            self._add(
                "warehouse",
                WmsWarehouseModel(
                    code=f"DEMO-WH-{suffix}-{index}",
                    name=f"{data.profile.company_name} 分仓{index}",
                    type="overflow",
                    manager="试用管理员",
                    status=0,
                    description="WMS试用数据扩展仓",
                    **self._demo_fields(demo_batch_id),
                ),
            )
        zone = self._add(
            "zone",
            WmsZoneModel(
                code=f"DEMO-ZONE-{suffix}",
                name="A区-标准货架",
                warehouse_id=warehouse.id,
                usage="raw_and_finished",
                status=0,
                **self._demo_fields(demo_batch_id),
            ),
        )
        await self.db.flush()
        location = self._add(
            "location",
            WmsLocationModel(
                code=f"DEMO-LOC-{suffix}",
                name="A01-01-01",
                warehouse_id=warehouse.id,
                zone_id=zone.id,
                capacity=Decimal("1000"),
                category_constraints=["电子料", "成品"],
                mix_rule="same_material",
                status=0,
                **self._demo_fields(demo_batch_id),
            ),
        )
        supplier = self._add(
            "supplier",
            WmsSupplierModel(
                code=f"DEMO-SUP-{suffix}",
                name="深圳优选电子供应商",
                contact="陈经理",
                phone="13800000000",
                status=0,
                **self._demo_fields(demo_batch_id),
            ),
        )
        customer = self._add(
            "customer",
            WmsCustomerModel(
                code=f"DEMO-CUS-{suffix}",
                name="华东渠道客户",
                contact="王主管",
                phone="13900000000",
                status=0,
                **self._demo_fields(demo_batch_id),
            ),
        )
        material = self._add(
            "material",
            WmsMaterialModel(
                code=f"DEMO-MAT-{suffix}",
                name="智能控制板",
                spec="PCB-A1",
                unit="pcs",
                category="电子料",
                safety_stock=Decimal("20"),
                status=0,
                **self._demo_fields(demo_batch_id),
            ),
        )
        for index in range(2, data.profile.material_count + 1):
            self._add(
                "material",
                WmsMaterialModel(
                    code=f"DEMO-MAT-{suffix}-{index}",
                    name=f"试用物料{index}",
                    spec=f"SPEC-{index}",
                    unit="pcs",
                    category="电子料",
                    safety_stock=Decimal("10"),
                    status=0,
                    **self._demo_fields(demo_batch_id),
                ),
            )
        self._add(
            "barcode_rule",
            WmsBarcodeRuleModel(
                code=f"DEMO-BC-{suffix}",
                name="批次条码规则",
                object_type="batch",
                prefix="WMS",
                segment_strategy={"segments": ["prefix", "date", "sequence"]},
                status=0,
                **self._demo_fields(demo_batch_id),
            ),
        )
        await self.db.flush()

        batch_no = f"DEMO-BATCH-{suffix}"
        arrival = self._add(
            "arrival_order",
            WmsArrivalOrderModel(
                order_no=f"DAO-{suffix}",
                supplier_id=supplier.id,
                warehouse_id=warehouse.id,
                status="closed",
                received_time=now,
                external_source="manual",
                remark="试用数据到货单",
                **self._demo_fields(demo_batch_id),
            ),
        )
        await self.db.flush()
        arrival_line = self._add(
            "arrival_line",
            WmsArrivalLineModel(
                order_id=arrival.id,
                material_id=material.id,
                planned_qty=Decimal("120"),
                received_qty=Decimal("120"),
                inspected_qty=Decimal("120"),
                accepted_qty=Decimal("110"),
                rejected_qty=Decimal("10"),
                batch_no=batch_no,
                status="closed",
                **self._demo_fields(demo_batch_id),
            ),
        )
        inspection = self._add(
            "inspection_task",
            WmsInspectionTaskModel(
                task_no=f"DIQ-{suffix}",
                arrival_order_id=arrival.id,
                arrival_no=arrival.order_no,
                status="closed",
                result="accepted_with_defect",
                inspector_id=self._user_id(),
                inspected_time=now,
                remark="试用数据检验任务",
                **self._demo_fields(demo_batch_id),
            ),
        )
        await self.db.flush()
        inspection_line = self._add(
            "inspection_line",
            WmsInspectionLineModel(
                task_id=inspection.id,
                arrival_line_id=arrival_line.id,
                material_id=material.id,
                batch_no=batch_no,
                quantity=Decimal("120"),
                accepted_qty=Decimal("110"),
                rejected_qty=Decimal("10"),
                result="accepted_with_defect",
                status="closed",
                **self._demo_fields(demo_batch_id),
            ),
        )
        inbound = self._add(
            "inbound_order",
            WmsInboundOrderModel(
                order_no=f"DIN-{suffix}",
                inspection_task_id=inspection.id,
                arrival_order_id=arrival.id,
                warehouse_id=warehouse.id,
                location_id=location.id,
                status="confirmed",
                confirmed_time=now,
                external_source="manual",
                remark="试用数据入库单",
                **self._demo_fields(demo_batch_id),
            ),
        )
        await self.db.flush()
        self._add(
            "inbound_line",
            WmsInboundLineModel(
                order_id=inbound.id,
                inspection_line_id=inspection_line.id,
                material_id=material.id,
                warehouse_id=warehouse.id,
                location_id=location.id,
                batch_no=batch_no,
                quantity=Decimal("110"),
                stock_status="available",
                status="confirmed",
                **self._demo_fields(demo_batch_id),
            ),
        )
        await WmsStockLedgerService(self.auth).receive_pending(self._stock_payload(material.id, warehouse.id, location.id, batch_no, Decimal("120"), "arrival", arrival.order_no, demo_batch_id))
        await WmsStockLedgerService(self.auth).approve_to_available(self._stock_payload(material.id, warehouse.id, location.id, batch_no, Decimal("110"), "inbound", inbound.order_no, demo_batch_id))
        await WmsStockLedgerService(self.auth).reject_to_defective(self._stock_payload(material.id, warehouse.id, location.id, batch_no, Decimal("10"), "inspection", inspection.task_no, demo_batch_id))

        outbound = self._add(
            "outbound_order",
            WmsOutboundOrderModel(
                order_no=f"DOU-{suffix}",
                customer_id=customer.id,
                warehouse_id=warehouse.id,
                status="pending_reserve",
                external_source="manual",
                remark="试用数据销售出库单",
                **self._demo_fields(demo_batch_id),
            ),
        )
        issue = self._add(
            "issue_order",
            WmsIssueOrderModel(
                order_no=f"DIS-{suffix}",
                work_order_no=f"MO-{suffix}",
                warehouse_id=warehouse.id,
                status="pending_reserve",
                external_source="manual",
                remark="试用数据生产领料单",
                **self._demo_fields(demo_batch_id),
            ),
        )
        await self.db.flush()
        self._add(
            "outbound_line",
            WmsOutboundLineModel(
                order_id=outbound.id,
                material_id=material.id,
                warehouse_id=warehouse.id,
                location_id=location.id,
                batch_no=batch_no,
                requested_qty=Decimal("30"),
                status="pending_reserve",
                **self._demo_fields(demo_batch_id),
            ),
        )
        self._add(
            "issue_line",
            WmsIssueLineModel(
                order_id=issue.id,
                material_id=material.id,
                warehouse_id=warehouse.id,
                location_id=location.id,
                batch_no=batch_no,
                requested_qty=Decimal("25"),
                status="pending_reserve",
                **self._demo_fields(demo_batch_id),
            ),
        )
        self._add(
            "warning",
            WmsStockWarningModel(
                warning_no=f"DWR-{suffix}",
                warning_type="safety_stock",
                material_id=material.id,
                warehouse_id=warehouse.id,
                batch_no=batch_no,
                current_qty=Decimal("110"),
                threshold_qty=Decimal("150"),
                status="open",
                remark="试用数据安全库存预警",
                **self._demo_fields(demo_batch_id),
            ),
        )
        self._add(
            "trace_link",
            WmsTraceLinkModel(
                source_type="arrival",
                source_id=arrival.id,
                source_no=arrival.order_no,
                target_type="inbound",
                target_id=inbound.id,
                target_no=inbound.order_no,
                relation_type="material_batch",
                material_id=material.id,
                batch_no=batch_no,
                **self._demo_fields(demo_batch_id),
            ),
        )
        await self.db.flush()
        summary = [
            f"已生成仓库 {warehouse.name}",
            f"已生成物料 {material.name} 与批次 {batch_no}",
            "已生成到货、检验、入库、出库、领料、预警和追溯样例",
        ]
        return WmsDemoBatchOut(module="wms", scenario=data.profile.scenario, demo_batch_id=demo_batch_id, task_id=0, counts=self.counts, summary=summary)

    def _stock_payload(self, material_id: int, warehouse_id: int, location_id: int, batch_no: str, quantity: Decimal, document_type: str, document_no: str, demo_batch_id: str) -> WmsStockMutationSchema:
        return WmsStockMutationSchema(
            material_id=material_id,
            warehouse_id=warehouse_id,
            location_id=location_id,
            batch_no=batch_no,
            quantity=quantity,
            document_type=document_type,
            document_no=document_no,
            is_demo=True,
            demo_batch_id=demo_batch_id,
        )

    def _add(self, label: str, obj):
        self.db.add(obj)
        self.counts[label] = self.counts.get(label, 0) + 1
        return obj

    def _demo_fields(self, demo_batch_id: str) -> dict:
        return {
            "tenant_id": self._tenant_id(),
            "created_id": self._user_id(),
            "updated_id": self._user_id(),
            "is_demo": True,
            "demo_batch_id": demo_batch_id,
        }

    def _tenant_id(self) -> int:
        return self.auth.tenant_id or 1

    def _user_id(self) -> int | None:
        user = self.auth.get_user()
        return getattr(user, "id", None)

    def _delete_order(self) -> list[tuple[str, type]]:
        return [
            ("warning", WmsStockWarningModel),
            ("trace_link", WmsTraceLinkModel),
            ("stock_lock", WmsStockLockModel),
            ("stock_flow", WmsStockFlowModel),
            ("stock_balance", WmsStockBalanceModel),
            ("stock_batch", WmsStockBatchModel),
            ("outbound_line", WmsOutboundLineModel),
            ("outbound_order", WmsOutboundOrderModel),
            ("issue_line", WmsIssueLineModel),
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
        stmt = select(func.count()).select_from(model).where(model.tenant_id == self._tenant_id(), model.is_demo.is_(True), model.demo_batch_id == demo_batch_id)
        return (await self.db.execute(stmt)).scalar_one() or 0
