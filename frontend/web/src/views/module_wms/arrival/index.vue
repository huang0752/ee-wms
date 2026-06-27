<template>
  <WmsWorkbenchShell
    title="到货与检验作业台"
    description="把采购到货、收货登记、IQC 检验和待入库衔接到一个入口，突出检验结果和异常批次。"
    eyebrow="RECEIVING & IQC"
    :metrics="metrics"
    :metric-columns="5"
  >
    <template #actions>
      <ElButton :icon="Refresh" @click="refreshData">刷新</ElButton>
      <ElButton v-if="activeTab === 'arrival'" type="primary" :icon="Plus" @click="openCreate">新建到货</ElButton>
    </template>

    <template #toolbar>
      <div class="wms-page-toolbar">
        <ElSegmented v-model="activeTab" :options="tabOptions" />
        <ElInput v-model="keyword" clearable placeholder="单号/任务号" :prefix-icon="Search" @keyup.enter="refreshData" />
        <ElSelect v-model="statusFilter" clearable placeholder="状态" @change="refreshData">
          <ElOption v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
        </ElSelect>
      </div>
    </template>

    <ElTable
      v-if="activeTab === 'arrival'"
      v-loading="loading"
      :data="arrivalRows"
      row-key="id"
      height="calc(100vh - 390px)"
    >
      <ElTableColumn prop="order_no" label="到货单号" min-width="160" fixed="left" />
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
      <ElTableColumn prop="supplier_id" label="供应商ID" width="100" />
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
      <ElTableColumn prop="expected_time" label="预计到货" min-width="160" />
      <ElTableColumn prop="received_time" label="收货时间" min-width="160" />
      <ElTableColumn label="操作" width="190" fixed="right">
        <template #default="{ row }">
          <ElButton text type="primary" :disabled="row.status !== 'pending_receive'" @click="receiveArrival(row)">收货</ElButton>
          <ElButton text @click="openArrivalDetail(row)">详情</ElButton>
        </template>
      </ElTableColumn>
    </ElTable>

    <ElTable v-else v-loading="loading" :data="inspectionRows" row-key="id" height="calc(100vh - 390px)">
      <ElTableColumn prop="task_no" label="检验任务号" min-width="160" fixed="left" />
      <ElTableColumn prop="arrival_no" label="到货单号" min-width="160" />
      <ElTableColumn label="状态" width="130">
        <template #default="{ row }">
          <WmsStatusTag :status="row.status" />
        </template>
      </ElTableColumn>
      <ElTableColumn label="检验结果" width="110">
        <template #default="{ row }">
          <ElTag :type="resultTagType(row.result)" effect="plain">{{ resultLabel(row.result) }}</ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn prop="inspector_id" label="检验人ID" width="100" />
      <ElTableColumn prop="external_quality_id" label="外部质量ID" min-width="150" show-overflow-tooltip />
      <ElTableColumn prop="inspected_time" label="检验时间" min-width="160" />
      <ElTableColumn label="操作" width="190" fixed="right">
        <template #default="{ row }">
          <ElButton text type="primary" :disabled="row.status !== 'pending_inspection'" @click="openJudge(row)">判定</ElButton>
          <ElButton text @click="openInspectionDetail(row)">详情</ElButton>
        </template>
      </ElTableColumn>
    </ElTable>

    <ElDialog v-model="createVisible" title="新建到货单" width="840px" destroy-on-close>
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
          <ElCol :span="8">
            <ElFormItem label="预计到货">
              <ElDatePicker v-model="arrivalForm.expected_time" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" />
            </ElFormItem>
          </ElCol>
          <ElCol :span="8">
            <ElFormItem label="来源">
              <ElSelect v-model="arrivalForm.external_source">
                <ElOption label="手工" value="manual" />
                <ElOption label="ERP" value="erp" />
                <ElOption label="MES" value="mes" />
              </ElSelect>
            </ElFormItem>
          </ElCol>
          <ElCol :span="8">
            <ElFormItem label="外部单号">
              <ElInput v-model="arrivalForm.external_no" />
            </ElFormItem>
          </ElCol>
        </ElRow>
        <ElTable :data="arrivalForm.lines" border>
          <ElTableColumn label="物料ID" width="150">
            <template #default="{ row }">
              <ElInputNumber v-model="row.material_id" :min="1" controls-position="right" />
            </template>
          </ElTableColumn>
          <ElTableColumn label="计划数量" width="160">
            <template #default="{ row }">
              <ElInputNumber v-model="row.planned_qty" :min="0.0001" :precision="4" controls-position="right" />
            </template>
          </ElTableColumn>
          <ElTableColumn label="批次号" min-width="180">
            <template #default="{ row }">
              <ElInput v-model="row.batch_no" />
            </template>
          </ElTableColumn>
          <ElTableColumn label="备注" min-width="180">
            <template #default="{ row }">
              <ElInput v-model="row.remark" />
            </template>
          </ElTableColumn>
        </ElTable>
      </ElForm>
      <template #footer>
        <ElButton @click="createVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="submitting" @click="submitArrival">保存</ElButton>
      </template>
    </ElDialog>

    <ElDialog v-model="judgeVisible" title="检验判定" width="780px" destroy-on-close>
      <ElForm :model="judgeForm" label-width="96px">
        <ElRow :gutter="16">
          <ElCol :span="8">
            <ElFormItem label="质量ID">
              <ElInput v-model="judgeForm.external_quality_id" />
            </ElFormItem>
          </ElCol>
          <ElCol :span="16">
            <ElFormItem label="备注">
              <ElInput v-model="judgeForm.remark" />
            </ElFormItem>
          </ElCol>
        </ElRow>
      </ElForm>
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
        <ElTableColumn label="结果">
          <template #default="{ row }">
            <ElSelect v-model="row.result" clearable>
              <ElOption label="合格" value="accepted" />
              <ElOption label="让步接收" value="partial" />
              <ElOption label="不合格" value="rejected" />
            </ElSelect>
          </template>
        </ElTableColumn>
      </ElTable>
      <template #footer>
        <ElButton @click="judgeVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="submitting" @click="submitJudge">提交判定</ElButton>
      </template>
    </ElDialog>

    <WmsDocumentDrawer
      v-model="detailVisible"
      :title="detailTitle"
      :record="detailRecord"
      :fields="detailFields"
      :primary-prop="detailPrimaryProp"
    >
      <template #lines>
        <ElTable :data="detailRows" border>
          <ElTableColumn prop="material_id" label="物料ID" width="90" />
          <ElTableColumn prop="batch_no" label="批次号" min-width="140" />
          <ElTableColumn prop="planned_qty" label="计划" width="90" />
          <ElTableColumn prop="quantity" label="检验数" width="90" />
          <ElTableColumn prop="received_qty" label="实收" width="90" />
          <ElTableColumn prop="accepted_qty" label="合格" width="90" />
          <ElTableColumn prop="rejected_qty" label="不合格" width="90" />
          <ElTableColumn label="合格率" min-width="140">
            <template #default="{ row }">
              <ElProgress :percentage="getQuantityProgress(row.accepted_qty, row.quantity || row.planned_qty)" :stroke-width="7" />
            </template>
          </ElTableColumn>
          <ElTableColumn label="状态" width="120">
            <template #default="{ row }">
              <WmsStatusTag :status="row.status" />
            </template>
          </ElTableColumn>
        </ElTable>
      </template>
    </WmsDocumentDrawer>
  </WmsWorkbenchShell>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { ElMessage, type FormInstance, type FormRules } from "element-plus";
