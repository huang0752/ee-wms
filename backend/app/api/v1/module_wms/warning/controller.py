from typing import Annotated

from fastapi import APIRouter, Depends, Path
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_params import PaginationQueryParam
from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute

from .model import WmsStockWarningModel
from .schema import WmsStockWarningOutSchema, WmsStockWarningQueryParam, WmsWarningScanSchema
from .service import WmsStockWarningService

WarningRouter = APIRouter(route_class=OperationLogRoute, prefix="/warning", tags=["WMS", "库存预警"])


@WarningRouter.get("/list", response_model=ResponseSchema[PageResultSchema[WmsStockWarningOutSchema]])
async def list_warning_controller(page: Annotated[PaginationQueryParam, Depends()], search: Annotated[WmsStockWarningQueryParam, Depends()], auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:warning:query"]))]) -> JSONResponse:
    conditions = [WmsStockWarningModel.tenant_id == (auth.tenant_id or 1), WmsStockWarningModel.is_deleted.is_(False)]
    if search.status and search.status[1]:
        conditions.append(WmsStockWarningModel.status == search.status[1])
    if search.warning_type and search.warning_type[1]:
        conditions.append(WmsStockWarningModel.warning_type == search.warning_type[1])
    offset = ((page.page_no or 1) - 1) * (page.page_size or 10)
    limit = page.page_size or 10
    total = (await auth.db.execute(select(func.count()).select_from(WmsStockWarningModel).where(*conditions))).scalar_one()
    rows = (await auth.db.execute(select(WmsStockWarningModel).where(*conditions).order_by(WmsStockWarningModel.id.desc()).offset(offset).limit(limit))).scalars().all()
    return SuccessResponse(data=PageResultSchema[WmsStockWarningOutSchema](page_no=page.page_no or 1, page_size=limit, total=total, has_next=offset + limit < total, items=[WmsStockWarningOutSchema.model_validate(row) for row in rows]), msg="查询成功")


@WarningRouter.post("/scan", response_model=ResponseSchema[list[WmsStockWarningOutSchema]])
async def scan_warning_controller(data: WmsWarningScanSchema, auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:warning:scan"]))]) -> JSONResponse:
    return SuccessResponse(data=await WmsStockWarningService(auth).scan(data.warehouse_id), msg="扫描成功")


@WarningRouter.post("/close/{warning_id}", response_model=ResponseSchema[WmsStockWarningOutSchema])
async def close_warning_controller(warning_id: Annotated[int, Path(ge=1)], auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:warning:close"]))]) -> JSONResponse:
    return SuccessResponse(data=await WmsStockWarningService(auth).close(warning_id), msg="关闭成功")

