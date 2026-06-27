<template>
  <WmsWorkbenchShell
    title="入库上架作业台"
    description="承接 IQC 判定后的合格品和不良品入库，关注库位、库存状态、确认时间和来源同步。"
    eyebrow="INBOUND PUTAWAY"
    :metrics="metrics"
  >
    <template #actions>
      <ElButton :icon="Refresh" @click="refreshData">刷新</ElButton>
      <ElButton type="primary" :icon="Plus" @click="openCreate">从检验生成</ElButton>
    </template>

    <template #toolbar>
      <div class="wms-page-toolbar">
        <ElInput v-model="keyword" clearable placeholder="入库单号" :prefix-icon="Search" @keyup.enter="refreshData" />
        <ElSelect v-model="statusFilter" clearable placeholder="状态" @change="refreshData">
          <ElOption label="待确认" value="pending_confirm" />
          <ElOption label="已确认" value="confirmed" />
        </ElSelect>
      </div>
    </template>

    <ElTable v-loading="loading" :data="rows" row-key="id" height="calc(100vh - 390px)">
      <ElTableColumn prop="order_no" label="入库单号" min-width="160" fixed="left" />
      <ElTableColumn label="状态" width="130">
        <template #default="{ row }">
          <WmsStatusTag :status="row.status" />
        </template>
      </ElTableColumn>
      <ElTableColumn label="进度" min-width="160">
        <template #default="{ row }">
          <ElProgress :percentage="getWmsStatusMeta(row.status).progress" :stroke-width="7" />
        </template>
      </ElTableColumn>
      <ElTableColumn prop="inspection_task_id" label="检验任务ID" width="110" />
      <ElTableColumn prop="arrival_order_id" label="到货单ID" width="100" />
      <ElTableColumn prop="warehouse_id" label="仓库ID" width="90" />
      <ElTableColumn prop="location_id" label="默认库位ID" width="110" />
      <ElTableColumn label="来源/同步" min-width="160">
        <template #default="{ row }">
          <div class="wms-stack-cell">
            <span>{{ getSourceLabel(row.external_source) }}</span>
            <small>{{ getSyncLabel(row.sync_status) }}</small>
          </div>
        </template>
      </ElTableColumn>
      <ElTableColumn prop="external_no" label="外部单号" min-width="150" show-overflow-tooltip />
      <ElTableColumn prop="confirmed_time" label="确认时间" min-width="160" />
      <ElTableColumn label="操作" width="190" fixed="right">
        <template #default="{ row }">
          <ElButton text type="primary" :disabled="row.status !== 'pending_confirm'" @click="confirmInbound(row)">确认</ElButton>
          <ElButton text @click="openDetail(row)">详情</ElButton>
        </template>
      </ElTableColumn>
    </ElTable>

    <ElDialog v-model="createVisible" title="从检验任务生成入库单" width="560px">
      <ElForm :model="createForm" label-width="118px">
        <ElFormItem label="检验任务ID">
          <ElInputNumber v-model="createForm.task_id" :min="1" controls-position="right" />
        </ElFormItem>
        <ElFormItem label="默认入库库位">
          <ElInputNumber v-model="createForm.location_id" :min="1" controls-position="right" />
        </ElFormItem>
        <ElFormItem label="备注">
          <ElInput v-model="createForm.remark" type="textarea" :rows="3" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="createVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="submitting" @click="submitCreate">生成</ElButton>
      </template>
    </ElDialog>

    <WmsDocumentDrawer
      v-model="detailVisible"
      title="入库详情"
      :record="detailRecord"
      :fields="detailFields"
      primary-prop="order_no"
    >
      <template #lines>
        <ElTable :data="lineRows" border>
          <ElTableColumn prop="material_id" label="物料ID" width="90" />
          <ElTableColumn prop="warehouse_id" label="仓库ID" width="90" />
          <ElTableColumn prop="location_id" label="库位ID" width="90" />
          <ElTableColumn prop="batch_no" label="批次号" min-width="140" />
          <ElTableColumn prop="quantity" label="入库数量" width="100" />
          <ElTableColumn label="库存状态" width="120">
            <template #default="{ row }">
              <WmsStatusTag :status="row.stock_status" />
            </template>
          </ElTableColumn>
          <ElTableColumn label="行状态" width="120">
            <template #default="{ row }">
              <WmsStatusTag :status="row.status" />
            </template>
          </ElTableColumn>
          <ElTableColumn prop="remark" label="备注" min-width="160" show-overflow-tooltip />
        </ElTable>
      </template>
    </WmsDocumentDrawer>
  </WmsWorkbenchShell>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { Plus, Refresh, Search } from "@element-plus/icons-vue";
