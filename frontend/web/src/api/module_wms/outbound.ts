import { request } from "@utils";

const API_PATH = "/wms/outbound";

export const WmsOutboundAPI = {
  list(query?: WmsOutboundQuery) {
    return request<ApiResponse<PageResult<WmsOutboundOrder>>>({ url: `${API_PATH}/list`, method: "get", params: query });
  },
  lines(orderId: number) {
    return request<ApiResponse<WmsOutboundLine[]>>({ url: `${API_PATH}/${orderId}/lines`, method: "get" });
  },
  create(body: WmsOutboundForm) {
    return request<ApiResponse<WmsOutboundOrder>>({ url: `${API_PATH}/create`, method: "post", data: body });
  },
  reserve(orderId: number) {
    return request<ApiResponse<WmsOutboundOrder>>({ url: `${API_PATH}/reserve/${orderId}`, method: "post" });
  },
  pick(orderId: number) {
    return request<ApiResponse<WmsOutboundOrder>>({ url: `${API_PATH}/pick/${orderId}`, method: "post" });
  },
  review(orderId: number) {
    return request<ApiResponse<WmsOutboundOrder>>({ url: `${API_PATH}/review/${orderId}`, method: "post" });
  },
  confirm(orderId: number) {
    return request<ApiResponse<WmsOutboundOrder>>({ url: `${API_PATH}/confirm/${orderId}`, method: "post" });
  },
  cancel(orderId: number) {
    return request<ApiResponse<WmsOutboundOrder>>({ url: `${API_PATH}/cancel/${orderId}`, method: "post" });
  },
};

export interface WmsOutboundQuery extends PageQuery, UserByQueryParams, TenantByQueryParams {
  order_no?: string;
  status?: string;
}

export interface WmsOutboundLineForm {
  material_id?: number;
  requested_qty?: number;
  remark?: string;
}

export interface WmsOutboundForm extends BaseFormType {
  order_no?: string;
  customer_id?: number;
  warehouse_id?: number;
  external_source?: string;
  external_id?: string;
  external_no?: string;
  sync_status?: string;
  workflow_instance_id?: string;
  remark?: string;
  lines: WmsOutboundLineForm[];
}

export interface WmsOutboundOrder extends BaseType {
  order_no: string;
  customer_id?: number;
  warehouse_id: number;
  status: string;
  picked_time?: string;
  reviewed_time?: string;
  confirmed_time?: string;
  external_source: string;
  external_id?: string;
  external_no?: string;
  sync_status: string;
  workflow_instance_id?: string;
  remark?: string;
  is_demo?: boolean;
  demo_batch_id?: string;
}

export interface WmsOutboundLine extends BaseType {
  order_id: number;
  material_id: number;
  warehouse_id: number;
  location_id?: number;
  batch_no?: string;
  requested_qty: string;
  locked_qty: string;
  shipped_qty: string;
  stock_lock_id?: number;
  status: string;
  remark?: string;
  is_demo?: boolean;
  demo_batch_id?: string;
}

export default WmsOutboundAPI;
