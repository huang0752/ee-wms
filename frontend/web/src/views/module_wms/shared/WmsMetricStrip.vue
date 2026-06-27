<template>
  <section class="wms-metric-strip" :class="`cols-${columns}`">
    <article v-for="metric in metrics" :key="metric.label" class="wms-metric-card" :class="`is-${metric.tone}`">
      <div class="wms-metric-card__icon">
        <FaSvgIcon :icon="metric.icon" />
      </div>
      <div class="wms-metric-card__body">
        <span>{{ metric.label }}</span>
        <strong>{{ metric.value }}<small v-if="metric.unit">{{ metric.unit }}</small></strong>
        <p v-if="metric.hint">{{ metric.hint }}</p>
      </div>
    </article>
  </section>
</template>

<script setup lang="ts">
import type { WmsMetricCard } from "./wmsOperations";

defineOptions({ name: "WmsMetricStrip" });

withDefaults(
  defineProps<{
    metrics: WmsMetricCard[];
    columns?: 3 | 4 | 5;
  }>(),
  {
    columns: 4,
  }
);
</script>

<style scoped>
.wms-metric-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.wms-metric-strip.cols-3 {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.wms-metric-strip.cols-5 {
  grid-template-columns: repeat(5, minmax(0, 1fr));
}

.wms-metric-card {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 12px;
  min-height: 86px;
  padding: 14px;
  overflow: hidden;
  background: var(--el-bg-color);
  border: 1px solid color-mix(in srgb, var(--fa-card-border) 76%, transparent);
  border-radius: 8px;
}

.wms-metric-card__icon {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  font-size: 21px;
  color: var(--el-color-primary);
  background: color-mix(in srgb, var(--el-color-primary-light-9) 78%, transparent);
  border-radius: 8px;
}

.wms-metric-card__body {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.wms-metric-card__body span,
.wms-metric-card__body p {
  overflow: hidden;
  color: var(--el-text-color-secondary);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.wms-metric-card__body span {
  font-size: 12px;
}

.wms-metric-card__body strong {
  font-size: 24px;
  font-variant-numeric: tabular-nums;
  font-weight: 700;
  line-height: 1.1;
  color: var(--el-text-color-primary);
}

.wms-metric-card__body small {
  margin-left: 4px;
  font-size: 12px;
  font-weight: 500;
  color: var(--el-text-color-secondary);
}

.wms-metric-card__body p {
  margin: 0;
  font-size: 12px;
}

.wms-metric-card.is-success .wms-metric-card__icon {
  color: var(--el-color-success);
  background: color-mix(in srgb, var(--el-color-success-light-9) 78%, transparent);
}

.wms-metric-card.is-warning .wms-metric-card__icon {
  color: var(--el-color-warning);
  background: color-mix(in srgb, var(--el-color-warning-light-9) 78%, transparent);
}

.wms-metric-card.is-danger .wms-metric-card__icon {
  color: var(--el-color-danger);
  background: color-mix(in srgb, var(--el-color-danger-light-9) 78%, transparent);
}

.wms-metric-card.is-info .wms-metric-card__icon {
  color: var(--el-color-info);
  background: color-mix(in srgb, var(--el-color-info-light-9) 78%, transparent);
}

@media (width <= 1200px) {
  .wms-metric-strip,
  .wms-metric-strip.cols-5 {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (width <= 720px) {
  .wms-metric-strip,
  .wms-metric-strip.cols-3,
  .wms-metric-strip.cols-5 {
    grid-template-columns: 1fr;
  }
}
</style>