import WmsInboundAPI, { type WmsInboundLine, type WmsInboundOrder } from "@/api/module_wms/inbound";
import WmsDocumentDrawer from "@/views/module_wms/shared/WmsDocumentDrawer.vue";
import WmsStatusTag from "@/views/module_wms/shared/WmsStatusTag.vue";
import WmsWorkbenchShell from "@/views/module_wms/shared/WmsWorkbenchShell.vue";
import {
  buildDocumentMetrics,
  buildStaticMetric,
  formatNullable,
  getSourceLabel,
  getSyncLabel,
  getWmsStatusMeta,
  type WmsDescriptionItem,
} from "@/views/module_wms/shared/wmsOperations";

defineOptions({ name: "WmsInbound", inheritAttrs: false });

const keyword = ref("");
const statusFilter = ref("");
const loading = ref(false);
const submitting = ref(false);
const createVisible = ref(false);
const detailVisible = ref(false);
const rows = ref<WmsInboundOrder[]>([]);
const lineRows = ref<WmsInboundLine[]>([]);
const selectedRow = ref<WmsInboundOrder | null>(null);
const createForm = reactive<{ task_id?: number; location_id?: number; remark?: string }>({});

const metrics = computed(() => [
  buildStaticMetric("入库单", rows.value.length, "ri:inbox-archive-line", "primary", "张", "当前列表"),
  ...buildDocumentMetrics(rows.value, [
    { label: "待确认", statuses: ["pending_confirm"], icon: "ri:time-line" },
    { label: "已入库", statuses: ["confirmed"], icon: "ri:checkbox-circle-line" },
  ]),
  buildStaticMetric(
    "不良入库行",
    lineRows.value.filter((line) => line.stock_status === "defective").length,
    "ri:error-warning-line",
    "danger",
    "行",
    "当前详情"
  ),
]);

const detailRecord = computed(() =>
  selectedRow.value
    ? {
        ...selectedRow.value,
        source_label: getSourceLabel(selectedRow.value.external_source),
        sync_label: getSyncLabel(selectedRow.value.sync_status),
        external_no_display: formatNullable(selectedRow.value.external_no),
        workflow_display: formatNullable(selectedRow.value.workflow_instance_id),
      }
    : null
);
const detailFields: WmsDescriptionItem[] = [
  { label: "入库单号", prop: "order_no" },
  { label: "检验任务ID", prop: "inspection_task_id" },
  { label: "到货单ID", prop: "arrival_order_id" },
  { label: "仓库ID", prop: "warehouse_id" },
  { label: "默认库位", prop: "location_id" },
  { label: "来源", prop: "source_label" },
  { label: "外部单号", prop: "external_no_display" },
  { label: "同步状态", prop: "sync_label" },
  { label: "确认时间", prop: "confirmed_time" },
  { label: "流程实例", prop: "workflow_display" },
  { label: "备注", prop: "remark", span: 2 },
];

async function refreshData() {
  loading.value = true;
  try {
    const response = await WmsInboundAPI.list({
      page_no: 1,
      page_size: 100,
      order_no: keyword.value || undefined,
      status: statusFilter.value || undefined,
    });
    rows.value = response.data.data.items || [];
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  Object.assign(createForm, { task_id: undefined, location_id: undefined, remark: "" });
  createVisible.value = true;
}

async function submitCreate() {
  if (!createForm.task_id) return;
  submitting.value = true;
  try {
    await WmsInboundAPI.createFromInspection(createForm.task_id, {
      location_id: createForm.location_id,
      remark: createForm.remark,
    });
    ElMessage.success("生成成功");
    createVisible.value = false;
    await refreshData();
  } finally {
    submitting.value = false;
  }
}

async function confirmInbound(row: WmsInboundOrder) {
  await WmsInboundAPI.confirm(row.id!);
  ElMessage.success("确认成功");
  await refreshData();
}

async function openDetail(row: WmsInboundOrder) {
  selectedRow.value = row;
  const response = await WmsInboundAPI.lines(row.id!);
  lineRows.value = response.data.data;
  detailVisible.value = true;
}

onMounted(refreshData);
</script>

<style scoped>
.wms-page-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.wms-page-toolbar :deep(.el-input) {
  max-width: 260px;
}

.wms-page-toolbar :deep(.el-select) {
  width: 180px;
}

.wms-stack-cell {
  display: grid;
  gap: 2px;
}

.wms-stack-cell small {
  color: var(--el-text-color-secondary);
}
</style>
