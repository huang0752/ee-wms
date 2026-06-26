<template>
  <div class="wms-demo">
    <ElTabs v-model="activeTab" class="wms-demo__tabs">
      <ElTabPane label="生成配置" name="config">
        <div class="wms-demo__grid">
          <section class="wms-demo__panel">
            <div class="wms-demo__panel-title">企业与编号</div>
            <ElForm :model="form" label-width="108px">
              <ElRow :gutter="16">
                <ElCol :xs="24" :md="12">
                  <ElFormItem label="企业名称"
                    ><ElInput v-model="form.profile.company_name" maxlength="128"
                  /></ElFormItem>
                </ElCol>
                <ElCol :xs="24" :md="12">
                  <ElFormItem label="行业"
                    ><ElInput v-model="form.profile.industry" maxlength="64"
                  /></ElFormItem>
                </ElCol>
                <ElCol :xs="24" :md="8">
                  <ElFormItem label="规模">
                    <ElSegmented v-model="form.profile.company_size" :options="sizeOptions" />
                  </ElFormItem>
                </ElCol>
                <ElCol :xs="24" :md="8">
                  <ElFormItem label="生成模式">
                    <ElSelect v-model="form.scale_mode">
                      <ElOption label="快速体验" value="quick" />
                      <ElOption label="标准演示" value="standard" />
                      <ElOption label="丰富演示" value="rich" />
                      <ElOption label="自定义" value="custom" />
                    </ElSelect>
                  </ElFormItem>
                </ElCol>
                <ElCol :xs="24" :md="8">
                  <ElFormItem label="时间范围">
                    <ElInputNumber
                      v-model="form.time_range_days"
                      :min="7"
                      :max="180"
                      controls-position="right"
                    />
                  </ElFormItem>
                </ElCol>
                <ElCol :xs="24" :md="8">
                  <ElFormItem label="租户短码"
                    ><ElInput v-model="form.numbering.tenant_short_code" maxlength="16"
                  /></ElFormItem>
                </ElCol>
                <ElCol :xs="24" :md="8">
                  <ElFormItem label="日期格式">
                    <ElSelect v-model="form.numbering.date_format">
                      <ElOption label="yyyyMMdd" value="yyyyMMdd" />
                      <ElOption label="yyMMdd" value="yyMMdd" />
                      <ElOption label="yyyyMM" value="yyyyMM" />
                    </ElSelect>
                  </ElFormItem>
                </ElCol>
                <ElCol :xs="24" :md="8">
                  <ElFormItem label="流水位数">
                    <ElInputNumber
                      v-model="form.numbering.sequence_digits"
                      :min="4"
                      :max="8"
                      controls-position="right"
                    />
                  </ElFormItem>
                </ElCol>
              </ElRow>
            </ElForm>
          </section>

          <section class="wms-demo__panel">
            <div class="wms-demo__panel-title">数量目标</div>
            <div class="wms-demo__numbers">
              <label v-for="item in quantityFields" :key="item.key" class="wms-demo__number">
                <span>{{ item.label }}</span>
                <ElInputNumber
                  v-model="form.quantity_targets[item.key]"
                  :min="item.min"
                  :max="item.max"
                  controls-position="right"
                />
              </label>
            </div>
          </section>
        </div>

        <section class="wms-demo__panel">
          <div class="wms-demo__panel-head">
            <div class="wms-demo__panel-title">产品与生成要求</div>
            <ElButton :icon="Plus" @click="addProduct">新增产品</ElButton>
          </div>
          <ElTable :data="form.custom_products" border>
            <ElTableColumn label="产品" min-width="170"
              ><template #default="{ row }"><ElInput v-model="row.name" /></template
            ></ElTableColumn>
            <ElTableColumn label="品类" min-width="140"
              ><template #default="{ row }"><ElInput v-model="row.category" /></template
            ></ElTableColumn>
            <ElTableColumn label="电压/规格" min-width="180"
              ><template #default="{ row }"
                ><ElInput
                  :model-value="row.spec_examples.join('、')"
                  @update:model-value="row.spec_examples = splitText($event)" /></template
            ></ElTableColumn>
            <ElTableColumn label="仓储特性" min-width="180"
              ><template #default="{ row }"
                ><ElInput
                  :model-value="row.storage_traits.join('、')"
                  @update:model-value="row.storage_traits = splitText($event)" /></template
            ></ElTableColumn>
            <ElTableColumn label="权重" width="120"
              ><template #default="{ row }"
                ><ElInputNumber
                  v-model="row.weight"
                  :min="1"
                  :max="10"
                  controls-position="right" /></template
            ></ElTableColumn>
            <ElTableColumn width="74" fixed="right"
              ><template #default="{ $index }"
                ><ElButton
                  :icon="Delete"
                  text
                  type="danger"
                  @click="removeProduct($index)" /></template
            ></ElTableColumn>
          </ElTable>
          <ElRow :gutter="16" class="wms-demo__textarea-row">
            <ElCol :xs="24" :md="12">
              <ElInput
                v-model="form.quality_requirements"
                type="textarea"
                :rows="4"
                maxlength="1000"
                show-word-limit
                placeholder="质量要求、检验规则、特殊存储约束"
              />
            </ElCol>
            <ElCol :xs="24" :md="12">
              <ElInput
                v-model="form.generation_instructions"
                type="textarea"
                :rows="4"
                maxlength="1500"
                show-word-limit
                placeholder="生成偏好，例如供应商层次、项目类型、批次时间分布"
              />
            </ElCol>
          </ElRow>
        </section>
      </ElTabPane>

      <ElTabPane label="样本池" name="pool">
        <section class="wms-demo__panel">
          <div class="wms-demo__panel-head">
            <ElSelect
              v-model="form.sample_pool_id"
              placeholder="选择样本池"
              class="wms-demo__pool-select"
              @change="selectPool"
            >
              <ElOption v-for="pool in pools" :key="pool.id" :label="pool.name" :value="pool.id" />
            </ElSelect>
            <ElButton
              :icon="CopyDocument"
              :disabled="!selectedPool || !selectedPool.is_system"
              @click="copyPool"
              >复制为租户样本池</ElButton
            >
            <ElButton
              type="primary"
              :icon="Check"
              :disabled="!selectedPool || selectedPool.is_system"
              @click="savePool"
              >保存样本池</ElButton
            >
          </div>
          <ElInput
            v-if="selectedPool"
            v-model="selectedPool.prompt_template"
            type="textarea"
            :rows="5"
            placeholder="样本池提示词"
            :disabled="selectedPool.is_system"
          />
          <ElTable :data="selectedPool?.items ?? []" border class="wms-demo__table">
            <ElTableColumn label="启用" width="82"
              ><template #default="{ row }"
                ><ElSwitch
                  v-model="row.enabled"
                  :disabled="selectedPool?.is_system"
                  @change="saveItem(row)" /></template
            ></ElTableColumn>
            <ElTableColumn prop="group_name" label="分组" min-width="130" />
            <ElTableColumn label="样本项" min-width="170"
              ><template #default="{ row }"
                ><ElInput
                  v-model="row.item_name"
                  :disabled="selectedPool?.is_system"
                  @change="saveItem(row)" /></template
            ></ElTableColumn>
            <ElTableColumn label="规格模式" min-width="220"
              ><template #default="{ row }"
                ><ElInput
                  :disabled="selectedPool?.is_system"
                  :model-value="row.spec_patterns.join('、')"
                  @change="saveItem(row)"
                  @update:model-value="row.spec_patterns = splitText($event)" /></template
            ></ElTableColumn>
            <ElTableColumn label="权重" width="120"
              ><template #default="{ row }"
                ><ElInputNumber
                  v-model="row.weight"
                  :disabled="selectedPool?.is_system"
                  :min="1"
                  :max="10"
                  @change="saveItem(row)" /></template
            ></ElTableColumn>
          </ElTable>
        </section>
      </ElTabPane>

      <ElTabPane label="预览与生成" name="preview">
        <section class="wms-demo__panel">
          <div class="wms-demo__panel-head">
            <div class="wms-demo__panel-title">生成预览</div>
            <ElSpace>
              <ElButton :icon="View" :loading="previewing" @click="previewDemo">预览</ElButton>
              <ElButton type="primary" :icon="Plus" :loading="initializing" @click="initDemo"
                >生成试用数据</ElButton
              >
            </ElSpace>
          </div>
          <ElDescriptions v-if="preview" :column="3" border>
            <ElDescriptionsItem label="样本池">{{ preview.sample_pool_name }}</ElDescriptionsItem>
            <ElDescriptionsItem label="模式">{{ preview.scale_mode }}</ElDescriptionsItem>
            <ElDescriptionsItem label="产品数">{{ preview.product_mix.length }}</ElDescriptionsItem>
          </ElDescriptions>
          <ElTable :data="previewCountRows" border class="wms-demo__table">
            <ElTableColumn prop="name" label="对象" />
            <ElTableColumn prop="count" label="预计数量" width="140" />
          </ElTable>
          <ElAlert
            v-for="item in preview?.warnings ?? []"
            :key="item"
            :title="item"
            type="warning"
            show-icon
            :closable="false"
            class="wms-demo__alert"
          />
        </section>

        <section class="wms-demo__panel" v-if="latestBatch">
          <div class="wms-demo__panel-title">最近生成</div>
          <ElDescriptions :column="2" border>
            <ElDescriptionsItem label="批次号">{{ latestBatch.demo_batch_id }}</ElDescriptionsItem>
            <ElDescriptionsItem label="任务ID">{{ latestBatch.task_id }}</ElDescriptionsItem>
          </ElDescriptions>
          <ElTimeline class="wms-demo__timeline">
            <ElTimelineItem v-for="item in latestBatch.summary" :key="item" type="success">{{
              item
            }}</ElTimelineItem>
          </ElTimeline>
        </section>
      </ElTabPane>

      <ElTabPane label="记录清理" name="history">
        <section class="wms-demo__panel">
          <div class="wms-demo__panel-head">
            <ElInput
              v-model="cleanBatchId"
              clearable
              placeholder="输入试用批次号"
              class="wms-demo__batch-input"
            />
            <ElButton type="danger" plain :icon="Delete" :loading="cleaning" @click="cleanDemo"
              >清理批次</ElButton
            >
          </div>
          <ElTable :data="histories" border>
            <ElTableColumn prop="demo_batch_id" label="批次号" min-width="190" />
            <ElTableColumn prop="title" label="任务" min-width="220" />
            <ElTableColumn prop="status" label="状态" width="110" />
            <ElTableColumn label="操作" width="110"
              ><template #default="{ row }"
                ><ElButton text type="danger" @click="cleanBatchId = row.demo_batch_id || ''"
                  >选择</ElButton
                ></template
              ></ElTableColumn
            >
          </ElTable>
        </section>
      </ElTabPane>
    </ElTabs>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Check, CopyDocument, Delete, Plus, View } from "@element-plus/icons-vue";
