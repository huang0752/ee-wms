<template>
  <div class="wms-master">
    <ElCard shadow="never" class="wms-master__toolbar">
      <div class="wms-master__toolbar-row">
        <ElSegmented v-model="activeResource" :options="resourceOptions" @change="refreshData" />
        <div class="wms-master__actions">
          <ElInput
            v-model="query.name"
            clearable
            placeholder="名称/关键字"
            :prefix-icon="Search"
            @keyup.enter="refreshData"
            @clear="refreshData"
          />
          <ElButton :icon="Refresh" @click="refreshData" />
          <ElButton type="primary" :icon="Plus" @click="openCreate">新增</ElButton>
        </div>
      </div>
    </ElCard>

    <ElCard shadow="never" class="wms-master__table">
      <ElTable v-loading="loading" :data="rows" row-key="id" height="calc(100vh - 310px)">
        <ElTableColumn prop="code" label="编码" min-width="140" />
        <ElTableColumn prop="name" label="名称" min-width="160" />
        <ElTableColumn v-if="activeResource === 'material'" prop="spec" label="规格" min-width="160" />
        <ElTableColumn v-if="activeResource === 'material'" prop="unit" label="单位" width="90" />
        <ElTableColumn v-if="activeResource === 'warehouse'" prop="manager" label="负责人" width="120" />
        <ElTableColumn v-if="activeResource === 'location'" prop="mix_rule" label="混放规则" width="120" />
        <ElTableColumn v-if="['supplier', 'customer'].includes(activeResource)" prop="contact" label="联系人" width="120" />
        <ElTableColumn v-if="activeResource === 'barcode-rule'" prop="object_type" label="对象类型" width="120" />
        <ElTableColumn label="状态" width="100">
          <template #default="{ row }">
            <ElTag :type="row.status === 0 ? 'success' : 'info'" effect="plain">
              {{ row.status === 0 ? "启用" : "停用" }}
            </ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="description" label="备注" min-width="180" show-overflow-tooltip />
        <ElTableColumn label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <ElButton text type="primary" @click="openEdit(row)">编辑</ElButton>
            <ElButton text type="danger" @click="removeRow(row)">删除</ElButton>
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
    </ElCard>

    <ElDialog v-model="dialogVisible" :title="dialogTitle" width="640px" destroy-on-close>
      <ElForm ref="formRef" :model="form" :rules="rules" label-width="96px">
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
            <ElFormItem label="批次管理">
              <ElSwitch v-model="form.batch_flag" />
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
  </div>
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

defineOptions({ name: "WmsMaster", inheritAttrs: false });

const resourceOptions: Array<{ label: string; value: WmsMasterResource }> = [
  { label: "仓库", value: "warehouse" },
  { label: "库区", value: "zone" },
  { label: "库位", value: "location" },
  { label: "物料", value: "material" },
  { label: "供应商", value: "supplier" },
  { label: "客户", value: "customer" },
  { label: "条码规则", value: "barcode-rule" },
];

const activeResource = ref<WmsMasterResource>("warehouse");
const rows = ref<WmsMasterTable[]>([]);
const total = ref(0);
const loading = ref(false);
const submitting = ref(false);
const dialogVisible = ref(false);
const editingId = ref<number | null>(null);
const formRef = ref<FormInstance>();

const query = reactive({
  page_no: 1,
  page_size: 10,
  name: "",
});

const form = reactive<WmsMasterForm>({
  code: "",
  name: "",
  status: 0,
  batch_flag: true,
  sn_flag: false,
});

const dialogTitle = computed(() => {
  const label = resourceOptions.find((item) => item.value === activeResource.value)?.label || "主数据";
  return `${editingId.value ? "编辑" : "新增"}${label}`;
});

const rules = computed<FormRules>(() => ({
  code: [{ required: true, message: "请输入编码", trigger: "blur" }],
  name: [{ required: true, message: "请输入名称", trigger: "blur" }],
  object_type:
    activeResource.value === "barcode-rule"
      ? [{ required: true, message: "请输入对象类型", trigger: "blur" }]
      : [],
}));

function resetForm(row?: WmsMasterTable) {
  Object.assign(form, {
    code: row?.code || "",
    name: row?.name || "",
    status: row?.status ?? 0,
    description: row?.description || "",
    type: row?.type || "",
    manager: row?.manager || "",
    spec: row?.spec || "",
    unit: row?.unit || "",
    category: row?.category || "",
    batch_flag: row?.batch_flag ?? true,
    sn_flag: row?.sn_flag ?? false,
    contact: row?.contact || "",
    phone: row?.phone || "",
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
    });
    rows.value = response.data.data.items;
    total.value = response.data.data.total;
  } finally {
    loading.value = false;
  }
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
.wms-master {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.wms-master__toolbar,
.wms-master__table {
  border: 1px solid var(--fa-card-border);
  border-radius: 8px;
}

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

.wms-master__pagination {
  display: flex;
  justify-content: flex-end;
  padding-top: 16px;
}
</style>
