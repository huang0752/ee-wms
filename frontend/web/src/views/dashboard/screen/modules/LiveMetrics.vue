<template>
  <div class="panel p1">
    <div class="panel-hd"><span class="dot warn" />仓储运行健康</div>
    <div class="metric-list">
      <div v-for="m in displayMetrics" :key="m.label" class="metric-row">
        <div class="mr-label">{{ m.label }}</div>
        <div class="mr-value" :style="{ color: m.color }">
          {{ m.value }}<span class="mr-unit">{{ m.unit }}</span>
        </div>
        <div class="mr-bar-wrap">
          <div ref="barRefs" class="mr-bar" :style="{ width: m.pct + '%', background: m.color }" />
        </div>
      </div>
      <div v-if="displayMetrics.length === 0" class="metric-empty">暂无运行指标</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

defineOptions({ name: "LiveMetrics" });

interface DashboardMetric {
  label: string;
  value: number | string;
  unit?: string | null;
  status: string;
}

const props = withDefaults(
  defineProps<{
    metrics?: DashboardMetric[];
  }>(),
  {
    metrics: () => [],
  }
);

const colors = ["#00d4ff", "#7c3aed", "#10b981", "#f59e0b", "#ef4444"];
const displayMetrics = computed(() => {
  const rows = props.metrics.slice(0, 4);
  const max = Math.max(...rows.map((item) => toNumber(item.value)), 0);
  return rows.map((item, index) => ({
    label: item.label,
    value: formatValue(item.value),
    unit: item.unit || "",
    color: item.status === "warning" ? "#ef4444" : colors[index % colors.length],
    pct: max ? Math.max(4, (toNumber(item.value) / max) * 100) : 0,
  }));
});

function toNumber(value: unknown) {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function formatValue(value: number | string) {
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value);
  return n >= 10000 ? `${(n / 10000).toFixed(1)}万` : n.toLocaleString();
}
</script>

<style scoped>
.metric-list {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 4px;
  justify-content: center;
}

.metric-row {
  padding: 2px 0;
}

.mr-label {
  margin-bottom: 2px;
  font-size: 10px;
  opacity: 0.35;
}

.mr-value {
  margin-bottom: 3px;
  font-size: 18px;
  font-weight: 700;
  line-height: 1;
}

.mr-unit {
  margin-left: 2px;
  font-size: 10px;
  font-weight: 400;
  opacity: 0.4;
}

.mr-bar-wrap {
  height: 2px;
  overflow: hidden;
  background: rgb(26 40 80 / 40%);
  border-radius: 1px;
}

.mr-bar {
  height: 100%;
  border-radius: 1px;
  transition: width 0.8s;
}

.metric-empty {
  display: grid;
  flex: 1;
  font-size: 12px;
  color: #94a3b8;
  place-items: center;
  opacity: 0.65;
}
</style>
