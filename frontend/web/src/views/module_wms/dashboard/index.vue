<template>
  <div class="wms-dashboard">
    <section class="wms-dashboard__header">
      <div>
        <h1>仓储驾驶舱</h1>
        <p>装配：{{ summary?.assembly || "wms" }} · 阶段：{{ summary?.phase || "v1-running-loop" }}</p>
      </div>
      <ElButton :loading="loading" :icon="Refresh" @click="loadDashboard">刷新</ElButton>
    </section>

    <WmsIntelligenceSummary :summary="intelligenceSummary" />

    <ElRow :gutter="16">
      <ElCol v-for="metric in metrics" :key="metric.label" :xs="24" :sm="12" :lg="6" class="mb-4">
        <FaStatsCard
          :title="metric.label"
          :count="Number(metric.value) || 0"
          :description="metric.unit ? `${metric.status} · ${metric.unit}` : metric.status"
          icon="ri:archive-line"
          icon-style="bg-primary"
        />
      </ElCol>
    </ElRow>

    <ElRow :gutter="16">
      <ElCol :xs="24" :lg="10" class="mb-4">
        <ElCard shadow="never" class="wms-dashboard__panel">
          <template #header>
            <span>库存结构</span>
          </template>
          <div v-for="item in stockBars" :key="item.label" class="wms-dashboard__bar">
            <div>
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
            <ElProgress :percentage="item.percent" :status="item.status" :stroke-width="10" />
          </div>
        </ElCard>
      </ElCol>

      <ElCol :xs="24" :lg="6" class="mb-4">
        <FaTimelineListCard
          title="阶段任务"
          subtitle="来自 WMS dashboard API"
          :list="timelineTasks"
          :max-count="5"
        />
      </ElCol>

      <ElCol :xs="24" :lg="8" class="mb-4">
        <ElCard shadow="never" class="wms-dashboard__panel">
          <template #header>
            <span>流水趋势</span>
          </template>
          <div v-for="item in trendBars" :key="item.flow_type" class="wms-dashboard__bar">
            <div>
              <span>{{ flowTypeText(item.flow_type) }}</span>
              <strong>{{ item.quantity }}</strong>
            </div>
            <ElProgress :percentage="item.percent" :stroke-width="10" />
          </div>
          <ElEmpty v-if="trendBars.length === 0" :image-size="80" description="暂无流水" />
        </ElCard>
      </ElCol>
    </ElRow>

    <ElRow :gutter="16">
      <ElCol :xs="24" :lg="14" class="mb-4">
        <ElCard shadow="never" class="wms-dashboard__panel">
          <template #header>
            <span>最新库存流水</span>
          </template>
          <ElTable :data="flows" height="320" row-key="id">
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
            <span>未处理预警</span>
          </template>
          <ElTable :data="warnings" height="320" row-key="id">
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

const metrics = computed(() => summary.value?.metrics ?? []);
const timelineTasks = computed(() =>
  (summary.value?.tasks ?? []).map((item) => ({
    time: item.time,
    status: item.status === "next" ? "var(--el-color-primary)" : "var(--el-color-info)",
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
    { label: "可用", value: Number(structure.available_qty), status: "success" as const },
    { label: "锁定", value: Number(structure.locked_qty), status: undefined },
    { label: "冻结", value: Number(structure.frozen_qty), status: "warning" as const },
    { label: "待检", value: Number(structure.pending_qty), status: undefined },
    { label: "不良", value: Number(structure.defective_qty), status: "exception" as const },
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
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
}

.wms-dashboard__header {
  display: flex;
  gap: 24px;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  background: var(--el-bg-color);

  h1 {
    margin: 0;
    font-size: 22px;
    line-height: 1.25;
    color: var(--el-text-color-primary);
  }

  p {
    margin: 6px 0 0;
    font-size: 14px;
    color: var(--el-text-color-secondary);
  }
}

.wms-dashboard__panel {
  border: 1px solid var(--fa-card-border);
  border-radius: 8px;
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
    color: var(--el-text-color-secondary);
  }

  strong {
    color: var(--el-text-color-primary);
  }
}
</style>
