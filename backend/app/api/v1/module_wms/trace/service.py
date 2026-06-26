from sqlalchemy import select

from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException

from ..stock.model import WmsStockFlowModel, WmsTraceLinkModel
from ..stock.schema import WmsStockFlowOutSchema
from .schema import WmsTraceNode, WmsTraceResult


class WmsTraceService:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        if auth.db is None:
            raise CustomException(msg="数据库会话不存在")
        self.db = auth.db

    async def by_batch(self, batch_no: str, material_id: int | None = None, direction: str = "forward") -> WmsTraceResult:
        flow_conditions = [
            WmsStockFlowModel.tenant_id == self._tenant_id(),
            WmsStockFlowModel.batch_no == batch_no,
            WmsStockFlowModel.is_deleted.is_(False),
        ]
        link_conditions = [
            WmsTraceLinkModel.tenant_id == self._tenant_id(),
            WmsTraceLinkModel.batch_no == batch_no,
            WmsTraceLinkModel.is_deleted.is_(False),
        ]
        if material_id:
            flow_conditions.append(WmsStockFlowModel.material_id == material_id)
            link_conditions.append(WmsTraceLinkModel.material_id == material_id)
        order = WmsStockFlowModel.id.asc() if direction == "forward" else WmsStockFlowModel.id.desc()
        flows = (await self.db.execute(select(WmsStockFlowModel).where(*flow_conditions).order_by(order))).scalars().all()
        links = (await self.db.execute(select(WmsTraceLinkModel).where(*link_conditions).order_by(WmsTraceLinkModel.id.asc()))).scalars().all()
        nodes = [
            WmsTraceNode(node_type=flow.document_type or flow.flow_type, node_no=flow.document_no or flow.flow_no, relation_type=flow.flow_type)
            for flow in flows
        ]
        for link in links:
            if direction == "backward":
                nodes.append(WmsTraceNode(node_type=link.source_type, node_no=link.source_no, relation_type=link.relation_type))
            else:
                nodes.append(WmsTraceNode(node_type=link.target_type, node_no=link.target_no, relation_type=link.relation_type))
        return WmsTraceResult(
            material_id=material_id,
            batch_no=batch_no,
            direction=direction,
            flows=[WmsStockFlowOutSchema.model_validate(flow) for flow in flows],
            nodes=nodes,
        )

    def _tenant_id(self) -> int:
        return self.auth.tenant_id or 1

