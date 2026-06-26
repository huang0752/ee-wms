from sqlalchemy import func, select

from app.common.enums import QueueEnum
from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.exceptions import CustomException

from ..arrival.schema import WmsArrivalCreateSchema, WmsArrivalLineCreateSchema
from ..arrival.service import WmsArrivalService
from ..master.model import WmsMaterialModel, WmsWarehouseModel
from ..stock.model import WmsStockBalanceModel, WmsStockFlowModel
from ..trace.service import WmsTraceService
from .model import WmsIntegrationRequestModel
from .schema import (
    WmsDocumentInboundPayload,
    WmsIntegrationAcceptedOut,
    WmsIntegrationInboundSchema,
    WmsIntegrationOutboundOut,
    WmsIntegrationOutboundQuery,
    WmsIntegrationRequestOut,
    WmsIntegrationRequestQueryParam,
    WmsMaterialInboundPayload,
)


class WmsIntegrationService:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        if auth.db is None:
            raise CustomException(msg="数据库会话不存在")
        self.db = auth.db

    async def accept(self, data: WmsIntegrationInboundSchema) -> WmsIntegrationAcceptedOut:
        existing = await self._get_by_key(data.source, data.idempotency_key)
        if existing:
            return WmsIntegrationAcceptedOut(request=WmsIntegrationRequestOut.model_validate(existing), reused=True)

        result = await self._handle_contract(data)
        request = WmsIntegrationRequestModel(
            tenant_id=self._tenant_id(),
            created_id=self._user_id(),
            updated_id=self._user_id(),
            source=data.source,
            contract=data.contract,
            idempotency_key=data.idempotency_key,
            external_no=self._external_no(data.payload),
            status="accepted",
            payload=data.payload.model_dump(mode="json"),
            result=result,
            is_demo=data.is_demo,
            demo_batch_id=data.demo_batch_id,
        )
        self.db.add(request)
        await self.db.flush()
        return WmsIntegrationAcceptedOut(request=WmsIntegrationRequestOut.model_validate(request), reused=False)

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: WmsIntegrationRequestQueryParam | None = None,
    ) -> PageResultSchema[WmsIntegrationRequestOut]:
        conditions = [WmsIntegrationRequestModel.tenant_id == self._tenant_id(), WmsIntegrationRequestModel.is_deleted.is_(False)]
        for key, value in (vars(search) if search else {}).items():
            if key in {"page_no", "page_size", "order_by"} or value is None:
                continue
            column = getattr(WmsIntegrationRequestModel, key, None)
            if column is None:
                continue
            if isinstance(value, tuple):
                operator, operand = value
                if operand in (None, ""):
                    continue
                if operator == QueueEnum.eq.value:
                    conditions.append(column == operand)
            else:
                conditions.append(column == value)
        offset = (page_no - 1) * page_size
        total = (await self.db.execute(select(func.count()).select_from(WmsIntegrationRequestModel).where(*conditions))).scalar_one()
        rows = (
            await self.db.execute(
                select(WmsIntegrationRequestModel)
                .where(*conditions)
                .order_by(WmsIntegrationRequestModel.id.desc())
                .offset(offset)
                .limit(page_size)
            )
        ).scalars().all()
        return PageResultSchema[WmsIntegrationRequestOut](
            page_no=page_no,
            page_size=page_size,
            total=total,
            has_next=offset + page_size < total,
            items=[WmsIntegrationRequestOut.model_validate(row) for row in rows],
        )

    async def outbound(self, query: WmsIntegrationOutboundQuery) -> WmsIntegrationOutboundOut:
        if query.contract == "available_stock":
            return WmsIntegrationOutboundOut(contract=query.contract, items=await self._available_stock(query.material_code))
        if query.contract == "shortage_result":
            return WmsIntegrationOutboundOut(contract=query.contract, items=await self._shortage_result(query.material_code))
        if query.contract == "issue_result":
            return WmsIntegrationOutboundOut(contract=query.contract, items=await self._flows_by_document("issue", query.document_no))
        if query.contract == "inbound_result":
            return WmsIntegrationOutboundOut(contract=query.contract, items=await self._flows_by_document("inbound", query.document_no))
        if query.contract == "trace_result":
            if not query.batch_no:
                raise CustomException(msg="追溯查询必须提供批次号", status_code=400)
            result = await WmsTraceService(self.auth).by_batch(query.batch_no, direction="forward")
            return WmsIntegrationOutboundOut(contract=query.contract, items=[result.model_dump(mode="json")])
        raise CustomException(msg="不支持的出站契约", status_code=400)

    async def _handle_contract(self, data: WmsIntegrationInboundSchema) -> dict:
        if data.contract == "material":
            payload = self._material_payload(data.payload)
            return {"material_code": payload.material_code, "accepted": True}
        if data.contract == "purchase_arrival":
            payload = self._document_payload(data.payload)
            warehouse = await self._warehouse_by_code(payload.warehouse_code)
            lines = []
            for line in payload.lines:
                material = await self._material_by_code(line.material_code)
                lines.append(
                    WmsArrivalLineCreateSchema(
                        material_id=material.id,
                        planned_qty=line.quantity,
                        batch_no=line.batch_no or f"{payload.external_no}-{material.code}",
                        remark=line.remark,
                    )
                )
            arrival = await WmsArrivalService(self.auth).create(
                WmsArrivalCreateSchema(
                    order_no=payload.external_no,
                    warehouse_id=warehouse.id,
                    external_source=data.source,
                    external_id=data.idempotency_key,
                    external_no=payload.external_no,
                    sync_status="pending",
                    lines=lines,
                )
            )
            return {"arrival_order_id": arrival.id, "order_no": arrival.order_no}
        if data.contract in {"sales_order", "mes_work_order", "bom_demand", "completion_inbound"}:
            payload = self._document_payload(data.payload)
            return {"external_no": payload.external_no, "accepted": True, "deferred": True}
        raise CustomException(msg="不支持的入站契约", status_code=400)

    async def _available_stock(self, material_code: str | None) -> list[dict]:
        stmt = (
            select(WmsStockBalanceModel, WmsMaterialModel.code)
            .join(WmsMaterialModel, WmsMaterialModel.id == WmsStockBalanceModel.material_id)
            .where(
                WmsStockBalanceModel.tenant_id == self._tenant_id(),
                WmsStockBalanceModel.is_deleted.is_(False),
                WmsStockBalanceModel.available_qty > 0,
            )
            .order_by(WmsStockBalanceModel.id.asc())
        )
        if material_code:
            stmt = stmt.where(WmsMaterialModel.code == material_code)
        rows = (await self.db.execute(stmt)).all()
        return [
            {
                "material_code": code,
                "warehouse_id": balance.warehouse_id,
                "location_id": balance.location_id,
                "batch_no": balance.batch_no,
                "available_qty": str(balance.available_qty),
            }
            for balance, code in rows
        ]

    async def _shortage_result(self, material_code: str | None) -> list[dict]:
        stmt = (
            select(WmsMaterialModel.code, WmsMaterialModel.safety_stock, func.coalesce(func.sum(WmsStockBalanceModel.available_qty), 0))
            .outerjoin(WmsStockBalanceModel, WmsStockBalanceModel.material_id == WmsMaterialModel.id)
            .where(WmsMaterialModel.tenant_id == self._tenant_id(), WmsMaterialModel.is_deleted.is_(False))
            .group_by(WmsMaterialModel.id)
        )
        if material_code:
            stmt = stmt.where(WmsMaterialModel.code == material_code)
        rows = (await self.db.execute(stmt)).all()
        result = []
        for code, safety_stock, available_qty in rows:
            safety = safety_stock or 0
            if available_qty < safety:
                result.append({"material_code": code, "available_qty": str(available_qty), "safety_stock": str(safety), "shortage_qty": str(safety - available_qty)})
        return result

    async def _flows_by_document(self, document_type: str, document_no: str | None) -> list[dict]:
        stmt = select(WmsStockFlowModel).where(
            WmsStockFlowModel.tenant_id == self._tenant_id(),
            WmsStockFlowModel.document_type == document_type,
            WmsStockFlowModel.is_deleted.is_(False),
        )
        if document_no:
            stmt = stmt.where(WmsStockFlowModel.document_no == document_no)
        rows = (await self.db.execute(stmt.order_by(WmsStockFlowModel.id.asc()))).scalars().all()
        return [
            {
                "flow_no": row.flow_no,
                "flow_type": row.flow_type,
                "material_id": row.material_id,
                "batch_no": row.batch_no,
                "quantity": str(row.quantity),
                "document_no": row.document_no,
            }
            for row in rows
        ]

    async def _get_by_key(self, source: str, idempotency_key: str) -> WmsIntegrationRequestModel | None:
        return (
            await self.db.execute(
                select(WmsIntegrationRequestModel)
                .where(
                    WmsIntegrationRequestModel.tenant_id == self._tenant_id(),
                    WmsIntegrationRequestModel.source == source,
                    WmsIntegrationRequestModel.idempotency_key == idempotency_key,
                    WmsIntegrationRequestModel.is_deleted.is_(False),
                )
                .limit(1)
            )
        ).scalars().first()

    async def _warehouse_by_code(self, code: str | None) -> WmsWarehouseModel:
        if not code:
            raise CustomException(msg="仓库编码不能为空", status_code=400)
        row = (
            await self.db.execute(
                select(WmsWarehouseModel)
                .where(WmsWarehouseModel.tenant_id == self._tenant_id(), WmsWarehouseModel.code == code, WmsWarehouseModel.is_deleted.is_(False))
                .limit(1)
            )
        ).scalars().first()
        if not row:
            raise CustomException(msg=f"仓库不存在: {code}", status_code=400)
        return row

    async def _material_by_code(self, code: str) -> WmsMaterialModel:
        row = (
            await self.db.execute(
                select(WmsMaterialModel)
                .where(WmsMaterialModel.tenant_id == self._tenant_id(), WmsMaterialModel.code == code, WmsMaterialModel.is_deleted.is_(False))
                .limit(1)
            )
        ).scalars().first()
        if not row:
            raise CustomException(msg=f"物料不存在: {code}", status_code=400)
        return row

    def _material_payload(self, payload) -> WmsMaterialInboundPayload:
        if not isinstance(payload, WmsMaterialInboundPayload):
            raise CustomException(msg="物料契约载荷不匹配", status_code=400)
        return payload

    def _document_payload(self, payload) -> WmsDocumentInboundPayload:
        if not isinstance(payload, WmsDocumentInboundPayload):
            raise CustomException(msg="单据契约载荷不匹配", status_code=400)
        return payload

    def _external_no(self, payload) -> str | None:
        return getattr(payload, "external_no", None)

    def _tenant_id(self) -> int:
        return self.auth.tenant_id or 1

    def _user_id(self) -> int | None:
        user = self.auth.get_user()
        return getattr(user, "id", None)
