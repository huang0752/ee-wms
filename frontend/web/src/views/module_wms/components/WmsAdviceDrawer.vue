<template>
  <ElDrawer v-model="visible" title="智能建议" size="420px" destroy-on-close>
    <ElEmpty v-if="!advice" description="暂无建议" />
    <div v-else class="wms-advice">
      <div class="wms-advice__meta">
        <ElTag :type="advice.source === 'ai' ? 'primary' : 'info'" effect="plain">
          {{ advice.source === "ai" ? "AI 智能建议" : "规则建议" }}
        </ElTag>
        <ElTag :type="riskType" effect="plain">{{ riskText }}</ElTag>
      </div>
      <section>
        <h3>风险原因</h3>
        <p>{{ advice.reason }}</p>
      </section>
      <section>
        <h3>处理建议</h3>
        <p>{{ advice.advice }}</p>
      </section>
      <section v-if="advice.actions?.length">
        <h3>关联动作</h3>
        <div class="wms-advice__actions">
          <ElButton v-for="action in advice.actions" :key="action.label" plain>
            {{ action.label }}
          </ElButton>
        </div>
      </section>
    </div>
  </ElDrawer>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { WmsWarningAdvice } from "@/api/module_wms/intelligence";

defineOptions({ name: "WmsAdviceDrawer" });

const visible = defineModel<boolean>({ default: false });
const props = defineProps<{
  advice?: WmsWarningAdvice | null;
}>();

const riskType = computed(() => {
  if (props.advice?.risk_level === "critical") return "danger";
  if (props.advice?.risk_level === "warning") return "warning";
  return "success";
});

const riskText = computed(() => {
  if (props.advice?.risk_level === "critical") return "高风险";
  if (props.advice?.risk_level === "warning") return "需关注";
  return "正常";
});
</script>

<style scoped>
.wms-advice {
  display: grid;
  gap: 18px;
}

.wms-advice__meta,
.wms-advice__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.wms-advice h3 {
  margin: 0 0 8px;
  font-size: 14px;
  color: var(--el-text-color-primary);
}

.wms-advice p {
  margin: 0;
  line-height: 1.7;
  color: var(--el-text-color-regular);
}
</style>
