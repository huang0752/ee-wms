<template>
  <div class="wms-arrival">
    <ElCard shadow="never" class="wms-arrival__toolbar">
      <div class="wms-arrival__toolbar-row">
        <ElSegmented v-model="activeTab" :options="tabOptions" />
        <div class="wms-arrival__actions">
          <ElInput v-model="keyword" clearable placeholder="单号" :prefix-icon="Search" @keyup.enter="refreshData" />
          <ElButton :icon="Refresh" @click="refreshData" />
          <ElButton v-if="activeTab === 'arrival'" type="primary" :icon="Plus" @click="openCreate">新建到货</ElButton>
        </div>
      </div>
    </ElCard>

    <ElCard v-if="activeTab === 'arrival'" shadow="never" class="wms-arrival__table">
      <ElTable v-loading="loading" :data="arrivalRows" row-key="id" height="calc(100vh - 310px)">
        <ElTableColumn prop="order_no" label="到货单号" min-width="150" />
        <ElTableColumn prop="supplier_id" label="供应商ID" width="110" />
        <ElTableColumn prop="warehouse_id" label="仓库ID" width="100" />
        <ElTableColumn prop="status" label="状态" width="150" />
        <ElTableColumn prop="external_source" label="来源" width="100" />
        <ElTableColumn label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <ElButton text type="primary" :disabled="row.status !== 'pending_receive'" @click="receiveArrival(row)">收货</ElButton>
            <ElButton text @click="loadArrivalLines(row)">明细</ElButton>
          </template>
        </ElTableColumn>
      </ElTable>
    </ElCard>

    <ElCard v-else shadow="never" class="wms-arrival__table">
      <ElTable v-loading="loading" :data="inspectionRows" row-key="id" height="calc(100vh - 310px)">
        <ElTableColumn prop="task_no" label="检验任务号" min-width="150" />
        <ElTableColumn prop="arrival_no" label="到货单号" min-width="150" />
        <ElTableColumn prop="status" label="状态" width="150" />
        <ElTableColumn prop="result" label="结果" width="100" />
        <ElTableColumn label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <ElButton text type="primary" :disabled="row.status !== 'pending_inspection'" @click="openJudge(row)">判定</ElButton>
            <ElButton text @click="loadInspectionLines(row)">明细</ElButton>
          </template>
        </ElTableColumn>
      </ElTable>
    </ElCard>

    <ElDialog v-model="createVisible" title="新建到货单" width="720px" destroy-on-close>
      <ElForm ref="createFormRef" :model="arrivalForm" :rules="arrivalRules" label-width="96px">
        <ElRow :gutter="16">
          <ElCol :span="8">
            <ElFormItem label="单号">
              <ElInput v-model="arrivalForm.order_no" placeholder="留空自动生成" />
            </ElFormItem>
          </ElCol>
          <ElCol :span="8">
            <ElFormItem label="供应商ID">
              <ElInputNumber v-model="arrivalForm.supplier_id" :min="1" controls-position="right" />
            </ElFormItem>
          </ElCol>
          <ElCol :span="8">
            <ElFormItem label="仓库ID" prop="warehouse_id">
              <ElInputNumber v-model="arrivalForm.warehouse_id" :min="1" controls-position="right" />
            </ElFormItem>
          </ElCol>
        </ElRow>
        <ElTable :data="arrivalForm.lines" border>
          <ElTableColumn label="物料ID" width="150">
            <template #default="{ row }">
              <ElInputNumber v-model="row.material_id" :min="1" controls-position="right" />
            </template>
          </ElTableColumn>
          <ElTableColumn label="数量" width="150">
            <template #default="{ row }">
              <ElInputNumber v-model="row.planned_qty" :min="0.0001" :precision="4" controls-position="right" />
            </template>
          </ElTableColumn>
          <ElTableColumn label="批次号">
            <template #default="{ row }">
              <ElInput v-model="row.batch_no" />
            </template>
          </ElTableColumn>
        </ElTable>
      </ElForm>
      <template #footer>
        <ElButton @click="createVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="submitting" @click="submitArrival">保存</ElButton>
      </template>
    </ElDialog>

    <ElDialog v-model="judgeVisible" title="检验判定" width="720px" destroy-on-close>
      <ElTable :data="judgeForm.lines" border>
        <ElTableColumn prop="line_id" label="明细ID" width="90" />
        <ElTableColumn label="合格数" width="160">
          <template #default="{ row }">
            <ElInputNumber v-model="row.accepted_qty" :min="0" :precision="4" controls-position="right" />
          </template>
        </ElTableColumn>
        <ElTableColumn label="不合格数" width="160">
          <template #default="{ row }">
            <ElInputNumber v-model="row.rejected_qty" :min="0" :precision="4" controls-position="right" />
          </template>
        </ElTableColumn>
        <ElTableColumn prop="result" label="结果" />
      </ElTable>
      <template #footer>
        <ElButton @click="judgeVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="submitting" @click="submitJudge">提交判定</ElButton>
      </template>
    </ElDialog>

    <ElDialog v-model="linesVisible" title="明细" width="760px">
      <ElTable :data="detailRows" border>
        <ElTableColumn prop="material_id" label="物料ID" width="100" />
        <ElTableColumn prop="batch_no" label="批次号" min-width="140" />
        <ElTableColumn prop="planned_qty" label="计划" width="100" />
        <ElTableColumn prop="quantity" label="检验数" width="100" />
        <ElTableColumn prop="accepted_qty" label="合格" width="100" />
        <ElTableColumn prop="rejected_qty" label="不合格" width="100" />
        <ElTableColumn prop="status" label="状态" width="140" />
      </ElTable>
    </ElDialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from "vue";
