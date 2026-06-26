import { request } from "@utils";

const API_PATH = "/wms/master";

export type WmsMasterResource =
  | "warehouse"
  | "zone"
  | "location"
  | "material"
  | "supplier"
  | "customer"
  | "barcode-rule";

export const WmsMasterAPI = {
  list(resource: WmsMasterResource, query?: WmsMasterPageQuery) {
    return request<ApiResponse<PageResult<WmsMasterTable>>>({
      url: `${API_PATH}/${resource}/list`,
      method: "get",
      params: query,
    });
  },

  create(resource: WmsMasterResource, body: WmsMasterForm) {
    return request<ApiResponse<WmsMasterTable>>({
      url: `${API_PATH}/${resource}/create`,
      method: "post",
      data: body,
    });
  },

  update(resource: WmsMasterResource, id: number, body: WmsMasterForm) {
    return request<ApiResponse<WmsMasterTable>>({
      url: `${API_PATH}/${resource}/update/${id}`,
      method: "put",
      data: body,
    });
  },

  delete(resource: WmsMasterResource, ids: number[]) {
    return request<ApiResponse>({
      url: `${API_PATH}/${resource}/delete`,
      method: "delete",
      data: ids,
    });
  },
};

export interface WmsMasterPageQuery extends PageQuery, UserByQueryParams, TenantByQueryParams {
  code?: string;
  name?: string;
  status?: number;
  warehouse_id?: number;
  zone_id?: number;
  category?: string;
  is_demo?: boolean;
}

export interface WmsMasterTable extends BaseType {
  code: string;
  name: string;
  status: number;
  description?: string;
  warehouse_id?: number;
  zone_id?: number;
  type?: string;
  manager?: string;
  usage?: string;
  spec?: string;
  unit?: string;
  category?: string;
  batch_flag?: boolean;
  sn_flag?: boolean;
  contact?: string;
  phone?: string;
  address?: string;
  object_type?: string;
  prefix?: string;
}

export interface WmsMasterForm extends BaseFormType {
  code?: string;
  name?: string;
  status?: number;
  description?: string;
  warehouse_id?: number;
  zone_id?: number;
  type?: string;
  manager?: string;
  usage?: string;
  spec?: string;
  unit?: string;
  category?: string;
  batch_flag?: boolean;
  sn_flag?: boolean;
  contact?: string;
  phone?: string;
  address?: string;
  object_type?: string;
  prefix?: string;
}

export default WmsMasterAPI;
