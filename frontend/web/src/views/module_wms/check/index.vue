<template>
  <div class="wms-check">
    <ElCard shadow="never"><div class="bar"><ElInput v-model="keyword" placeholder="盘点单号" :prefix-icon="Search" clearable /><ElButton :icon="Refresh" @click="refreshData" /><ElButton type="primary" :icon="Plus" @click="openCreate">新建盘点</ElButton></div></ElCard>
    <ElCard shadow="never"><ElTable v-loading="loading" :data="rows" row-key="id" height="calc(100vh - 310px)">
      <ElTableColumn prop="order_no" label="盘点单号" min-width="150" /><ElTableColumn prop="warehouse_id" label="仓库ID" width="100" /><ElTableColumn prop="status" label="状态" width="120" /><ElTableColumn prop="audited_time" label="审核时间" min-width="170" />
      <ElTableColumn label="操作" width="180"><template #default="{ row }"><ElButton text type="primary" :disabled="row.status !== 'draft'" @click="audit(row)">审核</ElButton><ElButton text @click="loadLines(row)">明细</ElButton></template></ElTableColumn>
    </ElTable></ElCard>
    <ElDialog v-model="createVisible" title="新建盘点" width="760px"><ElForm :model="form" label-width="96px"><ElRow><ElCol :span="8"><ElFormItem label="仓库ID"><ElInputNumber v-model="form.warehouse_id" :min="1" /></ElFormItem></ElCol><ElCol :span="8"><ElFormItem label="单号"><ElInput v-model="form.order_no" /></ElFormItem></ElCol></ElRow>
    <ElTable :data="form.lines" border><ElTableColumn label="物料ID"><template #default="{ row }"><ElInputNumber v-model="row.material_id" :min="1" /></template></ElTableColumn><ElTableColumn label="库位ID"><template #default="{ row }"><ElInputNumber v-model="row.location_id" :min="1" /></template></ElTableColumn><ElTableColumn label="批次"><template #default="{ row }"><ElInput v-model="row.batch_no" /></template></ElTableColumn><ElTableColumn label="系统数"><template #default="{ row }"><ElInputNumber v-model="row.system_qty" :min="0" :precision="4" /></template></ElTableColumn><ElTableColumn label="实盘数"><template #default="{ row }"><ElInputNumber v-model="row.counted_qty" :min="0" :precision="4" /></template></ElTableColumn></ElTable></ElForm>
    <template #footer><ElButton @click="createVisible=false">取消</ElButton><ElButton type="primary" @click="submitCreate">保存</ElButton></template></ElDialog>
    <ElDialog v-model="linesVisible" title="盘点明细" width="760px"><ElTable :data="lineRows" border><ElTableColumn prop="material_id" label="物料ID"/><ElTableColumn prop="batch_no" label="批次"/><ElTableColumn prop="system_qty" label="系统数"/><ElTableColumn prop="counted_qty" label="实盘数"/><ElTableColumn prop="diff_qty" label="差异"/><ElTableColumn prop="status" label="状态"/></ElTable></ElDialog>
  </div>
</template>
<script setup lang="ts">
import { onMounted, reactive, ref } from "vue"; import { ElMessage } from "element-plus"; import { Plus, Refresh, Search } from "@element-plus/icons-vue";
import WmsCheckAPI,{type WmsCheckForm,type WmsCheckLine,type WmsCheckOrder}from"@/api/module_wms/check";
defineOptions({name:"WmsCheck",inheritAttrs:false}); const keyword=ref("");const loading=ref(false);const createVisible=ref(false);const linesVisible=ref(false);const rows=ref<WmsCheckOrder[]>([]);const lineRows=ref<WmsCheckLine[]>([]);const form=reactive<WmsCheckForm>({lines:[{system_qty:0,counted_qty:0}]});
async function refreshData(){loading.value=true;try{const r=await WmsCheckAPI.list({page_no:1,page_size:50,order_no:keyword.value||undefined});rows.value=r.data.data.items||[]}finally{loading.value=false}}
function openCreate(){Object.assign(form,{order_no:"",warehouse_id:undefined,lines:[{system_qty:0,counted_qty:0}]});createVisible.value=true}
async function submitCreate(){await WmsCheckAPI.create(form);ElMessage.success("创建成功");createVisible.value=false;await refreshData()}
async function audit(row:WmsCheckOrder){await WmsCheckAPI.audit(row.id!);ElMessage.success("审核成功");await refreshData()}
async function loadLines(row:WmsCheckOrder){const r=await WmsCheckAPI.lines(row.id!);lineRows.value=r.data.data;linesVisible.value=true}
onMounted(refreshData);
</script>
<style scoped>.wms-check{display:flex;flex-direction:column;gap:12px;padding:16px}.bar{display:flex;gap:12px;align-items:center;justify-content:flex-end}</style>

