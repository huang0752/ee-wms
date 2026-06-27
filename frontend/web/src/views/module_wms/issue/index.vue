<template>
  <WmsWorkbenchShell
    title="生产领料作业台"
    description="围绕 MES 工单需求组织锁库、拣货、复核、领用确认，优先暴露工单、缺料和同步信息。"
    eyebrow="MATERIAL ISSUE"
    :metrics="metrics"
    :metric-columns="5"
  >
    <template #actions>
      <ElButton :icon="Refresh" @click="refreshData">刷新</ElButton>
      <ElButton type="primary" :icon="Plus" @click="openCreate">新建领料</ElButton>
    </template>

    <template #toolbar>
      <div class="wms-page-toolbar">
        <ElInput v-model="keyword" clearable placeholder="领料单号" :prefix-icon="Search" @keyup.enter="refreshData" />
        <ElInput v-model="workOrderKeyword" clearable placeholder="生产工单号" @keyup.enter="refreshData" />
        <ElSelect v-model="statusFilter" clearable placeholder="状态" @change="refreshData">
          <ElOption v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
        </ElSelect>
      </div>
    </template>

    <ElTable v-loading="loading" :data="rows" row-key="id" height="calc(100vh - 390px)">
      <ElTableColumn prop="order_no" label="领料单号" min-width="160" fixed="left" />
      <ElTableColumn prop="work_order_no" label="生产工单" min-width="150" />
      <ElTableColumn label="作业状态" width="130">
        <template #default="{ row }">
          <WmsStatusTag :status="row.status" />
        </template>
      </ElTableColumn>
      <ElTableColumn label="进度" min-width="170">
        <template #default="{ row }">
          <ElProgress :percentage="getWmsStatusMeta(row.status).progress" :stroke-width="7" />
        </template>
      </ElTableColumn>
      <ElTableColumn prop="warehouse_id" label="仓库ID" width="90" />
      <ElTableColumn label="来源/同步" min-width="160">
        <template #default="{ row }">
          <div class="wms-stack-cell">
            <span>{{ getSourceLabel(row.external_source) }}</span>
            <small>{{ getSyncLabel(row.sync_status) }}</small>
          </div>
        </template>
      </ElTableColumn>
      <ElTableColumn prop="external_no" label="外部单号" min-width="150" show-overflow-tooltip />
      <ElTableColumn prop="picked_time" label="拣货时间" min-width="160" />
      <ElTableColumn prop="reviewed_time" label="复核时间" min-width="160" />
      <ElTableColumn prop="confirmed_time" label="确认时间" min-width="160" />
      <ElTableColumn label="操作" width="360" fixed="right">
        <template #default="{ row }">
          <ElButton text type="primary" :disabled="row.status !== 'pending_reserve'" @click="runAction('reserve', row)">锁库</ElButton>
          <ElButton text :disabled="row.status !== 'reserved'" @click="runAction('pick', row)">拣货</ElButton>
          <ElButton text :disabled="row.status !== 'picked'" @click="runAction('review', row)">复核</ElButton>
          <ElButton text type="success" :disabled="row.status !== 'reviewed'" @click="runAction('confirm', row)">确认</ElButton>
          <ElButton text type="danger" :disabled="['confirmed', 'cancelled'].includes(row.status)" @click="runAction('cancel', row)">取消</ElButton>
          <ElButton text @click="openDetail(row)">详情</ElButton>
        </template>
      </ElTableColumn>
    </ElTable>

    <ElDialog v-model="createVisible" title="新建生产领料单" width="820px">
      <ElForm :model="form" label-width="106px">
        <ElRow :gutter="16">
          <ElCol :span="8">
            <ElFormItem label="单号">
              <ElInput v-model="form.order_no" placeholder="留空自动生成" />
            </ElFormItem>
          </ElCol>
          <ElCol :span="8">
            <ElFormItem label="工单号">
              <ElInput v-model="form.work_order_no" placeholder="MES工单" />
            </ElFormItem>
          </ElCol>
          <ElCol :span="8">
            <ElFormItem label="仓库ID">
              <ElInputNumber v-model="form.warehouse_id" :min="1" controls-position="right" />
            </ElFormItem>
          </ElCol>
          <ElCol :span="8">
            <ElFormItem label="来源">
              <ElSelect v-model="form.external_source">
                <ElOption label="手工" value="manual" />
                <ElOption label="MES" value="mes" />
                <ElOption label="ERP" value="erp" />
              </ElSelect>
            </ElFormItem>
          </ElCol>
          <ElCol :span="8">
            <ElFormItem label="外部单号">
              <ElInput v-model="form.external_no" />
            </ElFormItem>
          </ElCol>
          <ElCol :span="8">
            <ElFormItem label="同步状态">
              <ElSelect v-model="form.sync_status">
                <ElOption label="无需同步" value="not_required" />
                <ElOption label="待同步" value="pending" />
              </ElSelect>
            </ElFormItem>
          </ElCol>
        </ElRow>
        <ElTable :data="form.lines" border>
          <ElTableColumn label="物料ID" width="170">
            <template #default="{ row }">
              <ElInputNumber v-model="row.material_id" :min="1" />
            </template>
          </ElTableColumn>
          <ElTableColumn label="需求数量" width="180">
            <template #default="{ row }">
              <ElInputNumber v-model="row.requested_qty" :min="0.0001" :precision="4" />
            </template>
          </ElTableColumn>
          <ElTableColumn label="备注">
            <template #default="{ row }">
              <ElInput v-model="row.remark" />
            </template>
          </ElTableColumn>
        </ElTable>
      </ElForm>
      <template #footer>
        <ElButton @click="createVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="submitting" @click="submitCreate">保存</ElButton>
      </template>
    </ElDialog>

    <WmsDocumentDrawer
      v-model="detailVisible"
      title="领料详情"
      :record="detailRecord"
      :fields="detailFields"
      primary-prop="order_no"
    >
      <template #lines>
        <ElTable :data="lineRows" border>
          <ElTableColumn prop="material_id" label="物料ID" width="90" />
          <ElTableColumn prop="batch_no" label="批次号" min-width="140" />
          <ElTableColumn prop="requested_qty" label="需求" width="90" />
          <ElTableColumn prop="locked_qty" label="锁定" width="90" />
          <ElTableColumn prop="shipped_qty" label="领用" width="90" />
          <ElTableColumn label="满足率" min-width="150">
            <template #default="{ row }">
              <ElProgress :percentage="getQuantityProgress(row.shipped_qty || row.locked_qty, row.requested_qty)" :stroke-width="7" />
            </template>
          </ElTableColumn>
          <ElTableColumn prop="stock_lock_id" label="锁库ID" width="90" />
          <ElTableColumn label="状态" width="110">
            <template #default="{ row }">
              <WmsStatusTag :status="row.status" />
            </template>
          </ElTableColumn>
        </ElTable>
      </template>
      <template #flow>
        <ElSteps :active="flowActiveStep" finish-status="success" simple>
          <ElStep title="锁库" />
          <ElStep title="拣货" />
          <ElStep title="复核" />
          <ElStep title="领用" />
        </ElSteps>
      </template>
    </WmsDocumentDrawer>
  </WmsWorkbenchShell>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { Plus, Refresh, Search } from "@element-plus/icons-vue";