import WmsDemoAPI, {
  type WmsDemoBatch,
  type WmsDemoHistory,
  type WmsDemoInitForm,
  type WmsDemoPreview,
  type WmsDemoSampleItem,
  type WmsDemoSamplePool,
} from "@/api/module_wms/demo";

defineOptions({ name: "WmsDemo", inheritAttrs: false });

const activeTab = ref("config");
const previewing = ref(false);
const initializing = ref(false);
const cleaning = ref(false);
const preview = ref<WmsDemoPreview>();
const latestBatch = ref<WmsDemoBatch>();
const cleanBatchId = ref("");
const pools = ref<WmsDemoSamplePool[]>([]);
const selectedPool = ref<WmsDemoSamplePool>();
const histories = ref<WmsDemoHistory[]>([]);
const sizeOptions = [
  { label: "小型", value: "small" },
  { label: "中型", value: "medium" },
  { label: "大型", value: "large" },
];
const quantityFields = [
  { key: "warehouse_count", label: "仓库", min: 1, max: 8 },
  { key: "location_count", label: "库位", min: 10, max: 1000 },
  { key: "material_count", label: "物料", min: 10, max: 600 },
  { key: "stock_flow_count", label: "库存流水", min: 20, max: 5000 },
  { key: "business_doc_count", label: "业务单据", min: 20, max: 1500 },
  { key: "warning_count", label: "预警", min: 0, max: 200 },
] as const;