import { Plus, Refresh, Search } from "@element-plus/icons-vue";
import WmsArrivalAPI, { type WmsArrivalForm, type WmsArrivalLine, type WmsArrivalOrder } from "@/api/module_wms/arrival";
import WmsInspectionAPI, {
  type WmsInspectionJudgeForm,
  type WmsInspectionLine,
  type WmsInspectionTask,
} from "@/api/module_wms/inspection";
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

defineOptions({ name: "WmsArrival", inheritAttrs: false });

type ActiveTab = "arrival" | "inspection";
type DetailMode = "arrival" | "inspection";
type DetailRow = WmsArrivalLine | WmsInspectionLine;

const tabOptions: Array<{ label: string; value: ActiveTab }> = [
  { label: "到货单", value: "arrival" },
  { label: "检验任务", value: "inspection" },
];
const statusOptions = [
  { label: "待收货", value: "pending_receive" },
  { label: "待检验", value: "pending_inspection" },
  { label: "待入库", value: "pending_inbound" },
  { label: "已关闭", value: "closed" },
];

const activeTab = ref<ActiveTab>("arrival");
const detailMode = ref<DetailMode>("arrival");
const keyword = ref("");
const statusFilter = ref("");
const loading = ref(false);
const submitting = ref(false);
const createVisible = ref(false);
const judgeVisible = ref(false);
const detailVisible = ref(false);
const createFormRef = ref<FormInstance>();
const arrivalRows = ref<WmsArrivalOrder[]>([]);
const inspectionRows = ref<WmsInspectionTask[]>([]);
const detailRows = ref<DetailRow[]>([]);
const selectedArrival = ref<WmsArrivalOrder | null>(null);
const selectedInspection = ref<WmsInspectionTask | null>(null);
const currentTaskId = ref<number>();

const arrivalForm = reactive<WmsArrivalForm>({
  warehouse_id: undefined,
  supplier_id: undefined,
  external_source: "manual",
  sync_status: "not_required",
  lines: [{ material_id: undefined, planned_qty: 1, batch_no: "" }],
});

const judgeForm = reactive<WmsInspectionJudgeForm>({ lines: [] });
const arrivalRules: FormRules = {
  warehouse_id: [{ required: true, message: "请输入仓库ID", trigger: "blur" }],
};

