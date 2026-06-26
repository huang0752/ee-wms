from datetime import datetime

from sqlalchemy import func, select

from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException

from ..master.model import WmsMaterialModel
from ..stock.model import WmsStockBalanceModel
from .model import WmsStockWarningModel
from .schema import WmsStockWarningOutSchema


class WmsStockWarningService:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        if auth.db is None:
            raise CustomException(msg="数据库会话不存在")
        self.db = auth.db

    async def scan(self, warehouse_id: int | None = None) -> list[WmsStockWarningOutSchema]:
        stmt = select(WmsMaterialModel).where(WmsMaterialModel.tenant_id == self._tenant_id(), WmsMaterialModel.is_deleted.is_(False))
        materials = (await self.db.execute(stmt)).scalars().all()
        created = []
        for material in materials:
            total_stmt = select(func.coalesce(func.sum(WmsStockBalanceModel.available_qty), 0)).where(
                WmsStockBalanceModel.tenant_id == self._tenant_id(),
                WmsStockBalanceModel.material_id == material.id,
                WmsStockBalanceModel.is_deleted.is_(False),
            )
            if warehouse_id:
                total_stmt = total_stmt.where(WmsStockBalanceModel.warehouse_id == warehouse_id)
            available = (await self.db.execute(total_stmt)).scalar_one()
            if material.safety_stock is not None and available < material.safety_stock:
                warning = await self._create_warning("safety_stock", material.id, warehouse_id, available, material.safety_stock)
                created.append(warning)
            if available <= 0:
                warning = await self._create_warning("shortage", material.id, warehouse_id, available, 0)
                created.append(warning)
        await self.db.flush()
        return [WmsStockWarningOutSchema.model_validate(item) for item in created]

    async def close(self, warning_id: int) -> WmsStockWarningOutSchema:
        warning = (await self.db.execute(select(WmsStockWarningModel).where(WmsStockWarningModel.id == warning_id, WmsStockWarningModel.tenant_id == self._tenant_id(), WmsStockWarningModel.is_deleted.is_(False)).limit(1))).scalars().first()
        if not warning:
            raise CustomException(msg="预警不存在", status_code=404)
        warning.status = "closed"
        warning.handled_time = datetime.now()
        warning.updated_id = self._user_id()
        await self.db.flush()
        return WmsStockWarningOutSchema.model_validate(warning)

    async def _create_warning(self, warning_type, material_id, warehouse_id, current_qty, threshold_qty):
        warning = WmsStockWarningModel(
            tenant_id=self._tenant_id(), warning_no=await self._next_no("WRN"), warning_type=warning_type,
            material_id=material_id, warehouse_id=warehouse_id, current_qty=current_qty, threshold_qty=threshold_qty,
            created_id=self._user_id(), updated_id=self._user_id(),
        )
        self.db.add(warning)
        await self.db.flush()
        return warning

    async def _next_no(self, prefix: str) -> str:
        count = (await self.db.execute(select(func.count()).select_from(WmsStockWarningModel))).scalar_one() or 0
        return f"{prefix}{count + 1:08d}"

    def _tenant_id(self) -> int:
        return self.auth.tenant_id or 1

    def _user_id(self) -> int | None:
        return getattr(self.auth.get_user(), "id", None)
