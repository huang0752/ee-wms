# Dashboard 接入规范

本文约束业务模块接入 dashboard 的目录、接口数据形态和组件复用方式。当前框架已有示例位于：

- `frontend/web/src/views/dashboard/home/index.vue`
- `frontend/web/src/views/dashboard/analysis/index.vue`
- `frontend/web/src/views/dashboard/workplace/index.vue`
- `frontend/web/src/views/dashboard/screen/index.vue`
- `frontend/web/src/components/cards/`
- `frontend/web/src/components/charts/`
- `frontend/web/src/components/ECharts/index.vue`

## 页面类型

### 普通工作台

用于后台首页、业务概览、个人待办入口。优先参考 `dashboard/home` 和 `dashboard/workplace`。

推荐组件：

- 指标卡：`FaStatsCard`、`FaProgressCard`
- 小趋势卡：`FaBarChartCard`、`FaLineChartCard`、`FaDonutChartCard`
- 列表卡：`FaDataListCard`、`FaTimelineListCard`
- 图表：`FaBarChart`、`FaLineChart`、`FaRingChart`、`FaHBarChart`
- 数字动画：`FaCountTo`

布局约定：

- 页面入口放在 `frontend/web/src/views/module_xxx/dashboard/index.vue`。
- 复杂区块拆到同级 `modules/`，参考 `dashboard/workplace/modules/*`。
- 栅格使用 `ElRow` / `ElCol`，移动端至少配置 `:xs="24"`。
- 区块间距使用现有 `mb-5`、`gap-5`、`card-group` 等模式，不新增孤立的页面级视觉风格。

### 分析页

用于趋势、排行、分布和多图表组合。优先参考 `dashboard/analysis/index.vue`。

推荐组件：

- 趋势：`FaLineChart`
- 柱状：`FaBarChart`、`FaHBarChart`、`FaDualBarCompareChart`
- 占比：`FaRingChart`
- 分布：`FaScatterChart`、`FaRadarChart`
- 低层封装：只有 `fa-*` 图表不能表达时，才使用 `ECharts/index.vue` 或直接配置 ECharts。

### 大屏

用于全屏态监控和展示。优先参考 `dashboard/screen/index.vue`。

大屏可以有更强视觉效果，但仍应复用 `components/charts` 和当前 ECharts 初始化方式。普通业务后台不要复制大屏的绝对定位、暗色面板和固定尺寸样式。

## 标准数据形态

业务 dashboard 接口建议聚合为一个模块级接口，例如：

```ts
export interface ModuleDashboardData {
  summaryCards: Array<{
    key: string;
    title: string;
    value: number;
    unit?: string;
    description?: string;
    icon?: string;
    trend?: number;
  }>;
  trendSeries: Array<{
    name: string;
    xAxis: string[];
    values: number[];
  }>;
  rankings: Array<{
    key: string | number;
    name: string;
    value: number;
    percent?: number;
  }>;
  warnings: Array<{
    id: string | number;
    title: string;
    level: "info" | "warning" | "danger";
    time?: string;
  }>;
  realtime?: {
    online?: number;
    pending?: number;
    updatedAt?: string;
  };
}
```

前端 API 文件放在 `frontend/web/src/api/module_xxx/dashboard.ts`。页面只负责把接口字段映射到 `fa-*` 组件 props，不在组件里硬编码业务枚举和阈值。

## 加载与空状态

- 普通工作台使用页面级 `loading` 或区块级 skeleton，不让图表在无数据时抛错。
- 列表数据为空时沿用卡片组件的空态；表格类数据使用 `FaTable` 默认 `ElEmpty`。
- 自动刷新只放在页面入口或 dashboard 专用 hook 中，子模块不各自启动定时器。

## 复用边界

- 业务模块 dashboard 应优先组合现有 `cards`、`charts`、`FaCountTo`。
- 需要新增通用卡片或图表时，沉淀到 `frontend/web/src/components/cards` 或 `frontend/web/src/components/charts`，不要只放在单个业务模块内。
- 如果只是业务文案、颜色、数据字段不同，不新增组件；通过 props 映射解决。
