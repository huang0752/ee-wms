<template>
  <div class="wms-transfer">
    <ElCard shadow="never"><div class="bar"><ElInput v-model="keyword" placeholder="调拨单号" :prefix-icon="Search" clearable /><ElButton :icon="Refresh" @click="refreshData" /><ElButton type="primary" :icon="Plus" @click="openCreate">新建调拨</ElButton></div></ElCard>
    <ElCard shadow="never"><ElTable v-loading="loading" :data="rows" row-key="id" height="calc(100vh - 310px)">
      <ElTableColumn prop="order_no" label="调拨单号" min-width="150" /><ElTableColumn prop="from_warehouse_id" label="调出仓" width="100" /><ElTableColumn prop="to_warehouse_id" label="调入仓" width="100" /><ElTableColumn prop="status" label="状态" width="120" />
      <ElTableColumn label="操作" width="180"><template #default="{ row }"><ElButton text type="primary" :disabled="row.status !== 'draft'" @click="confirm(row)">确认</ElButton><ElButton text @click="loadLines(row)">明细</ElButton></template></ElTableColumn>
    </ElTable></ElCard>
    <ElDialog v-model="createVisible" title="新建调拨" width="720px">
      <ElForm :model="form" label-width="96px"><ElRow :gutter="16"><ElCol :span="8"><ElFormItem label="单号"><ElInput v-model="form.order_no" /></ElFormItem></ElCol><ElCol :span="8"><ElFormItem label="调出仓"><ElInputNumber v-model="form.from_warehouse_id" :min="1" /></ElFormItem></ElCol><ElCol :span="8"><ElFormItem label="调入仓"><ElInputNumber v-model="form.to_warehouse_id" :min="1" /></ElFormItem></ElCol></ElRow>
      <ElTable :data="form.lines" border><ElTableColumn label="物料ID"><template #default="{ row }"><ElInputNumber v-model="row.material_id" :min="1" /></template></ElTableColumn><ElTableColumn label="调出库位"><template #default="{ row }"><ElInputNumber v-model="row.from_location_id" :min="1" /></template></ElTableColumn><ElTableColumn label="调入库位"><template #default="{ row }"><ElInputNumber v-model="row.to_location_id" :min="1" /></template></ElTableColumn><ElTableColumn label="批次"><template #default="{ row }"><ElInput v-model="row.batch_no" /></template></ElTableColumn><ElTableColumn label="数量"><template #default="{ row }"><ElInputNumber v-model="row.quantity" :min="0.0001" :precision="4" /></template></ElTableColumn></ElTable></ElForm>
      <template #footer><ElButton @click="createVisible=false">取消</ElButton><ElButton type="primary" @click="submitCreate">保存</ElButton></template>
    </ElDialog>
    <ElDialog v-model="linesVisible" title="调拨明细" width="720px"><ElTable :data="lineRows" border><ElTableColumn prop="material_id" label="物料ID"/><ElTableColumn prop="batch_no" label="批次"/><ElTableColumn prop="quantity" label="数量"/><ElTableColumn prop="status" label="状态"/></ElTable></ElDialog>
  </div>
</template>
<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { Plus, Refresh, Search } from "@element-plus/icons-vue";
import WmsTransferAPI, { type WmsTransferForm, type WmsTransferLine, type WmsTransferOrder } from "@/api/module_wms/transfer";
defineOptions({ name: "WmsTransfer", inheritAttrs: false });
const keyword=ref(""); const loading=ref(false); const createVisible=ref(false); const linesVisible=ref(false); const rows=ref<WmsTransferOrder[]>([]); const lineRows=ref<WmsTransferLine[]>([]);
const form=reactive<WmsTransferForm>({lines:[{quantity:1}]});
async function refreshData(){loading.value=true;try{const r=await WmsTransferAPI.list({page_no:1,page_size:50,order_no:keyword.value||undefined});rows.value=r.data.data.items||[]}finally{loading.value=false}}
function openCreate(){Object.assign(form,{order_no:"",from_warehouse_id:undefined,to_warehouse_id:undefined,lines:[{quantity:1}]});createVisible.value=true}
async function submitCreate(){await WmsTransferAPI.create(form);ElMessage.success("创建成功");createVisible.value=false;await refreshData()}
async function confirm(row:WmsTransferOrder){await WmsTransferAPI.confirm(row.id!);ElMessage.success("确认成功");await refreshData()}
async function loadLines(row:WmsTransferOrder){const r=await WmsTransferAPI.lines(row.id!);lineRows.value=r.data.data;linesVisible.value=true}
onMounted(refreshData);
</script>
<style scoped>.wms-transfer{display:flex;flex-direction:column;gap:12px;padding:16px}.bar{display:flex;gap:12px;align-items:center;justify-content:flex-end}</style>

