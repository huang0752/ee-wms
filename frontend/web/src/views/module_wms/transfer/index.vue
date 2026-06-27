<template>
  <WmsWorkbenchShell
    title="移库调拨作业台"
    description="管理跨仓、跨库位调拨，突出调出调入范围、批次数量和确认状态。"
    eyebrow="TRANSFER OPERATIONS"
    :metrics="metrics"
  >
    <template #actions>
      <ElButton :icon="Refresh" @click="refreshData">刷新</ElButton>
      <ElButton type="primary" :icon="Plus" @click="createVisible = true">新建调拨</ElButton>
    </template>
    <template #toolbar>
      <div class="wms-page-toolbar">
        <ElInput v-model="keyword" clearable placeholder="调拨单号" :prefix-icon="Search" @keyup.enter="refreshData" />
        <ElSelect v-model="statusFilter" clearable placeholder="状态" @change="refreshData">
          <ElOption label="草稿" value="draft" />
          <ElOption label="已确认" value="confirmed" />
        </ElSelect>
      </div>
    </template>

    <ElTable v-loading="loading" :data="rows" row-key="id" height="calc(100vh - 390px)">
      <ElTableColumn prop="order_no" label="调拨单号" min-width="160" fixed="left" />
      <ElTableColumn label="状态" width="120">
        <template #default="{ row }"><WmsStatusTag :status="row.status" /></template>
      </ElTableColumn>
      <ElTableColumn prop="from_warehouse_id" label="调出仓" width="100" />
      <ElTableColumn prop="to_warehouse_id" label="调入仓" width="100" />
      <ElTableColumn prop="confirmed_time" label="确认时间" min-width="160" />
      <ElTableColumn prop="remark" label="备注" min-width="180" show-overflow-tooltip />
      <ElTableColumn label="操作" width="170" fixed="right">
        <template #default="{ row }">
          <ElButton text type="primary" :disabled="row.status !== 'draft'" @click="confirm(row)">确认</ElButton>
          <ElButton text @click="openDetail(row)">详情</ElButton>
        </template>
      </ElTableColumn>
    </ElTable>

    <ElDialog v-model="createVisible" title="新建调拨单" width="820px">
      <ElForm :model="form" label-width="96px">
        <ElRow :gutter="16">
          <ElCol :span="8"><ElFormItem label="单号"><ElInput v-model="form.order_no" placeholder="留空自动生成" /></ElFormItem></ElCol>
          <ElCol :span="8"><ElFormItem label="调出仓"><ElInputNumber v-model="form.from_warehouse_id" :min="1" /></ElFormItem></ElCol>
          <ElCol :span="8"><ElFormItem label="调入仓"><ElInputNumber v-model="form.to_warehouse_id" :min="1" /></ElFormItem></ElCol>
        </ElRow>
        <ElTable :data="form.lines" border>
          <ElTableColumn label="物料ID" width="130"><template #default="{ row }"><ElInputNumber v-model="row.material_id" :min="1" /></template></ElTableColumn>
          <ElTableColumn label="调出库位" width="140"><template #default="{ row }"><ElInputNumber v-model="row.from_location_id" :min="1" /></template></ElTableColumn>
          <ElTableColumn label="调入库位" width="140"><template #default="{ row }"><ElInputNumber v-model="row.to_location_id" :min="1" /></template></ElTableColumn>
          <ElTableColumn label="批次"><template #default="{ row }"><ElInput v-model="row.batch_no" /></template></ElTableColumn>
          <ElTableColumn label="数量" width="150"><template #default="{ row }"><ElInputNumber v-model="row.quantity" :min="0.0001" :precision="4" /></template></ElTableColumn>
        </ElTable>
      </ElForm>
      <template #footer><ElButton @click="createVisible=false">取消</ElButton><ElButton type="primary" :loading="submitting" @click="submitCreate">保存</ElButton></template>
    </ElDialog>

    <WmsDocumentDrawer v-model="detailVisible" title="调拨详情" :record="selectedRow" :fields="detailFields" primary-prop="order_no">
      <template #lines>
        <ElTable :data="lineRows" border>
          <ElTableColumn prop="material_id" label="物料ID" width="90" />
          <ElTableColumn prop="from_location_id" label="调出库位" width="100" />
          <ElTableColumn prop="to_location_id" label="调入库位" width="100" />
          <ElTableColumn prop="batch_no" label="批次" min-width="140" />
          <ElTableColumn prop="quantity" label="数量" width="100" />
          <ElTableColumn label="状态" width="120"><template #default="{ row }"><WmsStatusTag :status="row.status" /></template></ElTableColumn>
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
import WmsTransferAPI, { type WmsTransferForm, type WmsTransferLine, type WmsTransferOrder } from "@/api/module_wms/transfer";
import WmsDocumentDrawer from "@/views/module_wms/shared/WmsDocumentDrawer.vue";
import WmsStatusTag from "@/views/module_wms/shared/WmsStatusTag.vue";
import WmsWorkbenchShell from "@/views/module_wms/shared/WmsWorkbenchShell.vue";
import { buildDocumentMetrics, buildStaticMetric, sumDecimalFields, type WmsDescriptionItem } from "@/views/module_wms/shared/wmsOperations";

defineOptions({ name: "WmsTransfer", inheritAttrs: false });

const keyword = ref("");
const statusFilter = ref("");
const loading = ref(false);
const submitting = ref(false);
const createVisible = ref(false);
const detailVisible = ref(false);
const rows = ref<WmsTransferOrder[]>([]);
const lineRows = ref<WmsTransferLine[]>([]);
const selectedRow = ref<WmsTransferOrder | null>(null);
const form = reactive<WmsTransferForm>({ lines: [{ quantity: 1 }] });

const metrics = computed(() => [
  buildStaticMetric("调拨单", rows.value.length, "ri:arrow-left-right-line", "primary", "张"),
  ...buildDocumentMetrics(rows.value, [
    { label: "待确认", statuses: ["draft"], icon: "ri:draft-line" },
    { label: "已确认", statuses: ["confirmed"], icon: "ri:checkbox-circle-line" },
  ]),
  buildStaticMetric("当前明细量", sumDecimalFields(lineRows.value, ["quantity"]), "ri:stack-line", "info"),
]);
const detailFields: WmsDescriptionItem[] = [
  { label: "调拨单号", prop: "order_no" },
  { label: "调出仓", prop: "from_warehouse_id" },
  { label: "调入仓", prop: "to_warehouse_id" },
  { label: "确认时间", prop: "confirmed_time" },
  { label: "备注", prop: "remark", span: 2 },
];

async function refreshData() {
  loading.value = true;
  try {
    const response = await WmsTransferAPI.list({ page_no: 1, page_size: 100, order_no: keyword.value || undefined, status: statusFilter.value || undefined });
    rows.value = response.data.data.items || [];
  } finally {
    loading.value = false;
  }
}

async function submitCreate() {
  submitting.value = true;
  try {
    await WmsTransferAPI.create(form);
    ElMessage.success("创建成功");
    createVisible.value = false;
    await refreshData();
  } finally {
    submitting.value = false;
  }
}

async function confirm(row: WmsTransferOrder) {
  await WmsTransferAPI.confirm(row.id!);
  ElMessage.success("确认成功");
  await refreshData();
}

async function openDetail(row: WmsTransferOrder) {
  selectedRow.value = row;
  const response = await WmsTransferAPI.lines(row.id!);
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
</style>
