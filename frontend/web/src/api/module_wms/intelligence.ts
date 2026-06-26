import { request } from "@utils";

const API_PATH = "/wms/intelligence";

export const WmsIntelligenceAPI = {
  dashboardSummary() {
    return request<ApiResponse<WmsIntelligenceSummary>>({
      url: `${API_PATH}/dashboard-summary`,
      method: "get",
    });
  },

  warningAdvice(warningId: number) {
    return request<ApiResponse<WmsWarningAdvice>>({
      url: `${API_PATH}/warning/${warningId}/advice`,
      method: "get",
    });
  },

  outboundExplain(body: WmsOutboundExplainRequest) {
    return request<ApiResponse<WmsOutboundExplain>>({
      url: `${API_PATH}/stock/outbound-explain`,
      method: "post",
      data: body,
    });
  },
};

export type WmsIntelligenceSource = "ai" | "rule_fallback";
export type WmsRiskLevel = "normal" | "warning" | "critical";

export interface WmsIntelligenceAction {
  label: string;
  route?: string | null;
  permission?: string | null;
  payload?: Record<string, unknown>;
}

export interface WmsIntelligenceSummary {
  title: string;
  summary: string;
  risk_level: WmsRiskLevel;
  source: WmsIntelligenceSource;
  bullets: string[];
  actions: WmsIntelligenceAction[];
}

export interface WmsWarningAdvice {
  warning_id: number;
  warning_type: string;
  risk_level: WmsRiskLevel;
  reason: string;
  advice: string;
  source: WmsIntelligenceSource;
  actions: WmsIntelligenceAction[];
}

export interface WmsOutboundExplainRequest {
  material_id: number;
  warehouse_id?: number;
  location_id?: number;
  required_qty?: string;
}

export interface WmsOutboundCandidateScore {
  balance_id: number;
  material_id: number;
  warehouse_id: number;
  location_id?: number | null;
  batch_no?: string | null;
  available_qty: string;
  score: number;
  rule_reasons: string[];
}

export interface WmsOutboundExplain {
  material_id: number;
  source: WmsIntelligenceSource;
  summary: string;
  candidates: WmsOutboundCandidateScore[];
}

export default WmsIntelligenceAPI;
