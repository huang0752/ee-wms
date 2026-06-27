<template>
  <div class="panel p1">
    <div class="panel-hd"><span class="dot purple" />仓库流水分布</div>
    <div ref="chartRef" class="chart-box" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch } from "vue";
import * as echarts from "echarts";

defineOptions({ name: "TargetReality" });

interface BarItem {
  name: string;
  value: number;
}

const props = withDefaults(
  defineProps<{
    items?: BarItem[];
  }>(),
  {
    items: () => [],
  }
);

const chartRef = ref<HTMLDivElement>();
let chart: echarts.ECharts | null = null;

const textStyle = { color: "#94a3b8", fontSize: 10 };
const labels = computed(() => props.items.map((item) => item.name));
const values = computed(() => props.items.map((item) => item.value));
const xMax = computed(() => {
  const max = Math.max(...values.value, 0);
  return Math.max(10, Math.ceil(max / 10) * 10);
});

function initChart(dom: HTMLDivElement) {
  chart = echarts.init(dom);
  chart.setOption({
    graphic: emptyGraphic(),
    grid: { top: 5, right: 30, bottom: 10, left: 10, containLabel: true },
    xAxis: {
      type: "value",
      max: xMax.value,
      splitLine: { lineStyle: { color: "#1a2050" } },
      axisLabel: textStyle,
    },
    yAxis: {
      type: "category",
      data: labels.value,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: textStyle,
    },
    series: [
      {
        name: "流水数",
        type: "bar",
        barWidth: 8,
        itemStyle: { borderRadius: [0, 2, 2, 0], color: "#7c3aed" },
        data: values.value,
      },
    ],
  });
}

function handleResize() {
  if (chart && !chart.isDisposed()) chart.resize();
}

function syncChart() {
  if (!chart || chart.isDisposed()) return;
  chart.setOption({
    graphic: emptyGraphic(),
    xAxis: { max: xMax.value },
    yAxis: { data: labels.value },
    series: [{ data: values.value }],
  });
}

function emptyGraphic() {
  return props.items.length
    ? []
    : [
        {
          type: "text",
          left: "center",
          top: "middle",
          style: { text: "暂无仓库流水", fill: "#94a3b8", fontSize: 12 },
        },
      ];
}

watch(() => props.items, syncChart, { deep: true });

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
