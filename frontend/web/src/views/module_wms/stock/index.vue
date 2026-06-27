<template>
  <WmsWorkbenchShell
    title="实时库存作业台"
    description="聚合批次余额、库存桶、锁库建议和库存流水，库存变更坚持流水先行、余额汇总。"
    eyebrow="INVENTORY CONTROL"
    :metrics="metrics"
    :metric-columns="5"
  >
    <template #actions>
      <ElButton :icon="Refresh" @click="refreshData">刷新</ElButton>
      <ElButton type="primary" :icon="Plus" @click="openAction('receive')">收货待检</ElButton>
      <ElButton :icon="Lock" @click="openAction('lock')">锁库</ElButton>
      <ElButton :icon="DataAnalysis" :disabled="!query.material_id" @click="openOutboundExplain">推荐解释</ElButton>
    </template>

    <template #toolbar>
      <div class="wms-page-toolbar">
        <ElSegmented v-model="activeTab" :options="tabOptions" />
        <ElInputNumber v-model="query.material_id" :min="1" controls-position="right" placeholder="物料ID" />
        <ElInput v-model="query.batch_no" clearable placeholder="批次号" :prefix-icon="Search" @keyup.enter="refreshData" />
        <ElCheckbox v-model="query.only_available">仅可用</ElCheckbox>
      </div>
    </template>

    <template v-if="activeTab === 'balance'">
      <ElTable v-loading="loading" :data="balances" row-key="id" height="calc(100vh - 420px)">
        <ElTableColumn prop="material_id" label="物料ID" width="90" fixed="left" />
        <ElTableColumn prop="warehouse_id" label="仓库ID" width="90" />
        <ElTableColumn prop="location_id" label="库位ID" width="90" />
        <ElTableColumn prop="batch_no" label="批次号" min-width="150" show-overflow-tooltip />
        <ElTableColumn label="库存状态" width="120">
          <template #default="{ row }">
            <WmsStatusTag :status="row.stock_status" />
          </template>
        </ElTableColumn>
        <ElTableColumn label="库存桶结构" min-width="260">
          <template #default="{ row }">
            <div class="wms-stock-buckets">
              <span class="success" :style="{ width: `${bucketPercent(row.available_qty, row.quantity)}%` }"></span>
              <span class="primary" :style="{ width: `${bucketPercent(row.locked_qty, row.quantity)}%` }"></span>
              <span class="warning" :style="{ width: `${bucketPercent(row.frozen_qty, row.quantity)}%` }"></span>
              <span class="info" :style="{ width: `${bucketPercent(row.pending_qty, row.quantity)}%` }"></span>
              <span class="danger" :style="{ width: `${bucketPercent(row.defective_qty, row.quantity)}%` }"></span>
            </div>
            <small class="wms-stock-bucket-text">
              可用 {{ row.available_qty }} / 锁定 {{ row.locked_qty }} / 冻结 {{ row.frozen_qty }} / 待检 {{ row.pending_qty }} / 不良
              {{ row.defective_qty }}
            </small>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="quantity" label="实物" width="100" />
        <ElTableColumn prop="available_qty" label="可用" width="100" />
        <ElTableColumn prop="locked_qty" label="锁定" width="100" />
        <ElTableColumn prop="frozen_qty" label="冻结" width="100" />
        <ElTableColumn label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <ElButton text type="primary" @click="openAction('approve', row)">转可用</ElButton>
            <ElButton text type="warning" @click="openAction('freeze', row)">冻结</ElButton>
            <ElButton text @click="openAction('unfreeze', row)">解冻</ElButton>
            <ElButton text @click="openBalanceDetail(row)">详情</ElButton>
          </template>
        </ElTableColumn>
      </ElTable>
      <div class="wms-pagination">
        <ElPagination
          v-model:current-page="query.page_no"
          v-model:page-size="query.page_size"
          layout="total, sizes, prev, pager, next"
          :total="balanceTotal"
          @current-change="refreshData"
          @size-change="refreshData"
        />
      </div>
    </template>

    <ElTable v-else v-loading="loading" :data="flows" row-key="id" height="calc(100vh - 390px)">
      <ElTableColumn prop="flow_no" label="流水号" min-width="150" fixed="left" />
      <ElTableColumn label="类型" width="130">
        <template #default="{ row }">{{ getFlowTypeLabel(row.flow_type) }}</template>
      </ElTableColumn>
      <ElTableColumn prop="direction" label="方向" width="80" />
      <ElTableColumn prop="material_id" label="物料ID" width="90" />
      <ElTableColumn prop="warehouse_id" label="仓库ID" width="90" />
      <ElTableColumn prop="location_id" label="库位ID" width="90" />
      <ElTableColumn prop="batch_no" label="批次号" min-width="140" show-overflow-tooltip />
      <ElTableColumn prop="quantity" label="数量" width="100" />
      <ElTableColumn label="状态变化" min-width="160">
        <template #default="{ row }">
          {{ formatNullable(row.stock_status_before) }} -> {{ formatNullable(row.stock_status_after) }}
        </template>
      </ElTableColumn>
      <ElTableColumn prop="document_type" label="单据类型" width="110" />
      <ElTableColumn prop="document_no" label="单据号" min-width="140" show-overflow-tooltip />
      <ElTableColumn prop="remark" label="备注" min-width="160" show-overflow-tooltip />
    </ElTable>

    <ElDialog v-model="dialogVisible" :title="dialogTitle" width="620px" destroy-on-close>
      <ElForm ref="formRef" :model="form" :rules="rules" label-width="96px">
        <ElRow :gutter="16">
          <ElCol :span="12">
            <ElFormItem label="物料ID" prop="material_id">
              <ElInputNumber v-model="form.material_id" :min="1" controls-position="right" />
            </ElFormItem>
          </ElCol>
          <ElCol :span="12">
            <ElFormItem label="仓库ID" prop="warehouse_id">
              <ElInputNumber v-model="form.warehouse_id" :min="1" controls-position="right" />
            </ElFormItem>
          </ElCol>
          <ElCol v-if="actionType !== 'lock'" :span="12">
            <ElFormItem label="库位ID">
              <ElInputNumber v-model="form.location_id" :min="1" controls-position="right" />
            </ElFormItem>
          </ElCol>
          <ElCol v-if="actionType !== 'lock'" :span="12">
            <ElFormItem label="批次号" prop="batch_no">
              <ElInput v-model="form.batch_no" />
            </ElFormItem>
          </ElCol>
          <ElCol :span="12">
            <ElFormItem label="数量" prop="quantity">
              <ElInputNumber v-model="form.quantity" :min="0.0001" :precision="4" controls-position="right" />
            </ElFormItem>
          </ElCol>
          <ElCol :span="12">
            <ElFormItem label="单据号">
              <ElInput v-model="form.document_no" />
            </ElFormItem>
          </ElCol>
          <ElCol :span="24">
            <ElFormItem label="备注">
              <ElInput v-model="form.remark" type="textarea" :rows="3" />
            </ElFormItem>
          </ElCol>
        </ElRow>
      </ElForm>
      <template #footer>
        <ElButton @click="dialogVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="submitting" @click="submitAction">确认</ElButton>
      </template>
    </ElDialog>

    <WmsDocumentDrawer
      v-model="balanceDetailVisible"
      title="库存批次详情"
      :record="selectedBalance"
      :fields="balanceDetailFields"
      primary-label="批次号"
      primary-prop="batch_no"
      status-prop="stock_status"
    />

    <FaDrawer v-model="explainVisible" title="出库推荐解释" size="620px" form-mode="detail" confirm-text="关闭">
      <ElEmpty v-if="!outboundExplain" description="暂无推荐解释" />
      <div v-else class="wms-stock-explain">
        <div class="wms-stock-explain__header">
          <ElTag effect="plain">{{ outboundExplain.source === "ai" ? "AI 解释" : "规则解释" }}</ElTag>
          <span>{{ outboundExplain.summary }}</span>
        </div>
        <ElTable :data="outboundExplain.candidates" row-key="balance_id">
          <ElTableColumn prop="batch_no" label="批次" min-width="120" />
          <ElTableColumn prop="available_qty" label="可用" width="100" />
          <ElTableColumn prop="score" label="评分" width="90" />
          <ElTableColumn label="原因" min-width="220">
            <template #default="{ row }">
              <div class="wms-reason-list">
                <span v-for="reason in row.rule_reasons" :key="reason">{{ reason }}</span>
              </div>
            </template>
          </ElTableColumn>
        </ElTable>
      </div>
    </FaDrawer>
  </WmsWorkbenchShell>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { ElMessage, type FormInstance, type FormRules } from "element-plus";
