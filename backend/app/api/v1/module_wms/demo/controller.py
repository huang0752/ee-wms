from typing import Annotated

from fastapi import APIRouter, Depends, Path
from fastapi.responses import JSONResponse

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute

from .generator import WmsDemoGenerator
from .schema import WmsDemoBatchOut, WmsDemoCleanOut, WmsDemoInitSchema

DemoRouter = APIRouter(route_class=OperationLogRoute, prefix="/demo", tags=["WMS", "试用数据"])


@DemoRouter.post("/init", summary="初始化WMS试用数据", response_model=ResponseSchema[WmsDemoBatchOut])
async def init_wms_demo_controller(
    data: WmsDemoInitSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:demo:init"]))],
) -> JSONResponse:
    result = await WmsDemoGenerator(auth).generate(data)
    return SuccessResponse(data=result, msg="初始化成功")


@DemoRouter.delete("/clean/{demo_batch_id}", summary="清理WMS试用数据", response_model=ResponseSchema[WmsDemoCleanOut])
async def clean_wms_demo_controller(
    demo_batch_id: Annotated[str, Path(min_length=1, max_length=64, description="试用数据批次")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:demo:clean"]))],
) -> JSONResponse:
    result = await WmsDemoGenerator(auth).clean(demo_batch_id)
    return SuccessResponse(data=result, msg="清理成功")
