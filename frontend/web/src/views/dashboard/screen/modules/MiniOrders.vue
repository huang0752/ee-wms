<template>
  <div class="mini-chart-panel">
    <div class="mc-hd">待处理单据</div>
    <div class="mc-value" style="color: #7c3aed">{{ displayValue }}</div>
    <div ref="chartRef" class="mc-chart" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch } from "vue";
import * as echarts from "echarts";

defineOptions({ name: "MiniOrders" });

const props = defineProps<{
  value?: number;
}>();

const chartRef = ref<HTMLDivElement>();
let chart: echarts.ECharts | null = null;
const val = ref(props.value ?? 0);
const displayValue = computed(() => Math.round(val.value).toLocaleString());

function initChart(dom: HTMLDivElement) {
  chart = echarts.init(dom);
  chart.setOption({
    tooltip: { show: false },
    series: [
      {
        type: "pie",
        radius: ["55%", "78%"],
        center: ["50%", "58%"],
        label: { show: false },
        itemStyle: { borderColor: "#060b24", borderWidth: 1 },
        data: [
          { value: val.value, name: "待处理", itemStyle: { color: "#7c3aed" } },
          { value: 0, name: "处理中", itemStyle: { color: "#a78bfa" } },
          { value: 0, name: "待复核", itemStyle: { color: "#1a2050" } },
        ],
      },
    ],
  });
}

function syncValue(value: number) {
  val.value = value;
  if (chart && !chart.isDisposed()) {
    chart.setOption({
      series: [
        {
          data: [
            { value },
            { value: 0 },
            { value: 0 },
          ],
        },
      ],
    });
  }
}

function tick() {
  if (!chart || chart.isDisposed()) return;
  syncValue(props.value ?? 0);
}

watch(
  () => props.value,
  (value) => {
    if (value !== undefined) syncValue(value);
  }
);

onMounted(() => {
  const el = chartRef.value;
  if (!el) return;

  const observer = new ResizeObserver((entries) => {
    const entry = entries[0];
    if (entry && entry.contentRect.width > 0 && entry.contentRect.height > 0) {
      observer.disconnect();
      initChart(el);
    }
  });
  observer.observe(el);
});
onUnmounted(() => {
  chart?.dispose();
});
</script>

<style scoped>
.mini-chart-panel {
  position: relative;
  display: flex;
  flex-direction: column;
  padding: 10px 12px;
  overflow: hidden;
  background: linear-gradient(180deg, rgb(0 30 80 / 55%) 0%, rgb(6 11 36 / 70%) 100%);
  border: 1px solid var(--border, rgb(0 180 255 / 12%));
  border-radius: 10px;
}

.mini-chart-panel::after {
  position: absolute;
  top: 4px;
  left: 4px;
  width: 6px;
  height: 6px;
  content: "";
  border-top: 1px solid rgb(124 58 237 / 40%);
  border-left: 1px solid rgb(124 58 237 / 40%);
}

.mc-hd {
  margin-bottom: 2px;
  font-size: 10px;
  opacity: 0.35;
}

.mc-value {
  margin-bottom: 0;
  font-size: 16px;
  font-weight: 700;
  line-height: 1;
}

.mc-chart {
  flex: 1;
  min-height: 0;
}
</style>
