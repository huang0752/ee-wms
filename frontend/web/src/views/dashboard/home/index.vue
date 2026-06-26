<template>
  <div class="wms-home">
    <section class="wms-hero">
      <div>
        <p class="wms-kicker">EE WMS</p>
        <h1>电工装备智慧仓储系统</h1>
        <p class="wms-subtitle">
          当前处于产品减法与基础模块建设阶段。系统已保留平台、系统、任务、AI
          和代码生成底座，示例与营销入口按 WMS 装配裁剪。
        </p>
      </div>
      <div class="wms-assembly">
        <span>运行装配</span>
        <strong>{{ assemblyTitle }}</strong>
      </div>
    </section>

    <ElRow :gutter="16">
      <ElCol v-for="item in statusCards" :key="item.title" :xs="24" :sm="12" :lg="6" class="mb-4">
        <ElCard shadow="never" class="wms-card">
          <div class="wms-card-head">
            <FaSvgIcon :icon="item.icon" />
            <span>{{ item.title }}</span>
          </div>
          <strong>{{ item.value }}</strong>
          <p>{{ item.description }}</p>
        </ElCard>
      </ElCol>
    </ElRow>

    <ElRow :gutter="16">
      <ElCol :xs="24" :lg="15" class="mb-4">
        <ElCard shadow="never" class="wms-panel">
          <template #header>
            <div class="wms-panel-title">
              <span>建设步骤</span>
              <ElTag type="info" effect="plain">第一版简单实现</ElTag>
            </div>
          </template>
          <div class="wms-step-list">
            <div v-for="step in roadmap" :key="step.name" class="wms-step">
              <div class="wms-step-index">{{ step.index }}</div>
              <div>
                <h3>{{ step.name }}</h3>
                <p>{{ step.description }}</p>
              </div>
              <ElTag :type="step.type" effect="light">{{ step.status }}</ElTag>
            </div>
          </div>
        </ElCard>
      </ElCol>

      <ElCol :xs="24" :lg="9" class="mb-4">
        <ElCard shadow="never" class="wms-panel">
          <template #header>
            <div class="wms-panel-title">
              <span>已裁剪内容</span>
              <ElTag type="success" effect="plain">运行中</ElTag>
            </div>
          </template>
          <ul class="wms-cut-list">
            <li v-for="item in cutItems" :key="item">
              <FaSvgIcon icon="ri:check-line" />
              <span>{{ item }}</span>
            </li>
          </ul>
        </ElCard>
      </ElCol>
    </ElRow>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useAssemblyStore } from "@stores";

defineOptions({ name: "Home", inheritAttrs: false });

const assemblyStore = useAssemblyStore();

const assemblyTitle = computed(
  () => assemblyStore.summary.title || assemblyStore.summary.name || "WMS"
);

const statusCards = [
  {
    title: "产品装配",
    value: "WMS",
    description: "按 WMS 运行态加载功能",
    icon: "ri:apps-2-line",
  },
  {
    title: "业务模块",
    value: "待建设",
    description: "下一步创建 module_wms",
    icon: "ri:archive-stack-line",
  },
  {
    title: "接口基座",
    value: "已保留",
    description: "系统、平台、任务、AI 可用",
    icon: "ri:server-line",
  },
  {
    title: "演示内容",
    value: "已关闭",
    description: "不展示框架营销与案例入口",
    icon: "ri:scissors-cut-line",
  },
];

const roadmap = [
  {
    index: "01",
    name: "产品运行面裁剪",
    description: "隐藏框架示例、宣传公告、营销路由和无关菜单，形成 WMS 产品壳。",
    status: "进行中",
    type: "warning" as const,
  },
  {
    index: "02",
    name: "WMS 模块空壳",
    description: "建立 module_wms 后端命名空间、前端目录、菜单和权限前缀。",
    status: "下一步",
    type: "primary" as const,
  },
  {
    index: "03",
    name: "基础资料",
    description: "仓库、库区、库位、物料、批次规则和供应商等主数据。",
    status: "待开始",
    type: "info" as const,
  },
  {
    index: "04",
    name: "库存与出入库",
    description: "先批次库存，预留 SN、PDA、IQC、MES/ERP 对接扩展点。",
    status: "待开始",
    type: "info" as const,
  },
];

const cutItems = [
  "module_example 插件接口",
  "案例管理动态菜单",
  "定价、文章、教程、更新日志静态路由",
  "框架发布公告与新版本提示",
  "登录后新手引导弹窗",
  "首页交易、粉丝、版本更新等演示卡片",
];
</script>

<style scoped lang="scss">
.wms-home {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.wms-hero {
  display: flex;
  gap: 24px;
  align-items: center;
  justify-content: space-between;
  min-height: 176px;
  padding: 28px;
  background:
    linear-gradient(135deg, rgb(21 128 61 / 10%), transparent 42%),
    linear-gradient(90deg, var(--el-bg-color), var(--el-fill-color-light));
  border: 1px solid var(--fa-card-border);
  border-radius: 8px;
}

.wms-kicker {
  margin: 0 0 8px;
  font-size: 13px;
  font-weight: 700;
  color: var(--el-color-primary);
}

.wms-hero h1 {
  margin: 0;
  font-size: 30px;
  line-height: 1.25;
  color: var(--el-text-color-primary);
}

.wms-subtitle {
  max-width: 760px;
  margin: 12px 0 0;
  font-size: 14px;
  line-height: 1.7;
  color: var(--el-text-color-secondary);
}

.wms-assembly {
  display: grid;
  gap: 8px;
  min-width: 180px;
  padding: 18px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}

.wms-assembly span,
.wms-card p,
.wms-step p {
  color: var(--el-text-color-secondary);
}

.wms-assembly strong {
  font-size: 18px;
  color: var(--el-text-color-primary);
}

.wms-card,
.wms-panel {
  border: 1px solid var(--fa-card-border);
  border-radius: 8px;
}

.wms-card-head,
.wms-panel-title,
.wms-cut-list li,
.wms-step {
  display: flex;
  align-items: center;
}

.wms-card-head {
  gap: 8px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.wms-card strong {
  display: block;
  margin-top: 14px;
  font-size: 24px;
  color: var(--el-text-color-primary);
}

.wms-card p {
  margin: 8px 0 0;
  font-size: 13px;
}

.wms-panel-title {
  justify-content: space-between;
  font-weight: 600;
}

.wms-step-list {
  display: grid;
  gap: 12px;
}

.wms-step {
  gap: 14px;
  min-height: 76px;
  padding: 14px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}

.wms-step-index {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  font-weight: 700;
  color: var(--el-color-primary);
  background: var(--el-fill-color-light);
  border-radius: 8px;
}

.wms-step h3 {
  margin: 0;
  font-size: 15px;
  color: var(--el-text-color-primary);
}

.wms-step p {
  margin: 6px 0 0;
  font-size: 13px;
  line-height: 1.5;
}

.wms-step > div:nth-child(2) {
  flex: 1;
  min-width: 0;
}

.wms-cut-list {
  display: grid;
  gap: 13px;
  padding: 0;
  margin: 0;
  list-style: none;
}

.wms-cut-list li {
  gap: 8px;
  font-size: 14px;
  color: var(--el-text-color-regular);
}

.wms-cut-list :deep(.fa-svg-icon) {
  color: var(--el-color-success);
}

@media (width <= 768px) {
  .wms-hero {
    flex-direction: column;
    align-items: stretch;
    padding: 20px;
  }

  .wms-hero h1 {
    font-size: 24px;
  }

  .wms-step {
    align-items: flex-start;
  }
}
</style>
