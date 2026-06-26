from typing import Annotated

from fastapi import APIRouter, Depends, Path
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_params import PaginationQueryParam
from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute

from .model import WmsTransferLineModel, WmsTransferOrderModel
from .schema import WmsTransferCreateSchema, WmsTransferLineOutSchema, WmsTransferOrderOutSchema, WmsTransferQueryParam
from .service import WmsTransferService

TransferRouter = APIRouter(route_class=OperationLogRoute, prefix="/transfer", tags=["WMS", "调拨管理"])


@TransferRouter.get("/list", response_model=ResponseSchema[PageResultSchema[WmsTransferOrderOutSchema]])
async def list_transfer_controller(page: Annotated[PaginationQueryParam, Depends()], search: Annotated[WmsTransferQueryParam, Depends()], auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:transfer:query"]))]) -> JSONResponse:
    conditions = [WmsTransferOrderModel.tenant_id == (auth.tenant_id or 1), WmsTransferOrderModel.is_deleted.is_(False)]
    if search.status and search.status[1]:
        conditions.append(WmsTransferOrderModel.status == search.status[1])
    if search.order_no and search.order_no[1]:
        conditions.append(WmsTransferOrderModel.order_no.like(f"%{search.order_no[1]}%"))
    offset = ((page.page_no or 1) - 1) * (page.page_size or 10)
    limit = page.page_size or 10
    total = (await auth.db.execute(select(func.count()).select_from(WmsTransferOrderModel).where(*conditions))).scalar_one()
    rows = (await auth.db.execute(select(WmsTransferOrderModel).where(*conditions).order_by(WmsTransferOrderModel.id.desc()).offset(offset).limit(limit))).scalars().all()
    return SuccessResponse(data=PageResultSchema[WmsTransferOrderOutSchema](page_no=page.page_no or 1, page_size=limit, total=total, has_next=offset + limit < total, items=[WmsTransferOrderOutSchema.model_validate(row) for row in rows]), msg="查询成功")


@TransferRouter.get("/{order_id}/lines", response_model=ResponseSchema[list[WmsTransferLineOutSchema]])
async def list_transfer_lines_controller(order_id: Annotated[int, Path(ge=1)], auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:transfer:query"]))]) -> JSONResponse:
    rows = (await auth.db.execute(select(WmsTransferLineModel).where(WmsTransferLineModel.order_id == order_id, WmsTransferLineModel.tenant_id == (auth.tenant_id or 1), WmsTransferLineModel.is_deleted.is_(False)).order_by(WmsTransferLineModel.id.asc()))).scalars().all()
    return SuccessResponse(data=[WmsTransferLineOutSchema.model_validate(row) for row in rows], msg="查询成功")


@TransferRouter.post("/create", response_model=ResponseSchema[WmsTransferOrderOutSchema])
async def create_transfer_controller(data: WmsTransferCreateSchema, auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:transfer:create"]))]) -> JSONResponse:
    return SuccessResponse(data=await WmsTransferService(auth).create(data), msg="创建成功")


@TransferRouter.post("/confirm/{order_id}", response_model=ResponseSchema[WmsTransferOrderOutSchema])
async def confirm_transfer_controller(order_id: Annotated[int, Path(ge=1)], auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:transfer:confirm"]))]) -> JSONResponse:
    return SuccessResponse(data=await WmsTransferService(auth).confirm(order_id), msg="确认成功")

