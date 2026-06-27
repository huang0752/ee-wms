import { request } from "@utils";

const API_PATH = "/wms/inspection";

export const WmsInspectionAPI = {
  list(query?: WmsInspectionQuery) {
    return request<ApiResponse<PageResult<WmsInspectionTask>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },
  lines(taskId: number) {
    return request<ApiResponse<WmsInspectionLine[]>>({
      url: `${API_PATH}/${taskId}/lines`,
      method: "get",
    });
  },
  judge(taskId: number, body: WmsInspectionJudgeForm) {
    return request<ApiResponse<WmsInspectionTask>>({
      url: `${API_PATH}/judge/${taskId}`,
      method: "post",
      data: body,
    });
  },
};

export interface WmsInspectionQuery extends PageQuery, UserByQueryParams, TenantByQueryParams {
  task_no?: string;
  status?: string;
  arrival_no?: string;
}

export interface WmsInspectionTask extends BaseType {
  task_no: string;
  arrival_order_id: number;
  arrival_no: string;
  status: string;
  result?: string;
  inspector_id?: number;
  inspected_time?: string;
  attachment_refs?: string;
  external_quality_id?: string;
  remark?: string;
  is_demo?: boolean;
  demo_batch_id?: string;
}

export interface WmsInspectionLine extends BaseType {
  task_id: number;
  arrival_line_id: number;
  material_id: number;
  batch_no: string;
  quantity: string;
  accepted_qty: string;
  rejected_qty: string;
  result?: string;
  status: string;
  remark?: string;
  is_demo?: boolean;
  demo_batch_id?: string;
}

export interface WmsInspectionJudgeLineForm {
  line_id: number;
  accepted_qty: number;
  rejected_qty: number;
  result?: string;
  remark?: string;
}

export interface WmsInspectionJudgeForm extends BaseFormType {
  result?: string;
  attachment_refs?: string;
  external_quality_id?: string;
  remark?: string;
  lines: WmsInspectionJudgeLineForm[];
}

export default WmsInspectionAPI;
