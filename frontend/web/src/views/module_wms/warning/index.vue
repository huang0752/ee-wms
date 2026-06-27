<template>
  <WmsWorkbenchShell
    title="库存预警中心"
    description="把库存上下限、批次异常和处理闭环放在同一张运营视图里，避免预警只停留在列表提醒。"
    eyebrow="WMS RISK CONTROL"
    :metrics="metrics"
  >
    <template #actions>
      <ElButton :icon="Refresh" :loading="loading" @click="refreshData">刷新</ElButton>
      <ElButton type="primary" :icon="Search" :loading="scanning" @click="scan">扫描预警</ElButton>
    </template>

    <template #toolbar>
      <div class="wms-warning__toolbar">
        <ElInputNumber v-model="warehouseId" :min="1" controls-position="right" placeholder="仓库ID" />
        <ElSelect v-model="query.warning_type" clearable placeholder="预警类型" @change="refreshData">
          <ElOption label="低库存" value="low_stock" />
          <ElOption label="超储" value="over_stock" />
          <ElOption label="批次临期" value="expiry" />
          <ElOption label="冻结异常" value="freeze" />
        </ElSelect>
        <ElSegmented v-model="query.status" :options="statusOptions" @change="refreshData" />
      </div>
    </template>

    <div class="wms-warning__content">
      <aside class="wms-warning__lane">
        <button
          v-for="group in groupedWarnings"
          :key="group.key"
          type="button"
          :class="['wms-warning__group', { 'is-active': selectedWarning?.id === group.items[0]?.id }]"
          @click="selectWarning(group.items[0])"
        >
          <span>{{ group.label }}</span>
          <strong>{{ group.items.length }}</strong>
          <small>{{ group.hint }}</small>
        </button>
      </aside>

      <ElTable
        v-loading="loading"
        :data="rows"
        row-key="id"
        height="calc(100vh - 430px)"
        highlight-current-row
        @row-click="selectWarning"
      >
        <ElTableColumn prop="warning_no" label="预警编号" min-width="150" fixed="left" />
        <ElTableColumn label="风险类型" min-width="140">
          <template #default="{ row }">
            <ElTag :type="warningTypeMeta(row.warning_type).type" effect="plain">
              {{ warningTypeMeta(row.warning_type).label }}
            </ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="material_id" label="物料ID" width="100" />
        <ElTableColumn prop="warehouse_id" label="仓库ID" width="100" />
        <ElTableColumn prop="batch_no" label="批次" min-width="130" show-overflow-tooltip />
        <ElTableColumn label="当前/阈值" min-width="150">
          <template #default="{ row }">
            <span class="wms-warning__qty">{{ formatQuantity(row.current_qty) }}</span>
            <small> / {{ formatQuantity(row.threshold_qty) }}</small>
          </template>
        </ElTableColumn>
        <ElTableColumn label="处理状态" width="120">
          <template #default="{ row }">
            <WmsStatusTag :status="row.status" />
          </template>
        </ElTableColumn>
        <ElTableColumn prop="handled_time" label="处理时间" min-width="170" show-overflow-tooltip />
        <ElTableColumn prop="remark" label="备注" min-width="180" show-overflow-tooltip />
        <ElTableColumn label="操作" width="190" fixed="right">
          <template #default="{ row }">
            <ElButton text type="primary" @click.stop="openAdvice(row)">智能建议</ElButton>
            <ElButton text type="primary" :disabled="row.status === 'closed'" @click.stop="close(row)">关闭</ElButton>
          </template>
        </ElTableColumn>
      </ElTable>
    </div>

    <WmsDocumentDrawer
      v-model="detailVisible"
      title="预警详情"
      :record="selectedWarning"
      :fields="detailFields"
      primary-label="预警编号"
      primary-prop="warning_no"
    />
    <WmsAdviceDrawer v-model="adviceVisible" :advice="currentAdvice" />
  </WmsWorkbenchShell>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { Refresh, Search } from "@element-plus/icons-vue";
import WmsWarningAPI, { type WmsWarning } from "@/api/module_wms/warning";
import WmsIntelligenceAPI, { type WmsWarningAdvice } from "@/api/module_wms/intelligence";
import WmsAdviceDrawer from "@/views/module_wms/components/WmsAdviceDrawer.vue";
import WmsDocumentDrawer from "@/views/module_wms/shared/WmsDocumentDrawer.vue";
import WmsStatusTag from "@/views/module_wms/shared/WmsStatusTag.vue";
import WmsWorkbenchShell from "@/views/module_wms/shared/WmsWorkbenchShell.vue";
import {
  buildStaticMetric,
  formatNullable,
  formatQuantity,
  type WmsDescriptionItem,
  type WmsMetricCard,
} from "@/views/module_wms/shared/wmsOperations";

defineOptions({ name: "WmsWarning", inheritAttrs: false });

const statusOptions = [
  { label: "全部", value: "" },
  { label: "待处理", value: "open" },
  { label: "已关闭", value: "closed" },
];

const query = reactive({
  warning_type: "",
  status: "",
});
const warehouseId = ref<number>();
const loading = ref(false);
const scanning = ref(false);
const detailVisible = ref(false);
const adviceVisible = ref(false);
const rows = ref<WmsWarning[]>([]);
const selectedWarning = ref<WmsWarning | null>(null);
const currentAdvice = ref<WmsWarningAdvice | null>(null);

