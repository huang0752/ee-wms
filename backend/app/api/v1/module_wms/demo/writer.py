from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from math import ceil

from sqlalchemy import func, select

from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException

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
from ..stock.ledger_service import WmsStockLedgerService
from ..stock.model import WmsStockBalanceModel, WmsStockBatchModel, WmsStockFlowModel, WmsStockLockModel, WmsTraceLinkModel
from ..stock.schema import WmsStockLockSchema
from ..transfer.model import WmsTransferLineModel, WmsTransferOrderModel
from ..warning.model import WmsStockWarningModel
from .codecs import safe_category_code
from .numbering import WmsDemoNumbering
from .planner import DemoPlan


class WmsDemoWriter:
    WAREHOUSE_NAMES = ["中心原材料仓", "高压成套成品仓", "电缆盘具仓", "二次设备恒温仓", "区域备件仓", "不良隔离仓"]
    ZONE_NAMES = ["待检暂存区", "合格品区", "重型设备区", "电子防静电区", "盘具线缆区", "不良隔离区", "发运备货区", "循环盘点区"]
    SUPPLIER_NAMES = ["华中变压器组件有限公司", "长江电气铁芯股份", "华东开关机构有限公司", "南方绝缘件制造", "江南电缆材料有限公司", "南京继保设备有限公司", "珠三角铜排科技"]
    CUSTOMER_NAMES = ["国网华东工程项目部", "南网配电设备改造项目", "西北新能源升压站项目", "华中城市配网改造项目", "沿海输变电扩建项目", "轨道交通供电集成项目"]
    SOURCE_CYCLE = ["erp", "mes", "pda", "manual", "integration"]
    SYNC_CYCLE = ["synced", "synced", "pending", "not_required", "failed"]
    OUTBOUND_STATUSES = ["confirmed", "reviewed", "picked", "reserved", "pending_reserve"]
    ISSUE_STATUSES = ["confirmed", "picked", "reserved", "pending_reserve"]

    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        if auth.db is None:
            raise CustomException(msg="数据库会话不存在")
        self.db = auth.db
        self.counts: dict[str, int] = {}

    async def write(self, plan: DemoPlan, demo_batch_id: str) -> tuple[dict[str, int], list[str]]:
        numbering = WmsDemoNumbering(self.auth, plan.request.numbering, demo_batch_id=demo_batch_id)
        warehouses = await self._warehouses(plan, numbering, demo_batch_id)
        zones = await self._zones(plan, numbering, warehouses, demo_batch_id)
        locations = await self._locations(plan, numbering, warehouses, zones, demo_batch_id)
        suppliers = await self._suppliers(plan, numbering, demo_batch_id)
        customers = await self._customers(plan, numbering, demo_batch_id)
        materials = await self._materials(plan, numbering, demo_batch_id)
        await self._barcode_rules(numbering, demo_batch_id)
        balances = await self._stock_cycle(plan, numbering, warehouses, locations, suppliers, materials, demo_batch_id)
        await self._outbound_and_issue(plan, numbering, warehouses, locations, customers, materials, balances, demo_batch_id)
        if not plan.legacy_mode and plan.request.scale_mode != "quick":
            await self._transfer_and_check(plan, numbering, warehouses, locations, materials, balances, demo_batch_id)
        await self._warnings(plan, numbering, warehouses, materials, balances, demo_batch_id)
        await self.db.flush()
        counts = await self._persisted_counts(demo_batch_id)
        return counts, self._summary(plan, counts)

    async def _warehouses(self, plan: DemoPlan, numbering: WmsDemoNumbering, demo_batch_id: str) -> list[WmsWarehouseModel]:
        result = []
        for index in range(plan.counts["warehouse"]):
            name = self._enriched_name(plan.enrichment.warehouses if plan.enrichment else [], index)
            fallback_name = self.WAREHOUSE_NAMES[index % len(self.WAREHOUSE_NAMES)]
            obj = WmsWarehouseModel(
                code=self._code(plan, numbering, "warehouse"),
                name=name or f"{plan.request.profile.company_name}-{fallback_name}",
                type=["raw", "finished", "line_side", "regional", "defective"][index % 5],
                manager=["张工", "李主管", "王经理", "赵班长"][index % 4],
                status=0,
                description=f"{fallback_name}，用于{plan.request.profile.industry}演示数据",
                **self._demo_fields(demo_batch_id),
            )
            self._add("warehouse", obj)
            result.append(obj)
        await self.db.flush()
        return result

    async def _zones(
        self,
        plan: DemoPlan,
        numbering: WmsDemoNumbering,
        warehouses: list[WmsWarehouseModel],
        demo_batch_id: str,
    ) -> list[WmsZoneModel]:
        result = []
        for index in range(plan.counts["zone"]):
            warehouse = warehouses[index % len(warehouses)]
            name = self._enriched_name(plan.enrichment.zones if plan.enrichment else [], index)
            zone_name = self.ZONE_NAMES[index % len(self.ZONE_NAMES)]
            obj = WmsZoneModel(
                code=self._code(plan, numbering, "zone", parent_code=warehouse.code),
                name=name or f"{warehouse.name}-{zone_name}",
                warehouse_id=warehouse.id,
                usage=["receiving", "qualified", "shipping", "inspection", "defective"][index % 5],
                status=0,
                **self._demo_fields(demo_batch_id),
            )
            self._add("zone", obj)
            result.append(obj)
        await self.db.flush()
        return result

    async def _locations(
        self,
        plan: DemoPlan,
        numbering: WmsDemoNumbering,
        warehouses: list[WmsWarehouseModel],
        zones: list[WmsZoneModel],
        demo_batch_id: str,
    ) -> list[WmsLocationModel]:
        result = []
        for index in range(plan.counts["location"]):
            zone = zones[index % len(zones)]
            warehouse = next(item for item in warehouses if item.id == zone.warehouse_id)
            row = index // 10 + 1
            col = index % 10 + 1
            obj = WmsLocationModel(
                code=self._code(plan, numbering, "location", parent_code=zone.code),
                name=f"{zone.name}-{row:02d}-{col:02d}",
                warehouse_id=warehouse.id,
                zone_id=zone.id,
                capacity=Decimal(500 + (index % 8) * 250),
                category_constraints=["电工装备", "关键物资", "需检物资"] if index % 3 == 0 else ["电工装备"],
                mix_rule=["same_material", "same_batch", "same_category"][index % 3],
                status=0,
                **self._demo_fields(demo_batch_id),
            )
            self._add("location", obj)
            result.append(obj)
        await self.db.flush()
        return result

    async def _suppliers(self, plan: DemoPlan, numbering: WmsDemoNumbering, demo_batch_id: str) -> list[WmsSupplierModel]:
        result = []
        for index in range(plan.counts["supplier"]):
            product = plan.product_mix[index % len(plan.product_mix)]
            name = self._enriched_name(plan.enrichment.suppliers if plan.enrichment else [], index)
            name = name or (product.get("supplier_patterns") or [self.SUPPLIER_NAMES[index % len(self.SUPPLIER_NAMES)]])[0]
            obj = WmsSupplierModel(
                code=self._code(plan, numbering, "supplier"),
                name=name if index < len(self.SUPPLIER_NAMES) else f"{name}{index + 1}",
                contact=["供应链经理", "质量接口人", "计划主管"][index % 3],
                phone=f"1380000{index + 1:04d}",
                status=0,
                **self._demo_fields(demo_batch_id),
            )
            self._add("supplier", obj)
            result.append(obj)
        await self.db.flush()
        return result

    async def _customers(self, plan: DemoPlan, numbering: WmsDemoNumbering, demo_batch_id: str) -> list[WmsCustomerModel]:
        result = []
        for index in range(plan.counts["customer"]):
            name = self._enriched_name(plan.enrichment.customers if plan.enrichment else [], index)
            obj = WmsCustomerModel(
                code=self._code(plan, numbering, "customer"),
                name=name or self.CUSTOMER_NAMES[index % len(self.CUSTOMER_NAMES)],
                contact=["项目经理", "物资负责人", "现场交付经理"][index % 3],
                phone=f"1390000{index + 1:04d}",
                status=0,
                **self._demo_fields(demo_batch_id),
            )
            self._add("customer", obj)
            result.append(obj)
        await self.db.flush()
        return result

    async def _materials(self, plan: DemoPlan, numbering: WmsDemoNumbering, demo_batch_id: str) -> list[WmsMaterialModel]:
        result = []
        for index, product in enumerate(plan.product_mix):
            spec_patterns = product.get("spec_patterns") or ["通用规格"]
            material_patterns = product.get("material_patterns") or [product["name"]]
            category = str(product.get("category") or "电工装备")
            enriched = self._enriched_material(plan, product, index)
            if enriched and enriched.category:
                category = enriched.category
            obj = WmsMaterialModel(
                code=self._code(plan, numbering, "material", category_short=safe_category_code(category)),
                name=enriched.name if enriched else f"{material_patterns[index % len(material_patterns)]}{index + 1}",
                spec=f"{(enriched.spec_hint if enriched and enriched.spec_hint else spec_patterns[index % len(spec_patterns)])}-{index + 1:03d}",
                unit=self._material_unit(str(product["name"]), category),
                category=category,
                batch_flag=True,
                sn_flag=category in {"二次设备", "表计"} or "继保" in str(product["name"]),
                safety_stock=Decimal(20 + (index % 10) * 5),
                status=0,
                **self._demo_fields(demo_batch_id),
            )
            self._add("material", obj)
            result.append(obj)
        await self.db.flush()
        return result

    async def _barcode_rules(self, numbering: WmsDemoNumbering, demo_batch_id: str) -> None:
        for object_type in ["material", "batch", "location", "document"]:
            self._add(
                "barcode_rule",
                WmsBarcodeRuleModel(
                    code=self._code(None, numbering, "barcode_rule"),
                    name=f"{object_type}条码规则",
                    object_type=object_type,
                    prefix=object_type.upper()[:3],
                    segment_strategy={"segments": ["tenant", "date", "sequence"], "source": "demo"},
                    status=0,
                    **self._demo_fields(demo_batch_id),
                ),
            )
        await self.db.flush()

    async def _stock_cycle(
        self,
        plan: DemoPlan,
        numbering: WmsDemoNumbering,
        warehouses: list[WmsWarehouseModel],
        locations: list[WmsLocationModel],
        suppliers: list[WmsSupplierModel],
        materials: list[WmsMaterialModel],
        demo_batch_id: str,
    ) -> list[WmsStockBalanceModel]:
        balances = []
        cycle_count = 1 if plan.legacy_mode else max(plan.counts.get("stock_balance", 0), ceil(plan.counts["stock_flow"] / 6), 1)
        for index in range(cycle_count):
            material = materials[index % len(materials)]
            warehouse = warehouses[index % len(warehouses)]
            location = locations[index % len(locations)]
            supplier = suppliers[index % len(suppliers)]
            batch_no = numbering.batch_no(material.code)
            qty = Decimal(80 + (index % 9) * 10)
            accepted = qty - Decimal(index % 4)
            rejected = qty - accepted
            frozen = Decimal(0 if index % 7 else 6 + index % 5)
            available = max(Decimal("0"), accepted - frozen)
            order_time = datetime.now() - timedelta(days=index % plan.request.time_range_days)
            source = self._source(index)
            sync_status = self._sync_status(index)

            arrival = self._add(
                "arrival_order",
                WmsArrivalOrderModel(
                    order_no=numbering.document_no("arrival"),
                    supplier_id=supplier.id,
                    warehouse_id=warehouse.id,
                    status="closed",
                    expected_time=order_time,
                    received_time=order_time,
                    external_source=source,
                    external_no=f"{source.upper()}-PO-{order_time:%Y%m%d}-{index + 1:04d}",
                    sync_status=sync_status,
                    workflow_instance_id=f"WF-ARR-{demo_batch_id[-6:]}-{index + 1:04d}",
                    remark=f"{supplier.name} {material.name} 到货，批次 {batch_no}",
                    **self._demo_fields(demo_batch_id),
                ),
            )
            await self.db.flush()
            arrival_line = self._add(
                "arrival_line",
                WmsArrivalLineModel(
                    order_id=arrival.id,
                    material_id=material.id,
                    planned_qty=qty,
                    received_qty=qty,
                    inspected_qty=qty,
                    accepted_qty=accepted,
                    rejected_qty=rejected,
                    batch_no=batch_no,
                    status="closed",
                    **self._demo_fields(demo_batch_id),
                ),
            )
            inspection = self._add(
                "inspection_task",
                WmsInspectionTaskModel(
                    task_no=numbering.document_no("inspection"),
                    arrival_order_id=arrival.id,
                    arrival_no=arrival.order_no,
                    status="closed",
                    result="accepted_with_defect" if rejected > 0 else "accepted",
                    inspector_id=self._user_id(),
                    inspected_time=order_time,
                    remark="外观、绝缘、附件齐套检验" if rejected == 0 else "存在轻微缺陷，合格品入库、不良品隔离",
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
                    quantity=qty,
                    accepted_qty=accepted,
                    rejected_qty=rejected,
                    result=inspection.result,
                    status="closed",
                    **self._demo_fields(demo_batch_id),
                ),
            )
            inbound = self._add(
                "inbound_order",
                WmsInboundOrderModel(
                    order_no=numbering.document_no("inbound"),
                    inspection_task_id=inspection.id,
                    arrival_order_id=arrival.id,
                    warehouse_id=warehouse.id,
                    location_id=location.id,
                    status="confirmed",
                    confirmed_time=order_time,
                    external_source=source,
                    external_no=f"{source.upper()}-IN-{order_time:%Y%m%d}-{index + 1:04d}",
                    sync_status=sync_status,
                    workflow_instance_id=f"WF-IN-{demo_batch_id[-6:]}-{index + 1:04d}",
                    remark=f"{material.name} 合格数量 {accepted} 入库到 {location.name}",
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
                    quantity=accepted,
                    stock_status="mixed" if rejected or frozen else "available",
                    status="confirmed",
                    **self._demo_fields(demo_batch_id),
                ),
            )
            self._add(
                "stock_batch",
                WmsStockBatchModel(
                    material_id=material.id,
                    warehouse_id=warehouse.id,
                    location_id=location.id,
                    batch_no=batch_no,
                    stock_status="mixed" if rejected or frozen else "available",
                    source_type="inbound",
                    source_no=inbound.order_no,
                    production_date=order_time,
                    **self._demo_fields(demo_batch_id),
                ),
            )
            balance = self._add(
                "stock_balance",
                WmsStockBalanceModel(
                    material_id=material.id,
                    warehouse_id=warehouse.id,
                    location_id=location.id,
                    batch_no=batch_no,
                    stock_status="mixed" if rejected or frozen else "available",
                    quantity=qty,
                    available_qty=available,
                    pending_qty=Decimal("0"),
                    defective_qty=rejected,
                    locked_qty=Decimal("0"),
                    frozen_qty=frozen,
                    **self._demo_fields(demo_batch_id),
                ),
            )
            await self.db.flush()
            self._flow(numbering, material, warehouse, location, balance, batch_no, qty, "receive_pending", "in", "arrival", arrival.order_no, demo_batch_id)
            self._flow(numbering, material, warehouse, location, balance, batch_no, accepted, "approve_to_available", "adjust", "inbound", inbound.order_no, demo_batch_id)
            if rejected:
                self._flow(numbering, material, warehouse, location, balance, batch_no, rejected, "reject_to_defective", "adjust", "inspection", inspection.task_no, demo_batch_id)
            if frozen:
                self._flow(numbering, material, warehouse, location, balance, batch_no, frozen, "freeze", "adjust", "quality_hold", inspection.task_no, demo_batch_id)
            self._flow(numbering, material, warehouse, location, balance, batch_no, Decimal(index % 6 + 1), "cycle_adjust", "adjust", "demo", demo_batch_id, demo_batch_id)
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
            balances.append(balance)
        await self.db.flush()
        return balances

    async def _outbound_and_issue(
        self,
        plan: DemoPlan,
        numbering: WmsDemoNumbering,
        warehouses: list[WmsWarehouseModel],
        locations: list[WmsLocationModel],
        customers: list[WmsCustomerModel],
        materials: list[WmsMaterialModel],
        balances: list[WmsStockBalanceModel],
        demo_batch_id: str,
    ) -> None:
        if plan.legacy_mode:
            doc_count = 1
        else:
            planned_docs = plan.fact_plan.counts if plan.fact_plan else {}
            doc_count = max(
                planned_docs.get("outbound_order", 0),
                planned_docs.get("issue_order", 0),
                2,
            )
            doc_count = min(doc_count, len(balances))
        ledger = WmsStockLedgerService(self.auth)
        for index in range(doc_count):
            balance = balances[index % len(balances)]
            material = materials[index % len(materials)]
            warehouse = warehouses[index % len(warehouses)]
            location = locations[index % len(locations)]
            customer = customers[index % len(customers)]
            if balance.available_qty <= 0:
                continue
            qty = min(Decimal(5 + index % 10), balance.available_qty)
            outbound_status = self.OUTBOUND_STATUSES[index % len(self.OUTBOUND_STATUSES)]
            issue_status = self.ISSUE_STATUSES[index % len(self.ISSUE_STATUSES)]
            outbound = self._add(
                "outbound_order",
                WmsOutboundOrderModel(
                    order_no=numbering.document_no("outbound"),
                    customer_id=customer.id,
                    warehouse_id=warehouse.id,
                    status=outbound_status,
                    picked_time=self._status_time(outbound_status, "picked"),
                    reviewed_time=self._status_time(outbound_status, "reviewed"),
                    confirmed_time=self._status_time(outbound_status, "confirmed"),
                    external_source=self._source(index + 1),
                    external_no=f"SO-{datetime.now():%Y%m%d}-{index + 1:04d}",
                    sync_status=self._sync_status(index + 1),
                    workflow_instance_id=f"WF-OUT-{demo_batch_id[-6:]}-{index + 1:04d}",
                    remark=f"{customer.name} 项目发运需求",
                    **self._demo_fields(demo_batch_id),
                ),
            )
            issue = self._add(
                "issue_order",
                WmsIssueOrderModel(
                    order_no=numbering.document_no("issue"),
                    work_order_no=numbering.document_no("work_order"),
                    warehouse_id=warehouse.id,
                    status=issue_status,
                    picked_time=self._status_time(issue_status, "picked"),
                    reviewed_time=self._status_time(issue_status, "reviewed"),
                    confirmed_time=self._status_time(issue_status, "confirmed"),
                    external_source=self._source(index + 2),
                    external_no=f"MES-MO-{datetime.now():%Y%m%d}-{index + 1:04d}",
                    sync_status=self._sync_status(index + 2),
                    workflow_instance_id=f"WF-ISS-{demo_batch_id[-6:]}-{index + 1:04d}",
                    remark=f"{material.name} 生产工单领料",
                    **self._demo_fields(demo_batch_id),
                ),
            )
            await self.db.flush()
            locks = await ledger.lock_stock(
                WmsStockLockSchema(
                    material_id=material.id,
                    warehouse_id=warehouse.id,
                    location_id=location.id,
                    quantity=qty,
                    document_type="outbound",
                    document_no=outbound.order_no,
                    remark="动态试用数据销售出库锁库",
                    is_demo=True,
                    demo_batch_id=demo_batch_id,
                )
            )
            lock_id = locks[0].id if locks else None
            shipped_qty = qty if outbound_status == "confirmed" else Decimal("0")
            if lock_id and outbound_status == "confirmed":
                await ledger.ship_locked(lock_id)
            self._add(
                "outbound_line",
                WmsOutboundLineModel(
                    order_id=outbound.id,
                    material_id=material.id,
                    warehouse_id=warehouse.id,
                    location_id=location.id,
                    batch_no=balance.batch_no,
                    requested_qty=qty,
                    locked_qty=qty,
                    shipped_qty=shipped_qty,
                    stock_lock_id=lock_id,
                    status=outbound_status,
                    **self._demo_fields(demo_batch_id),
                ),
            )
            issue_qty = min(Decimal(3 + index % 7), balance.available_qty)
            issue_lock_id = None
            issue_locked_qty = Decimal("0")
            issue_shipped_qty = Decimal("0")
            if issue_qty > 0:
                issue_locks = await ledger.lock_stock(
                    WmsStockLockSchema(
                        material_id=material.id,
                        warehouse_id=warehouse.id,
                        location_id=location.id,
                        quantity=issue_qty,
                        document_type="issue",
                        document_no=issue.order_no,
                        remark="动态试用数据生产领料锁库",
                        is_demo=True,
                        demo_batch_id=demo_batch_id,
                    )
                )
                issue_lock_id = issue_locks[0].id if issue_locks else None
                issue_locked_qty = issue_qty
                if issue_lock_id and issue_status == "confirmed":
                    await ledger.ship_locked(issue_lock_id)
                    issue_shipped_qty = issue_qty
            self._add(
                "issue_line",
                WmsIssueLineModel(
                    order_id=issue.id,
                    material_id=material.id,
                    warehouse_id=warehouse.id,
                    location_id=location.id,
                    batch_no=balance.batch_no,
                    requested_qty=issue_qty,
                    locked_qty=issue_locked_qty,
                    shipped_qty=issue_shipped_qty,
                    stock_lock_id=issue_lock_id,
                    status=issue_status,
                    **self._demo_fields(demo_batch_id),
                ),
            )
            self._trace("inbound", balance.id, balance.batch_no, "outbound", outbound.id, outbound.order_no, material.id, demo_batch_id)
            self._trace("inbound", balance.id, balance.batch_no, "issue", issue.id, issue.order_no, material.id, demo_batch_id)

    def _trace(
        self,
        source_type: str,
        source_id: int | None,
        batch_no: str | None,
        target_type: str,
        target_id: int | None,
        target_no: str | None,
        material_id: int,
        demo_batch_id: str,
    ) -> None:
        self._add(
            "trace_link",
            WmsTraceLinkModel(
                source_type=source_type,
                source_id=source_id,
                source_no=batch_no,
                target_type=target_type,
                target_id=target_id,
                target_no=target_no,
                relation_type="material_batch",
                material_id=material_id,
                batch_no=batch_no,
                **self._demo_fields(demo_batch_id),
            ),
        )

    async def _transfer_and_check(
        self,
        plan: DemoPlan,
        numbering: WmsDemoNumbering,
        warehouses: list[WmsWarehouseModel],
        locations: list[WmsLocationModel],
        materials: list[WmsMaterialModel],
        balances: list[WmsStockBalanceModel],
        demo_batch_id: str,
    ) -> None:
        planned_docs = plan.fact_plan.counts if plan.fact_plan else {}
        transfer_count = max(1, planned_docs.get("transfer_order", 1))
        check_count = max(1, planned_docs.get("stock_check_order", 1))
        for index in range(max(transfer_count, check_count)):
            from_wh = warehouses[index % len(warehouses)]
            to_wh = warehouses[(index + 1) % len(warehouses)] if len(warehouses) > 1 else warehouses[0]
            from_loc = locations[index % len(locations)]
            to_loc = locations[(index + 1) % len(locations)] if len(locations) > 1 else locations[0]
            material = materials[index % len(materials)]
            balance = balances[index % len(balances)]
            if index < transfer_count:
                transfer = self._add(
                    "transfer_order",
                    WmsTransferOrderModel(
                        order_no=numbering.document_no("transfer"),
                        from_warehouse_id=from_wh.id,
                        to_warehouse_id=to_wh.id,
                        status="confirmed",
                        confirmed_time=datetime.now(),
                        remark="动态试用数据调拨单",
                        **self._demo_fields(demo_batch_id),
                    ),
                )
                await self.db.flush()
                self._add(
                    "transfer_line",
                    WmsTransferLineModel(
                        order_id=transfer.id,
                        material_id=material.id,
                        from_warehouse_id=from_wh.id,
                        from_location_id=from_loc.id,
                        to_warehouse_id=to_wh.id,
                        to_location_id=to_loc.id,
                        batch_no=balance.batch_no,
                        quantity=Decimal("12"),
                        status="confirmed",
                        **self._demo_fields(demo_batch_id),
                    ),
                )
            if index < check_count:
                reason = self._enriched_name(plan.enrichment.check_reasons if plan.enrichment else [], index)
                check = self._add(
                    "stock_check_order",
                    WmsStockCheckOrderModel(
                        order_no=numbering.document_no("stock_check"),
                        warehouse_id=from_wh.id,
                        status="audited",
                        audited_time=datetime.now(),
                        remark=reason or "动态试用数据盘点单",
                        **self._demo_fields(demo_batch_id),
                    ),
                )
                await self.db.flush()
                self._add(
                    "stock_check_line",
                    WmsStockCheckLineModel(
                        order_id=check.id,
                        material_id=material.id,
                        warehouse_id=from_wh.id,
                        location_id=from_loc.id,
                        batch_no=balance.batch_no,
                        system_qty=balance.quantity,
                        counted_qty=balance.quantity - Decimal("1"),
                        diff_qty=Decimal("-1"),
                        status="audited",
                        **self._demo_fields(demo_batch_id),
                    ),
                )

    async def _warnings(
        self,
        plan: DemoPlan,
        numbering: WmsDemoNumbering,
        warehouses: list[WmsWarehouseModel],
        materials: list[WmsMaterialModel],
        balances: list[WmsStockBalanceModel],
        demo_batch_id: str,
    ) -> None:
        for index in range(plan.counts["warning"]):
            material = materials[index % len(materials)]
            balance = balances[index % len(balances)]
            warehouse = warehouses[index % len(warehouses)]
            reason = self._enriched_name(plan.enrichment.warning_reasons if plan.enrichment else [], index)
            status = "closed" if index % 4 == 0 else "open"
            self._add(
                "warning",
                WmsStockWarningModel(
                    warning_no=numbering.document_no("warning"),
                    warning_type=["safety_stock", "slow_moving", "quality_hold", "sync_failed"][index % 4],
                    material_id=material.id,
                    warehouse_id=warehouse.id,
                    batch_no=balance.batch_no,
                    current_qty=balance.available_qty,
                    threshold_qty=material.safety_stock or Decimal("20"),
                    status=status,
                    handled_time=datetime.now() if status == "closed" else None,
                    remark=reason or ["低于安全库存", "超期未动销", "质检冻结待处理", "外部系统同步失败"][index % 4],
                    **self._demo_fields(demo_batch_id),
                ),
            )

    def _flow(
        self,
        numbering: WmsDemoNumbering,
        material: WmsMaterialModel,
        warehouse: WmsWarehouseModel,
        location: WmsLocationModel,
        balance: WmsStockBalanceModel,
        batch_no: str,
        quantity: Decimal,
        flow_type: str,
        direction: str,
        document_type: str,
        document_no: str,
        demo_batch_id: str,
        lock_id: int | None = None,
    ) -> None:
        self._add(
            "stock_flow",
            WmsStockFlowModel(
                flow_no=numbering.document_no("stock_flow"),
                flow_type=flow_type,
                direction=direction,
                material_id=material.id,
                warehouse_id=warehouse.id,
                location_id=location.id,
                balance_id=balance.id,
                lock_id=lock_id,
                batch_no=batch_no,
                stock_status_after=balance.stock_status,
                quantity=quantity,
                document_type=document_type,
                document_no=document_no,
                remark="动态试用库存流水",
                **self._demo_fields(demo_batch_id),
            ),
        )

    @staticmethod
    def _material_unit(name: str, category: str) -> str:
        if "电缆" in name or "线缆" in category:
            return "米"
        if "柜" in name or "变压器" in name or "组合电器" in name:
            return "台"
        if "铜排" in name:
            return "根"
        return "件"

    def _source(self, index: int) -> str:
        return self.SOURCE_CYCLE[index % len(self.SOURCE_CYCLE)]

    def _sync_status(self, index: int) -> str:
        return self.SYNC_CYCLE[index % len(self.SYNC_CYCLE)]

    @staticmethod
    def _status_time(status: str, stage: str) -> datetime | None:
        order = {
            "pending_reserve": 0,
            "reserved": 1,
            "picked": 2,
            "reviewed": 3,
            "confirmed": 4,
        }
        stage_order = {"picked": 2, "reviewed": 3, "confirmed": 4}
        if order.get(status, 0) < stage_order[stage]:
            return None
        return datetime.now()

    @staticmethod
    def _code(
        plan: DemoPlan | None,
        numbering: WmsDemoNumbering,
        object_type: str,
        *,
        category_short: str | None = None,
        parent_code: str | None = None,
    ) -> str:
        value = numbering.code(object_type, category_short=category_short, parent_code=parent_code)
        if plan and plan.legacy_mode and object_type in {"warehouse", "zone", "location", "material", "supplier", "customer", "barcode_rule"}:
            return value.replace("-", "_")
        return value

    async def _persisted_counts(self, demo_batch_id: str) -> dict[str, int]:
        counts = {}
        for label, model in self.count_models():
            counts[label] = await self.demo_count(model, demo_batch_id)
        return counts

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

    @staticmethod
    def _enriched_name(names: list[str], index: int) -> str | None:
        if not names:
            return None
        return names[index % len(names)]

    @staticmethod
    def _enriched_material(plan: DemoPlan, product: dict, index: int):
        if not plan.enrichment or not plan.enrichment.materials:
            return None
        key = str(product.get("name") or product.get("category") or "")
        for item in plan.enrichment.materials:
            if item.key == key:
                return item
        return plan.enrichment.materials[index % len(plan.enrichment.materials)]

    def _tenant_id(self) -> int:
        return self.auth.tenant_id or 1

    def _user_id(self) -> int | None:
        user = self.auth.get_user()
        return getattr(user, "id", None)

    async def demo_count(self, model: type, demo_batch_id: str) -> int:
        stmt = select(func.count()).select_from(model).where(
            model.tenant_id == self._tenant_id(),
            model.is_demo.is_(True),
            model.demo_batch_id == demo_batch_id,
        )
        return (await self.db.execute(stmt)).scalar_one() or 0

    @staticmethod
    def _summary(plan: DemoPlan, counts: dict[str, int]) -> list[str]:
        return [
            f"已生成 {counts.get('warehouse', 0)} 个仓库、{counts.get('location', 0)} 个库位",
            f"已生成 {counts.get('material', 0)} 个物料，覆盖 {len(plan.product_mix)} 个产品样本",
            f"已生成 {counts.get('stock_flow', 0)} 条库存流水，覆盖 {', '.join(plan.workflow_coverage)}",
        ]

    @staticmethod
    def count_models() -> list[tuple[str, type]]:
        return [
            ("warehouse", WmsWarehouseModel),
            ("zone", WmsZoneModel),
            ("location", WmsLocationModel),
            ("material", WmsMaterialModel),
            ("supplier", WmsSupplierModel),
            ("customer", WmsCustomerModel),
            ("barcode_rule", WmsBarcodeRuleModel),
            ("arrival_order", WmsArrivalOrderModel),
            ("arrival_line", WmsArrivalLineModel),
            ("inspection_task", WmsInspectionTaskModel),
            ("inspection_line", WmsInspectionLineModel),
            ("inbound_order", WmsInboundOrderModel),
            ("inbound_line", WmsInboundLineModel),
            ("outbound_order", WmsOutboundOrderModel),
            ("outbound_line", WmsOutboundLineModel),
            ("issue_order", WmsIssueOrderModel),
            ("issue_line", WmsIssueLineModel),
            ("transfer_order", WmsTransferOrderModel),
            ("transfer_line", WmsTransferLineModel),
            ("stock_check_order", WmsStockCheckOrderModel),
            ("stock_check_line", WmsStockCheckLineModel),
            ("stock_batch", WmsStockBatchModel),
            ("stock_balance", WmsStockBalanceModel),
            ("stock_flow", WmsStockFlowModel),
            ("stock_lock", WmsStockLockModel),
            ("trace_link", WmsTraceLinkModel),
            ("warning", WmsStockWarningModel),
        ]
