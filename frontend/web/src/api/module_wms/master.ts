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
  dept_id?: number;
  warehouse_id?: number;
  zone_id?: number;
  type?: string;
  manager?: string;
  usage?: string;
  capacity?: string;
  category_constraints?: string[];
  mix_rule?: string;
  spec?: string;
  unit?: string;
  category?: string;
  batch_flag?: boolean;
  sn_flag?: boolean;
  safety_stock?: string;
  contact?: string;
  phone?: string;
  email?: string;
  address?: string;
  object_type?: string;
  prefix?: string;
  segment_strategy?: Record<string, unknown>;
  is_demo?: boolean;
  demo_batch_id?: string;
}

export interface WmsMasterForm extends BaseFormType {
  code?: string;
  name?: string;
  status?: number;
  description?: string;
  dept_id?: number;
  warehouse_id?: number;
  zone_id?: number;
  type?: string;
  manager?: string;
  usage?: string;
  capacity?: number;
  category_constraints?: string[];
  mix_rule?: string;
  spec?: string;
  unit?: string;
  category?: string;
  batch_flag?: boolean;
  sn_flag?: boolean;
  safety_stock?: number;
  contact?: string;
  phone?: string;
  email?: string;
  address?: string;
  object_type?: string;
  prefix?: string;
  segment_strategy?: Record<string, unknown>;
  is_demo?: boolean;
  demo_batch_id?: string;
}

export default WmsMasterAPI;
