from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from app.common.enums import QueueEnum
from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_params import PaginationQueryParam
from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute

from .model import WmsInboundLineModel, WmsInboundOrderModel
from .schema import (
    WmsInboundCreateFromInspectionSchema,
    WmsInboundLineOutSchema,
    WmsInboundOrderOutSchema,
    WmsInboundQueryParam,
    WmsLocationRecommendOutSchema,
)
from .service import WmsInboundService

InboundRouter = APIRouter(route_class=OperationLogRoute, prefix="/inbound", tags=["WMS", "入库管理"])


@InboundRouter.get("/list", summary="WMS入库单列表", response_model=ResponseSchema[PageResultSchema[WmsInboundOrderOutSchema]])
async def list_inbound_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[WmsInboundQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:inbound:query"]))],
) -> JSONResponse:
    conditions = _conditions(WmsInboundOrderModel, vars(search), auth.tenant_id or 1)
    offset = ((page.page_no or 1) - 1) * (page.page_size or 10)
    limit = page.page_size or 10
    total = (await auth.db.execute(select(func.count()).select_from(WmsInboundOrderModel).where(*conditions))).scalar_one()
    rows = (await auth.db.execute(select(WmsInboundOrderModel).where(*conditions).order_by(WmsInboundOrderModel.id.desc()).offset(offset).limit(limit))).scalars().all()
    return SuccessResponse(
        data=PageResultSchema[WmsInboundOrderOutSchema](
            page_no=page.page_no or 1,
            page_size=limit,
            total=total,
            has_next=offset + limit < total,
            items=[WmsInboundOrderOutSchema.model_validate(row) for row in rows],
        ),
        msg="查询成功",
    )


@InboundRouter.get("/{order_id}/lines", summary="WMS入库明细", response_model=ResponseSchema[list[WmsInboundLineOutSchema]])
async def list_inbound_lines_controller(
    order_id: Annotated[int, Path(description="入库单ID", ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:inbound:query"]))],
) -> JSONResponse:
    rows = (
        await auth.db.execute(
            select(WmsInboundLineModel)
            .where(
                WmsInboundLineModel.order_id == order_id,
                WmsInboundLineModel.tenant_id == (auth.tenant_id or 1),
                WmsInboundLineModel.is_deleted.is_(False),
            )
            .order_by(WmsInboundLineModel.id.asc())
        )
    ).scalars().all()
    return SuccessResponse(data=[WmsInboundLineOutSchema.model_validate(row) for row in rows], msg="查询成功")


@InboundRouter.post(
    "/create-from-inspection/{task_id}",
    summary="从检验任务创建WMS入库单",
    response_model=ResponseSchema[WmsInboundOrderOutSchema],
)
async def create_inbound_from_inspection_controller(
    task_id: Annotated[int, Path(description="检验任务ID", ge=1)],
    data: WmsInboundCreateFromInspectionSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:inbound:create"]))],
) -> JSONResponse:
    result = await WmsInboundService(auth).create_from_inspection(task_id, data)
    return SuccessResponse(data=result, msg="创建成功")


@InboundRouter.post("/confirm/{order_id}", summary="确认WMS入库并过账", response_model=ResponseSchema[WmsInboundOrderOutSchema])
async def confirm_inbound_controller(
    order_id: Annotated[int, Path(description="入库单ID", ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:inbound:confirm"]))],
) -> JSONResponse:
    result = await WmsInboundService(auth).confirm(order_id)
    return SuccessResponse(data=result, msg="入库确认成功")


@InboundRouter.get("/recommend-location", summary="推荐WMS入库库位", response_model=ResponseSchema[list[WmsLocationRecommendOutSchema]])
async def recommend_location_controller(
    material_id: Annotated[int, Query(description="物料ID", ge=1)],
    warehouse_id: Annotated[int, Query(description="仓库ID", ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:inbound:query"]))],
) -> JSONResponse:
    result = await WmsInboundService(auth).recommend_location(material_id, warehouse_id)
    return SuccessResponse(data=result, msg="推荐成功")


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
