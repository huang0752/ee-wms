export type WmsTone = "primary" | "success" | "warning" | "danger" | "info";

export interface WmsStatusMeta {
  label: string;
  type: WmsTone;
  progress: number;
  stage: string;
  description: string;
}

export interface WmsMetricDefinition {
  label: string;
  statuses: string[];
  icon: string;
  unit?: string;
}

export interface WmsMetricCard {
  label: string;
  value: number | string;
  icon: string;
  tone: WmsTone;
  unit?: string;
  hint?: string;
}

export interface WmsDescriptionItem {
  label: string;
  prop: string;
  span?: number;
  render?: (value: unknown, row: RowLike) => string | number;
}

type RowLike = Record<string, unknown>;

const STATUS_META: Record<string, WmsStatusMeta> = {
  draft: { label: "草稿", type: "info", progress: 8, stage: "待提交", description: "单据已创建，尚未进入正式作业。" },
  pending_receive: {
    label: "待收货",
    type: "warning",
    progress: 18,
    stage: "收货",
    description: "到货单等待仓管收货确认。",
  },
  pending_inspection: {
    label: "待检验",
    type: "primary",
    progress: 38,
    stage: "检验",
    description: "物料已收货，等待 IQC 检验判定。",
  },
  pending_inbound: {
    label: "待入库",
    type: "warning",
    progress: 58,
    stage: "入库",
    description: "检验已完成，等待生成或确认入库单。",
  },
  pending_confirm: {
    label: "待确认",
    type: "warning",
    progress: 72,
    stage: "确认",
    description: "库存影响尚未正式落账。",
  },
  pending_reserve: {
    label: "待锁库",
    type: "warning",
    progress: 20,
    stage: "锁库",
    description: "出库需求已生成，等待库存锁定。",
  },
  reserved: {
    label: "已锁库",
    type: "primary",
    progress: 45,
    stage: "拣货",
    description: "可用库存已锁定，等待拣货。",
  },
  picked: {
    label: "已拣货",
    type: "primary",
    progress: 66,
    stage: "复核",
    description: "仓库已完成拣货，等待复核。",
  },
  reviewed: {
    label: "已复核",
    type: "primary",
    progress: 82,
    stage: "确认",
    description: "复核通过，等待最终出库确认。",
  },
  confirmed: {
    label: "已确认",
    type: "success",
    progress: 100,
    stage: "完成",
    description: "单据已完成并写入库存账。",
  },
  audited: {
    label: "已审核",
    type: "success",
    progress: 100,
    stage: "完成",
    description: "盘点差异已审核并完成调账。",
  },
  closed: {
    label: "已关闭",
    type: "success",
    progress: 100,
    stage: "关闭",
    description: "关联流程已关闭。",
  },
  cancelled: {
    label: "已取消",
    type: "info",
    progress: 100,
    stage: "取消",
    description: "单据已取消，不再继续执行。",
  },
  open: {
    label: "待处理",
    type: "danger",
    progress: 30,
    stage: "预警",
    description: "预警尚未关闭，需要仓储人员处理。",
  },
  active: {
    label: "生效中",
    type: "primary",
    progress: 60,
    stage: "执行",
    description: "锁库或策略正在生效。",
  },
  released: {
    label: "已释放",
    type: "info",
    progress: 100,
    stage: "释放",
    description: "锁定库存已释放。",
  },
  shipped: {
    label: "已发出",
    type: "success",
    progress: 100,
    stage: "完成",
    description: "锁定库存已发出。",
  },
  available: {
    label: "可用",
    type: "success",
    progress: 100,
    stage: "可用",
    description: "库存可用于领料或出库。",
  },
  pending: {
    label: "待处理",
    type: "warning",
    progress: 30,
    stage: "待处理",
    description: "事项等待后续处理。",
  },
  pending_inspection_stock: {
    label: "待检",
    type: "warning",
    progress: 40,
    stage: "待检",
    description: "库存待检，暂不可出库。",
  },
  defective: {
    label: "不良",
    type: "danger",
    progress: 100,
    stage: "隔离",
    description: "不良库存应隔离处理。",
  },
  frozen: {
    label: "冻结",
    type: "warning",
    progress: 50,
    stage: "冻结",
    description: "库存已冻结，暂不可用。",
  },
  mixed: {
    label: "混合",
    type: "info",
    progress: 65,
    stage: "汇总",
    description: "库存余额包含多个库存桶。",
  },
};

