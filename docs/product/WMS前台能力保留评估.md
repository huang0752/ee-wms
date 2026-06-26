# WMS 前台能力保留评估

## 结论

WMS V1 前台只保留业务运行需要的入口：系统、平台、仓储业务、用户资料、支付/工作台等基础入口。AI、任务和代码生成作为框架能力保留在后端和代码层，但不直接展示给 WMS 业务用户。

## 入口评估

| 入口 | V1 前台是否展示 | 处理方式 | 原因 |
|---|---|---|---|
| 代码管理 / 代码生成 | 否 | 禁用 `module-generator` route group | 开发工具，不属于仓储业务运行面。 |
| AI管理 | 否 | 禁用 `ai-chat` route group，关闭 `ai_assistant` feature flag | 模型、供应商 Key、调用参数属于平台/框架管理能力。 |
| 任务管理 | 否 | 禁用 `module-task` route group | 框架任务中心偏配置和调度管理，不等同于 WMS 作业任务。 |

## 保留边界

后端仍启用 `module_ai`、`module_task`、`module_generator`，用于框架维护、后续复用和能力验证。WMS 不直接暴露这些管理页。

后续如果需要 AI 或任务能力，应在 `module_wms` 下建立业务入口，例如：

- `module_wms/assistant`: 库存预警说明、出入库异常解释、补货建议。
- `module_wms/work`: 入库作业、出库作业、盘点任务、待办处理。
- `module_wms/import`: 批量导入、试用数据生成、长任务进度。

这些页面可以复用框架服务，但权限、菜单和交互应使用 `module_wms:<resource>:<action>`，避免把框架管理入口直接给业务用户。

## 当前装配要求

- `enabled_route_groups` 不包含 `ai-chat`、`module-task`、`module-generator`。
- `disabled_route_groups` 包含 `ai-chat`、`module-task`、`module-generator`。
- `featureFlags.aiAssistant = false`。
- 测试必须覆盖 `AI管理`、`任务管理`、`代码管理` 在 WMS 菜单中过滤。
