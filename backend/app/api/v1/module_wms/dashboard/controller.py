from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute

from ..stock.schema import WmsStockFlowOutSchema
from ..warning.schema import WmsStockWarningOutSchema
from .schema import WmsDashboardStockStructure, WmsDashboardSummary, WmsDashboardTask, WmsDashboardTrendItem
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
    result = await WmsDashboardService(auth).summary()
    return SuccessResponse(data=result, msg="查询成功")


@DashboardRouter.get("/tasks", summary="仓储驾驶舱任务", response_model=ResponseSchema[list[WmsDashboardTask]])
async def dashboard_tasks_controller(auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:dashboard:query"]))]) -> JSONResponse:
    return SuccessResponse(data=await WmsDashboardService(auth).tasks(), msg="查询成功")


@DashboardRouter.get("/stock-structure", summary="库存结构", response_model=ResponseSchema[WmsDashboardStockStructure])
async def dashboard_stock_structure_controller(auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:dashboard:query"]))]) -> JSONResponse:
    return SuccessResponse(data=await WmsDashboardService(auth).stock_structure(), msg="查询成功")


@DashboardRouter.get("/trends", summary="库存流水趋势", response_model=ResponseSchema[list[WmsDashboardTrendItem]])
async def dashboard_trends_controller(auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:dashboard:query"]))]) -> JSONResponse:
    return SuccessResponse(data=await WmsDashboardService(auth).trends(), msg="查询成功")


@DashboardRouter.get("/warnings", summary="最新预警", response_model=ResponseSchema[list[WmsStockWarningOutSchema]])
async def dashboard_warnings_controller(auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:dashboard:query"]))]) -> JSONResponse:
    return SuccessResponse(data=[WmsStockWarningOutSchema.model_validate(row) for row in await WmsDashboardService(auth).warnings()], msg="查询成功")


@DashboardRouter.get("/latest-flows", summary="最新库存流水", response_model=ResponseSchema[list[WmsStockFlowOutSchema]])
async def dashboard_latest_flows_controller(auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:dashboard:query"]))]) -> JSONResponse:
    return SuccessResponse(data=[WmsStockFlowOutSchema.model_validate(row) for row in await WmsDashboardService(auth).latest_flows()], msg="查询成功")
