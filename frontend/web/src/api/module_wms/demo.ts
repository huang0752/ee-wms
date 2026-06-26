import { request } from "@utils";

const API_PATH = "/wms/demo";

export const WmsDemoAPI = {
  init(body: WmsDemoInitForm) {
    return request<ApiResponse<WmsDemoBatch>>({
      url: `${API_PATH}/init`,
      method: "post",
      data: body,
    });
  },

  clean(demoBatchId: string) {
    return request<ApiResponse<WmsDemoCleanResult>>({
      url: `${API_PATH}/clean/${demoBatchId}`,
      method: "delete",
    });
  },
};

export interface WmsDemoEnterpriseProfile {
  company_name: string;
  industry: string;
  warehouse_count: number;
  material_count: number;
  scenario: string;
}

export interface WmsDemoInitForm {
  profile: WmsDemoEnterpriseProfile;
}

export interface WmsDemoBatch {
  module: string;
  scenario: string;
  demo_batch_id: string;
  task_id: number;
  counts: Record<string, number>;
  summary: string[];
}

export interface WmsDemoCleanResult {
  demo_batch_id: string;
  counts: Record<string, number>;
}

export default WmsDemoAPI;
