import { request } from "@utils";

const API_PATH = "/wms/inbound";

export const WmsInboundAPI = {
  list(query?: WmsInboundQuery) {
    return request<ApiResponse<PageResult<WmsInboundOrder>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },
  lines(orderId: number) {
    return request<ApiResponse<WmsInboundLine[]>>({
      url: `${API_PATH}/${orderId}/lines`,
      method: "get",
    });
  },
  createFromInspection(taskId: number, body: WmsInboundCreateFromInspectionForm) {
    return request<ApiResponse<WmsInboundOrder>>({
      url: `${API_PATH}/create-from-inspection/${taskId}`,
      method: "post",
      data: body,
    });
  },
  confirm(orderId: number) {
    return request<ApiResponse<WmsInboundOrder>>({
      url: `${API_PATH}/confirm/${orderId}`,
      method: "post",
    });
  },
  recommendLocation(query: { material_id: number; warehouse_id: number }) {
    return request<ApiResponse<WmsLocationRecommend[]>>({
      url: `${API_PATH}/recommend-location`,
      method: "get",
      params: query,
    });
  },
};

export interface WmsInboundQuery extends PageQuery, UserByQueryParams, TenantByQueryParams {
  order_no?: string;
  status?: string;
}

export interface WmsInboundCreateFromInspectionForm extends BaseFormType {
  location_id?: number;
  remark?: string;
}

export interface WmsInboundOrder extends BaseType {
  order_no: string;
  inspection_task_id?: number;
  arrival_order_id?: number;
  warehouse_id: number;
  location_id?: number;
  status: string;
  confirmed_time?: string;
  external_source: string;
  external_no?: string;
  remark?: string;
}

export interface WmsInboundLine extends BaseType {
  order_id: number;
  inspection_line_id?: number;
  material_id: number;
  warehouse_id: number;
  location_id?: number;
  batch_no: string;
  quantity: string;
  stock_status: string;
  status: string;
}

export interface WmsLocationRecommend {
  id: number;
  code: string;
  name: string;
  capacity?: string;
  mix_rule?: string;
}

export default WmsInboundAPI;
