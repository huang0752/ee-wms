from datetime import datetime

from sqlalchemy import func, select

from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException

from ..arrival.model import WmsArrivalLineModel, WmsArrivalOrderModel
from ..inspection.model import WmsInspectionLineModel, WmsInspectionTaskModel
from ..master.model import WmsLocationModel, WmsMaterialModel
from ..stock.ledger_service import WmsStockLedgerService
from ..stock.schema import WmsStockMutationSchema
from .model import WmsInboundLineModel, WmsInboundOrderModel
from .schema import WmsInboundCreateFromInspectionSchema, WmsInboundOrderOutSchema, WmsLocationRecommendOutSchema


class WmsInboundService:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        if auth.db is None:
            raise CustomException(msg="数据库会话不存在")
        self.db = auth.db

    async def create_from_inspection(self, task_id: int, data: WmsInboundCreateFromInspectionSchema) -> WmsInboundOrderOutSchema:
        task = await self._get_task(task_id)
        if task.status != "pending_inbound":
            raise CustomException(msg="检验任务不是待入库状态", status_code=400)
        arrival = await self._get_arrival(task.arrival_order_id)
        lines = await self._get_inspection_lines(task.id)
        inbound_lines = []
        for line in lines:
            if line.accepted_qty > 0:
                inbound_lines.append((line, line.accepted_qty, "available"))
            if line.rejected_qty > 0:
                inbound_lines.append((line, line.rejected_qty, "defective"))
        if not inbound_lines:
            raise CustomException(msg="没有可入库的检验数量", status_code=400)

        order = WmsInboundOrderModel(
            tenant_id=self._tenant_id(),
            order_no=await self._next_no("INB"),
            inspection_task_id=task.id,
            arrival_order_id=arrival.id,
            warehouse_id=arrival.warehouse_id,
            location_id=data.location_id,
            status="pending_confirm",
            external_source=arrival.external_source,
            external_id=arrival.external_id,
            external_no=arrival.external_no,
            sync_status=arrival.sync_status,
            workflow_instance_id=arrival.workflow_instance_id,
            remark=data.remark,
            is_demo=arrival.is_demo,
            demo_batch_id=arrival.demo_batch_id,
            created_id=self._user_id(),
            updated_id=self._user_id(),
        )
        self.db.add(order)
        await self.db.flush()
        for source_line, quantity, stock_status in inbound_lines:
            self.db.add(
                WmsInboundLineModel(
                    tenant_id=self._tenant_id(),
                    order_id=order.id,
                    inspection_line_id=source_line.id,
                    material_id=source_line.material_id,
                    warehouse_id=arrival.warehouse_id,
                    location_id=data.location_id,
                    batch_no=source_line.batch_no,
                    quantity=quantity,
                    stock_status=stock_status,
                    created_id=self._user_id(),
                    updated_id=self._user_id(),
                )
            )
        await self.db.flush()
        return WmsInboundOrderOutSchema.model_validate(order)

    async def confirm(self, order_id: int) -> WmsInboundOrderOutSchema:
        order = await self._get_order(order_id)
        if order.status != "pending_confirm":
            raise CustomException(msg="入库单不是待确认状态", status_code=400)
        lines = await self._get_inbound_lines(order.id)
        if not lines:
            raise CustomException(msg="入库单缺少明细", status_code=400)
        ledger = WmsStockLedgerService(self.auth)
        for line in lines:
            mutation = WmsStockMutationSchema(
                material_id=line.material_id,
                warehouse_id=line.warehouse_id,
                location_id=line.location_id,
                batch_no=line.batch_no,
                quantity=line.quantity,
                document_type="inbound",
                document_no=order.order_no,
                is_demo=line.is_demo,
                demo_batch_id=line.demo_batch_id,
            )
            await ledger.receive_pending(mutation)
            if line.stock_status == "available":
                await ledger.approve_to_available(mutation)
            elif line.stock_status == "defective":
                await ledger.reject_to_defective(mutation)
            else:
                raise CustomException(msg="不支持的入库库存状态", status_code=400)
            line.status = "confirmed"
            self._touch(line)

        order.status = "confirmed"
        order.confirmed_time = datetime.now()
        self._touch(order)
        await self._close_sources(order)
        await self.db.flush()
        return WmsInboundOrderOutSchema.model_validate(order)

    async def recommend_location(self, material_id: int, warehouse_id: int) -> list[WmsLocationRecommendOutSchema]:
        material = (
            await self.db.execute(
                select(WmsMaterialModel)
                .where(
                    WmsMaterialModel.id == material_id,
                    WmsMaterialModel.tenant_id == self._tenant_id(),
                    WmsMaterialModel.is_deleted.is_(False),
                )
                .limit(1)
            )
        ).scalars().first()
        if not material:
            raise CustomException(msg="物料不存在", status_code=404)
        rows = (
            await self.db.execute(
                select(WmsLocationModel)
                .where(
                    WmsLocationModel.warehouse_id == warehouse_id,
                    WmsLocationModel.tenant_id == self._tenant_id(),
                    WmsLocationModel.status == 0,
                    WmsLocationModel.is_deleted.is_(False),
                )
                .order_by(WmsLocationModel.id.asc())
            )
        ).scalars().all()
        result = []
        for row in rows:
            constraints = row.category_constraints or []
            if constraints and material.category not in constraints:
                continue
            result.append(WmsLocationRecommendOutSchema.model_validate(row, from_attributes=True))
        return result

    async def _close_sources(self, order: WmsInboundOrderModel) -> None:
        if order.inspection_task_id:
            task = await self._get_task(order.inspection_task_id)
            task.status = "closed"
            self._touch(task)
            for line in await self._get_inspection_lines(task.id):
                line.status = "closed"
                self._touch(line)
        if order.arrival_order_id:
            arrival = await self._get_arrival(order.arrival_order_id)
            arrival.status = "closed"
            self._touch(arrival)
            arrival_lines = (
                await self.db.execute(
                    select(WmsArrivalLineModel)
                    .where(
                        WmsArrivalLineModel.order_id == arrival.id,
                        WmsArrivalLineModel.tenant_id == self._tenant_id(),
                        WmsArrivalLineModel.is_deleted.is_(False),
                    )
                )
            ).scalars().all()
            for line in arrival_lines:
                line.status = "closed"
                self._touch(line)

    async def _get_order(self, order_id: int) -> WmsInboundOrderModel:
        order = (
            await self.db.execute(
                select(WmsInboundOrderModel)
                .where(
                    WmsInboundOrderModel.id == order_id,
                    WmsInboundOrderModel.tenant_id == self._tenant_id(),
                    WmsInboundOrderModel.is_deleted.is_(False),
                )
                .limit(1)
            )
        ).scalars().first()
        if not order:
            raise CustomException(msg="入库单不存在", status_code=404)
        return order

    async def _get_task(self, task_id: int) -> WmsInspectionTaskModel:
        task = (
            await self.db.execute(
                select(WmsInspectionTaskModel)
                .where(
                    WmsInspectionTaskModel.id == task_id,
                    WmsInspectionTaskModel.tenant_id == self._tenant_id(),
                    WmsInspectionTaskModel.is_deleted.is_(False),
                )
                .limit(1)
            )
        ).scalars().first()
        if not task:
            raise CustomException(msg="检验任务不存在", status_code=404)
        return task

    async def _get_arrival(self, order_id: int) -> WmsArrivalOrderModel:
        arrival = (
            await self.db.execute(
                select(WmsArrivalOrderModel)
                .where(
                    WmsArrivalOrderModel.id == order_id,
                    WmsArrivalOrderModel.tenant_id == self._tenant_id(),
                    WmsArrivalOrderModel.is_deleted.is_(False),
                )
                .limit(1)
            )
        ).scalars().first()
        if not arrival:
            raise CustomException(msg="到货单不存在", status_code=404)
        return arrival

    async def _get_inspection_lines(self, task_id: int) -> list[WmsInspectionLineModel]:
        return list(
            (
                await self.db.execute(
                    select(WmsInspectionLineModel)
                    .where(
                        WmsInspectionLineModel.task_id == task_id,
                        WmsInspectionLineModel.tenant_id == self._tenant_id(),
                        WmsInspectionLineModel.is_deleted.is_(False),
                    )
                    .order_by(WmsInspectionLineModel.id.asc())
                )
            ).scalars().all()
        )

    async def _get_inbound_lines(self, order_id: int) -> list[WmsInboundLineModel]:
        return list(
            (
                await self.db.execute(
                    select(WmsInboundLineModel)
                    .where(
                        WmsInboundLineModel.order_id == order_id,
                        WmsInboundLineModel.tenant_id == self._tenant_id(),
                        WmsInboundLineModel.is_deleted.is_(False),
                    )
                    .order_by(WmsInboundLineModel.id.asc())
                )
            ).scalars().all()
        )

    async def _next_no(self, prefix: str) -> str:
        count = (await self.db.execute(select(func.count()).select_from(WmsInboundOrderModel))).scalar_one() or 0
        return f"{prefix}{count + 1:08d}"

    def _tenant_id(self) -> int:
        return self.auth.tenant_id or 1

    def _user_id(self) -> int | None:
        user = self.auth.get_user()
        return getattr(user, "id", None)

    def _touch(self, obj) -> None:
        obj.updated_id = self._user_id()
