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
from ..stock.model import WmsStockBalanceModel, WmsStockBatchModel, WmsStockFlowModel, WmsStockLockModel, WmsTraceLinkModel
from ..transfer.model import WmsTransferLineModel, WmsTransferOrderModel
from ..warning.model import WmsStockWarningModel
from .numbering import WmsDemoNumbering
from .planner import DemoPlan


class WmsDemoWriter:
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
            await self._transfer_and_check(numbering, warehouses, locations, materials, balances, demo_batch_id)
        await self._warnings(plan, numbering, warehouses, materials, balances, demo_batch_id)
        await self.db.flush()
        counts = await self._persisted_counts(demo_batch_id)
        return counts, self._summary(plan, counts)

    async def _warehouses(self, plan: DemoPlan, numbering: WmsDemoNumbering, demo_batch_id: str) -> list[WmsWarehouseModel]:
        result = []
        for index in range(plan.counts["warehouse"]):
            obj = WmsWarehouseModel(
                code=self._code(plan, numbering, "warehouse"),
                name=f"{plan.request.profile.company_name}{'总仓' if index == 0 else f'分仓{index}'}",
                type="finished_and_raw" if index == 0 else "regional",
                manager="试用管理员",
                status=0,
                description="WMS试用数据",
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
            obj = WmsZoneModel(
                code=self._code(plan, numbering, "zone", parent_code=warehouse.code),
                name=f"{warehouse.name}-{'原料' if index % 2 == 0 else '成品'}区",
                warehouse_id=warehouse.id,
                usage="raw_and_finished",
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
                capacity=Decimal("1000"),
                category_constraints=["电工装备", "关键物资"],
                mix_rule="same_material",
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
            name = (product.get("supplier_patterns") or [f"{product['name']}供应商"])[0]
            obj = WmsSupplierModel(
                code=self._code(plan, numbering, "supplier"),
                name=f"{name}{index + 1}",
                contact="供应链经理",
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
            obj = WmsCustomerModel(
                code=self._code(plan, numbering, "customer"),
                name=f"{plan.request.profile.industry}项目客户{index + 1}",
                contact="项目经理",
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
            obj = WmsMaterialModel(
                code=self._code(plan, numbering, "material", category_short=category[:2].upper()),
                name=f"{material_patterns[index % len(material_patterns)]}{index + 1}",
                spec=f"{spec_patterns[index % len(spec_patterns)]}-{index + 1:03d}",
                unit="台" if "柜" in product["name"] or "变压器" in product["name"] else "件",
                category=category,
                batch_flag=True,
                sn_flag=False,
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
        cycle_count = 1 if plan.legacy_mode else max(1, ceil(plan.counts["stock_flow"] / 4))
        for index in range(cycle_count):
            material = materials[index % len(materials)]
            warehouse = warehouses[index % len(warehouses)]
            location = locations[index % len(locations)]
            supplier = suppliers[index % len(suppliers)]
            batch_no = numbering.batch_no(material.code)
            qty = Decimal(80 + (index % 9) * 10)
            accepted = qty - Decimal(index % 4)
            rejected = qty - accepted
            order_time = datetime.now() - timedelta(days=index % plan.request.time_range_days)

            arrival = self._add(
                "arrival_order",
                WmsArrivalOrderModel(
                    order_no=numbering.document_no("arrival"),
                    supplier_id=supplier.id,
                    warehouse_id=warehouse.id,
                    status="closed",
                    expected_time=order_time,
                    received_time=order_time,
                    external_source="manual",
                    remark="动态试用数据到货单",
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
                    remark="动态试用数据质检任务",
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
                    external_source="manual",
                    remark="动态试用数据入库单",
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
                    stock_status="available",
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
                    stock_status="available",
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
                    stock_status="mixed" if rejected else "available",
                    quantity=qty,
                    available_qty=accepted,
                    pending_qty=Decimal("0"),
                    defective_qty=rejected,
                    locked_qty=Decimal("0"),
                    frozen_qty=Decimal("0"),
                    **self._demo_fields(demo_batch_id),
                ),
            )
            await self.db.flush()
            self._flow(numbering, material, warehouse, location, balance, batch_no, qty, "receive_pending", "in", "arrival", arrival.order_no, demo_batch_id)
            self._flow(numbering, material, warehouse, location, balance, batch_no, accepted, "approve_to_available", "adjust", "inbound", inbound.order_no, demo_batch_id)
            if rejected:
                self._flow(numbering, material, warehouse, location, balance, batch_no, rejected, "reject_to_defective", "adjust", "inspection", inspection.task_no, demo_batch_id)
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
        doc_count = 1 if plan.legacy_mode else max(2, min(plan.counts["business_doc"] // 8, len(balances)))
        for index in range(doc_count):
            balance = balances[index % len(balances)]
            material = materials[index % len(materials)]
            warehouse = warehouses[index % len(warehouses)]
            location = locations[index % len(locations)]
            customer = customers[index % len(customers)]
            qty = Decimal(5 + index % 10)
            lock = self._add(
                "stock_lock",
                WmsStockLockModel(
                    lock_no=numbering.document_no("stock_lock"),
                    material_id=material.id,
                    warehouse_id=warehouse.id,
                    location_id=location.id,
                    batch_no=balance.batch_no,
                    quantity=qty,
                    released_qty=Decimal("0"),
                    shipped_qty=Decimal("0"),
                    status="active",
                    document_type="outbound",
                    document_no="demo",
                    **self._demo_fields(demo_batch_id),
                ),
            )
            await self.db.flush()
            outbound = self._add(
                "outbound_order",
                WmsOutboundOrderModel(
                    order_no=numbering.document_no("outbound"),
                    customer_id=customer.id,
                    warehouse_id=warehouse.id,
                    status="pending_reserve",
                    external_source="manual",
                    remark="动态试用数据销售出库单",
                    **self._demo_fields(demo_batch_id),
                ),
            )
            issue = self._add(
                "issue_order",
                WmsIssueOrderModel(
                    order_no=numbering.document_no("issue"),
                    work_order_no=numbering.document_no("work_order"),
                    warehouse_id=warehouse.id,
                    status="pending_reserve",
                    external_source="manual",
                    remark="动态试用数据生产领料单",
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
                    batch_no=balance.batch_no,
                    requested_qty=qty,
                    locked_qty=qty,
                    stock_lock_id=lock.id,
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
                    batch_no=balance.batch_no,
                    requested_qty=qty,
                    locked_qty=qty,
                    stock_lock_id=lock.id,
                    status="pending_reserve",
                    **self._demo_fields(demo_batch_id),
                ),
            )
            self._flow(numbering, material, warehouse, location, balance, balance.batch_no, qty, "reserve", "out", "outbound", outbound.order_no, demo_batch_id, lock_id=lock.id)

    async def _transfer_and_check(
        self,
        numbering: WmsDemoNumbering,
        warehouses: list[WmsWarehouseModel],
        locations: list[WmsLocationModel],
        materials: list[WmsMaterialModel],
        balances: list[WmsStockBalanceModel],
        demo_batch_id: str,
    ) -> None:
        from_wh = warehouses[0]
        to_wh = warehouses[1] if len(warehouses) > 1 else warehouses[0]
        from_loc = locations[0]
        to_loc = locations[1] if len(locations) > 1 else locations[0]
        material = materials[0]
        balance = balances[0]
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
        check = self._add(
            "stock_check_order",
            WmsStockCheckOrderModel(
                order_no=numbering.document_no("stock_check"),
                warehouse_id=from_wh.id,
                status="audited",
                audited_time=datetime.now(),
                remark="动态试用数据盘点单",
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
            self._add(
                "warning",
                WmsStockWarningModel(
                    warning_no=numbering.document_no("warning"),
                    warning_type="safety_stock" if index % 2 == 0 else "slow_moving",
                    material_id=material.id,
                    warehouse_id=warehouse.id,
                    batch_no=balance.batch_no,
                    current_qty=balance.available_qty,
                    threshold_qty=material.safety_stock or Decimal("20"),
                    status="open",
                    remark="动态试用数据库存预警",
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
