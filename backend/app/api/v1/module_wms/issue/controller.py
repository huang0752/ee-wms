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

from .model import WmsIssueLineModel, WmsIssueOrderModel
from .schema import WmsIssueCreateSchema, WmsIssueLineOutSchema, WmsIssueOrderOutSchema, WmsIssueQueryParam
from .service import WmsIssueService

IssueRouter = APIRouter(route_class=OperationLogRoute, prefix="/issue", tags=["WMS", "生产领料"])


@IssueRouter.get("/list", summary="WMS领料单列表", response_model=ResponseSchema[PageResultSchema[WmsIssueOrderOutSchema]])
async def list_issue_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[WmsIssueQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:issue:query"]))],
) -> JSONResponse:
    conditions = _conditions(WmsIssueOrderModel, vars(search), auth.tenant_id or 1)
    offset = ((page.page_no or 1) - 1) * (page.page_size or 10)
    limit = page.page_size or 10
    total = (await auth.db.execute(select(func.count()).select_from(WmsIssueOrderModel).where(*conditions))).scalar_one()
    rows = (await auth.db.execute(select(WmsIssueOrderModel).where(*conditions).order_by(WmsIssueOrderModel.id.desc()).offset(offset).limit(limit))).scalars().all()
    return SuccessResponse(
        data=PageResultSchema[WmsIssueOrderOutSchema](
            page_no=page.page_no or 1,
            page_size=limit,
            total=total,
            has_next=offset + limit < total,
            items=[WmsIssueOrderOutSchema.model_validate(row) for row in rows],
        ),
        msg="查询成功",
    )


@IssueRouter.get("/{order_id}/lines", summary="WMS领料明细", response_model=ResponseSchema[list[WmsIssueLineOutSchema]])
async def list_issue_lines_controller(
    order_id: Annotated[int, Path(description="领料单ID", ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:issue:query"]))],
) -> JSONResponse:
    rows = (
        await auth.db.execute(
            select(WmsIssueLineModel)
            .where(
                WmsIssueLineModel.order_id == order_id,
                WmsIssueLineModel.tenant_id == (auth.tenant_id or 1),
                WmsIssueLineModel.is_deleted.is_(False),
            )
            .order_by(WmsIssueLineModel.id.asc())
        )
    ).scalars().all()
    return SuccessResponse(data=[WmsIssueLineOutSchema.model_validate(row) for row in rows], msg="查询成功")


@IssueRouter.post("/create", summary="创建WMS领料单", response_model=ResponseSchema[WmsIssueOrderOutSchema])
async def create_issue_controller(
    data: WmsIssueCreateSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:issue:create"]))],
) -> JSONResponse:
    result = await WmsIssueService(auth).create(data)
    return SuccessResponse(data=result, msg="创建成功")


@IssueRouter.post("/reserve/{order_id}", summary="WMS领料锁库", response_model=ResponseSchema[WmsIssueOrderOutSchema])
async def reserve_issue_controller(
    order_id: Annotated[int, Path(description="领料单ID", ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:issue:reserve"]))],
) -> JSONResponse:
    result = await WmsIssueService(auth).reserve(order_id)
    return SuccessResponse(data=result, msg="锁库成功")


@IssueRouter.post("/pick/{order_id}", summary="WMS领料拣货", response_model=ResponseSchema[WmsIssueOrderOutSchema])
async def pick_issue_controller(
    order_id: Annotated[int, Path(description="领料单ID", ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:issue:pick"]))],
) -> JSONResponse:
    result = await WmsIssueService(auth).pick(order_id)
    return SuccessResponse(data=result, msg="拣货成功")


@IssueRouter.post("/review/{order_id}", summary="WMS领料复核", response_model=ResponseSchema[WmsIssueOrderOutSchema])
async def review_issue_controller(
    order_id: Annotated[int, Path(description="领料单ID", ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:issue:review"]))],
) -> JSONResponse:
    result = await WmsIssueService(auth).review(order_id)
    return SuccessResponse(data=result, msg="复核成功")


@IssueRouter.post("/confirm/{order_id}", summary="WMS领料确认", response_model=ResponseSchema[WmsIssueOrderOutSchema])
async def confirm_issue_controller(
    order_id: Annotated[int, Path(description="领料单ID", ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:issue:confirm"]))],
) -> JSONResponse:
    result = await WmsIssueService(auth).confirm(order_id)
    return SuccessResponse(data=result, msg="领料确认成功")


@IssueRouter.post("/cancel/{order_id}", summary="WMS领料取消", response_model=ResponseSchema[WmsIssueOrderOutSchema])
async def cancel_issue_controller(
    order_id: Annotated[int, Path(description="领料单ID", ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:issue:cancel"]))],
) -> JSONResponse:
    result = await WmsIssueService(auth).cancel(order_id)
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
