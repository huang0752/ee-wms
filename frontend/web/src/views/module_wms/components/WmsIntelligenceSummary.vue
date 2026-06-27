<template>
  <ElCard v-if="summary" shadow="never" class="wms-intelligence-summary">
    <template #header>
      <div class="wms-intelligence-summary__header">
        <div>
          <small>OPERATIONS INSIGHT</small>
          <span>{{ summary.title }}</span>
        </div>
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
  overflow: hidden;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--el-color-primary-light-9) 44%, transparent), transparent 48%),
    var(--el-bg-color);
  border: 1px solid color-mix(in srgb, var(--fa-card-border) 72%, var(--el-color-primary) 28%);
  border-radius: 8px;
}

.wms-intelligence-summary :deep(.el-card__header) {
  padding: 14px 18px;
  background: color-mix(in srgb, var(--el-bg-color) 82%, var(--el-color-primary) 8%);
  border-bottom: 1px solid color-mix(in srgb, var(--fa-card-border) 76%, var(--el-color-primary) 24%);
}

.wms-intelligence-summary :deep(.el-card__body) {
  padding: 18px;
}

.wms-intelligence-summary__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.wms-intelligence-summary__header div {
  display: grid;
  gap: 4px;
}

.wms-intelligence-summary__header small {
  font-size: 11px;
  font-weight: 700;
  color: var(--el-color-primary);
}

.wms-intelligence-summary__header span {
  font-size: 15px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.wms-intelligence-summary__text {
  margin: 0;
  color: var(--el-text-color-primary);
  line-height: 1.7;
}

.wms-intelligence-summary__bullets {
  display: grid;
  gap: 8px;
  margin-top: 14px;
}

.wms-intelligence-summary__bullet {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 10px 12px;
  color: var(--el-text-color-secondary);
  background: color-mix(in srgb, var(--el-bg-color) 78%, var(--el-color-primary) 6%);
  border: 1px solid color-mix(in srgb, var(--fa-card-border) 70%, transparent);
  border-radius: 8px;
}

.wms-intelligence-summary__bullet span {
  flex: 0 0 7px;
  width: 7px;
  height: 7px;
  margin-top: 8px;
  border-radius: 50%;
  background: var(--el-color-primary);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--el-color-primary) 12%, transparent);
}

.wms-intelligence-summary__bullet p {
  margin: 0;
  line-height: 1.6;
}
</style>
