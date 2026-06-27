import { request } from "@utils";

const API_PATH = "/wms/demo";
const AI_DEMO_REQUEST_TIMEOUT = 120000;

export const WmsDemoAPI = {
  preview(body: WmsDemoInitForm) {
    return request<ApiResponse<WmsDemoPreview>>({
      url: `${API_PATH}/preview`,
      method: "post",
      data: body,
      timeout: body.use_ai_enrichment ? AI_DEMO_REQUEST_TIMEOUT : undefined,
    });
  },

  init(body: WmsDemoInitForm) {
    return request<ApiResponse<WmsDemoBatch>>({
      url: `${API_PATH}/init`,
      method: "post",
      data: body,
      timeout: body.use_ai_enrichment ? AI_DEMO_REQUEST_TIMEOUT : undefined,
    });
  },

  clean(demoBatchId: string) {
    return request<ApiResponse<WmsDemoCleanResult>>({
      url: `${API_PATH}/clean/${demoBatchId}`,
      method: "delete",
    });
  },

  history() {
    return request<ApiResponse<WmsDemoHistory[]>>({
      url: `${API_PATH}/history`,
      method: "get",
    });
  },

  samplePools() {
    return request<ApiResponse<WmsDemoSamplePool[]>>({
      url: `${API_PATH}/sample-pools`,
      method: "get",
    });
  },

  copySamplePool(poolId: number) {
    return request<ApiResponse<WmsDemoSamplePool>>({
      url: `${API_PATH}/sample-pools/${poolId}/copy`,
      method: "post",
    });
  },

  updateSamplePool(
    poolId: number,
    body: Partial<
      Pick<
        WmsDemoSamplePool,
        "name" | "prompt_template" | "fallback_template" | "config" | "is_active"
      >
    >
  ) {
    return request<ApiResponse<WmsDemoSamplePool>>({
      url: `${API_PATH}/sample-pools/${poolId}`,
      method: "put",
      data: body,
    });
  },

  updateSampleItem(itemId: number, body: Partial<WmsDemoSampleItem>) {
    return request<ApiResponse<WmsDemoSampleItem>>({
      url: `${API_PATH}/sample-items/${itemId}`,
      method: "put",
      data: body,
    });
  },
};

export interface WmsDemoEnterpriseProfile {
  company_name: string;
  industry: string;
  company_size: "small" | "medium" | "large";
  scenario: string;
  warehouse_count?: number;
  material_count?: number;
}

export interface WmsDemoQuantityTargets {
  warehouse_count?: number;
  location_count?: number;
  material_count?: number;
  stock_flow_count?: number;
  business_doc_count?: number;
  warning_count?: number;
}

export interface WmsDemoNumberingProfile {
  tenant_short_code?: string;
  numbering_style: "default" | "tenant" | "traceable_demo";
  date_format: "yyyyMMdd" | "yyMMdd" | "yyyyMM";
  sequence_digits: number;
  include_demo_suffix: boolean;
  prefixes: Record<string, string>;
}

export interface WmsDemoCustomProduct {
  name: string;
  category?: string;
  voltage_level?: string;
  spec_examples: string[];
  unit?: string;
  storage_traits: string[];
  quality_requirements?: string;
  supplier_requirement?: string;
  weight: number;
}

export interface WmsDemoInitForm {
  profile: WmsDemoEnterpriseProfile;
  sample_pool_id?: number;
  numbering: WmsDemoNumberingProfile;
  product_directions: string[];
  custom_products: WmsDemoCustomProduct[];
  warehouse_scenarios: string[];
  scale_mode: "quick" | "standard" | "rich" | "custom";
  quantity_targets: WmsDemoQuantityTargets;
  time_range_days: number;
  naming_style: "industrial" | "compact" | "tenant";
  quality_requirements?: string;
  generation_instructions?: string;
  use_ai_enrichment: boolean;
  batch_policy: "reject_if_exists" | "append" | "clean_rebuild";
}

export interface WmsDemoScenarioSummary {
  title: string;
  summary: string;
  highlights: string[];
}

export interface WmsDemoPreview {
  sample_pool_name: string;
  scale_mode: string;
  estimated_counts: Record<string, number>;
  product_mix: Array<Record<string, unknown>>;
  workflow_coverage: string[];
  warnings: string[];
  preview_names: Record<string, string[]>;
  enrichment_source: string;
  scenario_summary?: WmsDemoScenarioSummary;
}

export interface WmsDemoBatch {
  module: string;
  scenario: string;
  demo_batch_id: string;
  task_id: number;
  counts: Record<string, number>;
  summary: string[];
  preview_snapshot?: WmsDemoPreview;
  quality_report?: Record<string, unknown>;
}

export interface WmsDemoCleanResult {
  demo_batch_id: string;
  counts: Record<string, number>;
}

export interface WmsDemoHistory {
  id: number;
  demo_batch_id?: string;
  title: string;
  status: string;
  progress?: number;
  payload?: Record<string, unknown>;
  result?: Record<string, unknown>;
}

export interface WmsDemoSampleItem {
  id: number;
  group_key: string;
  group_name: string;
  item_key: string;
  item_name: string;
  acceptance_scope?: string;
  spec_patterns: string[];
  supplier_patterns: string[];
  material_patterns: string[];
  storage_traits: string[];
  quality_traits: string[];
  weight: number;
  enabled: boolean;
}

export interface WmsDemoSamplePool {
  id: number;
  code: string;
  name: string;
  industry?: string;
  is_system: boolean;
  is_active: boolean;
  prompt_template?: string;
  fallback_template?: string;
  config?: Record<string, unknown>;
  items: WmsDemoSampleItem[];
}

export default WmsDemoAPI;
