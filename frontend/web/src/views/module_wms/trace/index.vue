<template>
  <div class="wms-trace">
    <ElCard shadow="never">
      <ElForm :inline="true" :model="query" class="wms-trace__form">
        <ElFormItem label="批次号">
          <ElInput v-model="query.batch_no" clearable placeholder="输入库存批次号" />
        </ElFormItem>
        <ElFormItem label="方向">
          <ElSegmented v-model="query.direction" :options="directionOptions" />
        </ElFormItem>
        <ElFormItem label="物料ID">
          <ElInputNumber v-model="query.material_id" :min="1" controls-position="right" />
        </ElFormItem>
        <ElFormItem>
          <ElButton type="primary" :icon="Search" :loading="loading" @click="search">查询</ElButton>
        </ElFormItem>
      </ElForm>
    </ElCard>

    <ElRow :gutter="16">
      <ElCol :xs="24" :lg="8" class="mb-4">
        <ElCard shadow="never" class="wms-trace__panel">
          <template #header>
            <span>追溯节点</span>
          </template>
          <ElTimeline v-if="result?.nodes.length">
            <ElTimelineItem v-for="node in result.nodes" :key="`${node.node_type}-${node.node_no}`" type="primary">
              <strong>{{ node.node_no || "-" }}</strong>
              <p>{{ node.node_type }} · {{ node.relation_type || "direct" }}</p>
            </ElTimelineItem>
          </ElTimeline>
          <ElEmpty v-else :image-size="90" description="暂无节点" />
        </ElCard>
      </ElCol>

      <ElCol :xs="24" :lg="16" class="mb-4">
        <ElCard shadow="never" class="wms-trace__panel">
          <template #header>
            <div class="wms-trace__header">
              <span>库存流水</span>
              <ElTag v-if="result" effect="plain">{{ result.batch_no }} · {{ directionText(result.direction) }}</ElTag>
            </div>
          </template>
          <ElTable v-loading="loading" :data="result?.flows || []" height="520" row-key="id">
            <ElTableColumn prop="flow_no" label="流水号" min-width="160" />
            <ElTableColumn prop="flow_type" label="类型" width="150">
              <template #default="{ row }">{{ flowTypeText(row.flow_type) }}</template>
            </ElTableColumn>
            <ElTableColumn prop="direction" label="方向" width="90" />
            <ElTableColumn prop="quantity" label="数量" width="100" />
            <ElTableColumn prop="warehouse_id" label="仓库ID" width="100" />
            <ElTableColumn prop="document_no" label="单据号" min-width="150" />
          </ElTable>
        </ElCard>
      </ElCol>
    </ElRow>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { Search } from "@element-plus/icons-vue";
import WmsTraceAPI, { type WmsTraceResult } from "@/api/module_wms/trace";

defineOptions({ name: "WmsTrace", inheritAttrs: false });

const loading = ref(false);
const result = ref<WmsTraceResult>();
const query = reactive({
  batch_no: "",
  direction: "forward" as "forward" | "backward",
  material_id: undefined as number | undefined,
});
const directionOptions = [
  { label: "正向", value: "forward" },
  { label: "反向", value: "backward" },
];

function directionText(direction: string) {
  return direction === "backward" ? "反向追溯" : "正向追溯";
}

function flowTypeText(type: string) {
  const map: Record<string, string> = {
    receive_pending: "收货待检",
    approve_to_available: "检验合格",
    reject_to_defective: "检验不良",
    lock: "库存锁定",
    release_lock: "释放锁定",
    ship: "出库扣减",
    freeze: "冻结",
    unfreeze: "解冻",
    transfer_out: "调拨出库",
    transfer_in: "调拨入库",
    adjust_check: "盘点调整",
  };
  return map[type] ?? type;
}

async function search() {
  if (!query.batch_no.trim()) {
    ElMessage.warning("请输入批次号");
    return;
  }
  loading.value = true;
  try {
    const response = await WmsTraceAPI.batch({
      batch_no: query.batch_no.trim(),
      direction: query.direction,
      material_id: query.material_id,
    });
    result.value = response.data.data;
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped lang="scss">
.wms-trace {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
}

.wms-trace__form {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.wms-trace__panel {
  border: 1px solid var(--fa-card-border);
  border-radius: 8px;
}

.wms-trace__header {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
}

p {
  margin: 4px 0 0;
  color: var(--el-text-color-secondary);
}
</style>