import { DataAnalysis, Lock, Plus, Refresh, Search } from "@element-plus/icons-vue";
import WmsStockAPI, {
  type WmsStockBalance,
  type WmsStockFlow,
  type WmsStockMutationForm,
} from "@/api/module_wms/stock";
import WmsIntelligenceAPI, { type WmsOutboundExplain } from "@/api/module_wms/intelligence";
import WmsDocumentDrawer from "@/views/module_wms/shared/WmsDocumentDrawer.vue";
import WmsStatusTag from "@/views/module_wms/shared/WmsStatusTag.vue";
import WmsWorkbenchShell from "@/views/module_wms/shared/WmsWorkbenchShell.vue";
import {
  buildStaticMetric,
  formatNullable,
  formatQuantity,
  getFlowTypeLabel,
  sumDecimalFields,
  toNumber,
  type WmsDescriptionItem,
} from "@/views/module_wms/shared/wmsOperations";

defineOptions({ name: "WmsStock", inheritAttrs: false });

type StockTab = "balance" | "flow";
type ActionType = "receive" | "approve" | "freeze" | "unfreeze" | "lock";

const tabOptions: Array<{ label: string; value: StockTab }> = [
  { label: "库存余额", value: "balance" },
  { label: "库存流水", value: "flow" },
];

