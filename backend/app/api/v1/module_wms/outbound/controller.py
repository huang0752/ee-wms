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

from .model import WmsOutboundLineModel, WmsOutboundOrderModel
from .schema import WmsOutboundCreateSchema, WmsOutboundLineOutSchema, WmsOutboundOrderOutSchema, WmsOutboundQueryParam
from .service import WmsOutboundService

OutboundRouter = APIRouter(route_class=OperationLogRoute, prefix="/outbound", tags=["WMS", "出库管理"])


@OutboundRouter.get("/list", summary="WMS出库单列表", response_model=ResponseSchema[PageResultSchema[WmsOutboundOrderOutSchema]])
async def list_outbound_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[WmsOutboundQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:outbound:query"]))],
) -> JSONResponse:
    conditions = _conditions(WmsOutboundOrderModel, vars(search), auth.tenant_id or 1)
    offset = ((page.page_no or 1) - 1) * (page.page_size or 10)
    limit = page.page_size or 10
    total = (await auth.db.execute(select(func.count()).select_from(WmsOutboundOrderModel).where(*conditions))).scalar_one()
    rows = (await auth.db.execute(select(WmsOutboundOrderModel).where(*conditions).order_by(WmsOutboundOrderModel.id.desc()).offset(offset).limit(limit))).scalars().all()
    return SuccessResponse(
        data=PageResultSchema[WmsOutboundOrderOutSchema](
            page_no=page.page_no or 1,
            page_size=limit,
            total=total,
            has_next=offset + limit < total,
            items=[WmsOutboundOrderOutSchema.model_validate(row) for row in rows],
        ),
        msg="查询成功",
    )


@OutboundRouter.get("/{order_id}/lines", summary="WMS出库明细", response_model=ResponseSchema[list[WmsOutboundLineOutSchema]])
async def list_outbound_lines_controller(
    order_id: Annotated[int, Path(description="出库单ID", ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:outbound:query"]))],
) -> JSONResponse:
    rows = (
        await auth.db.execute(
            select(WmsOutboundLineModel)
            .where(
                WmsOutboundLineModel.order_id == order_id,
                WmsOutboundLineModel.tenant_id == (auth.tenant_id or 1),
                WmsOutboundLineModel.is_deleted.is_(False),
            )
            .order_by(WmsOutboundLineModel.id.asc())
        )
    ).scalars().all()
    return SuccessResponse(data=[WmsOutboundLineOutSchema.model_validate(row) for row in rows], msg="查询成功")


@OutboundRouter.post("/create", summary="创建WMS出库单", response_model=ResponseSchema[WmsOutboundOrderOutSchema])
async def create_outbound_controller(
    data: WmsOutboundCreateSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:outbound:create"]))],
) -> JSONResponse:
    result = await WmsOutboundService(auth).create(data)
    return SuccessResponse(data=result, msg="创建成功")


@OutboundRouter.post("/reserve/{order_id}", summary="WMS出库锁库", response_model=ResponseSchema[WmsOutboundOrderOutSchema])
async def reserve_outbound_controller(
    order_id: Annotated[int, Path(description="出库单ID", ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:outbound:reserve"]))],
) -> JSONResponse:
    result = await WmsOutboundService(auth).reserve(order_id)
    return SuccessResponse(data=result, msg="锁库成功")


@OutboundRouter.post("/pick/{order_id}", summary="WMS出库拣货", response_model=ResponseSchema[WmsOutboundOrderOutSchema])
async def pick_outbound_controller(
    order_id: Annotated[int, Path(description="出库单ID", ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:outbound:pick"]))],
) -> JSONResponse:
    result = await WmsOutboundService(auth).pick(order_id)
    return SuccessResponse(data=result, msg="拣货成功")


@OutboundRouter.post("/review/{order_id}", summary="WMS出库复核", response_model=ResponseSchema[WmsOutboundOrderOutSchema])
async def review_outbound_controller(
    order_id: Annotated[int, Path(description="出库单ID", ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:outbound:review"]))],
) -> JSONResponse:
    result = await WmsOutboundService(auth).review(order_id)
    return SuccessResponse(data=result, msg="复核成功")


@OutboundRouter.post("/confirm/{order_id}", summary="WMS出库确认", response_model=ResponseSchema[WmsOutboundOrderOutSchema])
async def confirm_outbound_controller(
    order_id: Annotated[int, Path(description="出库单ID", ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:outbound:confirm"]))],
) -> JSONResponse:
    result = await WmsOutboundService(auth).confirm(order_id)
    return SuccessResponse(data=result, msg="出库确认成功")


@OutboundRouter.post("/cancel/{order_id}", summary="WMS出库取消", response_model=ResponseSchema[WmsOutboundOrderOutSchema])
async def cancel_outbound_controller(
    order_id: Annotated[int, Path(description="出库单ID", ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:outbound:cancel"]))],
) -> JSONResponse:
    result = await WmsOutboundService(auth).cancel(order_id)
    return SuccessResponse(data=result, msg="取消成功")


def _conditions(model: type, search: dict, tenant_id: int) -> list:
    conditions = [model.tenant_id == tenant_id, model.is_deleted.is_(False)]
    for key, value in search.items():
        if key in {"page_no", "page_size", "order_by"} or value is None:
            continue
        column = getattr(model, key, None)
        if column is None or not isinstance(value, tuple):
            continue
        operator, operand = value
        if operand in (None, ""):
            continue
        if operator == QueueEnum.like.value:
            conditions.append(column.like(f"%{operand}%"))
        elif operator == QueueEnum.eq.value:
            conditions.append(column == operand)
    return conditions
