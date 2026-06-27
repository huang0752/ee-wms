<template>
  <span class="wms-status-tag">
    <FaStatusTag :label="meta.label" :type="meta.type" effect="plain" />
    <small v-if="showStage">{{ meta.stage }}</small>
  </span>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { getWmsStatusMeta } from "./wmsOperations";

defineOptions({ name: "WmsStatusTag" });

const props = withDefaults(
  defineProps<{
    status?: string | null;
    showStage?: boolean;
  }>(),
  {
    showStage: false,
  }
);

const meta = computed(() => getWmsStatusMeta(props.status));
</script>

<style scoped>
.wms-status-tag {
  display: inline-flex;
  gap: 8px;
  align-items: center;
  white-space: nowrap;
}

.wms-status-tag small {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
