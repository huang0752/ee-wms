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

from ..inspection.schema import WmsInspectionTaskOutSchema
from .model import WmsArrivalLineModel, WmsArrivalOrderModel
from .schema import WmsArrivalCreateSchema, WmsArrivalLineOutSchema, WmsArrivalOrderOutSchema, WmsArrivalQueryParam
from .service import WmsArrivalService

ArrivalRouter = APIRouter(route_class=OperationLogRoute, prefix="/arrival", tags=["WMS", "到货管理"])


@ArrivalRouter.get("/list", summary="WMS到货单列表", response_model=ResponseSchema[PageResultSchema[WmsArrivalOrderOutSchema]])
async def list_arrival_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[WmsArrivalQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:arrival:query"]))],
) -> JSONResponse:
    conditions = _conditions(WmsArrivalOrderModel, vars(search), auth.tenant_id or 1)
    offset = ((page.page_no or 1) - 1) * (page.page_size or 10)
    limit = page.page_size or 10
    total = (await auth.db.execute(select(func.count()).select_from(WmsArrivalOrderModel).where(*conditions))).scalar_one()
    rows = (await auth.db.execute(select(WmsArrivalOrderModel).where(*conditions).order_by(WmsArrivalOrderModel.id.desc()).offset(offset).limit(limit))).scalars().all()
    return SuccessResponse(
        data=PageResultSchema[WmsArrivalOrderOutSchema](
            page_no=page.page_no or 1,
            page_size=limit,
            total=total,
            has_next=offset + limit < total,
            items=[WmsArrivalOrderOutSchema.model_validate(row) for row in rows],
        ),
        msg="查询成功",
    )


@ArrivalRouter.get("/{order_id}/lines", summary="WMS到货明细", response_model=ResponseSchema[list[WmsArrivalLineOutSchema]])
async def list_arrival_lines_controller(
    order_id: Annotated[int, Path(description="到货单ID", ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:arrival:query"]))],
) -> JSONResponse:
    rows = (
        await auth.db.execute(
            select(WmsArrivalLineModel)
            .where(
                WmsArrivalLineModel.order_id == order_id,
                WmsArrivalLineModel.tenant_id == (auth.tenant_id or 1),
                WmsArrivalLineModel.is_deleted.is_(False),
            )
            .order_by(WmsArrivalLineModel.id.asc())
        )
    ).scalars().all()
    return SuccessResponse(data=[WmsArrivalLineOutSchema.model_validate(row) for row in rows], msg="查询成功")


@ArrivalRouter.post("/create", summary="创建WMS到货单", response_model=ResponseSchema[WmsArrivalOrderOutSchema])
async def create_arrival_controller(
    data: WmsArrivalCreateSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:arrival:create"]))],
) -> JSONResponse:
    result = await WmsArrivalService(auth).create(data)
    return SuccessResponse(data=result, msg="创建成功")


@ArrivalRouter.post("/receive/{order_id}", summary="WMS到货收货并生成检验任务", response_model=ResponseSchema[WmsInspectionTaskOutSchema])
async def receive_arrival_controller(
    order_id: Annotated[int, Path(description="到货单ID", ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:arrival:receive"]))],
) -> JSONResponse:
    result = await WmsArrivalService(auth).receive(order_id)
    return SuccessResponse(data=result, msg="收货成功")


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
