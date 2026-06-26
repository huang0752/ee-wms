from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_params import PaginationQueryParam
from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute

from .schema import (
    WmsIntegrationAcceptedOut,
    WmsIntegrationInboundSchema,
    WmsIntegrationOutboundOut,
    WmsIntegrationOutboundQuery,
    WmsIntegrationRequestOut,
    WmsIntegrationRequestQueryParam,
)
from .service import WmsIntegrationService

IntegrationRouter = APIRouter(route_class=OperationLogRoute, prefix="/integration", tags=["WMS", "外部集成"])


@IntegrationRouter.post("/inbound", summary="接收外部入站契约", response_model=ResponseSchema[WmsIntegrationAcceptedOut])
async def integration_inbound_controller(
    data: WmsIntegrationInboundSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:integration:inbound"]))],
) -> JSONResponse:
    result = await WmsIntegrationService(auth).accept(data)
    return SuccessResponse(data=result, msg="接收成功")


@IntegrationRouter.post("/outbound", summary="查询外部出站契约", response_model=ResponseSchema[WmsIntegrationOutboundOut])
async def integration_outbound_controller(
    data: WmsIntegrationOutboundQuery,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:integration:outbound"]))],
) -> JSONResponse:
    result = await WmsIntegrationService(auth).outbound(data)
    return SuccessResponse(data=result, msg="查询成功")


@IntegrationRouter.get(
    "/request/list",
    summary="集成请求记录",
    response_model=ResponseSchema[PageResultSchema[WmsIntegrationRequestOut]],
)
async def integration_request_list_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[WmsIntegrationRequestQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:integration:query"]))],
) -> JSONResponse:
    result = await WmsIntegrationService(auth).page(page_no=page.page_no or 1, page_size=page.page_size or 10, search=search)
    return SuccessResponse(data=result, msg="查询成功")
