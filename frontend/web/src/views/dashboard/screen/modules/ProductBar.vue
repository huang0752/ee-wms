<template>
  <div class="panel p1">
    <div class="panel-hd"><span class="dot green" />库存流水排行 TOP6</div>
    <div ref="chartRef" class="chart-box" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch } from "vue";
import * as echarts from "echarts";

defineOptions({ name: "ProductBar" });

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
const chartItems = computed(() => props.items.slice(0, 6));
const textStyle = { color: "#94a3b8", fontSize: 10 };

function labels() {
  return chartItems.value.map((item) => item.name);
}

function values() {
  return chartItems.value.map((item) => item.value);
}

function initChart(dom: HTMLDivElement) {
  chart = echarts.init(dom);
  chart.setOption({
    graphic: emptyGraphic(),
    grid: { top: 5, right: 40, bottom: 10, left: 10, containLabel: true },
    xAxis: { type: "value", splitLine: { lineStyle: { color: "#1a2050" } }, axisLabel: textStyle },
    yAxis: {
      type: "category",
      data: labels(),
      inverse: true,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { ...textStyle, width: 64, overflow: "truncate" },
    },
    series: [
      {
        type: "bar",
        barWidth: 10,
        itemStyle: {
          borderRadius: [0, 3, 3, 0],
          color: (p: any) =>
            ["#00d4ff", "#7c3aed", "#10b981", "#f59e0b", "#ef4444", "#ec4899"][p.dataIndex % 6],
        },
        label: {
          show: true,
          position: "right",
          color: "#94a3b8",
          fontSize: 10,
          formatter: "{c}",
        },
        data: values(),
      },
    ],
  });
}

function handleResize() {
  if (chart && !chart.isDisposed()) chart.resize();
}

function tick() {
  if (!chart || chart.isDisposed()) return;
  chart.setOption({ graphic: emptyGraphic(), yAxis: { data: labels() }, series: [{ data: values() }] });
}

function emptyGraphic() {
  return chartItems.value.length
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

watch(
  () => props.items,
  () => {
    if (chart && !chart.isDisposed()) {
      tick();
    }
  },
  { deep: true }
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
