<template>
  <div ref="containerRef" class="screen-container">
    <canvas ref="canvasRef" class="particle-canvas" />
    <div class="scan-line scan-1" />
    <div class="scan-line scan-2" />

    <ScreenHeader />

    <!-- 顶部核心指标卡 x6 -->
    <div class="stat-row">
      <div v-for="s in stats" :key="s.label" class="stat-card">
        <div class="stat-val" :class="'stat-' + s.color">{{ s.value }}</div>
        <div class="stat-label">{{ s.label }}</div>
        <div class="stat-sub">
          <span :class="s.up ? 'up' : 'down'">{{ s.up ? "▲" : "▼" }} {{ s.change }}</span>
          <span class="stat-vs">{{ s.hint }}</span>
        </div>
      </div>
    </div>

    <!-- 主体布局 -->
    <div class="screen-grid">
      <!-- 左列 -->
      <ServiceLevel class="gp-r1 gp-c1-3" :series="flowHourSeries" />
      <TargetReality class="gp-r2 gp-c1-3" :items="warehouseFlowItems" />

      <!-- 中间左 -->
      <LiveMetrics class="gp-r1 gp-c3-5" :metrics="dashboardSummary?.metrics || []" />
      <FunnelChart class="gp-r2 gp-c3-5" :tasks="dashboardSummary?.tasks || []" />

      <!-- 中国地图 -->
      <div class="panel p1 map-panel gp-r1 gp-c5-9" style="grid-row: 1 / 3">
        <FaMapChart :dynamic="true" />
      </div>

      <!-- 中间右 -->
      <ChannelDonut class="gp-r1 gp-c9-11" :items="stockPieItems" />
      <UserProfile class="gp-r2 gp-c9-11" :scores="stockRadarScores" />

      <!-- 右列 -->
      <ProductBar class="gp-r1 gp-c11-13" :items="trendBarItems" />
      <RealtimeMessages class="gp-r2 gp-c11-13" :messages="screenMessages" />
    </div>

    <!-- 大卡片行 x6 统计图 -->
    <div class="card-row">
      <MiniRevenue :value="stockTotalValue" />
      <MiniOrders :value="pendingDocumentValue" />
      <MiniTraffic :value="flowQuantityValue" />
      <MiniRefund :value="warningClosureRate" />
      <MiniInventory :value="availableStockRate" />
      <MiniRating :value="stockHealthScore" :scores="stockRadarScores" />
    </div>

    <!-- 底部状态栏 -->
    <div class="bottom-bar">
      <div class="bb-item"><span class="bb-dot pulse" />系统运行正常</div>
      <div class="bb-item">数据更新时间：{{ updateTime }}</div>
      <div class="bb-ticker">
        <span class="ticker-track">
          <span v-for="t in tickerItems" :key="t" class="ticker-item">{{ t }}</span>
        </span>
      </div>
      <div class="bb-items-right">
        <div v-for="s in structItems" :key="s.label" class="bb-meta">
          <span class="bb-meta-dot" :class="'sr-' + s.cls" />
          {{ s.label }}: {{ s.value }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  computed,
  defineAsyncComponent,
  onMounted,
  onUnmounted,
  provide,
  reactive,
  ref,
  shallowRef,
} from "vue";
import {
  WmsDashboardAPI,
  type WmsDashboardFlow,
  type WmsDashboardMetric,
  type WmsDashboardStockStructure,
  type WmsDashboardSummary,
  type WmsDashboardTrendItem,
  type WmsDashboardWarning,
} from "@/api/module_wms/dashboard";
import ScreenHeader from "./modules/ScreenHeader.vue";
import ServiceLevel from "./modules/ServiceLevel.vue";
import TargetReality from "./modules/TargetReality.vue";
import LiveMetrics from "./modules/LiveMetrics.vue";
import FunnelChart from "./modules/FunnelChart.vue";
import ChannelDonut from "./modules/ChannelDonut.vue";
import UserProfile from "./modules/UserProfile.vue";
import ProductBar from "./modules/ProductBar.vue";
import RealtimeMessages from "./modules/RealtimeMessages.vue";
import MiniRevenue from "./modules/MiniRevenue.vue";
import MiniOrders from "./modules/MiniOrders.vue";
import MiniTraffic from "./modules/MiniTraffic.vue";
import MiniRefund from "./modules/MiniRefund.vue";
import MiniInventory from "./modules/MiniInventory.vue";
import MiniRating from "./modules/MiniRating.vue";

