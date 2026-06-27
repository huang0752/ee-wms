<template>
  <WmsWorkbenchShell
    title="仓储主数据中台"
    description="统一维护仓库、库区、库位、物料、往来单位和条码规则，页面同时呈现启用状态、约束字段和基础档案完整度。"
    eyebrow="WMS MASTER DATA"
    :metrics="metrics"
  >
    <template #actions>
      <ElButton :icon="Refresh" :loading="loading" @click="refreshData">刷新</ElButton>
      <ElButton type="primary" :icon="Plus" @click="openCreate">新增{{ activeResourceLabel }}</ElButton>
    </template>

    <template #toolbar>
      <div class="wms-master__toolbar-row">
        <ElSegmented v-model="activeResource" :options="resourceOptions" @change="handleResourceChange" />
        <div class="wms-master__actions">
          <ElInput
            v-model="query.name"
            clearable
            placeholder="名称/编码/关键字"
            :prefix-icon="Search"
            @keyup.enter="refreshData"
            @clear="refreshData"
          />
          <ElSelect v-model="query.status" clearable placeholder="状态" @change="refreshData">
            <ElOption label="启用" :value="0" />
            <ElOption label="停用" :value="1" />
          </ElSelect>
        </div>
      </div>
    </template>

    <div class="wms-master__content">
      <aside class="wms-master__resource-panel">
        <button
          v-for="item in resourceCards"
          :key="item.value"
          type="button"
          :class="['wms-master__resource', { 'is-active': item.value === activeResource }]"
          @click="switchResource(item.value)"
        >
          <span>{{ item.label }}</span>
          <strong>{{ item.count }}</strong>
          <small>{{ item.hint }}</small>
        </button>
      </aside>

      <section class="wms-master__table-panel">
        <ElTable
          v-loading="loading"
          :data="rows"
          row-key="id"
          height="calc(100vh - 455px)"
          highlight-current-row
          @row-click="openDetail"
        >
          <ElTableColumn prop="code" label="编码" min-width="140" fixed="left" show-overflow-tooltip />
          <ElTableColumn prop="name" label="名称" min-width="160" fixed="left" show-overflow-tooltip />
          <ElTableColumn v-if="activeResource === 'material'" prop="spec" label="规格型号" min-width="160" show-overflow-tooltip />
          <ElTableColumn v-if="activeResource === 'material'" prop="unit" label="单位" width="90" />
          <ElTableColumn v-if="activeResource === 'material'" prop="category" label="分类" min-width="120" />
          <ElTableColumn v-if="activeResource === 'warehouse'" prop="type" label="仓库类型" width="120" />
          <ElTableColumn v-if="activeResource === 'warehouse'" prop="manager" label="负责人" width="120" />
          <ElTableColumn v-if="activeResource === 'zone'" prop="warehouse_id" label="仓库ID" width="100" />
          <ElTableColumn v-if="activeResource === 'zone'" prop="usage" label="用途" min-width="130" />
          <ElTableColumn v-if="activeResource === 'location'" prop="warehouse_id" label="仓库ID" width="100" />
          <ElTableColumn v-if="activeResource === 'location'" prop="zone_id" label="库区ID" width="100" />
          <ElTableColumn v-if="activeResource === 'location'" prop="capacity" label="容量" width="120" />
          <ElTableColumn v-if="activeResource === 'location'" prop="mix_rule" label="混放规则" width="130" />
          <ElTableColumn v-if="['supplier', 'customer'].includes(activeResource)" prop="contact" label="联系人" width="120" />
          <ElTableColumn v-if="['supplier', 'customer'].includes(activeResource)" prop="phone" label="电话" min-width="130" />
          <ElTableColumn v-if="['supplier', 'customer'].includes(activeResource)" prop="email" label="邮箱" min-width="170" show-overflow-tooltip />
          <ElTableColumn v-if="activeResource === 'barcode-rule'" prop="object_type" label="对象类型" width="120" />
          <ElTableColumn v-if="activeResource === 'barcode-rule'" prop="prefix" label="前缀" width="110" />
          <ElTableColumn label="状态" width="100">
            <template #default="{ row }">
              <ElTag :type="row.status === 0 ? 'success' : 'info'" effect="plain">
                {{ row.status === 0 ? "启用" : "停用" }}
              </ElTag>
            </template>
          </ElTableColumn>
          <ElTableColumn prop="description" label="备注" min-width="190" show-overflow-tooltip />
          <ElTableColumn label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <ElButton text type="primary" @click.stop="openEdit(row)">编辑</ElButton>
              <ElButton text type="danger" @click.stop="removeRow(row)">删除</ElButton>
            </template>
          </ElTableColumn>
        </ElTable>
        <div class="wms-master__pagination">
          <ElPagination
            v-model:current-page="query.page_no"
            v-model:page-size="query.page_size"
            layout="total, sizes, prev, pager, next"
            :total="total"
            @current-change="refreshData"
            @size-change="refreshData"
          />
        </div>
      </section>
    </div>

    <WmsDocumentDrawer
      v-model="detailVisible"
      title="主数据详情"
      :record="selectedRow"
      :fields="detailFields"
      primary-label="编码"
      primary-prop="code"
      status-prop="statusText"
    />

    <ElDialog v-model="dialogVisible" :title="dialogTitle" width="760px" destroy-on-close>
      <ElForm ref="formRef" :model="form" :rules="rules" label-width="104px">
        <ElRow :gutter="16">
          <ElCol :span="12">
            <ElFormItem label="编码" prop="code">
              <ElInput v-model="form.code" :disabled="editingId !== null" />
            </ElFormItem>
          </ElCol>
          <ElCol :span="12">
            <ElFormItem label="名称" prop="name">
              <ElInput v-model="form.name" />
            </ElFormItem>
          </ElCol>
          <ElCol v-if="activeResource === 'warehouse'" :span="12">
            <ElFormItem label="类型">
              <ElInput v-model="form.type" placeholder="main/virtual/temporary" />
            </ElFormItem>
          </ElCol>
          <ElCol v-if="activeResource === 'warehouse'" :span="12">
            <ElFormItem label="负责人">
              <ElInput v-model="form.manager" />
            </ElFormItem>
          </ElCol>
          <ElCol v-if="activeResource === 'zone'" :span="12">
            <ElFormItem label="仓库ID">
              <ElInputNumber v-model="form.warehouse_id" :min="1" controls-position="right" />
            </ElFormItem>
          </ElCol>
          <ElCol v-if="activeResource === 'zone'" :span="12">
            <ElFormItem label="用途">
              <ElInput v-model="form.usage" />
            </ElFormItem>
          </ElCol>
          <ElCol v-if="activeResource === 'location'" :span="12">
            <ElFormItem label="仓库ID">
              <ElInputNumber v-model="form.warehouse_id" :min="1" controls-position="right" />
            </ElFormItem>
          </ElCol>
          <ElCol v-if="activeResource === 'location'" :span="12">
            <ElFormItem label="库区ID">
              <ElInputNumber v-model="form.zone_id" :min="1" controls-position="right" />
            </ElFormItem>
          </ElCol>
          <ElCol v-if="activeResource === 'location'" :span="12">
            <ElFormItem label="混放规则">
              <ElInput v-model="form.mix_rule" placeholder="single/mixed/batch" />
            </ElFormItem>
          </ElCol>
          <ElCol v-if="activeResource === 'location'" :span="12">
            <ElFormItem label="库位容量">
              <ElInputNumber v-model="form.capacity" :min="0" controls-position="right" />
            </ElFormItem>
          </ElCol>
          <ElCol v-if="activeResource === 'material'" :span="12">
            <ElFormItem label="规格">
              <ElInput v-model="form.spec" />
            </ElFormItem>
          </ElCol>
          <ElCol v-if="activeResource === 'material'" :span="12">
            <ElFormItem label="单位">
              <ElInput v-model="form.unit" />
            </ElFormItem>
          </ElCol>
          <ElCol v-if="activeResource === 'material'" :span="12">
            <ElFormItem label="类别">
              <ElInput v-model="form.category" />
            </ElFormItem>
          </ElCol>
          <ElCol v-if="activeResource === 'material'" :span="12">
            <ElFormItem label="安全库存">
              <ElInputNumber v-model="form.safety_stock" :min="0" controls-position="right" />
            </ElFormItem>
          </ElCol>
          <ElCol v-if="activeResource === 'material'" :span="12">
            <ElFormItem label="批次管理">
              <ElSwitch v-model="form.batch_flag" />
            </ElFormItem>
          </ElCol>
          <ElCol v-if="activeResource === 'material'" :span="12">
            <ElFormItem label="序列号管理">
              <ElSwitch v-model="form.sn_flag" />
            </ElFormItem>
          </ElCol>
          <ElCol v-if="['supplier', 'customer'].includes(activeResource)" :span="12">
            <ElFormItem label="联系人">
              <ElInput v-model="form.contact" />
            </ElFormItem>
          </ElCol>
          <ElCol v-if="['supplier', 'customer'].includes(activeResource)" :span="12">
            <ElFormItem label="电话">
              <ElInput v-model="form.phone" />
            </ElFormItem>
          </ElCol>
          <ElCol v-if="['supplier', 'customer'].includes(activeResource)" :span="12">
            <ElFormItem label="邮箱">
              <ElInput v-model="form.email" />
            </ElFormItem>
          </ElCol>
          <ElCol v-if="['supplier', 'customer'].includes(activeResource)" :span="12">
            <ElFormItem label="地址">
              <ElInput v-model="form.address" />
            </ElFormItem>
          </ElCol>
          <ElCol v-if="activeResource === 'barcode-rule'" :span="12">
            <ElFormItem label="对象类型" prop="object_type">
              <ElInput v-model="form.object_type" placeholder="material/batch/location" />
            </ElFormItem>
          </ElCol>
          <ElCol v-if="activeResource === 'barcode-rule'" :span="12">
            <ElFormItem label="前缀">
              <ElInput v-model="form.prefix" />
            </ElFormItem>
          </ElCol>
          <ElCol :span="12">
            <ElFormItem label="状态">
              <ElRadioGroup v-model="form.status">
                <ElRadio :value="0">启用</ElRadio>
                <ElRadio :value="1">停用</ElRadio>
              </ElRadioGroup>
            </ElFormItem>
          </ElCol>
          <ElCol :span="24">
            <ElFormItem label="备注">
              <ElInput v-model="form.description" type="textarea" :rows="3" />
            </ElFormItem>
          </ElCol>
        </ElRow>
      </ElForm>
      <template #footer>
        <ElButton @click="dialogVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="submitting" @click="submitForm">保存</ElButton>
      </template>
    </ElDialog>
  </WmsWorkbenchShell>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from "element-plus";
