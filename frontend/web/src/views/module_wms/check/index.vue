<template>
  <WmsWorkbenchShell
    title="库存盘点作业台"
    description="围绕账实差异进行盘点、审核和调账，明细展示系统数、实盘数与差异量。"
    eyebrow="STOCK CHECK"
    :metrics="metrics"
  >
    <template #actions>
      <ElButton :icon="Refresh" @click="refreshData">刷新</ElButton>
      <ElButton type="primary" :icon="Plus" @click="createVisible = true">新建盘点</ElButton>
    </template>
    <template #toolbar>
      <div class="wms-page-toolbar">
        <ElInput v-model="keyword" clearable placeholder="盘点单号" :prefix-icon="Search" @keyup.enter="refreshData" />
        <ElSelect v-model="statusFilter" clearable placeholder="状态" @change="refreshData">
          <ElOption label="草稿" value="draft" />
          <ElOption label="已审核" value="audited" />
        </ElSelect>
      </div>
    </template>

    <ElTable v-loading="loading" :data="rows" row-key="id" height="calc(100vh - 390px)">
      <ElTableColumn prop="order_no" label="盘点单号" min-width="160" fixed="left" />
      <ElTableColumn label="状态" width="120"><template #default="{ row }"><WmsStatusTag :status="row.status" /></template></ElTableColumn>
      <ElTableColumn prop="warehouse_id" label="仓库ID" width="100" />
      <ElTableColumn prop="audited_time" label="审核时间" min-width="160" />
      <ElTableColumn prop="remark" label="备注" min-width="180" show-overflow-tooltip />
      <ElTableColumn label="操作" width="170" fixed="right">
        <template #default="{ row }">
          <ElButton text type="primary" :disabled="row.status !== 'draft'" @click="audit(row)">审核</ElButton>
          <ElButton text @click="openDetail(row)">详情</ElButton>
        </template>
      </ElTableColumn>
    </ElTable>

    <ElDialog v-model="createVisible" title="新建盘点单" width="820px">
      <ElForm :model="form" label-width="96px">
        <ElRow :gutter="16">
          <ElCol :span="8"><ElFormItem label="单号"><ElInput v-model="form.order_no" placeholder="留空自动生成" /></ElFormItem></ElCol>
          <ElCol :span="8"><ElFormItem label="仓库ID"><ElInputNumber v-model="form.warehouse_id" :min="1" /></ElFormItem></ElCol>
          <ElCol :span="8"><ElFormItem label="备注"><ElInput v-model="form.remark" /></ElFormItem></ElCol>
        </ElRow>
        <ElTable :data="form.lines" border>
          <ElTableColumn label="物料ID"><template #default="{ row }"><ElInputNumber v-model="row.material_id" :min="1" /></template></ElTableColumn>
          <ElTableColumn label="库位ID"><template #default="{ row }"><ElInputNumber v-model="row.location_id" :min="1" /></template></ElTableColumn>
          <ElTableColumn label="批次"><template #default="{ row }"><ElInput v-model="row.batch_no" /></template></ElTableColumn>
          <ElTableColumn label="系统数"><template #default="{ row }"><ElInputNumber v-model="row.system_qty" :min="0" :precision="4" /></template></ElTableColumn>
          <ElTableColumn label="实盘数"><template #default="{ row }"><ElInputNumber v-model="row.counted_qty" :min="0" :precision="4" /></template></ElTableColumn>
        </ElTable>
      </ElForm>
      <template #footer><ElButton @click="createVisible=false">取消</ElButton><ElButton type="primary" :loading="submitting" @click="submitCreate">保存</ElButton></template>
    </ElDialog>

    <WmsDocumentDrawer v-model="detailVisible" title="盘点详情" :record="selectedRow" :fields="detailFields" primary-prop="order_no">
      <template #lines>
        <ElTable :data="lineRows" border>
          <ElTableColumn prop="material_id" label="物料ID" width="90" />
          <ElTableColumn prop="location_id" label="库位ID" width="90" />
          <ElTableColumn prop="batch_no" label="批次" min-width="140" />
          <ElTableColumn prop="system_qty" label="系统数" width="100" />
          <ElTableColumn prop="counted_qty" label="实盘数" width="100" />
          <ElTableColumn label="差异" width="110">
            <template #default="{ row }">
              <ElTag :type="Number(row.diff_qty) === 0 ? 'success' : 'danger'" effect="plain">{{ row.diff_qty }}</ElTag>
            </template>
          </ElTableColumn>
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
import WmsCheckAPI, { type WmsCheckForm, type WmsCheckLine, type WmsCheckOrder } from "@/api/module_wms/check";
import WmsDocumentDrawer from "@/views/module_wms/shared/WmsDocumentDrawer.vue";
import WmsStatusTag from "@/views/module_wms/shared/WmsStatusTag.vue";
import WmsWorkbenchShell from "@/views/module_wms/shared/WmsWorkbenchShell.vue";
import { buildDocumentMetrics, buildStaticMetric, sumDecimalFields, type WmsDescriptionItem } from "@/views/module_wms/shared/wmsOperations";

defineOptions({ name: "WmsCheck", inheritAttrs: false });

const keyword = ref("");
const statusFilter = ref("");
const loading = ref(false);
const submitting = ref(false);
const createVisible = ref(false);
const detailVisible = ref(false);
const rows = ref<WmsCheckOrder[]>([]);
const lineRows = ref<WmsCheckLine[]>([]);
const selectedRow = ref<WmsCheckOrder | null>(null);
const form = reactive<WmsCheckForm>({ lines: [{ system_qty: 0, counted_qty: 0 }] });

const metrics = computed(() => [
  buildStaticMetric("盘点单", rows.value.length, "ri:survey-line", "primary", "张"),
  ...buildDocumentMetrics(rows.value, [
    { label: "待审核", statuses: ["draft"], icon: "ri:draft-line" },
    { label: "已审核", statuses: ["audited"], icon: "ri:checkbox-circle-line" },
  ]),
  buildStaticMetric("当前差异", sumDecimalFields(lineRows.value, ["diff_qty"]), "ri:contrast-drop-line", "danger"),
]);
const detailFields: WmsDescriptionItem[] = [
  { label: "盘点单号", prop: "order_no" },
  { label: "仓库ID", prop: "warehouse_id" },
  { label: "审核时间", prop: "audited_time" },
  { label: "备注", prop: "remark", span: 2 },
];

async function refreshData() {
  loading.value = true;
  try {
    const response = await WmsCheckAPI.list({ page_no: 1, page_size: 100, order_no: keyword.value || undefined, status: statusFilter.value || undefined });
    rows.value = response.data.data.items || [];
  } finally {
    loading.value = false;
  }
}

async function submitCreate() {
  submitting.value = true;
  try {
    await WmsCheckAPI.create(form);
    ElMessage.success("创建成功");
    createVisible.value = false;
    await refreshData();
  } finally {
    submitting.value = false;
  }
}

async function audit(row: WmsCheckOrder) {
  await WmsCheckAPI.audit(row.id!);
  ElMessage.success("审核成功");
  await refreshData();
}

async function openDetail(row: WmsCheckOrder) {
  selectedRow.value = row;
  const response = await WmsCheckAPI.lines(row.id!);
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
