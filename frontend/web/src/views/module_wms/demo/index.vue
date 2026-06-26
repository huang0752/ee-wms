<template>
  <div class="wms-demo">
    <ElCard shadow="never" class="wms-demo__panel">
      <template #header>
        <span>试用数据初始化</span>
      </template>
      <ElForm :model="form.profile" label-width="96px" class="wms-demo__form">
        <ElFormItem label="企业名称">
          <ElInput v-model="form.profile.company_name" maxlength="128" />
        </ElFormItem>
        <ElFormItem label="行业">
          <ElInput v-model="form.profile.industry" maxlength="64" />
        </ElFormItem>
        <ElFormItem label="场景">
          <ElSelect v-model="form.profile.scenario">
            <ElOption label="第一版标准样例" value="starter" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="仓库数">
          <ElInputNumber v-model="form.profile.warehouse_count" :min="1" :max="3" />
        </ElFormItem>
        <ElFormItem label="物料数">
          <ElInputNumber v-model="form.profile.material_count" :min="1" :max="20" />
        </ElFormItem>
        <ElFormItem>
          <ElButton type="primary" :icon="Plus" :loading="initializing" @click="initDemo">初始化</ElButton>
        </ElFormItem>
      </ElForm>
    </ElCard>

    <ElCard shadow="never" class="wms-demo__panel">
      <template #header>
        <span>批次结果</span>
      </template>
      <ElDescriptions v-if="latestBatch" :column="2" border>
        <ElDescriptionsItem label="批次号">{{ latestBatch.demo_batch_id }}</ElDescriptionsItem>
        <ElDescriptionsItem label="任务ID">{{ latestBatch.task_id }}</ElDescriptionsItem>
        <ElDescriptionsItem label="场景">{{ latestBatch.scenario }}</ElDescriptionsItem>
        <ElDescriptionsItem label="模块">{{ latestBatch.module }}</ElDescriptionsItem>
      </ElDescriptions>
      <ElEmpty v-else :image-size="90" description="暂无初始化结果" />

      <ElDivider />
      <ElSpace wrap>
        <ElInput v-model="cleanBatchId" clearable placeholder="输入试用批次号" class="wms-demo__batch-input" />
        <ElButton type="danger" plain :icon="Delete" :loading="cleaning" @click="cleanDemo">清理批次</ElButton>
      </ElSpace>
    </ElCard>

    <ElRow :gutter="16">
      <ElCol :xs="24" :lg="12">
        <ElCard shadow="never" class="wms-demo__panel">
          <template #header>
            <span>生成摘要</span>
          </template>
          <ElTimeline v-if="latestBatch?.summary.length">
            <ElTimelineItem v-for="item in latestBatch.summary" :key="item" type="success">
              {{ item }}
            </ElTimelineItem>
          </ElTimeline>
          <ElEmpty v-else :image-size="80" description="暂无摘要" />
        </ElCard>
      </ElCol>
      <ElCol :xs="24" :lg="12">
        <ElCard shadow="never" class="wms-demo__panel">
          <template #header>
            <span>数据计数</span>
          </template>
          <ElTable :data="countRows" height="260">
            <ElTableColumn prop="name" label="对象" />
            <ElTableColumn prop="count" label="数量" width="120" />
          </ElTable>
        </ElCard>
      </ElCol>
    </ElRow>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Delete, Plus } from "@element-plus/icons-vue";
import WmsDemoAPI, { type WmsDemoBatch, type WmsDemoInitForm } from "@/api/module_wms/demo";

defineOptions({ name: "WmsDemo", inheritAttrs: false });

const initializing = ref(false);
const cleaning = ref(false);
const latestBatch = ref<WmsDemoBatch>();
const cleanBatchId = ref("");
const form = reactive<WmsDemoInitForm>({
  profile: {
    company_name: "华南智能制造有限公司",
    industry: "智能制造",
    warehouse_count: 1,
    material_count: 3,
    scenario: "starter",
  },
});
const countRows = computed(() =>
  Object.entries(latestBatch.value?.counts ?? {}).map(([name, count]) => ({
    name,
    count,
  }))
);

async function initDemo() {
  initializing.value = true;
  try {
    const response = await WmsDemoAPI.init(form);
    latestBatch.value = response.data.data;
    cleanBatchId.value = latestBatch.value.demo_batch_id;
    ElMessage.success("试用数据已初始化");
  } finally {
    initializing.value = false;
  }
}

async function cleanDemo() {
  const batchId = cleanBatchId.value.trim();
  if (!batchId) {
    ElMessage.warning("请输入试用批次号");
    return;
  }
  await ElMessageBox.confirm(`确认清理批次 ${batchId} 的试用数据？`, "清理确认", { type: "warning" });
  cleaning.value = true;
  try {
    const response = await WmsDemoAPI.clean(batchId);
    ElMessage.success(`已清理 ${Object.values(response.data.data.counts).reduce((sum, item) => sum + item, 0)} 条试用数据`);
    if (latestBatch.value?.demo_batch_id === batchId) {
      latestBatch.value = undefined;
    }
  } finally {
    cleaning.value = false;
  }
}
</script>

<style scoped lang="scss">
.wms-demo {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
}

.wms-demo__panel {
  border: 1px solid var(--fa-card-border);
  border-radius: 8px;
}

.wms-demo__form {
  max-width: 720px;
}

.wms-demo__batch-input {
  width: 320px;
}
</style>
