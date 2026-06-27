from datetime import datetime

from sqlalchemy import func, select

from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException

from ..inspection.model import WmsInspectionLineModel, WmsInspectionTaskModel
from ..inspection.schema import WmsInspectionTaskOutSchema
from ..tenant_guard import ensure_wms_material, ensure_wms_supplier, ensure_wms_warehouse, require_wms_tenant_id
from .model import WmsArrivalLineModel, WmsArrivalOrderModel
from .schema import WmsArrivalCreateSchema, WmsArrivalOrderOutSchema


class WmsArrivalService:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        if auth.db is None:
            raise CustomException(msg="数据库会话不存在")
        self.db = auth.db

    async def create(self, data: WmsArrivalCreateSchema) -> WmsArrivalOrderOutSchema:
        tenant_id = self._tenant_id()
        await ensure_wms_supplier(self.db, tenant_id, data.supplier_id)
        await ensure_wms_warehouse(self.db, tenant_id, data.warehouse_id)
        for line_data in data.lines:
            await ensure_wms_material(self.db, tenant_id, line_data.material_id)
        order_no = data.order_no or await self._next_no("ARR")
        exists = (
            await self.db.execute(
                select(WmsArrivalOrderModel)
                .where(
                    WmsArrivalOrderModel.tenant_id == self._tenant_id(),
                    WmsArrivalOrderModel.order_no == order_no,
                    WmsArrivalOrderModel.is_deleted.is_(False),
                )
                .limit(1)
            )
        ).scalars().first()
        if exists:
            raise CustomException(msg="到货单号已存在", status_code=400)

        order = WmsArrivalOrderModel(
            tenant_id=self._tenant_id(),
            order_no=order_no,
            supplier_id=data.supplier_id,
            warehouse_id=data.warehouse_id,
            expected_time=data.expected_time,
            external_source=data.external_source,
            external_id=data.external_id,
            external_no=data.external_no,
            sync_status=data.sync_status,
            workflow_instance_id=data.workflow_instance_id,
            remark=data.remark,
            created_id=self._user_id(),
            updated_id=self._user_id(),
        )
        self.db.add(order)
        await self.db.flush()
        for line_data in data.lines:
            self.db.add(
                WmsArrivalLineModel(
                    tenant_id=self._tenant_id(),
                    order_id=order.id,
                    material_id=line_data.material_id,
                    planned_qty=line_data.planned_qty,
                    batch_no=line_data.batch_no,
                    remark=line_data.remark,
                    created_id=self._user_id(),
                    updated_id=self._user_id(),
                )
            )
        await self.db.flush()
        return WmsArrivalOrderOutSchema.model_validate(order)

    async def receive(self, order_id: int) -> WmsInspectionTaskOutSchema:
        order = await self._get_order(order_id)
        if order.status != "pending_receive":
            raise CustomException(msg="到货单不是待收货状态", status_code=400)
        lines = await self._get_lines(order.id)
        if not lines:
            raise CustomException(msg="到货单缺少明细", status_code=400)

        order.status = "pending_inspection"
        order.received_time = datetime.now()
        self._touch(order)
        task = WmsInspectionTaskModel(
            tenant_id=self._tenant_id(),
            task_no=await self._next_no("IQC", WmsInspectionTaskModel),
            arrival_order_id=order.id,
            arrival_no=order.order_no,
            status="pending_inspection",
            created_id=self._user_id(),
            updated_id=self._user_id(),
        )
        self.db.add(task)
        await self.db.flush()
        for line in lines:
            line.status = "pending_inspection"
            line.received_qty = line.planned_qty
            self._touch(line)
            self.db.add(
                WmsInspectionLineModel(
                    tenant_id=self._tenant_id(),
                    task_id=task.id,
                    arrival_line_id=line.id,
                    material_id=line.material_id,
                    batch_no=line.batch_no,
                    quantity=line.received_qty,
                    status="pending_inspection",
                    created_id=self._user_id(),
                    updated_id=self._user_id(),
                )
            )
        await self.db.flush()
        return WmsInspectionTaskOutSchema.model_validate(task)

    async def _get_order(self, order_id: int) -> WmsArrivalOrderModel:
        order = (
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
        if not order:
            raise CustomException(msg="到货单不存在", status_code=404)
        return order

    async def _get_lines(self, order_id: int) -> list[WmsArrivalLineModel]:
        return list(
            (
                await self.db.execute(
                    select(WmsArrivalLineModel)
                    .where(
                        WmsArrivalLineModel.order_id == order_id,
                        WmsArrivalLineModel.tenant_id == self._tenant_id(),
                        WmsArrivalLineModel.is_deleted.is_(False),
                    )
                    .order_by(WmsArrivalLineModel.id.asc())
                )
            ).scalars().all()
        )

    async def _next_no(self, prefix: str, model: type = WmsArrivalOrderModel) -> str:
        count = (await self.db.execute(select(func.count()).select_from(model))).scalar_one() or 0
        return f"{prefix}{count + 1:08d}"

    def _tenant_id(self) -> int:
        return require_wms_tenant_id(self.auth)

    def _user_id(self) -> int | None:
        user = self.auth.get_user()
        return getattr(user, "id", None)

    def _touch(self, obj) -> None:
        obj.updated_id = self._user_id()
