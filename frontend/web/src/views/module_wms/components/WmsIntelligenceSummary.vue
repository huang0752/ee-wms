<template>
  <ElCard v-if="summary" shadow="never" class="wms-intelligence-summary">
    <template #header>
      <div class="wms-intelligence-summary__header">
        <span>{{ summary.title }}</span>
        <ElTag :type="summary.source === 'ai' ? 'primary' : 'info'" effect="plain">
          {{ summary.source === "ai" ? "AI 摘要" : "规则摘要" }}
        </ElTag>
      </div>
    </template>
    <p class="wms-intelligence-summary__text">{{ summary.summary }}</p>
    <div v-if="summary.bullets?.length" class="wms-intelligence-summary__bullets">
      <div v-for="item in summary.bullets" :key="item" class="wms-intelligence-summary__bullet">
        <span />
        <p>{{ item }}</p>
      </div>
    </div>
  </ElCard>
</template>

<script setup lang="ts">
import type { WmsIntelligenceSummary } from "@/api/module_wms/intelligence";

defineOptions({ name: "WmsIntelligenceSummary" });

defineProps<{
  summary?: WmsIntelligenceSummary;
}>();
</script>

<style scoped>
.wms-intelligence-summary {
  border: 1px solid var(--fa-card-border);
  border-radius: 8px;
}

.wms-intelligence-summary__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-weight: 600;
}

.wms-intelligence-summary__text {
  margin: 0;
  color: var(--el-text-color-primary);
  line-height: 1.7;
}

.wms-intelligence-summary__bullets {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}

.wms-intelligence-summary__bullet {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  color: var(--el-text-color-secondary);
}

.wms-intelligence-summary__bullet span {
  flex: 0 0 6px;
  width: 6px;
  height: 6px;
  margin-top: 9px;
  border-radius: 50%;
  background: var(--el-color-primary);
}

.wms-intelligence-summary__bullet p {
  margin: 0;
  line-height: 1.6;
}
</style>
