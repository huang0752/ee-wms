from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException

from .master.model import (
    WmsCustomerModel,
    WmsLocationModel,
    WmsMaterialModel,
    WmsSupplierModel,
    WmsWarehouseModel,
)


def require_wms_tenant_id(auth: AuthSchema) -> int:
    if auth.tenant_id is None:
        raise CustomException(msg="租户上下文缺失", status_code=403)
    return auth.tenant_id


async def ensure_wms_material(db: AsyncSession, tenant_id: int, material_id: int) -> WmsMaterialModel:
    return await _ensure_row(db, WmsMaterialModel, tenant_id, material_id, "物料")


async def ensure_wms_warehouse(db: AsyncSession, tenant_id: int, warehouse_id: int) -> WmsWarehouseModel:
    return await _ensure_row(db, WmsWarehouseModel, tenant_id, warehouse_id, "仓库")


async def ensure_wms_supplier(db: AsyncSession, tenant_id: int, supplier_id: int | None) -> WmsSupplierModel | None:
    if supplier_id is None:
        return None
    return await _ensure_row(db, WmsSupplierModel, tenant_id, supplier_id, "供应商")


async def ensure_wms_customer(db: AsyncSession, tenant_id: int, customer_id: int | None) -> WmsCustomerModel | None:
    if customer_id is None:
        return None
    return await _ensure_row(db, WmsCustomerModel, tenant_id, customer_id, "客户")


async def ensure_wms_location(
    db: AsyncSession,
    tenant_id: int,
    location_id: int | None,
    *,
    warehouse_id: int | None = None,
) -> WmsLocationModel | None:
    if location_id is None:
        return None
    location = await _ensure_row(db, WmsLocationModel, tenant_id, location_id, "库位")
    if warehouse_id is not None and location.warehouse_id != warehouse_id:
        raise CustomException(msg="库位不属于指定仓库", status_code=400)
    return location


async def _ensure_row(db: AsyncSession, model, tenant_id: int, row_id: int, label: str):
    stmt = (
        select(model)
        .where(
            model.id == row_id,
            model.tenant_id == tenant_id,
            model.is_deleted.is_(False),
        )
        .limit(1)
    )
    row = (await db.execute(stmt)).scalars().first()
    if not row:
        raise CustomException(msg=f"{label}不存在或不属于当前租户", status_code=400)
    return row
