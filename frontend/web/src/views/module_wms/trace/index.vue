<template>
  <WmsWorkbenchShell
    title="批次追溯图谱"
    description="围绕批次号查询入库、检验、冻结、调拨、盘点和出库流水，形成可审计的正反向追溯路径。"
    eyebrow="WMS TRACEABILITY"
    :metrics="metrics"
  >
    <template #actions>
      <ElButton type="primary" :icon="Search" :loading="loading" @click="search">查询追溯</ElButton>
    </template>

    <template #toolbar>
      <ElForm :inline="true" :model="query" class="wms-trace__form">
        <ElFormItem label="批次号">
          <ElInput v-model="query.batch_no" clearable placeholder="输入库存批次号" @keyup.enter="search" />
        </ElFormItem>
        <ElFormItem label="方向">
          <ElSegmented v-model="query.direction" :options="directionOptions" />
        </ElFormItem>
        <ElFormItem label="物料ID">
          <ElInputNumber v-model="query.material_id" :min="1" controls-position="right" />
        </ElFormItem>
      </ElForm>
    </template>

    <div class="wms-trace__content">
      <aside class="wms-trace__graph">
        <header>
          <span>追溯路径</span>
          <ElTag v-if="result" effect="plain">{{ result.batch_no }} · {{ directionText(result.direction) }}</ElTag>
        </header>
        <ElTimeline v-if="traceNodes.length">
          <ElTimelineItem
            v-for="node in traceNodes"
            :key="`${node.node_type}-${node.node_no}`"
            :type="nodeTone(node.node_type)"
            :timestamp="node.relation_type || 'direct'"
          >
            <strong>{{ node.node_no || "-" }}</strong>
            <p>{{ nodeTypeText(node.node_type) }}</p>
          </ElTimelineItem>
        </ElTimeline>
        <ElEmpty v-else :image-size="90" description="输入批次号后生成路径" />
      </aside>

      <section class="wms-trace__ledger">
        <div class="wms-trace__summary">
          <article v-for="item in flowGroups" :key="item.type">
            <span>{{ item.label }}</span>
            <strong>{{ item.count }}</strong>
          </article>
        </div>
        <ElTable v-loading="loading" :data="result?.flows || []" height="calc(100vh - 492px)" row-key="id">
          <ElTableColumn prop="flow_no" label="流水号" min-width="160" fixed="left" show-overflow-tooltip />
          <ElTableColumn label="业务类型" min-width="150">
            <template #default="{ row }">
              <ElTag effect="plain">{{ flowTypeText(row.flow_type) }}</ElTag>
            </template>
          </ElTableColumn>
          <ElTableColumn label="方向" width="90">
            <template #default="{ row }">
              <ElTag :type="row.direction === 'out' ? 'warning' : 'success'" effect="plain">
                {{ row.direction === "out" ? "出" : "入" }}
              </ElTag>
            </template>
          </ElTableColumn>
          <ElTableColumn prop="quantity" label="数量" width="110" />
          <ElTableColumn prop="warehouse_id" label="仓库ID" width="100" />
          <ElTableColumn prop="location_id" label="库位ID" width="100" />
          <ElTableColumn prop="document_no" label="单据号" min-width="150" show-overflow-tooltip />
          <ElTableColumn prop="created_time" label="发生时间" min-width="170" show-overflow-tooltip />
        </ElTable>
      </section>
    </div>
  </WmsWorkbenchShell>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { Search } from "@element-plus/icons-vue";
import WmsTraceAPI, { type WmsTraceNode, type WmsTraceResult } from "@/api/module_wms/trace";
import WmsWorkbenchShell from "@/views/module_wms/shared/WmsWorkbenchShell.vue";
import {
  buildStaticMetric,
  getFlowTypeLabel,
  type WmsMetricCard,
} from "@/views/module_wms/shared/wmsOperations";

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

const traceNodes = computed(() => result.value?.nodes || []);
const flowGroups = computed(() => {
  const flows = result.value?.flows || [];
  const groups = new Map<string, number>();
  flows.forEach((flow) => {
    groups.set(flow.flow_type, (groups.get(flow.flow_type) || 0) + 1);
  });
  return Array.from(groups.entries()).map(([type, count]) => ({ type, label: flowTypeText(type), count }));
});
const metrics = computed<WmsMetricCard[]>(() => {
  const flows = result.value?.flows || [];
  const inQty = flows.filter((flow) => flow.direction !== "out").length;
  const outQty = flows.filter((flow) => flow.direction === "out").length;
  return [
    buildStaticMetric("追溯节点", traceNodes.value.length, { icon: "i-ep-share" }),
    buildStaticMetric("流水记录", flows.length, { icon: "i-ep-tickets" }),
    buildStaticMetric("入向动作", inQty, { icon: "i-ep-download", tone: "success" }),
    buildStaticMetric("出向动作", outQty, { icon: "i-ep-upload", tone: outQty ? "warning" : "info" }),
  ];
});

function directionText(direction: string) {
  return direction === "backward" ? "反向追溯" : "正向追溯";
}

function nodeTypeText(type: string) {
  const map: Record<string, string> = {
    arrival: "到货",
    inspection: "检验",
    inbound: "入库",
    outbound: "销售出库",
    issue: "领料出库",
    transfer: "调拨",
    check: "盘点",
    stock_flow: "库存流水",
  };
  return map[type] ?? type;
}

function nodeTone(type: string): "primary" | "success" | "warning" | "danger" | "info" {
  if (["inbound", "inspection"].includes(type)) return "success";
  if (["outbound", "issue"].includes(type)) return "warning";
  if (type === "check") return "danger";
  return "primary";
}

function flowTypeText(type: string) {
  const localMap: Record<string, string> = {
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
  return localMap[type] ?? getFlowTypeLabel(type);
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
.wms-trace__form {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.wms-trace__form :deep(.el-form-item) {
  margin-bottom: 0;
}

.wms-trace__content {
  display: grid;
  grid-template-columns: 330px minmax(0, 1fr);
  min-height: 0;
}

.wms-trace__graph {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px;
  border-right: 1px solid color-mix(in srgb, var(--fa-card-border) 76%, transparent);
}

.wms-trace__graph header {
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
}

.wms-trace__graph header span {
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.wms-trace__graph p {
  margin: 4px 0 0;
  color: var(--el-text-color-secondary);
}

.wms-trace__ledger {
  min-width: 0;
}

.wms-trace__summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  padding: 14px;
  border-bottom: 1px solid color-mix(in srgb, var(--fa-card-border) 76%, transparent);
}

.wms-trace__summary article {
  display: grid;
  gap: 4px;
  padding: 10px 12px;
  background: var(--el-fill-color-extra-light);
  border-radius: 8px;
}

.wms-trace__summary span {
  overflow: hidden;
  color: var(--el-text-color-secondary);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.wms-trace__summary strong {
  font-size: 22px;
  color: var(--el-text-color-primary);
}

@media (width <= 1100px) {
  .wms-trace__content {
    grid-template-columns: 1fr;
  }

  .wms-trace__graph {
    border-right: 0;
    border-bottom: 1px solid color-mix(in srgb, var(--fa-card-border) 76%, transparent);
  }
}
</style>
