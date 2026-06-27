<template>
  <DashboardScreen class="home-dashboard-screen" />
</template>

<script setup lang="ts">
import DashboardScreen from "@/views/dashboard/screen/index.vue";

defineOptions({ name: "Home", inheritAttrs: false });
</script>

<style scoped>
.home-dashboard-screen {
  height: calc(100vh - 92px);
  min-height: calc(100vh - 92px);
}
</style>
