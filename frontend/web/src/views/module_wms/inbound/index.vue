<template>
  <div class="wms-inbound">
    <ElCard shadow="never" class="wms-inbound__toolbar">
      <div class="wms-inbound__toolbar-row">
        <ElInput v-model="keyword" clearable placeholder="入库单号" :prefix-icon="Search" @keyup.enter="refreshData" />
        <div class="wms-inbound__actions">
          <ElButton :icon="Refresh" @click="refreshData" />
          <ElButton type="primary" :icon="Plus" @click="openCreate">从检验生成</ElButton>
        </div>
      </div>
    </ElCard>

    <ElCard shadow="never" class="wms-inbound__table">
      <ElTable v-loading="loading" :data="rows" row-key="id" height="calc(100vh - 310px)">
        <ElTableColumn prop="order_no" label="入库单号" min-width="150" />
        <ElTableColumn prop="inspection_task_id" label="检验任务ID" width="120" />
        <ElTableColumn prop="warehouse_id" label="仓库ID" width="100" />
        <ElTableColumn prop="location_id" label="库位ID" width="100" />
        <ElTableColumn prop="status" label="状态" width="140" />
        <ElTableColumn prop="confirmed_time" label="确认时间" min-width="170" />
        <ElTableColumn label="操作" width="190" fixed="right">
          <template #default="{ row }">
            <ElButton text type="primary" :disabled="row.status !== 'pending_confirm'" @click="confirmInbound(row)">确认</ElButton>
            <ElButton text @click="loadLines(row)">明细</ElButton>
          </template>
        </ElTableColumn>
      </ElTable>
    </ElCard>

    <ElDialog v-model="createVisible" title="从检验任务生成入库单" width="520px">
      <ElForm :model="createForm" label-width="110px">
        <ElFormItem label="检验任务ID">
          <ElInputNumber v-model="createForm.task_id" :min="1" controls-position="right" />
        </ElFormItem>
        <ElFormItem label="入库库位ID">
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

    <ElDialog v-model="linesVisible" title="入库明细" width="760px">
      <ElTable :data="lineRows" border>
        <ElTableColumn prop="material_id" label="物料ID" width="100" />
        <ElTableColumn prop="warehouse_id" label="仓库ID" width="100" />
        <ElTableColumn prop="location_id" label="库位ID" width="100" />
        <ElTableColumn prop="batch_no" label="批次号" min-width="140" />
        <ElTableColumn prop="quantity" label="数量" width="110" />
        <ElTableColumn prop="stock_status" label="库存状态" width="130" />
        <ElTableColumn prop="status" label="状态" width="130" />
      </ElTable>
    </ElDialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { Plus, Refresh, Search } from "@element-plus/icons-vue";
import WmsInboundAPI, { type WmsInboundLine, type WmsInboundOrder } from "@/api/module_wms/inbound";

defineOptions({ name: "WmsInbound", inheritAttrs: false });

const keyword = ref("");
const loading = ref(false);
const submitting = ref(false);
const createVisible = ref(false);
const linesVisible = ref(false);
const rows = ref<WmsInboundOrder[]>([]);
const lineRows = ref<WmsInboundLine[]>([]);
const createForm = reactive({
  task_id: undefined as number | undefined,
  location_id: undefined as number | undefined,
  remark: "",
});

async function refreshData() {
  loading.value = true;
  try {
    const response = await WmsInboundAPI.list({ page_no: 1, page_size: 50, order_no: keyword.value || undefined });
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

async function loadLines(row: WmsInboundOrder) {
  const response = await WmsInboundAPI.lines(row.id!);
  lineRows.value = response.data.data;
  linesVisible.value = true;
}

onMounted(refreshData);
</script>

<style scoped>
.wms-inbound {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
}

.wms-inbound__toolbar,
.wms-inbound__table {
  border-radius: 8px;
}

.wms-inbound__toolbar-row,
.wms-inbound__actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.wms-inbound__toolbar-row {
  justify-content: space-between;
}
</style>