defineOptions({ name: "DashboardScreen" });

const FaMapChart = defineAsyncComponent(() => import("@/components/charts/fa-map-chart/index.vue"));

const containerRef = ref<HTMLDivElement>();
const canvasRef = ref<HTMLCanvasElement>();
const isFullscreen = ref(false);
const updateTime = ref("");
const tickerItems = ref(["WMS 数据加载中"]);
const animFrame = shallowRef(0);
let statsTimer = 0;
let timeTimer = 0;
let dashboardTimer = 0;

type StatColor = "cyan" | "purple" | "green" | "warn" | "teal" | "rose";

interface StatCard {
  label: string;
  value: string;
  change: string;
  hint: string;
  up: boolean;
  color: StatColor;
}

interface ScreenChartItem {
  name: string;
  value: number;
  color?: string;
}

interface ScreenMessage {
  time: string;
  tag: string;
  tagText: string;
  text: string;
}

const stats = reactive<StatCard[]>([
  { label: "库存总量", value: "--", change: "加载中", hint: "库存结构", up: true, color: "cyan" },
  { label: "仓库", value: "--", change: "加载中", hint: "基础档案", up: true, color: "purple" },
  { label: "物料", value: "--", change: "加载中", hint: "主数据", up: true, color: "green" },
  { label: "待处理单据", value: "--", change: "加载中", hint: "作业队列", up: true, color: "warn" },
  { label: "库存批次", value: "--", change: "加载中", hint: "批次台账", up: true, color: "teal" },
  { label: "未关闭预警", value: "--", change: "加载中", hint: "预警中心", up: true, color: "rose" },
]);

const structItems = reactive([
  { label: "WMS 数据", value: "加载中", cls: "cyan" },
]);

const dashboardSummary = ref<WmsDashboardSummary>();
const stockStructure = ref<WmsDashboardStockStructure>();
const trends = ref<WmsDashboardTrendItem[]>([]);
const warnings = ref<WmsDashboardWarning[]>([]);
const flows = ref<WmsDashboardFlow[]>([]);
const hasDashboardData = ref(false);

const stockTotalValue = computed(() => {
  const structure = stockStructure.value;
  if (!structure) return 0;
  return (
    toNumber(structure.available_qty) +
    toNumber(structure.locked_qty) +
    toNumber(structure.frozen_qty) +
    toNumber(structure.pending_qty) +
    toNumber(structure.defective_qty)
  );
});

const pendingDocumentValue = computed(() => Number(metricByLabel("待处理单据")?.value ?? 0) || 0);
const openWarningValue = computed(() => Number(metricByLabel("未关闭预警")?.value ?? warnings.value.length) || 0);
const flowQuantityValue = computed(() => {
  const trendTotal = trends.value.reduce((sum, item) => sum + toNumber(item.quantity), 0);
  const latestFlowTotal = flows.value.reduce((sum, item) => sum + toNumber(item.quantity), 0);
  return trendTotal || latestFlowTotal;
});
const warningClosureRate = computed(() => {
  if (!hasDashboardData.value) return 0;
  return Math.max(0, Math.min(100, 100 - openWarningValue.value * 4));
});
const availableStockRate = computed(() => {
  const total = stockTotalValue.value;
  if (!total || !stockStructure.value) return 0;
  return (toNumber(stockStructure.value.available_qty) / total) * 100;
});
const stockHealthScore = computed(() => {
  if (!stockStructure.value || !hasDashboardData.value) return 0;
  const scores = stockRadarScores.value;
  return scores.length ? Math.round(scores.reduce((sum, item) => sum + item, 0) / scores.length) : 0;
});

