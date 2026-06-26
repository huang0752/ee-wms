import { request } from "@utils";

const API_PATH = "/wms/dashboard";

export const WmsDashboardAPI = {
  summary() {
    return request<ApiResponse<WmsDashboardSummary>>({
      url: `${API_PATH}/summary`,
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

export default WmsDashboardAPI;
