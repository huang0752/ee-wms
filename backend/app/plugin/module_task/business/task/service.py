from uuid import uuid4

from fastapi import status

from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException

from .crud import BusinessTaskCRUD
from .schema import (
    BusinessTaskCreateSchema,
    BusinessTaskOutSchema,
    BusinessTaskQueryParam,
    BusinessTaskUpdateSchema,
    DemoBatchCleanOutSchema,
    DemoBatchOutSchema,
    DemoBatchTriggerSchema,
)


class BusinessTaskService:
    """通用业务长任务服务。"""

    _TERMINAL_STATUSES = {"success", "failed", "canceled"}

    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        self.crud = BusinessTaskCRUD(auth)

    async def create(self, data: BusinessTaskCreateSchema) -> BusinessTaskOutSchema:
        obj = await self.crud.create(data=data)
        return BusinessTaskOutSchema.model_validate(obj)

    async def detail(self, id: int) -> BusinessTaskOutSchema:
        return await self.crud.get_or_404(id=id, out_schema=BusinessTaskOutSchema)

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: BusinessTaskQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> dict:
        return await self.crud.page(
            offset=(page_no - 1) * page_size,
            limit=page_size,
            order_by=order_by or [{"created_time": "desc"}],
            search=vars(search) if search else None,
            out_schema=BusinessTaskOutSchema,
        )

    async def update_status(self, id: int, data: BusinessTaskUpdateSchema) -> BusinessTaskOutSchema:
        current = await self.crud.get_or_404(id=id)
        next_status = data.status or current.status
        if current.status in self._TERMINAL_STATUSES and next_status != current.status:
            raise CustomException(msg="终态任务不允许回退", status_code=status.HTTP_400_BAD_REQUEST)
        if data.progress is not None and current.progress > data.progress and current.status in self._TERMINAL_STATUSES:
            raise CustomException(msg="终态任务不允许回退进度", status_code=status.HTTP_400_BAD_REQUEST)
        update_obj = await self.crud.update(id=id, data=data)
        return BusinessTaskOutSchema.model_validate(update_obj)


class DemoBatchRegistry:
    """试用数据初始化处理器注册表。"""

    _handlers: dict[str, object] = {}

    @classmethod
    def register(cls, module: str, handler: object) -> None:
        cls._handlers[module] = handler

    @classmethod
    def get(cls, module: str) -> object | None:
        return cls._handlers.get(module)


class DemoBatchService:
    """试用数据初始化任务框架。"""

    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth

    async def trigger(self, data: DemoBatchTriggerSchema) -> DemoBatchOutSchema:
        demo_batch_id = f"demo_{data.module}_{uuid4().hex[:12]}"
        task = await BusinessTaskService(self.auth).create(
            BusinessTaskCreateSchema(
                module=data.module,
                biz_type="demo_batch_init",
                biz_id=demo_batch_id,
                title=f"{data.module} 试用数据初始化",
                payload={"scenario": data.scenario, **(data.payload or {})},
                is_demo=True,
                demo_batch_id=demo_batch_id,
            )
        )
        return DemoBatchOutSchema(
            module=data.module,
            scenario=data.scenario,
            demo_batch_id=demo_batch_id,
            task_id=task.id or 0,
        )

    async def clean(self, demo_batch_id: str) -> DemoBatchCleanOutSchema:
        module = demo_batch_id.split("_", 2)[1] if demo_batch_id.startswith("demo_") and "_" in demo_batch_id else "demo"
        task = await BusinessTaskService(self.auth).create(
            BusinessTaskCreateSchema(
                module=module,
                biz_type="demo_batch_clean",
                biz_id=demo_batch_id,
                title="试用数据清理",
                is_demo=True,
                demo_batch_id=demo_batch_id,
            )
        )
        return DemoBatchCleanOutSchema(demo_batch_id=demo_batch_id, task_id=task.id or 0)
