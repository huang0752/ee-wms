from typing import Annotated

from fastapi import APIRouter, Depends, Path
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from app.common.enums import QueueEnum
from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_params import PaginationQueryParam
from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute

from .ledger_service import WmsStockLedgerService
from .model import WmsStockBalanceModel, WmsStockFlowModel
from .recommend_service import WmsStockRecommendService
from .schema import (
    WmsStockAdjustSchema,
    WmsStockBalanceOutSchema,
    WmsStockBalanceQueryParam,
    WmsStockFlowOutSchema,
    WmsStockFlowQueryParam,
    WmsStockLockOutSchema,
    WmsStockLockSchema,
    WmsStockMutationSchema,
)

StockRouter = APIRouter(route_class=OperationLogRoute, prefix="/stock", tags=["WMS", "库存管理"])


@StockRouter.get(
    "/balance/list",
    summary="WMS库存余额列表",
    response_model=ResponseSchema[PageResultSchema[WmsStockBalanceOutSchema]],
)
async def list_stock_balance_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[WmsStockBalanceQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:stock:query"]))],
) -> JSONResponse:
    conditions = _query_conditions(WmsStockBalanceModel, vars(search), auth.tenant_id or 1)
    if search.only_available is True:
        conditions.append(WmsStockBalanceModel.available_qty > 0)
    offset = ((page.page_no or 1) - 1) * (page.page_size or 10)
    limit = page.page_size or 10
    total = (await auth.db.execute(select(func.count()).select_from(WmsStockBalanceModel).where(*conditions))).scalar_one()
    stmt = select(WmsStockBalanceModel).where(*conditions).order_by(WmsStockBalanceModel.id.desc()).offset(offset).limit(limit)
    rows = (await auth.db.execute(stmt)).scalars().all()
    return SuccessResponse(
        data=PageResultSchema[WmsStockBalanceOutSchema](
            page_no=page.page_no or 1,
            page_size=limit,
            total=total,
            has_next=offset + limit < total,
            items=[WmsStockBalanceOutSchema.model_validate(row) for row in rows],
        ),
        msg="查询成功",
    )


@StockRouter.get(
    "/flow/list",
    summary="WMS库存流水列表",
    response_model=ResponseSchema[PageResultSchema[WmsStockFlowOutSchema]],
)
async def list_stock_flow_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[WmsStockFlowQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:stock:query"]))],
) -> JSONResponse:
    conditions = _query_conditions(WmsStockFlowModel, vars(search), auth.tenant_id or 1)
    offset = ((page.page_no or 1) - 1) * (page.page_size or 10)
    limit = page.page_size or 10
    total = (await auth.db.execute(select(func.count()).select_from(WmsStockFlowModel).where(*conditions))).scalar_one()
    stmt = select(WmsStockFlowModel).where(*conditions).order_by(WmsStockFlowModel.id.asc()).offset(offset).limit(limit)
    rows = (await auth.db.execute(stmt)).scalars().all()
    return SuccessResponse(
        data=PageResultSchema[WmsStockFlowOutSchema](
            page_no=page.page_no or 1,
            page_size=limit,
            total=total,
            has_next=offset + limit < total,
            items=[WmsStockFlowOutSchema.model_validate(row) for row in rows],
        ),
        msg="查询成功",
    )


@StockRouter.post(
    "/receive-pending",
    summary="WMS收货进入待检库存",
    response_model=ResponseSchema[WmsStockBalanceOutSchema],
)
async def receive_pending_controller(
    data: WmsStockMutationSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:stock:create"]))],
) -> JSONResponse:
    result = await WmsStockLedgerService(auth).receive_pending(data)
    return SuccessResponse(data=result, msg="收货成功")


@StockRouter.post(
    "/approve-to-available",
    summary="WMS待检库存转可用",
    response_model=ResponseSchema[WmsStockBalanceOutSchema],
)
async def approve_to_available_controller(
    data: WmsStockMutationSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:stock:update"]))],
) -> JSONResponse:
    result = await WmsStockLedgerService(auth).approve_to_available(data)
    return SuccessResponse(data=result, msg="转可用成功")


