import { request } from "@utils";

const API_PATH = "/wms/dashboard";

export const WmsDashboardAPI = {
  summary() {
    return request<ApiResponse<WmsDashboardSummary>>({
      url: `${API_PATH}/summary`,
      method: "get",
    });
  },

  tasks() {
    return request<ApiResponse<WmsDashboardTask[]>>({
      url: `${API_PATH}/tasks`,
      method: "get",
    });
  },

  stockStructure() {
    return request<ApiResponse<WmsDashboardStockStructure>>({
      url: `${API_PATH}/stock-structure`,
      method: "get",
    });
  },

  trends() {
    return request<ApiResponse<WmsDashboardTrendItem[]>>({
      url: `${API_PATH}/trends`,
      method: "get",
    });
  },

  warnings() {
    return request<ApiResponse<WmsDashboardWarning[]>>({
      url: `${API_PATH}/warnings`,
      method: "get",
    });
  },

  latestFlows() {
    return request<ApiResponse<WmsDashboardFlow[]>>({
      url: `${API_PATH}/latest-flows`,
      method: "get",
    });
  },
};

export interface WmsDashboardMetric {
  label: string;
  value: number | string;
  unit?: string | null;
  status: "normal" | "pending" | "warning" | string;
}

export interface WmsDashboardTask {
  title: string;
  status: string;
  time: string;
}

export interface WmsDashboardSummary {
  assembly: string;
  phase: string;
  metrics: WmsDashboardMetric[];
  tasks: WmsDashboardTask[];
  next_steps: string[];
}

export interface WmsDashboardStockStructure {
  available_qty: string;
  locked_qty: string;
  frozen_qty: string;
  pending_qty: string;
  defective_qty: string;
}

export interface WmsDashboardTrendItem {
  flow_type: string;
  quantity: string;
}

export interface WmsDashboardWarning extends BaseType {
  warning_no: string;
  warning_type: string;
  material_id: number;
  warehouse_id?: number;
  current_qty: string;
  threshold_qty?: string;
  status: string;
  handled_time?: string;
}

export interface WmsDashboardFlow extends BaseType {
  flow_no: string;
  flow_type: string;
  direction: string;
  material_id: number;
  warehouse_id: number;
  location_id?: number;
  batch_no: string;
  quantity: string;
  document_type?: string;
  document_no?: string;
}

export default WmsDashboardAPI;
