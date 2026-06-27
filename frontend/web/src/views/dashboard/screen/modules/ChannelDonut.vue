<template>
  <div class="panel p1">
    <div class="panel-hd"><span class="dot accent" />库存状态占比</div>
    <div ref="chartRef" class="chart-box" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch } from "vue";
import * as echarts from "echarts";

defineOptions({ name: "ChannelDonut" });

interface DonutItem {
  name: string;
  value: number;
  color?: string;
}

const props = withDefaults(
  defineProps<{
    items?: DonutItem[];
  }>(),
  {
    items: () => [],
  }
);

const chartRef = ref<HTMLDivElement>();
let chart: echarts.ECharts | null = null;
const chartItems = computed(() => props.items);

function buildSeriesData() {
  return chartItems.value.map((item, index) => ({
    value: item.value,
    name: item.name,
    itemStyle: { color: item.color || ["#00d4ff", "#7c3aed", "#10b981", "#f59e0b", "#ef4444"][index % 5] },
  }));
}

function initChart(dom: HTMLDivElement) {
  chart = echarts.init(dom);
  chart.setOption({
    graphic: emptyGraphic(),
    tooltip: {
      trigger: "item" as const,
      backgroundColor: "#0f143c",
      borderColor: "#1a2050",
      textStyle: { color: "#e0e6ff", fontSize: 10 },
      formatter: "{b}: {c} ({d}%)",
    },
    legend: {
      bottom: 0,
      textStyle: { color: "#94a3b8", fontSize: 9 },
      itemWidth: 8,
      itemHeight: 8,
    },
    series: [
      {
        type: "pie",
        radius: ["50%", "70%"],
        center: ["50%", "45%"],
        label: { show: false },
        emphasis: {
          scaleSize: 6,
          label: { show: true, fontSize: 10, color: "#94a3b8", formatter: "{b}\n{d}%" },
        },
        itemStyle: { borderColor: "#060b24", borderWidth: 2 },
        data: buildSeriesData(),
      },
    ],
  });
}

function handleResize() {
  if (chart && !chart.isDisposed()) chart.resize();
}

function tick() {
  if (!chart || chart.isDisposed()) return;
  chart.setOption({ graphic: emptyGraphic(), series: [{ data: buildSeriesData() }] });
}

function emptyGraphic() {
  return chartItems.value.length
    ? []
    : [
        {
          type: "text",
          left: "center",
          top: "middle",
          style: { text: "暂无库存结构", fill: "#94a3b8", fontSize: 12 },
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
