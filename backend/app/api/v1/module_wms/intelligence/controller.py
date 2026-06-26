from typing import Annotated

from fastapi import APIRouter, Depends, Path
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission
from app.core.exceptions import CustomException
from app.core.router_class import OperationLogRoute

from ..stock.recommend_service import WmsStockRecommendService
from ..stock.schema import WmsStockLockSchema
from ..warning.model import WmsStockWarningModel
from .ai_service import WmsIntelligenceAIService
from .rule_service import WmsIntelligenceRuleService
from .schema import WmsIntelligenceSource, WmsIntelligenceSummaryOut, WmsOutboundExplainOut, WmsOutboundExplainRequest, WmsWarningAdviceOut

IntelligenceRouter = APIRouter(route_class=OperationLogRoute, prefix="/intelligence", tags=["WMS", "智能分析"])


@IntelligenceRouter.get(
    "/dashboard-summary",
    summary="WMS驾驶舱智能摘要",
    response_model=ResponseSchema[WmsIntelligenceSummaryOut],
)
async def dashboard_intelligence_summary_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:dashboard:query"]))],
) -> JSONResponse:
    result = await WmsIntelligenceAIService(auth).dashboard_summary()
    return SuccessResponse(data=result, msg="生成成功")


@IntelligenceRouter.get(
    "/warning/{warning_id}/advice",
    summary="WMS库存预警智能建议",
    response_model=ResponseSchema[WmsWarningAdviceOut],
)
async def warning_advice_controller(
    warning_id: Annotated[int, Path(ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:warning:query"]))],
) -> JSONResponse:
    warning = await _get_warning(auth, warning_id)
    result = await WmsIntelligenceAIService(auth).warning_advice(warning)
    return SuccessResponse(data=result, msg="生成成功")


@IntelligenceRouter.post(
    "/stock/outbound-explain",
    summary="WMS出库库存推荐解释",
    response_model=ResponseSchema[WmsOutboundExplainOut],
)
async def outbound_explain_controller(
    data: WmsOutboundExplainRequest,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:stock:query"]))],
) -> JSONResponse:
    service = WmsIntelligenceRuleService(auth)
    candidates = await WmsStockRecommendService(auth).recommend_outbound(
        WmsStockLockSchema(
            material_id=data.material_id,
            warehouse_id=data.warehouse_id,
            location_id=data.location_id,
            quantity=data.required_qty or "1",
        )
    )
    scored = service.score_outbound_candidates(candidates, warehouse_id=data.warehouse_id, location_id=data.location_id)
    return SuccessResponse(
        data=WmsOutboundExplainOut(
            material_id=data.material_id,
            source=WmsIntelligenceSource.rule_fallback,
            summary=service.outbound_summary(scored),
            candidates=scored,
        ),
        msg="生成成功",
    )


async def _get_warning(auth: AuthSchema, warning_id: int) -> WmsStockWarningModel:
    stmt = select(WmsStockWarningModel).where(
        WmsStockWarningModel.id == warning_id,
        WmsStockWarningModel.tenant_id == (auth.tenant_id or 1),
        WmsStockWarningModel.is_deleted.is_(False),
    )
    warning = (await auth.db.execute(stmt)).scalar_one_or_none()
    if warning is None:
        raise CustomException(msg="预警不存在", status_code=404)
    return warning
