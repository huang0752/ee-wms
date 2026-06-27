import { request } from "@utils";

const API_PATH = "/wms/transfer";

export const WmsTransferAPI = {
  list(query?: WmsTransferQuery) {
    return request<ApiResponse<PageResult<WmsTransferOrder>>>({ url: `${API_PATH}/list`, method: "get", params: query });
  },
  lines(orderId: number) {
    return request<ApiResponse<WmsTransferLine[]>>({ url: `${API_PATH}/${orderId}/lines`, method: "get" });
  },
  create(body: WmsTransferForm) {
    return request<ApiResponse<WmsTransferOrder>>({ url: `${API_PATH}/create`, method: "post", data: body });
  },
  confirm(orderId: number) {
    return request<ApiResponse<WmsTransferOrder>>({ url: `${API_PATH}/confirm/${orderId}`, method: "post" });
  },
};

export interface WmsTransferQuery extends PageQuery { order_no?: string; status?: string }
export interface WmsTransferLineForm { material_id?: number; from_location_id?: number; to_location_id?: number; batch_no?: string; quantity?: number }
export interface WmsTransferForm extends BaseFormType { order_no?: string; from_warehouse_id?: number; to_warehouse_id?: number; remark?: string; lines: WmsTransferLineForm[] }
export interface WmsTransferOrder extends BaseType { order_no: string; from_warehouse_id: number; to_warehouse_id: number; status: string; confirmed_time?: string; remark?: string; is_demo?: boolean; demo_batch_id?: string }
export interface WmsTransferLine extends BaseType { material_id: number; from_warehouse_id: number; from_location_id?: number; to_warehouse_id: number; to_location_id?: number; batch_no: string; quantity: string; status: string; remark?: string }
export default WmsTransferAPI;