import WmsIssueAPI, { type WmsIssueForm, type WmsIssueLine, type WmsIssueOrder } from "@/api/module_wms/issue";
import WmsDocumentDrawer from "@/views/module_wms/shared/WmsDocumentDrawer.vue";
import WmsStatusTag from "@/views/module_wms/shared/WmsStatusTag.vue";
import WmsWorkbenchShell from "@/views/module_wms/shared/WmsWorkbenchShell.vue";
import {
  buildDocumentMetrics,
  buildStaticMetric,
  formatNullable,
  getQuantityProgress,
  getSourceLabel,
  getSyncLabel,
  getWmsStatusMeta,
  type WmsDescriptionItem,
} from "@/views/module_wms/shared/wmsOperations";

defineOptions({ name: "WmsIssue", inheritAttrs: false });

type ActionName = "reserve" | "pick" | "review" | "confirm" | "cancel";

const statusOptions = [
  { label: "待锁库", value: "pending_reserve" },
  { label: "已锁库", value: "reserved" },
  { label: "已拣货", value: "picked" },
  { label: "已复核", value: "reviewed" },
  { label: "已确认", value: "confirmed" },
  { label: "已取消", value: "cancelled" },
];

const keyword = ref("");
const workOrderKeyword = ref("");
const statusFilter = ref("");
const loading = ref(false);
const submitting = ref(false);
const createVisible = ref(false);
const detailVisible = ref(false);
const rows = ref<WmsIssueOrder[]>([]);
const lineRows = ref<WmsIssueLine[]>([]);
const selectedRow = ref<WmsIssueOrder | null>(null);
const form = reactive<WmsIssueForm>({
  external_source: "manual",
  sync_status: "not_required",
  lines: [{ material_id: undefined, requested_qty: 1 }],
});

