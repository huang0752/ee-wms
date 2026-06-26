import { request } from "@utils";

const API_PATH = "/wms/check";

export const WmsCheckAPI = {
  list(query?: WmsCheckQuery) {
    return request<ApiResponse<PageResult<WmsCheckOrder>>>({ url: `${API_PATH}/list`, method: "get", params: query });
  },
  lines(orderId: number) {
    return request<ApiResponse<WmsCheckLine[]>>({ url: `${API_PATH}/${orderId}/lines`, method: "get" });
  },
  create(body: WmsCheckForm) {
    return request<ApiResponse<WmsCheckOrder>>({ url: `${API_PATH}/create`, method: "post", data: body });
  },
  audit(orderId: number) {
    return request<ApiResponse<WmsCheckOrder>>({ url: `${API_PATH}/audit/${orderId}`, method: "post" });
  },
};

export interface WmsCheckQuery extends PageQuery { order_no?: string; status?: string }
export interface WmsCheckLineForm { material_id?: number; location_id?: number; batch_no?: string; system_qty?: number; counted_qty?: number }
export interface WmsCheckForm extends BaseFormType { order_no?: string; warehouse_id?: number; lines: WmsCheckLineForm[] }
export interface WmsCheckOrder extends BaseType { order_no: string; warehouse_id: number; status: string; audited_time?: string }
export interface WmsCheckLine extends BaseType { material_id: number; batch_no: string; system_qty: string; counted_qty: string; diff_qty: string; status: string }
export default WmsCheckAPI;

