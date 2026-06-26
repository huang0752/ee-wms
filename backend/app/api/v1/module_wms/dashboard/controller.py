from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute

from .schema import WmsDashboardSummary
from .service import WmsDashboardService

DashboardRouter = APIRouter(
    route_class=OperationLogRoute,
    prefix="/dashboard",
    tags=["WMS", "仓储驾驶舱"],
)


@DashboardRouter.get(
    "/summary",
    summary="仓储驾驶舱摘要",
    response_model=ResponseSchema[WmsDashboardSummary],
)
async def dashboard_summary_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:dashboard:query"]))],
) -> JSONResponse:
    result = await WmsDashboardService.summary()
    return SuccessResponse(data=result, msg="查询成功")
