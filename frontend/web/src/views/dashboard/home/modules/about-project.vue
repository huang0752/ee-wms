<template>
  <div class="fa-card p-5 flex justify-between h-full">
    <div>
      <h2 class="text-2xl font-medium">关于项目</h2>
      <p class="text-g-700 mt-1">
        {{ systemName }} 面向多租户仓储业务，提供库存、单据、条码、预警与演示数据能力。
      </p>
      <p class="text-g-700 mt-1">系统默认品牌可由租户配置覆盖，业务模块按 WMS 产品边界逐步开放。</p>
    </div>
    <img class="w-75 max-md:hidden!" src="@imgs/draw/draw1.png" alt="draw1" loading="eager" />
  </div>
</template>

<script setup lang="ts">
import AppConfig from "@/config";

const systemName = AppConfig.systemInfo.name;
</script>
