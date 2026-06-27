from datetime import datetime

from sqlalchemy import func, select

from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException

from ..stock.ledger_service import WmsStockLedgerService
from ..stock.schema import WmsStockMutationSchema
from ..tenant_guard import ensure_wms_location, ensure_wms_material, ensure_wms_warehouse, require_wms_tenant_id
from .model import WmsTransferLineModel, WmsTransferOrderModel
from .schema import WmsTransferCreateSchema, WmsTransferOrderOutSchema


class WmsTransferService:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        if auth.db is None:
            raise CustomException(msg="数据库会话不存在")
        self.db = auth.db

    async def create(self, data: WmsTransferCreateSchema) -> WmsTransferOrderOutSchema:
        tenant_id = self._tenant_id()
        await ensure_wms_warehouse(self.db, tenant_id, data.from_warehouse_id)
        await ensure_wms_warehouse(self.db, tenant_id, data.to_warehouse_id)
        for line in data.lines:
            await ensure_wms_material(self.db, tenant_id, line.material_id)
            await ensure_wms_location(self.db, tenant_id, line.from_location_id, warehouse_id=data.from_warehouse_id)
            await ensure_wms_location(self.db, tenant_id, line.to_location_id, warehouse_id=data.to_warehouse_id)
        order = WmsTransferOrderModel(
            tenant_id=self._tenant_id(),
            order_no=data.order_no or await self._next_no("TRF"),
            from_warehouse_id=data.from_warehouse_id,
            to_warehouse_id=data.to_warehouse_id,
            remark=data.remark,
            created_id=self._user_id(),
            updated_id=self._user_id(),
        )
        self.db.add(order)
        await self.db.flush()
        for line in data.lines:
            self.db.add(WmsTransferLineModel(
                tenant_id=self._tenant_id(), order_id=order.id, material_id=line.material_id,
                from_warehouse_id=data.from_warehouse_id, from_location_id=line.from_location_id,
                to_warehouse_id=data.to_warehouse_id, to_location_id=line.to_location_id,
                batch_no=line.batch_no, quantity=line.quantity, remark=line.remark,
                created_id=self._user_id(), updated_id=self._user_id(),
            ))
        await self.db.flush()
        return WmsTransferOrderOutSchema.model_validate(order)

    async def confirm(self, order_id: int) -> WmsTransferOrderOutSchema:
        order = await self._get_order(order_id)
        if order.status != "draft":
            raise CustomException(msg="调拨单不是草稿状态", status_code=400)
        ledger = WmsStockLedgerService(self.auth)
        for line in await self._get_lines(order.id):
            await ledger.transfer_out(WmsStockMutationSchema(
                material_id=line.material_id, warehouse_id=line.from_warehouse_id,
                location_id=line.from_location_id, batch_no=line.batch_no, quantity=line.quantity,
                document_type="transfer", document_no=order.order_no,
            ))
            await ledger.transfer_in(WmsStockMutationSchema(
                material_id=line.material_id, warehouse_id=line.to_warehouse_id,
                location_id=line.to_location_id, batch_no=line.batch_no, quantity=line.quantity,
                document_type="transfer", document_no=order.order_no,
            ))
            line.status = "confirmed"
            self._touch(line)
        order.status = "confirmed"
        order.confirmed_time = datetime.now()
        self._touch(order)
        await self.db.flush()
        return WmsTransferOrderOutSchema.model_validate(order)

    async def _get_order(self, order_id: int) -> WmsTransferOrderModel:
        row = (await self.db.execute(select(WmsTransferOrderModel).where(WmsTransferOrderModel.id == order_id, WmsTransferOrderModel.tenant_id == self._tenant_id(), WmsTransferOrderModel.is_deleted.is_(False)).limit(1))).scalars().first()
        if not row:
            raise CustomException(msg="调拨单不存在", status_code=404)
        return row

    async def _get_lines(self, order_id: int) -> list[WmsTransferLineModel]:
        return list((await self.db.execute(select(WmsTransferLineModel).where(WmsTransferLineModel.order_id == order_id, WmsTransferLineModel.tenant_id == self._tenant_id(), WmsTransferLineModel.is_deleted.is_(False)).order_by(WmsTransferLineModel.id.asc()))).scalars().all())

    async def _next_no(self, prefix: str) -> str:
        count = (await self.db.execute(select(func.count()).select_from(WmsTransferOrderModel))).scalar_one() or 0
        return f"{prefix}{count + 1:08d}"

    def _tenant_id(self) -> int:
        return require_wms_tenant_id(self.auth)

    def _user_id(self) -> int | None:
        return getattr(self.auth.get_user(), "id", None)

    def _touch(self, obj) -> None:
        obj.updated_id = self._user_id()
