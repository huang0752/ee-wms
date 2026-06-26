from typing import Annotated

from fastapi import APIRouter, Depends, Path
from fastapi.responses import JSONResponse
from sqlalchemy import desc, select

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute
from app.plugin.module_task.business.task.model import BusinessTaskModel

from .generator import WmsDemoGenerator
from .planner import WmsDemoPlanner
from .pool_schema import WmsDemoSampleItemOut, WmsDemoSampleItemUpdate, WmsDemoSamplePoolOut, WmsDemoSamplePoolUpdate
from .pool_service import WmsDemoSamplePoolService
from .quality import WmsDemoQualityService
from .schema import WmsDemoBatchOut, WmsDemoCleanOut, WmsDemoHistoryOut, WmsDemoInitSchema, WmsDemoPreviewOut

DemoRouter = APIRouter(route_class=OperationLogRoute, prefix="/demo", tags=["WMS", "试用数据"])


@DemoRouter.post("/preview", summary="预览WMS试用数据计划", response_model=ResponseSchema[WmsDemoPreviewOut])
async def preview_wms_demo_controller(
    data: WmsDemoInitSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:demo:init"]))],
) -> JSONResponse:
    plan = await WmsDemoPlanner(auth).build(data)
    preview = plan.preview()
    preview.warnings.extend(WmsDemoQualityService.preview_report(plan).get("warnings", []))
    return SuccessResponse(data=preview, msg="预览成功")


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


@DemoRouter.get("/sample-pools", summary="查询WMS试用样本池", response_model=ResponseSchema[list[WmsDemoSamplePoolOut]])
async def list_wms_demo_sample_pools_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:demo:init"]))],
) -> JSONResponse:
    result = await WmsDemoSamplePoolService(auth).list_pools()
    return SuccessResponse(data=result)


@DemoRouter.get("/sample-pools/{pool_id}", summary="获取WMS试用样本池", response_model=ResponseSchema[WmsDemoSamplePoolOut])
async def get_wms_demo_sample_pool_controller(
    pool_id: Annotated[int, Path(ge=1, description="样本池ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:demo:init"]))],
) -> JSONResponse:
    result = await WmsDemoSamplePoolService(auth).get_pool(pool_id)
    return SuccessResponse(data=result)


@DemoRouter.post("/sample-pools/{pool_id}/copy", summary="复制WMS试用样本池", response_model=ResponseSchema[WmsDemoSamplePoolOut])
async def copy_wms_demo_sample_pool_controller(
    pool_id: Annotated[int, Path(ge=1, description="样本池ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:demo:init"]))],
) -> JSONResponse:
    result = await WmsDemoSamplePoolService(auth).copy_pool(pool_id)
    return SuccessResponse(data=result, msg="复制成功")


@DemoRouter.put("/sample-pools/{pool_id}", summary="更新WMS试用样本池", response_model=ResponseSchema[WmsDemoSamplePoolOut])
async def update_wms_demo_sample_pool_controller(
    pool_id: Annotated[int, Path(ge=1, description="样本池ID")],
    data: WmsDemoSamplePoolUpdate,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:demo:init"]))],
) -> JSONResponse:
    result = await WmsDemoSamplePoolService(auth).update_pool(pool_id, data)
    return SuccessResponse(data=result, msg="保存成功")


@DemoRouter.put("/sample-items/{item_id}", summary="更新WMS试用样本项", response_model=ResponseSchema[WmsDemoSampleItemOut])
async def update_wms_demo_sample_item_controller(
    item_id: Annotated[int, Path(ge=1, description="样本项ID")],
    data: WmsDemoSampleItemUpdate,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:demo:init"]))],
) -> JSONResponse:
    result = await WmsDemoSamplePoolService(auth).update_item(item_id, data)
    return SuccessResponse(data=result, msg="保存成功")


@DemoRouter.get("/history", summary="查询WMS试用数据历史", response_model=ResponseSchema[list[WmsDemoHistoryOut]])
async def list_wms_demo_history_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:demo:init"]))],
) -> JSONResponse:
    stmt = (
        select(BusinessTaskModel)
        .where(
            BusinessTaskModel.module == "wms",
            BusinessTaskModel.biz_type == "demo_batch_init",
            BusinessTaskModel.tenant_id == (auth.tenant_id or 1),
            BusinessTaskModel.is_deleted.is_(False),
        )
        .order_by(desc(BusinessTaskModel.created_time))
        .limit(20)
    )
    rows = (await auth.db.execute(stmt)).scalars().all() if auth.db else []
    result = [
        WmsDemoHistoryOut(
            id=row.id,
            demo_batch_id=row.demo_batch_id,
            title=row.title or "",
            status=row.status,
            progress=row.progress,
            payload=row.payload,
            result=row.result,
        )
        for row in rows
    ]
    return SuccessResponse(data=result)
