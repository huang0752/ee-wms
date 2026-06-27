<template>
  <div class="panel p1">
    <div class="panel-hd"><span class="dot purple" />待办作业闭环</div>
    <div class="funnel-list">
      <div v-for="(item, i) in data" :key="item.label" class="fn-item">
        <div class="fn-row">
          <span class="fn-idx" :style="{ background: colors[i] }">{{ i + 1 }}</span>
          <span class="fn-label">{{ item.label }}</span>
          <span class="fn-val">{{ item.value }}</span>
          <span class="fn-rate" :style="{ color: colors[i] }">占比 {{ item.rate }}%</span>
        </div>
        <div class="fn-bar-wrap">
          <div class="fn-bar" :style="{ width: item.pct + '%', background: colors[i] }" />
        </div>
      </div>
      <div v-if="data.length === 0" class="fn-empty">暂无待办任务</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

defineOptions({ name: "FunnelChart" });

interface DashboardTask {
  title: string;
  status: string;
  time: string;
}

const props = withDefaults(
  defineProps<{
    tasks?: DashboardTask[];
  }>(),
  {
    tasks: () => [],
  }
);

const colors = ["#00d4ff", "#7c3aed", "#10b981", "#f59e0b"];
const data = computed(() => {
  const values = props.tasks.slice(0, 4).map((item) => ({
    label: item.title.replace(/^处理/, "").slice(0, 6),
    rawValue: parseTaskValue(item.time),
  }));
  const max = Math.max(...values.map((item) => item.rawValue), 0);
  return values.map((item) => ({
    label: item.label,
    value: item.rawValue.toLocaleString(),
    rate: max ? Math.round((item.rawValue / max) * 100) : 0,
    pct: max ? (item.rawValue / max) * 100 : 0,
  }));
});

function parseTaskValue(value: string) {
  const match = value.match(/\d+(?:\.\d+)?/);
  return match ? Number(match[0]) : 0;
}
</script>

<style scoped>
.funnel-list {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 5px;
  justify-content: center;
}

.fn-item {
  padding: 2px 0;
}

.fn-row {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-bottom: 3px;
  font-size: 10px;
}

.fn-idx {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  font-size: 8px;
  font-weight: 700;
  color: #fff;
  border-radius: 3px;
}

.fn-label {
  flex-shrink: 0;
  width: 64px;
  opacity: 0.5;
}

.fn-val {
  flex: 1;
  font-variant-numeric: tabular-nums;
  text-align: right;
  opacity: 0.8;
}

.fn-rate {
  flex-shrink: 0;
  width: 54px;
  font-size: 9px;
  font-weight: 600;
  text-align: right;
}

.fn-bar-wrap {
  height: 3px;
  overflow: hidden;
  background: rgb(26 40 80 / 40%);
  border-radius: 2px;
}

.fn-bar {
  height: 100%;
  border-radius: 2px;
  transition: width 0.8s;
}

.fn-empty {
  display: grid;
  flex: 1;
  font-size: 12px;
  color: #94a3b8;
  place-items: center;
  opacity: 0.65;
}
</style>
