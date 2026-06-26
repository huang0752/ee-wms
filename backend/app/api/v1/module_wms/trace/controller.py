from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute

from .schema import WmsTraceResult
from .service import WmsTraceService

TraceRouter = APIRouter(route_class=OperationLogRoute, prefix="/trace", tags=["WMS", "仓储追溯"])


@TraceRouter.get("/batch", summary="按批次追溯", response_model=ResponseSchema[WmsTraceResult])
async def trace_batch_controller(
    batch_no: Annotated[str, Query(description="批次号", min_length=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:trace:query"]))],
    direction: Annotated[str, Query(description="方向")] = "forward",
    material_id: Annotated[int | None, Query(description="物料ID", ge=1)] = None,
) -> JSONResponse:
    result = await WmsTraceService(auth).by_batch(batch_no=batch_no, material_id=material_id, direction=direction)
    return SuccessResponse(data=result, msg="查询成功")