const stockPieItems = computed<ScreenChartItem[]>(() => {
  const structure = stockStructure.value;
  if (!structure) return [];
  return [
    { name: "可用库存", value: toNumber(structure.available_qty), color: "#00d4ff" },
    { name: "锁定库存", value: toNumber(structure.locked_qty), color: "#7c3aed" },
    { name: "待检库存", value: toNumber(structure.pending_qty), color: "#10b981" },
    { name: "冻结库存", value: toNumber(structure.frozen_qty), color: "#f59e0b" },
    { name: "不良库存", value: toNumber(structure.defective_qty), color: "#ef4444" },
  ].filter((item) => item.value > 0);
});

const trendBarItems = computed<ScreenChartItem[]>(() =>
  trends.value
    .map((item) => ({ name: flowTypeText(item.flow_type), value: toNumber(item.quantity) }))
    .filter((item) => item.value > 0)
    .sort((a, b) => b.value - a.value)
    .slice(0, 6)
);
const warehouseFlowItems = computed<ScreenChartItem[]>(() => {
  const groups = new Map<number, number>();
  flows.value.forEach((item) => {
    groups.set(item.warehouse_id, (groups.get(item.warehouse_id) ?? 0) + toNumber(item.quantity));
  });
  return Array.from(groups.entries())
    .map(([warehouseId, value]) => ({ name: `仓库${warehouseId}`, value }))
    .filter((item) => item.value > 0)
    .sort((a, b) => b.value - a.value)
    .slice(0, 4);
});
const flowHourSeries = computed(() => {
  const buckets = new Map<string, { inbound: number; outbound: number }>();
  flows.value.forEach((item) => {
    const label = hourText(item.created_time);
    if (!buckets.has(label)) buckets.set(label, { inbound: 0, outbound: 0 });
    const bucket = buckets.get(label)!;
    if (isInboundFlow(item)) {
      bucket.inbound += toNumber(item.quantity);
    } else {
      bucket.outbound += toNumber(item.quantity);
    }
  });
  const labels = Array.from(buckets.keys()).sort().slice(-10);
  return {
    labels,
    inbound: labels.map((label) => buckets.get(label)?.inbound ?? 0),
    outbound: labels.map((label) => buckets.get(label)?.outbound ?? 0),
  };
});
const stockRadarScores = computed(() => {
  const structure = stockStructure.value;
  const total = stockTotalValue.value;
  if (!structure || !total || !hasDashboardData.value) return [];
  const lockedRate = (toNumber(structure.locked_qty) / total) * 100;
  const frozenRate = (toNumber(structure.frozen_qty) / total) * 100;
  const pendingRate = (toNumber(structure.pending_qty) / total) * 100;
  return [
    clamp(availableStockRate.value, 0, 100),
    clamp(100 - lockedRate, 0, 100),
    clamp(100 - frozenRate, 0, 100),
    clamp(warningClosureRate.value, 0, 100),
    clamp(100 - pendingRate, 0, 100),
  ];
});

const screenMessages = computed<ScreenMessage[]>(() => {
  const warningMessages = warnings.value.slice(0, 4).map((item) => ({
    time: timeText(item.created_time),
    tag: "alarm",
    tagText: "预警",
    text: `${warningTypeText(item.warning_type)} ${item.warning_no} 当前库存 ${formatNumber(toNumber(item.current_qty))}`,
  }));
  const flowMessages = flows.value.slice(0, 8).map((item) => ({
    time: timeText(item.created_time),
    tag: flowMessageTag(item.direction),
    tagText: flowMessageText(item.direction),
    text: `${flowTypeText(item.flow_type)} ${item.flow_no} 批次 ${item.batch_no || "-"} 数量 ${formatNumber(
      toNumber(item.quantity)
    )}`,
  }));
  return [...warningMessages, ...flowMessages].slice(0, 8);
});

