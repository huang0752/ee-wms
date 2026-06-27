<template>
  <FaDrawer
    :model-value="modelValue"
    :title="title"
    size="760px"
    form-mode="detail"
    confirm-text="关闭"
    @update:model-value="$emit('update:modelValue', $event)"
    @confirm="$emit('update:modelValue', false)"
  >
    <div v-if="record" class="wms-document-drawer">
      <section class="wms-document-drawer__summary">
        <div>
          <span>{{ primaryLabel }}</span>
          <strong>{{ primaryValue }}</strong>
        </div>
        <WmsStatusTag :status="status" show-stage />
      </section>

      <ElProgress
        :percentage="statusMeta.progress"
        :status="progressStatus"
        :stroke-width="8"
        striped
        striped-flow
      />
      <p class="wms-document-drawer__status-text">{{ statusMeta.description }}</p>

      <ElTabs v-model="activeTab">
        <ElTabPane label="业务信息" name="base">
          <FaDescriptions :items="fields" :data="record" :column="2" :span="1" size="small" />
        </ElTabPane>
        <ElTabPane v-if="$slots.lines" label="明细" name="lines">
          <slot name="lines" />
        </ElTabPane>
        <ElTabPane v-if="$slots.flow" label="流程" name="flow">
          <slot name="flow" />
        </ElTabPane>
      </ElTabs>
    </div>
    <ElEmpty v-else description="暂无详情" />
  </FaDrawer>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import WmsStatusTag from "./WmsStatusTag.vue";
import { getWmsStatusMeta, type WmsDescriptionItem } from "./wmsOperations";

defineOptions({ name: "WmsDocumentDrawer" });

const props = withDefaults(
  defineProps<{
    modelValue: boolean;
    title: string;
    record?: Record<string, unknown> | null;
    fields: WmsDescriptionItem[];
    primaryLabel?: string;
    primaryProp?: string;
    statusProp?: string;
  }>(),
  {
    record: null,
    primaryLabel: "单据号",
    primaryProp: "order_no",
    statusProp: "status",
  }
);

defineEmits<{
  "update:modelValue": [value: boolean];
}>();

const activeTab = ref("base");

const status = computed(() => String(props.record?.[props.statusProp] ?? ""));
const statusMeta = computed(() => getWmsStatusMeta(status.value));
const progressStatus = computed<"" | "success" | "warning" | "exception">(() => {
  if (statusMeta.value.type === "success") return "success";
  if (statusMeta.value.type === "danger") return "exception";
  if (statusMeta.value.type === "warning") return "warning";
  return "";
});
const primaryValue = computed(() => String(props.record?.[props.primaryProp] ?? "-"));

watch(
  () => props.modelValue,
  (visible) => {
    if (visible) activeTab.value = "base";
  }
);
</script>

<style scoped>
.wms-document-drawer {
  display: grid;
  gap: 14px;
}

.wms-document-drawer__summary {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  padding: 14px;
  background: color-mix(in srgb, var(--el-color-primary-light-9) 46%, transparent);
  border: 1px solid color-mix(in srgb, var(--fa-card-border) 70%, transparent);
  border-radius: 8px;
}

.wms-document-drawer__summary div {
  display: grid;
  gap: 4px;
}

.wms-document-drawer__summary span,
.wms-document-drawer__status-text {
  color: var(--el-text-color-secondary);
}

.wms-document-drawer__summary strong {
  font-size: 18px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.wms-document-drawer__status-text {
  margin: -6px 0 0;
  line-height: 1.6;
}
</style>