const metrics = computed(() => [
  buildStaticMetric("领料单", rows.value.length, "ri:file-list-3-line", "primary", "张", "当前列表"),
  ...buildDocumentMetrics(rows.value, [
    { label: "待锁库", statuses: ["pending_reserve"], icon: "ri:lock-line" },
    { label: "待拣货", statuses: ["reserved"], icon: "ri:hand-coin-line" },
    { label: "待复核", statuses: ["picked", "reviewed"], icon: "ri:shield-check-line" },
    { label: "已领用", statuses: ["confirmed"], icon: "ri:checkbox-circle-line" },
  ]),
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
  { label: "领料单号", prop: "order_no" },
  { label: "生产工单", prop: "work_order_no" },
  { label: "仓库ID", prop: "warehouse_id" },
  { label: "来源", prop: "source_label" },
  { label: "外部单号", prop: "external_no_display" },
  { label: "同步状态", prop: "sync_label" },
  { label: "拣货时间", prop: "picked_time" },
  { label: "复核时间", prop: "reviewed_time" },
  { label: "确认时间", prop: "confirmed_time" },
  { label: "流程实例", prop: "workflow_display" },
  { label: "备注", prop: "remark", span: 2 },
];
const flowActiveStep = computed(() => {
  const map: Record<string, number> = {
    pending_reserve: 0,
    reserved: 1,
    picked: 2,
    reviewed: 3,
    confirmed: 4,
  };
  return map[selectedRow.value?.status ?? ""] ?? 0;
});

async function refreshData() {
  loading.value = true;
  try {
    const response = await WmsIssueAPI.list({
      page_no: 1,
      page_size: 100,
      order_no: keyword.value || undefined,
      work_order_no: workOrderKeyword.value || undefined,
      status: statusFilter.value || undefined,
    });
    rows.value = response.data.data.items || [];
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  Object.assign(form, {
    order_no: "",
    work_order_no: "",
    warehouse_id: undefined,
    external_source: "manual",
    external_no: "",
    sync_status: "not_required",
    lines: [{ material_id: undefined, requested_qty: 1 }],
  });
  createVisible.value = true;
}

async function submitCreate() {
  submitting.value = true;
  try {
    await WmsIssueAPI.create(form);
    ElMessage.success("创建成功");
    createVisible.value = false;
    await refreshData();
  } finally {
    submitting.value = false;
  }
}

async function runAction(action: ActionName, row: WmsIssueOrder) {
  await WmsIssueAPI[action](row.id!);
  ElMessage.success("操作成功");
  await refreshData();
}

async function openDetail(row: WmsIssueOrder) {
  selectedRow.value = row;
  const response = await WmsIssueAPI.lines(row.id!);
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
  max-width: 240px;
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
