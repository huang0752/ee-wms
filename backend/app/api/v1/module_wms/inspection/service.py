from datetime import datetime
from decimal import Decimal

from sqlalchemy import select

from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException

from ..arrival.model import WmsArrivalLineModel, WmsArrivalOrderModel
from .model import WmsInspectionLineModel, WmsInspectionTaskModel
from .schema import WmsInspectionJudgeSchema, WmsInspectionTaskOutSchema


class WmsInspectionService:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        if auth.db is None:
            raise CustomException(msg="数据库会话不存在")
        self.db = auth.db

    async def judge(self, task_id: int, data: WmsInspectionJudgeSchema) -> WmsInspectionTaskOutSchema:
        task = await self._get_task(task_id)
        if task.status != "pending_inspection":
            raise CustomException(msg="检验任务不是待检状态", status_code=400)
        lines = {line.id: line for line in await self._get_lines(task.id)}
        if set(lines) != {item.line_id for item in data.lines}:
            raise CustomException(msg="检验明细不完整或不存在", status_code=400)

        total_accepted = Decimal("0")
        total_rejected = Decimal("0")
        for item in data.lines:
            line = lines[item.line_id]
            if item.accepted_qty + item.rejected_qty != line.quantity:
                raise CustomException(msg="合格数量与不合格数量之和必须等于检验数量", status_code=400)
            line.accepted_qty = item.accepted_qty
            line.rejected_qty = item.rejected_qty
            line.result = item.result or self._line_result(item.accepted_qty, item.rejected_qty)
            line.status = "pending_inbound"
            line.remark = item.remark
            self._touch(line)
            total_accepted += item.accepted_qty
            total_rejected += item.rejected_qty
            await self._sync_arrival_line(line)

        task.result = data.result or self._task_result(total_accepted, total_rejected)
        task.status = "pending_inbound"
        task.inspector_id = self._user_id()
        task.inspected_time = datetime.now()
        task.attachment_refs = data.attachment_refs
        task.external_quality_id = data.external_quality_id
        task.remark = data.remark
        self._touch(task)
        arrival = await self._get_arrival(task.arrival_order_id)
        arrival.status = "pending_inbound"
        self._touch(arrival)
        await self.db.flush()
        return WmsInspectionTaskOutSchema.model_validate(task)

    async def _sync_arrival_line(self, line: WmsInspectionLineModel) -> None:
        arrival_line = (
            await self.db.execute(
                select(WmsArrivalLineModel)
                .where(
                    WmsArrivalLineModel.id == line.arrival_line_id,
                    WmsArrivalLineModel.tenant_id == self._tenant_id(),
                    WmsArrivalLineModel.is_deleted.is_(False),
                )
                .limit(1)
            )
        ).scalars().first()
        if not arrival_line:
            raise CustomException(msg="到货明细不存在", status_code=404)
        arrival_line.inspected_qty = line.quantity
        arrival_line.accepted_qty = line.accepted_qty
        arrival_line.rejected_qty = line.rejected_qty
        arrival_line.status = "pending_inbound"
        self._touch(arrival_line)

    async def _get_task(self, task_id: int) -> WmsInspectionTaskModel:
        task = (
            await self.db.execute(
                select(WmsInspectionTaskModel)
                .where(
                    WmsInspectionTaskModel.id == task_id,
                    WmsInspectionTaskModel.tenant_id == self._tenant_id(),
                    WmsInspectionTaskModel.is_deleted.is_(False),
                )
                .limit(1)
            )
        ).scalars().first()
        if not task:
            raise CustomException(msg="检验任务不存在", status_code=404)
        return task

    async def _get_lines(self, task_id: int) -> list[WmsInspectionLineModel]:
        return list(
            (
                await self.db.execute(
                    select(WmsInspectionLineModel)
                    .where(
                        WmsInspectionLineModel.task_id == task_id,
                        WmsInspectionLineModel.tenant_id == self._tenant_id(),
                        WmsInspectionLineModel.is_deleted.is_(False),
                    )
                    .order_by(WmsInspectionLineModel.id.asc())
                )
            ).scalars().all()
        )

    async def _get_arrival(self, order_id: int) -> WmsArrivalOrderModel:
        arrival = (
            await self.db.execute(
                select(WmsArrivalOrderModel)
                .where(
                    WmsArrivalOrderModel.id == order_id,
                    WmsArrivalOrderModel.tenant_id == self._tenant_id(),
                    WmsArrivalOrderModel.is_deleted.is_(False),
                )
                .limit(1)
            )
        ).scalars().first()
        if not arrival:
            raise CustomException(msg="到货单不存在", status_code=404)
        return arrival

    def _line_result(self, accepted_qty: Decimal, rejected_qty: Decimal) -> str:
        if accepted_qty > 0 and rejected_qty > 0:
            return "partial"
        if rejected_qty > 0:
            return "fail"
        return "pass"

    def _task_result(self, accepted_qty: Decimal, rejected_qty: Decimal) -> str:
        return self._line_result(accepted_qty, rejected_qty)

    def _tenant_id(self) -> int:
        return self.auth.tenant_id or 1

    def _user_id(self) -> int | None:
        user = self.auth.get_user()
        return getattr(user, "id", None)

    def _touch(self, obj) -> None:
        obj.updated_id = self._user_id()
