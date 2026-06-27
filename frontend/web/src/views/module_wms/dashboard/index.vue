<template>
  <div class="wms-dashboard">
    <section class="wms-dashboard__hero">
      <div class="wms-dashboard__hero-main">
        <div class="wms-dashboard__eyebrow">
          <span class="wms-dashboard__pulse"></span>
          WMS OPERATIONS CENTER
        </div>
        <h1>仓储驾驶舱</h1>
        <p>面向库存、单据、预警与流水的实时运行视图，优先暴露异常和待处理作业。</p>
        <div class="wms-dashboard__meta">
          <span>装配 {{ summary?.assembly || "wms" }}</span>
          <span>阶段 {{ summary?.phase || "v1-running-loop" }}</span>
        </div>
      </div>
      <div class="wms-dashboard__hero-side">
        <div class="wms-dashboard__status-card">
          <span>运行状态</span>
          <strong>{{ openWarningCount > 0 ? "需要关注" : "运行平稳" }}</strong>
          <p>{{ openWarningCount > 0 ? `${openWarningCount} 条预警待处理` : "暂无未关闭预警" }}</p>
        </div>
        <ElButton type="primary" :loading="loading" :icon="Refresh" @click="loadDashboard">刷新数据</ElButton>
      </div>
    </section>

    <WmsIntelligenceSummary :summary="intelligenceSummary" />

    <section class="wms-dashboard__metrics">
      <article
        v-for="metric in metricCards"
        :key="metric.label"
        class="wms-dashboard__metric"
        :class="`is-${metric.tone}`"
      >
        <div class="wms-dashboard__metric-icon">
          <FaSvgIcon :icon="metric.icon" />
        </div>
        <div class="wms-dashboard__metric-body">
          <span>{{ metric.label }}</span>
          <strong>{{ Number(metric.value) || 0 }}</strong>
          <p>{{ metric.unit ? `${metric.status} / ${metric.unit}` : metric.status }}</p>
        </div>
      </article>
    </section>

    <ElRow :gutter="16">
      <ElCol :xs="24" :lg="9" class="mb-4">
        <ElCard shadow="never" class="wms-dashboard__panel">
          <template #header>
            <div class="wms-dashboard__panel-title">
              <span>库存结构</span>
              <small>按库存状态聚合</small>
            </div>
          </template>
          <div v-for="item in stockBars" :key="item.label" class="wms-dashboard__bar">
            <div>
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
            <div class="wms-dashboard__track">
              <span :class="item.tone" :style="{ width: `${item.percent}%` }"></span>
            </div>
          </div>
        </ElCard>
      </ElCol>

      <ElCol :xs="24" :lg="7" class="mb-4">
        <ElCard shadow="never" class="wms-dashboard__panel wms-dashboard__task-panel">
          <template #header>
            <div class="wms-dashboard__panel-title">
              <span>阶段任务</span>
              <small>待办作业闭环</small>
            </div>
          </template>
          <div class="wms-dashboard__tasks">
            <div v-for="item in timelineTasks" :key="item.content" class="wms-dashboard__task">
              <span :class="item.code"></span>
              <div>
                <strong>{{ item.content }}</strong>
                <p>{{ item.time }}</p>
              </div>
            </div>
          </div>
        </ElCard>
      </ElCol>

      <ElCol :xs="24" :lg="8" class="mb-4">
        <ElCard shadow="never" class="wms-dashboard__panel">
          <template #header>
            <div class="wms-dashboard__panel-title">
              <span>流水趋势</span>
              <small>最近库存流转</small>
            </div>
          </template>
          <div v-for="item in trendBars" :key="item.flow_type" class="wms-dashboard__bar">
            <div>
              <span>{{ flowTypeText(item.flow_type) }}</span>
              <strong>{{ item.quantity }}</strong>
            </div>
            <div class="wms-dashboard__track">
              <span class="flow" :style="{ width: `${item.percent}%` }"></span>
            </div>
          </div>
          <ElEmpty v-if="trendBars.length === 0" :image-size="80" description="暂无流水" />
        </ElCard>
      </ElCol>
    </ElRow>

    <ElRow :gutter="16">
      <ElCol :xs="24" :lg="14" class="mb-4">
        <ElCard shadow="never" class="wms-dashboard__panel">
          <template #header>
            <div class="wms-dashboard__panel-title">
              <span>最新库存流水</span>
              <small>入库、出库、调拨和盘点动作</small>
            </div>
          </template>
          <ElTable :data="flows" height="320" row-key="id" class="wms-dashboard__table">
            <ElTableColumn prop="flow_no" label="流水号" min-width="150" />
            <ElTableColumn prop="flow_type" label="类型" width="150">
              <template #default="{ row }">{{ flowTypeText(row.flow_type) }}</template>
            </ElTableColumn>
            <ElTableColumn prop="batch_no" label="批次" min-width="140" />
            <ElTableColumn prop="quantity" label="数量" width="100" />
            <ElTableColumn prop="document_no" label="单据号" min-width="140" />
          </ElTable>
        </ElCard>
      </ElCol>

      <ElCol :xs="24" :lg="10" class="mb-4">
        <ElCard shadow="never" class="wms-dashboard__panel">
          <template #header>
            <div class="wms-dashboard__panel-title">
              <span>未处理预警</span>
              <small>安全库存、缺料、效期和呆滞</small>
            </div>
          </template>
          <ElTable :data="warnings" height="320" row-key="id" class="wms-dashboard__table">
            <ElTableColumn prop="warning_no" label="预警号" min-width="140" />
            <ElTableColumn prop="warning_type" label="类型" width="120" />
            <ElTableColumn prop="material_id" label="物料ID" width="90" />
            <ElTableColumn prop="current_qty" label="当前数" width="100" />
            <ElTableColumn prop="status" label="状态" width="90" />
          </ElTable>
        </ElCard>
      </ElCol>
    </ElRow>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { Refresh } from "@element-plus/icons-vue";
