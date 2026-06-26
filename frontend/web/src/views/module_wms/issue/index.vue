<template>
  <div class="wms-issue">
    <ElCard shadow="never" class="wms-issue__toolbar">
      <div class="wms-issue__toolbar-row">
        <ElInput v-model="keyword" clearable placeholder="领料单号" :prefix-icon="Search" @keyup.enter="refreshData" />
        <div class="wms-issue__actions">
          <ElButton :icon="Refresh" @click="refreshData" />
          <ElButton type="primary" :icon="Plus" @click="openCreate">新建领料</ElButton>
        </div>
      </div>
    </ElCard>
    <ElCard shadow="never" class="wms-issue__table">
      <ElTable v-loading="loading" :data="rows" row-key="id" height="calc(100vh - 310px)">
        <ElTableColumn prop="order_no" label="领料单号" min-width="150" />
        <ElTableColumn prop="work_order_no" label="工单号" min-width="130" />
        <ElTableColumn prop="warehouse_id" label="仓库ID" width="100" />
        <ElTableColumn prop="status" label="状态" width="140" />
        <ElTableColumn label="操作" width="340" fixed="right">
          <template #default="{ row }">
            <ElButton text type="primary" :disabled="row.status !== 'pending_reserve'" @click="runAction('reserve', row)">锁库</ElButton>
            <ElButton text :disabled="row.status !== 'reserved'" @click="runAction('pick', row)">拣货</ElButton>
            <ElButton text :disabled="row.status !== 'picked'" @click="runAction('review', row)">复核</ElButton>
            <ElButton text type="success" :disabled="row.status !== 'reviewed'" @click="runAction('confirm', row)">确认</ElButton>
            <ElButton text type="danger" :disabled="['confirmed', 'cancelled'].includes(row.status)" @click="runAction('cancel', row)">取消</ElButton>
            <ElButton text @click="loadLines(row)">明细</ElButton>
          </template>
        </ElTableColumn>
      </ElTable>
    </ElCard>

    <ElDialog v-model="createVisible" title="新建领料单" width="720px">
      <ElForm :model="form" label-width="96px">
        <ElRow :gutter="16">
          <ElCol :span="8"><ElFormItem label="单号"><ElInput v-model="form.order_no" placeholder="留空自动生成" /></ElFormItem></ElCol>
          <ElCol :span="8"><ElFormItem label="工单号"><ElInput v-model="form.work_order_no" /></ElFormItem></ElCol>
          <ElCol :span="8"><ElFormItem label="仓库ID"><ElInputNumber v-model="form.warehouse_id" :min="1" /></ElFormItem></ElCol>
        </ElRow>
        <ElTable :data="form.lines" border>
          <ElTableColumn label="物料ID" width="180"><template #default="{ row }"><ElInputNumber v-model="row.material_id" :min="1" /></template></ElTableColumn>
          <ElTableColumn label="需求数量" width="180"><template #default="{ row }"><ElInputNumber v-model="row.requested_qty" :min="0.0001" :precision="4" /></template></ElTableColumn>
          <ElTableColumn label="备注"><template #default="{ row }"><ElInput v-model="row.remark" /></template></ElTableColumn>
        </ElTable>
      </ElForm>
      <template #footer>
        <ElButton @click="createVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="submitting" @click="submitCreate">保存</ElButton>
      </template>
    </ElDialog>

    <ElDialog v-model="linesVisible" title="领料明细" width="820px">
      <ElTable :data="lineRows" border>
        <ElTableColumn prop="material_id" label="物料ID" width="100" />
        <ElTableColumn prop="batch_no" label="批次号" min-width="140" />
        <ElTableColumn prop="requested_qty" label="需求" width="100" />
        <ElTableColumn prop="locked_qty" label="锁定" width="100" />
        <ElTableColumn prop="shipped_qty" label="领用" width="100" />
        <ElTableColumn prop="stock_lock_id" label="锁库ID" width="100" />
        <ElTableColumn prop="status" label="状态" width="130" />
      </ElTable>
    </ElDialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { Plus, Refresh, Search } from "@element-plus/icons-vue";
import WmsIssueAPI, { type WmsIssueForm, type WmsIssueLine, type WmsIssueOrder } from "@/api/module_wms/issue";

defineOptions({ name: "WmsIssue", inheritAttrs: false });

type ActionName = "reserve" | "pick" | "review" | "confirm" | "cancel";

const keyword = ref("");
const loading = ref(false);
const submitting = ref(false);
const createVisible = ref(false);
const linesVisible = ref(false);
const rows = ref<WmsIssueOrder[]>([]);
const lineRows = ref<WmsIssueLine[]>([]);
const form = reactive<WmsIssueForm>({ external_source: "manual", lines: [{ material_id: undefined, requested_qty: 1 }] });

async function refreshData() {
  loading.value = true;
  try {
    const response = await WmsIssueAPI.list({ page_no: 1, page_size: 50, order_no: keyword.value || undefined });
    rows.value = response.data.data.items || [];
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  Object.assign(form, { order_no: "", work_order_no: "", warehouse_id: undefined, external_source: "manual", lines: [{ material_id: undefined, requested_qty: 1 }] });
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

async function loadLines(row: WmsIssueOrder) {
  const response = await WmsIssueAPI.lines(row.id!);
  lineRows.value = response.data.data;
  linesVisible.value = true;
}

onMounted(refreshData);
</script>

<style scoped>
.wms-issue { display: flex; flex-direction: column; gap: 12px; padding: 16px; }
.wms-issue__toolbar, .wms-issue__table { border-radius: 8px; }
.wms-issue__toolbar-row, .wms-issue__actions { display: flex; align-items: center; gap: 12px; }
.wms-issue__toolbar-row { justify-content: space-between; }
</style>