import { Plus, Refresh, Search } from "@element-plus/icons-vue";
import WmsMasterAPI, {
  type WmsMasterForm,
  type WmsMasterResource,
  type WmsMasterTable,
} from "@/api/module_wms/master";
import WmsDocumentDrawer from "@/views/module_wms/shared/WmsDocumentDrawer.vue";
import WmsWorkbenchShell from "@/views/module_wms/shared/WmsWorkbenchShell.vue";
import {
  buildStaticMetric,
  formatNullable,
  formatQuantity,
  type WmsDescriptionItem,
  type WmsMetricCard,
} from "@/views/module_wms/shared/wmsOperations";

defineOptions({ name: "WmsMaster", inheritAttrs: false });

const resourceOptions: Array<{ label: string; value: WmsMasterResource; hint: string }> = [
  { label: "仓库", value: "warehouse", hint: "仓储网络" },
  { label: "库区", value: "zone", hint: "空间分区" },
  { label: "库位", value: "location", hint: "作业最小单元" },
  { label: "物料", value: "material", hint: "SKU 基础档案" },
  { label: "供应商", value: "supplier", hint: "采购协同" },
  { label: "客户", value: "customer", hint: "发运对象" },
  { label: "条码规则", value: "barcode-rule", hint: "标识解析" },
];