const activeTab = ref<StockTab>("balance");
const balances = ref<WmsStockBalance[]>([]);
const flows = ref<WmsStockFlow[]>([]);
const balanceTotal = ref(0);
const loading = ref(false);
const submitting = ref(false);
const dialogVisible = ref(false);
const explainVisible = ref(false);
const balanceDetailVisible = ref(false);
const actionType = ref<ActionType>("receive");
const formRef = ref<FormInstance>();
const outboundExplain = ref<WmsOutboundExplain>();
const selectedBalance = ref<WmsStockBalance | null>(null);

const query = reactive({
  page_no: 1,
  page_size: 20,
  material_id: undefined as number | undefined,
  batch_no: "",
  only_available: false,
});

const form = reactive<WmsStockMutationForm>({
  material_id: undefined,
  warehouse_id: undefined,
  location_id: undefined,
  batch_no: "",
  quantity: 1,
  document_no: "",
  remark: "",
});

const metrics = computed(() => [
  buildStaticMetric("实物库存", formatQuantity(sumDecimalFields(balances.value, ["quantity"])), "ri:archive-drawer-line", "primary", "", "当前页汇总"),
  buildStaticMetric("可用库存", formatQuantity(sumDecimalFields(balances.value, ["available_qty"])), "ri:checkbox-circle-line", "success"),
  buildStaticMetric("锁定库存", formatQuantity(sumDecimalFields(balances.value, ["locked_qty"])), "ri:lock-line", "primary"),
  buildStaticMetric("冻结库存", formatQuantity(sumDecimalFields(balances.value, ["frozen_qty"])), "ri:forbid-2-line", "warning"),
  buildStaticMetric("待检/不良", formatQuantity(sumDecimalFields(balances.value, ["pending_qty", "defective_qty"])), "ri:error-warning-line", "danger"),
]);

const dialogTitle = computed(() => {
  const titles: Record<ActionType, string> = {
    receive: "收货待检",
    approve: "待检转可用",
    freeze: "冻结库存",
    unfreeze: "解冻库存",
    lock: "锁定库存",
  };
  return titles[actionType.value];
});

const rules = computed<FormRules>(() => ({
  material_id: [{ required: true, message: "请输入物料ID", trigger: "blur" }],
  warehouse_id: actionType.value === "lock" ? [] : [{ required: true, message: "请输入仓库ID", trigger: "blur" }],
  batch_no: actionType.value === "lock" ? [] : [{ required: true, message: "请输入批次号", trigger: "blur" }],
  quantity: [{ required: true, message: "请输入数量", trigger: "blur" }],
}));