function updateStats() {
  if (hasDashboardData.value) {
    applyWmsDashboardData();
    return;
  }
  stats.forEach((item) => {
    item.value = "--";
    item.change = "加载中";
    item.up = true;
  });
  tickerItems.value = ["WMS 数据加载中"];
  structItems.splice(0, structItems.length, { label: "WMS 数据", value: "加载中", cls: "cyan" });
}

function toNumber(value: unknown): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function formatNumber(value: number): string {
  return value >= 10000 ? `${(value / 10000).toFixed(1)}万` : Math.round(value).toLocaleString();
}

function metricByLabel(label: string): WmsDashboardMetric | undefined {
  return dashboardSummary.value?.metrics.find((item) => item.label === label);
}

function statusText(status?: string): string {
  const map: Record<string, string> = {
    normal: "正常",
    pending: "待处理",
    warning: "预警",
  };
  return status ? (map[status] ?? status) : "实时";
}

function metricValue(label: string, fallback: number | string = "--"): string {
  const metric = metricByLabel(label);
  const value = metric?.value ?? fallback;
  const unit = metric?.unit ?? "";
  const n = Number(value);
  return Number.isFinite(n) ? `${formatNumber(n)}${unit}` : `${value}${unit}`;
}

function applyStat(index: number, patch: Partial<StatCard>) {
  Object.assign(stats[index]!, patch);
}

function applyWmsDashboardData() {
  const warningCount = openWarningValue.value;
  applyStat(0, {
    label: "库存总量",
    value: formatNumber(stockTotalValue.value),
    change: "实时",
    hint: "库存结构",
    up: true,
  });
  applyStat(1, {
    label: "仓库",
    value: metricValue("仓库"),
    change: statusText(metricByLabel("仓库")?.status),
    hint: "基础档案",
    up: metricByLabel("仓库")?.status !== "warning",
  });
  applyStat(2, {
    label: "物料",
    value: metricValue("物料"),
    change: statusText(metricByLabel("物料")?.status),
    hint: "主数据",
    up: metricByLabel("物料")?.status !== "warning",
  });
  applyStat(3, {
    label: "待处理单据",
    value: metricValue("待处理单据"),
    change: pendingDocumentValue.value > 0 ? "待闭环" : "正常",
    hint: "作业队列",
    up: pendingDocumentValue.value === 0,
  });
  applyStat(4, {
    label: "库存批次",
    value: metricValue("库存批次"),
    change: statusText(metricByLabel("库存批次")?.status),
    hint: "批次台账",
    up: metricByLabel("库存批次")?.status !== "warning",
  });
  applyStat(5, {
    label: "未关闭预警",
    value: metricValue("未关闭预警", warningCount),
    change: warningCount > 0 ? "需关注" : "正常",
    hint: "预警中心",
    up: warningCount === 0,
  });
  updateTickerItems();
  updateStructItems();
}

function updateTickerItems() {
  tickerItems.value = [
    `仓库: ${metricValue("仓库")}`,
    `物料: ${metricValue("物料")}`,
    `库存批次: ${metricValue("库存批次")}`,
    `待处理单据: ${metricValue("待处理单据")}`,
    `未关闭预警: ${metricValue("未关闭预警", openWarningValue.value)}`,
    `最近流水: ${flows.value.length} 条`,
  ];
}