const form = reactive<WmsDemoInitForm>({
  profile: {
    company_name: "华南智能制造有限公司",
    industry: "电工装备",
    company_size: "medium",
    scenario: "starter",
  },
  numbering: {
    tenant_short_code: "EE",
    numbering_style: "tenant",
    date_format: "yyyyMMdd",
    sequence_digits: 4,
    include_demo_suffix: true,
    prefixes: {},
  },
  product_directions: [],
  custom_products: [
    {
      name: "油浸式变压器",
      category: "变压器",
      voltage_level: "10kV",
      spec_examples: ["S13-M", "S20-M"],
      storage_traits: ["重型库位", "防潮"],
      weight: 4,
    },
    {
      name: "高压开关柜",
      category: "成套设备",
      voltage_level: "35kV",
      spec_examples: ["KYN61", "XGN"],
      storage_traits: ["成品区", "防碰撞"],
      weight: 3,
    },
  ],
  warehouse_scenarios: ["原材料入库", "质检入库", "销售出库", "生产领料", "调拨盘点"],
  scale_mode: "standard",
  quantity_targets: {
    warehouse_count: 3,
    location_count: 100,
    material_count: 80,
    stock_flow_count: 300,
    business_doc_count: 160,
    warning_count: 8,
  },
  time_range_days: 90,
  naming_style: "industrial",
  quality_requirements:
    "覆盖到货、检验、入库、出库、领料、调拨、盘点、库存预警；产品和批次编号体现租户短码。",
  generation_instructions: "产品围绕电工装备供应商物资范围生成，供应商、规格、批次不要重复单一。",
  use_ai_enrichment: true,
});