const metrics = computed(() => {
  const arrivalMetrics = buildDocumentMetrics(arrivalRows.value, [
    { label: "待收货", statuses: ["pending_receive"], icon: "ri:truck-line" },
    { label: "待入库", statuses: ["pending_inbound"], icon: "ri:inbox-archive-line" },
  ]);
  const inspectionMetrics = buildDocumentMetrics(inspectionRows.value, [
    { label: "待检验", statuses: ["pending_inspection"], icon: "ri:microscope-line" },
    { label: "检后待入库", statuses: ["pending_inbound"], icon: "ri:shield-check-line" },
  ]);
  return [
    buildStaticMetric("到货单", arrivalRows.value.length, "ri:file-list-3-line", "primary", "张", "当前列表"),
    ...arrivalMetrics,
    ...inspectionMetrics,
  ];
});

const detailTitle = computed(() => (detailMode.value === "arrival" ? "到货详情" : "检验详情"));
const detailPrimaryProp = computed(() => (detailMode.value === "arrival" ? "order_no" : "task_no"));
const detailRecord = computed(() => {
  if (detailMode.value === "arrival" && selectedArrival.value) {
    return {
      ...selectedArrival.value,
      source_label: getSourceLabel(selectedArrival.value.external_source),
      sync_label: getSyncLabel(selectedArrival.value.sync_status),
      external_no_display: formatNullable(selectedArrival.value.external_no),
      workflow_display: formatNullable(selectedArrival.value.workflow_instance_id),
    };
  }
  if (selectedInspection.value) {
    return {
      ...selectedInspection.value,
      result_label: resultLabel(selectedInspection.value.result),
      external_quality_display: formatNullable(selectedInspection.value.external_quality_id),
    };
  }
  return null;
});
const detailFields = computed<WmsDescriptionItem[]>(() =>
  detailMode.value === "arrival"
    ? [
        { label: "到货单号", prop: "order_no" },
        { label: "供应商ID", prop: "supplier_id" },
        { label: "仓库ID", prop: "warehouse_id" },
        { label: "预计到货", prop: "expected_time" },
        { label: "收货时间", prop: "received_time" },
        { label: "来源", prop: "source_label" },
        { label: "外部单号", prop: "external_no_display" },
        { label: "同步状态", prop: "sync_label" },
        { label: "流程实例", prop: "workflow_display" },
        { label: "备注", prop: "remark", span: 2 },
      ]
    : [
        { label: "检验任务", prop: "task_no" },
        { label: "到货单号", prop: "arrival_no" },
        { label: "检验结果", prop: "result_label" },
        { label: "检验人ID", prop: "inspector_id" },
        { label: "检验时间", prop: "inspected_time" },
        { label: "外部质量ID", prop: "external_quality_display" },
        { label: "附件引用", prop: "attachment_refs" },
        { label: "备注", prop: "remark", span: 2 },
      ]
);

async function refreshData() {
  loading.value = true;
  try {
    if (activeTab.value === "arrival") {
      const response = await WmsArrivalAPI.list({
        page_no: 1,
        page_size: 100,
        order_no: keyword.value || undefined,
        status: statusFilter.value || undefined,
      });
      arrivalRows.value = response.data.data.items || [];
      return;
    }
    const response = await WmsInspectionAPI.list({
      page_no: 1,
      page_size: 100,
      task_no: keyword.value || undefined,
      status: statusFilter.value || undefined,
    });
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
    expected_time: "",
    external_source: "manual",
    external_no: "",
    sync_status: "not_required",
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

async function openArrivalDetail(row: WmsArrivalOrder) {
  detailMode.value = "arrival";
  selectedArrival.value = row;
  const response = await WmsArrivalAPI.lines(row.id!);
  detailRows.value = response.data.data;
  detailVisible.value = true;
}

async function openInspectionDetail(row: WmsInspectionTask) {
  detailMode.value = "inspection";
  selectedInspection.value = row;
  const response = await WmsInspectionAPI.lines(row.id!);
  detailRows.value = response.data.data;
  detailVisible.value = true;
}

async function openJudge(row: WmsInspectionTask) {
  currentTaskId.value = row.id;
  const response = await WmsInspectionAPI.lines(row.id!);
  judgeForm.lines = response.data.data.map((line: WmsInspectionLine) => ({
    line_id: line.id!,
    accepted_qty: Number(line.quantity),
    rejected_qty: 0,
    result: "accepted",
  }));
  judgeForm.external_quality_id = row.external_quality_id || "";
  judgeForm.remark = "";
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

function resultLabel(result?: string) {
  const map: Record<string, string> = {
    accepted: "合格",
    partial: "让步接收",
    rejected: "不合格",
  };
  return result ? map[result] ?? result : "未判定";
}

function resultTagType(result?: string) {
  if (result === "accepted") return "success";
  if (result === "rejected") return "danger";
  if (result === "partial") return "warning";
  return "info";
}

watch(activeTab, refreshData);
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
