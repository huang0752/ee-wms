import { request } from "@utils";

const API_PATH = "/wms/arrival";

export const WmsArrivalAPI = {
  list(query?: WmsArrivalQuery) {
    return request<ApiResponse<PageResult<WmsArrivalOrder>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },
  lines(orderId: number) {
    return request<ApiResponse<WmsArrivalLine[]>>({
      url: `${API_PATH}/${orderId}/lines`,
      method: "get",
    });
  },
  create(body: WmsArrivalForm) {
    return request<ApiResponse<WmsArrivalOrder>>({
      url: `${API_PATH}/create`,
      method: "post",
      data: body,
    });
  },
  receive(orderId: number) {
    return request<ApiResponse<WmsInspectionTask>>({
      url: `${API_PATH}/receive/${orderId}`,
      method: "post",
    });
  },
};

export interface WmsArrivalQuery extends PageQuery, UserByQueryParams, TenantByQueryParams {
  order_no?: string;
  status?: string;
}

export interface WmsArrivalLineForm {
  material_id?: number;
  planned_qty?: number;
  batch_no?: string;
  remark?: string;
}

export interface WmsArrivalForm extends BaseFormType {
  order_no?: string;
  supplier_id?: number;
  warehouse_id?: number;
  external_source?: string;
  external_no?: string;
  remark?: string;
  lines: WmsArrivalLineForm[];
}

export interface WmsArrivalOrder extends BaseType {
  order_no: string;
  supplier_id?: number;
  warehouse_id: number;
  status: string;
  received_time?: string;
  external_source: string;
  external_no?: string;
  remark?: string;
}

export interface WmsArrivalLine extends BaseType {
  order_id: number;
  material_id: number;
  planned_qty: string;
  received_qty: string;
  inspected_qty: string;
  accepted_qty: string;
  rejected_qty: string;
  batch_no: string;
  status: string;
}

export interface WmsInspectionTask extends BaseType {
  task_no: string;
  arrival_order_id: number;
  arrival_no: string;
  status: string;
  result?: string;
}

export default WmsArrivalAPI;
