from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path
from fastapi.responses import JSONResponse

from app.common.response import ResponseSchema, SuccessResponse
from app.core import cache_util
from app.core.base_params import PaginationQueryParam
from app.core.base_schema import AuthSchema, BatchSetAvailable, PageResultSchema
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute

from .schema import (
    WmsMasterCreateSchema,
    WmsMasterOutSchema,
    WmsMasterQueryParam,
    WmsMasterResource,
    WmsMasterUpdateSchema,
)
from .service import WmsMasterService

MasterRouter = APIRouter(route_class=OperationLogRoute, prefix="/master", tags=["WMS", "仓储基础"])

_MASTER_NS = "wms_master"


def _permission(resource: WmsMasterResource, action: str) -> list[str]:
    normalized = resource.replace("-", "_")
    return [f"module_wms:{normalized}:{action}"]


@MasterRouter.get(
    "/{resource}/list",
    summary="WMS主数据列表",
    response_model=ResponseSchema[PageResultSchema[WmsMasterOutSchema]],
)
async def list_master_controller(
    resource: Annotated[WmsMasterResource, Path(description="主数据资源")],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[WmsMasterQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:master:query"]))],
) -> JSONResponse:
    result = await WmsMasterService(auth, resource).page(
        page_no=page.page_no or 1,
        page_size=page.page_size or 10,
        search=search,
        order_by=page.order_by,
    )
    return SuccessResponse(data=result, msg="查询成功")


@MasterRouter.get(
    "/{resource}/detail/{id}",
    summary="WMS主数据详情",
    response_model=ResponseSchema[WmsMasterOutSchema],
)
async def detail_master_controller(
    resource: Annotated[WmsMasterResource, Path(description="主数据资源")],
    id: Annotated[int, Path(description="数据ID", ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:master:query"]))],
) -> JSONResponse:
    result = await WmsMasterService(auth, resource).detail(id=id)
    return SuccessResponse(data=result, msg="查询成功")


@MasterRouter.post(
    "/{resource}/create",
    summary="创建WMS主数据",
    response_model=ResponseSchema[WmsMasterOutSchema],
)
async def create_master_controller(
    resource: Annotated[WmsMasterResource, Path(description="主数据资源")],
    data: WmsMasterCreateSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:master:create"]))],
) -> JSONResponse:
    result = await WmsMasterService(auth, resource).create(data=data)
    await cache_util.clear(namespace=_MASTER_NS)
    return SuccessResponse(data=result, msg="创建成功")


@MasterRouter.put(
    "/{resource}/update/{id}",
    summary="更新WMS主数据",
    response_model=ResponseSchema[WmsMasterOutSchema],
)
async def update_master_controller(
    resource: Annotated[WmsMasterResource, Path(description="主数据资源")],
    id: Annotated[int, Path(description="数据ID", ge=1)],
    data: WmsMasterUpdateSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:master:update"]))],
) -> JSONResponse:
    result = await WmsMasterService(auth, resource).update(id=id, data=data)
    await cache_util.clear(namespace=_MASTER_NS)
    return SuccessResponse(data=result, msg="更新成功")


@MasterRouter.delete(
    "/{resource}/delete",
    summary="删除WMS主数据",
    response_model=ResponseSchema[None],
)
async def delete_master_controller(
    resource: Annotated[WmsMasterResource, Path(description="主数据资源")],
    ids: Annotated[list[int], Body(description="ID列表")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:master:delete"]))],
) -> JSONResponse:
    await WmsMasterService(auth, resource).delete(ids=ids)
    await cache_util.clear(namespace=_MASTER_NS)
    return SuccessResponse(msg="删除成功")


@MasterRouter.patch(
    "/{resource}/status/batch",
    summary="批量修改WMS主数据状态",
    response_model=ResponseSchema[None],
)
async def batch_set_available_master_controller(
    resource: Annotated[WmsMasterResource, Path(description="主数据资源")],
    data: BatchSetAvailable,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:master:update"]))],
) -> JSONResponse:
    await WmsMasterService(auth, resource).set_available(data=data)
    await cache_util.clear(namespace=_MASTER_NS)
    return SuccessResponse(msg="状态修改成功")