export const WMS_FLOW_TYPE_LABELS: Record<string, string> = {
  receive_pending: "收货待检",
  approve_to_available: "检验合格",
  reject_to_defective: "检验不良",
  lock: "库存锁定",
  release_lock: "释放锁定",
  ship: "出库扣减",
  freeze: "冻结",
  unfreeze: "解冻",
  transfer_out: "调拨出库",
  transfer_in: "调拨入库",
  adjust_check: "盘点调整",
};

export const WMS_SOURCE_LABELS: Record<string, string> = {
  manual: "手工",
  erp: "ERP",
  mes: "MES",
  pda: "PDA",
  integration: "集成",
};

export const WMS_SYNC_LABELS: Record<string, string> = {
  not_required: "无需同步",
  pending: "待同步",
  synced: "已同步",
  failed: "同步失败",
};

export function getWmsStatusMeta(status?: string | null): WmsStatusMeta {
  if (!status) {
    return { label: "-", type: "info", progress: 0, stage: "未知", description: "暂无状态。" };
  }
  if (status === "pending_inspection") return STATUS_META.pending_inspection!;
  return (
    STATUS_META[status] ?? {
      label: status,
      type: "info",
      progress: 0,
      stage: "未知",
      description: "暂未配置该状态的业务说明。",
    }
  );
}

export function getQuantityProgress(done?: unknown, total?: unknown): number {
  const numerator = toNumber(done);
  const denominator = toNumber(total);
  if (denominator <= 0 || numerator <= 0) return 0;
  return Math.min(100, Math.round((numerator / denominator) * 100));
}

export function sumDecimalFields(rows: RowLike[], fields: string[]): number {
  return rows.reduce((sum, row) => {
    return (
      sum +
      fields.reduce((fieldSum, field) => {
        return fieldSum + toNumber(row[field]);
      }, 0)
    );
  }, 0);
}

export function buildDocumentMetrics(rows: RowLike[], definitions: WmsMetricDefinition[]): WmsMetricCard[] {
  return definitions.map((definition) => {
    const value = rows.filter((row) => definition.statuses.includes(String(row.status ?? ""))).length;
    const firstStatus = definition.statuses[0];
    return {
      label: definition.label,
      value,
      icon: definition.icon,
      tone: getWmsStatusMeta(firstStatus).type,
      unit: definition.unit,
    };
  });
}

export function buildStaticMetric(
  label: string,
  value: number | string,
  iconOrOptions: string | { icon: string; tone?: WmsTone; unit?: string; hint?: string },
  tone: WmsTone = "primary",
  unit?: string,
  hint?: string
): WmsMetricCard {
  if (typeof iconOrOptions === "string") {
    return { label, value, icon: iconOrOptions, tone, unit, hint };
  }
  return {
    label,
    value,
    icon: iconOrOptions.icon,
    tone: iconOrOptions.tone ?? "primary",
    unit: iconOrOptions.unit,
    hint: iconOrOptions.hint,
  };
}

export function formatNullable(value: unknown, suffix = ""): string {
  if (value === null || value === undefined || value === "") return "-";
  return `${String(value)}${suffix}`;
}

export function formatQuantity(value: unknown, unit = ""): string {
  const numeric = toNumber(value);
  if (!Number.isFinite(numeric)) return "-";
  const formatted = Number.isInteger(numeric) ? String(numeric) : numeric.toFixed(4).replace(/0+$/, "").replace(/\.$/, "");
  return unit ? `${formatted} ${unit}` : formatted;
}

export function getSourceLabel(value?: string | null): string {
  if (!value) return "-";
  return WMS_SOURCE_LABELS[value] ?? value;
}

export function getSyncLabel(value?: string | null): string {
  if (!value) return "-";
  return WMS_SYNC_LABELS[value] ?? value;
}

export function getFlowTypeLabel(value?: string | null): string {
  if (!value) return "-";
  return WMS_FLOW_TYPE_LABELS[value] ?? value;
}

export function toNumber(value: unknown): number {
  if (typeof value === "number") return Number.isFinite(value) ? value : 0;
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return 0;
}
