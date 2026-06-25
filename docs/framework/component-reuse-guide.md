# fa-* 组件复用规范

本文约束新业务页面优先复用当前框架已有的 Art Design Pro / `fa-*` 封装，避免直接堆 Element Plus 组件导致交互和视觉不一致。

## 基础原则

- 业务页面优先使用 `fa-*` 组件和现有 hooks。
- Element Plus 原生组件用于布局、少量组件内部插槽、或当前 `fa-*` 尚未覆盖的场景。
- 可配置页面使用配置数组和渲染函数，不在模板里重复写一组相同按钮、表单项和状态标签。
- 缺少通用能力时，先判断是否能沉淀到 `frontend/web/src/components/`，再决定业务内私有组件。

## 列表页

当前标准组合可参考 `frontend/web/src/views/module_platform/tenant/index.vue`：

- 搜索：`FaSearchBar`
- 表格工具栏：`FaTableHeader`、`FaTableHeaderLeft`
- 表格：`FaTable`
- 数据请求：`useTable`
- 多选：`useTableSelection`
- 删除确认：`confirmDelete`、`confirmBatchDelete`
- 行操作：`renderTableOperationCell`
- 状态列：`resolveStatusColumns`

列表页约定：

- 页面根节点使用 `fa-full-height`。
- 搜索条件通过 `SearchFormItem[]` 配置，审计字段使用 `include-audit`。
- 表格列通过 `columnsFactory` 生成，状态字段优先交给 `resolveStatusColumns`。
- 行操作先定义 `TableOperationAction[]`，再按 `hasAuth` 过滤后交给 `renderTableOperationCell`。
- 新增、批删、导入、导出、批量启停使用 `FaTableHeaderLeft` 的权限 props，不重复写按钮布局。

## 表单与弹窗

推荐组合：

- 弹窗：`FaDialog`
- 抽屉：`FaDrawer`
- 表单：`FaForm`
- 详情：`FaDescriptions`

使用约定：

- 创建/编辑弹窗用 `FaDialog` 的 `form-mode="create"` 或 `form-mode="update"`，详情用 `form-mode="detail"`。
- 表单项使用 `FormItem[]` 配置；普通输入、选择、开关、日期、级联、树选择都走 `FaForm` 内置类型。
- 详情页使用 `FaDescriptions` 的 `items` 和字段插槽；状态字段可使用内置 `tag` 或 `FaStatusTag`。
- 复杂编辑区可以用 `ElTabs` 分组，但每个 tab 内仍优先放 `FaForm`。

## 导入导出与上传

已有组件：

- Excel 导入：`FaExcelImport`、`FaImportDialog`
- Excel 导出：`FaExcelExport`、`FaExportDialog`
- 文件上传：`FaUpload`

使用约定：

- 表格页工具栏只暴露导入/导出入口，弹窗内容交给 `fa-*` 导入导出组件。
- 上传交互统一使用 `FaUpload`，复用其预览、大小限制、裁剪等能力。
- 上传分类、业务存储路径和权限属于后端接口契约，不在业务页面里临时拼接路径。

## 图表与统计

普通 dashboard 和业务统计优先使用：

- `FaStatsCard`
- `FaProgressCard`
- `FaDataListCard`
- `FaTimelineListCard`
- `FaBarChartCard`
- `FaLineChartCard`
- `FaDonutChartCard`
- `components/charts/fa-*`
- `FaCountTo`

只有当前图表封装不能表达时，才使用 `frontend/web/src/components/ECharts/index.vue` 或新增 `components/charts/fa-xxx-chart`。

## 权限写法

- 新平台模块权限使用 `module_platform:<resource>:<action>`。
- 系统模块权限使用 `module_system:<resource>:<action>`。
- 租户管理位于平台模块，新规范权限为 `module_platform:tenant:*`。
- 历史 `module_system:tenant:*` 只作为兼容别名保留，新页面和新菜单种子不再新增旧命名。
- 前端按钮显示统一走 `useAuth`、`v-auth` 或 `v-hasPerm`，不要手写 `userStore.prems.includes(...)`。

## 例外处理

以下情况允许业务内私有组件：

- 组件包含强业务流程，无法通过 props 泛化。
- 只在单一页面内出现，且没有跨模块复用价值。
- 当前 `fa-*` 组件无法满足交互，需要先验证业务闭环。

私有组件稳定后，如果第二个模块也需要，应迁移到共享 `fa-*` 或通用 hooks。