const previewCountRows = computed(() =>
  Object.entries(preview.value?.estimated_counts ?? {}).map(([name, count]) => ({ name, count }))
);

onMounted(async () => {
  await Promise.all([loadPools(), loadHistory()]);
});

function splitText(value: string) {
  return value
    .split(/[、,，\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function addProduct() {
  form.custom_products.push({
    name: "",
    category: "",
    spec_examples: [],
    storage_traits: [],
    weight: 1,
  });
}

function removeProduct(index: number) {
  form.custom_products.splice(index, 1);
}

async function loadPools() {
  const response = await WmsDemoAPI.samplePools();
  pools.value = response.data.data;
  selectedPool.value = pools.value[0];
  form.sample_pool_id = selectedPool.value?.id;
}

function selectPool(poolId: number) {
  selectedPool.value = pools.value.find((item) => item.id === poolId);
}

async function copyPool() {
  if (!selectedPool.value) return;
  const response = await WmsDemoAPI.copySamplePool(selectedPool.value.id);
  await loadPools();
  form.sample_pool_id = response.data.data.id;
  selectPool(response.data.data.id);
  ElMessage.success("已复制为租户样本池");
}

async function savePool() {
  if (!selectedPool.value || selectedPool.value.is_system) return;
  const response = await WmsDemoAPI.updateSamplePool(selectedPool.value.id, {
    name: selectedPool.value.name,
    prompt_template: selectedPool.value.prompt_template,
    fallback_template: selectedPool.value.fallback_template,
    config: selectedPool.value.config,
    is_active: selectedPool.value.is_active,
  });
  selectedPool.value = response.data.data;
  ElMessage.success("样本池已保存");
}

async function saveItem(row: WmsDemoSampleItem) {
  if (!selectedPool.value || selectedPool.value.is_system) return;
  await WmsDemoAPI.updateSampleItem(row.id, row);
}

async function previewDemo() {
  previewing.value = true;
  try {
    const response = await WmsDemoAPI.preview(form);
    preview.value = response.data.data;
    activeTab.value = "preview";
  } finally {
    previewing.value = false;
  }
}

async function initDemo() {
  initializing.value = true;
  try {
    const response = await WmsDemoAPI.init(form);
    latestBatch.value = response.data.data;
    cleanBatchId.value = latestBatch.value.demo_batch_id;
    preview.value = latestBatch.value.preview_snapshot;
    await loadHistory();
    ElMessage.success("试用数据已生成");
  } finally {
    initializing.value = false;
  }
}

async function loadHistory() {
  const response = await WmsDemoAPI.history();
  histories.value = response.data.data;
}

async function cleanDemo() {
  const batchId = cleanBatchId.value.trim();
  if (!batchId) {
    ElMessage.warning("请输入试用批次号");
    return;
  }
  await ElMessageBox.confirm(`确认清理批次 ${batchId} 的试用数据？`, "清理确认", {
    type: "warning",
  });
  cleaning.value = true;
  try {
    const response = await WmsDemoAPI.clean(batchId);
    const total = Object.values(response.data.data.counts).reduce((sum, item) => sum + item, 0);
    ElMessage.success(`已清理 ${total} 条试用数据`);
    if (latestBatch.value?.demo_batch_id === batchId) latestBatch.value = undefined;
    await loadHistory();
  } finally {
    cleaning.value = false;
  }
}
</script>

<style scoped lang="scss">
.wms-demo {
  padding: 16px;
}

.wms-demo__tabs {
  --el-tabs-header-height: 42px;
}

.wms-demo__grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 16px;
}

.wms-demo__panel {
  padding: 16px;
  margin-bottom: 16px;
  background: var(--el-bg-color);
  border: 1px solid var(--fa-card-border);
  border-radius: 8px;
}

.wms-demo__panel-head {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.wms-demo__panel-title {
  margin-bottom: 14px;
  font-size: 15px;
  font-weight: 600;
}

.wms-demo__numbers {
  display: grid;
  gap: 12px;
}

.wms-demo__number {
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr);
  gap: 8px;
  align-items: center;
}

.wms-demo__textarea-row,
.wms-demo__table,
.wms-demo__timeline {
  margin-top: 14px;
}

.wms-demo__pool-select,
.wms-demo__batch-input {
  width: 320px;
}

.wms-demo__alert {
  margin-top: 10px;
}

@media (width <= 900px) {
  .wms-demo__grid {
    grid-template-columns: 1fr;
  }

  .wms-demo__panel-head {
    flex-direction: column;
    align-items: stretch;
  }

  .wms-demo__pool-select,
  .wms-demo__batch-input {
    width: 100%;
  }
}
</style>
