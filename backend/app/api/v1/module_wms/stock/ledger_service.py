from decimal import Decimal

from sqlalchemy import and_, func, select

from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException

from .model import (
    WmsStockBalanceModel,
    WmsStockBatchModel,
    WmsStockFlowModel,
    WmsStockLockModel,
)
from .schema import (
    WmsStockAdjustSchema,
    WmsStockBalanceOutSchema,
    WmsStockLockOutSchema,
    WmsStockLockSchema,
    WmsStockMutationSchema,
)

ZERO = Decimal("0")


class WmsStockLedgerService:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        if auth.db is None:
            raise CustomException(msg="数据库会话不存在")
        self.db = auth.db

    async def receive_pending(self, data: WmsStockMutationSchema) -> WmsStockBalanceOutSchema:
        qty = self._qty(data.quantity)
        await self._ensure_batch(data, "pending_inspection")
        flow = await self._write_flow(data=data, flow_type="receive_pending", direction="in", after="pending_inspection")
        balance = await self._get_or_create_balance(data)
        flow.balance_id = balance.id
        balance.quantity += qty
        balance.pending_qty += qty
        self._touch(balance)
        await self.db.flush()
        return WmsStockBalanceOutSchema.model_validate(balance)

    async def approve_to_available(self, data: WmsStockMutationSchema) -> WmsStockBalanceOutSchema:
        qty = self._qty(data.quantity)
        balance = await self._get_required_balance(data)
        self._ensure_enough(balance.pending_qty, qty, "待检库存不足")
        flow = await self._write_flow(data=data, flow_type="approve_to_available", direction="adjust", before="pending_inspection", after="available")
        flow.balance_id = balance.id
        balance.pending_qty -= qty
        balance.available_qty += qty
        self._touch(balance)
        await self.db.flush()
        return WmsStockBalanceOutSchema.model_validate(balance)

    async def reject_to_defective(self, data: WmsStockMutationSchema) -> WmsStockBalanceOutSchema:
        qty = self._qty(data.quantity)
        balance = await self._get_required_balance(data)
        self._ensure_enough(balance.pending_qty, qty, "待检库存不足")
        flow = await self._write_flow(data=data, flow_type="reject_to_defective", direction="adjust", before="pending_inspection", after="defective")
        flow.balance_id = balance.id
        balance.pending_qty -= qty
        balance.defective_qty += qty
        self._touch(balance)
        await self.db.flush()
        return WmsStockBalanceOutSchema.model_validate(balance)

    async def lock_stock(self, data: WmsStockLockSchema) -> list[WmsStockLockOutSchema]:
        need_qty = self._qty(data.quantity)
        balances = await self._available_balances(data)
        allocated: list[WmsStockLockModel] = []
        remaining = need_qty

        for balance in balances:
            if remaining <= ZERO:
                break
            take_qty = min(remaining, balance.available_qty)
            if take_qty <= ZERO:
                continue
            mutation = self._mutation_from_balance(balance=balance, data=data, quantity=take_qty)
            lock = WmsStockLockModel(
                lock_no=await self._next_no("LK"),
                tenant_id=self._tenant_id(),
                material_id=balance.material_id,
                warehouse_id=balance.warehouse_id,
                location_id=balance.location_id,
                batch_no=balance.batch_no,
                sn_code=balance.sn_code,
                quantity=take_qty,
                status="active",
                document_type=data.document_type,
                document_no=data.document_no,
                created_id=self._user_id(),
                updated_id=self._user_id(),
            )
            self.db.add(lock)
            await self.db.flush()
            flow = await self._write_flow(data=mutation, flow_type="lock_stock", direction="lock", before="available", after="locked", lock_id=lock.id)
            flow.balance_id = balance.id
            balance.available_qty -= take_qty
            balance.locked_qty += take_qty
            self._touch(balance)
            allocated.append(lock)
            remaining -= take_qty

        if remaining > ZERO:
            raise CustomException(msg="可用库存不足，无法锁定", status_code=400)

        await self.db.flush()
        return [WmsStockLockOutSchema.model_validate(item) for item in allocated]

    async def release_lock(self, lock_id: int) -> WmsStockBalanceOutSchema:
        lock = await self._get_lock(lock_id)
        if lock.status != "active":
            raise CustomException(msg="锁库记录不是可释放状态", status_code=400)
        qty = lock.quantity - lock.released_qty - lock.shipped_qty
        self._ensure_enough(qty, Decimal("0.0001"), "锁定库存已释放或已出库")
        mutation = self._mutation_from_lock(lock, qty)
        balance = await self._get_required_balance(mutation)
        flow = await self._write_flow(data=mutation, flow_type="release_lock", direction="unlock", before="locked", after="available", lock_id=lock.id)
        flow.balance_id = balance.id
        self._ensure_enough(balance.locked_qty, qty, "锁定库存不足")
        balance.locked_qty -= qty
        balance.available_qty += qty
        lock.released_qty += qty
        lock.status = "released"
        self._touch(balance)
        self._touch(lock)
        await self.db.flush()
        return WmsStockBalanceOutSchema.model_validate(balance)

    async def ship_locked(self, lock_id: int) -> WmsStockBalanceOutSchema:
        lock = await self._get_lock(lock_id)
        if lock.status != "active":
            raise CustomException(msg="锁库记录不是可出库状态", status_code=400)
        qty = lock.quantity - lock.released_qty - lock.shipped_qty
        self._ensure_enough(qty, Decimal("0.0001"), "锁定库存已释放或已出库")
        mutation = self._mutation_from_lock(lock, qty)
        balance = await self._get_required_balance(mutation)
        flow = await self._write_flow(data=mutation, flow_type="ship_locked", direction="out", before="locked", after="shipped", lock_id=lock.id)
        flow.balance_id = balance.id
        self._ensure_enough(balance.locked_qty, qty, "锁定库存不足")
        self._ensure_enough(balance.quantity, qty, "实物库存不足")
        balance.locked_qty -= qty
        balance.quantity -= qty
        lock.shipped_qty += qty
        lock.status = "shipped"
        self._touch(balance)
        self._touch(lock)
        await self.db.flush()
        return WmsStockBalanceOutSchema.model_validate(balance)

    async def freeze(self, data: WmsStockMutationSchema) -> WmsStockBalanceOutSchema:
        qty = self._qty(data.quantity)
        balance = await self._get_required_balance(data)
        self._ensure_enough(balance.available_qty, qty, "可用库存不足，无法冻结")
        flow = await self._write_flow(data=data, flow_type="freeze", direction="adjust", before="available", after="frozen")
        flow.balance_id = balance.id
        balance.available_qty -= qty
        balance.frozen_qty += qty
        self._touch(balance)
        await self.db.flush()
        return WmsStockBalanceOutSchema.model_validate(balance)

    async def unfreeze(self, data: WmsStockMutationSchema) -> WmsStockBalanceOutSchema:
        qty = self._qty(data.quantity)
        balance = await self._get_required_balance(data)
        self._ensure_enough(balance.frozen_qty, qty, "冻结库存不足，无法解冻")
        flow = await self._write_flow(data=data, flow_type="unfreeze", direction="adjust", before="frozen", after="available")
        flow.balance_id = balance.id
        balance.frozen_qty -= qty
        balance.available_qty += qty
        self._touch(balance)
        await self.db.flush()
        return WmsStockBalanceOutSchema.model_validate(balance)

    async def transfer_out(self, data: WmsStockMutationSchema) -> WmsStockBalanceOutSchema:
        qty = self._qty(data.quantity)
        balance = await self._get_required_balance(data)
        self._ensure_enough(balance.available_qty, qty, "可用库存不足，无法调出")
        flow = await self._write_flow(data=data, flow_type="transfer_out", direction="out", before="available", after="transferred")
        flow.balance_id = balance.id
        balance.available_qty -= qty
        balance.quantity -= qty
        self._touch(balance)
        await self.db.flush()
        return WmsStockBalanceOutSchema.model_validate(balance)

    async def transfer_in(self, data: WmsStockMutationSchema) -> WmsStockBalanceOutSchema:
        qty = self._qty(data.quantity)
        await self._ensure_batch(data, "available")
        flow = await self._write_flow(data=data, flow_type="transfer_in", direction="in", before="transferred", after="available")
        balance = await self._get_or_create_balance(data)
        flow.balance_id = balance.id
        balance.quantity += qty
        balance.available_qty += qty
        self._touch(balance)
        await self.db.flush()
        return WmsStockBalanceOutSchema.model_validate(balance)

    async def adjust_after_check(self, data: WmsStockAdjustSchema) -> WmsStockBalanceOutSchema:
        qty = self._qty(data.quantity)
        balance = await self._get_or_create_balance(data)
        flow = await self._write_flow(data=data, flow_type="adjust_after_check", direction="adjust", after=data.stock_bucket)
        flow.balance_id = balance.id
        if data.stock_bucket == "available":
            balance.available_qty += qty
        elif data.stock_bucket == "frozen":
            balance.frozen_qty += qty
        elif data.stock_bucket == "defective":
            balance.defective_qty += qty
        elif data.stock_bucket == "pending":
            balance.pending_qty += qty
        else:
            raise CustomException(msg="不支持的库存调整桶", status_code=400)
        balance.quantity += qty
        self._touch(balance)
        await self.db.flush()
        return WmsStockBalanceOutSchema.model_validate(balance)

    async def adjust_after_check_delta(self, data: WmsStockMutationSchema, delta_qty: Decimal) -> WmsStockBalanceOutSchema:
        delta = Decimal(str(delta_qty))
        if delta == ZERO:
            return WmsStockBalanceOutSchema.model_validate(await self._get_or_create_balance(data))
        qty = abs(delta)
        mutation = data.model_copy(update={"quantity": qty})
        balance = await self._get_or_create_balance(mutation)
        flow = await self._write_flow(data=mutation, flow_type="adjust_after_check", direction="adjust", before="available", after="available")
        flow.balance_id = balance.id
        if delta > ZERO:
            balance.quantity += qty
            balance.available_qty += qty
        else:
            self._ensure_enough(balance.available_qty, qty, "可用库存不足，无法盘亏")
            self._ensure_enough(balance.quantity, qty, "实物库存不足，无法盘亏")
            balance.quantity -= qty
            balance.available_qty -= qty
        self._touch(balance)
        await self.db.flush()
        return WmsStockBalanceOutSchema.model_validate(balance)

    async def _ensure_batch(self, data: WmsStockMutationSchema, status: str) -> WmsStockBatchModel:
        stmt = (
            select(WmsStockBatchModel)
            .where(
                WmsStockBatchModel.tenant_id == self._tenant_id(),
                WmsStockBatchModel.material_id == data.material_id,
                WmsStockBatchModel.batch_no == data.batch_no,
                WmsStockBatchModel.sn_code == data.sn_code,
                WmsStockBatchModel.is_deleted.is_(False),
            )
            .limit(1)
        )
        batch = (await self.db.execute(stmt)).scalars().first()
        if batch:
            return batch
        batch = WmsStockBatchModel(
            tenant_id=self._tenant_id(),
            material_id=data.material_id,
            warehouse_id=data.warehouse_id,
            location_id=data.location_id,
            batch_no=data.batch_no,
            sn_code=data.sn_code,
            stock_status=status,
            source_type=data.document_type,
            source_no=data.document_no,
            is_demo=data.is_demo,
            demo_batch_id=data.demo_batch_id,
            created_id=self._user_id(),
            updated_id=self._user_id(),
        )
        self.db.add(batch)
        await self.db.flush()
        return batch

    async def _get_or_create_balance(self, data: WmsStockMutationSchema) -> WmsStockBalanceModel:
        stmt = self._balance_stmt(data.material_id, data.warehouse_id, data.location_id, data.batch_no, data.sn_code).limit(1)
        balance = (await self.db.execute(stmt)).scalars().first()
        if balance:
            return balance
        balance = WmsStockBalanceModel(
            tenant_id=self._tenant_id(),
            material_id=data.material_id,
            warehouse_id=data.warehouse_id,
            location_id=data.location_id,
            batch_no=data.batch_no,
            sn_code=data.sn_code,
            quantity=ZERO,
            available_qty=ZERO,
            locked_qty=ZERO,
            frozen_qty=ZERO,
            pending_qty=ZERO,
            defective_qty=ZERO,
            is_demo=data.is_demo,
            demo_batch_id=data.demo_batch_id,
            created_id=self._user_id(),
            updated_id=self._user_id(),
        )
        self.db.add(balance)
        await self.db.flush()
        return balance

    async def _get_required_balance(self, data: WmsStockMutationSchema) -> WmsStockBalanceModel:
        balance = (await self.db.execute(self._balance_stmt(data.material_id, data.warehouse_id, data.location_id, data.batch_no, data.sn_code).limit(1))).scalars().first()
        if not balance:
            raise CustomException(msg="库存余额不存在", status_code=400)
        return balance

    def _balance_stmt(self, material_id: int, warehouse_id: int, location_id: int | None, batch_no: str, sn_code: str | None):
        return select(WmsStockBalanceModel).where(
            WmsStockBalanceModel.tenant_id == self._tenant_id(),
            WmsStockBalanceModel.material_id == material_id,
            WmsStockBalanceModel.warehouse_id == warehouse_id,
            WmsStockBalanceModel.location_id.is_(None) if location_id is None else WmsStockBalanceModel.location_id == location_id,
            WmsStockBalanceModel.batch_no == batch_no,
            WmsStockBalanceModel.sn_code.is_(None) if sn_code is None else WmsStockBalanceModel.sn_code == sn_code,
            WmsStockBalanceModel.is_deleted.is_(False),
        )

    async def _available_balances(self, data: WmsStockLockSchema) -> list[WmsStockBalanceModel]:
        conditions = [
            WmsStockBalanceModel.tenant_id == self._tenant_id(),
            WmsStockBalanceModel.material_id == data.material_id,
            WmsStockBalanceModel.available_qty > ZERO,
            WmsStockBalanceModel.is_deleted.is_(False),
        ]
        if data.warehouse_id:
            conditions.append(WmsStockBalanceModel.warehouse_id == data.warehouse_id)
        if data.location_id:
            conditions.append(WmsStockBalanceModel.location_id == data.location_id)
        stmt = select(WmsStockBalanceModel).where(and_(*conditions)).order_by(WmsStockBalanceModel.created_time.asc(), WmsStockBalanceModel.id.asc())
        return list((await self.db.execute(stmt)).scalars().all())

    async def _get_lock(self, lock_id: int) -> WmsStockLockModel:
        stmt = (
            select(WmsStockLockModel)
            .where(
                WmsStockLockModel.id == lock_id,
                WmsStockLockModel.tenant_id == self._tenant_id(),
                WmsStockLockModel.is_deleted.is_(False),
            )
            .limit(1)
        )
        lock = (await self.db.execute(stmt)).scalars().first()
        if not lock:
            raise CustomException(msg="锁库记录不存在", status_code=404)
        return lock

    async def _write_flow(
        self,
        data: WmsStockMutationSchema,
        flow_type: str,
        direction: str,
        before: str | None = None,
        after: str | None = None,
        lock_id: int | None = None,
    ) -> WmsStockFlowModel:
        flow = WmsStockFlowModel(
            flow_no=await self._next_no("FL"),
            flow_type=flow_type,
            direction=direction,
            tenant_id=self._tenant_id(),
            material_id=data.material_id,
            warehouse_id=data.warehouse_id,
            location_id=data.location_id,
            lock_id=lock_id,
            batch_no=data.batch_no,
            sn_code=data.sn_code,
            stock_status_before=before,
            stock_status_after=after,
            quantity=self._qty(data.quantity),
            document_type=data.document_type,
            document_no=data.document_no,
            remark=data.remark,
            is_demo=data.is_demo,
            demo_batch_id=data.demo_batch_id,
            created_id=self._user_id(),
            updated_id=self._user_id(),
        )
        self.db.add(flow)
        await self.db.flush()
        return flow

    async def _next_no(self, prefix: str) -> str:
        count_stmt = select(func.count()).select_from(WmsStockFlowModel if prefix == "FL" else WmsStockLockModel)
        count = (await self.db.execute(count_stmt)).scalar_one() or 0
        return f"{prefix}{count + 1:08d}"

    def _mutation_from_balance(self, balance: WmsStockBalanceModel, data: WmsStockLockSchema, quantity: Decimal) -> WmsStockMutationSchema:
        return WmsStockMutationSchema(
            material_id=balance.material_id,
            warehouse_id=balance.warehouse_id,
            location_id=balance.location_id,
            batch_no=balance.batch_no,
            sn_code=balance.sn_code,
            quantity=quantity,
            document_type=data.document_type,
            document_no=data.document_no,
            remark=data.remark,
            is_demo=balance.is_demo,
            demo_batch_id=balance.demo_batch_id,
        )

    def _mutation_from_lock(self, lock: WmsStockLockModel, quantity: Decimal) -> WmsStockMutationSchema:
        return WmsStockMutationSchema(
            material_id=lock.material_id,
            warehouse_id=lock.warehouse_id,
            location_id=lock.location_id,
            batch_no=lock.batch_no,
            sn_code=lock.sn_code,
            quantity=quantity,
            document_type=lock.document_type,
            document_no=lock.document_no,
            is_demo=lock.is_demo,
            demo_batch_id=lock.demo_batch_id,
        )

    def _qty(self, quantity: Decimal) -> Decimal:
        qty = Decimal(str(quantity))
        if qty <= ZERO:
            raise CustomException(msg="数量必须大于0", status_code=400)
        return qty

    def _ensure_enough(self, actual: Decimal, required: Decimal, msg: str) -> None:
        if Decimal(str(actual)) < Decimal(str(required)):
            raise CustomException(msg=msg, status_code=400)

    def _tenant_id(self) -> int:
        return self.auth.tenant_id or 1

    def _user_id(self) -> int | None:
        user = self.auth.get_user()
        return getattr(user, "id", None)

    def _touch(self, obj) -> None:
        obj.updated_id = self._user_id()
