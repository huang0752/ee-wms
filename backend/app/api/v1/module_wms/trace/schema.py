from pydantic import BaseModel, Field

from ..stock.schema import WmsStockFlowOutSchema


class WmsTraceNode(BaseModel):
    node_type: str = Field(description="节点类型")
    node_no: str | None = Field(default=None, description="节点编号")
    relation_type: str | None = Field(default=None, description="关系类型")


class WmsTraceResult(BaseModel):
    material_id: int | None = Field(default=None, description="物料ID")
    batch_no: str = Field(description="批次号")
    direction: str = Field(description="追溯方向")
    flows: list[WmsStockFlowOutSchema] = Field(default_factory=list, description="库存流水")
    nodes: list[WmsTraceNode] = Field(default_factory=list, description="追溯节点")

