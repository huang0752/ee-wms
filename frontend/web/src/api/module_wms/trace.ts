import { request } from "@utils";
import type { WmsStockFlow } from "./stock";

const API_PATH = "/wms/trace";

export const WmsTraceAPI = {
  batch(query: WmsTraceBatchQuery) {
    return request<ApiResponse<WmsTraceResult>>({
      url: `${API_PATH}/batch`,
      method: "get",
      params: query,
    });
  },
};

export interface WmsTraceBatchQuery {
  batch_no: string;
  direction?: "forward" | "backward";
  material_id?: number;
}

export interface WmsTraceNode {
  node_type: string;
  node_no?: string;
  relation_type?: string;
}

export interface WmsTraceResult {
  material_id?: number;
  batch_no: string;
  direction: string;
  flows: WmsStockFlow[];
  nodes: WmsTraceNode[];
}

export default WmsTraceAPI;