import {
  WmsDashboardAPI,
  type WmsDashboardFlow,
  type WmsDashboardStockStructure,
  type WmsDashboardSummary,
  type WmsDashboardTrendItem,
  type WmsDashboardWarning,
} from "@/api/module_wms/dashboard";
import WmsIntelligenceSummary from "@/views/module_wms/components/WmsIntelligenceSummary.vue";
import WmsIntelligenceAPI, { type WmsIntelligenceSummary as WmsIntelligenceSummaryData } from "@/api/module_wms/intelligence";

defineOptions({ name: "WmsDashboard", inheritAttrs: false });

const loading = ref(false);
const summary = ref<WmsDashboardSummary>();
const stockStructure = ref<WmsDashboardStockStructure>();
const trends = ref<WmsDashboardTrendItem[]>([]);
const warnings = ref<WmsDashboardWarning[]>([]);
const flows = ref<WmsDashboardFlow[]>([]);
const intelligenceSummary = ref<WmsIntelligenceSummaryData>();

const metricVisuals: Record<string, { icon: string; tone: string }> = {
  仓库: { icon: "ri:store-2-line", tone: "primary" },
  物料: { icon: "ri:box-3-line", tone: "success" },
  库存批次: { icon: "ri:archive-drawer-line", tone: "info" },
  待处理单据: { icon: "ri:file-list-3-line", tone: "warning" },
  未关闭预警: { icon: "ri:alarm-warning-line", tone: "danger" },
};

const metricCards = computed(() =>
  (summary.value?.metrics ?? []).map((metric) => ({
    ...metric,
    ...(metricVisuals[metric.label] ?? {
      icon: "ri:archive-line",
      tone: "primary",
    }),
  }))
);
const openWarningCount = computed(() => Number(metricCards.value.find((item) => item.label === "未关闭预警")?.value ?? 0));
const timelineTasks = computed(() =>
  (summary.value?.tasks ?? []).map((item) => ({
    time: item.time,
    content: item.title,
    code: item.status,
  }))
);
const stockBars = computed(() => {
  const structure = stockStructure.value ?? {
    available_qty: "0",
    locked_qty: "0",
    frozen_qty: "0",
    pending_qty: "0",
    defective_qty: "0",
  };
  const rows = [
    { label: "可用", value: Number(structure.available_qty), tone: "success" },
    { label: "锁定", value: Number(structure.locked_qty), tone: "info" },
    { label: "冻结", value: Number(structure.frozen_qty), tone: "warning" },
    { label: "待检", value: Number(structure.pending_qty), tone: "primary" },
    { label: "不良", value: Number(structure.defective_qty), tone: "danger" },
  ];
  const total = rows.reduce((sum, item) => sum + item.value, 0) || 1;
  return rows.map((item) => ({ ...item, percent: Math.round((item.value / total) * 100) }));
});
const trendBars = computed(() => {
  const max = Math.max(...trends.value.map((item) => Number(item.quantity)), 0) || 1;
  return trends.value.map((item) => ({ ...item, percent: Math.round((Number(item.quantity) / max) * 100) }));
});

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