const activeResource = ref<WmsMasterResource>("warehouse");
const rows = ref<WmsMasterTable[]>([]);
const total = ref(0);
const loading = ref(false);
const submitting = ref(false);
const detailVisible = ref(false);
const dialogVisible = ref(false);
const editingId = ref<number | null>(null);
const selectedRow = ref<(WmsMasterTable & { statusText?: string }) | null>(null);
const formRef = ref<FormInstance>();

const query = reactive({
  page_no: 1,
  page_size: 10,
  name: "",
  status: undefined as number | undefined,
});

const form = reactive<WmsMasterForm>({
  code: "",
  name: "",
  status: 0,
  batch_flag: true,
  sn_flag: false,
});

const activeResourceLabel = computed(() => {
  return resourceOptions.find((item) => item.value === activeResource.value)?.label || "主数据";
});

const dialogTitle = computed(() => `${editingId.value ? "编辑" : "新增"}${activeResourceLabel.value}`);

const rules = computed<FormRules>(() => ({
  code: [{ required: true, message: "请输入编码", trigger: "blur" }],
  name: [{ required: true, message: "请输入名称", trigger: "blur" }],
  object_type:
    activeResource.value === "barcode-rule"
      ? [{ required: true, message: "请输入对象类型", trigger: "blur" }]
      : [],
}));

