import { request } from "@utils";

const API_PATH = "/wms/warning";

export const WmsWarningAPI = {
  list(query?: WmsWarningQuery) {
    return request<ApiResponse<PageResult<WmsWarning>>>({ url: `${API_PATH}/list`, method: "get", params: query });
  },
  scan(body: { warehouse_id?: number }) {
    return request<ApiResponse<WmsWarning[]>>({ url: `${API_PATH}/scan`, method: "post", data: body });
  },
  close(id: number) {
    return request<ApiResponse<WmsWarning>>({ url: `${API_PATH}/close/${id}`, method: "post" });
  },
};

export interface WmsWarningQuery extends PageQuery { warning_type?: string; status?: string }
export interface WmsWarning extends BaseType { warning_no: string; warning_type: string; material_id: number; warehouse_id?: number; current_qty: string; threshold_qty?: string; status: string; handled_time?: string }
export default WmsWarningAPI;