async function loadDashboard() {
  loading.value = true;
  try {
    const [summaryResp, structureResp, trendResp, warningResp, flowResp, intelligenceResp] = await Promise.all([
      WmsDashboardAPI.summary(),
      WmsDashboardAPI.stockStructure(),
      WmsDashboardAPI.trends(),
      WmsDashboardAPI.warnings(),
      WmsDashboardAPI.latestFlows(),
      WmsIntelligenceAPI.dashboardSummary(),
    ]);
    summary.value = summaryResp.data.data;
    stockStructure.value = structureResp.data.data;
    trends.value = trendResp.data.data;
    warnings.value = warningResp.data.data;
    flows.value = flowResp.data.data;
    intelligenceSummary.value = intelligenceResp.data.data;
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void loadDashboard();
});
</script>

<style scoped lang="scss">
.wms-dashboard {
  --wms-surface: color-mix(in srgb, var(--el-bg-color) 92%, var(--el-color-primary) 8%);
  --wms-panel: color-mix(in srgb, var(--el-bg-color) 96%, var(--el-color-primary) 4%);
  --wms-panel-strong: color-mix(in srgb, var(--el-bg-color) 88%, var(--el-color-primary) 12%);
  --wms-border: color-mix(in srgb, var(--fa-card-border) 72%, var(--el-color-primary) 28%);
  --wms-muted: var(--el-text-color-secondary);
  --wms-track: color-mix(in srgb, var(--el-fill-color-light) 88%, var(--el-color-primary) 12%);

  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--el-color-primary-light-9) 45%, transparent), transparent 34%),
    var(--el-bg-color-page);
}

.wms-dashboard__hero {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 24px;
  overflow: hidden;
  padding: 22px 24px;
  background:
    linear-gradient(135deg, var(--wms-panel-strong), var(--el-bg-color) 58%),
    var(--el-bg-color);
  border: 1px solid var(--wms-border);
  border-radius: 8px;
  box-shadow: 0 16px 36px rgb(15 23 42 / 0.06);

  &::before {
    position: absolute;
    inset: 0 auto 0 0;
    width: 4px;
    content: "";
    background: linear-gradient(180deg, var(--el-color-primary), var(--el-color-success), var(--el-color-warning));
  }
}

.wms-dashboard__hero-main {
  min-width: 0;

  h1 {
    margin: 6px 0 8px;
    font-size: 28px;
    font-weight: 700;
    line-height: 1.2;
    color: var(--el-text-color-primary);
  }

  p {
    max-width: 720px;
    margin: 0;
    font-size: 14px;
    line-height: 1.7;
    color: var(--wms-muted);
  }
}

.wms-dashboard__eyebrow {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 700;
  color: var(--el-color-primary);
}

.wms-dashboard__pulse {
  width: 8px;
  height: 8px;
  background: var(--el-color-success);
  border-radius: 50%;
  box-shadow: 0 0 0 6px color-mix(in srgb, var(--el-color-success) 16%, transparent);
}

.wms-dashboard__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;

  span {
    padding: 5px 9px;
    font-size: 12px;
    color: var(--wms-muted);
    background: color-mix(in srgb, var(--el-bg-color) 82%, var(--el-color-primary) 18%);
    border: 1px solid color-mix(in srgb, var(--wms-border) 72%, transparent);
    border-radius: 6px;
  }
}

.wms-dashboard__hero-side {
  display: flex;
  gap: 12px;
  align-items: stretch;
}

.wms-dashboard__status-card {
  min-width: 168px;
  padding: 12px 14px;
  background: color-mix(in srgb, var(--el-bg-color) 84%, var(--el-color-success) 16%);
  border: 1px solid color-mix(in srgb, var(--el-color-success) 34%, var(--wms-border));
  border-radius: 8px;

  span {
    display: block;
    font-size: 12px;
    color: var(--wms-muted);
  }

  strong {
    display: block;
    margin-top: 4px;
    font-size: 18px;
    color: var(--el-text-color-primary);
  }

  p {
    margin: 4px 0 0;
    font-size: 12px;
    color: var(--wms-muted);
  }
}

.wms-dashboard__metrics {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
}

.wms-dashboard__metric {
  position: relative;
  display: flex;
  gap: 14px;
  min-height: 126px;
  padding: 18px;
  overflow: hidden;
  background: var(--wms-panel);
  border: 1px solid var(--wms-border);
  border-radius: 8px;
  transition:
    transform 0.2s ease,
    border-color 0.2s ease,
    box-shadow 0.2s ease;

  &::after {
    position: absolute;
    right: -34px;
    bottom: -42px;
    width: 104px;
    height: 104px;
    content: "";
    background: var(--metric-color);
    border-radius: 50%;
    opacity: 0.08;
  }

  &:hover {
    border-color: color-mix(in srgb, var(--metric-color) 42%, var(--wms-border));
    box-shadow: 0 14px 30px color-mix(in srgb, var(--metric-color) 10%, transparent);
    transform: translateY(-2px);
  }

  &.is-primary {
    --metric-color: var(--el-color-primary);
  }

  &.is-success {
    --metric-color: var(--el-color-success);
  }

  &.is-info {
    --metric-color: var(--el-color-info);
  }

  &.is-warning {
    --metric-color: var(--el-color-warning);
  }

  &.is-danger {
    --metric-color: var(--el-color-danger);
  }
}

