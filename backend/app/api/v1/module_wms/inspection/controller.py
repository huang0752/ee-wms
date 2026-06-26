from typing import Annotated

from fastapi import APIRouter, Depends, Path
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from app.common.enums import QueueEnum
from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_params import PaginationQueryParam
from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute

from .model import WmsInspectionLineModel, WmsInspectionTaskModel
from .schema import WmsInspectionJudgeSchema, WmsInspectionLineOutSchema, WmsInspectionQueryParam, WmsInspectionTaskOutSchema
from .service import WmsInspectionService

InspectionRouter = APIRouter(route_class=OperationLogRoute, prefix="/inspection", tags=["WMS", "检验管理"])


@InspectionRouter.get("/list", summary="WMS检验任务列表", response_model=ResponseSchema[PageResultSchema[WmsInspectionTaskOutSchema]])
async def list_inspection_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[WmsInspectionQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:inspection:query"]))],
) -> JSONResponse:
    conditions = _conditions(WmsInspectionTaskModel, vars(search), auth.tenant_id or 1)
    offset = ((page.page_no or 1) - 1) * (page.page_size or 10)
    limit = page.page_size or 10
    total = (await auth.db.execute(select(func.count()).select_from(WmsInspectionTaskModel).where(*conditions))).scalar_one()
    rows = (await auth.db.execute(select(WmsInspectionTaskModel).where(*conditions).order_by(WmsInspectionTaskModel.id.desc()).offset(offset).limit(limit))).scalars().all()
    return SuccessResponse(
        data=PageResultSchema[WmsInspectionTaskOutSchema](
            page_no=page.page_no or 1,
            page_size=limit,
            total=total,
            has_next=offset + limit < total,
            items=[WmsInspectionTaskOutSchema.model_validate(row) for row in rows],
        ),
        msg="查询成功",
    )


@InspectionRouter.get("/{task_id}/lines", summary="WMS检验明细", response_model=ResponseSchema[list[WmsInspectionLineOutSchema]])
async def list_inspection_lines_controller(
    task_id: Annotated[int, Path(description="检验任务ID", ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:inspection:query"]))],
) -> JSONResponse:
    rows = (
        await auth.db.execute(
            select(WmsInspectionLineModel)
            .where(
                WmsInspectionLineModel.task_id == task_id,
                WmsInspectionLineModel.tenant_id == (auth.tenant_id or 1),
                WmsInspectionLineModel.is_deleted.is_(False),
            )
            .order_by(WmsInspectionLineModel.id.asc())
        )
    ).scalars().all()
    return SuccessResponse(data=[WmsInspectionLineOutSchema.model_validate(row) for row in rows], msg="查询成功")


@InspectionRouter.post("/judge/{task_id}", summary="WMS检验判定", response_model=ResponseSchema[WmsInspectionTaskOutSchema])
async def judge_inspection_controller(
    task_id: Annotated[int, Path(description="检验任务ID", ge=1)],
    data: WmsInspectionJudgeSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:inspection:judge"]))],
) -> JSONResponse:
    result = await WmsInspectionService(auth).judge(task_id, data)
    return SuccessResponse(data=result, msg="检验完成")


def _conditions(model: type, search: dict, tenant_id: int) -> list:
    conditions = [model.tenant_id == tenant_id, model.is_deleted.is_(False)]
    for key, value in search.items():
        if key in {"page_no", "page_size", "order_by"} or value is None:
            continue
        column = getattr(model, key, None)
        if column is None or not isinstance(value, tuple):
            continue
        operator, operand = value
        if operand in (None, ""):
            continue
        if operator == QueueEnum.like.value:
            conditions.append(column.like(f"%{operand}%"))
        elif operator == QueueEnum.eq.value:
            conditions.append(column == operand)
    return conditions