const detailFields: WmsDescriptionItem[] = [
  { label: "预警类型", prop: "warning_type", render: (_, row) => warningTypeMeta(String(row.warning_type)).label },
  { label: "物料ID", prop: "material_id" },
  { label: "仓库ID", prop: "warehouse_id" },
  { label: "批次", prop: "batch_no", render: (_, row) => formatNullable(row.batch_no) },
  { label: "当前库存", prop: "current_qty", render: (_, row) => formatQuantity(row.current_qty) },
  { label: "阈值", prop: "threshold_qty", render: (_, row) => formatQuantity(row.threshold_qty) },
  { label: "处理时间", prop: "handled_time", render: (_, row) => formatNullable(row.handled_time) },
  { label: "备注", prop: "remark", render: (_, row) => formatNullable(row.remark) },
];

const metrics = computed<WmsMetricCard[]>(() => {
  const openRows = rows.value.filter((item) => item.status !== "closed");
  const closedRows = rows.value.filter((item) => item.status === "closed");
  const lowStockRows = rows.value.filter((item) => item.warning_type === "low_stock");
  return [
    buildStaticMetric("未闭环预警", openRows.length, { icon: "ri:alarm-warning-line", tone: openRows.length ? "danger" : "success" }),
    buildStaticMetric("已关闭", closedRows.length, { icon: "ri:checkbox-circle-line", tone: "success" }),
    buildStaticMetric("低库存", lowStockRows.length, { icon: "ri:arrow-down-circle-line", tone: lowStockRows.length ? "warning" : "info" }),
    buildStaticMetric("涉及物料", new Set(rows.value.map((item) => item.material_id)).size, { icon: "ri:box-3-line" }),
  ];
});

const groupedWarnings = computed(() => {
  const groups = [
    { key: "open", label: "待处理", hint: "需要人工确认或补货", items: rows.value.filter((item) => item.status !== "closed") },
    { key: "low_stock", label: "低库存", hint: "建议生成采购/调拨", items: rows.value.filter((item) => item.warning_type === "low_stock") },
    { key: "closed", label: "已关闭", hint: "保留处理凭证", items: rows.value.filter((item) => item.status === "closed") },
  ];
  return groups.filter((group) => group.items.length);
});

function warningTypeMeta(type: string): { label: string; type: "success" | "warning" | "danger" | "info" } {
  const map: Record<string, { label: string; type: "success" | "warning" | "danger" | "info" }> = {
    low_stock: { label: "低库存", type: "danger" },
    over_stock: { label: "超储", type: "warning" },
    expiry: { label: "批次临期", type: "warning" },
    freeze: { label: "冻结异常", type: "info" },
  };
  return map[type] ?? { label: type || "未知", type: "info" };
}

async function refreshData() {
  loading.value = true;
  try {
    const response = await WmsWarningAPI.list({
      page_no: 1,
      page_size: 100,
      warning_type: query.warning_type || undefined,
      status: query.status || undefined,
    });
    rows.value = response.data.data.items || [];
    selectedWarning.value = rows.value[0] || null;
  } finally {
    loading.value = false;
  }
}

async function scan() {
  scanning.value = true;
  try {
    await WmsWarningAPI.scan({ warehouse_id: warehouseId.value });
    ElMessage.success("扫描完成");
    await refreshData();
  } finally {
    scanning.value = false;
  }
}

async function close(row: WmsWarning) {
  await WmsWarningAPI.close(row.id!);
  ElMessage.success("已关闭");
  await refreshData();
}

function selectWarning(row?: WmsWarning) {
  if (!row) return;
  selectedWarning.value = row;
  detailVisible.value = true;
}

async function openAdvice(row: WmsWarning) {
  if (!row.id) return;
  const response = await WmsIntelligenceAPI.warningAdvice(row.id);
  currentAdvice.value = response.data.data;
  adviceVisible.value = true;
}

onMounted(refreshData);
</script>

<style scoped>
.wms-warning__toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.wms-warning__toolbar :deep(.el-select) {
  width: 180px;
}

.wms-warning__content {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  min-height: 0;
}

.wms-warning__lane {
  display: grid;
  align-content: start;
  gap: 10px;
  padding: 14px;
  border-right: 1px solid color-mix(in srgb, var(--fa-card-border) 76%, transparent);
}

.wms-warning__group {
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

.wms-warning__group.is-active,
.wms-warning__group:hover {
  border-color: color-mix(in srgb, var(--el-color-primary) 42%, transparent);
}

.wms-warning__group span,
.wms-warning__group strong {
  color: var(--el-text-color-primary);
}

.wms-warning__group small {
  grid-column: 1 / -1;
  color: var(--el-text-color-secondary);
}

.wms-warning__qty {
  font-weight: 700;
  color: var(--el-text-color-primary);
}

@media (width <= 1100px) {
  .wms-warning__content {
    grid-template-columns: 1fr;
  }

  .wms-warning__lane {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    border-right: 0;
    border-bottom: 1px solid color-mix(in srgb, var(--fa-card-border) 76%, transparent);
  }
}
</style>