function updateStructItems() {
  const structure = stockStructure.value;
  if (!structure) return;
  const nextItems = [
    { label: "装配", value: dashboardSummary.value?.assembly || "wms", cls: "cyan" },
    { label: "阶段", value: dashboardSummary.value?.phase || "running", cls: "green" },
    { label: "可用库存", value: formatNumber(toNumber(structure.available_qty)), cls: "purple" },
    { label: "待检库存", value: formatNumber(toNumber(structure.pending_qty)), cls: "warn" },
    { label: "冻结库存", value: formatNumber(toNumber(structure.frozen_qty)), cls: "cyan" },
    { label: "锁定库存", value: formatNumber(toNumber(structure.locked_qty)), cls: "green" },
    { label: "不良库存", value: formatNumber(toNumber(structure.defective_qty)), cls: "purple" },
    { label: "最新流水", value: `${flows.value.length}条`, cls: "cyan" },
  ];
  structItems.splice(0, structItems.length, ...nextItems);
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function flowTypeText(type: string) {
  const map: Record<string, string> = {
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
  return map[type] ?? type;
}

function warningTypeText(type: string) {
  const map: Record<string, string> = {
    safety_stock: "安全库存",
    shortage: "缺料预警",
    expiry: "效期预警",
    stagnant: "呆滞预警",
  };
  return map[type] ?? type;
}

function flowMessageTag(direction: string) {
  if (direction === "out" || direction === "outbound") return "order";
  if (direction === "in" || direction === "inbound") return "audit";
  return "system";
}

function flowMessageText(direction: string) {
  if (direction === "out" || direction === "outbound") return "出库";
  if (direction === "in" || direction === "inbound") return "入库";
  return "流水";
}

function isInboundFlow(item: WmsDashboardFlow) {
  return (
    item.direction === "in" ||
    item.direction === "inbound" ||
    item.flow_type === "receive_pending" ||
    item.flow_type === "approve_to_available" ||
    item.flow_type === "transfer_in"
  );
}

function hourText(value?: string) {
  if (!value) return "--:00";
  const time = new Date(value);
  if (Number.isNaN(time.getTime())) return value.slice(0, 2).padStart(2, "0") + ":00";
  return time.toLocaleTimeString("zh-CN", { hour: "2-digit", hour12: false }) + ":00";
}

function timeText(value?: string) {
  if (!value) return updateTime.value || "--:--";
  const time = new Date(value);
  if (Number.isNaN(time.getTime())) return value.slice(0, 5);
  return time.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false });
}

async function loadWmsDashboard() {
  try {
    const [summaryResp, structureResp, trendResp, warningResp, flowResp] = await Promise.all([
      WmsDashboardAPI.summary(),
      WmsDashboardAPI.stockStructure(),
      WmsDashboardAPI.trends(),
      WmsDashboardAPI.warnings(),
      WmsDashboardAPI.latestFlows(),
    ]);
    dashboardSummary.value = summaryResp.data.data;
    stockStructure.value = structureResp.data.data;
    trends.value = trendResp.data.data;
    warnings.value = warningResp.data.data;
    flows.value = flowResp.data.data;
    hasDashboardData.value = true;
    applyWmsDashboardData();
  } catch {
    hasDashboardData.value = false;
  }
}

async function toggleFullscreen() {
  try {
    if (document.fullscreenElement) {
      await document.exitFullscreen();
    } else {
      await containerRef.value?.requestFullscreen();
    }
  } catch {
    /* ignored */
  }
}

function onFullscreenChange() {
  isFullscreen.value = !!document.fullscreenElement;
}

// fullscreenchange 是 document 级别事件，必须在 onUnmounted 中清理，
// 否则 keep-alive / 重复进入会累积监听器
onMounted(() => {
  document.addEventListener("fullscreenchange", onFullscreenChange);
});

onUnmounted(() => {
  document.removeEventListener("fullscreenchange", onFullscreenChange);
});

provide("toggleFullscreen", toggleFullscreen);
provide("isFullscreen", isFullscreen);

/* ========== 粒子背景 ========== */
let ctx: CanvasRenderingContext2D | null = null;
interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  r: number;
}
let particles: Particle[] = [];

function initParticles() {
  const c = canvasRef.value;
  if (!c) return;
  ctx = c.getContext("2d");
  resizeCanvas();
  spawnParticles();
  tick();
}

function resizeCanvas() {
  const c = canvasRef.value;
  if (!c || !containerRef.value) return;
  c.width = containerRef.value.clientWidth;
  c.height = containerRef.value.clientHeight;
}