.wms-dashboard__metric-icon {
  display: flex;
  flex: 0 0 44px;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  font-size: 22px;
  color: var(--metric-color);
  background: color-mix(in srgb, var(--metric-color) 12%, var(--el-bg-color));
  border: 1px solid color-mix(in srgb, var(--metric-color) 24%, transparent);
  border-radius: 8px;
}

.wms-dashboard__metric-body {
  min-width: 0;

  span {
    display: block;
    font-size: 13px;
    color: var(--wms-muted);
  }

  strong {
    display: block;
    margin-top: 6px;
    font-variant-numeric: tabular-nums;
    font-size: 30px;
    font-weight: 750;
    line-height: 1;
    color: var(--el-text-color-primary);
  }

  p {
    margin: 8px 0 0;
    font-size: 12px;
    color: var(--wms-muted);
  }
}

.wms-dashboard__panel {
  overflow: hidden;
  background: var(--wms-panel);
  border: 1px solid var(--wms-border);
  border-radius: 8px;

  :deep(.el-card__header) {
    padding: 15px 18px;
    background: color-mix(in srgb, var(--el-bg-color) 78%, var(--el-color-primary) 8%);
    border-bottom: 1px solid var(--wms-border);
  }

  :deep(.el-card__body) {
    padding: 18px;
  }
}

.wms-dashboard__panel-title {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;

  span {
    font-size: 15px;
    font-weight: 700;
    color: var(--el-text-color-primary);
  }

  small {
    font-size: 12px;
    color: var(--wms-muted);
  }
}

.wms-dashboard__bar {
  display: flex;
  flex-direction: column;
  gap: 8px;

  & + & {
    margin-top: 14px;
  }

  div {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 13px;
    color: var(--wms-muted);
  }

  strong {
    font-variant-numeric: tabular-nums;
    color: var(--el-text-color-primary);
  }
}

.wms-dashboard__track {
  height: 9px;
  overflow: hidden;
  background: var(--wms-track);
  border-radius: 999px;

  span {
    display: block;
    min-width: 4px;
    height: 100%;
    border-radius: inherit;
    transition: width 0.25s ease;

    &.success {
      background: var(--el-color-success);
    }

    &.info {
      background: var(--el-color-info);
    }

    &.warning {
      background: var(--el-color-warning);
    }

    &.primary,
    &.flow {
      background: var(--el-color-primary);
    }

    &.danger {
      background: var(--el-color-danger);
    }
  }
}

.wms-dashboard__task-panel {
  min-height: 100%;
}

.wms-dashboard__tasks {
  display: grid;
  gap: 12px;
}

.wms-dashboard__task {
  display: grid;
  grid-template-columns: 10px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
  padding: 12px;
  background: color-mix(in srgb, var(--el-bg-color) 76%, var(--el-color-primary) 6%);
  border: 1px solid color-mix(in srgb, var(--wms-border) 70%, transparent);
  border-radius: 8px;

  > span {
    width: 10px;
    height: 10px;
    margin-top: 5px;
    background: var(--el-color-info);
    border-radius: 50%;

    &.active {
      background: var(--el-color-primary);
      box-shadow: 0 0 0 5px color-mix(in srgb, var(--el-color-primary) 14%, transparent);
    }

    &.next {
      background: var(--el-color-warning);
    }
  }

  strong {
    display: block;
    overflow: hidden;
    font-size: 13px;
    font-weight: 650;
    color: var(--el-text-color-primary);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  p {
    margin: 4px 0 0;
    font-size: 12px;
    color: var(--wms-muted);
  }
}

.wms-dashboard__table {
  :deep(.el-table__header th) {
    color: var(--wms-muted);
    background: color-mix(in srgb, var(--el-bg-color) 82%, var(--el-color-primary) 6%);
  }

  :deep(.el-table__row:hover > td) {
    background: color-mix(in srgb, var(--el-color-primary-light-9) 56%, transparent);
  }
}

@media (max-width: 1280px) {
  .wms-dashboard__metrics {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .wms-dashboard__hero {
    grid-template-columns: 1fr;
  }

  .wms-dashboard__hero-side {
    flex-direction: column;
  }

  .wms-dashboard__metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .wms-dashboard {
    padding: 12px;
  }

  .wms-dashboard__hero {
    padding: 18px;
  }

  .wms-dashboard__metrics {
    grid-template-columns: 1fr;
  }
}
</style>
