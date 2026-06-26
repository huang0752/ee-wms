from typing import Annotated

from fastapi import APIRouter, Depends, Path
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_params import PaginationQueryParam
from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute

from .model import WmsStockCheckLineModel, WmsStockCheckOrderModel
from .schema import WmsStockCheckCreateSchema, WmsStockCheckLineOutSchema, WmsStockCheckOrderOutSchema, WmsStockCheckQueryParam
from .service import WmsStockCheckService

CheckRouter = APIRouter(route_class=OperationLogRoute, prefix="/check", tags=["WMS", "盘点管理"])


@CheckRouter.get("/list", response_model=ResponseSchema[PageResultSchema[WmsStockCheckOrderOutSchema]])
async def list_check_controller(page: Annotated[PaginationQueryParam, Depends()], search: Annotated[WmsStockCheckQueryParam, Depends()], auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:check:query"]))]) -> JSONResponse:
    conditions = [WmsStockCheckOrderModel.tenant_id == (auth.tenant_id or 1), WmsStockCheckOrderModel.is_deleted.is_(False)]
    if search.status and search.status[1]:
        conditions.append(WmsStockCheckOrderModel.status == search.status[1])
    if search.order_no and search.order_no[1]:
        conditions.append(WmsStockCheckOrderModel.order_no.like(f"%{search.order_no[1]}%"))
    offset = ((page.page_no or 1) - 1) * (page.page_size or 10)
    limit = page.page_size or 10
    total = (await auth.db.execute(select(func.count()).select_from(WmsStockCheckOrderModel).where(*conditions))).scalar_one()
    rows = (await auth.db.execute(select(WmsStockCheckOrderModel).where(*conditions).order_by(WmsStockCheckOrderModel.id.desc()).offset(offset).limit(limit))).scalars().all()
    return SuccessResponse(data=PageResultSchema[WmsStockCheckOrderOutSchema](page_no=page.page_no or 1, page_size=limit, total=total, has_next=offset + limit < total, items=[WmsStockCheckOrderOutSchema.model_validate(row) for row in rows]), msg="查询成功")


@CheckRouter.get("/{order_id}/lines", response_model=ResponseSchema[list[WmsStockCheckLineOutSchema]])
async def list_check_lines_controller(order_id: Annotated[int, Path(ge=1)], auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:check:query"]))]) -> JSONResponse:
    rows = (await auth.db.execute(select(WmsStockCheckLineModel).where(WmsStockCheckLineModel.order_id == order_id, WmsStockCheckLineModel.tenant_id == (auth.tenant_id or 1), WmsStockCheckLineModel.is_deleted.is_(False)).order_by(WmsStockCheckLineModel.id.asc()))).scalars().all()
    return SuccessResponse(data=[WmsStockCheckLineOutSchema.model_validate(row) for row in rows], msg="查询成功")


@CheckRouter.post("/create", response_model=ResponseSchema[WmsStockCheckOrderOutSchema])
async def create_check_controller(data: WmsStockCheckCreateSchema, auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:check:create"]))]) -> JSONResponse:
    return SuccessResponse(data=await WmsStockCheckService(auth).create(data), msg="创建成功")


@CheckRouter.post("/audit/{order_id}", response_model=ResponseSchema[WmsStockCheckOrderOutSchema])
async def audit_check_controller(order_id: Annotated[int, Path(ge=1)], auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:check:audit"]))]) -> JSONResponse:
    return SuccessResponse(data=await WmsStockCheckService(auth).audit(order_id), msg="审核成功")

