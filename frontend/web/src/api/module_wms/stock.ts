import { request } from "@utils";

const API_PATH = "/wms/stock";

export const WmsStockAPI = {
  balances(query?: WmsStockBalanceQuery) {
    return request<ApiResponse<PageResult<WmsStockBalance>>>({
      url: `${API_PATH}/balance/list`,
      method: "get",
      params: query,
    });
  },

  flows(query?: WmsStockFlowQuery) {
    return request<ApiResponse<PageResult<WmsStockFlow>>>({
      url: `${API_PATH}/flow/list`,
      method: "get",
      params: query,
    });
  },

  receivePending(body: WmsStockMutationForm) {
    return request<ApiResponse<WmsStockBalance>>({
      url: `${API_PATH}/receive-pending`,
      method: "post",
      data: body,
    });
  },

  approveToAvailable(body: WmsStockMutationForm) {
    return request<ApiResponse<WmsStockBalance>>({
      url: `${API_PATH}/approve-to-available`,
      method: "post",
      data: body,
    });
  },

  lock(body: WmsStockLockForm) {
    return request<ApiResponse<WmsStockLock[]>>({
      url: `${API_PATH}/lock`,
      method: "post",
      data: body,
    });
  },

  releaseLock(lockId: number) {
    return request<ApiResponse<WmsStockBalance>>({
      url: `${API_PATH}/release-lock/${lockId}`,
      method: "post",
    });
  },

  shipLock(lockId: number) {
    return request<ApiResponse<WmsStockBalance>>({
      url: `${API_PATH}/ship-lock/${lockId}`,
      method: "post",
    });
  },

  freeze(body: WmsStockMutationForm) {
    return request<ApiResponse<WmsStockBalance>>({
      url: `${API_PATH}/freeze`,
      method: "post",
      data: body,
    });
  },

  unfreeze(body: WmsStockMutationForm) {
    return request<ApiResponse<WmsStockBalance>>({
      url: `${API_PATH}/unfreeze`,
      method: "post",
      data: body,
    });
  },

  recommend(body: WmsStockLockForm) {
    return request<ApiResponse<WmsStockBalance[]>>({
      url: `${API_PATH}/recommend`,
      method: "post",
      data: body,
    });
  },
};

export interface WmsStockBalanceQuery extends PageQuery, UserByQueryParams, TenantByQueryParams {
  material_id?: number;
  warehouse_id?: number;
  location_id?: number;
  batch_no?: string;
  only_available?: boolean;
  is_demo?: boolean;
}

export interface WmsStockFlowQuery extends PageQuery, UserByQueryParams, TenantByQueryParams {
  material_id?: number;
  batch_no?: string;
  flow_type?: string;
  document_no?: string;
}

export interface WmsStockBalance extends BaseType {
  material_id: number;
  warehouse_id: number;
  location_id?: number;
  batch_no: string;
  sn_code?: string;
  stock_status: string;
  quantity: string;
  available_qty: string;
  locked_qty: string;
  frozen_qty: string;
  pending_qty: string;
  defective_qty: string;
  is_demo: boolean;
  demo_batch_id?: string;
}

export interface WmsStockFlow extends BaseType {
  flow_no: string;
  flow_type: string;
  direction: string;
  material_id: number;
  warehouse_id: number;
  location_id?: number;
  balance_id?: number;
  lock_id?: number;
  batch_no: string;
  sn_code?: string;
  stock_status_before?: string;
  stock_status_after?: string;
  quantity: string;
  document_type?: string;
  document_no?: string;
  remark?: string;
}

export interface WmsStockLock extends BaseType {
  lock_no: string;
  material_id: number;
  warehouse_id: number;
  location_id?: number;
  batch_no: string;
  sn_code?: string;
  quantity: string;
  released_qty: string;
  shipped_qty: string;
  status: string;
  document_type?: string;
  document_no?: string;
}

export interface WmsStockMutationForm extends BaseFormType {
  material_id?: number;
  warehouse_id?: number;
  location_id?: number;
  batch_no?: string;
  sn_code?: string;
  quantity?: number;
  document_type?: string;
  document_no?: string;
  remark?: string;
}

export interface WmsStockLockForm extends BaseFormType {
  material_id?: number;
  warehouse_id?: number;
  location_id?: number;
  quantity?: number;
  document_type?: string;
  document_no?: string;
  remark?: string;
}

export default WmsStockAPI;
