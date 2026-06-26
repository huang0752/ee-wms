from sqlalchemy import and_, select

from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException

from .model import WmsStockBalanceModel
from .schema import WmsStockBalanceOutSchema, WmsStockLockSchema


class WmsStockRecommendService:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        if auth.db is None:
            raise CustomException(msg="数据库会话不存在")
        self.db = auth.db

    async def recommend_outbound(self, query: WmsStockLockSchema) -> list[WmsStockBalanceOutSchema]:
        conditions = [
            WmsStockBalanceModel.tenant_id == (self.auth.tenant_id or 1),
            WmsStockBalanceModel.material_id == query.material_id,
            WmsStockBalanceModel.available_qty > 0,
            WmsStockBalanceModel.pending_qty >= 0,
            WmsStockBalanceModel.frozen_qty >= 0,
            WmsStockBalanceModel.defective_qty >= 0,
            WmsStockBalanceModel.is_deleted.is_(False),
        ]
        if query.warehouse_id:
            conditions.append(WmsStockBalanceModel.warehouse_id == query.warehouse_id)
        if query.location_id:
            conditions.append(WmsStockBalanceModel.location_id == query.location_id)
        stmt = select(WmsStockBalanceModel).where(and_(*conditions)).order_by(WmsStockBalanceModel.created_time.asc(), WmsStockBalanceModel.id.asc())
        rows = (await self.db.execute(stmt)).scalars().all()
        return [WmsStockBalanceOutSchema.model_validate(row) for row in rows]