function spawnParticles() {
  const c = canvasRef.value;
  if (!c) return;
  const count = Math.floor((c.width * c.height) / 18000);
  particles = Array.from({ length: count }, () => ({
    x: Math.random() * c.width,
    y: Math.random() * c.height,
    vx: (Math.random() - 0.5) * 0.4,
    vy: (Math.random() - 0.5) * 0.4,
    r: Math.random() * 1.5 + 0.5,
  }));
}

function tick() {
  if (!ctx || !canvasRef.value) return;
  const c = canvasRef.value;
  const w = c.width;
  const h = c.height;
  ctx.clearRect(0, 0, w, h);

  for (const p of particles) {
    p.x += p.vx;
    p.y += p.vy;
    if (p.x < 0) p.x = w;
    if (p.x > w) p.x = 0;
    if (p.y < 0) p.y = h;
    if (p.y > h) p.y = 0;
  }

  for (let i = 0; i < particles.length; i++) {
    const a = particles[i]!;
    ctx.beginPath();
    ctx.arc(a.x, a.y, a.r, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(0,212,255,0.25)";
    ctx.fill();

    for (let j = i + 1; j < particles.length; j++) {
      const b = particles[j]!;
      const dx = a.x - b.x;
      const dy = a.y - b.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < 120) {
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.strokeStyle = `rgba(0,212,255,${0.06 * (1 - dist / 120)})`;
        ctx.lineWidth = 0.5;
        ctx.stroke();
      }
    }
  }

  animFrame.value = requestAnimationFrame(tick);
}

onMounted(() => {
  const timeTick = () => {
    updateTime.value = new Date().toLocaleTimeString("zh-CN", { hour12: false });
  };
  timeTick();
  timeTimer = window.setInterval(timeTick, 1000);
  initParticles();
  statsTimer = window.setInterval(updateStats, 3000);
  dashboardTimer = window.setInterval(loadWmsDashboard, 30000);
  updateStats();
  void loadWmsDashboard();
  window.addEventListener("resize", handleWindowResize);
});

onUnmounted(() => {
  cancelAnimationFrame(animFrame.value);
  clearInterval(statsTimer);
  clearInterval(timeTimer);
  clearInterval(dashboardTimer);
  window.removeEventListener("resize", handleWindowResize);
  if (document.fullscreenElement) {
    document.exitFullscreen().catch(() => {});
  }
});

function handleWindowResize() {
  resizeCanvas();
  spawnParticles();
}
</script>

<style scoped>
.screen-container {
  --bg: #060b24;
  --accent: #00d4ff;
  --text: #b8c6e0;
  --border: rgb(0 180 255 / 12%);

  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  font-family: "PingFang SC", "Microsoft YaHei", monospace;
  color: var(--text);
  background: var(--bg);
}

.particle-canvas {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}

.scan-line {
  position: absolute;
  left: 0;
  z-index: 1;
  width: 100%;
  height: 1px;
  pointer-events: none;
  opacity: 0.08;
  will-change: transform;
}

.scan-1 {
  top: 0;
  background: linear-gradient(90deg, transparent, var(--accent), transparent);
  animation: scanDown 6s linear infinite;
}

