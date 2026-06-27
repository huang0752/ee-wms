from datetime import datetime

from sqlalchemy import func, select

from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException

from ..stock.ledger_service import WmsStockLedgerService
from ..stock.schema import WmsStockLockSchema
from ..tenant_guard import ensure_wms_customer, ensure_wms_material, ensure_wms_warehouse, require_wms_tenant_id
from .model import WmsOutboundLineModel, WmsOutboundOrderModel
from .schema import WmsOutboundCreateSchema, WmsOutboundOrderOutSchema


class WmsOutboundService:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        if auth.db is None:
            raise CustomException(msg="数据库会话不存在")
        self.db = auth.db

    async def create(self, data: WmsOutboundCreateSchema) -> WmsOutboundOrderOutSchema:
        tenant_id = self._tenant_id()
        await ensure_wms_customer(self.db, tenant_id, data.customer_id)
        await ensure_wms_warehouse(self.db, tenant_id, data.warehouse_id)
        for line_data in data.lines:
            await ensure_wms_material(self.db, tenant_id, line_data.material_id)
        order_no = data.order_no or await self._next_no("OUT")
        await self._ensure_order_no_unique(order_no)
        order = WmsOutboundOrderModel(
            tenant_id=self._tenant_id(),
            order_no=order_no,
            customer_id=data.customer_id,
            warehouse_id=data.warehouse_id,
            external_source=data.external_source,
            external_id=data.external_id,
            external_no=data.external_no,
            sync_status=data.sync_status,
            workflow_instance_id=data.workflow_instance_id,
            remark=data.remark,
            created_id=self._user_id(),
            updated_id=self._user_id(),
        )
        self.db.add(order)
        await self.db.flush()
        for line_data in data.lines:
            self.db.add(
                WmsOutboundLineModel(
                    tenant_id=self._tenant_id(),
                    order_id=order.id,
                    material_id=line_data.material_id,
                    warehouse_id=data.warehouse_id,
                    requested_qty=line_data.requested_qty,
                    remark=line_data.remark,
                    created_id=self._user_id(),
                    updated_id=self._user_id(),
                )
            )
        await self.db.flush()
        return WmsOutboundOrderOutSchema.model_validate(order)

    async def reserve(self, order_id: int) -> WmsOutboundOrderOutSchema:
        order = await self._get_order(order_id)
        if order.status != "pending_reserve":
            raise CustomException(msg="出库单不是待预留状态", status_code=400)
        lines = await self._get_lines(order.id)
        if not lines:
            raise CustomException(msg="出库单缺少明细", status_code=400)
        ledger = WmsStockLedgerService(self.auth)
        for line in lines:
            locks = await ledger.lock_stock(
                WmsStockLockSchema(
                    material_id=line.material_id,
                    warehouse_id=order.warehouse_id,
                    quantity=line.requested_qty,
                    document_type="outbound",
                    document_no=order.order_no,
                )
            )
            if not locks:
                raise CustomException(msg="未生成锁库记录", status_code=400)
            first = locks[0]
            line.stock_lock_id = first.id
            line.location_id = first.location_id
            line.batch_no = first.batch_no
            line.locked_qty = first.quantity
            line.status = "reserved"
            self._touch(line)
            for extra in locks[1:]:
                self.db.add(
                    WmsOutboundLineModel(
                        tenant_id=self._tenant_id(),
                        order_id=order.id,
                        material_id=line.material_id,
                        warehouse_id=order.warehouse_id,
                        location_id=extra.location_id,
                        batch_no=extra.batch_no,
                        requested_qty=0,
                        locked_qty=extra.quantity,
                        stock_lock_id=extra.id,
                        status="reserved",
                        created_id=self._user_id(),
                        updated_id=self._user_id(),
                    )
                )
        order.status = "reserved"
        self._touch(order)
        await self.db.flush()
        return WmsOutboundOrderOutSchema.model_validate(order)

    async def pick(self, order_id: int) -> WmsOutboundOrderOutSchema:
        order = await self._get_order(order_id)
        if order.status != "reserved":
            raise CustomException(msg="出库单不是已预留状态", status_code=400)
        order.status = "picked"
        order.picked_time = datetime.now()
        self._touch(order)
        for line in await self._get_lines(order.id):
            if line.status == "reserved":
                line.status = "picked"
                self._touch(line)
        await self.db.flush()
        return WmsOutboundOrderOutSchema.model_validate(order)

    async def review(self, order_id: int) -> WmsOutboundOrderOutSchema:
        order = await self._get_order(order_id)
        if order.status != "picked":
            raise CustomException(msg="出库单不是已拣货状态", status_code=400)
        order.status = "reviewed"
        order.reviewed_time = datetime.now()
        self._touch(order)
        for line in await self._get_lines(order.id):
            if line.status == "picked":
                line.status = "reviewed"
                self._touch(line)
        await self.db.flush()
        return WmsOutboundOrderOutSchema.model_validate(order)

    async def confirm(self, order_id: int) -> WmsOutboundOrderOutSchema:
        order = await self._get_order(order_id)
        if order.status != "reviewed":
            raise CustomException(msg="出库单不是已复核状态", status_code=400)
        ledger = WmsStockLedgerService(self.auth)
        for line in await self._get_lines(order.id):
            if not line.stock_lock_id:
                continue
            await ledger.ship_locked(line.stock_lock_id)
            line.shipped_qty = line.locked_qty
            line.status = "confirmed"
            self._touch(line)
        order.status = "confirmed"
        order.confirmed_time = datetime.now()
        self._touch(order)
        await self.db.flush()
        return WmsOutboundOrderOutSchema.model_validate(order)

    async def cancel(self, order_id: int) -> WmsOutboundOrderOutSchema:
        order = await self._get_order(order_id)
        if order.status in {"confirmed", "cancelled"}:
            raise CustomException(msg="出库单已结束，不能取消", status_code=400)
        ledger = WmsStockLedgerService(self.auth)
        for line in await self._get_lines(order.id):
            if line.stock_lock_id and line.status in {"reserved", "picked", "reviewed"}:
                await ledger.release_lock(line.stock_lock_id)
            line.status = "cancelled"
            self._touch(line)
        order.status = "cancelled"
        self._touch(order)
        await self.db.flush()
        return WmsOutboundOrderOutSchema.model_validate(order)

    async def _get_order(self, order_id: int) -> WmsOutboundOrderModel:
        order = (
            await self.db.execute(
                select(WmsOutboundOrderModel)
                .where(
                    WmsOutboundOrderModel.id == order_id,
                    WmsOutboundOrderModel.tenant_id == self._tenant_id(),
                    WmsOutboundOrderModel.is_deleted.is_(False),
                )
                .limit(1)
            )
        ).scalars().first()
        if not order:
            raise CustomException(msg="出库单不存在", status_code=404)
        return order

    async def _get_lines(self, order_id: int) -> list[WmsOutboundLineModel]:
        return list(
            (
                await self.db.execute(
                    select(WmsOutboundLineModel)
                    .where(
                        WmsOutboundLineModel.order_id == order_id,
                        WmsOutboundLineModel.tenant_id == self._tenant_id(),
                        WmsOutboundLineModel.is_deleted.is_(False),
                    )
                    .order_by(WmsOutboundLineModel.id.asc())
                )
            ).scalars().all()
        )

    async def _ensure_order_no_unique(self, order_no: str) -> None:
        exists = (
            await self.db.execute(
                select(WmsOutboundOrderModel)
                .where(
                    WmsOutboundOrderModel.tenant_id == self._tenant_id(),
                    WmsOutboundOrderModel.order_no == order_no,
                    WmsOutboundOrderModel.is_deleted.is_(False),
                )
                .limit(1)
            )
        ).scalars().first()
        if exists:
            raise CustomException(msg="出库单号已存在", status_code=400)

    async def _next_no(self, prefix: str) -> str:
        count = (await self.db.execute(select(func.count()).select_from(WmsOutboundOrderModel))).scalar_one() or 0
        return f"{prefix}{count + 1:08d}"

    def _tenant_id(self) -> int:
        return require_wms_tenant_id(self.auth)

    def _user_id(self) -> int | None:
        user = self.auth.get_user()
        return getattr(user, "id", None)

    def _touch(self, obj) -> None:
        obj.updated_id = self._user_id()
