<template>
  <div class="wms-dashboard">
    <section class="wms-dashboard__hero">
      <div>
        <p class="wms-dashboard__kicker">EE WMS</p>
        <h1>仓储驾驶舱</h1>
        <p>
          第一版先建立可运行产品壳和稳定库存内核。当前页面作为 WMS 业务入口，后续阶段会接入真实仓库、物料、库存和单据数据。
        </p>
      </div>
      <ElTag effect="plain" type="success">装配：{{ summary?.assembly || "wms" }}</ElTag>
    </section>

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
      <ElCol :xs="24" :lg="14" class="mb-4">
        <ElCard shadow="never" class="wms-dashboard__panel">
          <template #header>
            <div class="wms-dashboard__panel-title">
              <span>下一步建设</span>
              <ElButton :loading="loading" :icon="Refresh" text @click="loadSummary" />
            </div>
          </template>
          <ElTimeline>
            <ElTimelineItem
              v-for="item in nextSteps"
              :key="item"
              type="primary"
              placement="top"
            >
              {{ item }}
            </ElTimelineItem>
          </ElTimeline>
        </ElCard>
      </ElCol>

      <ElCol :xs="24" :lg="10" class="mb-4">
        <FaTimelineListCard
          title="阶段任务"
          subtitle="来自 WMS dashboard API"
          :list="timelineTasks"
          :max-count="5"
        />
      </ElCol>
    </ElRow>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { Refresh } from "@element-plus/icons-vue";
import { WmsDashboardAPI, type WmsDashboardSummary } from "@/api/module_wms/dashboard";

defineOptions({ name: "WmsDashboard", inheritAttrs: false });

const loading = ref(false);
const summary = ref<WmsDashboardSummary>();

const metrics = computed(() => summary.value?.metrics ?? []);
const nextSteps = computed(() => summary.value?.next_steps ?? []);
const timelineTasks = computed(() =>
  (summary.value?.tasks ?? []).map((item) => ({
    time: item.time,
    status: item.status === "next" ? "var(--el-color-primary)" : "var(--el-color-info)",
    content: item.title,
    code: item.status,
  }))
);

async function loadSummary() {
  loading.value = true;
  try {
    const response = await WmsDashboardAPI.summary();
    summary.value = response.data.data;
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void loadSummary();
});
</script>

<style scoped lang="scss">
.wms-dashboard {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.wms-dashboard__hero {
  display: flex;
  gap: 24px;
  align-items: flex-start;
  justify-content: space-between;
  padding: 24px;
  background: var(--el-bg-color);
  border: 1px solid var(--fa-card-border);
  border-radius: 8px;

  h1 {
    margin: 0;
    font-size: 28px;
    line-height: 1.25;
    color: var(--el-text-color-primary);
  }

  p {
    max-width: 780px;
    margin: 10px 0 0;
    font-size: 14px;
    line-height: 1.7;
    color: var(--el-text-color-secondary);
  }
}

.wms-dashboard__kicker {
  margin: 0 0 8px !important;
  font-size: 13px !important;
  font-weight: 700;
  color: var(--el-color-primary) !important;
}

.wms-dashboard__panel {
  border: 1px solid var(--fa-card-border);
  border-radius: 8px;
}

.wms-dashboard__panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}
</style>