import { ElMessage, type FormInstance, type FormRules } from "element-plus";
import { Plus, Refresh, Search } from "@element-plus/icons-vue";
import WmsArrivalAPI, { type WmsArrivalForm, type WmsArrivalLine, type WmsArrivalOrder } from "@/api/module_wms/arrival";
import WmsInspectionAPI, {
  type WmsInspectionJudgeForm,
  type WmsInspectionLine,
  type WmsInspectionTask,
} from "@/api/module_wms/inspection";

defineOptions({ name: "WmsArrival", inheritAttrs: false });

type ActiveTab = "arrival" | "inspection";
const tabOptions: Array<{ label: string; value: ActiveTab }> = [
  { label: "到货单", value: "arrival" },
  { label: "检验任务", value: "inspection" },
];

const activeTab = ref<ActiveTab>("arrival");
const keyword = ref("");
const loading = ref(false);
const submitting = ref(false);
const createVisible = ref(false);
const judgeVisible = ref(false);
const linesVisible = ref(false);
const createFormRef = ref<FormInstance>();
const arrivalRows = ref<WmsArrivalOrder[]>([]);
const inspectionRows = ref<WmsInspectionTask[]>([]);
const detailRows = ref<Array<WmsArrivalLine | WmsInspectionLine>>([]);
const currentTaskId = ref<number>();

const arrivalForm = reactive<WmsArrivalForm>({
  warehouse_id: undefined,
  supplier_id: undefined,
  external_source: "manual",
  lines: [{ material_id: undefined, planned_qty: 1, batch_no: "" }],
});

const judgeForm = reactive<WmsInspectionJudgeForm>({ lines: [] });

const arrivalRules: FormRules = {
  warehouse_id: [{ required: true, message: "请输入仓库ID", trigger: "blur" }],
};

async function refreshData() {
  loading.value = true;
  try {
    if (activeTab.value === "arrival") {
      const response = await WmsArrivalAPI.list({ page_no: 1, page_size: 50, order_no: keyword.value || undefined });
      arrivalRows.value = response.data.data.items || [];
      return;
    }
    const response = await WmsInspectionAPI.list({ page_no: 1, page_size: 50, task_no: keyword.value || undefined });
    inspectionRows.value = response.data.data.items || [];
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  Object.assign(arrivalForm, {
    order_no: "",
    warehouse_id: undefined,
    supplier_id: undefined,
    external_source: "manual",
    lines: [{ material_id: undefined, planned_qty: 1, batch_no: "" }],
  });
  createVisible.value = true;
}

async function submitArrival() {
  await createFormRef.value?.validate();
  submitting.value = true;
  try {
    await WmsArrivalAPI.create(arrivalForm);
    ElMessage.success("创建成功");
    createVisible.value = false;
    await refreshData();
  } finally {
    submitting.value = false;
  }
}

async function receiveArrival(row: WmsArrivalOrder) {
  await WmsArrivalAPI.receive(row.id!);
  ElMessage.success("收货成功");
  await refreshData();
}

async function loadArrivalLines(row: WmsArrivalOrder) {
  const response = await WmsArrivalAPI.lines(row.id!);
  detailRows.value = response.data.data;
  linesVisible.value = true;
}

async function loadInspectionLines(row: WmsInspectionTask) {
  const response = await WmsInspectionAPI.lines(row.id!);
  detailRows.value = response.data.data;
  linesVisible.value = true;
}

async function openJudge(row: WmsInspectionTask) {
  currentTaskId.value = row.id;
  const response = await WmsInspectionAPI.lines(row.id!);
  judgeForm.lines = response.data.data.map((line: WmsInspectionLine) => ({
    line_id: line.id!,
    accepted_qty: Number(line.quantity),
    rejected_qty: 0,
  }));
  judgeVisible.value = true;
}

async function submitJudge() {
  if (!currentTaskId.value) return;
  submitting.value = true;
  try {
    await WmsInspectionAPI.judge(currentTaskId.value, judgeForm);
    ElMessage.success("判定成功");
    judgeVisible.value = false;
    await refreshData();
  } finally {
    submitting.value = false;
  }
}

watch(activeTab, refreshData);
onMounted(refreshData);
</script>

<style scoped>
.wms-arrival {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
}

.wms-arrival__toolbar,
.wms-arrival__table {
  border-radius: 8px;
}

.wms-arrival__toolbar-row,
.wms-arrival__actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.wms-arrival__toolbar-row {
  justify-content: space-between;
}
</style>