.scan-2 {
  top: 100%;
  background: linear-gradient(90deg, transparent, #7c3aed, transparent);
  animation: scanDown 6s linear 3s infinite;
}
@keyframes scanDown {
  0% {
    transform: translateY(0);
  }

  100% {
    transform: translateY(-100vh);
  }
}

/* ===== 背景网格 ===== */
.screen-container::after {
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  content: "";
  background-image:
    linear-gradient(rgb(0 212 255 / 3%) 1px, transparent 1px),
    linear-gradient(90deg, rgb(0 212 255 / 3%) 1px, transparent 1px);
  background-size: 60px 60px;
}

/* ===== 顶部指标卡 ===== */
.stat-row {
  position: relative;
  z-index: 2;
  display: flex;
  flex-shrink: 0;
  gap: 16px;
  padding: 0 16px 16px;
}

.stat-card {
  position: relative;
  display: flex;
  flex: 1;
  flex-direction: column;
  justify-content: center;
  padding: 18px 24px;
  overflow: hidden;
  background: linear-gradient(135deg, rgb(0 20 60 / 60%) 0%, rgb(0 10 40 / 50%) 100%);
  border: 1px solid var(--border);
  border-radius: 10px;
}

.stat-card::before {
  position: absolute;
  top: -1px;
  right: 14px;
  left: 14px;
  height: 1px;
  content: "";
  background: linear-gradient(90deg, transparent, rgb(0 212 255 / 40%), transparent);
}

.stat-card::after {
  position: absolute;
  top: 4px;
  left: 4px;
  width: 8px;
  height: 8px;
  content: "";
  border-top: 1px solid rgb(0 212 255 / 50%);
  border-left: 1px solid rgb(0 212 255 / 50%);
}

.stat-val {
  margin-bottom: 6px;
  font-size: 28px;
  font-weight: 800;
  line-height: 1;
}

.stat-cyan {
  color: #00d4ff;
}

.stat-purple {
  color: #7c3aed;
}

.stat-green {
  color: #10b981;
}

.stat-warn {
  color: #f59e0b;
}

.stat-teal {
  color: #14b8a6;
}

.stat-rose {
  color: #f43f5e;
}

.stat-label {
  margin-bottom: 6px;
  font-size: 11px;
  opacity: 0.4;
}

.stat-sub {
  display: flex;
  gap: 6px;
  align-items: center;
  font-size: 10px;
}

.stat-sub .up {
  color: #10b981;
}

.stat-sub .down {
  color: #f59e0b;
}

.stat-vs {
  opacity: 0.3;
}

/* ===== Grid 主体 ===== */
.screen-grid {
  position: relative;
  z-index: 2;
  display: grid;
  flex: 1;
  grid-template-rows: repeat(2, 1fr);
  grid-template-columns: repeat(12, 1fr);
  gap: 16px;
  min-height: 0;
  padding: 0 16px 16px;
}

.gp-r1 {
  grid-row: 1;
}

.gp-r2 {
  grid-row: 2;
}

.gp-c1-3 {
  grid-column: 1 / 3;
}

.gp-c1-4 {
  grid-column: 1 / 4;
}

.gp-c3-5 {
  grid-column: 3 / 5;
}

.gp-c4-10 {
  grid-column: 4 / 10;
}

.gp-c5-9 {
  grid-column: 5 / 9;
}

.gp-c9-11 {
  grid-column: 9 / 11;
}

.gp-c10-13 {
  grid-column: 10 / 13;
}

.gp-c11-13 {
  grid-column: 11 / 13;
}

/* ===== 共享面板 ===== */
:deep(.panel) {
  position: relative;
  display: flex;
  flex-direction: column;
  padding: 18px 16px;
  overflow: hidden;
  background: linear-gradient(180deg, rgb(0 30 80 / 55%) 0%, rgb(6 11 36 / 70%) 100%);
  border: 1px solid var(--border);
  border-radius: 14px;
}

:deep(.panel)::before {
  position: absolute;
  top: 0;
  right: 20px;
  left: 20px;
  z-index: 1;
  height: 1px;
  pointer-events: none;
  content: "";
  background: linear-gradient(90deg, transparent, rgb(0 212 255 / 30%), transparent);
}

:deep(.panel)::after {
  position: absolute;
  inset: -1px;
  z-index: 0;
  pointer-events: none;
  content: "";
  background:
    linear-gradient(to right, rgb(0 212 255 / 30%) 1px, transparent 1px) 0 0 / 12px 1px no-repeat,
    linear-gradient(to bottom, rgb(0 212 255 / 30%) 1px, transparent 1px) 0 0 / 1px 12px no-repeat,
    linear-gradient(to left, rgb(0 212 255 / 30%) 1px, transparent 1px) 100% 0 / 12px 1px no-repeat,
    linear-gradient(to bottom, rgb(0 212 255 / 30%) 1px, transparent 1px) 100% 0 / 1px 12px
      no-repeat,
    linear-gradient(to right, rgb(0 212 255 / 30%) 1px, transparent 1px) 0 100% / 12px 1px no-repeat,
    linear-gradient(to top, rgb(0 212 255 / 30%) 1px, transparent 1px) 0 100% / 1px 12px no-repeat,
    linear-gradient(to left, rgb(0 212 255 / 30%) 1px, transparent 1px) 100% 100% / 12px 1px
      no-repeat,
    linear-gradient(to top, rgb(0 212 255 / 30%) 1px, transparent 1px) 100% 100% / 1px 12px
      no-repeat;
  border-radius: 14px;
}

:deep(.map-panel) {
  padding: 0;
  overflow: hidden;
}

:deep(.map-panel)::after {
  background: none;
}

:deep(.map-panel > div) {
  height: 100% !important;
  padding: 12px;
}

:deep(#china-map) {
  border-radius: 12px;
}

:deep(.panel-hd) {
  display: flex;
  flex-shrink: 0;
  gap: 8px;
  align-items: center;
  padding-bottom: 12px;
  margin-bottom: 10px;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 1px;
  border-bottom: 1px solid rgb(0 212 255 / 8%);
}

:deep(.dot) {
  display: inline-block;
  flex-shrink: 0;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  box-shadow: 0 0 6px currentcolor;
}

:deep(.dot.accent) {
  color: var(--accent);
  background: var(--accent);
}

:deep(.dot.green) {
  color: #10b981;
  background: #10b981;
}

:deep(.dot.warn) {
  color: #f59e0b;
  background: #f59e0b;
}

:deep(.dot.purple) {
  color: #7c3aed;
  background: #7c3aed;
}

/* ===== 大卡片行 x6 ===== */
.card-row {
  position: relative;
  z-index: 2;
  display: flex;
  flex-shrink: 0;
  gap: 16px;
  height: 180px;
  padding: 0 16px 16px;
}

.card-row > * {
  flex: 1;
}

/* ===== 底部状态栏 ===== */
.bottom-bar {
  position: relative;
  z-index: 2;
  display: flex;
  flex-shrink: 0;
  gap: 24px;
  align-items: center;
  padding: 10px 24px;
  margin: 0 16px 16px;
  font-size: 11px;
  background: linear-gradient(90deg, rgb(0 20 60 / 50%) 0%, rgb(0 20 60 / 30%) 100%);
  border: 1px solid rgb(0 180 255 / 10%);
  border-radius: 8px;
  opacity: 0.7;
}

.bb-item {
  display: flex;
  flex-shrink: 0;
  gap: 6px;
  align-items: center;
}

.bb-dot {
  width: 6px;
  height: 6px;
  background: #10b981;
  border-radius: 50%;
  box-shadow: 0 0 6px #10b981;
}

.bb-ticker {
  flex: 1;
  overflow: hidden;
  mask-image: linear-gradient(90deg, transparent, #000 10%, #000 90%, transparent);
}

.ticker-track {
  display: flex;
  gap: 32px;
  white-space: nowrap;
  animation: tickerScroll 20s linear infinite;
}

.ticker-item {
  flex-shrink: 0;
}
@keyframes tickerScroll {
  0% {
    transform: translateX(0);
  }

  100% {
    transform: translateX(-100%);
  }
}

.bb-items-right {
  display: flex;
  flex-shrink: 0;
  gap: 14px;
  align-items: center;
}

.bb-meta {
  display: flex;
  gap: 4px;
  align-items: center;
  font-size: 10px;
  opacity: 0.6;
}

.bb-meta-dot {
  flex-shrink: 0;
  width: 5px;
  height: 5px;
  border-radius: 50%;
}

.sr-cyan {
  background: #00d4ff;
  box-shadow: 0 0 5px #00d4ff;
}

.sr-green {
  background: #10b981;
  box-shadow: 0 0 5px #10b981;
}

.sr-purple {
  background: #7c3aed;
  box-shadow: 0 0 5px #7c3aed;
}

.sr-warn {
  background: #f59e0b;
  box-shadow: 0 0 5px #f59e0b;
}
</style>
