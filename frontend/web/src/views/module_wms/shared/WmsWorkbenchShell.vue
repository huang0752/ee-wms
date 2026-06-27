<template>
  <main class="wms-workbench">
    <section class="wms-workbench__head">
      <div>
        <span class="wms-workbench__eyebrow">{{ eyebrow }}</span>
        <h2>{{ title }}</h2>
        <p>{{ description }}</p>
      </div>
      <div class="wms-workbench__head-actions">
        <slot name="actions" />
      </div>
    </section>

    <WmsMetricStrip v-if="metrics.length" :metrics="metrics" :columns="metricColumns" />

    <ElCard shadow="never" class="wms-workbench__toolbar">
      <slot name="toolbar" />
    </ElCard>

    <ElCard shadow="never" class="wms-workbench__body">
      <slot />
    </ElCard>
  </main>
</template>

<script setup lang="ts">
import WmsMetricStrip from "./WmsMetricStrip.vue";
import type { WmsMetricCard } from "./wmsOperations";

defineOptions({ name: "WmsWorkbenchShell" });

withDefaults(
  defineProps<{
    title: string;
    description: string;
    eyebrow?: string;
    metrics?: WmsMetricCard[];
    metricColumns?: 3 | 4 | 5;
  }>(),
  {
    eyebrow: "WMS OPERATIONS",
    metrics: () => [],
    metricColumns: 4,
  }
);
</script>

<style scoped>
.wms-workbench {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 100%;
  padding: 16px;
}

.wms-workbench__head {
  display: flex;
  gap: 16px;
  align-items: flex-end;
  justify-content: space-between;
  padding: 18px;
  overflow: hidden;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--el-color-primary-light-9) 70%, transparent), transparent 42%),
    var(--el-bg-color);
  border: 1px solid color-mix(in srgb, var(--fa-card-border) 72%, var(--el-color-primary) 18%);
  border-radius: 8px;
}

.wms-workbench__eyebrow {
  display: inline-block;
  margin-bottom: 6px;
  font-size: 11px;
  font-weight: 700;
  color: var(--el-color-primary);
}

.wms-workbench__head h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  line-height: 1.2;
  color: var(--el-text-color-primary);
}

.wms-workbench__head p {
  max-width: 760px;
  margin: 8px 0 0;
  color: var(--el-text-color-secondary);
  line-height: 1.6;
}

.wms-workbench__head-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: flex-end;
}

.wms-workbench__toolbar,
.wms-workbench__body {
  border: 1px solid color-mix(in srgb, var(--fa-card-border) 76%, transparent);
  border-radius: 8px;
}

.wms-workbench__toolbar :deep(.el-card__body) {
  padding: 12px 14px;
}

.wms-workbench__body {
  flex: 1;
  min-height: 0;
}

.wms-workbench__body :deep(.el-card__body) {
  min-height: 0;
  padding: 0;
}

@media (width <= 768px) {
  .wms-workbench__head {
    align-items: stretch;
    flex-direction: column;
  }

  .wms-workbench__head-actions {
    justify-content: flex-start;
  }
}
</style>
