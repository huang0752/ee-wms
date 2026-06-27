<template>
  <div class="panel p1">
    <div class="panel-hd"><span class="dot green" />库存健康结构</div>
    <div ref="chartRef" class="chart-box" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from "vue";
import * as echarts from "echarts";

defineOptions({ name: "UserProfile" });

const props = withDefaults(
  defineProps<{
    scores?: number[];
  }>(),
  {
    scores: () => [],
  }
);

const chartRef = ref<HTMLDivElement>();
let chart: echarts.ECharts | null = null;

const indicators = [
  { name: "可用占比", max: 100 },
  { name: "未锁定", max: 100 },
  { name: "未冻结", max: 100 },
  { name: "预警闭环", max: 100 },
  { name: "待检可控", max: 100 },
];

function initChart(dom: HTMLDivElement) {
  chart = echarts.init(dom);
  chart.setOption({
    legend: {
      bottom: 0,
      textStyle: { color: "#94a3b8", fontSize: 8 },
      itemWidth: 8,
      itemHeight: 8,
    },
    radar: {
      center: ["50%", "48%"],
      radius: "55%",
      indicator: indicators,
      axisName: { color: "#94a3b8", fontSize: 8 },
      splitArea: { areaStyle: { color: ["rgba(0,212,255,0.02)", "rgba(0,212,255,0.02)"] } },
      splitLine: { lineStyle: { color: "#1a2050" } },
      axisLine: { lineStyle: { color: "#1a2050" } },
    },
    series: [
      {
        type: "radar",
        symbol: "circle",
        symbolSize: 3,
        lineStyle: { color: "#00d4ff", width: 2 },
        areaStyle: { color: "rgba(0,212,255,0.12)" },
        itemStyle: { color: "#00d4ff" },
        data: [{ value: normalizedScores(), name: "实时库存" }],
      },
    ],
  });
}

function handleResize() {
  if (chart && !chart.isDisposed()) chart.resize();
}

function syncChart() {
  if (!chart || chart.isDisposed()) return;
  chart.setOption({ series: [{ data: [{ value: normalizedScores(), name: "实时库存" }] }] });
}

function normalizedScores() {
  return indicators.map((_, index) => Math.round(props.scores[index] ?? 0));
}

watch(() => props.scores, syncChart, { deep: true });

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
  window.addEventListener("resize", handleResize);
});

onUnmounted(() => {
  window.removeEventListener("resize", handleResize);
  chart?.dispose();
});
</script>

<style scoped>
.chart-box {
  flex: 1;
  width: 100%;
  min-height: 0;
}
</style>