@StockRouter.post(
    "/lock",
    summary="WMS锁定库存",
    response_model=ResponseSchema[list[WmsStockLockOutSchema]],
)
async def lock_stock_controller(
    data: WmsStockLockSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:stock:lock"]))],
) -> JSONResponse:
    result = await WmsStockLedgerService(auth).lock_stock(data)
    return SuccessResponse(data=result, msg="锁定成功")


@StockRouter.post(
    "/release-lock/{lock_id}",
    summary="WMS释放锁定库存",
    response_model=ResponseSchema[WmsStockBalanceOutSchema],
)
async def release_lock_controller(
    lock_id: Annotated[int, Path(description="锁库ID", ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:stock:unlock"]))],
) -> JSONResponse:
    result = await WmsStockLedgerService(auth).release_lock(lock_id)
    return SuccessResponse(data=result, msg="释放成功")


@StockRouter.post(
    "/ship-lock/{lock_id}",
    summary="WMS锁定库存出库",
    response_model=ResponseSchema[WmsStockBalanceOutSchema],
)
async def ship_locked_controller(
    lock_id: Annotated[int, Path(description="锁库ID", ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:stock:ship"]))],
) -> JSONResponse:
    result = await WmsStockLedgerService(auth).ship_locked(lock_id)
    return SuccessResponse(data=result, msg="出库成功")


@StockRouter.post(
    "/freeze",
    summary="WMS冻结库存",
    response_model=ResponseSchema[WmsStockBalanceOutSchema],
)
async def freeze_stock_controller(
    data: WmsStockMutationSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:stock:freeze"]))],
) -> JSONResponse:
    result = await WmsStockLedgerService(auth).freeze(data)
    return SuccessResponse(data=result, msg="冻结成功")


@StockRouter.post(
    "/unfreeze",
    summary="WMS解冻库存",
    response_model=ResponseSchema[WmsStockBalanceOutSchema],
)
async def unfreeze_stock_controller(
    data: WmsStockMutationSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:stock:unfreeze"]))],
) -> JSONResponse:
    result = await WmsStockLedgerService(auth).unfreeze(data)
    return SuccessResponse(data=result, msg="解冻成功")


@StockRouter.post(
    "/adjust-after-check",
    summary="WMS盘点审核后调整库存",
    response_model=ResponseSchema[WmsStockBalanceOutSchema],
)
async def adjust_after_check_controller(
    data: WmsStockAdjustSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:stock:adjust"]))],
) -> JSONResponse:
    result = await WmsStockLedgerService(auth).adjust_after_check(data)
    return SuccessResponse(data=result, msg="调整成功")


@StockRouter.post(
    "/recommend",
    summary="WMS出库库存推荐",
    response_model=ResponseSchema[list[WmsStockBalanceOutSchema]],
)
async def recommend_stock_controller(
    data: WmsStockLockSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:stock:query"]))],
) -> JSONResponse:
    result = await WmsStockRecommendService(auth).recommend_outbound(data)
    return SuccessResponse(data=result, msg="推荐成功")


def _query_conditions(model: type, search: dict, tenant_id: int) -> list:
    conditions = [model.tenant_id == tenant_id, model.is_deleted.is_(False)]
    for key, value in search.items():
        if key in {"only_available", "page_no", "page_size", "order_by"} or value is None:
            continue
        column = getattr(model, key, None)
        if column is None:
            continue
        if isinstance(value, tuple):
            operator, operand = value
            if operand in (None, ""):
                continue
            if operator == QueueEnum.like.value:
                conditions.append(column.like(f"%{operand}%"))
            elif operator == QueueEnum.eq.value:
                conditions.append(column == operand)
        else:
            conditions.append(column == value)
    return conditions