const metrics = computed<WmsMetricCard[]>(() => {
  const enabled = rows.value.filter((item) => item.status === 0);
  const disabled = rows.value.filter((item) => item.status !== 0);
  const missingDescription = rows.value.filter((item) => !item.description).length;
  return [
    buildStaticMetric("当前资源", activeResourceLabel.value, { icon: "i-ep-files" }),
    buildStaticMetric("启用档案", enabled.length, { icon: "i-ep-circle-check", tone: "success" }),
    buildStaticMetric("停用档案", disabled.length, { icon: "i-ep-circle-close", tone: disabled.length ? "warning" : "info" }),
    buildStaticMetric("备注缺失", missingDescription, { icon: "i-ep-document", tone: missingDescription ? "warning" : "success" }),
  ];
});

const resourceCards = computed(() => {
  return resourceOptions.map((item) => ({
    ...item,
    count: item.value === activeResource.value ? total.value : "-",
  }));
});

const detailFields = computed<WmsDescriptionItem[]>(() => {
  const common: WmsDescriptionItem[] = [
    { label: "名称", prop: "name" },
    { label: "状态", prop: "statusText" },
    { label: "备注", prop: "description", render: (_, row) => formatNullable(row.description) },
  ];
  const resourceFields: Record<WmsMasterResource, WmsDescriptionItem[]> = {
    warehouse: [
      { label: "类型", prop: "type", render: (_, row) => formatNullable(row.type) },
      { label: "负责人", prop: "manager", render: (_, row) => formatNullable(row.manager) },
    ],
    zone: [
      { label: "仓库ID", prop: "warehouse_id" },
      { label: "用途", prop: "usage", render: (_, row) => formatNullable(row.usage) },
    ],
    location: [
      { label: "仓库ID", prop: "warehouse_id" },
      { label: "库区ID", prop: "zone_id" },
      { label: "混放规则", prop: "mix_rule", render: (_, row) => formatNullable(row.mix_rule) },
      { label: "库位容量", prop: "capacity", render: (_, row) => formatQuantity(row.capacity) },
    ],
    material: [
      { label: "规格", prop: "spec", render: (_, row) => formatNullable(row.spec) },
      { label: "单位", prop: "unit", render: (_, row) => formatNullable(row.unit) },
      { label: "分类", prop: "category", render: (_, row) => formatNullable(row.category) },
      { label: "安全库存", prop: "safety_stock", render: (_, row) => formatQuantity(row.safety_stock) },
      { label: "批次管理", prop: "batch_flag", render: (_, row) => (row.batch_flag ? "是" : "否") },
      { label: "序列号管理", prop: "sn_flag", render: (_, row) => (row.sn_flag ? "是" : "否") },
    ],
    supplier: [
      { label: "联系人", prop: "contact", render: (_, row) => formatNullable(row.contact) },
      { label: "电话", prop: "phone", render: (_, row) => formatNullable(row.phone) },
      { label: "邮箱", prop: "email", render: (_, row) => formatNullable(row.email) },
      { label: "地址", prop: "address", render: (_, row) => formatNullable(row.address) },
    ],
    customer: [
      { label: "联系人", prop: "contact", render: (_, row) => formatNullable(row.contact) },
      { label: "电话", prop: "phone", render: (_, row) => formatNullable(row.phone) },
      { label: "邮箱", prop: "email", render: (_, row) => formatNullable(row.email) },
      { label: "地址", prop: "address", render: (_, row) => formatNullable(row.address) },
    ],
    "barcode-rule": [
      { label: "对象类型", prop: "object_type", render: (_, row) => formatNullable(row.object_type) },
      { label: "前缀", prop: "prefix", render: (_, row) => formatNullable(row.prefix) },
    ],
  };
  return [...common, ...resourceFields[activeResource.value]];
});

