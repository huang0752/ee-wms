from datetime import datetime

from sqlalchemy import func, select

from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException

from ..stock.ledger_service import WmsStockLedgerService
from ..stock.schema import WmsStockMutationSchema
from .model import WmsStockCheckLineModel, WmsStockCheckOrderModel
from .schema import WmsStockCheckCreateSchema, WmsStockCheckOrderOutSchema


class WmsStockCheckService:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        if auth.db is None:
            raise CustomException(msg="数据库会话不存在")
        self.db = auth.db

    async def create(self, data: WmsStockCheckCreateSchema) -> WmsStockCheckOrderOutSchema:
        order = WmsStockCheckOrderModel(
            tenant_id=self._tenant_id(), order_no=data.order_no or await self._next_no("CHK"),
            warehouse_id=data.warehouse_id, remark=data.remark, created_id=self._user_id(), updated_id=self._user_id(),
        )
        self.db.add(order)
        await self.db.flush()
        for line in data.lines:
            self.db.add(WmsStockCheckLineModel(
                tenant_id=self._tenant_id(), order_id=order.id, material_id=line.material_id,
                warehouse_id=data.warehouse_id, location_id=line.location_id, batch_no=line.batch_no,
                system_qty=line.system_qty, counted_qty=line.counted_qty, diff_qty=line.counted_qty - line.system_qty,
                remark=line.remark, created_id=self._user_id(), updated_id=self._user_id(),
            ))
        await self.db.flush()
        return WmsStockCheckOrderOutSchema.model_validate(order)

    async def audit(self, order_id: int) -> WmsStockCheckOrderOutSchema:
        order = await self._get_order(order_id)
        if order.status != "draft":
            raise CustomException(msg="盘点单不是草稿状态", status_code=400)
        ledger = WmsStockLedgerService(self.auth)
        for line in await self._get_lines(order.id):
            await ledger.adjust_after_check_delta(WmsStockMutationSchema(
                material_id=line.material_id, warehouse_id=line.warehouse_id, location_id=line.location_id,
                batch_no=line.batch_no, quantity=abs(line.diff_qty) or 1, document_type="stock_check", document_no=order.order_no,
            ), line.diff_qty)
            line.status = "audited"
            self._touch(line)
        order.status = "audited"
        order.audited_time = datetime.now()
        self._touch(order)
        await self.db.flush()
        return WmsStockCheckOrderOutSchema.model_validate(order)

    async def _get_order(self, order_id: int) -> WmsStockCheckOrderModel:
        row = (await self.db.execute(select(WmsStockCheckOrderModel).where(WmsStockCheckOrderModel.id == order_id, WmsStockCheckOrderModel.tenant_id == self._tenant_id(), WmsStockCheckOrderModel.is_deleted.is_(False)).limit(1))).scalars().first()
        if not row:
            raise CustomException(msg="盘点单不存在", status_code=404)
        return row

    async def _get_lines(self, order_id: int) -> list[WmsStockCheckLineModel]:
        return list((await self.db.execute(select(WmsStockCheckLineModel).where(WmsStockCheckLineModel.order_id == order_id, WmsStockCheckLineModel.tenant_id == self._tenant_id(), WmsStockCheckLineModel.is_deleted.is_(False)).order_by(WmsStockCheckLineModel.id.asc()))).scalars().all())

    async def _next_no(self, prefix: str) -> str:
        count = (await self.db.execute(select(func.count()).select_from(WmsStockCheckOrderModel))).scalar_one() or 0
        return f"{prefix}{count + 1:08d}"

    def _tenant_id(self) -> int:
        return self.auth.tenant_id or 1

    def _user_id(self) -> int | None:
        return getattr(self.auth.get_user(), "id", None)

    def _touch(self, obj) -> None:
        obj.updated_id = self._user_id()

