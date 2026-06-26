<template>
  <div class="wms-stock">
    <ElCard shadow="never" class="wms-stock__toolbar">
      <div class="wms-stock__toolbar-row">
        <ElSegmented v-model="activeTab" :options="tabOptions" />
        <div class="wms-stock__actions">
          <ElInputNumber v-model="query.material_id" :min="1" controls-position="right" placeholder="物料ID" />
          <ElInput v-model="query.batch_no" clearable placeholder="批次号" :prefix-icon="Search" @keyup.enter="refreshData" />
          <ElCheckbox v-model="query.only_available">仅可用</ElCheckbox>
          <ElButton :icon="Refresh" @click="refreshData" />
          <ElButton type="primary" :icon="Plus" @click="openAction('receive')">收货待检</ElButton>
          <ElButton :icon="Lock" @click="openAction('lock')">锁库</ElButton>
        </div>
      </div>
    </ElCard>

    <ElCard v-if="activeTab === 'balance'" shadow="never" class="wms-stock__table">
      <ElTable v-loading="loading" :data="balances" row-key="id" height="calc(100vh - 310px)">
        <ElTableColumn prop="material_id" label="物料ID" width="100" />
        <ElTableColumn prop="warehouse_id" label="仓库ID" width="100" />
        <ElTableColumn prop="location_id" label="库位ID" width="100" />
        <ElTableColumn prop="batch_no" label="批次号" min-width="150" />
        <ElTableColumn prop="quantity" label="实物" width="110" />
        <ElTableColumn prop="available_qty" label="可用" width="110" />
        <ElTableColumn prop="locked_qty" label="锁定" width="110" />
        <ElTableColumn prop="frozen_qty" label="冻结" width="110" />
        <ElTableColumn prop="pending_qty" label="待检" width="110" />
        <ElTableColumn prop="defective_qty" label="不良" width="110" />
        <ElTableColumn label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <ElButton text type="primary" @click="openAction('approve', row)">转可用</ElButton>
            <ElButton text type="warning" @click="openAction('freeze', row)">冻结</ElButton>
            <ElButton text @click="openAction('unfreeze', row)">解冻</ElButton>
          </template>
        </ElTableColumn>
      </ElTable>
      <div class="wms-stock__pagination">
        <ElPagination
          v-model:current-page="query.page_no"
          v-model:page-size="query.page_size"
          layout="total, sizes, prev, pager, next"
          :total="balanceTotal"
          @current-change="refreshData"
          @size-change="refreshData"
        />
      </div>
    </ElCard>

    <ElCard v-else shadow="never" class="wms-stock__table">
      <ElTable v-loading="loading" :data="flows" row-key="id" height="calc(100vh - 310px)">
        <ElTableColumn prop="flow_no" label="流水号" min-width="140" />
        <ElTableColumn prop="flow_type" label="类型" width="150" />
        <ElTableColumn prop="direction" label="方向" width="90" />
        <ElTableColumn prop="material_id" label="物料ID" width="100" />
        <ElTableColumn prop="batch_no" label="批次号" min-width="140" />
        <ElTableColumn prop="quantity" label="数量" width="110" />
        <ElTableColumn prop="stock_status_before" label="变更前" width="120" />
        <ElTableColumn prop="stock_status_after" label="变更后" width="120" />
        <ElTableColumn prop="document_no" label="单据号" min-width="140" />
      </ElTable>
    </ElCard>

    <ElDialog v-model="dialogVisible" :title="dialogTitle" width="560px" destroy-on-close>
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
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { ElMessage, type FormInstance, type FormRules } from "element-plus";
import { Lock, Plus, Refresh, Search } from "@element-plus/icons-vue";
import WmsStockAPI, {
  type WmsStockBalance,
  type WmsStockFlow,
  type WmsStockMutationForm,
} from "@/api/module_wms/stock";

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
const actionType = ref<ActionType>("receive");
const formRef = ref<FormInstance>();

const query = reactive({
  page_no: 1,
  page_size: 10,
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
    if (actionType.value === "receive") {
      await WmsStockAPI.receivePending(form);
    } else if (actionType.value === "approve") {
      await WmsStockAPI.approveToAvailable(form);
    } else if (actionType.value === "freeze") {
      await WmsStockAPI.freeze(form);
    } else if (actionType.value === "unfreeze") {
      await WmsStockAPI.unfreeze(form);
    } else {
      await WmsStockAPI.lock({
        material_id: form.material_id,
        warehouse_id: form.warehouse_id,
        location_id: form.location_id,
        quantity: form.quantity,
        document_no: form.document_no,
        remark: form.remark,
      });
    }
    ElMessage.success("操作成功");
    dialogVisible.value = false;
    await refreshData();
  } finally {
    submitting.value = false;
  }
}

watch(activeTab, refreshData);
onMounted(refreshData);
</script>

<style scoped>
.wms-stock {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
}

.wms-stock__toolbar,
.wms-stock__table {
  border-radius: 8px;
}

.wms-stock__toolbar-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.wms-stock__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.wms-stock__pagination {
  display: flex;
  justify-content: flex-end;
  padding-top: 16px;
}
</style>