function resetForm(row?: WmsMasterTable) {
  Object.assign(form, {
    code: row?.code || "",
    name: row?.name || "",
    status: row?.status ?? 0,
    description: row?.description || "",
    type: row?.type || "",
    manager: row?.manager || "",
    usage: row?.usage || "",
    warehouse_id: row?.warehouse_id,
    zone_id: row?.zone_id,
    capacity: row?.capacity ? Number(row.capacity) : undefined,
    spec: row?.spec || "",
    unit: row?.unit || "",
    category: row?.category || "",
    safety_stock: row?.safety_stock ? Number(row.safety_stock) : undefined,
    batch_flag: row?.batch_flag ?? true,
    sn_flag: row?.sn_flag ?? false,
    mix_rule: row?.mix_rule || "",
    contact: row?.contact || "",
    phone: row?.phone || "",
    email: row?.email || "",
    address: row?.address || "",
    object_type: row?.object_type || "",
    prefix: row?.prefix || "",
  });
}

async function refreshData() {
  loading.value = true;
  try {
    const response = await WmsMasterAPI.list(activeResource.value, {
      page_no: query.page_no,
      page_size: query.page_size,
      name: query.name || undefined,
      status: query.status,
    });
    rows.value = response.data.data.items;
    total.value = response.data.data.total;
  } finally {
    loading.value = false;
  }
}

function handleResourceChange() {
  query.page_no = 1;
  selectedRow.value = null;
  void refreshData();
}

function switchResource(resource: WmsMasterResource) {
  if (activeResource.value === resource) return;
  activeResource.value = resource;
  handleResourceChange();
}

function openCreate() {
  editingId.value = null;
  resetForm();
  dialogVisible.value = true;
}

function openEdit(row: WmsMasterTable) {
  editingId.value = row.id || null;
  resetForm(row);
  dialogVisible.value = true;
}

function openDetail(row: WmsMasterTable) {
  selectedRow.value = { ...row, statusText: row.status === 0 ? "启用" : "停用" };
  detailVisible.value = true;
}

async function submitForm() {
  await formRef.value?.validate();
  submitting.value = true;
  try {
    if (editingId.value) {
      await WmsMasterAPI.update(activeResource.value, editingId.value, form);
    } else {
      await WmsMasterAPI.create(activeResource.value, form);
    }
    ElMessage.success("保存成功");
    dialogVisible.value = false;
    await refreshData();
  } finally {
    submitting.value = false;
  }
}

async function removeRow(row: WmsMasterTable) {
  await ElMessageBox.confirm(`确认删除 ${row.name}？`, "删除确认", { type: "warning" });
  await WmsMasterAPI.delete(activeResource.value, [row.id!]);
  ElMessage.success("删除成功");
  await refreshData();
}

onMounted(() => {
  void refreshData();
});
</script>

<style scoped lang="scss">
.wms-master__toolbar-row {
  display: flex;
  gap: 16px;
  align-items: center;
  justify-content: space-between;
}

.wms-master__actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.wms-master__actions :deep(.el-input) {
  width: 240px;
}

.wms-master__actions :deep(.el-select) {
  width: 120px;
}

.wms-master__content {
  display: grid;
  grid-template-columns: 230px minmax(0, 1fr);
  min-height: 0;
}

.wms-master__resource-panel {
  display: grid;
  align-content: start;
  gap: 10px;
  padding: 14px;
  border-right: 1px solid color-mix(in srgb, var(--fa-card-border) 76%, transparent);
}

.wms-master__resource {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 4px 10px;
  width: 100%;
  padding: 12px;
  text-align: left;
  cursor: pointer;
  background: var(--el-fill-color-extra-light);
  border: 1px solid transparent;
  border-radius: 8px;
}

.wms-master__resource.is-active,
.wms-master__resource:hover {
  border-color: color-mix(in srgb, var(--el-color-primary) 42%, transparent);
}

.wms-master__resource span,
.wms-master__resource strong {
  color: var(--el-text-color-primary);
}

.wms-master__resource small {
  grid-column: 1 / -1;
  color: var(--el-text-color-secondary);
}

.wms-master__table-panel {
  min-width: 0;
}

.wms-master__pagination {
  display: flex;
  justify-content: flex-end;
  padding: 14px;
  border-top: 1px solid color-mix(in srgb, var(--fa-card-border) 76%, transparent);
}

@media (width <= 1100px) {
  .wms-master__toolbar-row,
  .wms-master__actions {
    align-items: stretch;
    flex-direction: column;
  }

  .wms-master__actions :deep(.el-input),
  .wms-master__actions :deep(.el-select) {
    width: 100%;
  }

  .wms-master__content {
    grid-template-columns: 1fr;
  }

  .wms-master__resource-panel {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    border-right: 0;
    border-bottom: 1px solid color-mix(in srgb, var(--fa-card-border) 76%, transparent);
  }
}
</style>