const balanceDetailFields: WmsDescriptionItem[] = [
  { label: "物料ID", prop: "material_id" },
  { label: "仓库ID", prop: "warehouse_id" },
  { label: "库位ID", prop: "location_id" },
  { label: "批次号", prop: "batch_no" },
  { label: "SN码", prop: "sn_code" },
  { label: "实物数量", prop: "quantity" },
  { label: "可用数量", prop: "available_qty" },
  { label: "锁定数量", prop: "locked_qty" },
  { label: "冻结数量", prop: "frozen_qty" },
  { label: "待检数量", prop: "pending_qty" },
  { label: "不良数量", prop: "defective_qty" },
  { label: "试用批次", prop: "demo_batch_id" },
];

function bucketPercent(value: unknown, total: unknown) {
  const denominator = toNumber(total);
  if (denominator <= 0) return 0;
  return Math.max(0, Math.min(100, Math.round((toNumber(value) / denominator) * 100)));
}

function fillForm(row?: WmsStockBalance) {
  Object.assign(form, {
    material_id: row?.material_id,
    warehouse_id: row?.warehouse_id,
    location_id: row?.location_id,
    batch_no: row?.batch_no || "",
    quantity: 1,
    document_no: "",
    remark: "",
  });
}

function openAction(type: ActionType, row?: WmsStockBalance) {
  actionType.value = type;
  fillForm(row);
  dialogVisible.value = true;
}

function openBalanceDetail(row: WmsStockBalance) {
  selectedBalance.value = row;
  balanceDetailVisible.value = true;
}

async function refreshData() {
  loading.value = true;
  try {
    if (activeTab.value === "balance") {
      const response = await WmsStockAPI.balances(query);
      balances.value = response.data.data.items || [];
      balanceTotal.value = response.data.data.total || 0;
      return;
    }
    const response = await WmsStockAPI.flows({
      page_no: 1,
      page_size: 100,
      material_id: query.material_id,
      batch_no: query.batch_no,
    });
    flows.value = response.data.data.items || [];
  } finally {
    loading.value = false;
  }
}

async function submitAction() {
  await formRef.value?.validate();
  submitting.value = true;
  try {
    if (actionType.value === "receive") await WmsStockAPI.receivePending(form);
    if (actionType.value === "approve") await WmsStockAPI.approveToAvailable(form);
    if (actionType.value === "freeze") await WmsStockAPI.freeze(form);
    if (actionType.value === "unfreeze") await WmsStockAPI.unfreeze(form);
    if (actionType.value === "lock") await WmsStockAPI.lock(form);
    ElMessage.success("操作成功");
    dialogVisible.value = false;
    await refreshData();
  } finally {
    submitting.value = false;
  }
}

async function openOutboundExplain() {
  if (!query.material_id) return;
  const response = await WmsIntelligenceAPI.outboundExplain({
    material_id: query.material_id,
    required_qty: "1",
  });
  outboundExplain.value = response.data.data;
  explainVisible.value = true;
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
  max-width: 220px;
}

.wms-stock-buckets {
  display: flex;
  width: 100%;
  height: 8px;
  overflow: hidden;
  background: var(--el-fill-color-light);
  border-radius: 999px;
}

.wms-stock-buckets span {
  min-width: 0;
}

.wms-stock-buckets .success {
  background: var(--el-color-success);
}

.wms-stock-buckets .primary {
  background: var(--el-color-primary);
}

.wms-stock-buckets .warning {
  background: var(--el-color-warning);
}

.wms-stock-buckets .info {
  background: var(--el-color-info);
}

.wms-stock-buckets .danger {
  background: var(--el-color-danger);
}

.wms-stock-bucket-text {
  display: block;
  margin-top: 6px;
  color: var(--el-text-color-secondary);
}

.wms-pagination {
  display: flex;
  justify-content: flex-end;
  padding: 12px;
}

.wms-stock-explain {
  display: grid;
  gap: 14px;
}

.wms-stock-explain__header {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  line-height: 1.6;
}

.wms-reason-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.wms-reason-list span {
  padding: 4px 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color-light);
  border-radius: 6px;
}
</style>
