<template>
  <div class="panel p1">
    <div class="panel-hd"><span class="dot green" />库存流水时段趋势</div>
    <div ref="chartRef" class="chart-box" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch } from "vue";
import * as echarts from "echarts";

defineOptions({ name: "ServiceLevel" });

interface FlowHourSeries {
  labels: string[];
  inbound: number[];
  outbound: number[];
}

const props = withDefaults(
  defineProps<{
    series?: FlowHourSeries;
  }>(),
  {
    series: () => ({ labels: [], inbound: [], outbound: [] }),
  }
);

const chartRef = ref<HTMLDivElement>();
let chart: echarts.ECharts | null = null;

const textStyle = { color: "#94a3b8" };
const hasData = computed(() => props.series.labels.length > 0);
const yMax = computed(() => {
  const max = Math.max(...props.series.inbound, ...props.series.outbound, 0);
  return Math.max(10, Math.ceil(max / 10) * 10);
});

function initChart(dom: HTMLDivElement) {
  chart = echarts.init(dom);
  chart.setOption({
    graphic: emptyGraphic(),
    grid: { top: 20, right: 25, bottom: 25, left: 45 },
    xAxis: {
      type: "category",
      data: props.series.labels,
      boundaryGap: false,
      axisLine: { lineStyle: { color: "#1a2050" } },
      axisLabel: { ...textStyle, rotate: 30 },
    },
    yAxis: {
      type: "value",
      name: "件",
      nameTextStyle: { color: "#94a3b8", fontSize: 10 },
      min: 0,
      max: yMax.value,
      splitLine: { lineStyle: { color: "#1a2050", type: "dashed" } },
      axisLabel: textStyle,
    },
    tooltip: {
      trigger: "axis" as const,
      valueFormatter: (v: any) => v + "件",
      backgroundColor: "#0f143c",
      borderColor: "#1a2050",
      textStyle: { color: "#e0e6ff" },
    },
    series: [
      {
        type: "line",
        smooth: true,
        symbol: "circle",
        symbolSize: 4,
        lineStyle: { color: "#10b981", width: 2 },
        itemStyle: { color: "#10b981" },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: "rgba(16,185,129,0.2)" },
            { offset: 1, color: "rgba(16,185,129,0)" },
          ]),
        },
        name: "入库",
        data: props.series.inbound,
      },
      {
        name: "出库",
        type: "line",
        smooth: true,
        symbol: "diamond",
        symbolSize: 3,
        lineStyle: { color: "#f59e0b", width: 1.5, type: "dashed" },
        itemStyle: { color: "#f59e0b" },
        data: props.series.outbound,
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
    xAxis: { data: props.series.labels },
    yAxis: { max: yMax.value },
    series: [{ data: props.series.inbound }, { data: props.series.outbound }],
  });
}

function emptyGraphic() {
  return hasData.value
    ? []
    : [
        {
          type: "text",
          left: "center",
          top: "middle",
          style: { text: "暂无库存流水", fill: "#94a3b8", fontSize: 12 },
        },
      ];
}

watch(() => props.series, syncChart, { deep: true });

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
