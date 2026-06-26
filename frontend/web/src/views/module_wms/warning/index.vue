<template>
  <div class="wms-warning">
    <ElCard shadow="never"><div class="bar"><ElInputNumber v-model="warehouseId" :min="1" placeholder="仓库ID" /><ElButton :icon="Refresh" @click="refreshData" /><ElButton type="primary" @click="scan">扫描预警</ElButton></div></ElCard>
    <ElCard shadow="never"><ElTable v-loading="loading" :data="rows" row-key="id" height="calc(100vh - 300px)">
      <ElTableColumn prop="warning_no" label="预警编号" min-width="140"/><ElTableColumn prop="warning_type" label="类型" width="130"/><ElTableColumn prop="material_id" label="物料ID" width="100"/><ElTableColumn prop="current_qty" label="当前数" width="110"/><ElTableColumn prop="threshold_qty" label="阈值" width="110"/><ElTableColumn prop="status" label="状态" width="100"/>
      <ElTableColumn label="操作" width="120"><template #default="{ row }"><ElButton text type="primary" :disabled="row.status==='closed'" @click="close(row)">关闭</ElButton></template></ElTableColumn>
    </ElTable></ElCard>
  </div>
</template>
<script setup lang="ts">
import { onMounted, ref } from "vue"; import { ElMessage } from "element-plus"; import { Refresh } from "@element-plus/icons-vue";
import WmsWarningAPI,{type WmsWarning}from"@/api/module_wms/warning";
defineOptions({name:"WmsWarning",inheritAttrs:false}); const warehouseId=ref<number>();const loading=ref(false);const rows=ref<WmsWarning[]>([]);
async function refreshData(){loading.value=true;try{const r=await WmsWarningAPI.list({page_no:1,page_size:100});rows.value=r.data.data.items||[]}finally{loading.value=false}}
async function scan(){await WmsWarningAPI.scan({warehouse_id:warehouseId.value});ElMessage.success("扫描完成");await refreshData()}
async function close(row:WmsWarning){await WmsWarningAPI.close(row.id!);ElMessage.success("已关闭");await refreshData()}
onMounted(refreshData);
</script>
<style scoped>.wms-warning{display:flex;flex-direction:column;gap:12px;padding:16px}.bar{display:flex;gap:12px;align-items:center;justify-content:flex-end}</style>
